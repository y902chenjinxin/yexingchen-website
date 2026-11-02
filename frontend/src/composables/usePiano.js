/**
 * 钢琴音频引擎（v2.46.334）
 *
 * 采样钢琴：每小三度一个录音（C3~A5 共 12 个），按键时取最近的采样做变速播放。
 * 为什么每小三度而不是每个音：全部 88 键要 88 个文件（十几 MB）；
 * 小三度内变速最多 ±1.5 个半音，音色几乎听不出差别，这是采样钢琴的通行做法。
 *
 * 🔴 三条硬约束：
 *   1. 不能用 `<audio>` 标签（多实例延迟 100ms+、移动端还会被回收）。
 *      这里 fetch + `decodeAudioData` 成 AudioBuffer，之后 `source.start(0)` 立即出声。
 *   2. AudioContext 必须在**用户手势里**创建/resume（浏览器自动播放策略）。
 *      所以 `init()` 只能从「开始演奏」这类点击里调，不能 onMounted 里偷偷调。
 *   3. 必须有限幅（DynamicsCompressor）。同时按 10 个键时，10 路采样叠加会削顶爆音。
 */
import { ref } from 'vue'

/** 采样点（MIDI 音高）→ 文件名。文件名用 s 表示升号（Ds3 = D#3）。 */
const SAMPLES = [
  [48, 'C3'], [51, 'Ds3'], [54, 'Fs3'], [57, 'A3'],
  [60, 'C4'], [63, 'Ds4'], [66, 'Fs4'], [69, 'A4'],
  [72, 'C5'], [75, 'Ds5'], [78, 'Fs5'], [81, 'A5'],
]

const BASE = '/sounds/piano/'
const MAX_VOICES = 24
const RELEASE = 0.22        // 松键后的制音时长（秒）

export function usePiano() {
  const ready = ref(false)
  const loading = ref(false)
  const loaded = ref(0)
  const total = SAMPLES.length
  const error = ref('')

  let ctx = null
  let master = null
  const buffers = new Map()      // midi → AudioBuffer
  const voices = new Map()       // midi → { src, gain, at }
  let initing = null

  function nearestSample(midi) {
    let best = SAMPLES[0][0]
    let dist = Infinity
    for (const [m] of SAMPLES) {
      const d = Math.abs(m - midi)
      if (d < dist) { dist = d; best = m }
    }
    return best
  }

  /** 必须在用户手势里调用一次。重复调用是安全的（会复用同一个 Promise）。 */
  function init() {
    if (ready.value) return Promise.resolve()
    if (initing) return initing
    initing = (async () => {
      loading.value = true
      error.value = ''
      try {
        const AC = window.AudioContext || window.webkitAudioContext
        if (!AC) throw new Error('这台设备的浏览器不支持 Web Audio')
        ctx = new AC({ latencyHint: 'interactive' })
        if (ctx.state === 'suspended') await ctx.resume()

        // 限幅：所有声音先过压缩器再到扬声器，最多 10 个键同时按也不会削顶
        const comp = ctx.createDynamicsCompressor()
        comp.threshold.value = -8
        comp.knee.value = 6
        comp.ratio.value = 12
        comp.attack.value = 0.003
        comp.release.value = 0.25

        master = ctx.createGain()
        master.gain.value = 0.72
        master.connect(comp)
        comp.connect(ctx.destination)

        await Promise.all(SAMPLES.map(async ([midi, name]) => {
          const res = await fetch(BASE + name + '.mp3')
          if (!res.ok) throw new Error(`采样加载失败：${name}`)
          const buf = await res.arrayBuffer()
          buffers.set(midi, await ctx.decodeAudioData(buf))
          loaded.value++
        }))
        ready.value = true
      } catch (e) {
        error.value = e.message || '音频初始化失败'
        throw e
      } finally {
        loading.value = false
      }
    })()
    return initing
  }

  /** 按下：发声（同一个音重复按会先收掉上一个，避免叠成两层） */
  function noteOn(midi, velocity = 0.85) {
    if (!ready.value || !ctx) return
    if (ctx.state === 'suspended') ctx.resume().catch(() => {})
    if (voices.has(midi)) noteOff(midi, 0.04)

    // 复音上限：超了就掐掉最早的那个（钢琴踏板踩到底也不会无限叠）
    if (voices.size >= MAX_VOICES) {
      let oldest = null
      let t = Infinity
      for (const [m, v] of voices) if (v.at < t) { t = v.at; oldest = m }
      if (oldest != null) noteOff(oldest, 0.02)
    }

    const sm = nearestSample(midi)
    const buf = buffers.get(sm)
    if (!buf) return

    const src = ctx.createBufferSource()
    src.buffer = buf
    src.playbackRate.value = Math.pow(2, (midi - sm) / 12)

    const gain = ctx.createGain()
    const now = ctx.currentTime
    const peak = Math.min(1, 0.2 + velocity * 0.8)
    // 4ms 起音：太快会有"咔"的爆音，太慢按键会感觉迟钝
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(peak, now + 0.004)

    src.connect(gain)
    gain.connect(master)
    src.start(now)

    const v = { src, gain, at: now }
    voices.set(midi, v)
    src.onended = () => {
      if (voices.get(midi) === v) voices.delete(midi)
      try { src.disconnect(); gain.disconnect() } catch { /* 已断开 */ }
    }
  }

  /** 松开：走制音包络，不硬切（硬切就是"啪"的一声） */
  function noteOff(midi, release = RELEASE) {
    const v = voices.get(midi)
    if (!v || !ctx) return
    voices.delete(midi)
    const now = ctx.currentTime
    try {
      v.gain.gain.cancelScheduledValues(now)
      v.gain.gain.setValueAtTime(Math.max(0.0001, v.gain.gain.value), now)
      v.gain.gain.exponentialRampToValueAtTime(0.0001, now + release)
      v.src.stop(now + release + 0.02)
    } catch { /* 已经停了 */ }
  }

  function allOff() {
    for (const m of [...voices.keys()]) noteOff(m, 0.08)
  }

  function dispose() {
    allOff()
    try { master?.disconnect() } catch { /* noop */ }
    try { ctx?.close() } catch { /* noop */ }
    buffers.clear()
    ctx = null
    master = null
    ready.value = false
    initing = null
    loaded.value = 0
  }

  return { ready, loading, loaded, total, error, init, noteOn, noteOff, allOff, dispose }
}

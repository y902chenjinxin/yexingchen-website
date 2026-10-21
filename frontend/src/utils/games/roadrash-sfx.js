/** 暴力摩托 · 音效（v2.46.159）
 *
 * 为什么是合成而不是采样：项目里 /sounds/cards/ 只有棋牌采样，没有引擎/碰撞素材；
 * 引擎声本质是「转速决定的连续音」，用 WebAudio 振荡器实时跟速度反而比固定采样更贴（
 * 采样做变调循环会在换速时露馅）。撞击、挥击用噪声 + 低通模拟瞬态冲击。
 *
 * 约束：
 *   - 必须在用户手势里创建 AudioContext（游戏「开始比赛」是 click，满足自动播放策略）。
 *   - 浏览器不支持 WebAudio 时全静默降级，不抛错。
 *   - 静音状态存 localStorage，与棋牌 sfx 各自独立（赛车默认开）。
 */

const KEY = 'roadrash_muted'

let ctx = null
let master = null
let engine = null
let wind = null
let muted = false
try { muted = localStorage.getItem(KEY) === '1' } catch { /* 隐私模式忽略 */ }

function ac() {
  if (ctx) return ctx
  try {
    const AC = window.AudioContext || window.webkitAudioContext
    if (!AC) return null
    ctx = new AC()
    master = ctx.createGain()
    master.gain.value = muted ? 0 : 0.5
    master.connect(ctx.destination)
  } catch { ctx = null }
  return ctx
}

function noiseBuffer(a, dur = 0.4) {
  const len = Math.max(64, Math.floor(a.sampleRate * dur))
  const b = a.createBuffer(1, len, a.sampleRate)
  const d = b.getChannelData(0)
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1
  return b
}

function now() { return ctx ? ctx.currentTime : 0 }

export function setMuted(v) {
  muted = !!v
  try { localStorage.setItem(KEY, muted ? '1' : '0') } catch { /* 忽略 */ }
  if (master && ctx) master.gain.setTargetAtTime(muted ? 0 : 0.5, ctx.currentTime, 0.05)
  if (muted) stopEngine()
}
export function isMuted() { return muted }

/** 引擎：锯齿（主）+ 方波低八度（缸体）→ 低通；LFO 做怠速抖动 */
function startEngine() {
  const a = ac()
  if (!a || engine) return
  try {
    if (a.state === 'suspended') a.resume()
    const o1 = a.createOscillator()
    o1.type = 'sawtooth'
    const o2 = a.createOscillator()
    o2.type = 'square'
    const lp = a.createBiquadFilter()
    lp.type = 'lowpass'
    lp.frequency.value = 700
    lp.Q.value = 2.5
    const g = a.createGain()
    g.gain.value = 0.0001
    const lfo = a.createOscillator()
    lfo.type = 'sine'
    lfo.frequency.value = 7.5
    const lfoG = a.createGain()
    lfoG.gain.value = 4
    lfo.connect(lfoG)
    lfoG.connect(o1.frequency)
    o1.connect(lp)
    o2.connect(lp)
    lp.connect(g)
    g.connect(master)
    o1.start(); o2.start(); lfo.start()
    engine = { o1, o2, lp, g, lfo }

    const src = a.createBufferSource()
    src.buffer = noiseBuffer(a, 1.5)
    src.loop = true
    const bp = a.createBiquadFilter()
    bp.type = 'bandpass'
    bp.frequency.value = 1200
    bp.Q.value = 0.5
    const wg = a.createGain()
    wg.gain.value = 0.0001
    src.connect(bp); bp.connect(wg); wg.connect(master); src.start()
    wind = { src, bp, wg }
  } catch { /* 静默 */ }
}

function stopEngine() {
  if (!engine) return
  try {
    const t = now()
    engine.g.gain.setTargetAtTime(0.0001, t, 0.06)
    engine.o1.stop(t + 0.4)
    engine.o2.stop(t + 0.4)
    engine.lfo.stop(t + 0.4)
    if (wind) {
      wind.wg.gain.setTargetAtTime(0.0001, t, 0.06)
      wind.src.stop(t + 0.4)
    }
  } catch { /* 忽略 */ }
  engine = null
  wind = null
}

/** 每帧跟随车速：ratio 0~1，throttle 是否在给油 */
function setSpeed(ratio, throttle) {
  if (!engine || !ctx) return
  const r = Math.max(0, Math.min(1, ratio))
  const f = 52 + r * 196 + (throttle ? 14 : 0)
  try {
    const t = ctx.currentTime
    engine.o1.frequency.setTargetAtTime(f, t, 0.07)
    engine.o2.frequency.setTargetAtTime(f * 0.5, t, 0.07)
    engine.lp.frequency.setTargetAtTime(420 + r * 1500, t, 0.1)
    engine.g.gain.setTargetAtTime(0.035 + r * 0.065, t, 0.12)
    wind.wg.gain.setTargetAtTime(0.0001 + r * r * 0.085, t, 0.18)
  } catch { /* 忽略 */ }
}

function thump(freq, toFreq, dur, gain, delay = 0) {
  if (muted) return
  const a = ac()
  if (!a) return
  try {
    const t = a.currentTime + delay
    const osc = a.createOscillator()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(freq, t)
    osc.frequency.exponentialRampToValueAtTime(Math.max(28, toFreq), t + dur)
    const g = a.createGain()
    g.gain.setValueAtTime(0.0001, t)
    g.gain.linearRampToValueAtTime(gain, t + 0.012)
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur)
    osc.connect(g); g.connect(master)
    osc.start(t); osc.stop(t + dur + 0.05)
  } catch { /* 忽略 */ }
}

function burst(dur, fromHz, toHz, gain, delay = 0, type = 'lowpass') {
  if (muted) return
  const a = ac()
  if (!a) return
  try {
    const t = a.currentTime + delay
    const src = a.createBufferSource()
    src.buffer = noiseBuffer(a, dur)
    const f = a.createBiquadFilter()
    f.type = type
    f.frequency.setValueAtTime(fromHz, t)
    f.frequency.exponentialRampToValueAtTime(Math.max(80, toHz), t + dur)
    const g = a.createGain()
    g.gain.setValueAtTime(gain, t)
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur)
    src.connect(f); f.connect(g); g.connect(master)
    src.start(t)
  } catch { /* 忽略 */ }
}

export const rrSfx = {
  startEngine,
  stopEngine,
  setSpeed,
  /** 撞车 / 撞路障：低频闷响 + 金属噪声。s 0~1.5，越大越重 */
  impact(s = 1) {
    thump(130 * (0.85 + Math.random() * 0.3), 40, 0.26, 0.42 * s)
    burst(0.28, 2600, 380, 0.30 * s)
  },
  /** 挥击命中：短促「啪」+ 一点低频体感（打在头盔/皮衣上的闷） */
  hit(heavy = false) {
    burst(heavy ? 0.14 : 0.09, heavy ? 2200 : 3200, 700, heavy ? 0.26 : 0.18, 0, 'bandpass')
    thump(heavy ? 110 : 150, 60, 0.12, heavy ? 0.22 : 0.12)
  },
  /** 摔车：更长、更重的撞击 + 拖拽金属声 + 下坠音 */
  crash() {
    thump(150, 30, 0.5, 0.6)
    burst(0.6, 3400, 260, 0.4)
    burst(0.45, 900, 220, 0.22, 0.12, 'bandpass')
    const a = ac()
    if (!a || muted) return
    try {
      const t = a.currentTime
      const osc = a.createOscillator()
      osc.type = 'triangle'
      osc.frequency.setValueAtTime(320, t)
      osc.frequency.exponentialRampToValueAtTime(60, t + 0.7)
      const g = a.createGain()
      g.gain.setValueAtTime(0.10, t)
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.75)
      osc.connect(g); g.connect(master)
      osc.start(t); osc.stop(t + 0.8)
    } catch { /* 忽略 */ }
  },
}

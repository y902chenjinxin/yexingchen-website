/** 棋牌三件套 · 操作音效（v2.46.41 真实采样扩容）。
 *
 * v2.46.40（夜星「出牌声音还是很机械」）：接入真实录音采样，合成音降级为兜底——
 * 出牌/发牌 = Kenney Casino Audio（CC0）；麻将拍桌 = autotable 的 CC0 录音。
 * v2.46.41 继续扩容：不要=推牌、碰=木牌轻敲两连、杠=木牌中敲三连（Kenney Impact
 * CC0）、掷骰=骰子掷出 7 变体、结算=收牌洗牌声；新增 sfx.preload() 进桌预热，
 * 消掉第一次出牌的取包延迟。
 * - 全部采样沿用 ±随机变调（playbackRate）与立体声声像；OGG 桌面/鸿蒙
 *   Chromium 全支持，iOS Safari 解不了 OGG 自动回落合成音，不影响功能。
 * - 无背景音乐（PRD 硬要求），只有操作音。一键静音存 localStorage 跨局记忆。
 * - 浏览器未授权 / 不支持 WebAudio 时全部静默降级。
 */
import { vibrate } from './haptics'

const KEY = 'xuanhuang_game_muted'

/** 真实采样清单（v2.46.41 扩容）：数组 = 可随机轮换的变体（防复读机）。
 *  首用懒加载并缓存 AudioBuffer；进牌桌时 sfx.preload() 预热全部。 */
const S = '/sounds/cards/'
const SAMPLES = {
  cardPlace: [1, 2, 3, 4].map(i => `${S}card-place-${i}.ogg`),
  cardSlide: [1, 2, 3, 4].map(i => `${S}card-slide-${i}.ogg`),
  cardShove: [1, 2, 3, 4].map(i => `${S}card-shove-${i}.ogg`),
  diceThrow: [`${S}dice-throw-1.ogg`, `${S}dice-throw-2.ogg`, `${S}dice-throw-3.ogg`,
    `${S}die-throw-1.ogg`, `${S}die-throw-2.ogg`, `${S}die-throw-3.ogg`, `${S}die-throw-4.ogg`],
  woodLight: [`${S}wood-light-0.ogg`, `${S}wood-light-1.ogg`, `${S}wood-light-2.ogg`],
  woodMedium: [`${S}wood-med-0.ogg`, `${S}wood-med-1.ogg`],
  shuffle: [`${S}card-shuffle.ogg`],
  tileDown: [`${S}tile-discard.wav`],
}

let ctx = null
let muted = false
try { muted = localStorage.getItem(KEY) === '1' } catch { /* 隐私模式忽略 */ }

function ac() {
  if (ctx) return ctx
  try {
    const AC = window.AudioContext || window.webkitAudioContext
    ctx = AC ? new AC() : null
  } catch { ctx = null }
  return ctx
}

/** 采样缓存：url → AudioBuffer | null（null=加载失败，不再重试） */
const bufCache = new Map()

function loadSample(url) {
  if (bufCache.has(url)) return bufCache.get(url)
  const p = ac()?.decodeAudioData
    ? fetch(url).then(r => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(r.status))))
      .then(ab => new Promise((res, rej) => {
        // decodeAudioData 回调式与 Promise 式兼容差异 → 包一层
        ctx.decodeAudioData(ab, res, rej)
      }))
      .catch(() => null)
    : Promise.resolve(null)
  bufCache.set(url, p)
  return p
}

/** 座位号 → 声像值：相对视角座位 1（右家）偏右 0.5、3（左家）偏左 -0.5、其余居中 */
export function panOf(seat, povSeat) {
  const rel = ((Number(seat) - Number(povSeat)) % 4 + 4) % 4
  return rel === 1 ? 0.5 : rel === 3 ? -0.5 : 0
}

function blip(freq, dur = 0.08, type = 'sine', gain = 0.05, delay = 0, pan = 0) {
  if (muted) return
  const a = ac()
  if (!a) return
  try {
    if (a.state === 'suspended') a.resume()
    // ±3% 随机变调：防「完全相同的音连播 N 次」的复读机感
    const f = freq * (1 + (Math.random() * 0.06 - 0.03))
    const t0 = a.currentTime + delay
    const osc = a.createOscillator()
    const g = a.createGain()
    osc.type = type
    osc.frequency.setValueAtTime(f, t0)
    g.gain.setValueAtTime(0, t0)
    g.gain.linearRampToValueAtTime(gain, t0 + 0.012)
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
    osc.connect(g)
    // StereoPanner 兼容性兜底：不支持就直连（无声像，不影响功能）
    let tail = g
    if (a.createStereoPanner) {
      const p = a.createStereoPanner()
      p.pan.value = Math.max(-1, Math.min(1, pan))
      g.connect(p)
      tail = p
    }
    tail.connect(a.destination)
    osc.start(t0); osc.stop(t0 + dur + 0.02)
  } catch { /* 静默 */ }
}

function chord(freqs, dur = 0.16, gain = 0.045, pan = 0) {
  freqs.forEach((f, i) => blip(f, dur, 'triangle', gain, i * 0.07, pan))
}

/** 带通噪声短击（v2.46.26）：真实「啪」声是宽带噪声冲击，振荡器做不出来。
 *  白噪声 buffer 指数衰减包络 + bandpass 滤波，freq≈3000 是骨牌拍面的高频击点。 */
function noiseBurst(pan = 0, delay = 0, dur = 0.05, freq = 3000, q = 1.2, gain = 0.09) {
  if (muted) return
  const a = ac()
  if (!a) return
  try {
    if (a.state === 'suspended') a.resume()
    const t0 = a.currentTime + delay
    const len = Math.max(64, Math.floor(a.sampleRate * dur))
    const buf = a.createBuffer(1, len, a.sampleRate)
    const d = buf.getChannelData(0)
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len)
    const src = a.createBufferSource()
    src.buffer = buf
    const bp = a.createBiquadFilter()
    bp.type = 'bandpass'
    // ±5% 随机中心频率：每张牌落桌听感略不同（与 blip 的 ±3% 同思路）
    bp.frequency.value = freq * (1 + (Math.random() * 0.1 - 0.05))
    bp.Q.value = q
    const g = a.createGain()
    g.gain.value = gain
    src.connect(bp); bp.connect(g)
    let tail = g
    if (a.createStereoPanner) {
      const p = a.createStereoPanner()
      p.pan.value = Math.max(-1, Math.min(1, pan))
      g.connect(p)
      tail = p
    }
    tail.connect(a.destination)
    src.start(t0)
  } catch { /* 静默 */ }
}

/** 真实采样播放（v2.46.40）：urls 里随机挑一个变体，±rateJitter 变调 + 声像。
 *  采样未就绪时先播 fallback()（合成音）顶上，同时后台加载，下一发就是真声。 */
function playSample(urls, pan, { gain = 0.6, rateJitter = 0.06, delay = 0, fallback } = {}) {
  if (muted) return
  const a = ac()
  if (!a) return
  const url = urls[Math.floor(Math.random() * urls.length)]
  const bufP = loadSample(url)
  const startBuf = buf => {
    if (!buf) return
    try {
      if (a.state === 'suspended') a.resume()
      const t0 = a.currentTime + delay
      const src = a.createBufferSource()
      src.buffer = buf
      src.playbackRate.value = 1 + (Math.random() * 2 - 1) * rateJitter
      const g = a.createGain()
      g.gain.value = gain
      src.connect(g)
      let tail = g
      if (a.createStereoPanner) {
        const p = a.createStereoPanner()
        p.pan.value = Math.max(-1, Math.min(1, pan))
        g.connect(p)
        tail = p
      }
      tail.connect(a.destination)
      src.start(t0)
    } catch { /* 静默 */ }
  }
  Promise.resolve(bufP).then(buf => {
    if (buf) startBuf(buf)
    else if (fallback) fallback() // 未就绪 / 加载失败：合成音顶一次，加载成功后下次是真声
  })
}

export function setMuted(v) {  muted = !!v
  try { localStorage.setItem(KEY, muted ? '1' : '0') } catch { /* 忽略 */ }
}
export function isMuted() { return muted }

export const sfx = {
  /** 预热全部采样（v2.46.41）：牌桌 onMounted 时调用，消掉第一次出牌的取包延迟 */
  preload() {
    if (muted || !ac()) return
    Object.values(SAMPLES).flat().forEach(u => loadSample(u))
  },
  /** 发牌（v2.46.40 真实采样）：card-slide 每张随机变体、错开 60ms 连播 4 张 */
  deal(pan = 0) {
    const synthDeal = () => { for (let i = 0; i < 5; i++) blip(880 - i * 60, 0.05, 'square', 0.03, i * 0.05, pan) }
    for (let i = 0; i < 4; i++) {
      playSample(SAMPLES.cardSlide, pan, { gain: 0.38, delay: i * 0.06, fallback: i === 0 ? synthDeal : undefined })
    }
  },
  /** 出牌（v2.46.40 真实采样）：card-place 随机 4 变体之一（+ 轻触感 10ms） */
  play(pan = 0) {
    playSample(SAMPLES.cardPlace, pan, {
      gain: 0.55,
      fallback: () => { blip(520, 0.07, 'triangle', 0.055, 0, pan); blip(760, 0.06, 'sine', 0.03, 0.04, pan) },
    })
    vibrate(10)
  },
  /** 麻将牌拍在桌上（v2.46.40 真实采样：autotable 的骨牌落桌录音，CC0）：
   *  ±6% 变调，拍面瞬态是真实录音；采样未就绪时回落 v2.46.26 三层合成。 */
  tileDown(pan = 0) {
    playSample(SAMPLES.tileDown, pan, {
      gain: 0.8,
      fallback: () => {
        noiseBurst(pan, 0, 0.045, 3400, 1.1, 0.11)
        blip(160 + Math.random() * 40, 0.09, 'sine', 0.12, 0, pan)
        blip(760, 0.045, 'triangle', 0.05, 0.005, pan)
        noiseBurst(pan, 0.05, 0.03, 2200, 1.4, 0.05)
      },
    })
    vibrate(12)
  },
  /** 不要 / 过（v2.46.41 真实采样）：推牌声 card-shove */
  pass(pan = 0) {
    playSample(SAMPLES.cardShove, pan, { gain: 0.45, fallback: () => blip(300, 0.09, 'sine', 0.035, 0, pan) })
  },
  /** 选牌轻响（不带触感：划选时会连响，震动了会烦） */
  pick(pan = 0) { blip(680, 0.035, 'sine', 0.03, 0, pan) },
  /** 报牌提醒（剩牌 ≤ 阈值时一声双音上扬） */
  alert(pan = 0) { blip(660, 0.09, 'triangle', 0.05, 0, pan); blip(990, 0.12, 'triangle', 0.05, 0.1, pan); vibrate(12) },
  /** 碰（v2.46.41 真实采样）：木牌轻敲两连（Kenney Impact，CC0） */
  pong(pan = 0) {
    const synthPong = () => { blip(420, 0.07, 'square', 0.05, 0, pan); blip(560, 0.07, 'square', 0.045, 0.06, pan) }
    playSample(SAMPLES.woodLight, pan, { gain: 0.6, fallback: synthPong })
    playSample(SAMPLES.woodLight, pan, { gain: 0.45, delay: 0.09 })
    vibrate(15)
  },
  /** 杠（v2.46.41 真实采样）：木牌中敲三连 */
  kong(pan = 0) {
    const synthKong = () => chord([380, 500, 660], 0.14, 0.05, pan)
    for (let i = 0; i < 3; i++) {
      playSample(SAMPLES.woodMedium, pan, { gain: i === 2 ? 0.6 : 0.5, delay: i * 0.09, fallback: i === 0 ? synthKong : undefined })
    }
    vibrate([10, 30, 10])
  },
  /** 胡牌 / 胜利 */
  win(pan = 0) { chord([523, 659, 784, 1046], 0.18, 0.055, pan); vibrate([20, 40, 20]) },
  /** 失败 / 被胡 */
  lose(pan = 0) { chord([440, 370, 294], 0.2, 0.045, pan) },
  /** 掷骰（v2.46.41 真实采样）：骰子掷出声，7 变体轮换 */
  dice(pan = 0) {
    playSample(SAMPLES.diceThrow, pan, {
      gain: 0.55,
      fallback: () => { for (let i = 0; i < 6; i++) blip(300 + Math.random() * 500, 0.035, 'square', 0.028, i * 0.045, pan) },
    })
  },
  /** 结算弹层出现（v2.46.41）：收牌洗牌声打底 */
  settle(pan = 0) {
    playSample(SAMPLES.shuffle, pan, { gain: 0.3, fallback: () => chord([392, 523, 659], 0.2, 0.05, pan) })
  },

  /* ===== v2.46.20 棋类音色（此前象棋/围棋/五子棋/军棋/飞行棋全程无声） ===== */
  /** 木质落子（象棋 / 军棋走子）：低频短促的「嗒」 */
  wood(pan = 0) { blip(190, 0.06, 'triangle', 0.09, 0, pan); blip(120, 0.09, 'sine', 0.055, 0.012, pan); vibrate(10) },
  /** 石子落盘（围棋 / 五子棋）：清脆一点 */
  stone(pan = 0) { blip(1150, 0.045, 'sine', 0.07, 0, pan); blip(560, 0.05, 'triangle', 0.035, 0.018, pan); vibrate(8) },
  /** 翻牌（暗棋 / 军棋翻棋 / 道具卡） */
  flip(pan = 0) { blip(620, 0.04, 'square', 0.03, 0, pan); blip(880, 0.05, 'triangle', 0.032, 0.045, pan); vibrate(8) },
  /** 吃子碰撞（重一点） */
  capture(pan = 0) { blip(300, 0.07, 'square', 0.06, 0, pan); blip(210, 0.1, 'triangle', 0.05, 0.05, pan); vibrate([8, 20, 8]) },
  /** 将军警示：同音急促两连 */
  check(pan = 0) { blip(740, 0.09, 'square', 0.05, 0, pan); blip(740, 0.12, 'square', 0.05, 0.14, pan); vibrate(12) },
  /** 终局重音（将死 / 拔旗 / 吃将）：下行三音 */
  mate(pan = 0) { chord([330, 262, 196], 0.24, 0.055, pan); vibrate([20, 40, 20]) },
  /** 收钱（上扬双音） */
  coin(pan = 0) { blip(920, 0.06, 'triangle', 0.045, 0, pan); blip(1240, 0.09, 'triangle', 0.045, 0.06, pan) },
  /** 付钱（下行双音） */
  coinPay(pan = 0) { blip(660, 0.06, 'triangle', 0.04, 0, pan); blip(470, 0.09, 'triangle', 0.04, 0.06, pan) },
  /** 飞行棋逐格跳：n 连轻音、音高递增（连跳比一次性滑过去爽） */
  steps(n = 1, pan = 0) {
    for (let i = 0; i < Math.min(n, 12); i++) blip(480 + i * 42, 0.045, 'square', 0.028, i * 0.07, pan)
    vibrate(8)
  },
}

export default sfx

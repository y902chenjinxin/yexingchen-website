/** 棋牌三件套 · 操作音效（v2.43）。
 *
 * 纯 WebAudio 合成，不加载任何音频文件：
 * - 无背景音乐（PRD 硬要求），只有发牌 / 出牌 / 不要 / 碰杠胡 / 掷骰 / 胜负这些操作音。
 * - 一键静音，静音状态存 localStorage，跨局记忆。
 * - 浏览器未授权 / 不支持 WebAudio 时全部静默降级，不影响玩法。
 */
const KEY = 'xuanhuang_game_muted'

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

function blip(freq, dur = 0.08, type = 'sine', gain = 0.05, delay = 0) {
  if (muted) return
  const a = ac()
  if (!a) return
  try {
    if (a.state === 'suspended') a.resume()
    const t0 = a.currentTime + delay
    const osc = a.createOscillator()
    const g = a.createGain()
    osc.type = type
    osc.frequency.setValueAtTime(freq, t0)
    g.gain.setValueAtTime(0, t0)
    g.gain.linearRampToValueAtTime(gain, t0 + 0.012)
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
    osc.connect(g); g.connect(a.destination)
    osc.start(t0); osc.stop(t0 + dur + 0.02)
  } catch { /* 静默 */ }
}

function chord(freqs, dur = 0.16, gain = 0.045) {
  freqs.forEach((f, i) => blip(f, dur, 'triangle', gain, i * 0.07))
}

export function setMuted(v) {
  muted = !!v
  try { localStorage.setItem(KEY, muted ? '1' : '0') } catch { /* 忽略 */ }
}
export function isMuted() { return muted }

export const sfx = {
  /** 发牌：一串短促下滑音 */
  deal() { for (let i = 0; i < 5; i++) blip(880 - i * 60, 0.05, 'square', 0.03, i * 0.05) },
  /** 出牌：干脆的一击 */
  play() { blip(520, 0.07, 'triangle', 0.055); blip(760, 0.06, 'sine', 0.03, 0.04) },
  /** 不要 / 过 */
  pass() { blip(300, 0.09, 'sine', 0.035) },
  /** 选牌轻响 */
  pick() { blip(680, 0.035, 'sine', 0.03) },
  /** 碰 */
  pong() { blip(420, 0.07, 'square', 0.05); blip(560, 0.07, 'square', 0.045, 0.06) },
  /** 杠 */
  kong() { chord([380, 500, 660], 0.14, 0.05) },
  /** 胡牌 / 胜利 */
  win() { chord([523, 659, 784, 1046], 0.18, 0.055) },
  /** 失败 / 被胡 */
  lose() { chord([440, 370, 294], 0.2, 0.045) },
  /** 掷骰 */
  dice() { for (let i = 0; i < 6; i++) blip(300 + Math.random() * 500, 0.035, 'square', 0.028, i * 0.045) },
  /** 结算弹层出现 */
  settle() { chord([392, 523, 659], 0.2, 0.05) },
}

export default sfx

/** 棋牌三件套 · 操作音效（v2.46.19 升级）。
 *
 * 纯 WebAudio 合成，不加载任何音频文件：
 * - 无背景音乐（PRD 硬要求），只有发牌 / 出牌 / 不要 / 碰杠胡 / 掷骰 / 胜负这些操作音。
 * - v2.46.19：每次发声加 ±3% 随机变调 —— 固定频率连听几局会产生「复读机疲劳」，
 *   微小的随机让同一音效每次都略有不同（参考成熟棋牌的 layering 做法）。
 * - v2.46.19：支持立体声声像（StereoPannerNode）—— 出牌方在屏幕左边时声音偏左、
 *   右边偏右，用听觉辅助确认「是谁出的牌」。panOf() 把座位号换算成 -0.5~0.5 的声像值。
 * - 一键静音，静音状态存 localStorage，跨局记忆。
 * - 浏览器未授权 / 不支持 WebAudio 时全部静默降级，不影响玩法。
 */
import { vibrate } from './haptics'

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

export function setMuted(v) {
  muted = !!v
  try { localStorage.setItem(KEY, muted ? '1' : '0') } catch { /* 忽略 */ }
}
export function isMuted() { return muted }

export const sfx = {
  /** 发牌：一串短促下滑音 */
  deal(pan = 0) { for (let i = 0; i < 5; i++) blip(880 - i * 60, 0.05, 'square', 0.03, i * 0.05, pan) },
  /** 出牌：干脆的一击（+ 轻触感 10ms） */
  play(pan = 0) { blip(520, 0.07, 'triangle', 0.055, 0, pan); blip(760, 0.06, 'sine', 0.03, 0.04, pan); vibrate(10) },
  /** 不要 / 过 */
  pass(pan = 0) { blip(300, 0.09, 'sine', 0.035, 0, pan) },
  /** 选牌轻响（不带触感：划选时会连响，震动了会烦） */
  pick(pan = 0) { blip(680, 0.035, 'sine', 0.03, 0, pan) },
  /** 报牌提醒（剩牌 ≤ 阈值时一声双音上扬） */
  alert(pan = 0) { blip(660, 0.09, 'triangle', 0.05, 0, pan); blip(990, 0.12, 'triangle', 0.05, 0.1, pan); vibrate(12) },
  /** 碰 */
  pong(pan = 0) { blip(420, 0.07, 'square', 0.05, 0, pan); blip(560, 0.07, 'square', 0.045, 0.06, pan); vibrate(15) },
  /** 杠 */
  kong(pan = 0) { chord([380, 500, 660], 0.14, 0.05, pan); vibrate([10, 30, 10]) },
  /** 胡牌 / 胜利 */
  win(pan = 0) { chord([523, 659, 784, 1046], 0.18, 0.055, pan); vibrate([20, 40, 20]) },
  /** 失败 / 被胡 */
  lose(pan = 0) { chord([440, 370, 294], 0.2, 0.045, pan) },
  /** 掷骰 */
  dice(pan = 0) { for (let i = 0; i < 6; i++) blip(300 + Math.random() * 500, 0.035, 'square', 0.028, i * 0.045, pan) },
  /** 结算弹层出现 */
  settle(pan = 0) { chord([392, 523, 659], 0.2, 0.05, pan) },

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

/** 棋牌 · 触感反馈（v2.46.19）。
 *
 * navigator.vibrate 的克制封装：
 * - 默认开启，一键开关存 localStorage 跨局记忆；
 * - 不支持 vibrate 的环境（iOS Safari / 部分桌面浏览器）静默降级为空操作；
 * - 只在关键动作上给短震（出牌 / 碰杠胡 / 炸弹），高频的选牌不震 ——
 *   滥用触感是「gimmicky」的，参考主流棋牌只做重音。
 * - prefers-reduced-motion 用户大概率也不想要震动：默认关掉一次。
 */
const KEY = 'xuanhuang_game_haptics'

let enabled = true
try {
  const saved = localStorage.getItem(KEY)
  if (saved !== null) enabled = saved === '1'
  else if (typeof window !== 'undefined' && window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches) enabled = false
} catch { /* 隐私模式忽略 */ }

export function hapticsEnabled() { return enabled }

export function setHaptics(v) {
  enabled = !!v
  try { localStorage.setItem(KEY, enabled ? '1' : '0') } catch { /* 忽略 */ }
}

/** pattern：毫秒数或 [震,停,震…] 数组；不支持 / 未开启时静默 */
export function vibrate(pattern) {
  if (!enabled) return
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      navigator.vibrate(pattern)
    }
  } catch { /* 静默 */ }
}

export default { vibrate, hapticsEnabled, setHaptics }

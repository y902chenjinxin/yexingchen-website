/**
 * 设备判定（v2.46.347）
 *
 * ⚠️ **不要用 `useIsMobile()` 来判"这是不是手机"**。
 * 那个 composable 的语义是「是否启用移动端外壳」，v2.40.30 起只认自家 APK 的 UA
 * （`XuanHuangApp`）或 `?m=1` —— 手机浏览器打开时它返回 **false**（走桌面版布局）。
 *
 * 而「这个功能只能在手机上玩」需要的是「我是不是正站在一台手机上」。
 * 两者结论经常相反，混用会让手机浏览器被误判成电脑。
 */

const APK_UA = /XuanHuangApp/i
const MOBILE_UA = /Android|iPhone|iPod|Mobile|HarmonyOS|OpenHarmony|HuaweiBrowser|MiuiBrowser|MicroMessenger/i

function ua() {
  return (typeof navigator !== 'undefined' && navigator.userAgent) || ''
}

/**
 * 是不是手机。
 *
 * 判定口径（按可靠性排序）：
 *   1. 自家 APK 的 UA —— 一定算
 *   2. **触屏** + **屏幕窄**（短边 < 900）+ UA 里有移动标识
 *
 * 为什么不只看 UA：鸿蒙/部分国产浏览器的 UA 会伪装成桌面 Chrome。
 * 为什么不只看屏宽：桌面浏览器把窗口拉窄也会窄。
 * 三个条件同时成立才认，误判两侧都很难。
 *
 * iPad / 平板（短边 ≥ 900）按电脑处理 —— 这些设备本来就能跑桌面版布局。
 */
export function isPhoneDevice() {
  if (typeof window === 'undefined') return false
  const u = ua()
  if (APK_UA.test(u)) return true

  const touch = (navigator.maxTouchPoints || 0) > 0
  if (!touch) return false
  if (!MOBILE_UA.test(u)) return false

  const w = (typeof screen !== 'undefined' && screen.width) || window.innerWidth || 0
  const h = (typeof screen !== 'undefined' && screen.height) || window.innerHeight || 0
  return Math.min(w, h) < 900
}

/** 反过来的问法，读代码时更顺 */
export function isDesktopDevice() {
  return !isPhoneDevice()
}

/** 一段给人看的原因（写进提示里，别让人猜） */
export function deviceHint() {
  return isPhoneDevice() ? '手机' : '电脑'
}

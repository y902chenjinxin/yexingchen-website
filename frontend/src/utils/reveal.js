/**
 * 主题切换圆形揭示（APP_design.md #10 · v2.46.33）
 *
 * 从点击坐标以 clip-path circle 扩散揭示新主题；View Transitions API
 * 不可用（旧 WebView / Firefox）时直接切换，无感降级。
 * 配套 CSS 在 mobile-paper.css `::view-transition-new(root)`。
 *
 * 用法：onClick 中 revealTheme(() => prefs.setTheme('day'), e)
 */
export function revealTheme(applyFn, event) {
  try {
    const root = document.documentElement
    if (event && document.startViewTransition) {
      const x = event.clientX ?? window.innerWidth / 2
      const y = event.clientY ?? window.innerHeight / 2
      root.style.setProperty('--reveal-x', `${x}px`)
      root.style.setProperty('--reveal-y', `${y}px`)
      document.startViewTransition(() => {
        applyFn()
        return new Promise((r) => requestAnimationFrame(() => r()))
      })
      return
    }
  } catch { /* 降级直切 */ }
  applyFn()
}

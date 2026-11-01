/**
 * 主题切换（v2.46.313 重写：去掉 View Transitions）
 *
 * 原来用 `document.startViewTransition` 做「从点击坐标圆形揭示新主题」。
 * 实测（1280×820，现网真实页面）：
 *   · 走 View Transitions：`data-theme` 生效要 **4109ms**
 *   · 直接改属性：属性 0ms、首帧 33~38ms、最长任务 84ms
 * 差的 4 秒全在「整页截两张快照再合成动画」——本站满屏 backdrop-filter、
 * 大面积渐变与阴影，光快照就要好几秒（真机 WebView 同病）。夜星反馈的
 * 「切白天黑夜要等 3-5 秒」就是它。
 *
 * 现在改成：同步直切 + 根三层（html/body/#app）220ms 背景色过渡。
 * 观感不突兀，总耗时 <300ms；配套 CSS 见 main.css `.theme-flip`。
 */

let flipTimer = 0

export function revealTheme(applyFn) {
  const root = document.documentElement
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  /* 先挂过渡类，再切属性 —— 顺序反过来的话颜色已经变完了，过渡不会触发 */
  if (!reduce) {
    root.classList.add('theme-flip')
    clearTimeout(flipTimer)
    flipTimer = setTimeout(() => root.classList.remove('theme-flip'), 300)
  }
  applyFn()
}

/* 兼容旧调用点：revealTheme(fn, event) 的第二个参数已不再使用（没有揭示动画了） */

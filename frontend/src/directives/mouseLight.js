/**
 * mouseLight · 自定义 Vue 指令
 *
 * 给任意 DOM 元素加上 v-mouse-light 后，hover 时获得：
 *  1. 3D 微倾斜（perspective + rotate3d，跟随鼠标）
 *  2. 鎏金聚光（CSS 变量 --ml-x / --ml-y 驱动 radial-gradient）
 *  3. 鼠标离开后平滑复位（CSS transition）
 *  4. prefers-reduced-motion 完全跳过倾斜与聚光
 *
 * 使用：
 *   <div v-mouse-light>...</div>
 *   <div v-mouse-light="{ tilt: 8, spot: true, lift: true }">...</div>
 *
 * 参数：
 *   tilt - 倾斜角度上限（度），默认 6
 *   spot - 是否启用聚光，默认 true
 *   lift - 是否同时上浮 translateY(-2px)，默认 true
 *
 * CSS 配合（在 .xxx:hover 中使用）：
 *   background: radial-gradient(
 *     220px circle at var(--ml-x, 50%) var(--ml-y, 50%),
 *     var(--yq-gold-faint, rgba(199,169,107,.18)),
 *     transparent 60%
 *   );
 */
let _seq = 0

function bind(el, binding) {
  if (el.__mouseLightBound) return
  el.__mouseLightBound = true
  el.__mouseLightId = ++_seq

  const opts = Object.assign({ tilt: 6, spot: true, lift: true }, binding.value || {})
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

  // 初始 CSS 变量与 transition
  el.style.setProperty('--ml-x', '50%')
  el.style.setProperty('--ml-y', '50%')
  el.style.setProperty('--ml-tilt', '0deg')
  el.style.setProperty('--ml-shadow', '0 0 0 rgba(0,0,0,0)')
  el.style.transition = 'transform .22s cubic-bezier(.2,.7,.2,1), box-shadow .22s ease, --ml-tilt .22s ease'
  // 标记元素，便于全局 CSS 选择器定位（不必每次 :hover 再注入 ::before）
  el.dataset.mouseLight = ''
  // 保存原始 overflow，必要时临时设 hidden 让 ::before 聚光不溢出
  if (!el.style.overflow || el.style.overflow === 'visible') {
    el.__mouseLightOrigOverflow = el.style.overflow
    el.style.overflow = 'hidden'
  }

  // perspective 需要父容器；el 自身加 transform-style: preserve-3d 让子元素也能享受 3D
  if (!reduced) {
    el.style.transformStyle = 'preserve-3d'
    el.style.willChange = 'transform'
  }

  let raf = 0

  function onEnter() {
    if (reduced) return
    if (opts.lift) {
      el.style.setProperty('box-shadow', '0 18px 44px rgba(0,0,0,.28), 0 4px 10px rgba(0,0,0,.16)', 'important')
    }
  }

  function onMove(e) {
    if (reduced) return
    const rect = el.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width  // 0~1
    const y = (e.clientY - rect.top) / rect.height
    const rx = (0.5 - y) * opts.tilt       // 上半部→上仰
    const ry = (x - 0.5) * opts.tilt       // 右半部→右倾
    cancelAnimationFrame(raf)
    raf = requestAnimationFrame(() => {
      el.style.setProperty('--ml-x', (x * 100).toFixed(2) + '%')
      el.style.setProperty('--ml-y', (y * 100).toFixed(2) + '%')
      el.style.setProperty('--ml-tilt', `${rx.toFixed(2)}deg, ${ry.toFixed(2)}deg`)
      el.style.setProperty(
        'transform',
        `perspective(900px) rotate3d(1, 0, 0, ${rx.toFixed(2)}deg) rotate3d(0, 1, 0, ${ry.toFixed(2)}deg) translateY(${opts.lift ? '-2px' : '0'})`,
        'important'
      )
    })
  }

  function onLeave() {
    cancelAnimationFrame(raf)
    el.style.setProperty('--ml-x', '50%')
    el.style.setProperty('--ml-y', '50%')
    el.style.setProperty('--ml-tilt', '0deg')
    el.style.removeProperty('transform')
    el.style.removeProperty('box-shadow')
  }

  el.addEventListener('mouseenter', onEnter)
  el.addEventListener('mousemove', onMove)
  el.addEventListener('mouseleave', onLeave)
  el.addEventListener('blur', onLeave)

  el.__mouseLightCleanup = () => {
    cancelAnimationFrame(raf)
    el.removeEventListener('mouseenter', onEnter)
    el.removeEventListener('mousemove', onMove)
    el.removeEventListener('mouseleave', onLeave)
    el.removeEventListener('blur', onLeave)
    // 恢复原始 overflow
    if (el.__mouseLightOrigOverflow !== undefined) {
      el.style.overflow = el.__mouseLightOrigOverflow
      delete el.__mouseLightOrigOverflow
    } else {
      el.style.removeProperty('overflow')
    }
    delete el.dataset.mouseLight
    delete el.__mouseLightBound
    delete el.__mouseLightId
    delete el.__mouseLightCleanup
  }
}

function unbind(el) {
  el.__mouseLightCleanup?.()
}

export default {
  name: 'mouseLight',
  mounted(el, binding) { bind(el, binding) },
  updated(el, binding) { /* 允许动态修改参数：先解绑再绑 */ if (el.__mouseLightBound) unbind(el); bind(el, binding) },
  beforeUnmount(el) { unbind(el) },
}

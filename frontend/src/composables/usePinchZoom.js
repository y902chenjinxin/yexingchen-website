/**
 * usePinchZoom —— 牌桌「铺满一屏 + 双指缩放 / 单指拖动」。
 *
 * 只在 `active()` 为真时接管手势（全屏模式）；未激活时返回空样式，布局与改造前完全一致。
 *
 * 基准是「自适应比例 fit」：把牌桌外壳（`.gt-shell`）等比缩放到刚好放进舞台。
 * 逻辑画布高度固定（`opts.height`，默认 720px），宽度按**舞台宽高比**实时算出
 * （`w = h * stageW / stageH`）—— 这样画布与舞台同比例，等比缩放后两轴都严丝合缝铺满，
 * 不会出现一侧留黑边。用户的双指缩放是在此基准上的相对倍数（zoom=1 即铺满一屏），单指拖动平移。
 *
 * 牌桌自身有交互的区域（手牌划选、记录滚动、按钮）通过 NO_PAN 选择器排除，不参与平移。
 */
import { ref, computed, nextTick } from 'vue'

const NO_PAN = [
  'button', 'a', 'input', 'textarea', 'select', '[data-no-pan]',
  '.gt-card', '.gt-tile', '.gd-hand', '.gd-history-list',
  '.mj-hand', '.mj-discards', '.mp-players',
].join(',')

export function usePinchZoom(stageRef, active, opts = {}) {
  const minZoom = opts.minZoom ?? 0.5
  const maxZoom = opts.maxZoom ?? 4
  const logicalH = opts.height ?? 720

  const scale = ref(1)      // 当前绝对缩放（已含 fit）
  const tx = ref(0)
  const ty = ref(0)
  const ready = ref(false)
  const canvasW = ref(1280)   // 逻辑画布宽度（按舞台宽高比算）

  let fit = 1
  let natW = 1
  let natH = 1

  function stageEl() { return stageRef.value }
  function shellEl() { return stageRef.value?.querySelector('.gt-shell') }

  function clampPan(x, y) {
    const stage = stageEl()
    if (!stage) return [x, y]
    const sw = stage.clientWidth
    const sh = stage.clientHeight
    const cw = natW * scale.value
    const ch = natH * scale.value
    const loX = Math.min(0, sw - cw)
    const hiX = Math.max(0, sw - cw)
    const loY = Math.min(0, sh - ch)
    const hiY = Math.max(0, sh - ch)
    return [Math.min(hiX, Math.max(loX, x)), Math.min(hiY, Math.max(loY, y))]
  }

  function center() {
    const stage = stageEl()
    if (!stage) return
    tx.value = (stage.clientWidth - natW * scale.value) / 2
    ty.value = (stage.clientHeight - natH * scale.value) / 2
  }

  function reset() {
    scale.value = fit
    center()
  }

  async function measure() {
    const stage = stageEl()
    const shell = shellEl()
    if (!stage || !shell) return
    const sw = stage.clientWidth || 1
    const sh = stage.clientHeight || 1
    // 画布宽度跟随舞台宽高比；变化 >1px 才写，避免 ResizeObserver 自激振荡
    const w = Math.max(360, Math.round(logicalH * (sw / sh)))
    if (Math.abs(w - canvasW.value) > 1) {
      canvasW.value = w
      await nextTick()
    }
    natW = shell.offsetWidth || canvasW.value
    natH = shell.offsetHeight || logicalH
    // 同比例下 sw/natW 与 sh/natH 相等，取较小者兜底浮点误差
    fit = Math.max(0.12, Math.min(3, Math.min(sw / natW, sh / natH)))
    ready.value = true
    reset()
  }

  /* ---------- 手势 ---------- */
  let mode = null            // 'pan' | 'pinch'
  let panStart = null        // 单指起点
  let panT0 = null           // 单指起始 translate
  let s0 = 1
  let d0 = 1
  let c0 = null              // 起始中点对应的内容坐标

  function dist(a, b) { return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY) }
  function mid(a, b) { return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 } }

  function onStart(e) {
    if (!active()) return
    if (e.touches.length === 2) {
      const [a, b] = e.touches
      mode = 'pinch'
      d0 = dist(a, b) || 1
      const m = mid(a, b)
      s0 = scale.value
      c0 = { x: (m.x - tx.value) / s0, y: (m.y - ty.value) / s0 }
    } else if (e.touches.length === 1) {
      const el = e.target
      if (el && el.closest && el.closest(NO_PAN)) { mode = null; return }
      mode = 'pan'
      panStart = { x: e.touches[0].clientX, y: e.touches[0].clientY }
      panT0 = { x: tx.value, y: ty.value }
    }
  }

  function onMove(e) {
    if (!active() || !mode) return
    if (mode === 'pinch' && e.touches.length === 2) {
      if (e.cancelable) e.preventDefault()
      const [a, b] = e.touches
      const d = dist(a, b) || 1
      const ns = Math.max(fit * minZoom, Math.min(fit * maxZoom, s0 * (d / d0)))
      const m = mid(a, b)
      scale.value = ns
      const [nx, ny] = clampPan(m.x - c0.x * ns, m.y - c0.y * ns)
      tx.value = nx
      ty.value = ny
    } else if (mode === 'pan' && e.touches.length === 1) {
      if (e.cancelable) e.preventDefault()
      const [nx, ny] = clampPan(
        panT0.x + (e.touches[0].clientX - panStart.x),
        panT0.y + (e.touches[0].clientY - panStart.y),
      )
      tx.value = nx
      ty.value = ny
    }
  }

  function onEnd(e) {
    if (e.touches.length === 0) {
      mode = null
      panStart = null
      panT0 = null
      c0 = null
    } else if (e.touches.length === 1) {
      // 双指松开一根 → 接续为单指拖动，避免手感断裂
      mode = 'pan'
      panStart = { x: e.touches[0].clientX, y: e.touches[0].clientY }
      panT0 = { x: tx.value, y: ty.value }
    }
  }

  function onWheel(e) {
    if (!active() || !(e.ctrlKey || e.metaKey)) return
    e.preventDefault()
    const stage = stageEl()
    if (!stage) return
    const ns = Math.max(fit * minZoom, Math.min(fit * maxZoom, scale.value * (e.deltaY > 0 ? 0.92 : 1.08)))
    const rect = stage.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const cx = (mx - tx.value) / scale.value
    const cy = (my - ty.value) / scale.value
    scale.value = ns
    const [nx, ny] = clampPan(mx - cx * ns, my - cy * ns)
    tx.value = nx
    ty.value = ny
  }

  function onDblClick() {
    if (!active()) return
    if (Math.abs(scale.value - fit) < 0.01) {
      scale.value = Math.min(fit * maxZoom, fit * 1.8)
      center()
    } else {
      reset()
    }
  }

  const style = computed(() => (active() && ready.value)
    ? {
      // 逻辑画布：宽按舞台宽高比算出、高固定 logicalH —— 与舞台同比例，
      // 等比缩放后两轴都铺满（fx=fy=1），不会一侧留黑边。
      width: `${canvasW.value}px`,
      height: `${logicalH}px`,
      transform: `translate(${tx.value}px, ${ty.value}px) scale(${scale.value})`,
    }
    : {})

  /** 绑定到舞台元素；返回解绑函数 */
  function bind(el) {
    if (!el) return () => {}
    el.addEventListener('touchstart', onStart, { passive: true })
    el.addEventListener('touchmove', onMove, { passive: false })
    el.addEventListener('touchend', onEnd)
    el.addEventListener('touchcancel', onEnd)
    el.addEventListener('wheel', onWheel, { passive: false })
    el.addEventListener('dblclick', onDblClick)
    return () => {
      el.removeEventListener('touchstart', onStart)
      el.removeEventListener('touchmove', onMove)
      el.removeEventListener('touchend', onEnd)
      el.removeEventListener('touchcancel', onEnd)
      el.removeEventListener('wheel', onWheel)
      el.removeEventListener('dblclick', onDblClick)
    }
  }

  return { style, scale, ready, measure, reset, bind, fit: () => fit }
}

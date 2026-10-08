/**
 * usePinchZoom —— 牌桌「铺满一屏 + 双指缩放 / 单指拖动」。
 *
 * 只在 `active()` 为真时接管手势（全屏模式）；未激活时返回空样式，布局与改造前完全一致。
 *
 * **缩放基准（v2.46 重做）**：以参考设计尺寸（默认 1280×720）为准，只放大不缩小。
 *   zoom = clamp(min(stageW/1280, stageH/720), 1, maxUpscale)
 *   canvas = stage / zoom
 *
 * 为什么这么改：旧版是「宽度随舞台宽高比、高度固定 720」再等比缩小铺满。手机横屏舞台
 * 只有约 780×390，zoom 被压到 0.54 —— 牌桌里的牌、字全部被砍半（掼蛋的牌只剩 33px 宽，
 * 摸不准也划不动）。现在手机上一律 **1:1 原生渲染**，牌桌按真实 CSS 像素布局，牌自然就大；
 * 只有舞台大于参考尺寸（桌面大屏）时才等比放大，最多 `maxUpscale` 倍，避免牌大得离谱。
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
  const refW = opts.refW ?? 1280      // 参考设计宽（桌面布局按这个宽度调好的）
  const refH = opts.refH ?? 720       // 参考设计高
  const maxUpscale = opts.maxUpscale ?? 1.75
  const minZoom = opts.minZoom ?? 1   // 相对基准的最小倍数：1 = 不许缩到比「铺满」更小
  const maxZoom = opts.maxZoom ?? 3

  const scale = ref(1)      // 当前绝对缩放（fit 即基准）
  const tx = ref(0)
  const ty = ref(0)
  const ready = ref(false)
  const canvasW = ref(refW)   // 逻辑画布宽 = 舞台宽 / 基准缩放
  const canvasH = ref(refH)

  let fit = 1
  let natW = refW
  let natH = refH

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
    if (!stage) return
    const sw = stage.clientWidth || 1
    const sh = stage.clientHeight || 1
    // 基准缩放：只放大不缩小（手机 1:1 原生；桌面大屏等比放大，上限 maxUpscale）
    const zoom = Math.max(1, Math.min(maxUpscale, Math.min(sw / refW, sh / refH)))
    const cw = Math.max(240, Math.round(sw / zoom))
    const ch = Math.max(180, Math.round(sh / zoom))
    if (Math.abs(cw - canvasW.value) > 1 || Math.abs(ch - canvasH.value) > 1) {
      canvasW.value = cw
      canvasH.value = ch
      await nextTick()
    }
    const shell = shellEl()
    // 牌桌是异步组件：外壳还没挂上就先不定 ready，让外层重试循环继续；
    // 此期间 style 走「100% / 不缩放」兜底，画面正确只是没做放大。
    if (!shell) return
    natW = shell.offsetWidth || canvasW.value
    natH = shell.offsetHeight || canvasH.value
    fit = Math.max(0.2, Math.min(sw / natW, sh / natH))
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

  const style = computed(() => {
    if (!active()) return {}
    // 未测量完成：先铺满舞台 1:1，保证任何时候都不会「只显示左上角」
    if (!ready.value) return { width: '100%', height: '100%', transform: 'none' }
    return {
      width: `${canvasW.value}px`,
      height: `${canvasH.value}px`,
      transform: `translate(${tx.value}px, ${ty.value}px) scale(${scale.value})`,
    }
  })

  /** 绑定到舞台元素；返回解绑函数 */
  function bind(el) {
    if (!el) return () => {}
    el.addEventListener('touchstart', onStart, { passive: true })
    el.addEventListener('touchmove', onMove, { passive: false })
    el.addEventListener('touchend', onEnd)
    el.addEventListener('touchcancel', onEnd)
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      el.removeEventListener('touchstart', onStart)
      el.removeEventListener('touchmove', onMove)
      el.removeEventListener('touchend', onEnd)
      el.removeEventListener('touchcancel', onEnd)
      el.removeEventListener('wheel', onWheel)
    }
  }

  return { style, scale, ready, measure, reset, bind, fit: () => fit }
}

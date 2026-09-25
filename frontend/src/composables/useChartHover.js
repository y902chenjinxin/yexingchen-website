import { computed, ref, unref } from 'vue'

/**
 * 图表悬浮读数：把指针位置吸附到最近的数据列。
 *
 * - columns：每列在 viewBox 内的 x 坐标，支持传数组、ref/computed，或返回数组的函数
 * - 用 getScreenCTM 反算 viewBox 坐标，因此 preserveAspectRatio 为 meet 时
 *   （画布比 viewBox 宽、左右留白）也能精确命中
 */
export function useChartHover({ svgRef, columns }) {
  const hoverIndex = ref(null)

  const cols = computed(() => {
    const v = typeof columns === 'function' ? columns() : unref(columns)
    return Array.isArray(v) ? v : []
  })

  const hoverX = computed(() =>
    hoverIndex.value == null ? 0 : (cols.value[hoverIndex.value] ?? 0))

  function pick(clientX) {
    const el = svgRef.value
    const list = cols.value
    if (!el || !list.length) return
    const ctm = typeof el.getScreenCTM === 'function' ? el.getScreenCTM() : null
    if (!ctm) return
    const pt = el.createSVGPoint()
    pt.x = clientX
    pt.y = 0
    const px = pt.matrixTransform(ctm.inverse()).x
    let best = 0
    let bestD = Infinity
    for (let i = 0; i < list.length; i++) {
      const d = Math.abs(list[i] - px)
      if (d < bestD) { bestD = d; best = i }
    }
    hoverIndex.value = best
  }

  function onMove(e) { pick(e.clientX) }
  function onLeave() { hoverIndex.value = null }
  function onTouchStart(e) { const t = e.touches && e.touches[0]; if (t) pick(t.clientX) }
  function onTouchMove(e) { const t = e.touches && e.touches[0]; if (t) pick(t.clientX) }
  function onTouchEnd() { hoverIndex.value = null }

  return { hoverIndex, hoverX, cols, onMove, onLeave, onTouchStart, onTouchMove, onTouchEnd }
}
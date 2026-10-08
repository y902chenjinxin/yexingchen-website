/**
 * useRootHeight —— 把牌桌外壳的**实际渲染高度**写进一个响应式值，供 CSS 变量
 * （`--gt-h`）使用，让牌面尺寸在手机横屏（约 390 高）与桌面大屏上自动取到合适的值。
 *
 * `cap` 不是可有可无的：桌面端牌桌高度是被内容撑开的，若不封顶就会出现
 * 「牌变大 → 内容变高 → 牌再变大」的正反馈。封顶后必然收敛。
 *
 * 用法：
 *   const { rootRef, rootH } = useRootHeight()
 *   <div ref="rootRef" :style="{ '--gt-h': rootH + 'px' }">
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'

export function useRootHeight(cap = 760) {
  const rootRef = ref(null)
  const rootH = ref(0)
  let ro = null

  function measure() {
    const el = rootRef.value
    if (!el) return
    const h = Math.min(el.clientHeight || 0, cap)
    if (h > 0 && Math.abs(h - rootH.value) > 2) rootH.value = h
  }

  onMounted(() => {
    measure()
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(measure)
      if (rootRef.value) ro.observe(rootRef.value)
    }
  })
  onBeforeUnmount(() => {
    ro?.disconnect()
    ro = null
  })

  return { rootRef, rootH, measure }
}

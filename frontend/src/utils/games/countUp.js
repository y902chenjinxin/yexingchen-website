/** 结算数字逐格上滚（v2.46.20）。
 *
 * Balatro 式的「合计 tick」：结算面板的关键数字不再直接甩出来，
 * 而是从 0（或上一局值）在 ~0.7s 内缓动滚到位 —— 数值没变，爽感翻倍。
 * 用法：const shown = countUp(() => result.value?.delta || 0)
 */
import { ref, watch, onBeforeUnmount } from 'vue'

export default function countUp(targetSource, ms = 700) {
  const shown = ref(0)
  let raf = null
  watch(targetSource, (t) => {
    const from = shown.value
    const t0 = performance.now()
    if (raf) cancelAnimationFrame(raf)
    const step = (now) => {
      const k = Math.min(1, (now - t0) / Math.max(1, ms))
      const eased = 1 - Math.pow(1 - k, 3)          // ease-out cubic：先快后慢
      shown.value = Math.round(from + (t - from) * eased)
      if (k < 1) raf = requestAnimationFrame(step)
      else raf = null
    }
    raf = requestAnimationFrame(step)
  }, { immediate: true })
  onBeforeUnmount(() => { if (raf) cancelAnimationFrame(raf) })
  return shown
}

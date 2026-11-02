/**
 * 横向吸附条带的「刻度」逻辑（v2.46.323）
 *
 * 为什么不用 IntersectionObserver：
 *  IO 只在「进入/离开阈值」时回调，滑动很快时会**漏掉中间项**（一次跨 3 张只回 1 次），
 *  而且阈值是相对视口的，容器在页面里偏移大时（safe-area / 顶部标题）会整体偏移，
 *  表现为「明明居中了却不触发」。滚动 + rAF 每帧算一次最近中心，是最稳的。
 *
 * 判定口径 = **卡片中心离容器中心最近的那个索引**（不是 scrollLeft / 卡宽）：
 *  条带两侧有 16px padding、末尾一张常常无法真正居中（撞到 maxScroll），
 *  用除法算会在这两处偏 1 格。
 */

import { onBeforeUnmount, onMounted, ref, unref } from 'vue'
import { tick } from '@/utils/haptic'

/**
 * 当前最靠近容器中线的子元素索引。
 * @returns {number} 没有子元素时返回 -1
 */
export function centeredIndex(el) {
  if (!el || !el.children || !el.children.length) return -1
  const box = el.getBoundingClientRect()
  const mid = box.left + box.width / 2
  const kids = el.children
  let best = -1
  let bestDist = Infinity
  for (let i = 0; i < kids.length; i++) {
    const r = kids[i].getBoundingClientRect()
    if (!r.width) continue
    const d = Math.abs(r.left + r.width / 2 - mid)
    if (d < bestDist) { bestDist = d; best = i }
  }
  return best
}

/**
 * 给一个横向吸附容器挂「跨格 → 哒一声」。
 *
 * @param {import('vue').Ref|(() => HTMLElement|null)} target 容器（ref 或 getter）
 * @param {object} opts
 * @param {(idx:number)=>void} [opts.onChange] 索引变化回调（用于联动 active 态）
 * @param {() => number} [opts.strength] 可选：按滚动速度给 0.35~1 的力度
 * @returns {{ activeIndex: import('vue').Ref<number>, sync: () => void }}
 */
export function useSnapTicks(target, opts = {}) {
  const activeIndex = ref(-1)
  let el = null
  let raf = 0
  let stopped = false

  function compute() {
    raf = 0
    if (!el || stopped) return
    const idx = centeredIndex(el)
    if (idx < 0 || idx === activeIndex.value) return
    const first = activeIndex.value < 0 // 首次落位不算「跨格」，别一进页面就响
    activeIndex.value = idx
    if (!first) tick(opts.strength ? opts.strength() : 1)
    opts.onChange?.(idx)
  }

  function onScroll() {
    if (raf || stopped) return
    raf = requestAnimationFrame(compute)
  }

  function bind() {
    // 幂等：v-for / v-if 里的容器可能在挂载后才出现，允许外部再调一次
    if (el) el.removeEventListener('scroll', onScroll)
    el = typeof target === 'function' ? target() : unref(target)
    if (!el) return false
    el.addEventListener('scroll', onScroll, { passive: true })
    compute()
    return true
  }

  onMounted(() => { bind() })

  onBeforeUnmount(() => {
    stopped = true
    el?.removeEventListener('scroll', onScroll)
    if (raf) cancelAnimationFrame(raf)
  })

  return { activeIndex, sync: compute, rebind: bind }
}

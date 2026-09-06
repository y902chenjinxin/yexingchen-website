<template>
  <div class="dc">
    <svg :viewBox="`0 0 ${size} ${size}`" class="dc-svg" role="img" aria-label="支出分类占比">
      <circle
        v-for="(seg, i) in segments"
        :key="i"
        cx="50%"
        cy="50%"
        :r="r"
        fill="none"
        :stroke="seg.color"
        :stroke-width="thickness"
        :stroke-dasharray="`${seg.len} ${C - seg.len}`"
        :stroke-dashoffset="seg.offset"
        transform="rotate(-90 50 50)"
        stroke-linecap="butt"
        class="dc-seg"
        :style="{ '--seg': i }"
      />
      <text x="50%" y="47%" text-anchor="middle" class="dc-total">{{ totalLabel }}</text>
      <text x="50%" y="59%" text-anchor="middle" class="dc-total-sub">{{ countLabel }}</text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{category, amount, color}]
})

const size = 190
const thickness = 24
const r = (size - thickness * 2 - 6) / 2
const C = 2 * Math.PI * r

const tot = computed(() => props.data.reduce((s, c) => s + (c.amount || 0), 0))
const segments = computed(() => {
  if (!tot.value) return []
  let off = 0
  return props.data.map((c) => {
    const len = tot.value ? ((c.amount || 0) / tot.value) * C : 0
    const seg = { color: c.color, len, offset: -off }
    off += len
    return seg
  })
})
const totalLabel = computed(() => Number(tot.value).toFixed(0))
const countLabel = computed(() => `${props.data.length} 类`)
</script>

<style scoped>
.dc { flex: none; width: 190px; height: 190px; }
.dc-svg { width: 100%; height: 100%; display: block; }
.dc-seg { opacity: 0; animation: dc-in .6s ease forwards; }
.dc-seg:nth-child(1) { animation-delay: .05s; }
.dc-seg:nth-child(2) { animation-delay: .10s; }
.dc-seg:nth-child(3) { animation-delay: .15s; }
.dc-seg:nth-child(4) { animation-delay: .20s; }
.dc-seg:nth-child(5) { animation-delay: .25s; }
.dc-seg:nth-child(6) { animation-delay: .30s; }
.dc-seg:nth-child(7) { animation-delay: .35s; }
.dc-seg:nth-child(8) { animation-delay: .40s; }
.dc-seg:nth-child(9) { animation-delay: .45s; }
@keyframes dc-in { from { opacity: 0; } to { opacity: 1; } }
.dc-total { font-size: 30px; font-weight: 700; fill: var(--lj-text); letter-spacing: .02em; }
.dc-total-sub { font-size: 12px; fill: var(--lj-text-3); }
@media (prefers-reduced-motion: reduce) { .dc-seg { opacity: 1; animation: none; } }
</style>
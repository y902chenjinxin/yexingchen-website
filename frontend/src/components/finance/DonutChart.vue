<template>
  <div class="dc">
    <svg :viewBox="`0 0 ${size} ${size}`" class="dc-svg" role="img" :aria-label="ariaLabel">
      <circle
        v-for="(seg, i) in segments"
        :key="i"
        cx="50%"
        cy="50%"
        :r="r"
        fill="none"
        :stroke="seg.color"
        :stroke-width="thickness"
        :stroke-dasharray="seg.frame"
        :transform="`rotate(${seg.angle} ${center} ${center})`"
        stroke-linecap="butt"
        class="dc-seg"
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
  unit: { type: String, default: '类' },     // 中心计数单位（账本=类 / 持仓=只）
  ariaLabel: { type: String, default: '分类占比环形图' },
})

const size = 190
const thickness = 24
const center = size / 2
const r = (size - thickness * 2 - 6) / 2
const C = 2 * Math.PI * r

const tot = computed(() => props.data.reduce((s, c) => s + (c.amount || 0), 0))
// 每段以「累计圆心角」旋转其独立起点绘制，绕开 stroke-dashoffset 的边界行为，保证圆环完整闭合
const segments = computed(() => {
  const total = tot.value
  if (!total) return []
  let acc = 0
  return props.data.map((c) => {
    const frac = Math.max(0, (c.amount || 0) / total)
    const seg = {
      color: c.color,
      len: frac * C,
      frame: `${frac * C} ${C - frac * C}`,
      angle: acc * 360 - 90,
    }
    acc += frac
    return seg
  })
})
const totalLabel = computed(() => Number(tot.value).toFixed(2))
const countLabel = computed(() => `${props.data.length} ${props.unit}`)
</script>

<style scoped>
.dc { flex: none; width: 190px; height: 190px; }
.dc-svg { width: 100%; height: 100%; display: block; }
.dc-seg { opacity: 1; }
.dc-total { font-size: 30px; font-weight: 700; fill: var(--lj-text); letter-spacing: .02em; }
.dc-total-sub { font-size: 12px; fill: var(--lj-text-3); }
</style>
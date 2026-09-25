<template>
  <div class="trend" :style="{ height: height + 'px' }">
    <svg
      ref="svgEl"
      :viewBox="`0 0 ${VW} ${VH}`"
      preserveAspectRatio="none"
      class="trend-svg"
      aria-hidden="true"
      @mousemove="onMove"
      @mouseleave="onLeave"
      @touchstart.passive="onTouchStart"
      @touchmove.passive="onTouchMove"
      @touchend.passive="onTouchEnd"
    >
      <defs>
        <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="var(--dp-accent)" stop-opacity=".4"/>
          <stop offset="1" stop-color="var(--dp-accent)" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <!-- 零基线 -->
      <line :x1="0" :y1="VH" :x2="VW" :y2="VH" stroke="var(--dp-line)" stroke-width=".5"/>
      <!-- 面积路径（支出） -->
      <path v-if="pathD" :d="pathD" fill="url(#trend-fill)" />
      <!-- 折线（支出） -->
      <path v-if="lineD" :d="lineD" fill="none" stroke="var(--dp-accent-strong)" stroke-width="1.2" stroke-linejoin="round" stroke-linecap="round"/>
      <!-- 数据点（hover 显示数值） -->
      <g v-for="(p, i) in points" :key="i">
        <circle :cx="p.x" :cy="p.y" r="1.6" fill="var(--dp-surface)" stroke="var(--dp-accent-strong)" stroke-width=".8"/>
      </g>
      <!-- 悬浮十字线 -->
      <g v-if="hoverIndex !== null">
        <line :x1="hoverX" :x2="hoverX" :y1="0" :y2="VH" class="trend-cross"/>
        <circle :cx="hoverX" :cy="hoverPoint.y" r="2.6" class="trend-hover-dot"/>
      </g>
    </svg>
    <ChartTip
      :show="hoverIndex !== null"
      :x="hoverX"
      :vw="VW"
      :title="hoverTitle"
      :rows="hoverRows"
    />
    <div class="trend-axis">
      <span>{{ firstDate }}</span>
      <span>{{ midDate }}</span>
      <span>{{ lastDate }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import ChartTip from '@/components/charts/ChartTip.vue'
import { useChartHover } from '@/composables/useChartHover'

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ date, income, expense }]
  height: { type: Number, default: 120 },
  mode: { type: String, default: 'expense' }, // expense / income / both
  unit: { type: String, default: '' },
})

const VW = 300
const VH = 80

const points = computed(() => {
  const d = props.data || []
  if (!d.length) return []
  const values = d.map(x => props.mode === 'income' ? (x.income || 0) : (x.expense || 0))
  const max = Math.max(...values, 1)
  const stepX = VW / Math.max(d.length - 1, 1)
  return values.map((v, i) => ({
    x: i * stepX,
    y: VH - (v / max) * (VH - 4),
  }))
})

const svgEl = ref(null)
const { hoverIndex, hoverX, onMove, onLeave, onTouchStart, onTouchMove, onTouchEnd } = useChartHover({
  svgRef: svgEl,
  columns: () => points.value.map(p => p.x),
})

const hoverPoint = computed(() => points.value[hoverIndex.value] || { x: 0, y: 0 })
const hoverTitle = computed(() => (props.data[hoverIndex.value]?.date || '').slice(5))
const hoverRows = computed(() => {
  const d = props.data[hoverIndex.value]
  if (!d) return []
  const fmt = (v) => `${props.unit}${Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
  if (props.mode === 'both') {
    return [
      { label: '收入', value: fmt(d.income) },
      { label: '支出', value: fmt(d.expense) },
    ]
  }
  const isInc = props.mode === 'income'
  return [{ label: isInc ? '收入' : '支出', value: fmt(isInc ? d.income : d.expense) }]
})

const lineD = computed(() => {
  if (!points.value.length) return ''
  return points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
})

const pathD = computed(() => {
  if (!points.value.length) return ''
  const line = points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
  return `${line} L ${VW} ${VH} L 0 ${VH} Z`
})

const firstDate = computed(() => (props.data[0]?.date || '').slice(5))
const midDate = computed(() => {
  const d = props.data || []
  if (!d.length) return ''
  return (d[Math.floor(d.length / 2)]?.date || '').slice(5)
})
const lastDate = computed(() => {
  const d = props.data || []
  if (!d.length) return ''
  return (d[d.length - 1]?.date || '').slice(5)
})
</script>

<style scoped>
.trend {
  position: relative;
  width: 100%;
}
.trend-svg {
  width: 100%;
  height: calc(100% - 18px);
  display: block;
  cursor: crosshair;
}
.trend-cross { stroke: var(--dp-accent-strong); stroke-width: .8; stroke-dasharray: 3 3; opacity: .55; }
.trend-hover-dot { fill: var(--dp-surface); stroke: var(--dp-accent-strong); stroke-width: 1.2; }
.trend-axis {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--dp-text3);
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
  letter-spacing: .02em;
}
</style>
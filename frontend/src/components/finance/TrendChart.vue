<template>
  <div class="tc">
    <svg :viewBox="`0 0 ${W} ${H}`" class="tc-svg" role="img" aria-label="本月收支趋势">
      <!-- 网格线 -->
      <g v-for="i in gridLines" :key="i" class="tc-grid">
        <line :x1="pad.l" :x2="W - pad.r" :y1="gridY(i)" :y2="gridY(i)" />
      </g>

      <!-- 面积渐变（支出） -->
      <defs>
        <linearGradient id="tc-area-exp" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#C05C4E" stop-opacity=".35" />
          <stop offset="100%" stop-color="#C05C4E" stop-opacity="0" />
        </linearGradient>
        <linearGradient id="tc-area-inc" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#C7A96B" stop-opacity=".32" />
          <stop offset="100%" stop-color="#C7A96B" stop-opacity="0" />
        </linearGradient>
      </defs>

      <polygon v-if="hasExp" :points="areaExp" fill="url(#tc-area-exp)" class="tc-area" />
      <polygon v-if="hasInc" :points="areaInc" fill="url(#tc-area-inc)" class="tc-area" />

      <polyline v-if="hasExp" :points="lineExp" fill="none" stroke="#C05C4E" stroke-width="2" stroke-linejoin="round" class="tc-line" />
      <polyline v-if="hasInc" :points="lineInc" fill="none" stroke="#C7A96B" stroke-width="2" stroke-linejoin="round" class="tc-line" />

      <!-- X 轴日期 -->
      <text v-for="(d, i) in xLabels" :key="`x` + i" :x="d.x" :y="H - 4" text-anchor="middle" class="tc-axis">{{ d.label }}</text>

      <!-- 图例 -->
      <g class="tc-legend">
        <line x1="0" y1="0" x2="16" y2="0" stroke="#C05C4E" stroke-width="2" /><text x="20" y="4">支出</text>
        <line x1="76" y1="0" x2="92" y2="0" stroke="#C7A96B" stroke-width="2" /><text x="96" y="4">收入</text>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  days: { type: Array, default: () => [] }, // [{day, income, expense}]
  hasAny: { type: Boolean, default: false },
})

const W = 500
const H = 230
const pad = { l: 24, r: 12, t: 20, b: 24 }
const plotW = W - pad.l - pad.r
const plotH = H - pad.t - pad.b

const n = computed(() => props.days.length)
// 用户无数据时仍渲染坐标，但只显示网格、不画线
const maxV = computed(() => {
  let m = 0
  for (const d of props.days) { m = Math.max(m, d.income || 0, d.expense || 0) }
  // 留白：顶到 0 线不便观察，扩 20%
  return m * 1.2 || 1
})
function x(i) { return n.value <= 1 ? pad.l + plotW / 2 : pad.l + (i / (n.value - 1)) * plotW }
function yPrice(v) { return pad.t + plotH - (Math.min(v, maxV.value) / maxV.value) * plotH }

const lineExp = computed(() => props.days.map((d, i) => `${x(i)},${yPrice(d.expense || 0)}`).join(' '))
const lineInc = computed(() => props.days.map((d, i) => `${x(i)},${yPrice(d.income || 0)}`).join(' '))
const areaExp = computed(() => `${x(0)},${plotBottom()} ${lineExp.value} ${x(n.value - 1)},${plotBottom()}`)
const areaInc = computed(() => `${x(0)},${plotBottom()} ${lineInc.value} ${x(n.value - 1)},${plotBottom()}`)
function plotBottom() { return pad.t + plotH }

const hasExp = computed(() => props.days.some(d => d.expense))
const hasInc = computed(() => props.days.some(d => d.income))

const gridLines = [0, 1, 2, 3, 4]
function gridY(i) { return pad.t + (i / 4) * plotH }
const xLabels = computed(() => {
  const nVal = n.value
  if (!nVal) return []
  // 取首/中/尾 最多 5 个
  const idxs = []
  const step = Math.max(1, Math.ceil(nVal / 5))
  for (let i = 0; i < nVal; i += step) idxs.push(i)
  if (!idxs.includes(nVal - 1)) idxs.push(nVal - 1)
  return idxs.map((i) => ({ x: x(i), label: (props.days[i]?.day || '').slice(5) }))
})
</script>

<style scoped>
.tc { width: 100%; }
.tc-svg { width: 100%; height: auto; display: block; }
.tc-grid line { stroke: rgba(127,168,163,.12); stroke-width: 1; }
.tc-line { opacity: 0; animation: tc-in .8s ease forwards; }
.tc-line:nth-of-type(1) { animation-delay: .05s; }
.tc-area { opacity: 0; animation: tc-fade .8s ease forwards; }
@keyframes tc-in { from { stroke-dasharray: 600; opacity: 0; } to { stroke-dasharray: 600; opacity: 1; } }
@keyframes tc-fade { from { opacity: 0; } to { opacity: 1; } }
.tc-axis { font-size: 11px; fill: var(--lj-text-3); }
.tc-legend { font-size: 12px; fill: var(--lj-text-2); transform: translate(8px, 14px); }
@media (prefers-reduced-motion: reduce) { .tc-line,.tc-area { opacity: 1; animation: none; } }
</style>
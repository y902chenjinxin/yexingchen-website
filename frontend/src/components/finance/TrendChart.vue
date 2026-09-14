<template>
  <div class="tc">
    <div class="tc-wrap">
      <svg :viewBox="`0 0 ${W} ${H}`" class="tc-svg" role="img" aria-label="本月收支趋势" ref="svgEl" @mousemove="onMove" @mouseleave="onLeave">
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

        <!-- 峰值标注 -->
        <g v-if="peakExp.v > 0" class="tc-peak">
          <circle :cx="x(peakExp.i)" :cy="yPrice(peakExp.v)" r="4" fill="#C05C4E" class="tc-peak-dot" />
          <text :x="x(peakExp.i)" :y="yPrice(peakExp.v) - 7" text-anchor="middle" class="tc-peak-txt tc-peak-txt-exp">峰 {{ fmt(peakExp.v) }}</text>
        </g>
        <g v-if="peakInc.v > 0" class="tc-peak">
          <circle :cx="x(peakInc.i)" :cy="yPrice(peakInc.v)" r="4" fill="#C7A96B" class="tc-peak-dot" />
          <text :x="x(peakInc.i)" :y="yPrice(peakInc.v) - 7" text-anchor="middle" class="tc-peak-txt tc-peak-txt-inc">峰 {{ fmt(peakInc.v) }}</text>
        </g>

        <!-- 垂直线 + 交点（悬浮） -->
        <g v-if="hover !== null" class="tc-hover">
          <line :x1="hoverX" :x2="hoverX" :y1="pad.t" :y2="plotBottom()" class="tc-cross" />
          <circle v-if="hoverInc > 0" :cx="hoverX" :cy="yPrice(hoverInc)" r="3.5" fill="#C7A96B" class="tc-hover-dot" />
          <circle v-if="hoverExp > 0" :cx="hoverX" :cy="yPrice(hoverExp)" r="3.5" fill="#C05C4E" class="tc-hover-dot" />
        </g>

        <!-- X 轴日期 -->
        <text v-for="(d, i) in xLabels" :key="`x` + i" :x="d.x" :y="H - 4" text-anchor="middle" class="tc-axis">{{ d.label }}</text>

        <!-- 图例 -->
        <g class="tc-legend">
          <line x1="0" y1="0" x2="16" y2="0" stroke="#C05C4E" stroke-width="2" /><text x="20" y="4">支出</text>
          <line x1="76" y1="0" x2="92" y2="0" stroke="#C7A96B" stroke-width="2" /><text x="96" y="4">收入</text>
        </g>
      </svg>

      <!-- 悬浮数值提示 -->
      <div v-if="hover !== null" class="tc-tip" :style="tipStyle">
        <div class="tc-tip-day">{{ hoverDay }}</div>
        <div class="tc-tip-row inc"><span>收入</span><b>+ ¥ {{ fmt(hoverInc) }}</b></div>
        <div class="tc-tip-row exp"><span>支出</span><b>− ¥ {{ fmt(hoverExp) }}</b></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  days: { type: Array, default: () => [] }, // [{day, income, expense}]
  hasAny: { type: Boolean, default: false },
})

const svgEl = ref(null)
const hover = ref(null)

const W = 500
const H = 230
const pad = { l: 24, r: 12, t: 20, b: 24 }
const plotW = W - pad.l - pad.r
const plotH = H - pad.t - pad.b

const n = computed(() => props.days.length)
const maxV = computed(() => {
  let m = 0
  for (const d of props.days) { m = Math.max(m, d.income || 0, d.expense || 0) }
  return m * 1.2 || 1
})
function x(i) { return n.value <= 1 ? pad.l + plotW / 2 : pad.l + (i / (n.value - 1)) * plotW }
function yPrice(v) { return pad.t + plotH - (Math.min(v, maxV.value) / maxV.value) * plotH }
function plotBottom() { return pad.t + plotH }

const lineExp = computed(() => props.days.map((d, i) => `${x(i)},${yPrice(d.expense || 0)}`).join(' '))
const lineInc = computed(() => props.days.map((d, i) => `${x(i)},${yPrice(d.income || 0)}`).join(' '))
const areaExp = computed(() => `${x(0)},${plotBottom()} ${lineExp.value} ${x(n.value - 1)},${plotBottom()}`)
const areaInc = computed(() => `${x(0)},${plotBottom()} ${lineInc.value} ${x(n.value - 1)},${plotBottom()}`)

const hasExp = computed(() => props.days.some(d => d.expense))
const hasInc = computed(() => props.days.some(d => d.income))

const gridLines = [0, 1, 2, 3, 4]
function gridY(i) { return pad.t + (i / 4) * plotH }
const xLabels = computed(() => {
  const nVal = n.value
  if (!nVal) return []
  const idxs = []
  const step = Math.max(1, Math.ceil(nVal / 5))
  for (let i = 0; i < nVal; i += step) idxs.push(i)
  if (!idxs.includes(nVal - 1)) idxs.push(nVal - 1)
  return idxs.map((i) => ({ x: x(i), label: (props.days[i]?.day || '').slice(5) }))
})

// 峰值
const peakExp = computed(() => {
  let idx = -1, m = 0
  props.days.forEach((d, i) => { const v = d.expense || 0; if (v > m) { m = v; idx = i } })
  return { i: idx, v: m }
})
const peakInc = computed(() => {
  let idx = -1, m = 0
  props.days.forEach((d, i) => { const v = d.income || 0; if (v > m) { m = v; idx = i } })
  return { i: idx, v: m }
})

// 悬浮态
const hoverX = computed(() => (hover.value == null ? 0 : x(hover.value)))
const hoverInc = computed(() => (hover.value == null ? 0 : (props.days[hover.value]?.income || 0)))
const hoverExp = computed(() => (hover.value == null ? 0 : (props.days[hover.value]?.expense || 0)))
const hoverDay = computed(() => (hover.value == null ? '' : (props.days[hover.value]?.day || '').slice(5)))
const tipStyle = computed(() => {
  if (hover.value == null) return {}
  const cellW = plotW / Math.max(1, n.value - 1)
  const pct = ((x(hover.value)) / W) * 100
  const flip = pct > 68
  return { left: `${pct}%`, transform: `translateX(${flip ? -110 : 10}%)` }
})

function onMove(e) {
  if (n.value < 1) return
  const rect = svgEl.value.getBoundingClientRect()
  if (!rect.width) return
  const px = ((e.clientX - rect.left) / rect.width) * W
  const i = Math.round(((px - pad.l) / plotW) * (n.value - 1))
  hover.value = Math.max(0, Math.min(n.value - 1, i))
}
function onLeave() {
  hover.value = null
}

function fmt(v) { return Number(v || 0).toFixed(1).replace(/\.0$/, '') }
</script>

<style scoped>
.tc { width: 100%; }
.tc-wrap { position: relative; width: 100%; }
.tc-svg { width: 100%; height: auto; display: block; cursor: crosshair; }
.tc-grid line { stroke: rgba(127,168,163,.12); stroke-width: 1; }
.tc-line { opacity: 0; animation: tc-in .8s ease forwards; }
.tc-line:nth-of-type(1) { animation-delay: .05s; }
.tc-area { opacity: 0; animation: tc-fade .8s ease forwards; }
@keyframes tc-in { from { stroke-dasharray: 600; opacity: 0; } to { stroke-dasharray: 600; opacity: 1; } }
@keyframes tc-fade { from { opacity: 0; } to { opacity: 1; } }
.tc-axis { font-size: 11px; fill: var(--lj-text-3); }
.tc-legend { font-size: 12px; fill: var(--lj-text-2); transform: translate(8px, 14px); }

.tc-peak-dot { opacity: 0; animation: tc-fade .4s ease forwards; }
.tc-peak-txt { font-size: 10px; fill: var(--lj-text-3); letter-spacing: .03em; }
.tc-peak-txt-exp { fill: #C05C4E; opacity: .95; }
.tc-peak-txt-inc { fill: #C7A96B; opacity: .95; }

.tc-cross { stroke: rgba(127,168,163,.4); stroke-width: 1; stroke-dasharray: 3 3; }
.tc-hover-dot { opacity: 0; animation: tc-fade .15s ease forwards; }

.tc-tip {
  position: absolute;
  top: 6px;
  min-width: 96px;
  padding: 7px 10px;
  border-radius: 10px;
  font-family: var(--font-serif);
  font-size: 12px;
  color: var(--lj-text);
  background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line);
  box-shadow: 0 8px 22px rgba(0,0,0,.22);
  pointer-events: none;
  line-height: 1.5;
  z-index: 3;
}
.tc-tip-day { font-size: 11px; color: var(--lj-text-2); letter-spacing: .05em; margin-bottom: 2px; }
.tc-tip-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.tc-tip-row b { font-variant-numeric: tabular-nums; font-weight: 600; }
.tc-tip-row.inc b { color: #C7A96B; }
.tc-tip-row.exp b { color: #C05C4E; }
@media (prefers-reduced-motion: reduce) { .tc-line,.tc-area { opacity: 1; animation: none; } .tc-peak-dot,.tc-hover-dot { opacity: 1; animation: none; } }
</style>
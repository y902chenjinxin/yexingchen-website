<template>
  <div ref="box" class="kc-box" :style="{ height: height + 'px' }">
    <svg ref="svg" class="kc-svg" :viewBox="viewBox">
      <defs>
        <linearGradient id="kc-vol" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="currentColor" stop-opacity="0.35" />
          <stop offset="1" stop-color="currentColor" stop-opacity="0.04" />
        </linearGradient>
      </defs>

      <!-- 网格 -->
      <g class="kc-grid">
        <line v-for="y in gridLines" :key="'g'+y.y" :x1="padL" :x2="w - padR" :y1="y.y" :y2="y.y" />
      </g>

      <!-- 蜡烛 -->
      <g v-for="(k, i) in view" :key="i">
        <line class="kc-wick" :x1="k.x" :x2="k.x" :y1="k.highY" :y2="k.lowY"
          :stroke="k.color" stroke-width="1" />
        <rect class="kc-body" :x="k.x - cw / 2" :y="k.topY" :width="cw" :height="Math.max(1, k.bottomY - k.topY)"
          :fill="k.color" rx="1" />
      </g>

      <!-- 均线 -->
      <polyline v-for="ma in mas" :key="ma.key" class="kc-ma" :points="ma.points" :stroke="ma.color" fill="none" stroke-width="1.2" />

      <!-- 成交量 -->
      <g class="kc-vol">
        <rect v-for="(k, i) in view" :key="'v'+i"
          :x="k.x - cw / 2" :y="volTop + (1 - k.volNorm) * volH" :width="cw"
          :height="Math.max(1, k.volNorm * volH)" :fill="k.color" opacity="0.55" />
      </g>

      <!-- 纵轴价格标签 -->
      <text v-for="p in priceLabels" :key="'p'+p.i" class="kc-lbl" :x="w - padR + 6" :y="p.y + 3">{{ p.txt }}</text>

      <!-- 十字线 -->
      <g v-if="hover" class="kc-cross">
        <line class="kc-cross-line" :x1="padL" :x2="w - padR" :y1="hover.y" :y2="hover.y" />
        <line class="kc-cross-line" :x1="hover.x" :x2="hover.x" :y1="volTop" :y2="padT" />
        <g class="kc-cross-tip">
          <circle :cx="hover.x" :cy="hover.y" r="3" />
          <text :x="hover.x" :y="hover.y - 8" text-anchor="middle">{{ hover.info }}</text>
        </g>
      </g>
    </svg>

    <!-- 悬浮信息条 -->
    <div v-if="hover" class="kc-tip" :style="{ left: tipX + 'px', top: 6 + 'px' }">
      <span class="kc-tip-date">{{ hover.k.date }}</span>
      <span :class="hover.k.up ? 'up' : 'down'">开 {{ hover.k.open }} 高{{ hover.k.high }}</span>
      <span :class="hover.k.up ? 'up' : 'down'">收 {{ hover.k.close }} 低 {{ hover.k.low }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 320 },
  ma: { type: Array, default: () => [5, 10, 20] },
})

const box = ref(null)
const svg = ref(null)
let W = 720
const padL = 8
const padR = 46
const padT = 14
const volH = 46
const volGap = 8

const viewBox = computed(() => `0 0 ${W} ${props.height}`)

const w = computed(() => W - padL - padR)

// 均线
const MA_COLORS = { 5: '#E0A93C', 10: '#5E9BD6', 20: '#A97FB5' }
function calcMa(period) {
  const arr = props.data
  return arr.map((k, i) => {
    if (i < period - 1) return null
    let s = 0
    for (let j = i - period + 1; j <= i; j++) s += arr[j].close
    return { x: i, v: s / period }
  })
}

const mas = computed(() => {
  const range = chartRange()
  return props.ma
    .filter(p => props.data.length >= p)
    .map(p => {
      const pts = calcMa(p)
        .map((m, i) => (m && m.x >= range.start ? { x: m.x, v: m.v } : null))
        .filter(Boolean)
        .map(m => `${padL + ((m.x - range.start) / Math.max(1, range.n - 1)) * w.value},${yOf(m.v)}`)
        .join(' ')
      return { key: p, color: MA_COLORS[p] || '#999', points: pts }
    })
})

function chartRange() {
  const n = props.data.length
  const start = Math.max(0, n - 180)
  return { start, n: n - start, end: n }
}

const view = computed(() => {
  const data = props.data
  const range = chartRange()
  const slice = data.slice(range.start, range.end)
  if (!slice.length) return []
  let hi = -Infinity
  let lo = Infinity
  let maxVol = 0
  for (const k of slice) {
    if (k.high > hi) hi = k.high
    if (k.low < lo) lo = k.low
    if (k.volume > maxVol) maxVol = k.volume
  }
  const span = hi - lo || 1
  const step = (range.n - 1) || 1
  const cw = Math.max(3, Math.min(12, (w.value / range.n) * 0.7))
  const chartBottom = props.height - volH - volGap
  function cx(i) { return padL + (i / step) * w.value }
  function yOfPrice(v) { return padT + (hi - v) / span * (chartBottom - padT) }
  return slice.map((k, i) => {
    const color = (k.close ?? k.open) >= (k.open ?? k.close) ? RISE : FALL
    const yo = yOfPrice(k.open)
    const yc = yOfPrice(k.close)
    return {
      x: cx(i), cw,
      highY: yOfPrice(k.high), lowY: yOfPrice(k.low),
      topY: Math.min(yo, yc), bottomY: Math.max(yo, yc),
      color,
      volNorm: maxVol ? k.volume / maxVol : 0,
      up: color === RISE,
      k,
    }
  })
})

const volTop = computed(() => props.height - volH)
function yOf(v) {
  const data = props.data
  const range = chartRange()
  const slice = data.slice(range.start, range.end)
  let hi = -Infinity, lo = Infinity
  for (const k of slice) { if (k.high > hi) hi = k.high; if (k.low < lo) lo = k.low }
  const span = hi - lo || 1
  const chartBottom = props.height - volH - volGap
  return padT + (hi - v) / span * (chartBottom - padT)
}

const gridLines = computed(() => {
  const lines = []
  const n = 4
  const top = padT
  const bottom = props.height - volH - volGap
  for (let i = 0; i <= n; i++) {
    lines.push({ y: top + (bottom - top) * i / n })
  }
  return lines
})

const priceLabels = computed(() => {
  const data = props.data
  if (!data.length) return []
  const range = chartRange()
  const slice = data.slice(range.start, range.end)
  let hi = -Infinity, lo = Infinity
  for (const k of slice) { if (k.high > hi) hi = k.high; if (k.low < lo) lo = k.low }
  const span = hi - lo || 1
  const bottom = props.height - volH - volGap
  const out = []
  for (let i = 0; i <= 4; i++) {
    const v = hi - span * i / 4
    out.push({ i, v, y: padT + (bottom - padT) * i / 4, txt: v.toFixed(2) })
  }
  return out
})

const RISE = '#D8504F'
const FALL = '#3F968E'

// 十字线 / 悬浮
const hover = ref(null)
function onMove(e) {
  const rect = svg.value.getBoundingClientRect()
  const x = (e.clientX - rect.left) / rect.width * W
  const range = chartRange()
  const n = range.n
  const idx = Math.round((x - padL) / (w.value / Math.max(1, n - 1)))
  if (idx < 0 || idx >= n || range.start + idx >= props.data.length) { hover.value = null; return }
  const k = view.value[idx]
  if (!k) return
  const data = props.data[range.start + idx]
  hover.value = {
    x: k.x, y: (k.topY + k.bottomY) / 2, k: data,
    info: `${data.open} / ${data.close}`,
  }
}
function onLeave() { hover.value = null }

const tipX = computed(() => {
  if (!hover.value) return 0
  const rel = (hover.value.x / W) * box.value.clientWidth
  return Math.min(Math.max(rel - 60, 8), box.value.clientWidth - 130)
})

function resize() {
  if (!box.value) return
  nextTick(() => { W = Math.max(320, box.value.clientWidth) })
}

let ro
onMounted(() => {
  resize()
  ro = new ResizeObserver(resize)
  ro.observe(box.value)
})
onBeforeUnmount(() => ro && ro.disconnect())
</script>

<style scoped>
.kc-box { position: relative; width: 100%; }
.kc-svg { width: 100%; height: 100%; display: block; cursor: crosshair; }
.kc-grid line { stroke: rgba(74, 95, 99, 0.10); stroke-dasharray: 2 3; }
.kc-lbl { font-size: 10px; fill: rgba(111, 138, 138, 0.8); }
.kc-ma { pointer-events: none; }
.kc-cross-line { stroke: rgba(120, 150, 150, 0.35); stroke-dasharray: 3 3; }
.kc-cross-tip circle { fill: #C7A96B; }
.kc-cross-tip text { font-size: 10px; fill: #C7A96B; }
.kc-tip {
  position: absolute; display: flex; flex-direction: column; gap: 2px;
  padding: 6px 10px; border-radius: 10px; pointer-events: none; z-index: 2;
  background: rgba(11, 15, 20, 0.82); -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
  border: 1px solid rgba(199, 169, 107, 0.25); color: #D8E2E0; font-size: 11px; line-height: 1.4;
}
.kc-tip-date { color: #C7A96B; }
.kc-tip .up { color: #D8504F; }
.kc-tip .down { color: #3F968E; }
</style>
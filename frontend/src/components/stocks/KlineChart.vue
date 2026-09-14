<template>
  <div ref="box" class="kc-box" :style="{ height: height + 'px' }">
    <!-- 头部：周期切换 + 操作提示 -->
    <div class="kc-head">
      <div class="kc-tabs">
        <button v-for="p in periods" :key="p.k" class="kc-tab" :class="{ on: period === p.k }"
          @click="setPeriod(p.k)">{{ p.label }}</button>
      </div>
      <span class="kc-hint">拖拽平移 · 滚轮缩放 · 双击复位 · 底部拉长时间轴</span>
    </div>

    <svg ref="svg" class="kc-svg" :viewBox="viewBox"
      @pointerdown="chartDown" @pointermove="chartMove" @pointerup="chartUp" @pointerleave="chartLeave"
      @wheel.prevent="onWheel" @dblclick.prevent="resetRange">
      <defs>
        <linearGradient id="kc-vol-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="currentColor" stop-opacity="0.35" />
          <stop offset="1" stop-color="currentColor" stop-opacity="0.06" />
        </linearGradient>
      </defs>

      <g class="kc-grid">
        <template v-for="g in grid">
          <line :x1="pltL" :x2="plotR" :y1="g.y" :y2="g.y" />
          <text class="kc-lbl" :x="plotR + 6" :y="g.y + 3">{{ g.txt }}</text>
        </template>
      </g>

      <g v-if="preY != null" class="kc-prev">
        <line :x1="pltL" :x2="plotR" :y1="preY" :y2="preY" :stroke="preyColor" />
        <g :transform="`translate(${plotR + 2}, ${Math.max(padT + 2, preY - 9)})`">
          <rect x="-2" y="-3" :width="tagW" height="12" rx="3" :fill="preyColor" opacity="0.18" />
          <text x="-2" y="6" class="kc-prev-txt">{{ prevTxt }}</text>
        </g>
      </g>

      <!-- 高位 / 低位参考线 -->
      <g v-if="highY != null" class="kc-ref">
        <line :x1="pltL" :x2="plotR" :y1="highY" :y2="highY" />
        <g :transform="`translate(${plotR + 2}, ${Math.max(padT + 2, highY - 9)})`">
          <rect x="-2" y="-3" :width="highTagW" height="12" rx="3" :fill="highColor" opacity="0.16" />
          <text x="-2" y="6" class="kc-ref-txt">{{ highTxt }}</text>
        </g>
      </g>

      <g v-for="(k, i) in view" :key="'c' + i">
        <line class="kc-wick" :x1="k.x" :x2="k.x" :y1="k.hiY" :y2="k.loY" :stroke="k.color" stroke-width="1.1" />
        <rect class="kc-body" :x="k.x - k.cw / 2" :y="k.topY" :width="k.cw" :height="k.bodyH" :fill="k.color" rx="1" />
      </g>

      <polyline v-for="ma in mas" :key="'ma' + ma.key" class="kc-ma"
        :points="ma.pts" :stroke="ma.color" fill="none" stroke-width="1.3" stroke-linejoin="round" />

      <g v-for="(k, i) in view" :key="'v' + i">
        <rect :x="k.x - k.cw / 2" :y="k.volY" :width="k.cw" :height="k.volH"
          :fill="k.color" opacity="0.6" rx="1" />
      </g>
      <text class="kc-vol-lbl" :x="pltL" :y="volTop - 6">{{ volMaxTxt }}</text>

      <g class="kc-date">
        <text v-for="d in dateLabels" :key="d.i" :x="d.x" :y="dateY" text-anchor="middle" class="kc-date-txt">{{ d.txt }}</text>
      </g>

      <g class="kc-legend" :transform="`translate(${pltL}, 4)`">
        <text class="kc-leg-k" x="0" y="10">{{ periodLabel }}</text>
        <template v-for="lg in mas" :key="'l' + lg.key">
          <line :x1="lg.lx" :y1="6" :x2="lg.lx + 9" :y2="6" :stroke="lg.color" stroke-width="2" />
          <text :x="lg.lx + 12" :y="10" class="kc-leg-t" :fill="lg.color">MA{{ lg.key }}</text>
        </template>
        <template v-if="showPrevTag">
          <circle :cx="lgx.last" :cy="6" r="3" :fill="preyColor" />
          <text :x="lgx.last + 6" :y="10" class="kc-leg-t" :fill="preyColor">昨收</text>
        </template>
      </g>

      <g v-if="hover" class="kc-cross">
        <line class="kc-cross-line" :x1="hover.x" :x2="hover.x" :y1="volTop" :y2="padT" />
        <line class="kc-cross-line" :x1="pltL" :x2="plotR" :y1="hover.y" :y2="hover.y" />
        <circle :cx="hover.x" :cy="hover.y" r="3" class="kc-cross-dot" />
      </g>
    </svg>

    <!-- 底部可拖拽时间轴（拉长时间范围） -->
    <div class="kc-strip">
      <div ref="track" class="kc-strip-track">
        <div class="kc-strip-window" :style="winStyle" data-mode="move"
          @pointerdown="stripStart" @pointermove="stripMove" @pointerup="stripEnd"
          @pointercancel="stripEnd">
          <div class="kc-thumb left" data-mode="left" @pointerdown.stop="stripStart"
            @pointermove="stripMove" @pointerup="stripEnd"></div>
          <div class="kc-thumb right" data-mode="right" @pointerdown.stop="stripStart"
            @pointermove="stripMove" @pointerup="stripEnd"></div>
        </div>
      </div>
      <div class="kc-strip-meta">
        <span>显示 {{ count }} / 共 {{ total }} 根</span>
        <button class="kc-reset" @click="resetRange">复位</button>
      </div>
    </div>

    <div v-if="hover" class="kc-tip" :class="hover.tipSide" style="top:10px">
      <div class="kc-tip-date">{{ hover.k.date }}<span v-if="hover.chg != null" :class="hover.up ? 'up' : 'down'"> {{ hover.up ? '+' : '−' }}{{ Math.abs(hover.chg).toFixed(2) }}%</span></div>
      <div class="kc-tip-row"><span>开</span><b :class="hover.up ? 'up' : 'down'">{{ hover.k.open }}</b><span>高</span><b :class="hover.up ? 'up' : 'down'">{{ hover.k.high }}</b></div>
      <div class="kc-tip-row"><span>收</span><b :class="hover.up ? 'up' : 'down'">{{ hover.k.close }}</b><span>低</span><b :class="hover.up ? 'up' : 'down'">{{ hover.k.low }}</b></div>
      <div class="kc-tip-meta">量 {{ volTxt(hover.k.volume) }}<template v-if="hover.k.amount"> · 额 {{ amtTxt(hover.k.amount) }}</template></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 420 },
})
const emit = defineEmits(['analysis'])

const box = ref(null)
const svg = ref(null)
const track = ref(null)
let W = 720
let H = props.height

const padT = 16, padB = 20, padL = 10, padR = 56, volH = 62, volGap = 8
const RISE = '#d8504f', FALL = '#3f968e', PREY = '#c7a96b'
const preyColor = PREY
const MA_C = { 5: '#f0aa3c', 10: '#4f9dde', 20: '#c07be0' }
const MIN_COUNT = 15

const pltL = padL
const plotR = computed(() => W - padR)
const priceTop = padT
const priceBot = computed(() => H - padB - volH - volGap)
const volTop = computed(() => priceBot.value + volGap)
const plotW = computed(() => plotR.value - pltL)
const viewBox = computed(() => `0 0 ${W} ${H}`)
const dateY = computed(() => H - 8)

/* ---------- 周期 ---------- */
const periods = [
  { k: 'day', label: '日K' },
  { k: 'week', label: '周K' },
  { k: 'month', label: '月K' },
]
const period = ref('day')
const periodLabel = computed(() => periods.find(p => p.k === period.value).label)

function weekKey(ds) {
  const d = new Date(ds)
  const d0 = new Date(d.getFullYear(), 0, 1)
  const wk = Math.ceil((((d - d0) / 86400000) + d0.getDay() + 1) / 7)
  return d.getFullYear() + '-W' + wk
}
function aggregate(daily, type) {
  if (!daily || !daily.length) return []
  if (type === 'day') return daily
  const out = []
  for (const k of daily) {
    const key = type === 'month' ? k.date.slice(0, 7) : weekKey(k.date)
    const last = out[out.length - 1]
    if (!last || last.key !== key) {
      out.push({ key, date: k.date, open: k.open, close: k.close, high: k.high, low: k.low, volume: k.volume, amount: k.amount })
    } else {
      last.close = k.close
      last.high = Math.max(last.high, k.high)
      last.low = Math.min(last.low, k.low)
      last.volume += k.volume
      last.amount += k.amount
    }
  }
  return out
}
const merged = computed(() => aggregate(props.data, period.value))
const total = computed(() => merged.value.length)

/* ---------- 显示窗口 ---------- */
const start = ref(0)
const count = ref(0)
function clamp(v, mn, mx) { const lo = Math.min(mn, mx), hi = Math.max(mn, mx); return Math.min(hi, Math.max(lo, v)) }
function setRange(s, c) {
  const t = total.value
  if (!t) return
  const lo = Math.min(MIN_COUNT, t)
  const c2 = clamp(Math.round(c) || 1, lo, t)
  start.value = clamp(Math.round(s), 0, t - c2)
  count.value = c2
}
function defaultRange() {
  const t = total.value
  if (!t) return
  const def = period.value === 'day' ? Math.min(120, t) : t
  setRange(t - def, def)
}
function resetRange() { defaultRange() }
function setPeriod(k) { period.value = k; defaultRange() }
if (total.value) defaultRange()

/* ---------- 绘制数据 ---------- */
function stats() {
  const t = merged.value
  if (!t.length) return null
  const to = Math.min(start.value + count.value, t.length)
  let hi = -Infinity, lo = Infinity, maxVol = 0
  for (let i = start.value; i < to; i++) {
    const k = t[i]
    if (k.high > hi) hi = k.high
    if (k.low < lo) lo = k.low
    if (k.volume > maxVol) maxVol = k.volume
  }
  const prev = start.value - 1 >= 0 ? t[start.value - 1].close : null
  if (prev != null) { if (prev > hi) hi = prev; if (prev < lo) lo = prev }
  if (!isFinite(hi) || !isFinite(lo) || hi === lo) { hi = hi || 1; lo = hi === lo ? hi - 1 : lo }
  return { start: start.value, n: Math.min(count.value, to - start.value), hi, lo, span: hi - lo || 1, maxVol, prev }
}
function yPrice(v, st) { return priceTop + ((st.hi - v) / st.span) * (priceBot.value - priceTop) }

const view = computed(() => {
  const t = merged.value
  const st = stats()
  if (!t.length || !st) return []
  const step = plotW.value / Math.max(1, st.n - 1)
  const cw = Math.max(3, Math.min(11, (plotW.value / st.n) * 0.72))
  const out = []
  let refClose = st.prev != null ? st.prev : (t[st.start] ? t[st.start].open : null)
  for (let i = 0; i < st.n; i++) {
    const k = t[st.start + i]
    const color = (k.close >= (k.open ?? k.close)) ? RISE : FALL
    const yo = yPrice(k.open ?? k.close, st)
    const yc = yPrice(k.close, st)
    const topY = Math.min(yo, yc)
    const bodyH = Math.max(1, Math.abs(yc - yo))
    let chg = null
    if (refClose != null && refClose) chg = ((k.close - refClose) / refClose) * 100
    refClose = k.close
    const vn = st.maxVol ? k.volume / st.maxVol : 0
    out.push({
      x: pltL + i * step, cw, color, up: color === RISE,
      hiY: yPrice(k.high, st), loY: yPrice(k.low, st), topY, bodyH,
      volY: volTop.value + (1 - vn) * volH, volH: Math.max(1, vn * volH),
      chg, k,
    })
  }
  return out
})

const mas = computed(() => {
  const t = merged.value
  const st = stats()
  if (!t.length || !st) return []
  return [5, 10, 20].filter(p => t.length >= p).map(p => {
    const step = plotW.value / Math.max(1, st.n - 1)
    const pts = []
    for (let i = st.start; i < st.start + st.n; i++) {
      if (i < p - 1) continue
      let s = 0
      for (let j = i - p + 1; j <= i; j++) s += t[j].close
      pts.push(`${((pltL + (i - st.start) * step)).toFixed(1)},${yPrice(s / p, st).toFixed(1)}`)
    }
    return { key: p, color: MA_C[p], pts: pts.join(' ') }
  })
})

const lgx = computed(() => {
  let cur = pltL + 26 + 16
  const arr = {}
  for (const m of mas.value) { m.lx = cur; cur += 12 + (5 + String(m.key).length) * 6.5 + 8 }
  arr.last = cur + 6
  return arr
})

const preY = computed(() => { const st = stats(); return st && st.prev != null ? yPrice(st.prev, st) : null })
const prevTxt = computed(() => { const st = stats(); return st && st.prev != null ? `昨收 ${st.prev.toFixed(2)}` : '昨收' })
const showPrevTag = computed(() => preY.value != null)

/* ---------- 高位价格参考线 ---------- */
const highColor = '#e5944e'
const highRef = computed(() => {
  const t = merged.value
  if (!t.length) return null
  const to = Math.min(start.value + count.value, t.length)
  let m = -Infinity
  for (let i = start.value; i < to; i++) m = Math.max(m, t[i].high)
  return isFinite(m) ? m : null
})
const highY = computed(() => { const st = stats(); return st && highRef.value != null ? yPrice(highRef.value, st) : null })
const highTxt = computed(() => highRef.value != null ? `最高 ${fmtPrice(highRef.value)}` : '')
const highTagW = computed(() => highTxt.value.length * 7.4 + 10)

/* ---------- 每日研判（规则化总结 + 建议） ---------- */
const ANALYSIS_N = 12
function avg(arr, i, p, key) { if (i < p - 1) return null; let s = 0; for (let j = i - p + 1; j <= i; j++) s += arr[j][key]; return s / p }
const analysis = computed(() => {
  const t = merged.value
  if (t.length < 2) return []
  return t.map((k, i) => {
    const prev = i > 0 ? t[i - 1].close : null
    const chg = prev ? (k.close - prev) / prev * 100 : null
    const ma5 = avg(t, i, 5, 'close')
    const ma20 = avg(t, i, 20, 'close')
    let v5 = null
    if (i >= 5) { let s = 0; for (let j = i - 5; j < i; j++) s += t[j].volume; v5 = s ? k.volume / (s / 5) : null }
    const above5 = ma5 != null && k.close >= ma5
    const above20 = ma20 != null && k.close >= ma20
    const up = k.close >= k.open
    const body = Math.abs(k.close - k.open)
    const rng = Math.max(0.0001, k.high - k.low)

    let shape
    if (chg > 1.5 && up) shape = '强势上攻'
    else if (chg < -1.5) shape = '弱势下行'
    else if (k.open > prev) shape = up ? '高开走高' : '高开走弱'
    else if (k.open < prev) shape = up ? '低开走高' : '低开走弱'
    else shape = '窄幅整理'

    let volTxt = ''
    if (v5 != null) volTxt = v5 >= 1.5 ? '放量' : v5 <= 0.6 ? '缩量' : '量能持平'

    let maTxt = ''
    if (above5 && above20) maTxt = '多头排列'
    else if (!above5 && !above20) maTxt = '空头排列'
    else maTxt = '均线纠缠'

    let score = 0
    if (above5) score += 1; else score -= 1
    if (above20) score += 1; else score -= 1
    if (v5 != null) score += v5 >= 1.3 ? 1 : v5 <= 0.7 ? -1 : 0
    if (chg != null) score += chg >= 1 ? 1 : chg <= -1 ? -1 : 0

    let lv, sug
    if (score >= 3 || (chg >= 3 && above5)) { lv = 'up'; sug = '多头占优，持股待涨或回踩低吸' }
    else if (score >= 1) { lv = 'hold'; sug = '结构未坏，持股观望' }
    else if (score <= -3 || (chg <= -3 && !above20)) { lv = 'danger'; sug = '空头走弱，规避风险' }
    else if (score <= -1) { lv = 'down'; sug = '短线偏弱，控制仓位' }
    else { lv = 'watch'; sug = '方向不明，多看少动' }
    if (v5 >= 1.5 && chg < 0 && chg <= -2) { lv = 'down'; sug = '放量下杀，注意减避' }

    const parts = [shape]
    if (volTxt) parts.push(volTxt)
    if (maTxt) parts.push(maTxt)
    return { date: k.date, close: k.close, chg, up, summary: parts.join('，'), sug, lv }
  }).slice(-ANALYSIS_N)
})
watch(analysis, v => emit('analysis', { period: period.value, list: v }), { immediate: true })

const grid = computed(() => {
  const st = stats(); const out = []
  if (!st) return out
  const n = 5
  for (let i = 0; i <= n; i++) out.push({ y: priceTop + (priceBot.value - priceTop) * i / n, txt: fmtPrice(st.hi - st.span * i / n) })
  return out
})

const dateLabels = computed(() => {
  const t = merged.value; const st = stats()
  if (!t.length || !st) return []
  const cnt = Math.max(2, Math.min(6, Math.floor(st.n / 24)))
  const step = plotW.value / Math.max(1, st.n - 1)
  const out = []
  for (let i = 0; i < cnt; i++) {
    const idx = Math.round((st.n - 1) * i / (cnt - 1))
    out.push({ x: pltL + idx * step, txt: (t[st.start + idx].date || '').replace(/-/g, '/').slice(5) })
  }
  return out
})

const volMaxTxt = computed(() => { const st = stats(); return st && st.maxVol ? `量 ${volTxt(st.maxVol)}` : '' })

/* ---------- 交互：十字线 + 拖拽平移 + 滚轮缩放 ---------- */
const hover = ref(null)
let pan = null
function chartDown(e) {
  const r = svg.value.getBoundingClientRect()
  if (!r.width) return
  const step = plotW.value / Math.max(1, (count.value - 1))
  pan = { sx: e.clientX, st: start.value, stepR: step / r.width }
  updateHover(e)
}
function chartMove(e) {
  if (pan) {
    const dx = e.clientX - pan.sx
    const dr = dx * pan.stepR
    const r = svg.value.getBoundingClientRect()
    const shift = Math.round(dr * (count.value - 1))
    setRange(pan.st + shift, count.value)
  }
  updateHover(e)
}
function chartUp() { pan = null }
function chartLeave() { pan = null; hover.value = null }
function updateHover(e) {
  const r = svg.value.getBoundingClientRect()
  if (!r.width) return
  const x = W * (e.clientX - r.left) / r.width
  const st = stats(); const v = view.value
  if (!st || !v.length) return
  const step = plotW.value / Math.max(1, st.n - 1)
  const idx = Math.round((x - pltL) / step)
  if (idx < 0 || idx >= v.length) { hover.value = null; return }
  const k = v[idx]
  hover.value = { x: k.x, y: k.topY + k.bodyH / 2, k: k, up: k.up, chg: k.chg, tipSide: k.x > W * 0.55 ? 'left' : 'right' }
}
function onWheel(e) {
  const t = total.value
  if (t < MIN_COUNT + 2) return
  const r = svg.value.getBoundingClientRect()
  const x = W * (e.clientX - r.left) / r.width
  const rel = clamp((x - pltL) / plotW.value, 0, 1)
  const gIdx = start.value + Math.round(rel * (count.value - 1)) // 指针下全局索引
  const factor = e.deltaY > 0 ? 1.25 : 0.8
  let nc = clamp(Math.round(count.value * factor), MIN_COUNT, t)
  if (nc === count.value) return
  const newStart = clamp(gIdx - Math.round(rel * (nc - 1)), 0, t - nc)
  setRange(newStart, nc)
}

/* ---------- 底部时间轴拖拽 ---------- */
const winStyle = computed(() => ({ left: (total.value ? start.value / total.value * 100 : 0) + '%', width: (total.value ? count.value / total.value * 100 : 0) + '%' }))
let strip = null
function stripStart(e) {
  if (!total.value) return
  const t = track.value.getBoundingClientRect()
  const mode = e.currentTarget.dataset.mode || 'move'
  let refPx
  if (mode === 'left') refPx = start.value / total.value * t.width
  else if (mode === 'right') refPx = (start.value + count.value) / total.value * t.width
  else refPx = start.value / total.value * t.width
  strip = { mode, t, refPx, sx: e.clientX, initStart: start.value, initCount: count.value }
  e.currentTarget.setPointerCapture(e.pointerId)
}
function stripMove(e) {
  if (!strip) return
  const dx = e.clientX - strip.sx
  const t = strip.t
  if (strip.mode === 'left') {
    setRange((strip.refPx + dx) / t.width * total.value, count.value)
  } else if (strip.mode === 'right') {
    const right = (strip.refPx + dx) / t.width * total.value
    setRange(strip.initStart, right - strip.initStart)
  } else {
    const shift = dx / t.width * total.value
    setRange(strip.initStart + shift, strip.initCount)
  }
}
function stripEnd(e) {
  if (strip && e.currentTarget) try { e.currentTarget.releasePointerCapture(e.pointerId) } catch (err) {}
  strip = null
}

/* ---------- 格式化 ---------- */
function fmtPrice(v) {
  if (v == null || !isFinite(v)) return ''
  if (v === Math.floor(v)) return v.toFixed(0)
  return v.toFixed(2)
}
function volTxt(v) {
  if (v == null) return '--'
  return v >= 1e8 ? (v / 1e8).toFixed(2) + '亿手' : v >= 1e4 ? (v / 1e4).toFixed(1) + '万手' : v.toFixed(0) + '手'
}
function amtTxt(v) {
  if (v == null) return '--'
  return v >= 1e8 ? (v / 1e8).toFixed(2) + '亿' : v >= 1e4 ? (v / 1e4).toFixed(1) + '万' : v.toFixed(0)
}

/* ---------- 尺寸 ---------- */
function resize() { if (box.value) { const w = box.value.clientWidth; if (w) W = w } }
let ro
onMounted(() => {
  defaultRange()
  resize()
  ro = new ResizeObserver(resize)
  ro.observe(box.value)
})
onBeforeUnmount(() => { ro && ro.disconnect() })
</script>

<style scoped>
.kc-box { position: relative; width: 100%; display: flex; flex-direction: column; }
.kc-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.kc-tabs { display: flex; gap: 6px; }
.kc-tab {
  padding: 4px 12px; border-radius: 999px; font-size: 12px; cursor: pointer;
  border: 1px solid rgba(120, 150, 150, 0.22);
  background: transparent; color: var(--lj-text-2); transition: all .2s;
}
.kc-tab.on { background: var(--lj-seal); border-color: transparent; color: var(--lj-txt-on-seal, #fff); }
.kc-hint { font-size: 11px; color: var(--lj-text-3); }

.kc-svg { width: 100%; height: auto; display: block; cursor: crosshair; touch-action: none; }

.kc-grid line { stroke: rgba(74, 95, 99, 0.10); stroke-dasharray: 2 4; }
.kc-lbl { font-size: 10px; fill: rgba(111, 138, 138, 0.75); }
.kc-prev line { stroke-dasharray: 3 3; stroke-width: 1; }
.kc-prev-txt { font-size: 10px; fill: #c7a96b; }
.kc-ref line { stroke: #e5944e; stroke-dasharray: 5 4; stroke-width: 1.2; }
.kc-ref-txt { font-size: 10px; fill: #e5944e; font-weight: 600; }
.kc-wick { stroke-linecap: round; }
.kc-body { stroke: none; }
.kc-ma { pointer-events: none; }
.kc-vol-lbl { font-size: 10px; fill: rgba(111, 138, 138, 0.7); }
.kc-date-txt { font-size: 10px; fill: rgba(111, 138, 138, 0.65); }
.kc-leg-k { font-size: 11px; fill: var(--lj-text-2, #8a9499); font-weight: 600; }
.kc-leg-t { font-size: 10px; fill: var(--lj-text-3, #9aa3a6); }
.kc-cross-line { stroke: rgba(120, 150, 150, 0.4); stroke-dasharray: 2 3; }
.kc-cross-dot { fill: #c7a96b; stroke: #fff; stroke-width: 1; }

/* 底部时间轴 */
.kc-strip { margin-top: 12px; padding: 0 0 2px; }
.kc-strip-track { position: relative; height: 18px; border-radius: 9px; background: rgba(120, 150, 150, 0.14); }
.kc-strip-window { position: absolute; top: 0; height: 18px; border-radius: 9px; background: rgba(199, 169, 107, 0.35); cursor: grab; }
.kc-strip-window:active { cursor: grabbing; }
.kc-thumb { position: absolute; top: -3px; width: 9px; height: 24px; border-radius: 5px; background: #c7a96b; cursor: ew-resize; box-shadow: 0 2px 6px rgba(0,0,0,.3); }
.kc-thumb.left { left: -3px; }
.kc-thumb.right { right: -3px; }
.kc-strip-meta { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; font-size: 11px; color: var(--lj-text-3); }
.kc-reset { border: none; background: none; color: var(--lj-seal); cursor: pointer; font-size: 11px; }

.kc-tip {
  position: absolute; padding: 8px 11px; border-radius: 10px;
  background: rgba(11, 15, 20, 0.86);
  -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
  border: 1px solid rgba(199, 169, 107, 0.22);
  color: #dbe4e2; font-size: 11.5px; line-height: 1.5; z-index: 3; min-width: 210px; pointer-events: none;
}
.kc-tip.right { left: 12px; }
.kc-tip.left { right: 12px; }
.kc-tip-date { color: #c7a96b; margin-bottom: 3px; letter-spacing: .02em; }
.kc-tip-row { display: flex; justify-content: space-between; gap: 12px; color: rgba(219, 228, 226, 0.55); }
.kc-tip-row b { font-weight: 600; color: #e8eef0; font-variant-numeric: tabular-nums; }
.kc-tip-meta { margin-top: 3px; color: rgba(219, 228, 226, 0.55); font-size: 10.5px; }
.kc-tip .up { color: #d8504f; }
.kc-tip .down { color: #3f968e; }
</style>
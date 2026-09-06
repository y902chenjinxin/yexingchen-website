<template>
  <div class="tm-map" ref="wrap" :style="{ cursor: drag ? 'grabbing' : 'grab' }">
    <div v-if="!geo" class="tm-loading">地图加载中…</div>
    <template v-else>
      <!-- ===== 主图 ===== -->
      <svg
        ref="svg"
        class="tm-svg"
        :viewBox="`0 0 ${W} ${H}`"
        preserveAspectRatio="xMidYMid meet"
        @pointerdown="onDown"
        @pointermove="onMove"
        @pointerup="onUp"
        @pointerleave="onUp"
        @wheel="onWheel"
        @dblclick.prevent="resetView"
      >
        <defs>
          <linearGradient id="tm-provg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#7fa8a3" stop-opacity=".72"/>
            <stop offset="1" stop-color="#4c7f7b" stop-opacity=".9"/>
          </linearGradient>
          <linearGradient id="tm-provg-hot" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#d9c8a0" stop-opacity=".95"/>
            <stop offset="1" stop-color="#c7a96b" stop-opacity="1"/>
          </linearGradient>
          <radialGradient id="tm-dotg" cx=".5" cy=".5" r=".5">
            <stop offset="0" stop-color="#c7f0ea"/>
            <stop offset="1" stop-color="#7fa8a3"/>
          </radialGradient>
          <filter id="tm-glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="3" result="b"/>
            <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        <g :transform="viewTransform">
          <!-- 省份 -->
          <g v-for="p in provinces" :key="p.name">
            <path
              class="tm-prov"
              :class="{
                visited: p.visited,
                dim: isDim(p.name),
                on: p.name === activeProvince
              }"
              :d="p.d"
              :fill="fillFor(p)"
              :data-prov="p.name"
              :ref="setProvEl"
              @mouseenter="onProvHover($event, p)"
              @mouseleave="onProvLeave"
            >
              <title>{{ p.name }}{{ p.count ? ` · ${p.count} 次足迹` : '' }}</title>
            </path>
          </g>
          <!-- 九段线 / 南海主体内 -->
          <path v-if="jdD" class="tm-prov jd" :d="jdD" fill="none" stroke="rgba(127,168,163,.35)" stroke-width="1"/>

          <!-- 同程连线（辉光先、核心后） -->
          <template v-for="l in tripLines" :key="l.id">
            <path class="tm-line-glow" :class="{ on: activeTripId === l.id }" :d="l.d"/>
            <path class="tm-line" :class="{ on: activeTripId === l.id }" :d="l.d"/>
          </template>

          <!-- 城市打点 -->
          <g v-for="pt in dots" :key="pt.key">
            <circle
              class="tm-dot"
              :class="{ on: pt.tripId === activeTripId, pulse: pt.tripId === activeTripId }"
              :cx="pt.x" :cy="pt.y"
              :r="pt.r"
              :data-city="pt.city"
              :data-trip="pt.tripId"
              @mouseenter="onDotHover($event, pt)"
              @mouseleave="onDotLeave"
            >
              <title>{{ pt.city }} · {{ pt.tripTitle }}</title>
            </circle>
          </g>
        </g>
      </svg>

      <!-- 南海诸岛 mini-map（右下角玻璃窗） -->
      <div class="tm-mini" :aria-hidden="true" :style="{ transform: `translate(-12px,-12px) scale(${view.s})` }">
        <svg :viewBox="`0 0 ${mW} ${mH}`" class="tm-mini-svg">
          <path v-for="d in miniD" :key="d" :d="d" fill="none" stroke="rgba(127,168,163,.6)" stroke-width="1"/>
        </svg>
      </div>

      <!-- 图例 -->
      <div class="tm-legend">
        <span class="tl-k"><i class="tl-sq on"></i>足迹省份</span>
        <span class="tl-k"><i class="tl-sq"></i>未去过</span>
        <span class="tl-k"><i class="tl-dot"></i>城市足迹</span>
        <span class="tl-k"><i class="tl-line-ic"></i>行程连线</span>
      </div>

      <!-- 省份筛选 chip -->
      <div v-if="drillProvince" class="tm-chip">
        <span>已聚焦「{{ drillProvince }}」</span>
        <button type="button" @click.stop="emit('province-click', null)">✕ 清除</button>
      </div>
      <div v-else-if="!isFit" class="tm-chip ghost">
        <span>拖动平移 · 滚轮缩放 · 双击复位</span>
      </div>

      <!-- 玻璃浮卡：省份 hover -->
      <div v-if="hoverProv" class="tm-card glass" :style="cardStyle">
        <div class="tc-title">{{ hoverProv.name }}</div>
        <div class="tc-line">
          <span class="tc-badge">{{ hoverProv.count || 0 }} 次足迹</span>
          <span class="tc-cities">{{ hoverProv.cities }}</span>
        </div>
      </div>

      <!-- 玻璃浮卡：城市 hover 汇总 -->
      <div v-if="hoverCity" class="tm-card glass" :style="cardStyle">
        <div class="tc-title">{{ hoverCity.city }}</div>
        <div class="tc-list">
          <button v-for="t in hoverCity.trips" :key="t" type="button" class="tc-trip" @click="activateTrip(t)">
            <i></i>{{ tripTitle(t) }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  points: { type: Array, default: () => [] },
  activeTripId: { type: Number, default: null },
  activeProvince: { type: String, default: null },
  drillProvince: { type: String, default: '' },
  legend: { type: Boolean, default: true },
  travels: { type: Array, default: () => [] }
})
const emit = defineEmits(['point-click', 'province-click'])

const wrap = ref(null)
const svg = ref(null)
const geo = ref(null)
fetch('/geo/china.json').then((r) => r.json()).then((d) => { geo.value = d }).catch(() => {})

const reduced = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const W = ref(600)
const H = ref(540)
let K = 1
let minLon = 73, maxLon = 135, minLat = 18, maxLat = 54
function project(lon, lat) { return [(lon - minLon) * K, (maxLat - lat) * 1] }
function buildD(ringsList) {
  const rings = ringsList.flat()
  return rings.map((ring) => ring.map(([lo, la], i) => {
    const [x, y] = project(lo, la)
    return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1)
  }).join(' ') + ' Z').join(' ')
}

/* ---------- 视口：缩放/平移 ---------- */
const view = reactive({ tx: 0, ty: 0, s: 1 })
const isFit = computed(() => Math.abs(view.s - 1) < 1e-4 && Math.abs(view.tx) < .5 && Math.abs(view.ty) < .5)
const viewTransform = computed(() => `translate(${view.tx} ${view.ty}) scale(${view.s})`)

const drag = ref(false)
let moved = false, pStart = null, pressTarget = null, pressDot = null
const provEls = new Map()
function setProvEl(el) {
  if (el) provEls.set(el.getAttribute('data-prov'), el)
}
function onDown(e) {
  drag.value = true; moved = false; pStart = { x: e.clientX, y: e.clientY }
  pressTarget = e.target
  pressDot = null
  if (pressTarget.getAttribute && pressTarget.getAttribute('data-city')) {
    const r = pressTarget.getBoundingClientRect()
    pressDot = { x: r.left + r.width / 2, y: r.top + r.height / 2, radius: Math.max(r.width, r.height) / 2 }
  }
  try { svg.value.setPointerCapture && svg.value.setPointerCapture(e.pointerId) } catch (_) { /* 合成/异常指针忽略 */ }
}
function onMove(e) {
  if (!drag.value) return
  const dx = e.clientX - pStart.x, dy = e.clientY - pStart.y
  if (Math.abs(dx) + Math.abs(dy) > 5) moved = true
  if (moved) { applyPan(dx, dy); pStart = { x: e.clientX, y: e.clientY }; pressTarget = null; pressDot = null }
}
function onUp(e) {
  if (!drag.value) return
  drag.value = false
  if (moved || !pressTarget || pressTarget === svg.value) return
  if (pressDot) {
    // 点击落在打点有效半径（中心 75%）内才视为激活行程，否则穿透为省份下钻
    const dx = e.clientX - pressDot.x, dy = e.clientY - pressDot.y
    const within = Math.hypot(dx, dy) <= pressDot.radius * 0.75
    if (within) {
      const trip = Number(pressTarget.getAttribute('data-trip'))
      if (!Number.isNaN(trip)) emit('point-click', trip)
    } else {
      const prov = provinceAt(e.clientX, e.clientY)
      if (prov) emit('province-click', prov)
    }
    return
  }
  const prov = pressTarget.getAttribute && pressTarget.getAttribute('data-prov')
  if (prov) emit('province-click', prov)
}
function provinceAt(clientX, clientY) {
  if (!svg.value) return null
  const pt = svg.value.createSVGPoint ? svg.value.createSVGPoint() : null
  if (!pt) return null
  pt.x = clientX; pt.y = clientY
  const p = pt.matrixTransform(svg.value.getScreenCTM().inverse())
  for (const [name, el] of provEls) {
    if (el && el.isPointInFill && el.isPointInFill(p)) return name
  }
  return null
}
function applyPan(dx, dy) {
  const m = svg.value.getCTM().inverse()
  const dxBB = m.a * dx + m.c * dy
  const dyBB = m.b * dx + m.d * dy
  view.tx += dxBB
  view.ty += dyBB
}
function onWheel(e) {
  e.preventDefault()
  const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15
  zoomAt(e.clientX, e.clientY, factor)
}
function zoomAt(clientX, clientY, factor) {
  const s2 = clamp(view.s * factor, 1, 14)
  const f = s2 / view.s
  const pt = toContent(clientX, clientY)
  if (!pt) return
  view.tx = pt.mx - pt.cx * s2
  view.ty = pt.my - pt.cy * s2
  view.s = s2
}
// client -> viewBox 基坐标
function toBase(clientX, clientY) {
  const ctm = svg.value.getCTM().inverse()
  return { x: ctm.a * clientX + ctm.b * clientY + ctm.e, y: ctm.d * clientY + ctm.c * clientX + ctm.f }
}
function toContent(clientX, clientY) {
  const b = toBase(clientX, clientY)
  return { mx: b.x, my: b.y, cx: (b.x - view.tx) / view.s, cy: (b.y - view.ty) / view.s }
}
function resetView() {
  view.tx = 0; view.ty = 0; view.s = 1
  emit('province-click', null)
}

let rafId = null
function flyTo(target) {
  if (reduced || !target) { applyView(target); return }
  cancelAnimationFrame(rafId)
  const st = { tx: view.tx, ty: view.ty, s: view.s }
  const t0 = performance.now(), dur = 420
  const ease = (t) => 1 - Math.pow(1 - t, 3)
  const step = (now) => {
    const p = Math.min(1, (now - t0) / dur), k = ease(p)
    view.tx = st.tx + (target.tx - st.tx) * k
    view.ty = st.ty + (target.ty - st.ty) * k
    view.s = st.s + (target.s - st.s) * k
    if (p < 1) rafId = requestAnimationFrame(step)
  }
  rafId = requestAnimationFrame(step)
}
function applyView(v) { if (v) { view.tx = v.tx; view.ty = v.ty; view.s = v.s } }

// 监听激活行程 → fly-to 聚焦该行程城市包围盒
watch(() => props.activeTripId, (id) => {
  if (id == null) { resetView(); return }
  const pts = dotsAll.value.filter((p) => p.tripId === id)
  if (!pts.length) { resetView(); return }
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9
  for (const p of pts) { if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x; if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y }
  const bw = maxX - minX || 20, bh = maxY - minY || 20
  const s = clamp(Math.min(W.value / (bw * 1.5), H.value / (bh * 1.5)), 1, 10)
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2
  flyTo({ tx: W.value / 2 - s * cx, ty: H.value / 2 - s * cy, s })
})

/* ---------- 数据 ---------- */
const provinces = computed(() => {
  if (!geo.value) return []
  const bnd = geo.value.bound
  minLon = bnd[0]; minLat = bnd[1]; maxLon = bnd[2]; maxLat = bnd[3]
  const mid = (minLat + maxLat) / 2 * Math.PI / 180
  K = Math.cos(mid)
  W.value = (maxLon - minLon) * K
  H.value = (maxLat - minLat)
  const byProv = {}
  for (const pt of props.points) { if (pt.province) byProv[pt.province] = (byProv[pt.province] || 0) + 1 }
  const citiesByProv = {}
  for (const pt of props.points) {
    if (!pt.province) continue
    ;(citiesByProv[pt.province] = citiesByProv[pt.province] || new Set()).add(pt.city)
  }
  return (geo.value.provinces || []).map((p) => {
    const count = byProv[p.name] || 0
    return { name: p.name, d: buildD(p.rings), visited: !!count, count,
             cities: [...(citiesByProv[p.name] || [])].join(' · ') }
  })
})

function fillFor(p) {
  if (p.on || p.name === props.activeProvince) return 'url(#tm-provg-hot)'
  if (p.visited) return 'url(#tm-provg)'
  return 'none'
}
function isDim(pname) {
  if (!props.drillProvince) return false
  return pname !== props.drillProvince
}

const jdD = computed(() => (geo.value && geo.value.jd.length ? buildD(geo.value.jd) : ''))
const dotsAll = computed(() => {
  if (!geo.value) return []
  const cityCount = {}
  for (const p of props.points) { if (p.city) cityCount[p.city] = (cityCount[p.city] || 0) + 1 }
  return props.points.filter((p) => p.lon != null && p.lat != null).map((p) => {
    const [x, y] = project(p.lon, p.lat)
    const cnt = cityCount[p.city] || 1
    return {
      key: p.tripId + ':' + p.seq, tripId: p.tripId, seq: p.seq, city: p.city,
      tripTitle: p.tripTitle || '', x, y,
      r: cnt >= 3 ? 4.6 : cnt === 2 ? 3.9 : 3.1
    }
  })
})
const dots = computed(() => {
  const dr = props.drillProvince
  return dotsAll.value.filter((p) => {
    if (!dr) return true
    const t = props.travels.find((x) => x.id === p.tripId)
    return t && t.cities && t.cities.some((c) => c.province === dr)
  })
})
const tripLines = computed(() => {
  if (!geo.value) return []
  const dr = props.drillProvince
  const groups = {}
  for (const p of props.points) {
    if (p.lon == null || p.lat == null) continue
    if (dr) {
      const t = props.travels.find((x) => x.id === p.tripId)
      if (!(t && t.cities && t.cities.some((c) => c.province === dr))) continue
    }
    (groups[p.tripId] = groups[p.tripId] || []).push({ seq: p.seq, lon: p.lon, lat: p.lat })
  }
  const lines = []
  for (const [id, arr] of Object.entries(groups)) {
    arr.sort((a, b) => a.seq - b.seq)
    if (arr.length < 2) continue
    const pts = arr.map((c) => project(c.lon, c.lat))
    lines.push({ id: Number(id), d: smoothD(pts) })
  }
  return lines
})
function smoothD(pts) {
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i], b = pts[i + 1], mx = ((a[0] + b[0]) / 2).toFixed(1), my = ((a[1] + b[1]) / 2).toFixed(1)
    d += ` Q${a[0].toFixed(1)} ${a[1].toFixed(1)} ${mx} ${my}`
  }
  const l = pts[pts.length - 1]
  d += ` L${l[0].toFixed(1)} ${l[1].toFixed(1)}`
  return d
}

/* ---------- 南海 mini-map ---------- */
const mW = 96, mH = 84
const MINI = { minLon: 108, maxLon: 124, minLat: 2, maxLat: 28 }
const miniD = computed(() => {
  if (!geo.value || !geo.value.jd.length) return []
  const mproj = (lo, la) => [((lo - MINI.minLon) / (MINI.maxLon - MINI.minLon)) * mW, ((MINI.maxLat - la) / (MINI.maxLat - MINI.minLat)) * mH]
  return geo.value.jd.map((rings) => rings.map((ring) => ring.map(([lo, la], i) => {
    const [x, y] = mproj(lo, la)
    return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1)
  }).join(' ') + ' Z').join(' '))
})

/* ---------- Hover 浮卡 ---------- */
const card = reactive({ x: 0, y: 0 })
const hoverProv = ref(null)
const hoverCity = ref(null)
const cardStyle = computed(() => ({ left: card.x + 'px', top: card.y + 'px' }))
function placeCard(e) {
  const r = wrap.value.getBoundingClientRect()
  let x = e.clientX - r.left + 14, y = e.clientY - r.top + 12
  const cw = 210, ch = 72
  if (x + cw > r.width - 8) x = e.clientX - r.left - cw - 10
  if (y + ch > r.height - 8) y = e.clientY - r.top - ch - 10
  card.x = Math.max(6, Math.min(x, r.width - cw - 6))
  card.y = Math.max(6, y)
}
function onProvHover(e, p) { placeCard(e); hoverProv.value = p }
function onProvLeave() { hoverProv.value = null }
const cityTrips = computed(() => {
  const map = {}
  for (const p of props.points) {
    if (!p.city) continue
    ;(map[p.city] = map[p.city] || []).push(p.tripId)
  }
  return map
})
function onDotHover(e, pt) {
  placeCard(e)
  hoverCity.value = { city: pt.city, trips: [...new Set(cityTrips.value[pt.city] || [])] }
}
function onDotLeave() { hoverCity.value = null }
function tripTitle(id) {
  const t = props.travels.find((x) => x.id === id)
  return t ? t.title : `行程 #${id}`
}
function activateTrip(id) { emit('point-click', id) }

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)) }

onBeforeUnmount(() => { cancelAnimationFrame(rafId) })
</script>

<style scoped>
.tm-map { position: relative; width: 100%; overflow: hidden; border-radius: 20px;
  background:
    radial-gradient(120% 90% at 20% 0%, rgba(127,168,163,.10), transparent 60%),
    radial-gradient(120% 100% at 85% 100%, rgba(199,169,107,.06), transparent 55%),
    rgba(10,15,21,.5);
  backdrop-filter: blur(2px);
}
.tm-loading { padding: 60px 0; text-align: center; color: var(--lj-text-3); font-size: 13px; }
.tm-svg { display: block; width: 100%; height: auto; user-select: none; touch-action: none; }

/* 省份 */
.tm-prov { transition: color .3s, opacity .3s, filter .25s; }
.tm-prov:not([fill*="url"]) { fill: rgba(120,135,145,.10); }
.tm-prov.visited { stroke: rgba(127,168,163,.5); stroke-width: .5; vector-effect: non-scaling-stroke; }
.tm-prov:not(.visited) { stroke: rgba(120,135,145,.5); stroke-width: .45; vector-effect: non-scaling-stroke; }
.tm-prov:hover { filter: brightness(1.45) drop-shadow(0 0 6px rgba(127,168,163,.5)); }
.tm-prov.dim { opacity: .14; filter: none; }
.tm-prov.on { filter: drop-shadow(0 0 10px rgba(199,169,107,.85)); }
.tm-prov.jd { filter: none; }

/* 连线 */
.tm-line-glow { fill: none; stroke: rgba(127,168,163,.35); stroke-width: 3.2; filter: blur(3px);
  opacity: .5; transition: opacity .3s; vector-effect: non-scaling-stroke; }
.tm-line-glow.on { opacity: .85; stroke: rgba(199,169,107,.7); }
.tm-line { fill: none; stroke: rgba(127,168,163,.85); stroke-width: 1.2; vector-effect: non-scaling-stroke;
  stroke-dasharray: 5 6; opacity: .75; transition: opacity .3s, stroke .3s; }
.tm-line.on { opacity: 1; stroke: #e4cd9a; }
.tm-line:not(.on) { animation: flow 1.1s linear infinite; }
@keyframes flow { to { stroke-dashoffset: -11; } }

/* 打点 */
.tm-dot { fill: url(#tm-dotg); stroke: rgba(255,255,255,.85); stroke-width: .6;
  cursor: pointer; transition: all .25s; vector-effect: non-scaling-stroke; }
.tm-dot:hover, .tm-dot.on { stroke-width: 1.1; filter: drop-shadow(0 0 5px rgba(199,169,107,.9)); }
.tm-dot.on { fill: #c7a96b; }
.tm-dot.pulse { animation: pulse .9s ease-out 1; }
@keyframes pulse {
  0% { r: 1.5; opacity: 1; }
  70% { opacity: .5; }
  100% { r: 10; opacity: 0; }
}

/* mini-map */
.tm-mini { position: absolute; right: 0; top: 0; z-index: 3; transform-origin: top right;
  padding: 6px; border-radius: 12px;
  background: rgba(16,22,29,.72); backdrop-filter: blur(8px);
  border: 1px solid rgba(127,168,163,.35); opacity: .85; transition: opacity .25s; }
.tm-mini:hover { opacity: 1; }
.tm-mini-svg { display: block; width: 96px; height: 84px; }

/* 图例 */
.tm-legend { position: absolute; left: 12px; bottom: 10px; z-index: 3; display: flex; flex-wrap: wrap; gap: 12px;
  padding: 7px 14px; border-radius: 999px;
  background: rgba(16,22,29,.72); -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
  border: 1px solid rgba(127,168,163,.3); font-size: 11px; color: var(--lj-text-2); }
.tl-k { display: inline-flex; align-items: center; gap: 5px; }
.tl-sq { width: 10px; height: 10px; border-radius: 3px; background: rgba(120,135,145,.16); border: 1px solid rgba(127,168,163,.5); }
.tl-sq.on { background: rgba(127,168,163,.7); box-shadow: 0 0 5px rgba(127,168,163,.7); }
.tl-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--lj-dai, #7FA8A3); box-shadow: 0 0 4px var(--lj-dai, #7FA8A3); }
.tl-line-ic { width: 16px; height: 3px; border-radius: 2px;
  background: linear-gradient(90deg, transparent, rgba(127,168,163,.9), transparent); }

/* 筛选 chip */
.tm-chip { position: absolute; right: 120px; bottom: 14px; z-index: 3; display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 12px; border-radius: 999px; font-size: 11px;
  background: rgba(199,169,107,.16); color: #d9c8a0; border: 1px solid rgba(199,169,107,.5); }
.tm-chip.ghost { background: rgba(16,22,29,.55); color: var(--lj-text-3); border-color: rgba(120,135,145,.4); }
.tm-chip button { border: none; background: none; color: inherit; cursor: pointer; font-size: 11px; padding: 0; }

/* 玻璃浮卡 */
.tm-card { position: absolute; z-index: 5; width: 210px; padding: 10px 12px; border-radius: 14px; pointer-events: auto;
  background: rgba(16,22,29,.82); -webkit-backdrop-filter: blur(14px) saturate(160%); backdrop-filter: blur(14px) saturate(160%);
  border: 1px solid rgba(127,168,163,.4); color: var(--lj-text); box-shadow: 0 12px 30px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.08);
  animation: fadeIn .18s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.tc-title { font-size: 13px; font-weight: 600; color: #e4cd9a; margin-bottom: 4px; }
.tc-line { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--lj-text-2); flex-wrap: wrap; }
.tc-cities { opacity: .85; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.tc-badge { color: #7fa8a3; }
.tc-list { display: flex; flex-direction: column; gap: 5px; }
.tc-trip { display: flex; align-items: center; gap: 6px; color: var(--lj-text-2); font-size: 12px; cursor: pointer;
  background: none; border: none; padding: 3px 2px; text-align: left; border-radius: 6px; }
.tc-trip:hover { color: #e4cd9a; background: rgba(127,168,163,.12); }
.tc-trip i { width: 5px; height: 5px; border-radius: 50%; background: var(--lj-ochre, #C7A96B); flex: none; }

@media (prefers-reduced-motion: reduce) {
  .tm-line:not(.on), .tm-dot.pulse { animation: none; }
  .tm-card { animation: none; }
}
</style>
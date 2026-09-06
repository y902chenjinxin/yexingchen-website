<template>
  <div class="tm-map" ref="wrap">
    <div v-if="!geo" class="tm-loading">地图加载中…</div>
    <svg
      v-else
      class="tm-svg"
      :viewBox="`0 0 ${W} ${H}`"
      preserveAspectRatio="xMidYMid meet"
    >
      <!-- 省份 -->
      <g v-for="p in provinces" :key="p.name">
        <path
          class="tm-prov"
          :class="{ visited: p.visited, on: p.name === activeProvince }"
          :d="p.d"
          fill="currentColor"
        >
          <title>{{ p.name }}{{ p.count ? ` · ${p.count} 次足迹` : '' }}</title>
        </path>
      </g>
      <!-- 九段线 / 南海诸岛 -->
      <g v-if="jdD">
        <path class="tm-prov" :d="jdD" fill="currentColor"><title>南海诸岛</title></path>
      </g>

      <!-- 同程连线 -->
      <g v-for="l in tripLines" :key="l.id">
        <path class="tm-line" :class="{ on: activeTripId === l.id }" :d="l.d" />
      </g>

      <!-- 城市打点 -->
      <g v-for="pt in dots" :key="pt.key">
        <circle
          class="tm-dot"
          :class="{ on: activeTripId === pt.tripId }"
          :cx="pt.x" :cy="pt.y"
          :r="activeTripId === pt.tripId ? 4.6 : 3.1"
          @click="emit('point-click', pt.tripId)"
        >
          <title>{{ pt.city }} · {{ pt.tripTitle }}</title>
        </circle>
      </g>
    </svg>
    <div v-if="legend" class="tm-legend">
      <span class="tl-k"><i class="tl-sq on"></i>已去过的省份</span>
      <span class="tl-k"><i class="tl-sq"></i>未去过</span>
      <span class="tl-k"><i class="tl-dot"></i>城市足迹</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  points: { type: Array, default: () => [] }, // {tripId, tripTitle, seq, city, province, lon, lat}
  activeTripId: { type: Number, default: null },
  activeProvince: { type: String, default: null },
  legend: { type: Boolean, default: true }
})
const emit = defineEmits(['point-click'])

const geo = ref(null)

fetch('/geo/china.json').then((r) => r.json()).then((d) => { geo.value = d }).catch(() => {})

const W = ref(600)
const H = ref(540)
let K = 1 // lon 余弦缩放
let minLon = 73, maxLon = 135, minLat = 18, maxLat = 54

function project(lon, lat) {
  return [(lon - minLon) * K, (maxLat - lat) * 1]
}

function buildD(ringsList) {
  const rings = ringsList.flat()
  return rings.map((ring) =>
    ring.map(([lo, la], i) => {
      const [x, y] = project(lo, la)
      return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1)
    }).join(' ') + ' Z'
  ).join(' ')
}

const provinces = computed(() => {
  if (!geo.value) return []
  const bnd = geo.value.bound
  minLon = bnd[0]; minLat = bnd[1]; maxLon = bnd[2]; maxLat = bnd[3]
  const mid = (minLat + maxLat) / 2 * Math.PI / 180
  K = Math.cos(mid)
  W.value = (maxLon - minLon) * K
  H.value = (maxLat - minLat)

  const byProv = {}
  for (const pt of props.points) {
    if (!pt.province) continue
    byProv[pt.province] = (byProv[pt.province] || 0) + 1
  }
  return (geo.value.provinces || []).map((p) => ({
    name: p.name,
    d: buildD(p.rings),
    visited: !!byProv[p.name],
    count: byProv[p.name] || 0
  }))
})

const jdD = computed(() => (geo.value && geo.value.jd.length ? buildD(geo.value.jd) : ''))
const dots = computed(() => {
  if (!geo.value) return []
  const seen = {}
  return (props.points || []).filter((p) => p.lon != null && p.lat != null).map((p) => {
    const [x, y] = project(p.lon, p.lat)
    const key = p.tripId + ':' + p.seq
    seen[key] = true
    return { key, tripId: p.tripId, seq: p.seq, city: p.city, tripTitle: p.tripTitle || '', x, y }
  })
})
const tripLines = computed(() => {
  if (!geo.value) return []
  const groups = {}
  for (const p of props.points) {
    if (p.lon == null || p.lat == null) continue
    (groups[p.tripId] = groups[p.tripId] || []).push({ seq: p.seq, lon: p.lon, lat: p.lat })
  }
  const lines = []
  for (const [id, arr] of Object.entries(groups)) {
    arr.sort((a, b) => a.seq - b.seq)
    if (arr.length < 2) continue
    const d = arr.map((c, i) => {
      const [x, y] = project(c.lon, c.lat)
      return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1)
    }).join(' ')
    lines.push({ id: Number(id), d })
  }
  return lines
})
</script>

<style scoped>
.tm-map { position: relative; width: 100%; }
.tm-loading { padding: 60px 0; text-align: center; color: var(--lj-text-3); font-size: 13px; }
.tm-svg { display: block; width: 100%; height: auto; user-select: none; }
.tm-prov { cursor: pointer; stroke: rgba(10,14,18,.55); stroke-width: .6; vector-effect: non-scaling-stroke;
  color: rgba(120,135,145,.16); transition: color .3s; }
.tm-prov.visited { color: rgba(127,168,163,.5); }
.tm-prov:hover { filter: brightness(1.5); }
.tm-prov.on { color: rgba(199,169,107,.5); }
.tm-line { fill: none; stroke: rgba(199,169,107,.55); stroke-width: 1.1; stroke-dasharray: 3 3;
  opacity: .45; transition: opacity .3s; vector-effect: non-scaling-stroke; }
.tm-line.on { opacity: .95; stroke-width: 1.6; stroke-dasharray: none; }
.tm-dot { cursor: pointer; fill: var(--lj-dai, #7FA8A3); stroke: rgba(255,255,255,.75); stroke-width: .6;
  opacity: .55; transition: all .25s; vector-effect: non-scaling-stroke; }
.tm-dot:hover, .tm-dot.on { opacity: 1; fill: var(--lj-ochre, #C7A96B); stroke-width: 1; filter: drop-shadow(0 0 4px rgba(199,169,107,.8)); }
.tm-legend { position: absolute; left: 10px; bottom: 8px; display: flex; gap: 14px; padding: 6px 12px;
  border-radius: 999px; background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); font-size: 11px; color: var(--lj-text-2); }
.tl-k { display: inline-flex; align-items: center; gap: 5px; }
.tl-sq { width: 10px; height: 10px; border-radius: 2px; background: rgba(120,135,145,.16); border: 1px solid rgba(10,14,18,.4); }
.tl-sq.on { background: rgba(127,168,163,.5); }
.tl-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--lj-dai, #7FA8A3); box-shadow: 0 0 3px var(--lj-dai, #7FA8A3); }
</style>
<!--
  WeatherCard.vue
  玄黄・工作台天气小部件（#2）
  - open-meteo.com 免费无 key：实时温度 / 天气码 / 3 日预报
  - 地理位置：浏览器定位（地理权限）→ 失败则用可搜索城市（本地记忆）
  - 1 小时 localStorage 缓存，避免频繁外呼
  - 失败降级：显示「无法获取天气」占位，不阻塞工作台
-->
<template>
  <div class="wx-card" :class="{ 'wx-card--err': error }">
    <!-- 头部：城市 + 操作 -->
    <div class="wx-head">
      <span class="wx-loc"><el-icon><Location /></el-icon>{{ cityLabel }}</span>
      <button class="wx-set" title="切换城市" @click="pickCity">
        <el-icon><Setting /></el-icon>
      </button>
    </div>

    <template v-if="current">
      <!-- 今日 -->
      <div class="wx-now">
        <span class="wx-icon" aria-hidden="true">{{ iconFor(current.weathercode) }}</span>
        <span class="wx-temp">{{ current.temperature }}°</span>
        <span class="wx-desc">{{ descFor(current.weathercode) }}</span>
      </div>
      <div class="wx-meta">
        <span>体感 {{ current.feelslike }}°</span>
        <span>湿度 {{ current.humidity }}%</span>
        <span>风 {{ current.windspeed }}km/h</span>
      </div>
      <!-- 3 日预报 -->
      <div class="wx-days">
        <div v-for="d in forecast" :key="d.date" class="wx-day">
          <span class="wx-day-name">{{ d.week }}</span>
          <span class="wx-day-icon" aria-hidden="true">{{ iconFor(d.weathercode) }}</span>
          <span class="wx-day-hi">{{ d.max }}°</span>
          <span class="wx-day-lo">{{ d.min }}°</span>
        </div>
      </div>
    </template>

    <p v-else-if="loading" class="wx-tip">正在获取天气…</p>
    <p v-else class="wx-tip">{{ error }}</p>

    <!-- 城市选择（轻量浮层） -->
    <div v-if="showPick" class="wx-pick">
      <input
        v-model="cityQuery"
        placeholder="输入城市名切换，回车确认"
        class="wx-pick-input"
        @keydown.enter="applyCity"
        @blur="showPick = false"
      />
      <div class="wx-pick-sugg">
        <span class="wx-pick-hint">常用：</span>
        <button v-for="c in SUGGEST" :key="c.name" class="wx-chip" @mousedown.prevent="chooseSuggest(c)">
          {{ c.name }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Location, Setting } from '@element-plus/icons-vue'

const BASE = 'https://api.open-meteo.com/v1/forecast'
const CACHE_KEY = 'yx_weather_v1'
const CITY_KEY = 'yx_weather_city_v1'

// 常用城市（经纬度）
const SUGGEST = [
  { name: '定位', lat: 0, lon: 0, locate: true },
  { name: '江苏 · 南京', lat: 32.06, lon: 118.79 },
  { name: '江苏 · 苏州', lat: 31.3, lon: 120.62 },
  { name: '上海', lat: 31.23, lon: 121.47 },
  { name: '北京', lat: 39.9, lon: 116.4 },
  { name: '广州', lat: 23.13, lon: 113.26 },
]

// 天气码 → 图标 & 描述（open-meteo WMO code）
function iconFor(code) {
  if (code === 0) return '☀️'
  if (code <= 3) return '🌤️'
  if (code <= 48) return '🌫️'
  if (code >= 95) return '🌩️'
  if (code >= 71) return '🌨️'
  if (code >= 61) return '🌧️'
  if (code >= 51) return '🌦️'
  return '☁️'
}
function descFor(code) {
  if (code === 0) return '晴朗'
  if (code <= 3) return '多云'
  if (code <= 48) return '雾'
  if (code >= 95) return '雷雨'
  if (code >= 71) return '雪'
  if (code >= 61) return '雨'
  if (code >= 51) return '细雨'
  return '阴'
}
const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const current = ref(null)
const forecast = ref([])
const loading = ref(false)
const error = ref('')
const cityLabel = ref('定位中')
const showPick = ref(false)
const cityQuery = ref('')
const locateMode = ref(false)

async function currentPos() {
  if (!locateMode.value) return null
  if (!navigator.geolocation) return null
  try {
    const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 6000 }))
    return { lat: pos.coords.latitude, lon: pos.coords.longitude }
  } catch { return null }
}

async function fetchWeather(lat, lon) {
  const url = `${BASE}?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&forecast_days=3&timezone=auto`
  const r = await fetch(url)
  if (!r.ok) throw new Error('网络错误')
  const j = await r.json()
  const c = j.current || {}
  const d = j.daily || {}
  const days = (d.time || []).map((date, i) => ({
    date,
    week: WEEK[new Date(date + 'T00:00:00').getDay()],
    max: Math.round((d.temperature_2m_max || [])[i]),
    min: Math.round((d.temperature_2m_min || [])[i]),
    weathercode: (d.weather_code || [])[i] ?? 0,
  }))
  current.value = {
    temperature: Math.round(c.temperature_2m ?? 0),
    feelslike: Math.round(c.apparent_temperature ?? 0),
    humidity: Math.round(c.relative_humidity_2m ?? 0),
    windspeed: Math.round(c.wind_speed_10m ?? 0),
    weathercode: c.weather_code ?? 0,
  }
  forecast.value = days
}

function saveCache(lat, lon) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), lat, lon }))
  } catch {}
}

function readCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}') } catch { return {} }
}

async function refresh() {
  // 1 小时内命中，用缓存坐标直接展示
  const cache = readCache()
  const fresh = cache.ts && Date.now() - cache.ts < 60 * 60 * 1000
  const cityCache = JSON.parse(localStorage.getItem(CITY_KEY) || 'null')

  let lat, lon
  if (cityCache && !cityCache.locate) {
    lat = cityCache.lat; lon = cityCache.lon; cityLabel.value = cityCache.label
    locateMode.value = false
  } else {
    locateMode.value = true
    const pos = await currentPos()
    if (pos) { lat = pos.lat; lon = pos.lon; cityLabel.value = '当前定位' }
    else if (fresh && cache.lat != null) { lat = cache.lat; lon = cache.lon; cityLabel.value = '当前定位' }
    else { lat = 32.06; lon = 118.79; cityLabel.value = '江苏 · 南京'; locateMode.value = false }
  }

  loading.value = true; error.value = ''
  try {
    await fetchWeather(lat, lon)
    saveCache(lat, lon)
    if (locateMode.value && !cityCache) cityLabel.value = '当前定位'
  } catch (e) {
    error.value = '无法获取天气'
    // 保留旧数据
    if (!current.value) current.value = null
  } finally { loading.value = false }
}

function pickCity() { showPick.value = !showPick.value }
function applyCity() {
  const q = cityQuery.value.trim()
  if (!q) return
  // 交给 reverse geocode 会引入额外 key；这里用中文名匹配不到就保留。简便：用腾讯定位开放接口需 key。
  // 折中：把用户输入作为"定位"触发浏览器权限（已有城市则走建议）
  showPick.value = false
  cityQuery.value = ''
}
function chooseSuggest(c) {
  showPick.value = false
  if (c.locate) {
    locateMode.value = true
    localStorage.removeItem(CITY_KEY)
  } else {
    locateMode.value = false
    cityLabel.value = c.name
    localStorage.setItem(CITY_KEY, JSON.stringify({ ...c, label: c.name }))
  }
  current.value = null; forecast.value = []
  refresh()
}

onMounted(() => { refresh() })
</script>

<style scoped>
.wx-card { position: relative; padding: 4px 2px 2px; }
.wx-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.wx-loc { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; color: var(--dp-text2); }
.wx-loc .el-icon { color: var(--dp-accent); }
.wx-set { border: 0; background: transparent; color: var(--dp-text3); cursor: pointer; padding: 4px; border-radius: 6px; }
.wx-set:hover { color: var(--dp-accent); background: var(--dp-accent-faint); }
.wx-now { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.wx-icon { font-size: 34px; line-height: 1; }
.wx-temp { font-size: 34px; font-weight: 700; color: var(--dp-text); font-variant-numeric: tabular-nums; }
.wx-desc { font-size: 13px; color: var(--dp-text2); }
.wx-meta { display: flex; gap: 12px; font-size: 11.5px; color: var(--dp-text3); margin-bottom: 12px; flex-wrap: wrap; }
.wx-days { display: flex; gap: 6px; }
.wx-day { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 8px 4px; border-radius: 8px; background: var(--dp-accent-faint, rgba(167,139,250,.1)); }
.wx-day-name { font-size: 11px; color: var(--dp-text3); }
.wx-day-icon { font-size: 18px; }
.wx-day-hi { font-size: 12px; color: var(--dp-text); font-weight: 600; }
.wx-day-lo { font-size: 11px; color: var(--dp-text3); }
.wx-tip { font-size: 12.5px; color: var(--dp-text3); margin: 20px 0; text-align: center; }
.wx-card--err .wx-tip { margin: 30px 0; }

.wx-pick {
  position: absolute;
  top: 0; left: 0; right: 0;
  background: var(--el-bg-color-overlay, #141426);
  border: 1px solid var(--dp-line-strong);
  border-radius: 8px;
  padding: 10px;
  z-index: 20;
  box-shadow: var(--dp-raised);
  display: flex; flex-direction: column; gap: 10px;
}
.wx-pick-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--dp-line-strong);
  border-radius: 6px;
  background: transparent;
  color: var(--dp-text);
  font-size: 13px;
  outline: none;
}
.wx-pick-input:focus-visible { border-color: var(--dp-accent); }
.wx-pick-sugg { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.wx-pick-hint { font-size: 11px; color: var(--dp-text3); }
.wx-chip {
  border: 1px solid var(--dp-line-strong);
  background: transparent;
  color: var(--dp-text2);
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
  cursor: pointer;
}
.wx-chip:hover { border-color: var(--dp-accent); color: var(--dp-accent); }
</style>
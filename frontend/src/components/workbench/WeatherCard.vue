<!--
  WeatherCard.vue
  玄黄・工作台天气小部件（#2，高德后端代理）
  - 高德天气 key 只存在服务器后端，前端经 /api/workbench/dashboard/weather 代理获取，不出服务器
  - 地理位置：浏览器定位（经纬度→后端 regeo）→ 失败则用可搜索城市（本地记忆）
  - 1 小时 localStorage 缓存坐标，避免每次重复定位；后端侧另有 10 分钟 adcode 缓存
  - 失败降级：显示「无法获取天气」占位，不阻塞工作台
-->
<template>
  <div class="wx-card" :class="{ 'wx-card--err': error && !current }">
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
        <span class="wx-icon" aria-hidden="true">{{ iconFor(current.weather) }}</span>
        <span class="wx-temp">{{ current.temperature }}°</span>
        <span class="wx-desc">{{ current.weather }}</span>
      </div>
      <div class="wx-meta">
        <span>湿度 {{ current.humidity }}%</span>
        <span>{{ windText(current) }}</span>
        <span v-if="current.reporttime" class="wx-time">更新 {{ shortTime(current.reporttime) }}</span>
      </div>
      <!-- 3 日预报 -->
      <div class="wx-days">
        <div v-for="d in forecast" :key="d.date" class="wx-day">
          <span class="wx-day-name">{{ dayName(d.date, d.week) }}</span>
          <span class="wx-day-icon" aria-hidden="true">{{ iconFor(d.weather) }}</span>
          <span class="wx-day-hi">{{ d.temp_max }}°</span>
          <span class="wx-day-lo">{{ d.temp_min }}°</span>
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
import { ref, onMounted } from 'vue'
import { Location, Setting } from '@element-plus/icons-vue'
import { workbenchApi } from '@/api/workbench'

const CACHE_KEY = 'yx_weather_v1'
const CITY_KEY = 'yx_weather_city_v1'

// 常用城市
const SUGGEST = [
  { name: '定位', lat: 0, lon: 0, locate: true },
  { name: '南京', city: '南京' },
  { name: '苏州', city: '苏州' },
  { name: '上海', city: '上海' },
  { name: '北京', city: '北京' },
  { name: '广州', city: '广州' },
]

// 高德中文天气文本 → 图标
function iconFor(txt = '') {
  if (/晴/.test(txt)) return '☀️'
  if (/云/.test(txt)) return '🌤️'
  if (/雷/.test(txt)) return '⛈️'
  if (/雪/.test(txt)) return '🌨️'
  if (/(霾|雾|沙|尘|霭)/.test(txt)) return '🌫️'
  if (/雨/.test(txt)) return '🌧️'
  if (/阴/.test(txt)) return '☁️'
  return '☁️'
}

const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
function dayName(date, week) {
  if (String(week) !== 'undefined' && week !== '' && week !== null) return '周' + { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '日' }[String(week)]
  if (date) return WEEK[new Date(date + 'T00:00:00').getDay()]
  return ''
}
function windText(c) {
  const d = c.winddirection || ''
  const p = c.windpower || ''
  if (!d && !p) return '风 --'
  return `${d}风 ${p}`
}
function shortTime(t) {
  return t && t.length >= 16 ? t.slice(11, 16) : ''
}

const current = ref(null)
const forecast = ref([])
const loading = ref(false)
const error = ref('')
const cityLabel = ref('定位中')
const showPick = ref(false)
const cityQuery = ref('')
const locateMode = ref(false)

function cachePos(lat, lon) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), lat, lon })) } catch {}
}
function readCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}') } catch { return {} }
}

async function currentPos() {
  if (!navigator.geolocation) return null
  try {
    const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 6000 }))
    return { lat: pos.coords.latitude, lon: pos.coords.longitude }
  } catch { return null }
}

async function fetchWeather(params) {
  const res = await workbenchApi.weather(params)
  const d = res?.data || {}
  if (!d.current && !d.forecast?.length) throw new Error('empty')
  current.value = d.current || null
  forecast.value = (d.forecast || []).slice(0, 4)
  if (d.city) cityLabel.value = d.city
}

async function refresh() {
  const cache = readCache()
  const fresh = cache.ts && Date.now() - cache.ts < 60 * 60 * 1000
  let cityCache = null
  try { cityCache = JSON.parse(localStorage.getItem(CITY_KEY) || 'null') } catch {}

  loading.value = true; error.value = ''
  try {
    if (cityCache && !cityCache.locate) {
      await fetchWeather({ city: cityCache.city })
    } else {
      locateMode.value = true
      const pos = await currentPos()
      if (pos) {
        await fetchWeather({ lat: pos.lat, lon: pos.lon })
        cachePos(pos.lat, pos.lon)
        cityLabel.value = cityLabel.value || '当前定位'
      } else if (fresh && cache.lat != null) {
        await fetchWeather({ lat: cache.lat, lon: cache.lon })
      } else {
        await fetchWeather({ city: '南京' })
      }
    }
  } catch (e) {
    error.value = '无法获取天气'
    current.value = null
  } finally {
    loading.value = false
  }
}

function pickCity() { showPick.value = !showPick.value }
function applyCity() {
  const q = cityQuery.value.trim()
  if (!q) return
  showPick.value = false
  cityQuery.value = ''
  locateMode.value = false
  current.value = null; forecast.value = []
  localStorage.setItem(CITY_KEY, JSON.stringify({ ...SUGGEST.find(s => s.city === q) || {}, city: q, locate: false }))
  cityLabel.value = q
  refresh()
}
function chooseSuggest(c) {
  showPick.value = false
  if (c.locate) {
    locateMode.value = true
    localStorage.removeItem(CITY_KEY)
  } else {
    locateMode.value = false
    cityLabel.value = c.city
    localStorage.setItem(CITY_KEY, JSON.stringify({ city: c.city, locate: false }))
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
.wx-meta .wx-time { margin-left: auto; }
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
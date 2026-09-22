<!--
  HistoryView.vue
  玄黄・历史上的今天 独立岛页（v2.41）
  - 顶部「横向时间轴」：可拖动游标选日期（自 1920-01-01 至今），下方事件列表同步刷新
  - 设计参考：ChronoMap 多轨时间轴 / Material Timeline / GitHub Primer 调色板
  - 下方事件按年份降序，最新事件在前
-->
<template>
  <IslandInnerBase
    type="history"
    title="历史上的今天"
    subtitle="每一天，都藏着未来的线索"
  >
    <template #toolbar>
      <button class="ht-btn ghost" @click="goToday">回到今天</button>
      <button class="ht-btn ghost" :disabled="loading" @click="load(true)">
        {{ loading ? '加载中…' : '⟳ 刷新' }}
      </button>
    </template>

    <!-- ============ 横向时间轴（可拖动选日期） ============ -->
    <section class="ht-timeline glass">
      <div class="ht-timeline-head">
        <span class="ht-tl-title">时间轴</span>
        <span class="ht-tl-tip">拖动滑块或点击月份切换日期 · 当前：{{ dateLabel }}</span>
        <span class="ht-tl-eras">
          <i class="era era-recent">2020s</i>
          <i class="era era-mill">2000s</i>
          <i class="era era-mid">1900s</i>
          <i class="era era-old">更早</i>
        </span>
      </div>

      <!-- 月份刻度条（12 个月份分格） -->
      <div class="ht-months" @click="onMonthsClick">
        <div
          v-for="m in 12"
          :key="m"
          class="ht-month"
          :class="{ active: month === m && !isToday }"
          :data-month="m"
          @click.stop="pickMonth(m)"
        >{{ m }} 月</div>
      </div>

      <!-- 滑块 + 刻度（年份区间：1920 - 今年） -->
      <div class="ht-slider-wrap">
        <input
          ref="sliderEl"
          type="range"
          class="ht-slider"
          :min="MIN_YEAR"
          :max="maxYear"
          :value="year"
          step="1"
          @input="onSliderInput"
          @change="onSliderChange"
          aria-label="选择年份"
        />
        <!-- 关键刻度文字 -->
        <div class="ht-slider-ticks" aria-hidden="true">
          <span v-for="t in yearTicks" :key="t" :style="{ left: tickLeft(t) + '%' }">{{ t }}</span>
        </div>
      </div>

      <!-- 已选日期徽章 -->
      <div class="ht-pill">
        <span class="ht-pill-d">{{ dateLabel }}</span>
        <span class="ht-pill-y">年份 {{ year }}</span>
        <span class="ht-pill-c">共 {{ items.length }} 个事件</span>
      </div>
    </section>

    <!-- ============ 事件列表（年份降序） ============ -->
    <section class="ht-events glass">
      <div v-if="loading && !items.length" class="ht-loading">
        <span class="ht-dot"></span><span class="ht-dot"></span><span class="ht-dot"></span>
      </div>
      <template v-else>
        <div v-if="!items.length" class="ht-empty">该日期暂无内置记录，试试别的月份吧</div>
        <ol v-else class="ht-list">
          <li
            v-for="(it, idx) in items"
            :key="`${it.year}-${idx}`"
            class="ht-item"
            :class="{ 'is-top': idx === 0 }"
          >
            <span class="ht-year">{{ it.year || '—' }}</span>
            <span class="ht-dot-line" aria-hidden="true"></span>
            <span class="ht-content">
              <span class="ht-title">{{ it.title }}</span>
              <span v-if="it.desc" class="ht-desc">{{ it.desc }}</span>
            </span>
          </li>
        </ol>
      </template>
    </section>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { workbenchApi } from '@/api/workbench'

const today = new Date()
const CURRENT_YEAR = today.getFullYear()
const CURRENT_MONTH = today.getMonth() + 1
const CURRENT_DAY = today.getDate()
const MIN_YEAR = 1920  // 时间轴起点
const MAX_YEAR = CURRENT_YEAR  // 时间轴终点

const year = ref(CURRENT_YEAR)
const month = ref(CURRENT_MONTH)
const day = ref(CURRENT_DAY)
const items = ref([])
const loading = ref(false)
const sliderEl = ref(null)

const maxYear = computed(() => MAX_YEAR)
const isToday = computed(() => year.value === CURRENT_YEAR && month.value === CURRENT_MONTH && day.value === CURRENT_DAY)
const dateLabel = computed(() => `${year.value} 年 ${String(month.value).padStart(2, '0')} 月 ${String(day.value).padStart(2, '0')} 日`)

/* 关键年份刻度：每 20 年一个 */
const yearTicks = computed(() => {
  const ticks = []
  for (let y = MIN_YEAR; y <= MAX_YEAR; y += 20) ticks.push(y)
  if (ticks[ticks.length - 1] !== MAX_YEAR) ticks.push(MAX_YEAR)
  return ticks
})
function tickLeft(t) {
  const span = MAX_YEAR - MIN_YEAR
  return ((t - MIN_YEAR) / span) * 100
}

/* 同一天顺序固定：年份降序（后端已排序，前端只展示） */
async function load(refresh = false) {
  loading.value = true
  try {
    const dateStr = `${year.value}-${String(month.value).padStart(2, '0')}-${String(day.value).padStart(2, '0')}`
    const res = await workbenchApi.todayInHistory(refresh ? { date: dateStr, refresh: true } : { date: dateStr })
    const data = (res && typeof res === 'object' && 'data' in res) ? res.data : (res || {})
    items.value = Array.isArray(data.items) ? data.items : []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function pickMonth(m) {
  month.value = m
  load()
}
function onMonthsClick(e) {
  // 兜底：万一 month 格没触发冒泡
  const t = e.target?.closest?.('.ht-month')
  if (!t) return
  const m = Number(t.dataset.month)
  if (m) pickMonth(m)
}
function onSliderInput(e) {
  const y = Number(e.target.value)
  if (!Number.isFinite(y)) return
  year.value = y
}
function onSliderChange() {
  // 改年份 → 重置到该年 1 月 1 日
  month.value = 1
  day.value = 1
  load()
}
function goToday() {
  year.value = CURRENT_YEAR
  month.value = CURRENT_MONTH
  day.value = CURRENT_DAY
  load()
}

onMounted(() => load())
watch([year, month, day], () => load())
</script>

<style scoped>
.ht-btn {
  border-radius: 9px; padding: 6px 12px; font-size: 12px; cursor: pointer;
  background: transparent; color: var(--dp-text); border: 1px solid var(--dp-line);
  transition: all .2s; margin-left: 8px;
}
.ht-btn:hover:not(:disabled) { color: var(--dp-accent); border-color: var(--dp-accent); }
.ht-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ============ 时间轴 ============ */
.ht-timeline {
  border-radius: 16px; padding: 18px 22px 16px; margin-bottom: 16px;
  background: var(--dp-surface); border: 1px solid var(--dp-line);
  box-shadow: var(--dp-shadow);
}
.ht-timeline-head {
  display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap;
  margin-bottom: 14px;
}
.ht-tl-title {
  font-size: 14px; font-weight: 600; color: var(--dp-text); letter-spacing: .06em;
}
.ht-tl-tip { font-size: 12px; color: var(--dp-text3); }
.ht-tl-eras {
  margin-left: auto; display: inline-flex; gap: 6px;
}
.era {
  font-style: normal; font-size: 10px; padding: 2px 8px; border-radius: 999px;
  letter-spacing: .04em; opacity: .85;
}
.era-recent { background: rgba(216, 80, 79, .12); color: #D8504F; }
.era-mill   { background: rgba(245, 158, 11, .15); color: #B45309; }
.era-mid    { background: rgba(63, 150, 142, .15); color: #2C8079; }
.era-old    { background: rgba(120, 113, 108, .15); color: #78716C; }

.ht-months {
  display: grid; grid-template-columns: repeat(12, 1fr); gap: 6px;
  margin-bottom: 14px;
}
.ht-month {
  text-align: center; font-size: 12px; padding: 8px 4px;
  border-radius: 10px; cursor: pointer; user-select: none;
  color: var(--dp-text2);
  background: rgba(255, 255, 255, .04);
  border: 1px solid transparent;
  transition: all .18s;
}
.ht-month:hover { color: var(--dp-text); background: rgba(255, 255, 255, .08); }
.ht-month.active {
  color: #fff;
  background: linear-gradient(135deg, var(--dp-accent), var(--dp-accent-strong, #5b8dee));
  border-color: transparent;
  box-shadow: 0 4px 14px rgba(91, 141, 238, .35);
}

/* 滑块：横向 + 渐变色 + 关键刻度文字 */
.ht-slider-wrap {
  position: relative;
  padding: 22px 8px 24px;
}
.ht-slider {
  width: 100%; height: 6px;
  -webkit-appearance: none; appearance: none;
  background: linear-gradient(90deg,
    rgba(120, 113, 108, .35) 0%,
    rgba(63, 150, 142, .45) 50%,
    rgba(216, 80, 79, .55) 100%);
  border-radius: 999px; outline: none; cursor: pointer;
  margin: 0;
}
.ht-slider::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 22px; height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fff, #f4f4f5);
  border: 2px solid var(--dp-accent);
  box-shadow: 0 2px 10px rgba(0, 0, 0, .25), 0 0 0 4px rgba(91, 141, 238, .15);
  cursor: grab;
  transition: transform .15s;
}
.ht-slider::-webkit-slider-thumb:hover { transform: scale(1.1); }
.ht-slider::-webkit-slider-thumb:active { cursor: grabbing; transform: scale(1.15); }
.ht-slider::-moz-range-thumb {
  width: 22px; height: 22px; border-radius: 50%;
  background: linear-gradient(135deg, #fff, #f4f4f5);
  border: 2px solid var(--dp-accent);
  box-shadow: 0 2px 10px rgba(0, 0, 0, .25), 0 0 0 4px rgba(91, 141, 238, .15);
  cursor: grab;
}
.ht-slider-ticks {
  position: absolute; left: 8px; right: 8px; bottom: 0; height: 16px; pointer-events: none;
}
.ht-slider-ticks span {
  position: absolute; transform: translateX(-50%);
  font-size: 10px; color: var(--dp-text3);
  font-variant-numeric: tabular-nums;
  top: 0;
}
.ht-slider-ticks span::before {
  content: ''; display: block; width: 1px; height: 4px;
  background: var(--dp-line); margin: 0 auto 2px;
}

.ht-pill {
  display: flex; gap: 14px; align-items: baseline; flex-wrap: wrap;
  margin-top: 8px; padding: 8px 12px;
  border-radius: 10px; background: rgba(91, 141, 238, .08);
  border: 1px dashed rgba(91, 141, 238, .25);
}
.ht-pill-d { font-size: 14px; font-weight: 600; color: var(--dp-text); }
.ht-pill-y { font-size: 12px; color: var(--dp-accent); font-variant-numeric: tabular-nums; }
.ht-pill-c { font-size: 12px; color: var(--dp-text2); margin-left: auto; }

/* ============ 事件列表 ============ */
.ht-events {
  border-radius: 16px; padding: 22px 24px 24px;
  background: var(--dp-surface); border: 1px solid var(--dp-line);
  box-shadow: var(--dp-shadow);
}
.ht-loading {
  display: flex; gap: 6px; padding: 22px 0; justify-content: center;
}
.ht-loading .ht-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--dp-accent);
  animation: ht-bounce 1s ease-in-out infinite;
}
.ht-loading .ht-dot:nth-child(2) { animation-delay: .15s; }
.ht-loading .ht-dot:nth-child(3) { animation-delay: .3s; }
@keyframes ht-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .4; }
  40% { transform: translateY(-4px); opacity: 1; }
}

.ht-empty {
  text-align: center; font-size: 13px;
  color: var(--dp-text3); padding: 28px 8px;
}

.ht-list {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 0;
  position: relative;
}
.ht-item {
  display: grid;
  grid-template-columns: 64px 1fr;
  align-items: flex-start;
  gap: 14px;
  padding: 12px 0;
  position: relative;
  border-bottom: 1px dashed var(--dp-line);
}
.ht-item:last-child { border-bottom: none; }
.ht-item.is-top .ht-title { color: var(--dp-accent); font-weight: 700; }

.ht-year {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 16px; font-weight: 700;
  color: var(--dp-accent);
  font-variant-numeric: tabular-nums;
  letter-spacing: -.01em;
  padding-top: 2px;
}
.ht-dot-line {
  position: absolute;
  left: 80px; top: 18px;
  width: 1px; height: 1px;
}
.ht-content {
  display: flex; flex-direction: column; gap: 4px;
  min-width: 0;
}
.ht-title {
  font-size: 14px; line-height: 1.55; color: var(--dp-text);
  letter-spacing: .01em;
}
.ht-desc {
  font-size: 12px; line-height: 1.6; color: var(--dp-text3);
}

/* 移动端压缩 */
@media (max-width: 768px) {
  .ht-timeline { padding: 14px 14px 12px; }
  .ht-months { gap: 4px; }
  .ht-month { font-size: 11px; padding: 6px 2px; }
  .ht-item { grid-template-columns: 50px 1fr; gap: 10px; }
  .ht-year { font-size: 14px; }
}
</style>
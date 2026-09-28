<template>
  <div class="lc-root" :class="{ dense }">
    <header class="lc-head">
      <button class="lc-nav" :title="navTitle(-1)" @click="step(-1)">‹</button>

      <div class="lc-title">
        <!-- 年月都可点：点年份进「年份快选」，点月份进「月份快选」 -->
        <template v-if="mode === 'day'">
          <button class="lc-tbtn" title="快速切换年份" @click="mode = 'year'">{{ viewYear }} 年</button>
          <button class="lc-tbtn" title="快速切换月份" @click="mode = 'month'">{{ viewMonth }} 月</button>
        </template>
        <template v-else-if="mode === 'year'">
          <button class="lc-tbtn on" title="返回日历" @click="mode = 'day'">{{ pageStart }} – {{ pageEnd }}</button>
        </template>
        <template v-else>
          <button class="lc-tbtn on" title="返回日历" @click="mode = 'day'">{{ viewYear }} 年</button>
          <span class="lc-tsub">选月份</span>
        </template>
      </div>

      <button class="lc-nav" :title="navTitle(1)" @click="step(1)">›</button>
      <button class="lc-today" @click="goToday">今天</button>
      <slot name="head-extra" />
    </header>

    <!-- 年份快选（10 年一屏，‹ › 翻十年） -->
    <div v-if="mode === 'year'" class="lc-panel lc-years">
      <button
        v-for="y in yearPage"
        :key="y"
        class="lc-ycell"
        :class="{ on: y === viewYear, now: y === thisYear }"
        @click="pickYear(y)"
      >{{ y }}</button>
    </div>

    <!-- 月份快选 -->
    <div v-else-if="mode === 'month'" class="lc-panel lc-months">
      <button
        v-for="m in 12"
        :key="m"
        class="lc-mcell"
        :class="{ on: m === viewMonth }"
        @click="pickMonth(m)"
      >{{ m }}月</button>
    </div>

    <template v-else>
      <div class="lc-week">
        <span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span>
      </div>
      <div class="lc-grid">
        <button
          v-for="(cell, i) in grid"
          :key="i"
          class="lc-cell"
          :class="cellClass(cell)"
          :disabled="!cell || !selectable"
          @click="cell && pick(cell.date)"
        >
          <template v-if="cell">
            <span class="lc-day">{{ cell.day }}</span>
            <span class="lc-sub">{{ cell.sub }}</span>
            <em v-if="cell.holiday" class="lc-flag rest">休</em>
            <em v-else-if="cell.makeup" class="lc-flag work">班</em>
          </template>
        </button>
      </div>
    </template>

    <footer class="lc-foot">
      <template v-if="selectedInfo">
        <b>{{ modelValue }}</b>
        <span v-if="selectedInfo.lunar_full">· {{ selectedInfo.lunar_full }}</span>
        <span v-if="selectedInfo.term" class="lc-tag term">{{ selectedInfo.term }}</span>
        <span v-for="f in selectedInfo.festivals" :key="f" class="lc-tag fest">{{ f }}</span>
        <span v-if="selectedInfo.holiday" class="lc-tag rest">
          假期第 {{ selectedInfo.holiday_index }}/{{ selectedInfo.holiday_days }} 天
        </span>
        <span v-else-if="selectedInfo.makeup" class="lc-tag work">补班（{{ selectedInfo.makeup }}）</span>
      </template>
      <span v-else class="lc-tip">{{ loading ? '加载中…' : hint }}</span>
      <slot name="foot-extra" />
    </footer>
  </div>
</template>

<script setup>
/** 月历核心组件（v2.40.37）——由 LunarDatePicker 与摸鱼日历共用。
 *
 * 每格显示公历 + 副标题（节日 > 节气 > 农历），法定假期标「休」、调休标「班」。
 * 数据来自 /api/lunar/month（缓存见 utils/lunarCache.js），组件只负责排版与交互。
 *
 * 头部年月均可点：**点年份直接进「年份快选」**（10 年一屏，‹ › 翻一屏），
 * 点月份进「月份快选」—— 想跳到几年前不用一月一月点。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { getMonthDays } from '@/utils/lunarCache'

const props = defineProps({
  modelValue: { type: String, default: '' },      // 'YYYY-MM-DD'
  year: { type: Number, default: 0 },             // 受控初始年（0 = 用今天）
  month: { type: Number, default: 0 },            // 受控初始月（0 = 用今天）
  selectable: { type: Boolean, default: true },   // 只读展示时传 false
  dense: { type: Boolean, default: false },       // 紧凑模式（页面内嵌用）
  hint: { type: String, default: '点日期查看农历 / 节气 / 放假信息' },
})
const emit = defineEmits(['update:modelValue', 'update:year', 'update:month', 'pick', 'month-change'])

const MIN_YEAR = 1900
const MAX_YEAR = 2099
const YEARS_PER_PAGE = 10

const today = new Date()
const thisYear = today.getFullYear()
const pad = (n) => String(n).padStart(2, '0')
const todayStr = `${thisYear}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

const viewYear = ref(props.year || thisYear)
const viewMonth = ref(props.month || today.getMonth() + 1)
const mode = ref('day')                          // day | month | year
const days = ref([])
const loading = ref(false)

const pageStart = computed(() => Math.floor(viewYear.value / YEARS_PER_PAGE) * YEARS_PER_PAGE)
const pageEnd = computed(() => pageStart.value + YEARS_PER_PAGE - 1)
const yearPage = computed(() =>
  Array.from({ length: YEARS_PER_PAGE }, (_, i) => pageStart.value + i)
    .filter(y => y >= MIN_YEAR && y <= MAX_YEAR),
)

/** 周一起始的 6×7 网格；空位 null。固定 42 格，切月时面板高度不跳 */
const grid = computed(() => {
  const first = new Date(viewYear.value, viewMonth.value - 1, 1)
  const lead = (first.getDay() + 6) % 7
  const cells = Array.from({ length: lead }, () => null)
  days.value.forEach(d => cells.push(d))
  while (cells.length % 7 !== 0) cells.push(null)
  while (cells.length < 42) cells.push(null)
  return cells
})

const selectedInfo = computed(
  () => days.value.find(d => d.date === props.modelValue) || null,
)

function cellClass(cell) {
  if (!cell) return 'blank'
  return {
    today: cell.date === todayStr,
    selected: cell.date === props.modelValue,
    red: cell.weekday >= 5,
    fest: !!cell.festival,
    term: !!cell.term,
    off: !!cell.holiday,
  }
}

async function loadMonth() {
  loading.value = true
  days.value = await getMonthDays(viewYear.value, viewMonth.value)
  loading.value = false
  emit('month-change', { year: viewYear.value, month: viewMonth.value })
}

function clampYear(y) {
  return Math.min(MAX_YEAR, Math.max(MIN_YEAR, y))
}
function shiftMonth(delta) {
  let m = viewMonth.value + delta
  let y = viewYear.value
  if (m < 1) { m = 12; y -= 1 }
  if (m > 12) { m = 1; y += 1 }
  viewYear.value = clampYear(y)
  viewMonth.value = m
}
function shiftYear(delta) {
  viewYear.value = clampYear(viewYear.value + delta)
}

/** 头部左右箭头：日视图翻月 / 月视图翻年 / 年视图翻十年 */
function step(delta) {
  if (mode.value === 'day') shiftMonth(delta)
  else if (mode.value === 'month') shiftYear(delta)
  else viewYear.value = clampYear(viewYear.value + delta * YEARS_PER_PAGE)
}
function navTitle(delta) {
  const d = delta < 0 ? '上一' : '下一'
  if (mode.value === 'day') return d + '月'
  if (mode.value === 'month') return d + '年'
  return d + '十年'
}

function pickYear(y) {
  viewYear.value = clampYear(y)
  mode.value = 'day'
  emit('update:year', viewYear.value)
}
function pickMonth(m) {
  viewMonth.value = m
  mode.value = 'day'
  emit('update:month', viewMonth.value)
}
function goToday() {
  viewYear.value = thisYear
  viewMonth.value = today.getMonth() + 1
  mode.value = 'day'
}
function pick(dateStr) {
  if (!props.selectable) return
  emit('update:modelValue', dateStr)
  emit('pick', dateStr)
}

watch([viewYear, viewMonth], () => {
  loadMonth()
  emit('update:year', viewYear.value)
  emit('update:month', viewMonth.value)
})
// 外部改 modelValue（如选完关闭再打开）时回到日视图
watch(() => props.modelValue, (v) => {
  if (!v || !/^\d{4}-\d{2}/.test(v)) return
  const [y, m] = v.split('-').map(Number)
  if (y !== viewYear.value) viewYear.value = clampYear(y)
  if (m !== viewMonth.value) viewMonth.value = m
})

/** 外部（父组件）需要重置视图/回今天时用 */
defineExpose({ goToday, toDay: () => { mode.value = 'day' } })

onMounted(() => {
  const init = props.year && props.month
    ? `${props.year}-${pad(props.month)}`
    : (props.modelValue || '')
  if (/^\d{4}-\d{2}/.test(init)) {
    const [y, m] = init.split('-').map(Number)
    viewYear.value = clampYear(y)
    viewMonth.value = m
  }
  loadMonth()
})
</script>

<style scoped>
.lc-root { width: 100%; }

/* ---------- 头部 ---------- */
.lc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.lc-title { flex: 1; display: flex; align-items: baseline; gap: 6px; min-width: 0; }
.lc-tbtn {
  border: none; background: transparent; cursor: pointer; font-family: inherit; padding: 2px 4px;
  border-radius: 7px; font-size: 15px; font-weight: 700; color: var(--dp-text, #18202a);
  transition: background .15s, color .15s;
}
.lc-tbtn:hover { background: rgba(199, 169, 107, .16); color: var(--yq-gold, #c7a96b); }
.lc-tbtn.on { color: var(--yq-gold, #c7a96b); }
.lc-tsub { font-size: 12px; color: var(--dp-text3, #8a8f98); }
.lc-nav {
  flex: none; width: 30px; height: 30px; border-radius: 50%; font-size: 15px;
  border: 1px solid var(--dp-line, rgba(0, 0, 0, .12)); background: var(--dp-surface, #fff);
  cursor: pointer; color: var(--dp-text2, #45505b);
}
.lc-nav:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.lc-today {
  flex: none; padding: 5px 12px; border-radius: 999px; border: 1px solid var(--yq-gold, #c7a96b);
  background: transparent; color: var(--yq-gold, #c7a96b); font-size: 12px; cursor: pointer; font-family: inherit;
}
.lc-today:hover { background: rgba(199, 169, 107, .12); }

/* ---------- 年份 / 月份快选 ---------- */
.lc-panel { display: grid; gap: 6px; padding: 4px 0 6px; }
.lc-years { grid-template-columns: repeat(5, 1fr); }
.lc-months { grid-template-columns: repeat(4, 1fr); }
.lc-ycell, .lc-mcell {
  height: 40px; border-radius: 10px; cursor: pointer; font-family: inherit;
  border: 1px solid transparent; background: transparent; color: var(--dp-text, #18202a);
  font-size: 13.5px; transition: background .15s;
}
.lc-ycell:hover, .lc-mcell:hover { background: rgba(199, 169, 107, .14); }
.lc-ycell.now { color: var(--yq-gold, #c7a96b); font-weight: 700; }
.lc-ycell.on, .lc-mcell.on { background: var(--yq-gold, #c7a96b); color: #fff; font-weight: 700; }

/* ---------- 日网格 ---------- */
.lc-week {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin-bottom: 4px;
  font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center;
}
.lc-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.lc-cell {
  position: relative; height: 50px; border: none; border-radius: 11px; background: transparent;
  cursor: pointer; font-family: inherit; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 1px; transition: background .15s;
}
.lc-cell:disabled { cursor: default; }
.lc-cell.blank { cursor: default; }
.lc-cell:hover:not(:disabled) { background: rgba(199, 169, 107, .14); }
.lc-day { font-size: 15px; color: var(--dp-text, #18202a); line-height: 1.1; }
.lc-sub {
  font-size: 10px; color: var(--dp-text3, #8a8f98); line-height: 1.1; max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.lc-cell.red .lc-day { color: #d9534f; }
.lc-cell.term .lc-sub { color: #2f8f6f; }
.lc-cell.fest .lc-sub { color: var(--yq-gold, #c7a96b); font-weight: 600; }
.lc-cell.today .lc-day { font-weight: 800; }
.lc-cell.today { background: rgba(199, 169, 107, .18); }
.lc-cell.selected { background: var(--yq-gold, #c7a96b); }
.lc-cell.selected .lc-day, .lc-cell.selected .lc-sub { color: #fff; }
.lc-flag {
  position: absolute; top: 2px; right: 3px; font-style: normal; font-size: 9px; line-height: 1;
  padding: 2px 3px; border-radius: 4px; color: #fff;
}
.lc-flag.rest { background: #d9534f; }
.lc-flag.work { background: #7f8c9b; }

/* ---------- 底部信息 ---------- */
.lc-foot {
  margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--dp-line, rgba(0, 0, 0, .08));
  font-size: 12px; color: var(--dp-text2, #45505b); display: flex; align-items: center;
  gap: 6px; flex-wrap: wrap;
}
.lc-tag { padding: 2px 8px; border-radius: 999px; font-size: 11px; }
.lc-tag.term { background: rgba(47, 143, 111, .14); color: #2f8f6f; }
.lc-tag.fest { background: rgba(199, 169, 107, .18); color: var(--yq-gold, #c7a96b); }
.lc-tag.rest { background: rgba(217, 83, 79, .14); color: #d9534f; }
.lc-tag.work { background: rgba(127, 140, 155, .16); color: #7f8c9b; }
.lc-tip { color: var(--dp-text3, #8a8f98); }

/* ---------- 紧凑模式（页面内嵌） ---------- */
.lc-root.dense .lc-cell { height: 46px; }
.lc-root.dense .lc-day { font-size: 14.5px; }

/* ---------- 窄屏 ---------- */
@media (max-width: 480px) {
  .lc-cell { height: 44px; border-radius: 9px; }
  .lc-day { font-size: 14px; }
  .lc-sub { font-size: 9px; }
  .lc-title { gap: 4px; }
  .lc-tbtn { font-size: 14px; }
  .lc-nav { width: 28px; height: 28px; }
  .lc-today { padding: 4px 10px; }
  .lc-ycell, .lc-mcell { height: 36px; font-size: 12.5px; }
}
</style>

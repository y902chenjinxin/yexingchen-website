<template>
  <div class="lp-root">
    <!-- 触发区：像普通输入框，点开弹日历 -->
    <button type="button" class="lp-field" :class="{ empty: !modelValue }" @click="open = !open">
      <span class="lp-field-main">{{ modelValue || placeholder }}</span>
      <span v-if="selectedInfo && selectedInfo.lunar_full" class="lp-field-lunar">{{ selectedInfo.lunar_full }}</span>
      <i class="lp-caret">▾</i>
    </button>
    <button v-if="modelValue" type="button" class="lp-clear" title="清除" @click.stop="pick('')">✕</button>

    <Teleport to="body">
      <div v-if="open" class="lp-mask" @click.self="open = false">
        <div class="lp-panel">
          <header class="lp-head">
            <button class="lp-nav" @click="shift(-1)">‹</button>
            <div class="lp-title">{{ viewYear }} 年 {{ viewMonth }} 月</div>
            <button class="lp-nav" @click="shift(1)">›</button>
            <button class="lp-today" @click="goToday">今天</button>
          </header>

          <div class="lp-week">
            <span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span>
          </div>

          <div class="lp-grid">
            <button
              v-for="(cell, i) in grid"
              :key="i"
              class="lp-cell"
              :class="cellClass(cell)"
              :disabled="!cell"
              @click="cell && pick(cell.date)"
            >
              <template v-if="cell">
                <span class="lp-day">{{ cell.day }}</span>
                <span class="lp-sub">{{ cell.sub }}</span>
                <em v-if="cell.holiday" class="lp-flag rest">休</em>
                <em v-else-if="cell.makeup" class="lp-flag work">班</em>
              </template>
            </button>
          </div>

          <footer class="lp-foot">
            <template v-if="selectedInfo">
              <b>{{ modelValue }}</b>
              <span v-if="selectedInfo.lunar_full">· {{ selectedInfo.lunar_full }}</span>
              <span v-if="selectedInfo.term" class="lp-tag term">{{ selectedInfo.term }}</span>
              <span v-for="f in selectedInfo.festivals" :key="f" class="lp-tag fest">{{ f }}</span>
              <span v-if="selectedInfo.holiday" class="lp-tag rest">
                假期第 {{ selectedInfo.holiday_index }}/{{ selectedInfo.holiday_days }} 天
              </span>
            </template>
            <template v-else>
              <span class="lp-tip">{{ loading ? '加载中…' : '点日期选择；带「休/班」的是法定假期与调休' }}</span>
            </template>
          </footer>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
/** 农历日历日期选择器（v2.40.36）。
 *
 * 参考手机日历：每格显示公历 + 农历/节气/节日，法定假期标「休」、调休标「班」。
 * 数据全部来自 /api/lunar/month（后端用 lunardate 算农历，节气用近似公式，假期用国务院口径），
 * 前端只负责排版与交互，并按「年-月」缓存已取过的月份。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { lunarApi } from '@/api/lunar'

const props = defineProps({
  modelValue: { type: String, default: '' },     // 'YYYY-MM-DD'
  placeholder: { type: String, default: '选择日期' },
})
const emit = defineEmits(['update:modelValue', 'pick'])

const open = ref(false)
const loading = ref(false)
const today = new Date()
const viewYear = ref(today.getFullYear())
const viewMonth = ref(today.getMonth() + 1)
const days = ref([])
const cache = new Map()          // 'Y-M' → days

const pad = (n) => String(n).padStart(2, '0')
const key = computed(() => `${viewYear.value}-${viewMonth.value}`)
const todayStr = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

/** 周一起始的 6×7 网格；空位为 null */
const grid = computed(() => {
  const first = new Date(viewYear.value, viewMonth.value - 1, 1)
  const lead = (first.getDay() + 6) % 7          // 周一时 0
  const cells = Array.from({ length: lead }, () => null)
  days.value.forEach(d => cells.push(d))
  while (cells.length % 7 !== 0) cells.push(null)
  // 行数不足 6 行时补满，避免切月时面板高度跳动
  while (cells.length < 42) cells.push(null)
  return cells
})
const selectedInfo = computed(() => days.value.find(d => d.date === props.modelValue) || null)

function cellClass(cell) {
  if (!cell) return 'blank'
  return {
    today: cell.date === todayStr,
    selected: cell.date === props.modelValue,
    red: cell.weekday >= 5,                       // 周末标红
    fest: !!cell.festival,
    term: !!cell.term,
    off: !!cell.holiday,
  }
}

async function loadMonth() {
  const k = key.value
  if (cache.has(k)) { days.value = cache.get(k); return }
  loading.value = true
  try {
    const res = await lunarApi.month(viewYear.value, viewMonth.value)
    const list = res?.data?.days || []
    cache.set(k, list)
    days.value = list
  } catch {
    days.value = []
  } finally {
    loading.value = false
  }
}

function shift(delta) {
  let m = viewMonth.value + delta, y = viewYear.value
  if (m < 1) { m = 12; y -= 1 }
  if (m > 12) { m = 1; y += 1 }
  viewMonth.value = m; viewYear.value = y
}
function goToday() {
  viewYear.value = today.getFullYear()
  viewMonth.value = today.getMonth() + 1
}

function pick(dateStr) {
  emit('update:modelValue', dateStr)
  emit('pick', dateStr)
  open.value = false
}

watch([viewYear, viewMonth], loadMonth)

onMounted(() => {
  // 打开时定位到已选日期所在月份
  if (props.modelValue && /^\d{4}-\d{2}/.test(props.modelValue)) {
    const [y, m] = props.modelValue.split('-').map(Number)
    viewYear.value = y; viewMonth.value = m
  }
  loadMonth()
})
</script>

<style scoped>
.lp-root { position: relative; display: inline-flex; align-items: center; gap: 6px; width: 100%; }
.lp-field {
  flex: 1; display: flex; align-items: center; gap: 8px; min-height: 38px; padding: 8px 12px;
  border: 1px solid var(--dp-line, rgba(0, 0, 0, .14)); border-radius: 10px; cursor: pointer;
  background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-family: inherit;
  font-size: 13.5px; text-align: left;
}
.lp-field.empty .lp-field-main { color: var(--dp-text3, #8a8f98); }
.lp-field-main { flex: 1; }
.lp-field-lunar { font-size: 11.5px; color: var(--yq-gold, #c7a96b); }
.lp-caret { color: var(--dp-text3, #8a8f98); font-size: 11px; }
.lp-clear {
  border: none; background: transparent; cursor: pointer; color: var(--dp-text3, #8a8f98);
  font-size: 13px; padding: 4px 6px;
}

.lp-mask {
  position: fixed; inset: 0; z-index: 2000; background: rgba(20, 26, 34, .38);
  display: flex; align-items: center; justify-content: center; padding: 16px;
}
.lp-panel {
  width: min(420px, 100%); max-height: 88vh; overflow-y: auto; border-radius: 18px; padding: 14px 16px 12px;
  background: var(--dp-bg, #f7f5f0); box-shadow: 0 20px 50px rgba(10, 16, 24, .28);
}
.lp-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.lp-title { flex: 1; font-size: 15px; font-weight: 700; color: var(--dp-text, #18202a); }
.lp-nav {
  width: 30px; height: 30px; border-radius: 50%; border: 1px solid var(--dp-line, rgba(0, 0, 0, .12));
  background: var(--dp-surface, #fff); cursor: pointer; font-size: 15px; color: var(--dp-text2, #45505b);
}
.lp-today {
  padding: 5px 12px; border-radius: 999px; border: 1px solid var(--yq-gold, #c7a96b);
  background: transparent; color: var(--yq-gold, #c7a96b); font-size: 12px; cursor: pointer; font-family: inherit;
}
.lp-week {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin-bottom: 4px;
  font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center;
}
.lp-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.lp-cell {
  position: relative; height: 50px; border: none; border-radius: 11px; background: transparent;
  cursor: pointer; font-family: inherit; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 1px; transition: background .15s;
}
.lp-cell.blank { cursor: default; }
.lp-cell:hover:not(.blank) { background: rgba(199, 169, 107, .14); }
.lp-day { font-size: 15px; color: var(--dp-text, #18202a); line-height: 1.1; }
.lp-sub { font-size: 10px; color: var(--dp-text3, #8a8f98); line-height: 1.1; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lp-cell.red .lp-day { color: #d9534f; }
.lp-cell.term .lp-sub { color: #2f8f6f; }
.lp-cell.fest .lp-sub { color: var(--yq-gold, #c7a96b); font-weight: 600; }
.lp-cell.today .lp-day { font-weight: 800; }
.lp-cell.today { background: rgba(199, 169, 107, .18); }
.lp-cell.selected { background: var(--yq-gold, #c7a96b); }
.lp-cell.selected .lp-day, .lp-cell.selected .lp-sub { color: #fff; }
.lp-flag {
  position: absolute; top: 2px; right: 3px; font-style: normal; font-size: 9px; line-height: 1;
  padding: 2px 3px; border-radius: 4px; color: #fff;
}
.lp-flag.rest { background: #d9534f; }
.lp-flag.work { background: #7f8c9b; }
.lp-foot {
  margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--dp-line, rgba(0, 0, 0, .08));
  font-size: 12px; color: var(--dp-text2, #45505b); display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.lp-tag { padding: 2px 8px; border-radius: 999px; font-size: 11px; }
.lp-tag.term { background: rgba(47, 143, 111, .14); color: #2f8f6f; }
.lp-tag.fest { background: rgba(199, 169, 107, .18); color: var(--yq-gold, #c7a96b); }
.lp-tag.rest { background: rgba(217, 83, 79, .14); color: #d9534f; }
.lp-tip { color: var(--dp-text3, #8a8f98); }
</style>

<!--
  HistoryView.vue
  玄黄・历史上的今天 独立岛页（v2.46）
  - 两栏：左侧自绘月度日历（毛玻璃 + 月切换 + 今天/选中高亮）；右侧铺列所选日期事件。
  - 文字统一用主题感知变量 --lj-*（夜间浅色 / 白天深色），避免白天白字。
  - 提供「回到今天」「刷新」。
-->
<template>
  <IslandInnerBase
    type="history"
    title="历史上的今天"
    subtitle="每一天，都藏着未来的线索"
  >
    <template #toolbar>
      <button v-if="!isTodaySel" class="ht-btn ghost" @click="goToday">回到今天</button>
      <button class="ht-btn ghost" :disabled="loading" @click="load(true)">
        {{ loading ? '加载中…' : '⟳ 刷新' }}
      </button>
    </template>

    <div class="ht-layout">
      <!-- ============ 日历（左 / 约 1/3） — 复用 vue-cal（antoniandre/vue-cal） ============ -->
      <section class="ht-cal glass">
        <div class="ht-cal-toolbar">
          <el-select
            class="ht-sel ht-sel-y"
            :model-value="viewDate.y"
            size="small"
            :teleported="false"
            @change="jumpYear"
          >
            <el-option v-for="y in yearOptions" :key="y" :value="y" :label="`${y} 年`" />
          </el-select>
          <span class="ht-cal-toolbar-tip">点击日期查看历史事件</span>
        </div>

        <VueCal
          ref="calRef"
          class="ht-vuecal"
          :selected-date="selectedDate"
          :view="calView"
          :time="false"
          :disable-views="['years', 'year']"
          :events="[]"
          :hide-weekends="false"
          :today-button="false"
          :view-selector="false"
          :locale="zhLocale"
          :disable-look-ahead="false"
          active-view="month"
          style="height: 320px;"
          @cell-click="onCellClick"
        />

        <div class="ht-cal-foot">
          <span class="ht-cal-today">{{ dateLabel }}</span>
          <span v-if="isTodaySel" class="ht-cal-tag">今天</span>
        </div>
      </section>

      <!-- ============ 事件列表（右 / 约 2/3） ============ -->
      <section class="ht-events glass">
        <div class="ht-events-head">
          <span class="ht-events-title">{{ dateLabel }} 事件</span>
          <span class="ht-events-sub">共 {{ items.length }} 条 · 按年份倒序</span>
        </div>

        <div v-if="loading && !items.length" class="ht-loading">
          <span class="ht-dot"></span><span class="ht-dot"></span><span class="ht-dot"></span>
          <span class="ht-loading-txt">加载中…</span>
        </div>
        <template v-else>
          <div v-if="!items.length" class="ht-empty">该日暂无内置记录，点其他日期试试</div>
          <ol v-else class="ht-list">
            <li v-for="(it, idx) in items" :key="`${it.year}-${idx}`" class="ht-row">
              <span class="ht-y">{{ it.year || '—' }}</span>
              <div class="ht-body">
                <span class="ht-t">{{ it.title }}</span>
                <span v-if="it.desc" class="ht-d">{{ it.desc }}</span>
              </div>
            </li>
          </ol>
        </template>
      </section>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElSelect, ElOption } from 'element-plus'
import { VueCal } from 'vue-cal'
import 'vue-cal/style'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { workbenchApi } from '@/api/workbench'

const pad = (n) => String(n).padStart(2, '0')
const today = new Date()
today.setHours(0, 0, 0, 0)

/* vue-cal 直接吃 Date：selectedDate 即选中日期，calView 即当前视图标识 */
const selectedDate = ref(new Date(today))
const calView = ref('month')

/* 用于顶部 select 显示当前年（vue-cal 暴露 viewDateDate.getFullYear 不直观，用 selectedDate 推） */
const viewDate = computed(() => ({ y: selectedDate.value.getFullYear(), m: selectedDate.value.getMonth() }))

/* 年下拉：1900 ~ 当前年 + 50 */
const yearOptions = computed(() => {
  const cur = today.getFullYear()
  const arr = []
  for (let y = 1900; y <= cur + 50; y++) arr.push(y)
  return arr
})

/* zh-CN locale（vue-cal 内置） */
const zhLocale = 'zh-CN'

const items = ref([])
const loading = ref(false)

function dateKey(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` }

const dateLabel = computed(() =>
  `${selectedDate.value.getFullYear()} 年 ${selectedDate.value.getMonth() + 1} 月 ${selectedDate.value.getDate()} 日`
)
const isTodaySel = computed(() => dateKey(selectedDate.value) === dateKey(today))
function dayQuery() { return dateKey(selectedDate.value) }

/* 点击日历单元格：vue-cal payload 是 { e, date, events } */
function onCellClick({ date }) {
  selectedDate.value = new Date(date)
  load(false)
}

/* 跳年：通过实例 API 切换视图到对应年（vue-cal 会保持选中月份） */
const calRef = ref(null)
function jumpYear(y) {
  const newY = Number(y)
  const cur = selectedDate.value
  const dim = new Date(newY, cur.getMonth() + 1, 0).getDate()
  let nextSel = new Date(cur)
  if (nextSel.getFullYear() !== newY) {
    nextSel = new Date(newY, cur.getMonth(), Math.min(cur.getDate(), dim))
  }
  selectedDate.value = nextSel
  // 让 vue-cal 立刻翻到新月份（避免停留在原月）
  if (calRef.value?.goToDate) calRef.value.goToDate(nextSel)
  if (dateKey(nextSel) !== dateKey(cur)) load(false)
}

function goToday() {
  const t = new Date(today)
  selectedDate.value = t
  if (calRef.value?.goToDate) calRef.value.goToDate(t)
  load(false)
}

async function load(refresh = false) {
  loading.value = true
  try {
    const res = await workbenchApi.todayInHistory(
      refresh ? { date: dayQuery(), refresh: true } : { date: dayQuery() }
    )
    const data = (res && typeof res === 'object' && 'data' in res) ? res.data : (res || {})
    items.value = Array.isArray(data.items) ? data.items : []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<style scoped>
/* ============ 两栏布局 ============ */
.ht-layout {
  display: grid;
  grid-template-columns: minmax(248px, 1.05fr) 2fr;
  gap: 18px;
  align-items: start;
}

/* ============ 通用按钮 ============ */
.ht-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--dp-line, rgba(255, 255, 255, 0.12));
  background: var(--dp-glass, rgba(255, 255, 255, 0.06));
  color: var(--lj-text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.ht-btn:hover:not(:disabled) { background: var(--dp-glass-strong, rgba(255, 255, 255, 0.14)); }
.ht-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.ht-btn:focus-visible { outline: 2px solid #bfa05f; outline-offset: 2px; }

/* ============ 日历（复用 vue-cal） ============ */
.ht-cal { padding: 0; border-radius: 16px; overflow: hidden; }
.ht-cal-toolbar {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--dp-line, rgba(127,127,127,0.14));
}
.ht-cal-toolbar-tip { font-size: 12px; color: var(--lj-text-3); letter-spacing: .04em; }

.ht-sel-y :deep(.el-select__wrapper) { min-width: 96px; }
.ht-sel :deep(.el-select__wrapper),
.ht-sel :deep(.el-select__wrapper.is-default),
.ht-sel :deep(.el-select__wrapper.is-hovering) {
  background: transparent;
  box-shadow: inset 0 0 0 1px var(--dp-line, rgba(127,127,127,0.2));
  font-family: var(--font-serif, serif);
  min-height: 26px;
}
.ht-sel :deep(.el-select__wrapper.is-hovering:not(.is-focused)) {
  box-shadow: inset 0 0 0 1px var(--dp-line-strong, rgba(127,127,127,0.35));
}
.ht-sel :deep(.el-select__wrapper.is-focused) {
  box-shadow: inset 0 0 0 1px var(--yq-gold, #c7a96b) !important;
}
.ht-sel :deep(.el-select__placeholder),
.ht-sel :deep(.el-select__selected-item) { color: var(--lj-text); font-size: 13px; }
.ht-sel :deep(.el-select__suffix) { color: var(--lj-text-2); }

/* vue-cal 主题覆盖 — 玄黄暗调，与项目卡片融合 */
.ht-vuecal.vuecal {
  --vuecal-primary-color: #c7a96b;
  --vuecal-secondary-color: #7fa8a3;
  --vuecal-base-color: transparent;
  --vuecal-cell-border-color: rgba(127,127,127,0.12);
  --vuecal-heading-color: rgba(127,127,127,0.45);
  --vuecal-today-color: #c7a96b;
  --vuecal-time-color: var(--lj-text-2);
  background: transparent;
  color: var(--lj-text);
  border: 0;
  border-radius: 0;
  font-family: var(--font-serif, serif);
  padding: 0;
  margin: 0;
}
.ht-vuecal.vuecal :deep(.vuecal__title-bar) {
  background: transparent;
  padding: 6px 14px 4px;
}
.ht-vuecal.vuecal :deep(.vuecal__title-bar .vuecal__title) {
  color: var(--lj-text);
  font-size: 14px; letter-spacing: .08em;
}
.ht-vuecal.vuecal :deep(.vuecal__title-bar .vuecal__arrow) {
  color: var(--lj-text-2);
  background: transparent;
  border: 1px solid var(--dp-line, rgba(127,127,127,0.2));
  border-radius: 8px;
  width: 28px; height: 28px;
  display: inline-flex; align-items: center; justify-content: center;
}
.ht-vuecal.vuecal :deep(.vuecal__title-bar .vuecal__arrow:hover) {
  background: var(--dp-glass, rgba(255,255,255,0.08));
  border-color: var(--dp-line-strong, rgba(127,127,127,0.35));
  color: var(--lj-text);
}
.ht-vuecal.vuecal :deep(.vuecal__heading) {
  color: var(--lj-text-3);
  font-size: 11px; letter-spacing: .1em;
  padding: 4px 6px 6px;
  text-align: center;
}
.ht-vuecal.vuecal :deep(.vuecal__body) { background: transparent; }
.ht-vuecal.vuecal :deep(.vuecal__cell) {
  background: transparent;
  color: var(--lj-text);
  border: 1px solid var(--dp-line, rgba(127,127,127,0.1));
  transition: background 0.15s ease;
  cursor: pointer;
}
.ht-vuecal.vuecal :deep(.vuecal__cell:hover) {
  background: var(--dp-glass, rgba(255,255,255,0.06));
}
.ht-vuecal.vuecal :deep(.vuecal__cell-events) { display: none; }
/* 今日：鎏金描边 + 金色 */
.ht-vuecal.vuecal :deep(.vuecal__cell--today) {
  background: rgba(199, 169, 107, 0.06);
}
.ht-vuecal.vuecal :deep(.vuecal__cell--today .vuecal__cell-date) {
  color: var(--yq-gold, #c7a96b);
  font-weight: 600;
}
/* 选中：金色渐变填充 */
.ht-vuecal.vuecal :deep(.vuecal__cell--selected) {
  background: linear-gradient(135deg, rgba(199,169,107,0.85), rgba(127,168,163,0.85)) !important;
  color: #0b0f14;
}
.ht-vuecal.vuecal :deep(.vuecal__cell--selected .vuecal__cell-date) {
  color: #0b0f14; font-weight: 700;
}
/* 非本月弱化 */
.ht-vuecal.vuecal :deep(.vuecal__cell--out-of-scope) {
  color: var(--lj-text-3);
  opacity: .45;
}
.ht-vuecal.vuecal :deep(.vuecal__cell-date) {
  font-size: 13px;
  color: inherit;
  padding: 4px 6px;
  font-family: inherit;
}

.ht-cal-foot { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 8px 14px 12px; border-top: 1px solid var(--dp-line, rgba(127,127,127,0.1)); }
.ht-cal-today { font-family: var(--font-serif, serif); font-size: 12px; letter-spacing: .03em; color: var(--lj-text); }
.ht-cal-tag {
  font-size: 11px; padding: 2px 9px; border-radius: 999px;
  background: var(--lj-seal-soft, rgba(255,214,130,0.14)); color: var(--yq-gold, #b8860b);
}

/* ============ 事件列表 ============ */
.ht-events-head {
  display: flex; align-items: baseline; justify-content: space-between;
  padding: 4px 2px 12px; flex-wrap: wrap; gap: 6px;
}
.ht-events-title {
  font-family: var(--font-serif, serif); font-size: 15px;
  letter-spacing: .06em; color: var(--lj-text);
}
.ht-events-sub { font-size: 12px; color: var(--lj-text-2); }

.ht-loading { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 34px 0; }
.ht-loading-txt { font-size: 12px; color: var(--lj-text-2); letter-spacing: .12em; }
.ht-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #4c8a5f; animation: ht-blink 1.2s ease-in-out infinite;
}
.ht-dot:nth-child(2) { animation-delay: .18s; }
.ht-dot:nth-child(3) { animation-delay: .36s; }
@keyframes ht-blink { 0%,100%{opacity:.25;transform:scale(.8)} 50%{opacity:1;transform:scale(1)} }

.ht-empty { padding: 30px 8px; text-align: center; color: var(--lj-text-3); font-size: 13px; }

.ht-list {
  margin: 0; padding: 0; list-style: none;
  display: flex; flex-direction: column; gap: 10px;
}
.ht-row {
  display: flex; align-items: baseline; gap: 16px;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--dp-glass, rgba(255, 255, 255, 0.045));
  border: 1px solid var(--dp-line, rgba(255, 255, 255, 0.06));
  transition: background 0.2s ease;
}
.ht-row:hover { background: var(--dp-glass-strong, rgba(255, 255, 255, 0.08)); }
.ht-y {
  flex-shrink: 0; min-width: 64px; text-align: right;
  font-family: var(--font-serif, serif);
  font-size: 15px; color: var(--yq-gold, #c7a96b); letter-spacing: .03em;
}
.ht-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ht-t { font-size: 14px; color: var(--lj-text); line-height: 1.5; }
.ht-d { font-size: 12px; color: var(--lj-text-2); line-height: 1.65; }

/* ============ 窄屏：单列堆叠 ============ */
@media (max-width: 900px) {
  .ht-layout { grid-template-columns: 1fr; }
  .ht-cal { max-width: 460px; margin: 0 auto 0 0; }
}
@media (max-width: 768px) {
  .ht-cal { padding: 14px 14px; }
  .ht-cal-cell { font-size: 12px; }
  .ht-row { gap: 12px; padding: 10px 12px; }
  .ht-y { min-width: 52px; font-size: 14px; }
}
</style>
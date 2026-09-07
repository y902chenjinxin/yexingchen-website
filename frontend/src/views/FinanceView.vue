<template>
  <div class="fin-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="fin-inner">
      <!-- 页头：返回 + 标题 -->
      <header class="fin-head">
        <div class="fin-head-left">
          <BackButton class="fin-back" />
        </div>
        <div class="fin-titles">
          <h1 class="fin-title">个人账本</h1>
          <p class="fin-sub">流水明账 · 一目了然</p>
        </div>
        <div class="fin-head-right">
          <button class="fin-btn primary" @click="openNew">＋ 记一笔</button>
        </div>
      </header>

      <!-- 月份切换 + 记一笔面板 -->
      <div class="fin-toolbar">
        <div class="fin-month">
          <button class="fin-nav" @click="shiftMonth(-1)">‹</button>
          <button class="fin-month-label" @click="goThisMonth">{{ monthLabel }}<span v-if="!isThisMonth" class="fin-this" @click.stop="goThisMonth">回本月</span></button>
          <button class="fin-nav" @click="shiftMonth(1)">›</button>
        </div>
      </div>

      <!-- 记一笔（内联面板，非弹窗） -->
      <transition name="fd">
        <section v-if="form.show" class="fin-form glass">
          <div class="fin-form-head">
            <span class="fin-form-title">{{ form.editing ? '编辑流水' : '记一笔' }}</span>
            <span v-if="form.editing" class="fin-form-edit-tag">正在编辑 #{{ form.editingId }}</span>
            <button class="fin-form-close" @click="form.show = false">✕</button>
          </div>

          <div class="fin-form-body">
            <div class="fin-f-type">
              <button
                v-for="t in typeTabs"
                :key="t.key"
                class="fin-tab"
                :class="{ active: form.type === t.key }"
                @click="pickType(t.key)"
              >{{ t.label }}</button>
            </div>

            <div class="fin-f-row">
              <div class="fin-f-field grow">
                <label class="fin-f-label">金额（元）</label>
                <el-input-number
                  v-model="form.amount"
                  :min="0.01"
                  :precision="2"
                  :step="10"
                  :controls="false"
                  class="fin-amount"
                  placeholder="0.00"
                />
              </div>
              <div class="fin-f-field">
                <label class="fin-f-label">日期</label>
                <el-date-picker
                  v-model="form.date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  :clearable="false"
                  class="fin-date"
                />
              </div>
            </div>

            <div class="fin-f-field">
              <label class="fin-f-label">分类</label>
              <div class="fin-cats">
                <button
                  v-for="c in currentCats"
                  :key="c.key"
                  class="fin-cat"
                  :class="{ active: form.category === c.key }"
                  @click="form.category = c.key"
                >{{ c.icon }} {{ c.key }}</button>
              </div>
            </div>

            <div class="fin-f-field">
              <label class="fin-f-label">备注</label>
              <div class="fin-note-row">
                <input
                  v-model="form.note"
                  class="fin-note-input"
                  placeholder="写点什么（可语音）…"
                  maxlength="255"
                />
                <VoiceInputButton @result="onVoiceNote" />
              </div>
            </div>

            <div class="fin-form-actions">
              <button v-if="form.editing" class="fin-btn ghost" @click="form.show = false">取消</button>
              <button class="fin-btn primary" :disabled="saving" @click="save">{{ form.editing ? '保存修改' : '记入账本' }}</button>
            </div>
          </div>
        </section>
      </transition>

      <!-- KPI 卡片 -->
      <section class="fin-kpis">
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">本月收入</span>
          <span class="fin-kpi-val income">+ ¥ {{ money(summary.month_income) }}</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">本月支出</span>
          <span class="fin-kpi-val expense">− ¥ {{ money(summary.month_expense) }}</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">本月笔数</span>
          <span class="fin-kpi-val">{{ summary.month_count }}</span>
          <span class="fin-kpi-sub">笔流水</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">累计结余</span>
          <span class="fin-kpi-val" :class="summary.balance >= 0 ? 'income' : 'expense'">{{ summary.balance >= 0 ? '+' : '−' }} ¥ {{ money(Math.abs(summary.balance)) }}</span>
        </div>
      </section>

      <!-- 图表区 -->
      <section class="fin-charts">
        <div class="fin-chart glass">
          <h2 class="fin-chart-title">本月支出分类占比</h2>
          <div v-if="summary.categories.length" class="fin-chart-body">
            <DonutChart :data="summary.categories" />
            <ul class="fin-legend">
              <li v-for="c in summary.categories" :key="c.category" class="fin-legend-item">
                <i class="fin-dot" :style="{ background: c.color }"></i>
                <span class="fin-legend-name">{{ c.icon }} {{ c.category }}</span>
                <span class="fin-legend-amt">¥ {{ money(c.amount) }}</span>
              </li>
            </ul>
          </div>
          <div v-else class="fin-chart-empty">本月暂无支出，去「记一笔」吧</div>
        </div>

        <div class="fin-chart glass">
          <h2 class="fin-chart-title">本月收支趋势</h2>
          <div v-if="summary.trends.length" class="fin-chart-body">
            <TrendChart :days="summary.trends" :has-any="hasAnyTrend" />
          </div>
          <div v-else class="fin-chart-empty">暂无数据</div>
        </div>
      </section>

      <!-- 流水列表 -->
      <section class="fin-ledger glass">
        <div class="fin-ledger-head">
          <h2 class="fin-chart-title">流水明细</h2>
          <div class="fin-filters">
            <el-select v-model="filters.type" placeholder="全部类型" clearable class="fin-filter" @change="reload(1)">
              <el-option label="支出" value="expense" />
              <el-option label="收入" value="income" />
            </el-select>
            <input v-model="filters.q" class="fin-filter-input" placeholder="搜索备注/分类…" @keyup.enter="reload(1)" />
            <button class="fin-btn ghost small" @click="reload(1)">查询</button>
          </div>
        </div>

        <div class="fin-list">
          <div v-if="!list.length" class="fin-list-empty">还没有符合条件的流水</div>
          <div v-else>
            <div v-for="row in list" :key="row.id" class="fin-row" :class="{ editing: form.editing && form.editingId === row.id }">
              <div class="fin-row-icon">{{ row.category_icon }}</div>
              <div class="fin-row-main">
                <div class="fin-row-top">
                  <span class="fin-row-cat">{{ row.category }}</span>
                  <span class="fin-row-note">{{ row.note }}</span>
                </div>
                <div class="fin-row-date">{{ fmtDay(row.occurred_at) }}</div>
              </div>
              <div class="fin-row-amt" :class="row.type">
                {{ row.type === 'income' ? '+' : '−' }} ¥ {{ money(row.amount) }}
              </div>
              <div class="fin-row-ops">
                <button class="fin-op" title="编辑" @click="openEdit(row)">✎</button>
                <el-popconfirm
                  title="确认删除这条流水？"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  width="220"
                  @confirm="del(row)"
                >
                  <template #reference>
                    <button class="fin-op danger" title="删除">🗑</button>
                  </template>
                </el-popconfirm>
              </div>
            </div>

            <div class="fin-pager">
              <span class="fin-pager-info">共 {{ total }} 笔</span>
              <el-pagination
                layout="prev, pager, next"
                :total="total"
                :page-size="pageSize"
                :current-page="page"
                background
                small
                @current-change="onPage"
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import BackButton from '@/components/BackButton.vue'
import VoiceInputButton from '@/components/VoiceInputButton.vue'
import DonutChart from '@/components/finance/DonutChart.vue'
import TrendChart from '@/components/finance/TrendChart.vue'
import { financeApi } from '@/api/finance'

function backToTopScroll() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const typeTabs = [
  { key: 'expense', label: '支出' },
  { key: 'income', label: '收入' },
]
const PALETTE = ['#7FA8A3', '#C7A96B', '#6E8BA6', '#B98BA6', '#8BB07A', '#C98B6B', '#6FA6C9', '#A98BC9', '#7F8FA3']

const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const summary = ref({ categories: [], trends: [], balance: 0 })
const categoriesMeta = ref({ expense: [], income: [] })
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const saving = ref(false)

const filters = reactive({ type: '', q: '' })

const form = reactive({
  show: false,
  editing: false,
  editingId: null,
  type: 'expense',
  amount: null,
  date: fmtDate(now),
  category: '餐饮',
  note: '',
})

const monthLabel = computed(() => {
  const [y, m] = month.value.split('-')
  return `${y}年${Number(m)}月`
})
const isThisMonth = computed(() => {
  const label = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  return month.value === label
})
const currentCats = computed(() => {
  const pool = form.type === 'income' ? categoriesMeta.value.income : categoriesMeta.value.expense
  return pool.length ? pool : [{ key: '其他', icon: '🧾' }]
})
const hasAnyTrend = computed(() => (summary.value.trends || []).some(d => d.income || d.expense))

function money(v) { return Number(v || 0).toFixed(2) }
function fmtDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function fmtDay(iso) {
  if (!iso) return ''
  return iso.slice(0, 10)
}

async function loadCategories() {
  const res = await financeApi.categories()
  categoriesMeta.value = res.data
}
async function loadSummary() {
  const res = await financeApi.summary(month.value)
  summary.value = { ...res.data, categories: res.data.categories.map((c, i) => ({ ...c, color: PALETTE[i % PALETTE.length] })) }
}
async function loadList() {
  const params = { page: page.value, size: pageSize }
  if (filters.type) params.type = filters.type
  if (filters.q) params.q = filters.q
  const res = await financeApi.list(params)
  list.value = res.data.list
  total.value = res.data.total
}
function reload(p) {
  if (p) page.value = p
  return loadList()
}
function shiftMonth(d) {
  const [y, m] = month.value.split('-').map(Number)
  const totalM = y * 12 + (m - 1) + d
  const ny = Math.floor(totalM / 12)
  const nm = (totalM % 12) + 1
  month.value = `${ny}-${String(nm).padStart(2, '0')}`
  page.value = 1
  loadSummary()
  loadList()
}
function goThisMonth() {
  month.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  page.value = 1
  loadSummary()
  loadList()
}

function resetForm() {
  form.type = 'expense'
  form.amount = null
  form.date = fmtDate(new Date())
  form.category = '餐饮'
  form.note = ''
}
function openNew() {
  resetForm()
  form.editing = false
  form.editingId = null
  form.show = true
  backToTopScroll()
}
function pickType(t) {
  form.type = t
  form.category = t === 'income' ? '工资' : '餐饮'
}
function openEdit(row) {
  form.show = true
  form.editing = true
  form.editingId = row.id
  form.type = row.type
  form.amount = row.amount
  form.date = fmtDay(row.occurred_at)
  form.category = row.category
  form.note = row.note
  backToTopScroll()
}
function onVoiceNote(text) {
  form.note = form.note.trim() ? `${form.note.trim()} ${text}` : text
}
async function save() {
  if (!form.amount || form.amount <= 0) {
    return
  }
  saving.value = true
  const payload = {
    type: form.type,
    amount: form.amount,
    category: form.category,
    note: form.note,
    occurred_at: `${form.date || fmtDate(new Date())}T12:00:00`,
  }
  try {
    if (form.editing) {
      await financeApi.update(form.editingId, payload)
    } else {
      await financeApi.create(payload)
    }
    form.show = false
    form.editing = false
    form.editingId = null
    await Promise.all([loadSummary(), reload(1)])
  } finally {
    saving.value = false
  }
}
async function del(row) {
  await financeApi.remove(row.id)
  await Promise.all([loadSummary(), loadList()])
}

onMounted(() => {
  loadCategories()
  loadSummary()
  loadList()
})
</script>

<style scoped>
.fin-page {
  position: relative;
  min-height: 100vh;
  padding: 96px 24px 60px;
  box-sizing: border-box;
  font-family: var(--font-serif);
  color: var(--lj-text);
  overflow-x: hidden;
}
.fin-inner { position: relative; z-index: 1; max-width: 1080px; margin: 0 auto; }

.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 55% 40% at 18% 6%, var(--glow-rain), transparent 60%),
    radial-gradient(ellipse 45% 40% at 85% 26%, var(--glow-gold), transparent 60%),
    var(--lj-bg); }
.lj-paper-texture { position: absolute; inset: 0; opacity: .5;
  background:
    repeating-linear-gradient(0deg, rgba(127,168,163,.02) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(127,168,163,.014) 0 1px, transparent 1px 7px); }
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .4;
  background: radial-gradient(circle, rgba(127,168,163,.14), transparent 70%); animation: fd-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 480px; height: 400px; top: 4%; left: -8%; }
.lj-wash.w2 { width: 420px; height: 360px; bottom: 4%; right: -8%; animation-delay: 9s; }
@keyframes fd-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(32px,-18px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

.glass { background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow); }

/* 页头 */
.fin-head { display: flex; align-items: center; gap: 18px; margin-bottom: 18px; }
.fin-head-left { flex: none; }
.fin-titles { flex: 1; }
.fin-title { margin: 0; font-size: 28px; letter-spacing: .12em; }
.fin-sub { margin: 6px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .18em; }
.fin-head-right { flex: none; }

.fin-btn { border: none; cursor: pointer; border-radius: 10px; font-family: var(--font-serif);
  color: var(--lj-text); background: var(--lj-glass); border: 1px solid var(--lj-line); padding: 9px 16px; transition: all .22s; }
.fin-btn:hover { border-color: var(--lj-line-strong); }
.fin-btn.primary { background: linear-gradient(135deg, rgba(127,168,163,.55), rgba(199,169,107,.4)); color: #fff; }
.fin-btn.primary:hover { filter: brightness(1.05); box-shadow: 0 6px 18px rgba(0,0,0,.25); }
.fin-btn.ghost { background: transparent; }
.fin-btn.small { padding: 6px 12px; font-size: 13px; }

/* 月份 */
.fin-toolbar { display: flex; justify-content: center; margin-bottom: 16px; }
.fin-month { display: flex; align-items: center; gap: 10px; }
.fin-nav { width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--lj-line); background: var(--lj-glass);
  color: var(--lj-text); font-size: 18px; cursor: pointer; transition: all .2s; }
.fin-nav:hover { border-color: var(--lj-line-strong); }
.fin-month-label { position: relative; border: 1px solid var(--lj-line); background: var(--lj-glass); color: var(--lj-text);
  padding: 7px 18px; border-radius: 999px; font-family: var(--font-serif); letter-spacing: .1em; font-size: 16px; cursor: default; }
.fin-this { margin-left: 8px; font-size: 11px; color: var(--lj-dai); cursor: pointer; }

/* 记一笔面板 */
.fin-form { border-radius: 16px; padding: 18px 20px; margin-bottom: 18px; }
.fin-form-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.fin-form-title { font-size: 16px; letter-spacing: .08em; }
.fin-form-edit-tag { font-size: 12px; color: var(--lj-ochre); }
.fin-form-close { margin-left: auto; border: none; background: transparent; color: var(--lj-text-2); font-size: 16px; cursor: pointer; }
.fin-form-body { display: flex; flex-direction: column; gap: 14px; }
.fin-f-type { display: flex; gap: 8px; }
.fin-tab { flex: 1; padding: 9px; border-radius: 10px; border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .22s; font-family: var(--font-serif); }
.fin-tab.active { border-color: var(--lj-seal); color: var(--lj-seal); background: rgba(127,168,163,.12); }
.fin-f-row { display: flex; gap: 16px; flex-wrap: wrap; }
.fin-f-field { flex: 1; min-width: 220px; }
.fin-f-field.grow { flex: 1.4; }
.fin-f-label { display: block; font-size: 12px; color: var(--lj-text-2); margin-bottom: 6px; letter-spacing: .06em; }
.fin-amount { width: 100%; }
.fin-date { width: 100%; }
.fin-cats { display: flex; flex-wrap: wrap; gap: 8px; }
.fin-cat { padding: 6px 12px; border-radius: 999px; border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .2s; font-family: var(--font-serif); font-size: 13px; }
.fin-cat.active { border-color: var(--lj-ochre); color: var(--lj-ochre); background: rgba(199,169,107,.14); }
.fin-note-row { display: flex; align-items: center; gap: 8px; }
.fin-note-input { flex: 1; padding: 9px 12px; border-radius: 10px; border: 1px solid var(--lj-line); background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); outline: none; }
.fin-note-input:focus { border-color: var(--lj-seal); }
.fin-form-actions { display: flex; justify-content: flex-end; gap: 10px; }
.fd-enter-active,.fd-leave-active { transition: all .28s ease; }
.fd-enter-from,.fd-leave-to { opacity: 0; transform: translateY(-10px); }

/* KPI */
.fin-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px; }
.fin-kpi { display: flex; flex-direction: column; gap: 6px; padding: 18px; border-radius: 16px; position: relative; overflow: hidden; }
.fin-kpi::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--lj-dai), transparent); opacity: .45; }
.fin-kpi-label { font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.fin-kpi-val { font-size: 22px; font-weight: 600; letter-spacing: .02em; }
.fin-kpi-val.income { color: var(--lj-ochre); }
.fin-kpi-val.expense { color: var(--lj-vermilion); }
.fin-kpi-sub { font-size: 11px; color: var(--lj-text-3); }

/* 图表 */
.fin-charts { display: grid; grid-template-columns: 1fr 1.4fr; gap: 16px; margin-bottom: 18px; }
.fin-chart { border-radius: 16px; padding: 18px; }
.fin-chart-title { margin: 0 0 14px; font-size: 15px; letter-spacing: .08em; }
.fin-chart-body { display: flex; gap: 18px; align-items: center; }
.fin-chart-empty { padding: 30px 6px; font-size: 13px; color: var(--lj-text-3); text-align: center; }
.fin-legend { list-style: none; margin: 0; padding: 0; flex: 1; display: flex; flex-direction: column; gap: 8px; max-height: 220px; overflow: auto; }
.fin-legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.fin-dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
.fin-legend-name { flex: 1; color: var(--lj-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fin-legend-amt { color: var(--lj-text); font-weight: 600; }

/* 流水 */
.fin-ledger { border-radius: 16px; padding: 18px; }
.fin-ledger-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 12px; flex-wrap: wrap; }
.fin-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fin-filter { width: 130px; }
.fin-filter-input { padding: 7px 11px; border-radius: 9px; border: 1px solid var(--lj-line); background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); outline: none; width: 180px; }
.fin-filter-input:focus { border-color: var(--lj-seal); }
.fin-list-empty { padding: 40px 6px; text-align: center; color: var(--lj-text-3); font-size: 13px; }
.fin-row { display: flex; align-items: center; gap: 12px; padding: 11px 8px; border-radius: 12px; transition: background .2s; }
.fin-row:hover { background: rgba(127,168,163,.06); }
.fin-row.editing { background: rgba(199,169,107,.10); box-shadow: inset 0 0 0 1px var(--lj-line); }
.fin-row + .fin-row { border-top: 1px solid rgba(127,168,163,.07); }
.fin-row-icon { width: 40px; height: 40px; flex: none; display: grid; place-items: center; font-size: 20px; border-radius: 12px; background: rgba(127,168,163,.12); }
.fin-row-main { flex: 1; min-width: 0; }
.fin-row-top { display: flex; align-items: center; gap: 8px; }
.fin-row-cat { font-size: 14px; font-weight: 600; }
.fin-row-note { font-size: 13px; color: var(--lj-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fin-row-date { font-size: 11px; color: var(--lj-text-3); margin-top: 3px; }
.fin-row-amt { font-size: 16px; font-weight: 600; white-space: nowrap; }
.fin-row-amt.income { color: var(--lj-ochre); }
.fin-row-amt.expense { color: var(--lj-vermilion); }
.fin-row-ops { display: flex; gap: 6px; }
.fin-op { width: 32px; height: 32px; border-radius: 9px; border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .2s; }
.fin-op:hover { border-color: var(--lj-seal); color: var(--lj-seal); }
.fin-op.danger:hover { border-color: var(--lj-vermilion); color: var(--lj-vermilion); }
.fin-pager { display: flex; align-items: center; justify-content: flex-end; gap: 14px; margin-top: 14px; }
.fin-pager-info { font-size: 12px; color: var(--lj-text-3); }

@media (max-width: 900px) {
  .fin-kpis { grid-template-columns: repeat(2, 1fr); }
  .fin-charts { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .fin-page { padding: 88px 14px 50px; }
  .fin-kpis { grid-template-columns: 1fr 1fr; }
  .fin-title { font-size: 22px; }
}
</style>
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
        <div class="fin-period">
          <div class="fin-dim">
            <button class="fin-dim-btn" :class="{ on: dim === 'day' }" @click="setDim('day')">日</button>
            <button class="fin-dim-btn" :class="{ on: dim === 'month' }" @click="setDim('month')">月</button>
            <button class="fin-dim-btn" :class="{ on: dim === 'year' }" @click="setDim('year')">年</button>
          </div>
          <button class="fin-nav" @click="shift(-1)">‹</button>
          <div class="fin-dd-wrap" @keydown.esc="ddOpen = false">
            <button class="fin-month-label" @click.stop="toggleDd">
              {{ periodLabel }}<span v-if="!isNowPeriod" class="fin-this" @click.stop="goNow">回{{ dim === 'day' ? '今天' : (dim === 'year' ? '今年' : '本月') }}</span>
              <span class="fin-dd-caret">▾</span>
            </button>
            <transition name="fd">
              <div v-if="ddOpen" class="fin-dd glass" @click.stop>
                <div class="fin-dd-col">
                  <div class="fin-dd-head">年</div>
                  <div class="fin-dd-list" ref="ddYearList">
                    <button v-for="y in yearOptions" :key="y" class="fin-dd-item" :class="{ on: y === ddYear }" @click="pickYear(y)">{{ y }}</button>
                  </div>
                </div>
                <div v-if="dim !== 'year'" class="fin-dd-col">
                  <div class="fin-dd-head">月</div>
                  <div class="fin-dd-list">
                    <button v-for="m in 12" :key="m" class="fin-dd-item" :class="{ on: m === ddMonth }" @click="pickMonth(m)">{{ m }}</button>
                  </div>
                </div>
                <div v-if="dim === 'day'" class="fin-dd-col">
                  <div class="fin-dd-head">日</div>
                  <div class="fin-dd-list">
                    <button v-for="d in ddDays" :key="d" class="fin-dd-item" :class="{ on: d === ddSelDay }" @click="pickDay(d)">{{ d }}</button>
                  </div>
                </div>
              </div>
            </transition>
          </div>
          <button class="fin-nav" @click="shift(1)">›</button>
        </div>
        <div class="fin-io">
          <button class="fin-btn ghost small" @click="exportCsv">导出 CSV</button>
          <label class="fin-btn ghost small fin-import">
            导入账本
            <input type="file" accept=".csv,.xlsx,.xlsm,.xls,text/csv,text/plain,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel" class="fin-import-file" @change="onImportFile" />
          </label>
          <a class="fin-help" href="javascript:void(0)" @click="showImportHelp = !showImportHelp">导入格式说明</a>
        </div>
      </div>

      <!-- 导入说明 -->
      <transition name="fd">
        <div v-if="showImportHelp" class="fin-io-help glass">
          <h4 class="fin-io-help-title">导入格式说明</h4>
          <p class="fin-io-help-line">支持 <b>.csv / .xlsx / .xlsm</b>（表格与文本均可）。</p>
          <p class="fin-io-help-line">无需手动整理：任意表头或杂乱格式（微信/支付宝/银行/Excel 导出），均由 <b>AI 自动识别</b>为「日期 / 收支 / 分类 / 金额 / 备注」并精简后展示，确认后再入库。</p>
          <p class="fin-io-help-line">规则参考：金额为负或「支/消费」语境归支出、为正归收入；分类缺失归「其他」；可上传本站「导出 CSV」的文件批量还原。</p>
          <p class="fin-io-help-line">旧版 <code>.xls</code> 请先另存为 <code>.xlsx</code> 或 CSV。</p>
        </div>
      </transition>

      <!-- 智能导入预览（内联面板，非弹窗） -->
      <transition name="fd">
        <section v-if="importing.analyzing || importing.rows.length || importing.skipped || importing.errors.length" class="fin-import-panel glass">
          <div class="fin-import-panel-head">
            <span class="fin-import-panel-title">🤖 智能导入预览</span>
            <span v-if="importing.analyzing" class="fin-import-loading">AI 正在识别并精简数据…</span>
            <span v-else class="fin-import-done">识别完成</span>
            <button class="fin-form-close" @click="cancelImport">✕</button>
          </div>

          <div v-if="importing.analyzing" class="fin-import-empty">正在读取并识别文件，请稍候…</div>

          <template v-else>
            <div class="fin-import-summary">
              <span>识别出 <b>{{ importing.rows.length }}</b> 条流水</span>
              <span v-if="importing.skipped">跳过 <b class="warn">{{ importing.skipped }}</b> 条无效数据</span>
              <span v-if="importing.summary" class="fin-import-ai">{{ importing.summary }}</span>
              <span v-if="importing.is_fake" class="fin-import-fake">未配置 AI Provider，已用本地规则解析</span>
            </div>

            <div v-if="importing.errors.length" class="fin-import-errors">
              <span v-for="(err, i) in importing.errors" :key="i" class="fin-import-err">{{ err }}</span>
            </div>

            <table v-if="importing.rows.length" class="fin-import-table">
              <thead>
                <tr><th>日期</th><th>收支</th><th>分类</th><th>金额</th><th>备注</th></tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in importing.rows" :key="i">
                  <td>{{ r.date }}</td>
                  <td><span class="fin-import-type" :class="r.type">{{ r.type === 'income' ? '收' : '支' }}</span></td>
                  <td>{{ r.category }}</td>
                  <td class="fin-import-amt" :class="r.type">{{ r.type === 'income' ? '+' : '−' }} ¥ {{ money(r.amount) }}</td>
                  <td class="fin-import-note">{{ r.note }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="fin-import-empty">没有识别到有效流水，请检查文件格式。</div>

            <div class="fin-import-actions">
              <button class="fin-btn ghost" @click="cancelImport">取消</button>
              <button class="fin-btn primary" :disabled="!importing.rows.length || importing.confirming" @click="doConfirmImport">
                {{ importing.confirming ? '导入中…' : `确认导入 ${importing.rows.length} 条` }}
              </button>
            </div>
          </template>
        </section>
      </transition>

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
              <div class="fin-f-label-row">
                <label class="fin-f-label">分类</label>
                <button class="fin-cat-manage" @click="openCatDialog">管理分类</button>
              </div>
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

      <!-- 手机端数据视图：净流入是主指标，避免四张等权卡片挤占首屏 -->
      <section class="fin-kpis fin-kpis-mobile" aria-label="账本数据概览">
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}净流入</span>
          <span class="fin-kpi-val">{{ periodNet >= 0 ? '+' : '−' }} ¥ {{ money(Math.abs(periodNet)) }}</span>
          <span class="fin-kpi-sub">收入减支出</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}支出</span>
          <span class="fin-kpi-val" :class="summary.expense ? 'expense' : ''">¥ {{ money(summary.expense) }}</span>
          <span class="fin-kpi-sub">消费总额</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">流水笔数</span>
          <span class="fin-kpi-val">{{ summary.count }}</span>
          <span class="fin-kpi-sub">笔记录</span>
        </div>
      </section>

      <!-- 桌面端保持原数据布局 -->
      <section class="fin-kpis fin-kpis-desktop">
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}收入</span>
          <span class="fin-kpi-val income">+ ¥ {{ money(summary.income) }}</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}支出</span>
          <span class="fin-kpi-val expense">− ¥ {{ money(summary.expense) }}</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}笔数</span>
          <span class="fin-kpi-val">{{ summary.count }}</span>
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
          <h2 class="fin-chart-title">{{ unitLabel }}支出分类占比</h2>
          <div v-if="summary.categories.length" class="fin-chart-body">
            <DonutChart :data="summary.categories" />
            <ul class="fin-legend">
              <li v-for="c in summary.categories" :key="c.category" class="fin-legend-item">
                <i class="fin-dot" :style="{ background: c.color }"></i>
                <span class="fin-legend-name">{{ c.icon }} {{ c.category }}</span>
                <span class="fin-legend-pct">{{ pct(c.amount) }}%</span>
                <span class="fin-legend-amt">¥ {{ money(c.amount) }}</span>
              </li>
            </ul>
          </div>
          <div v-else class="fin-chart-empty">{{ unitLabel }}暂无支出，去「记一笔」吧</div>
        </div>

        <div class="fin-chart glass">
          <h2 class="fin-chart-title">{{ unitLabel }}收支趋势</h2>
          <div v-if="dim !== 'day' && summary.trends.length" class="fin-chart-body">
            <TrendChart :days="summary.trends" :has-any="hasAnyTrend" />
          </div>
          <div v-else class="fin-chart-empty">{{ dim === 'day' ? '单日无跨期趋势，切换「月/年」查看' : '暂无数据' }}</div>
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
                size="small"
                @current-change="onPage"
              />
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- ============ 分类管理弹窗 ============ -->
    <div class="fin-cat-dialog">
      <el-dialog
        v-model="catDialog"
        :title="catDialogTitle"
        width="520px"
        :close-on-click-modal="false"
      >
        <!-- 自定义分类 -->
        <div class="fin-cd-section">
          <div class="fin-cd-head">
            <span class="fin-cd-title">自定义分类</span>
            <span class="fin-cd-note">改名会同步更新已记账的流水，不会留下「孤儿分类」</span>
          </div>

          <div v-if="customCats.length" class="fin-cd-list">
            <div v-for="c in customCats" :key="c.id" class="fin-cd-row">
              <el-select v-model="c.icon" class="fin-cd-icon" @change="(v) => saveCat(c, c.key, v)">
                <el-option v-for="e in ICON_PRESETS" :key="e" :label="e" :value="e" />
              </el-select>
              <el-input
                :model-value="c.key"
                class="fin-cd-name"
                maxlength="12"
                show-word-limit
                @change="(v) => saveCat(c, v, c.icon)"
              />
              <el-popconfirm
                title="删除后不再出现在选择列表；已记账的流水仍保留这个分类名"
                confirm-button-text="删除"
                cancel-button-text="取消"
                width="240"
                @confirm="removeCat(c)"
              >
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <p v-else class="fin-cd-empty">还没有自定义分类，用下面的输入框加一个。</p>

          <div class="fin-cd-add">
            <el-select v-model="newCat.icon" class="fin-cd-icon">
              <el-option v-for="e in ICON_PRESETS" :key="e" :label="e" :value="e" />
            </el-select>
            <el-input
              v-model="newCat.name"
              class="fin-cd-name"
              maxlength="12"
              placeholder="如：宠物、通勤、房贷"
              @keyup.enter="addCat"
            />
            <el-button type="primary" :loading="catSaving" @click="addCat">添加</el-button>
          </div>
        </div>

        <!-- 内置分类（只读） -->
        <div class="fin-cd-section">
          <div class="fin-cd-head">
            <span class="fin-cd-title">内置分类</span>
            <span class="fin-cd-note">系统自带，不可修改删除</span>
          </div>
          <div class="fin-cd-builtin">
            <span v-for="c in builtinCats" :key="c.key" class="fin-cd-chip">{{ c.icon }} {{ c.key }}</span>
          </div>
        </div>

        <template #footer>
          <el-button @click="catDialog = false">关闭</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import VoiceInputButton from '@/components/VoiceInputButton.vue'
import DonutChart from '@/components/finance/DonutChart.vue'
import TrendChart from '@/components/finance/TrendChart.vue'
import { financeApi, exportFinanceCsv } from '@/api/finance'

function backToTopScroll() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const typeTabs = [
  { key: 'expense', label: '支出' },
  { key: 'income', label: '收入' },
]
const PALETTE = ['#7FA8A3', '#C7A96B', '#6E8BA6', '#B98BA6', '#8BB07A', '#C98B6B', '#6FA6C9', '#A98BC9', '#7F8FA3']

const now = new Date()
const pad = (n) => String(n).padStart(2, '0')
const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
const dim = ref('month')
const day = ref(today)
const month = ref(`${now.getFullYear()}-${pad(now.getMonth() + 1)}`)
const year = ref(String(now.getFullYear()))
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

const periodLabel = computed(() => {
  if (dim.value === 'day') {
    const [y, m, d] = day.value.split('-')
    return `${y}年${Number(m)}月${Number(d)}日`
  }
  if (dim.value === 'year') return `${year.value}年`
  const [y, m] = month.value.split('-')
  return `${y}年${Number(m)}月`
})
const isNowPeriod = computed(() => {
  if (dim.value === 'day') return day.value === today
  if (dim.value === 'year') return year.value === String(now.getFullYear())
  return month.value === `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
})
const unitLabel = computed(() => (dim.value === 'day' ? '今日' : (dim.value === 'year' ? '本年' : '本月')))
const periodNet = computed(() => Number(summary.value.income || 0) - Number(summary.value.expense || 0))

const ddOpen = ref(false)
const ddYear = ref(now.getFullYear())
const ddMonth = ref(now.getMonth() + 1)
const ddYearList = ref(null)
const yearOptions = computed(() => {
  const max = now.getFullYear()
  const min = Math.min(summary.value.min_year || max, max)
  const arr = []
  for (let y = max; y >= min; y--) arr.push(y)
  return arr
})
const ddDays = computed(() => new Date(ddYear.value, ddMonth.value, 0).getDate())
const ddSelDay = computed(() => {
  if (dim.value !== 'day') return 0
  const [y, m, d] = day.value.split('-').map(Number)
  return (y === ddYear.value && m === ddMonth.value) ? d : 0
})
function toggleDd() {
  if (ddOpen.value) { ddOpen.value = false; return }
  if (dim.value === 'year') {
    ddYear.value = parseInt(year.value) || now.getFullYear()
    ddMonth.value = 1
  } else if (dim.value === 'day') {
    const [y, m] = day.value.split('-').map(Number)
    ddYear.value = y; ddMonth.value = m
  } else {
    const [y, m] = month.value.split('-').map(Number)
    ddYear.value = y; ddMonth.value = m
  }
  ddOpen.value = true
  nextTick(() => {
    const el = ddYearList.value
    if (!el) return
    const active = el.querySelector('.fin-dd-item.on')
    if (active) active.scrollIntoView({ block: 'center' })
  })
}
function pickYear(y) {
  ddYear.value = y
  if (dim.value !== 'year') return
  year.value = String(y)
  closeDd()
}
function pickMonth(m) {
  if (dim.value === 'year') return
  ddMonth.value = m
  if (dim.value === 'month') {
    month.value = `${ddYear.value}-${pad(m)}`
    closeDd()
  }
}
function pickDay(d) {
  if (dim.value !== 'day') return
  day.value = `${ddYear.value}-${pad(ddMonth.value)}-${pad(d)}`
  closeDd()
}
function closeDd() {
  ddOpen.value = false
  page.value = 1
  loadSummary()
  loadList()
}
function onDocClick() { if (ddOpen.value) ddOpen.value = false }
const currentCats = computed(() => {
  const pool = form.type === 'income' ? categoriesMeta.value.income : categoriesMeta.value.expense
  return pool.length ? pool : [{ key: '其他', icon: '🧾' }]
})
const hasAnyTrend = computed(() => (summary.value.trends || []).some(d => d.income || d.expense))

function money(v) { return Number(v || 0).toFixed(2) }
function pct(v) {
  const t = summary.value.categories.reduce((s, c) => s + (c.amount || 0), 0)
  if (!t) return '0'
  return ((v || 0) / t * 100).toFixed(1)
}
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

/* ---- 自定义分类管理 ---- */
// 常见图标预设：给个够用的小抄，省得用户为了一个 emoji 去翻输入法
const ICON_PRESETS = [
  '🍜', '🍚', '☕', '🛒', '🛍️', '🚇', '🚗', '✈️', '🏠', '💡',
  '🎮', '🎬', '🎵', '📚', '🎓', '💊', '🏥', '🏋️', '🐱', '🐾',
  '👶', '🎁', '🧧', '💐', '🧴', '🛠️', '📱', '💰', '📈', '🧾',
]
const catDialog = ref(false)
const catSaving = ref(false)
const newCat = ref({ icon: ICON_PRESETS[0], name: '' })

// 管理面板跟随当前收支方向：在「支出」下打开就管支出分类
const currentPool = computed(() => (
  form.type === 'income' ? categoriesMeta.value.income : categoriesMeta.value.expense
))
const customCats = computed(() => currentPool.value.filter(c => c.is_custom))
const builtinCats = computed(() => currentPool.value.filter(c => !c.is_custom))
const catDialogTitle = computed(() => (form.type === 'income' ? '管理收入分类' : '管理支出分类'))

function openCatDialog() {
  newCat.value = { icon: ICON_PRESETS[0], name: '' }
  catDialog.value = true
}

async function addCat() {
  const name = (newCat.value.name || '').trim()
  if (!name) {
    ElMessage.warning('请输入分类名')
    return
  }
  catSaving.value = true
  try {
    await financeApi.createCategory({ type: form.type, name, icon: newCat.value.icon })
    ElMessage.success(`已添加「${name}」`)
    newCat.value = { icon: newCat.value.icon, name: '' }
    await loadCategories()
  } catch { /* 错误已由 api 拦截器提示 */ } finally {
    catSaving.value = false
  }
}

async function saveCat(cat, name, icon) {
  const next = (name || '').trim()
  if (!next) {
    ElMessage.warning('分类名不能为空')
    await loadCategories()
    return
  }
  if (next === cat.key && icon === cat.icon) return
  try {
    await financeApi.updateCategory(cat.id, { type: form.type, name: next, icon })
    ElMessage.success('已更新')
    // 正在记的这笔如果选的就是它，跟着改名，否则保存时会被归成「其他」
    if (form.category === cat.key) form.category = next
    await loadCategories()
  } catch {
    await loadCategories()   // 回滚界面上的乐观改动
  }
}

async function removeCat(cat) {
  try {
    const res = await financeApi.deleteCategory(cat.id)
    ElMessage.success(res.msg || '已删除')
    if (form.category === cat.key) form.category = '其他'
    await loadCategories()
    await loadSummary()
  } catch { /* 错误已由 api 拦截器提示 */ }
}
async function loadSummary() {
  const params = { dim: dim.value }
  if (dim.value === 'day') params.day = day.value
  else if (dim.value === 'year') params.year = year.value
  else params.month = month.value
  const res = await financeApi.summary(params)
  summary.value = { ...res.data, categories: (res.data.categories || []).map((c, i) => ({ ...c, color: PALETTE[i % PALETTE.length] })) }
}
function onPage(p) {
  page.value = p
  loadList()
}

async function loadList() {
  const params = { page: page.value, size: pageSize }
  if (filters.type) params.type = filters.type
  if (filters.q) params.q = filters.q
  const res = await financeApi.list(params)
  list.value = res.data.list
  total.value = res.data.total
}
function handleCurrentChange() {}
const showImportHelp = ref(false)
async function exportCsv() {
  let start, end
  if (dim.value === 'day') {
    start = day.value
    end = day.value
  } else if (dim.value === 'year') {
    start = `${year.value}-01-01`
    end = `${year.value}-12-31`
  } else {
    const [y, m] = month.value.split('-').map(Number)
    start = `${month.value}-01`
    end = `${month.value}-${pad(new Date(y, m, 0).getDate())}`
  }
  try {
    await exportFinanceCsv({ start, end })
    ElMessage.success('CSV 已导出')
  } catch (e) {
    ElMessage.error('导出失败，请重试')
  }
}
const importing = reactive({
  analyzing: false,
  confirming: false,
  rows: [],
  skipped: 0,
  errors: [],
  summary: '',
  is_fake: false,
})

async function onImportFile(e) {
  const file = e.target.files && e.target.files[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file) return
  try {
    importing.analyzing = true
    importing.rows = []
    importing.skipped = 0
    importing.errors = []
    importing.summary = ''
    importing.is_fake = false
    const ext = (file.name.split('.').pop() || '').toLowerCase()
    const res = /^(xlsx|xlsm|xls)$/.test(ext)
      ? await financeApi.analyzeImportFile(file)
      : await financeApi.analyzeImport(await file.text())
    const d = res.data || {}
    importing.rows = d.rows || []
    importing.skipped = d.skipped || 0
    importing.errors = d.errors || []
    importing.summary = d.summary || ''
    importing.is_fake = !!d.is_fake
    if (!importing.rows.length && !importing.errors.length) ElMessage.warning('未识别到有效流水，请检查文件内容')
  } catch (err) {
    const d = err?.response?.data?.detail
    const msg = typeof d === 'string' ? d : (d?.msg || err?.message || '识别失败，请重试')
    ElMessage.error(`识别失败：${msg}`)
  } finally {
    importing.analyzing = false
  }
}

function cancelImport() {
  importing.rows = []
  importing.skipped = 0
  importing.errors = []
  importing.summary = ''
  importing.is_fake = false
  importing.analyzing = false
  importing.confirming = false
}

async function doConfirmImport() {
  if (!importing.rows.length) return
  importing.confirming = true
  try {
    const res = await financeApi.confirmImport(importing.rows)
    const d = res.data || {}
    ElMessage.success(`导入成功 ${d.imported} 条`)
    cancelImport()
    reloadAndScroll()
  } catch (err) {
    ElMessage.error('导入失败，请重试')
  } finally {
    importing.confirming = false
  }
}

function reload(p) {
  if (p) page.value = p
  return loadList()
}
function setDim(d) {
  if (dim.value === d || !['day', 'month', 'year'].includes(d)) return
  dim.value = d
  page.value = 1
  loadSummary()
  loadList()
}
function shift(step) {
  if (dim.value === 'day') {
    const nv = new Date(`${day.value}T12:00:00`)
    nv.setDate(nv.getDate() + step)
    day.value = fmtDate(nv)
  } else if (dim.value === 'year') {
    year.value = String(Number(year.value) + step)
  } else {
    const [y, m] = month.value.split('-').map(Number)
    const totalM = y * 12 + (m - 1) + step
    month.value = `${Math.floor(totalM / 12)}-${pad((totalM % 12) + 1)}`
  }
  page.value = 1
  loadSummary()
  loadList()
}
function goNow() {
  if (dim.value === 'day') day.value = today
  else if (dim.value === 'year') year.value = String(now.getFullYear())
  else month.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
  page.value = 1
  loadSummary()
  loadList()
}
async function reloadAndScroll() {
  await Promise.all([loadSummary(), reload(1)])
  backToTopScroll()
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
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
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
.fin-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.fin-period { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.fin-dim { display: flex; align-items: center; gap: 2px; padding: 3px; border-radius: 999px; background: rgba(127,168,163,.08);
  border: 1px solid var(--lj-line); }
.fin-dim-btn { border: 0; background: transparent; color: var(--lj-text-3); font-size: 12px; padding: 5px 14px; border-radius: 999px;
  cursor: pointer; font-family: var(--font-serif); letter-spacing: .08em; transition: all .2s; }
.fin-dim-btn:hover { color: var(--lj-text); }
.fin-dim-btn.on { color: #fff; background: var(--lj-dai); box-shadow: 0 2px 8px rgba(0,0,0,.25); }
.fin-nav { width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--lj-line); background: var(--lj-glass);
  color: var(--lj-text); font-size: 18px; cursor: pointer; transition: all .2s; }
.fin-nav:hover { border-color: var(--lj-line-strong); }
.fin-month-label { border: 1px solid var(--lj-line); background: var(--lj-glass); color: var(--lj-text);
  padding: 7px 16px; border-radius: 999px; font-family: var(--font-serif); letter-spacing: .1em; font-size: 16px;
  cursor: pointer; transition: border-color .2s; white-space: nowrap; }
.fin-month-label:hover { border-color: var(--lj-line-strong); }
.fin-this { margin-left: 8px; font-size: 11px; color: var(--lj-dai); cursor: pointer; }
.fin-dd-caret { margin-left: 8px; font-size: 12px; color: var(--lj-text-3); }
.fin-dd-wrap { position: relative; }
.fin-dd { position: absolute; top: calc(100% + 8px); left: 50%; transform: translateX(-50%); z-index: 60;
  display: flex; gap: 8px; padding: 12px; border-radius: 16px; box-shadow: 0 14px 40px rgba(0,0,0,.28); min-width: 240px; }
.fin-dd-col { display: flex; flex-direction: column; gap: 6px; min-width: 78px; }
.fin-dd-head { font-size: 11px; color: var(--lj-text-3); text-align: center; letter-spacing: .2em; padding: 2px 0; }
.fin-dd-list { max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px;
  scrollbar-width: thin; scrollbar-color: var(--lj-line-strong) transparent; padding-right: 2px; }
.fin-dd-list::-webkit-scrollbar { width: 6px; }
.fin-dd-list::-webkit-scrollbar-thumb { background: var(--lj-line-strong); border-radius: 3px; }
.fin-dd-item { border: 0; background: transparent; color: var(--lj-text-2); font-size: 13px; padding: 6px 10px;
  border-radius: 8px; cursor: pointer; font-family: var(--font-serif); transition: all .15s; text-align: center; }
.fin-dd-item:hover { background: rgba(127,168,163,.12); color: var(--lj-text); }
.fin-dd-item.on { color: #fff; background: var(--lj-dai); font-weight: 600; }

/* 导入/导出 */
.fin-io { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fin-import { position: relative; display: inline-block; margin: 0; }
.fin-import-file { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.fin-help { font-size: 12px; color: var(--lj-text-3); text-decoration: none; letter-spacing: .04em; }
.fin-help:hover { color: var(--lj-dai); }
.fin-io-help { padding: 14px 18px; border-radius: 14px; margin-bottom: 14px; }
.fin-io-help-title { margin: 0 0 8px; font-size: 14px; letter-spacing: .06em; }
.fin-io-help-line { margin: 4px 0; font-size: 12.5px; color: var(--lj-text-2); }
.fin-io-help-line code { background: rgba(127,168,163,.14); padding: 1px 6px; border-radius: 5px; color: var(--lj-seal); }

/* 智能导入预览 */
.fin-import-panel { padding: 16px 18px; border-radius: 16px; margin-bottom: 16px; }
.fin-import-panel-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.fin-import-panel-title { font-size: 15px; font-weight: 600; letter-spacing: .04em; color: var(--lj-seal); }
.fin-import-loading { font-size: 12.5px; color: var(--lj-text-2); animation: fin-pulse 1.2s ease-in-out infinite; }
.fin-import-done { font-size: 12px; padding: 2px 10px; border-radius: 999px; background: rgba(127,168,163,.16); color: var(--lj-seal); }
@keyframes fin-pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
.fin-import-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; font-size: 13px; margin-bottom: 10px; color: var(--lj-text); }
.fin-import-summary b { color: var(--lj-seal); }
.fin-import-summary b.warn { color: var(--lj-cinnabar, #c27053); }
.fin-import-ai { flex: 1 1 100%; font-size: 12.5px; color: var(--lj-text-2); font-style: italic; }
.fin-import-fake { font-size: 11.5px; padding: 2px 10px; border-radius: 999px; background: rgba(199,169,107,.18); color: var(--lj-gold, #b18a4a); }
.fin-import-errors { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-bottom: 10px; font-size: 12px; color: var(--lj-cinnabar, #c27053); }
.fin-import-empty { padding: 18px 0; text-align: center; font-size: 13px; color: var(--lj-text-2); }
.fin-import-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.fin-import-table th { text-align: left; padding: 7px 10px; font-weight: 600; font-size: 12px; color: var(--lj-text-2); border-bottom: 1px solid var(--lj-line);
  background: rgba(127,168,163,.08); }
.fin-import-table td { padding: 8px 10px; border-bottom: 1px dashed var(--lj-line); vertical-align: middle; }
.fin-import-type { display: inline-block; min-width: 24px; text-align: center; padding: 1px 8px; border-radius: 999px; font-size: 12px; }
.fin-import-type.income { background: rgba(127,168,163,.16); color: var(--lj-seal); }
.fin-import-type.expense { background: rgba(194,150,120,.18); color: var(--lj-cinnabar, #c27053); }
.fin-import-amt { white-space: nowrap; font-variant-numeric: tabular-nums; }
.fin-import-amt.income { color: var(--lj-seal); }
.fin-import-amt.expense { color: var(--lj-cinnabar, #c27053); }
.fin-import-note { color: var(--lj-text-2); max-width: 260px; }
.fin-import-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 14px; }

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
.fin-f-label-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.fin-cat-manage { background: none; border: none; padding: 0; cursor: pointer; font-size: 12px; color: var(--lj-ochre); font-family: var(--font-serif); letter-spacing: .04em; }
.fin-cat-manage:hover { text-decoration: underline; }

/* 分类管理弹窗 */
.fin-cd-section { margin-bottom: 20px; }
.fin-cd-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.fin-cd-title { font-size: 14px; color: var(--lj-text); letter-spacing: .06em; }
.fin-cd-note { font-size: 12px; color: var(--lj-text-3); }
.fin-cd-list { display: flex; flex-direction: column; gap: 8px; }
.fin-cd-row, .fin-cd-add { display: flex; align-items: center; gap: 8px; }
.fin-cd-icon { width: 76px; flex: none; }
.fin-cd-name { flex: 1; }
.fin-cd-empty { font-size: 13px; color: var(--lj-text-3); margin: 0 0 10px; }
.fin-cd-add { margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--lj-line); }
.fin-cd-builtin { display: flex; flex-wrap: wrap; gap: 8px; }
.fin-cd-chip { padding: 4px 10px; border-radius: 999px; border: 1px solid var(--lj-line); font-size: 12px; color: var(--lj-text-3); }
.fin-note-row { display: flex; align-items: center; gap: 8px; }
.fin-note-input { flex: 1; padding: 9px 12px; border-radius: 10px; border: 1px solid var(--lj-line); background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); outline: none; }
.fin-note-input:focus { border-color: var(--lj-seal); }
.fin-form-actions { display: flex; justify-content: flex-end; gap: 10px; }
.fd-enter-active,.fd-leave-active { transition: all .28s ease; }
.fd-enter-from,.fd-leave-to { opacity: 0; transform: translateY(-10px); }

/* KPI */
.fin-kpis-mobile { display: none; }
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
.fin-legend-pct { flex: none; font-size: 12px; color: var(--lj-seal); font-weight: 600; font-variant-numeric: tabular-nums; width: 46px; text-align: right; }
.fin-legend-amt { color: var(--lj-text); font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }

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

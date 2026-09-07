<template>
  <div class="st-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="st-inner">
      <!-- 页头 -->
      <header class="st-head">
        <div class="st-head-left"><BackButton class="st-back" /></div>
        <div class="st-titles">
          <h1 class="st-title">行情</h1>
          <p class="st-sub">自选股 · 持仓盈亏 · 实时报价</p>
        </div>
        <div class="st-head-right">
          <button class="st-btn ghost" :disabled="refreshing" @click="loadAll(true)">{{ refreshing ? '刷新中…' : '⟳ 刷新' }}</button>
          <button class="st-btn primary" @click="openAdd">{{ adding ? '关闭' : '＋ 加自选' }}</button>
        </div>
      </header>

      <!-- KPI 汇总 -->
      <section class="st-kpi">
        <div class="st-kpi-card glass">
          <span class="st-kpi-k">持仓市值</span>
          <span class="st-kpi-v">¥ {{ fmt(summary.market_value) }}</span>
          <span class="st-kpi-s">{{ summary.symbol_count }} 只自选</span>
        </div>
        <div class="st-kpi-card glass">
          <span class="st-kpi-k">今日盈亏</span>
          <span class="st-kpi-v" :class="pnlCls(summary.today_pnl)">{{ sign(summary.today_pnl) }}¥ {{ fmt(Math.abs(summary.today_pnl ?? 0)) }}</span>
          <span class="st-kpi-s">按持仓量估算</span>
        </div>
        <div class="st-kpi-card glass">
          <span class="st-kpi-k">持有盈亏</span>
          <span class="st-kpi-v" :class="pnlCls(summary.hold_pct)">{{ sign(summary.hold_pct) }}{{ fmt(summary.hold_pct, 2) }}%</span>
          <span class="st-kpi-s">成本均价对比现价</span>
        </div>
      </section>

      <!-- 加自选（内联面板，无弹窗） -->
      <transition name="st-panel">
        <section v-if="adding" class="st-form glass">
          <div class="st-form-head">
            <span class="st-form-title">加自选股</span>
            <span class="st-form-hint">输入代码查询，加入后自动识别名称</span>
            <button class="st-form-close" @click="closeAdd">✕</button>
          </div>
          <div class="st-form-row">
            <div class="st-f-field">
              <label class="st-f-label">市场</label>
              <select v-model="addMarket" class="st-input st-select">
                <option value="sh">沪 A</option>
                <option value="sz">深 A</option>
                <option value="hk">港股</option>
                <option value="us">美股</option>
              </select>
            </div>
            <div class="st-f-field grow">
              <label class="st-f-label">代码</label>
              <input v-model="addCode" class="st-input" placeholder="如 600519 / 00700 / AAPL" spellcheck="false"
                @input="onCodeInput" @keyup.enter="doAdd" />
            </div>
            <div class="st-f-field">
              <label class="st-f-label">数量（可选）</label>
              <input v-model.number="addQty" class="st-input" type="number" min="0" placeholder="持仓股数" />
            </div>
            <div class="st-f-field">
              <label class="st-f-label">成本价（可选）</label>
              <input v-model.number="addCost" class="st-input" type="number" min="0" step="0.01" placeholder="持仓成本" />
            </div>
          </div>

          <!-- 联想结果 -->
          <div v-if="sug.length" class="st-sug">
            <button v-for="s in sug" :key="s.market + s.code" class="st-sug-item" @click="pickSug(s)">
              <span class="st-sug-name">{{ s.name }}</span>
              <span class="st-sug-code">{{ s.market.toUpperCase() }} {{ s.code }}</span>
            </button>
          </div>

          <div class="st-form-actions">
            <span class="st-save-tip">模糊搜索「腾讯」「贵州」或代码均可自动匹配</span>
            <button class="st-btn primary" :disabled="addingSave" @click="doAdd">{{ addingSave ? '加入中…' : '加入自选' }}</button>
          </div>
        </section>
      </transition>

      <!-- 自选列表 -->
      <section class="st-list glass">
        <div class="st-list-head">
          <span class="st-list-title">自选股</span>
          <span class="st-list-sub" v-if="list.length">点击名称查看 K 线详情</span>
        </div>

        <!-- 桌面表格 -->
        <div v-if="!loading && list.length" class="st-table-wrap" :style="{ display: isMobile ? 'none' : 'block' }">
          <table class="st-table">
            <thead>
              <tr>
                <th>名称 / 代码</th><th class="r">现价</th><th class="r">涨跌幅</th>
                <th class="r">持仓</th><th class="r">持仓盈亏</th><th class="r">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="it in list" :key="it.id">
                <td>
                  <span class="st-td-name" @click="goDetail(it)">{{ it.name }}</span>
                  <span class="st-td-code">{{ it.market.toUpperCase() }} {{ it.code }}</span>
                  <span @click="toggleEdit(it)" class="st-td-edit">{{ editingId === it.id ? '收起' : '✎' }}</span>
                </td>
                <td class="r st-num">{{ fmt(it.price) }}</td>
                <td class="r" :class="pnlCls(it.pct)">{{ sign(it.pct) }}{{ fmt(it.pct, 2) }}%</td>
                <td class="r st-num">
                  <template v-if="editingId === it.id">
                    <input v-model.number="editQty" class="st-cell-input" type="number" min="0" placeholder="股数" />
                    <input v-model.number="editCost" class="st-cell-input" type="number" min="0" step="0.01" placeholder="成本" />
                  </template>
                  <template v-else>{{ it.quantity ? `${it.quantity}股` : '—' }}</template>
                </td>
                <td class="r" :class="pnlCls(it.hold_pnl)">
                  <template v-if="editingId === it.id">
                    <button class="st-btn tiny" @click="saveEdit(it)">保存</button>
                  </template>
                  <template v-else-if="it.quantity">{{ sign(it.hold_pnl) }}¥{{ fmt(Math.abs(it.hold_pnl ?? 0)) }}<br /><i class="st-sub-pct">{{ sign(it.hold_pct) }}{{ fmt(it.hold_pct, 2) }}%</i></template>
                  <template v-else>—</template>
                </td>
                <td class="r">
                  <button class="st-btn ghost tiny danger" @click="remove(it)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 移动端卡片 -->
        <div v-if="!loading && list.length && isMobile" class="st-cards">
          <div v-for="it in list" :key="'c'+it.id" class="st-card glass-inner">
            <div class="st-card-h">
              <div class="st-card-name" @click="goDetail(it)">{{ it.name }}<span class="st-card-code">{{ it.market.toUpperCase() }} {{ it.code }}</span></div>
              <button class="st-btn ghost tiny danger" @click="remove(it)">删除</button>
            </div>
            <div class="st-card-row">
              <span>现价 <b>{{ fmt(it.price) }}</b></span>
              <span :class="pnlCls(it.pct)">{{ sign(it.pct) }}{{ fmt(it.pct, 2) }}%</span>
            </div>
            <div v-if="it.quantity" class="st-card-row">
              <span>持仓 {{ it.quantity }}股 · 成本{{ fmt(it.cost_price) }}</span>
              <span :class="pnlCls(it.hold_pnl)">{{ sign(it.hold_pnl) }}¥{{ fmt(Math.abs(it.hold_pnl ?? 0)) }}</span>
            </div>
          </div>
        </div>

        <div v-if="!loading && !list.length" class="st-empty">还没有自选股，点右上角「加自选」开始盯盘</div>
        <div v-else-if="loading" class="st-empty">加载中…</div>
      </section>

      <footer class="st-risk">自用工具，数据仅供参考，不构成投资建议 · 行情数据未实时持久化，仅供参考</footer>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { stocksApi } from '@/api/stocks'

const router = useRouter()
const list = ref([])
const loading = ref(true)
const refreshing = ref(false)
const summary = reactive({ market_value: 0, today_pnl: 0, hold_pct: 0, symbol_count: 0 })

const adding = ref(false)
const addingSave = ref(false)
const addMarket = ref('sh')
const addCode = ref('')
const addQty = ref(null)
const addCost = ref(null)
const sug = ref([])
let sugTimer = null

const editingId = ref(null)
const editQty = ref(null)
const editCost = ref(null)

const isMobile = ref(window.innerWidth < 760)
function onResize() { isMobile.value = window.innerWidth < 760 }
function sign(v) { return v > 0 ? '+' : '' }
function fmt(v, n = 2) { return v == null ? '--' : Number(v).toFixed(n) }
function pnlCls(v) { return v > 0 ? 'up' : v < 0 ? 'down' : 'flat' }

async function loadAll(force = false) {
  if (force) refreshing.value = true
  loading.value = true
  try {
    const [wlr, sr] = await Promise.all([stocksApi.watchlist(), stocksApi.summary()])
    list.value = wlr.data?.list || []
    Object.assign(summary, sr.data || {})
  } catch (e) { /* 已在拦截器提示 */ }
  finally {
    loading.value = false
    refreshing.value = false
  }
}

function openAdd() {
  addCode.value = ''; addQty.value = null; addCost.value = null; sug.value = []
  adding.value = !adding.value
}
function closeAdd() { adding.value = false; sug.value = [] }

function onCodeInput() {
  clearTimeout(sugTimer)
  const q = addCode.value.trim()
  if (!q) { sug.value = []; return }
  sugTimer = setTimeout(async () => {
    try { sug.value = (await stocksApi.search(q)).data?.list || [] }
    catch (e) { sug.value = [] }
  }, 300)
}
function pickSug(s) {
  addCode.value = s.code
  addMarket.value = s.market
  sug.value = []
}
async function remove(it) {
  try {
    await stocksApi.remove(it.id)
    list.value = list.value.filter(x => x.id !== it.id)
    ElMessage.success('已删除')
  } catch (e) { /* handled */ }
}
async function doAdd() {
  const code = addCode.value.trim()
  if (!code) { ElMessage.warning('请填写股票代码'); return }
  addingSave.value = true
  try {
    const r = await stocksApi.add({
      code, market: addMarket.value,
      quantity: addQty.value || null, cost_price: addCost.value || null,
    })
    ElMessage.success(`已加入自选「${r.data.name}」`)
    adding.value = false; sug.value = []
    await loadAll()
  } catch (e) {
    const msg = e?.response?.data?.detail
    if (typeof msg === 'object' && msg?.msg) ElMessage.error(msg.msg)
  } finally { addingSave.value = false }
}

function toggleEdit(it) {
  editingId.value = editingId.value === it.id ? null : it.id
  editQty.value = it.quantity; editCost.value = it.cost_price
}
async function saveEdit(it) {
  try {
    const r = await stocksApi.update(it.id, { quantity: editQty.value || 0, cost_price: editCost.value })
    const fresh = r.data || {}
    Object.assign(it, fresh, fresh.quote ? { price: fresh.price, pct: fresh.pct, change: fresh.change } : {})
    if (fresh.hold_pnl != null) { it.hold_pnl = fresh.hold_pnl; it.hold_pct = fresh.hold_pct }
    editingId.value = null
    ElMessage.success('持仓已更新')
  } catch (e) { /* handled */ }
}

function goDetail(it) {
  router.push({ path: `/stocks/${it.code}`, query: { market: it.market } })
}

onMounted(() => {
  loadAll()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<style scoped>
.st-page { min-height: 100vh; position: relative; }
.st-inner { position: relative; padding: 84px 20px 40px; max-width: 1100px; margin: 0 auto; }

.st-head { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.st-head-left { display: flex; }
.st-back { margin-right: 2px; }
.st-titles { flex: 1; min-width: 160px; }
.st-title { margin: 0; font-size: 22px; letter-spacing: .1em; color: var(--lj-text); }
.st-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.st-head-right { display: flex; gap: 8px; margin-left: auto; }

.st-btn { border-radius: 9px; padding: 8px 16px; font-size: 13px; border: 1px solid transparent; cursor: pointer; transition: all .2s; }
.st-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; }
.st-btn.ghost { background: transparent; color: var(--lj-text); border-color: var(--lj-line); }
.st-btn.ghost:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.st-btn.tiny { padding: 3px 8px; font-size: 12px; }
.st-btn.danger { color: #D8504F; }
.st-btn:disabled { opacity: .5; cursor: not-allowed; }

.st-kpi { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
.st-kpi-card { display: flex; flex-direction: column; gap: 6px; padding: 18px; border-radius: 16px; }
.st-kpi-k { font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.st-kpi-v { font-size: 26px; font-weight: 700; letter-spacing: .01em; }
.st-kpi-s { font-size: 11px; color: var(--lj-text-3); }
.up { color: #D8504F; }
.down { color: #3F968E; }
.flat { color: var(--lj-text); }

.st-form { margin-bottom: 16px; padding: 18px 20px; border-radius: 16px; }
.st-form-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.st-form-title { font-size: 16px; letter-spacing: .08em; color: var(--lj-text); }
.st-form-hint { font-size: 12px; color: var(--lj-text-3); }
.st-form-close { margin-left: auto; background: none; border: none; color: var(--lj-text-2); font-size: 16px; cursor: pointer; }
.st-form-row { display: flex; gap: 12px; flex-wrap: wrap; }
.st-f-field { min-width: 150px; flex: 0 0 auto; }
.st-f-field.grow { flex: 1 1 180px; }
.st-f-label { display: block; font-size: 11px; color: var(--lj-text-2); margin-bottom: 5px; }
.st-input { width: 100%; background: rgba(11,15,20,.35); border: 1px solid var(--lj-line); color: var(--lj-text); border-radius: 8px; padding: 7px 10px; box-sizing: border-box; }
.st-input:focus { outline: none; border-color: var(--lj-seal); }
.st-select { appearance: none; }
.st-sug { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.st-sug-item { display: flex; align-items: baseline; gap: 8px; background: rgba(11,15,20,.35); border: 1px solid var(--lj-line); border-radius: 9px; padding: 6px 12px; cursor: pointer; color: var(--lj-text); }
.st-sug-item:hover { border-color: var(--lj-seal); }
.st-sug-name { font-size: 13px; }
.st-sug-code { font-size: 11px; color: var(--lj-text-3); }
.st-form-actions { display: flex; align-items: center; justify-content: space-between; margin-top: 14px; }
.st-save-tip { font-size: 11px; color: var(--lj-text-3); }

.st-list { border-radius: 16px; padding: 18px 20px; }
.st-list-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
.st-list-title { font-size: 16px; letter-spacing: .08em; color: var(--lj-text); }
.st-list-sub { font-size: 12px; color: var(--lj-text-3); }

.st-table-wrap { overflow-x: auto; }
.st-table { width: 100%; border-collapse: collapse; }
.st-table th { text-align: left; font-size: 12px; color: var(--lj-text-3); font-weight: 500; padding: 8px 10px; border-bottom: 1px solid var(--lj-line); }
.st-table th.r, .st-table td.r { text-align: right; }
.st-table td { padding: 11px 10px; font-size: 13px; color: var(--lj-text); border-bottom: 1px solid rgba(74,95,99,.12); }
.st-table tr:hover td { background: rgba(74,95,99,.05); }
.st-td-name { cursor: pointer; font-weight: 600; }
.st-td-name:hover { color: var(--lj-seal); }
.st-td-code { display: block; font-size: 11px; color: var(--lj-text-3); margin-top: 2px; }
.st-td-edit { margin-left: 8px; font-size: 12px; color: var(--lj-dai); cursor: pointer; }
.st-num { font-variant-numeric: tabular-nums; }
.st-sub-pct { font-style: normal; font-size: 11px; opacity: .8; }
.st-cell-input { width: 76px; background: rgba(11,15,20,.35); border: 1px solid var(--lj-line); color: var(--lj-text); border-radius: 6px; padding: 4px 6px; margin-right: 4px; }

.st-cards { display: flex; flex-direction: column; gap: 10px; }
.st-card { border-radius: 12px; padding: 14px; border: 1px solid var(--lj-line); }
.st-card-h { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.st-card-name { cursor: pointer; font-weight: 600; font-size: 14px; }
.st-card-code { display: block; font-size: 11px; color: var(--lj-text-3); margin-top: 3px; }
.st-card-row { display: flex; justify-content: space-between; font-size: 13px; margin-top: 4px; }

.st-empty { padding: 40px; text-align: center; color: var(--lj-text-3); font-size: 13px; }
.st-risk { margin-top: 26px; text-align: center; font-size: 11px; color: var(--lj-text-3); letter-spacing: .08em; }

@media (max-width: 760px) { .st-kpi { grid-template-columns: 1fr; } }
</style>
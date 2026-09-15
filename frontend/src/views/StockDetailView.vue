<template>
  <div class="sd-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="sd-inner">
      <!-- 返回 -->
      <div class="sd-topbar">
        <BackButton />
        <span class="sd-crumb" @click="$router.push('/stocks')">行情</span>
      </div>

      <!-- 报价头 -->
      <section class="sd-head glass">
        <div class="sd-head-l">
          <h1 class="sd-name">{{ quote.name || code }}</h1>
          <span class="sd-code">{{ marketLabel }} {{ code }}</span>
        </div>
        <div class="sd-head-r">
          <div class="sd-price" :class="cls">{{ fmt(quote.price) }}</div>
          <div class="sd-chg" :class="cls">
            <template v-if="quote.change != null && quote.pct != null">
              {{ sign(quote.change) }}{{ fmt(quote.change) }}（{{ sign(quote.pct) }}{{ fmt(quote.pct, 2) }}%）
            </template>
          </div>
        </div>
      </section>

      <!-- 行情速览 -->
      <section class="sd-quote glass">
        <div class="sd-q-item"><span class="sd-q-k">今开</span><b :class="refCls(quote.open)">{{ fmt(quote.open) }}</b></div>
        <div class="sd-q-item"><span class="sd-q-k">昨收</span><b class="flat">{{ fmt(quote.pre_close) }}</b></div>
        <div class="sd-q-item"><span class="sd-q-k s-up">最高</span><b :class="refCls(quote.high)">{{ fmt(quote.high) }}</b></div>
        <div class="sd-q-item"><span class="sd-q-k s-down">最低</span><b :class="refCls(quote.low)">{{ fmt(quote.low) }}</b></div>
        <div class="sd-q-item"><span class="sd-q-k">成交量</span><b>{{ volTxt(quote.volume) }}</b></div>
        <div class="sd-q-item"><span class="sd-q-k">成交额</span><b>{{ amtTxt(quote.amount) }}</b></div>
      </section>

      <!-- K 线 -->
      <section class="sd-kline glass">
        <div class="sd-block-head">
          <span class="sd-block-title">日 K 线</span>
          <span class="sd-block-sub">MA5/10/20 · 复权</span>
        </div>
        <KlineChart v-if="kline.length" :data="kline" :height="420" @analysis="onAnalysis" />
        <div v-else class="sd-loading">{{ klineErr || 'K 线加载中…' }}</div>
      </section>

      <!-- 每日研判 -->
      <section class="sd-analysis glass" v-if="view.period || (view.list && view.list.length)">
        <div class="sd-block-head">
          <span class="sd-block-title">每日研判</span>
          <span class="sd-an-period">{{ view.label }}</span>
          <span v-if="view.ai && view.model" class="sd-an-model" :title="'研判模型：' + view.model">{{ view.model }}</span>
          <span class="sd-block-sub" style="flex:1">
            {{ view.ai ? 'AI 技术面 · 规则保底 · 盘后生成' : '盘中规则化形态 · 操作参考' }}
          </span>
          <button class="sd-btn ghost small sd-an-gen" :disabled="genBusy" @click="generateAnalysis">
            {{ genBusy ? '生成中…' : (todayAnalyzed ? '今日已研判' : '立即研判') }}
          </button>
        </div>
        <div class="sd-an-table">
          <div class="sd-an-row sd-an-head">
            <span>日期</span><span class="ta-r">收盘</span><span class="ta-r">涨跌</span><span>形态总结</span><span>操作建议</span>
          </div>
          <div v-for="(it, i) in view.list" :key="it.date + i" class="sd-an-row" :class="{ latest: i === 0 }">
            <span class="sd-an-date">{{ it.date }}<i v-if="i === 0" class="sd-an-now">今</i></span>
            <span class="ta-r sd-an-close">{{ fmt(it.close) }}</span>
            <span class="ta-r" :class="it.up ? 'up' : 'down'">{{ chgTxt(it.chg) }}</span>
            <span class="sd-an-sum">{{ it.summary }}</span>
            <span class="sd-an-sug" :class="'lv-' + it.lv">
              <i class="sd-an-badge">{{ badgeTxt[it.lv] || badgeTxt.watch }}</i>
              <em>{{ it.sug }}</em>
            </span>
          </div>
        </div>
        <div class="sd-an-risk">技术面研判仅供参考，不构成投资建议{{ view.ai ? '· 盘后生成，盘中以实时规则为准' : '' }}</div>
      </section>

      <!-- 持仓 -->
      <section class="sd-hold glass">
        <div class="sd-block-head"><span class="sd-block-title">我的持仓</span></div>
        <div v-if="watch" class="sd-hold-body">
          <div class="sd-hold-row"><span>持仓数</span><b>{{ watch.quantity || 0 }} 股</b></div>
          <div class="sd-hold-row"><span>成本价</span><b>¥ {{ fmt(watch.cost_price) }}</b></div>
          <div class="sd-hold-row"><span>现价</span><b>¥ {{ fmt(quote.price) }}</b></div>
          <div class="sd-hold-row">
            <span>持仓盈亏</span>
            <b :class="pnlCls">{{ sign(watch.hold_pnl) }}¥ {{ fmt(Math.abs(watch.hold_pnl ?? 0)) }}（{{ sign(watch.hold_pct) }}{{ fmt(watch.hold_pct, 2) }}%）</b>
          </div>
          <div class="sd-hold-ops">
            <button class="sd-btn ghost small" @click="editing = !editing">{{ editing ? '收起' : '修改持仓' }}</button>
          </div>
          <div v-if="editing" class="sd-hold-edit">
            <input v-model.number="editQty" class="sd-input" type="number" min="0" placeholder="持仓数量" />
            <input v-model.number="editCost" class="sd-input" type="number" min="0" step="0.01" placeholder="持仓成本" />
            <button class="sd-btn primary small" :disabled="savingHold" @click="saveHold">{{ savingHold ? '保存中…' : '保存' }}</button>
          </div>
        </div>
        <div v-else class="sd-empty-row">该股未加入自选，无法展示持仓盈亏</div>
      </section>

      <!-- 相关资讯（复用资讯模块搜索） -->
      <section class="sd-news glass">
        <div class="sd-block-head">
          <span class="sd-block-title">相关资讯</span>
          <span class="sd-block-sub">按名称聚合订阅内容</span>
        </div>
        <div v-if="news.length" class="sd-news-list">
          <a v-for="n in news" :key="n.id" class="sd-news-item" :href="n.link || '#'" target="_blank" rel="noopener noreferrer">
            <span class="sd-news-dot">→</span><span class="sd-news-txt">{{ n.title }}</span>
          </a>
        </div>
        <div v-else class="sd-empty-row">暂未聚合到「{{ quote.name }}」相关资讯</div>
      </section>

      <footer class="sd-risk">自用工具，数据仅供参考，不构成投资建议</footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import BackButton from '@/components/BackButton.vue'
import KlineChart from '@/components/stocks/KlineChart.vue'
import { stocksApi } from '@/api/stocks'
import { ElMessage } from 'element-plus'

const route = useRoute()
const code = route.params.code
const market = (route.query.market || 'sh').toLowerCase()

const quote = ref({})
const kline = ref([])
const klineErr = ref('')
const watch = ref(null)
const editing = ref(false)
const savingHold = ref(false)
const editQty = ref(null)
const editCost = ref(null)
const news = ref([])
const analysis = ref({ period: '', list: [] })
const aiList = ref([])
const genBusy = ref(false)

const todayDate = new Date().toISOString().slice(0, 10)
// AI 研判优先展示；无记录时回退 KlineChart 的盘中规则研判
const view = computed(() => {
  if (aiList.value.length) {
    return {
      ai: true,
      label: 'AI · 盘后',
      model: aiList.value[0]?.model_name || '',
      list: aiList.value.map((it) => ({
        date: it.date,
        close: it.price,
        chg: it.pct,
        up: it.pct != null && it.pct > 0,
        summary: it.summary,
        sug: it.suggestion,
        lv: it.level,
      })),
    }
  }
  return { ...analysis.value, ai: false, label: '盘中规则', model: '' }
})
const todayAnalyzed = computed(() => aiList.value[0]?.date === todayDate)

const badgeTxt = { up: '强', hold: '持', watch: '观', down: '减', danger: '避' }
const periodNames = { day: '日K', week: '周K', month: '月K' }

const marketLabel = { sh: '沪', sz: '深', hk: '港', us: '美' }[market] || market.toUpperCase()

function chgTxt(v) { return v == null ? '--' : (v > 0 ? '+' : '') + fmt(v, 2) + '%' }
function onAnalysis(payload) {
  if (!payload) return
  analysis.value = { ...payload, periodLabel: periodNames[payload.period] || payload.period }
}

function sign(v) { return v > 0 ? '+' : '' }
function fmt(v, n = 2) { return v == null ? '--' : Number(v).toFixed(n) }
function refCls(v) { const r = quote.value.pre_close; if (v == null || r == null || v === r) return 'flat'; return v > r ? 'up' : 'down' }
function volTxt(v) {
  if (v == null) return '--'
  return v >= 1e8 ? (v / 1e8).toFixed(2) + '亿手'
    : v >= 1e4 ? (v / 1e4).toFixed(1) + '万手'
    : v.toFixed(0) + '手'
}
function amtTxt(v) {
  if (v == null) return '--'
  return v >= 1e8 ? (v / 1e8).toFixed(2) + '亿' : v >= 1e4 ? (v / 1e4).toFixed(1) + '万' : v.toFixed(0)
}
const pct = computed(() => quote.value.pct ?? 0)
const cls = computed(() => (pct.value > 0 ? 'up' : pct.value < 0 ? 'down' : 'flat'))
const pnlCls = computed(() => (watch.value?.hold_pnl > 0 ? 'up' : watch.value?.hold_pnl < 0 ? 'down' : 'flat'))

async function loadAll() {
  try {
    const r = await stocksApi.quote(market, code)
    quote.value = r.data || {}
    editQty.value = null; editCost.value = null
  } catch (e) { /* quote err handled */ }
  try { kline.value = (await stocksApi.kline(market, code, 500)).data?.list || [] }
  catch (e) { klineErr.value = '暂无 K 线数据' }
  try {
    const wl = (await stocksApi.watchlist()).data?.list || []
    watch.value = wl.find(x => x.code.toLowerCase() === code.toLowerCase() && x.market === market) || null
    if (watch.value) { editQty.value = watch.value.quantity; editCost.value = watch.value.cost_price }
  } catch (e) { /* ignore */ }
  if (quote.value.name) {
    try {
      const res = await fetch(`/api/feeds/articles?q=${encodeURIComponent(quote.value.name)}&size=4`)
      const j = await res.json()
      news.value = (j?.data?.list || []).slice(0, 4)
    } catch (e) { news.value = [] }
  }
  await loadAnalysis()
}

async function loadAnalysis() {
  try {
    const r = await stocksApi.analysis(market, code, 7)
    aiList.value = r.data?.list || []
  } catch (e) { aiList.value = [] }
}

async function generateAnalysis() {
  genBusy.value = true
  try {
    await stocksApi.generateAnalysis(market, code)
    ElMessage.success('研判已生成')
    await loadAnalysis()
    try { quote.value = (await stocksApi.quote(market, code)).data || quote.value } catch (e) { /* ignore */ }
  } catch (e) { /* 错误已由拦截器提示 */ }
  finally { genBusy.value = false }
}

async function saveHold() {
  if (!watch.value) return
  savingHold.value = true
  try {
    const r = await stocksApi.update(watch.value.id, { quantity: editQty.value || 0, cost_price: editCost.value })
    watch.value = r.data || watch.value
    editing.value = false
    ElMessage.success('持仓已更新')
  } finally { savingHold.value = false }
}

onMounted(loadAll)
</script>

<style scoped>
.sd-page { min-height: 100vh; position: relative; }
.sd-inner { position: relative; padding: 84px 20px 40px; max-width: 1000px; margin: 0 auto; }

.sd-topbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.sd-crumb { font-size: 13px; color: var(--lj-text-2); cursor: pointer; }
.sd-crumb:hover { color: var(--lj-seal); }

.sd-head { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-radius: 16px; }
.sd-name { margin: 0; font-size: 24px; letter-spacing: .04em; color: var(--lj-text); }
.sd-code { font-size: 13px; color: var(--lj-text-2); }
.sd-price { font-size: 34px; font-weight: 700; letter-spacing: .02em; }
.sd-chg { font-size: 15px; margin-top: 4px; }

.sd-quote { margin-top: 12px; padding: 14px 20px; border-radius: 16px; display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px 12px; }
.sd-q-item { display: flex; flex-direction: column; gap: 3px; }
.sd-q-k { font-size: 11px; color: var(--lj-text-3); letter-spacing: .05em; }
.sd-q-k.s-up { color: rgba(216, 80, 79, 0.85); }
.sd-q-k.s-down { color: rgba(63, 150, 142, 0.85); }
.sd-q-item b { font-size: 15px; font-weight: 600; color: var(--lj-text); font-variant-numeric: tabular-nums; letter-spacing: .01em; }
@media (max-width: 640px) { .sd-quote { grid-template-columns: repeat(3, 1fr); } }
.up { color: #D8504F; }
.down { color: #3F968E; }
.flat { color: var(--lj-text-2); }

.sd-kline, .sd-hold, .sd-news, .sd-analysis { margin-top: 16px; padding: 18px 20px; border-radius: 16px; }
.sd-block-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
.sd-block-title { font-size: 16px; letter-spacing: .08em; color: var(--lj-text); }
.sd-block-sub { font-size: 12px; color: var(--lj-text-3); }
.sd-loading, .sd-empty-row { padding: 26px; text-align: center; color: var(--lj-text-3); font-size: 13px; }
.sd-loading::before { content: ''; display: inline-block; width: 12px; height: 12px; margin-right: 8px; vertical-align: -2px;
  border-radius: 50%; border: 2px solid var(--lj-line-strong); border-top-color: var(--lj-dai); animation: sd-spin .9s linear infinite; }
@keyframes sd-spin { to { transform: rotate(360deg); } }

/* 每日研判 */
.sd-an-period {
  font-size: 11px; line-height: 18px; padding: 0 8px; border-radius: 999px;
  background: rgba(199, 169, 107, 0.14); color: var(--lj-seal); letter-spacing: .06em; flex: none;
}
.sd-an-model {
  font-size: 10.5px; line-height: 16px; padding: 0 6px; border-radius: 6px;
  background: rgba(127, 168, 163, 0.14); color: var(--lj-dai); letter-spacing: .03em;
  max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: none;
}
.sd-an-gen { flex: none; }
.sd-an-table { display: flex; flex-direction: column; max-height: 340px; overflow: auto; padding-right: 4px; margin: 0 -6px; }
.sd-an-row {
  display: grid; grid-template-columns: 78px 58px 66px 1fr 1.45fr; gap: 8px; align-items: center;
  font-size: 12.5px; padding: 7px 10px; border-radius: 10px; transition: background .15s;
}
.sd-an-row:hover { background: rgba(120, 150, 150, 0.08); }
.sd-an-head {
  color: var(--lj-text-3); font-size: 11px; letter-spacing: .08em;
  position: sticky; top: 0; z-index: 1;
  background: rgba(246, 243, 234, 0.7); -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
}
html[data-theme="night"] .sd-an-head { background: rgba(18, 24, 32, 0.7); }
.sd-an-date { color: var(--lj-text-2); font-variant-numeric: tabular-nums; display: inline-flex; align-items: center; gap: 6px; }
.sd-an-now {
  font-style: normal; font-size: 10px; line-height: 15px; padding: 0 4px; border-radius: 5px;
  background: rgba(216, 80, 79, 0.14); color: #d8504f; font-weight: 700; letter-spacing: .02em;
}
.sd-an-close { font-weight: 600; color: var(--lj-text); font-variant-numeric: tabular-nums; }
.ta-r { text-align: right; }
.sd-an-sum { color: var(--lj-text-2); line-height: 1.5; }
.sd-an-sug { display: flex; align-items: center; gap: 7px; min-width: 0; }
.sd-an-sug em { font-style: normal; color: var(--lj-text); line-height: 1.5; }
.sd-an-badge { font-style: normal; min-width: 22px; height: 20px; line-height: 20px; text-align: center; border-radius: 7px; font-size: 12px; font-weight: 700; flex: none; }
.sd-an-sug.lv-up .sd-an-badge { background: rgba(192, 57, 43, 0.15); color: #c0392b; }
.sd-an-sug.lv-up em { color: #c0392b; }
.sd-an-sug.lv-hold .sd-an-badge { background: rgba(198, 152, 63, 0.16); color: #b3821f; }
.sd-an-sug.lv-hold em { color: #b3821f; }
.sd-an-sug.lv-watch .sd-an-badge { background: rgba(122, 142, 148, 0.16); color: #5f7277; }
.sd-an-sug.lv-watch em { color: #5f7277; }
.sd-an-sug.lv-down .sd-an-badge { background: rgba(63, 150, 142, 0.15); color: #2f8077; }
.sd-an-sug.lv-down em { color: #2f8077; }
.sd-an-sug.lv-danger .sd-an-badge { background: rgba(91, 110, 225, 0.15); color: #4a5bd0; }
.sd-an-sug.lv-danger em { color: #4a5bd0; }
.sd-an-risk {
  margin-top: 8px; padding-top: 9px; border-top: 1px dashed var(--lj-line, rgba(120,150,150,0.2));
  font-size: 10.5px; color: var(--lj-text-3); letter-spacing: .04em;
}
@media (max-width: 640px) {
  .sd-an-row { grid-template-columns: 70px 52px 60px 1fr; }
  .sd-an-sug { grid-column: 1 / -1; margin-top: 1px; }
}

.sd-hold-body { display: flex; flex-direction: column; gap: 10px; }
.sd-hold-row { display: flex; justify-content: space-between; font-size: 14px; }
.sd-hold-row b { color: var(--lj-text); font-weight: 600; }
.sd-hold-ops { margin-top: 6px; }
.sd-hold-edit { display: flex; gap: 8px; align-items: center; margin-top: 10px; flex-wrap: wrap; }
.sd-input { background: rgba(11,15,20,.35); border: 1px solid var(--lj-line); color: var(--lj-text); border-radius: 8px; padding: 6px 10px; width: 130px; }

.sd-news-list { display: flex; flex-direction: column; gap: 8px; }
.sd-news-item { display: flex; gap: 8px; font-size: 13px; color: var(--lj-text-2); text-decoration: none; }
.sd-news-item:hover { color: var(--lj-seal); }
.sd-news-dot { color: var(--lj-dai); flex: none; }
.sd-news-txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.sd-btn { border-radius: 9px; padding: 7px 14px; font-size: 13px; border: 1px solid transparent; cursor: pointer; transition: all .2s; }
.sd-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; }
.sd-btn.ghost { background: transparent; color: var(--lj-text); border-color: var(--lj-line); }
.sd-btn.ghost:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.sd-btn.small { padding: 5px 10px; font-size: 12px; }

.sd-risk { margin-top: 26px; text-align: center; font-size: 11px; color: var(--lj-text-3); letter-spacing: .08em; }
</style>
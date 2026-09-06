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

      <!-- K 线 -->
      <section class="sd-kline glass">
        <div class="sd-block-head">
          <span class="sd-block-title">日 K 线</span>
          <span class="sd-block-sub">MA5/10/20 · 复权</span>
        </div>
        <KlineChart v-if="kline.length" :data="kline" :height="340" />
        <div v-else class="sd-loading">{{ klineErr || 'K 线加载中…' }}</div>
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

const marketLabel = { sh: '沪', sz: '深', hk: '港', us: '美' }[market] || market.toUpperCase()

function sign(v) { return v > 0 ? '+' : '' }
function fmt(v, n = 2) { return v == null ? '--' : Number(v).toFixed(n) }
const pct = computed(() => quote.value.pct ?? 0)
const cls = computed(() => (pct.value > 0 ? 'up' : pct.value < 0 ? 'down' : 'flat'))
const pnlCls = computed(() => (watch.value?.hold_pnl > 0 ? 'up' : watch.value?.hold_pnl < 0 ? 'down' : 'flat'))

async function loadAll() {
  try {
    const r = await stocksApi.quote(market, code)
    quote.value = r.data || {}
    editQty.value = null; editCost.value = null
  } catch (e) { /* quote err handled */ }
  try { kline.value = (await stocksApi.kline(market, code)).data?.list || [] }
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
.sd-crumb:hover { color: var(--lj-dai); }

.sd-head { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-radius: 16px; }
.sd-name { margin: 0; font-size: 24px; letter-spacing: .04em; color: var(--lj-text); }
.sd-code { font-size: 13px; color: var(--lj-text-2); }
.sd-price { font-size: 34px; font-weight: 700; letter-spacing: .02em; }
.sd-chg { font-size: 15px; margin-top: 4px; }
.up { color: #D8504F; }
.down { color: #3F968E; }
.flat { color: var(--lj-text-2); }

.sd-kline, .sd-hold, .sd-news { margin-top: 16px; padding: 18px 20px; border-radius: 16px; }
.sd-block-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
.sd-block-title { font-size: 16px; letter-spacing: .08em; color: var(--lj-text); }
.sd-block-sub { font-size: 12px; color: var(--lj-text-3); }
.sd-loading, .sd-empty-row { padding: 26px; text-align: center; color: var(--lj-text-3); font-size: 13px; }

.sd-hold-body { display: flex; flex-direction: column; gap: 10px; }
.sd-hold-row { display: flex; justify-content: space-between; font-size: 14px; }
.sd-hold-row b { color: var(--lj-text); font-weight: 600; }
.sd-hold-ops { margin-top: 6px; }
.sd-hold-edit { display: flex; gap: 8px; align-items: center; margin-top: 10px; flex-wrap: wrap; }
.sd-input { background: rgba(11,15,20,.35); border: 1px solid var(--lj-line); color: var(--lj-text); border-radius: 8px; padding: 6px 10px; width: 130px; }

.sd-news-list { display: flex; flex-direction: column; gap: 8px; }
.sd-news-item { display: flex; gap: 8px; font-size: 13px; color: var(--lj-text-2); text-decoration: none; }
.sd-news-item:hover { color: var(--lj-dai); }
.sd-news-dot { color: var(--lj-dai); flex: none; }
.sd-news-txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.sd-btn { border-radius: 9px; padding: 7px 14px; font-size: 13px; border: 1px solid transparent; cursor: pointer; transition: all .2s; }
.sd-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; }
.sd-btn.ghost { background: transparent; color: var(--lj-text); border-color: var(--lj-line); }
.sd-btn.ghost:hover { border-color: var(--lj-line-strong); color: var(--lj-dai); }
.sd-btn.small { padding: 5px 10px; font-size: 12px; }

.sd-risk { margin-top: 26px; text-align: center; font-size: 11px; color: var(--lj-text-3); letter-spacing: .08em; }
</style>
<template>
  <div class="fo-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="fo-inner">
      <header class="fo-head">
        <div class="fo-head-left"><BackButton class="fo-back" /></div>
        <div class="fo-titles">
          <h1 class="fo-title">财经</h1>
          <p class="fo-sub">行情 · 资讯 · 记账 · 倒计时，一屏总览</p>
        </div>
        <div class="fo-head-right">
          <button class="fo-btn ghost" :disabled="loading" @click="loadAll(true)">{{ loading ? '刷新中…' : '⟳ 刷新' }}</button>
          <button class="fo-btn primary" @click="$router.push('/finance/market')">行情</button>
        </div>
      </header>

      <!-- 顶部四张 KPI -->
      <section class="fo-kpi">
        <div class="fo-kpi-card glass" :class="pnlCls(stock.pnlPct)">
          <span class="fo-kpi-k">持仓盈亏</span>
          <span class="fo-kpi-v">{{ stock.pnlPct == null ? '--' : sign(stock.pnlPct) + fmt(stock.pnlPct, 2) + '%' }}</span>
          <span class="fo-kpi-s">{{ stock.symbolCount }} 只自选 · 市值 ¥{{ fmt(stock.marketValue) }}</span>
        </div>
        <div class="fo-kpi-card glass">
          <span class="fo-kpi-k">本月支出</span>
          <span class="fo-kpi-v">¥ {{ fmt(finance.expense) }}</span>
          <span class="fo-kpi-s">收入 ¥{{ fmt(finance.income) }} · 净额 ¥{{ fmt(finance.net) }}</span>
        </div>
        <div class="fo-kpi-card glass">
          <span class="fo-kpi-k">累计结余</span>
          <span class="fo-kpi-v" :class="finance.balance >= 0 ? 'up' : 'down'">¥ {{ fmt(finance.balance) }}</span>
          <span class="fo-kpi-s">{{ finance.count }} 条流水</span>
        </div>
        <div class="fo-kpi-card glass" :class="{ 'has-alert': stock.alerts > 0 }">
          <span class="fo-kpi-k">目标价预警</span>
          <span class="fo-kpi-v" :class="stock.alerts > 0 ? 'down' : ''">{{ stock.alerts }}</span>
          <span class="fo-kpi-s">{{ stock.alerts ? '有触达，请查看' : '暂无触达' }}</span>
        </div>
      </section>

      <!-- 主区两列：自选 + 资讯 -->
      <section class="fo-row">
        <!-- 自选股 -->
        <article class="fo-card glass">
          <div class="fo-card-head">
            <span class="fo-card-title">自选股</span>
            <span class="fo-card-extra">
              <a class="fo-link" @click.prevent="$router.push('/finance/market')">查看全部 ›</a>
            </span>
          </div>
          <div v-if="stock.top.length" class="fo-stock-list">
            <div v-for="row in stock.top" :key="row.id" class="fo-stock-row" @click="$router.push('/finance/market/stock/' + row.code + '?market=' + row.market)">
              <div class="fo-stock-name">
                <span class="fo-stock-code">{{ row.code }}</span>
                <span class="fo-stock-cn">{{ row.name }}</span>
              </div>
              <div class="fo-stock-num">
                <span class="fo-stock-price">{{ row.price ? row.price.toFixed(2) : '--' }}</span>
                <span class="fo-stock-chg" :class="pnlCls(row.change_pct)">
                  {{ row.change_pct == null ? '--' : sign(row.change_pct) + row.change_pct.toFixed(2) + '%' }}
                </span>
              </div>
            </div>
          </div>
          <div v-else class="fo-empty">
            <span>暂无自选股</span>
            <button class="fo-btn primary mini" @click="$router.push('/finance/market')">＋ 加自选</button>
          </div>
        </article>

        <!-- 资讯 -->
        <article class="fo-card glass">
          <div class="fo-card-head">
            <span class="fo-card-title">最新资讯</span>
            <span class="fo-card-extra">
              <a class="fo-link" @click.prevent="$router.push('/finance/news')">查看全部 ›</a>
            </span>
          </div>
          <div v-if="news.top.length" class="fo-news-list">
            <div v-for="row in news.top" :key="row.id" class="fo-news-row" @click="$router.push('/finance/news')">
              <span class="fo-news-cat" v-if="row.source_category">{{ row.source_category }}</span>
              <span class="fo-news-title">{{ row.title_zh || row.title }}</span>
              <span class="fo-news-meta" v-if="row.published_at">{{ row.published_at.slice(5, 16) }}</span>
            </div>
          </div>
          <div v-else class="fo-empty">
            <span>暂无资讯</span>
          </div>
        </article>
      </section>

      <!-- 次区两列：本月支出分类 + 倒计时 -->
      <section class="fo-row">
        <article class="fo-card glass">
          <div class="fo-card-head">
            <span class="fo-card-title">本月支出分布</span>
            <span class="fo-card-extra">
              <a class="fo-link" @click.prevent="$router.push('/finance/book')">去记账 ›</a>
            </span>
          </div>
          <div v-if="finance.categories.length" class="fo-cat-list">
            <div v-for="c in finance.categories.slice(0, 6)" :key="c.category" class="fo-cat-row">
              <span class="fo-cat-ico">{{ c.icon || '🧾' }}</span>
              <span class="fo-cat-name">{{ c.category }}</span>
              <div class="fo-cat-bar"><div class="fo-cat-bar-fill" :style="{ width: pct(c.amount_cents, finance.expenseCents) + '%' }"></div></div>
              <span class="fo-cat-amt">¥{{ fmt(c.amount) }}</span>
            </div>
          </div>
          <div v-else class="fo-empty">
            <span>本月暂无支出</span>
          </div>
        </article>

        <article class="fo-card glass">
          <div class="fo-card-head">
            <span class="fo-card-title">近期倒计时</span>
            <span class="fo-card-extra">
              <a class="fo-link" @click.prevent="$router.push('/tool/countdown')">查看全部 ›</a>
            </span>
          </div>
          <div v-if="countdowns.top.length" class="fo-cd-list">
            <div v-for="c in countdowns.top" :key="c.id" class="fo-cd-row">
              <span class="fo-cd-icon" :style="c.color ? { color: c.color } : {}">{{ c.icon || '✦' }}</span>
              <span class="fo-cd-title">{{ c.title }}</span>
              <span class="fo-cd-days" :class="c.days_left < 0 ? 'over' : (c.days_left <= 7 ? 'soon' : '')">
                {{ c.days_left < 0 ? '已过 ' + Math.abs(c.days_left) + ' 天' : '还剩 ' + c.days_left + ' 天' }}
              </span>
            </div>
          </div>
          <div v-else class="fo-empty">
            <span>暂无倒计时</span>
            <button class="fo-btn primary mini" @click="$router.push('/tool/countdown')">＋ 新建</button>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import BackButton from '@/components/BackButton.vue'
import { stocksApi } from '@/api/stocks'
import { feedsApi } from '@/api/feeds'
import { financeApi } from '@/api/finance'
import { listCountdowns } from '@/api/countdown'

const loading = ref(false)

const stock = reactive({ pnlPct: null, marketValue: 0, symbolCount: 0, alerts: 0, top: [] })
const news = reactive({ top: [] })
const finance = reactive({ income: 0, expense: 0, net: 0, balance: 0, count: 0, expenseCents: 0, categories: [] })
const countdowns = reactive({ top: [] })

function fmt(v, d = 0) {
  if (v == null || isNaN(v)) return '0'
  return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: d, minimumFractionDigits: d })
}
function sign(v) { return v > 0 ? '+' : (v < 0 ? '' : '') }
function pnlCls(v) {
  if (v == null) return ''
  return v > 0 ? 'up' : (v < 0 ? 'down' : '')
}
function pct(v, total) {
  if (!total) return 0
  return Math.max(2, Math.round((v / total) * 100))
}

async function loadAll(silent = false) {
  if (!silent) loading.value = true
  try {
    await Promise.allSettled([
      loadStock(),
      loadNews(),
      loadFinance(),
      loadCountdowns(),
    ])
  } finally {
    loading.value = false
  }
}

async function loadStock() {
  try {
    const [{ data: sum }, { data: wl }] = await Promise.all([
      stocksApi.summary(),
      stocksApi.watchlist(),
    ])
    stock.pnlPct = Number(sum?.hold_pct ?? 0)
    stock.marketValue = Number(sum?.market_value ?? 0)
    stock.symbolCount = Number(sum?.symbol_count ?? 0)
    stock.alerts = Number(sum?.alerts ?? 0)
    stock.top = (wl?.list || []).slice(0, 6).map((w) => ({
      id: w.id, code: w.code, market: w.market, name: w.name,
      price: Number(w.price ?? 0), change_pct: Number(w.pct ?? 0),
    }))
  } catch (e) { /* ignore */ }
}

async function loadNews() {
  try {
    const { data } = await feedsApi.list({ size: 6, page: 1 })
    news.top = (data?.list || []).slice(0, 6)
  } catch (e) { /* ignore */ }
}

async function loadFinance() {
  try {
    const { data } = await financeApi.summary({ dim: 'month' })
    finance.income = Number(data?.income ?? 0)
    finance.expense = Number(data?.expense ?? 0)
    finance.net = finance.income - finance.expense
    finance.balance = Number(data?.balance ?? 0)
    finance.count = Number(data?.total_count ?? 0)
    finance.categories = data?.categories || []
    finance.expenseCents = finance.categories.reduce((a, b) => a + Number(b.amount_cents || 0), 0) || Math.round(finance.expense * 100)
  } catch (e) { /* ignore */ }
}

async function loadCountdowns() {
  try {
    const { data } = await listCountdowns()
    const all = data?.list || []
    // 排序：未过期在前（按 days_left 升序），已过期放最后
    const live = all.filter((c) => c.days_left >= 0).sort((a, b) => a.days_left - b.days_left)
    const over = all.filter((c) => c.days_left < 0).sort((a, b) => b.days_left - a.days_left)
    countdowns.top = [...live, ...over].slice(0, 5)
  } catch (e) { /* ignore */ }
}

onMounted(loadAll)
</script>

<style scoped>
.fo-page { position: relative; min-height: 100vh; padding: 24px 32px 64px; color: var(--lj-ink); }
.lj-bg { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.lj-paper-texture { position: absolute; inset: 0; background: var(--lj-paper); opacity: 0.6; }
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4; }
.lj-wash.w1 { width: 480px; height: 480px; left: -120px; top: -120px; background: radial-gradient(circle, var(--lj-accent), transparent 70%); }
.lj-wash.w2 { width: 380px; height: 380px; right: -80px; bottom: -80px; background: radial-gradient(circle, var(--lj-accent-2), transparent 70%); }

.fo-inner { position: relative; max-width: 1280px; margin: 0 auto; }

.fo-head { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 16px; margin-bottom: 24px; }
.fo-titles { display: flex; flex-direction: column; gap: 4px; }
.fo-title { margin: 0; font-size: 28px; font-weight: 600; letter-spacing: 1px; }
.fo-sub { margin: 0; color: var(--lj-ink-soft); font-size: 13px; }
.fo-head-right { display: flex; gap: 10px; }
.fo-btn { appearance: none; border: 1px solid var(--lj-line); background: transparent; color: inherit; padding: 8px 16px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 160ms ease; }
.fo-btn:hover:not(:disabled) { border-color: var(--lj-accent); color: var(--lj-accent); }
.fo-btn.primary { background: var(--lj-accent); color: #fff; border-color: var(--lj-accent); }
.fo-btn.primary:hover:not(:disabled) { background: var(--lj-accent-deep); border-color: var(--lj-accent-deep); color: #fff; }
.fo-btn.mini { padding: 4px 10px; font-size: 12px; }
.fo-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.glass { background: var(--lj-card); border: 1px solid var(--lj-line); border-radius: 14px; backdrop-filter: blur(10px); padding: 18px 20px; }

/* KPI */
.fo-kpi { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.fo-kpi-card { display: flex; flex-direction: column; gap: 6px; }
.fo-kpi-k { font-size: 12px; color: var(--lj-ink-soft); }
.fo-kpi-v { font-size: 22px; font-weight: 600; }
.fo-kpi-v.up { color: var(--lj-up, #16a34a); }
.fo-kpi-v.down { color: var(--lj-down, #dc2626); }
.fo-kpi-s { font-size: 12px; color: var(--lj-ink-soft); }
.fo-kpi-card.has-alert { box-shadow: 0 0 0 2px var(--lj-down, #dc2626) inset; }

/* 双列行 */
.fo-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.fo-card { display: flex; flex-direction: column; gap: 12px; min-height: 280px; }
.fo-card-head { display: flex; justify-content: space-between; align-items: center; }
.fo-card-title { font-size: 16px; font-weight: 600; }
.fo-card-extra { font-size: 12px; }
.fo-link { color: var(--lj-accent); cursor: pointer; text-decoration: none; }
.fo-link:hover { text-decoration: underline; }

/* 自选股 */
.fo-stock-list { display: flex; flex-direction: column; gap: 8px; }
.fo-stock-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-radius: 8px; background: var(--lj-row); cursor: pointer; transition: background 160ms; }
.fo-stock-row:hover { background: var(--lj-row-hover); }
.fo-stock-name { display: flex; flex-direction: column; gap: 2px; }
.fo-stock-code { font-size: 14px; font-weight: 600; }
.fo-stock-cn { font-size: 12px; color: var(--lj-ink-soft); }
.fo-stock-num { text-align: right; display: flex; flex-direction: column; gap: 2px; }
.fo-stock-price { font-size: 14px; font-weight: 600; }
.fo-stock-chg { font-size: 12px; }
.fo-stock-chg.up { color: var(--lj-up, #16a34a); }
.fo-stock-chg.down { color: var(--lj-down, #dc2626); }

/* 资讯 */
.fo-news-list { display: flex; flex-direction: column; gap: 6px; }
.fo-news-row { display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: center; padding: 10px 12px; border-radius: 8px; background: var(--lj-row); cursor: pointer; transition: background 160ms; }
.fo-news-row:hover { background: var(--lj-row-hover); }
.fo-news-cat { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: var(--lj-tag); color: var(--lj-ink-soft); }
.fo-news-title { font-size: 14px; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fo-news-meta { font-size: 11px; color: var(--lj-ink-soft); }

/* 分类 */
.fo-cat-list { display: flex; flex-direction: column; gap: 8px; }
.fo-cat-row { display: grid; grid-template-columns: 28px 80px 1fr 80px; gap: 8px; align-items: center; padding: 6px 0; }
.fo-cat-ico { font-size: 18px; text-align: center; }
.fo-cat-name { font-size: 13px; }
.fo-cat-bar { height: 6px; background: var(--lj-bar-bg); border-radius: 3px; overflow: hidden; }
.fo-cat-bar-fill { height: 100%; background: linear-gradient(90deg, var(--lj-accent), var(--lj-accent-2)); transition: width 320ms; }
.fo-cat-amt { font-size: 13px; text-align: right; font-variant-numeric: tabular-nums; }

/* 倒计时 */
.fo-cd-list { display: flex; flex-direction: column; gap: 8px; }
.fo-cd-row { display: grid; grid-template-columns: 28px 1fr auto; gap: 8px; align-items: center; padding: 8px 12px; border-radius: 8px; background: var(--lj-row); }
.fo-cd-icon { font-size: 18px; text-align: center; }
.fo-cd-title { font-size: 14px; }
.fo-cd-days { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: var(--lj-bar-bg); color: var(--lj-ink-soft); }
.fo-cd-days.soon { background: var(--lj-warn-bg, #fde68a); color: var(--lj-warn, #92400e); }
.fo-cd-days.over { background: var(--lj-down-bg, #fecaca); color: var(--lj-down, #991b1b); }

/* 空状态 */
.fo-empty { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 24px 0; color: var(--lj-ink-soft); font-size: 13px; }

@media (max-width: 960px) {
  .fo-kpi { grid-template-columns: repeat(2, 1fr); }
  .fo-row { grid-template-columns: 1fr; }
}
</style>
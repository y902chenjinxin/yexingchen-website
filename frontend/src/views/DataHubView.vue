<template>
  <div class="dh-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="dh-inner">
      <!-- 返回 + 页头 -->
      <div class="dh-topbar">
        <BackButton />
        <span class="dh-crumb" @click="$router.push('/workbench')">工作台</span>
      </div>

      <header class="dh-head">
        <h1 class="dh-title">数据中心</h1>
        <p class="dh-sub">帐目 · 持仓 · 足迹 · 笔记 · 资讯 —— 一处一览</p>
      </header>

      <p v-if="loading" class="dh-loading">数据装载中…</p>
      <template v-else>
        <!-- 顶层核心 KPI 行 -->
        <div class="dh-kpis">
          <div class="dh-kpi glass" v-if="finance">
            <span class="dh-kpi-label">本月结余</span>
            <b class="dh-kpi-val" :class="balanceCls">{{ money(finance.balance) }}</b>
            <span class="dh-kpi-sub">
              收入 {{ money(finance.month_income) }} · 支出 {{ money(finance.month_expense) }}
            </span>
          </div>
          <div class="dh-kpi glass" v-if="stocks">
            <span class="dh-kpi-label">持仓市值</span>
            <b class="dh-kpi-val">{{ money(stocks.market_value) }}</b>
            <span class="dh-kpi-sub" :class="pnlCls(stocks.hold_pnl)">
              浮动盈亏 {{ money(stocks.hold_pnl) }}（{{ fmtPct(stocks.hold_pct) }}）
            </span>
          </div>
          <div class="dh-kpi glass" v-if="travels">
            <span class="dh-kpi-label">旅行足迹</span>
            <b class="dh-kpi-val">{{ travels.travel_count }} <i class="dh-unit">程</i></b>
            <span class="dh-kpi-sub">{{ travels.province_count }} 省 · {{ travels.city_count }} 城</span>
          </div>
          <div class="dh-kpi glass" v-if="notes">
            <span class="dh-kpi-label">笔记</span>
            <b class="dh-kpi-val">{{ notes.total }} <i class="dh-unit">篇</i></b>
            <span class="dh-kpi-sub">其中草稿 {{ notes.drafts }} 篇</span>
          </div>
        </div>

        <div class="dh-grid">
          <!-- 消费趋势 -->
          <section class="dh-card glass" v-if="finance">
            <div class="dh-card-head">
              <span class="dh-card-title">支出趋势</span>
              <span class="dh-card-sub">近 6 月</span>
            </div>
            <svg class="dh-chart" :viewBox="chartBox" preserveAspectRatio="none">
              <template v-for="(v, i) in expPoints" :key="'g' + i">
                <line class="dh-chart-g" :x1="v.x" :x2="v.x" :y1="padT" :y2="chartH - 4" />
              </template>
              <polyline class="dh-chart-poly" :points="expPtsStr" />
              <circle v-for="(v, i) in expPoints" :key="'c' + i" class="dh-chart-dot"
                :cx="v.x" :cy="v.y" r="3.2" />
              <template v-for="(v, i) in expPoints" :key="'t' + i">
                <text class="dh-chart-x" :x="v.x" :y="chartH - 2" :text-anchor=" i===0 ? 'start' : i===expPoints.length-1 ? 'end' : 'middle'">{{ v.label }}</text>
              </template>
              <text v-for="(v, i) in expPoints" :key="'tval' + i" class="dh-chart-xy" :x="v.x" :y="v.y - 7" :text-anchor=" i===0 ? 'start' : i===expPoints.length-1 ? 'end' : 'middle'">{{ moneyShort(v.value) }}</text>
            </svg>
          </section>

          <!-- 支出分类占比 -->
          <section class="dh-card glass" v-if="finance && finance.top_categories.length">
            <div class="dh-card-head">
              <span class="dh-card-title">本月支出分类</span>
            </div>
            <div class="dh-cats">
              <div v-for="(c, i) in finance.top_categories" :key="c.category" class="dh-cat">
                <span class="dh-cat-icon">{{ c.icon }}</span>
                <div class="dh-cat-mid">
                  <span class="dh-cat-name">{{ c.category }}</span>
                  <div class="dh-cat-track"><i class="dh-cat-fill" :style="{ width: pctOfTop(c, i + 1) + '%', background: catColor(i) }"></i></div>
                </div>
                <b class="dh-cat-val">{{ money(c.amount) }}</b>
              </div>
            </div>
          </section>

          <!-- 任务 -->
          <section class="dh-card glass" v-if="task">
            <div class="dh-card-head"><span class="dh-card-title">任务</span></div>
            <div class="dh-donut">
              <svg viewBox="0 0 80 80" class="dh-donut-svg">
                <circle class="dh-donut-ring" cx="40" cy="40" r="32" />
                <circle class="dh-donut-bar" cx="40" cy="40" r="32"
                  :stroke-dasharray="donutDash" :stroke-dashoffset="donutOffset" />
              </svg>
              <div class="dh-donut-center">
                <b>{{ donePctQ }}%</b>
                <span>已完成</span>
              </div>
            </div>
            <div class="dh-donut-legend">
              <span class="dh-legend-dot done"></span>已完成 {{ task.done }}
              <span class="dh-legend-dot todo"></span>待办 {{ task.todo }}
            </div>
          </section>

          <!-- 资讯 -->
          <section class="dh-card glass" v-if="feeds">
            <div class="dh-card-head"><span class="dh-card-title">资讯</span></div>
            <div class="dh-feeds">
              <div class="dh-feed big">
                <span class="dh-feed-tag unread">未读</span>
                <b>{{ feeds.unread }}</b><em>篇</em>
              </div>
              <div class="dh-feed">
                <span class="dh-feed-tag">订阅源</span>
                <b>{{ feeds.sources }}</b><em>个</em>
              </div>
              <p class="dh-feed-caption">订阅源持续为你汇聚信息，点击进入阅读。</p>
            </div>
          </section>
        </div>

        <!-- AI 对话链接 -->
        <section class="dh-card glass dh-ai" v-if="ai_conversations != null">
          <div class="dh-card-head">
            <span class="dh-card-title">AI 对话</span>
            <span class="dh-card-sub">{{ ai_conversations }} 段历史</span>
          </div>
          <p class="dh-ai-desc">沉淀过的每一次问答，都能成为你的个人知识库素材。</p>
          <router-link class="dh-ai-link" to="/assistant">前往 AI 对话 →</router-link>
        </section>

        <!-- 数据导出 -->
        <section class="dh-card glass dh-export">
          <div class="dh-card-head">
            <span class="dh-card-title">数据导出</span>
            <span class="dh-card-sub">把沉淀留一份在本地</span>
          </div>
          <div class="dh-export-actions">
            <button class="dh-exp" @click="exportNotes">🗒️ 笔记导出 Markdown</button>
            <button class="dh-exp" @click="exportFinance">💰 记账导出 CSV</button>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import BackButton from '@/components/BackButton.vue'
import { datahubApi } from '@/api/datahub'

const loading = ref(true)
const finance = ref(null)
const stocks = ref(null)
const travels = ref(null)
const notes = ref(null)
const task = ref(null)
const feeds = ref(null)
const ai_conversations = ref(null)

const padT = 12
const chartH = 128

// 数据导出（blob 下载）
async function downloadBlob(url) {
  const token = localStorage.getItem('token')
  const resp = await fetch(url, { headers: { authorization: `Bearer ${token}` } })
  if (!resp.ok) throw new Error('导出失败')
  const blob = await resp.blob()
  const a = document.createElement('a')
  const cd = resp.headers.get('content-disposition') || ''
  const m = /filename="?([^";]+)"?/.exec(cd)
  a.href = URL.createObjectURL(blob)
  a.download = m ? m[1] : 'export'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(a.href)
}
async function exportNotes() {
  try { await downloadBlob('/api/datahub/export/notes') } catch (e) { /* handled */ }
}
async function exportFinance() {
  const now = new Date()
  const y = now.getFullYear()
  const m0 = String(now.getMonth() + 1).padStart(2, '0')
  const params = `?start=${y}-${m0}-01&end=${y}-${m0}-${String(new Date(y, now.getMonth() + 1, 0).getDate()).padStart(2, '0')}`
  try { await downloadBlob('/api/finance/export' + params) } catch (e) { /* handled */ }
}

const chartBox = computed(() => `0 0 300 ${chartH}`)

const expPoints = computed(() => {
  if (!finance.value?.trend_labels) return []
  const labels = finance.value.trend_labels
  const vals = finance.value.trend_expense
  const n = labels.length
  const W = 300
  const max = Math.max(...vals, 1)
  return labels.map((label, i) => {
    const x = n <= 1 ? W / 2 : 18 + (i * (W - 36)) / (n - 1)
    const y = padT + (chartH - padT - 8) * (1 - (vals[i] / max))
    return { x, y, value: vals[i], label }
  })
})
const expPtsStr = computed(() => expPoints.value.map((p) => `${p.x},${p.y}`).join(' '))

const donePctQ = computed(() => {
  const t = task.value
  if (!t || (t.todo + t.done) === 0) return 0
  return Math.round((t.done / (t.todo + t.done)) * 100)
})
const donutDash = computed(() => {
  const c = 2 * Math.PI * 32
  return `${(donePctQ.value / 100) * c} ${c}`
})
const donutOffset = computed(() => 0)

const balanceCls = computed(() => (finance.value?.balance >= 0 ? 'pos' : 'neg'))

function money(v) {
  if (v == null) return '—'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function moneyShort(v) {
  return Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}
function fmtPct(v) {
  if (v == null) return '—'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%'
}
function pnlCls(v) {
  if (v == null) return ''
  return v >= 0 ? 'pos' : 'neg'
}
function pctOfTop(c, rank) {
  // 简单按名次递减条宽，视觉分档
  return Math.max(18, 100 - (rank - 1) * 14)
}
const CATS = ['#c25e4c', '#b3821f', '#5f7277', '#2f8077', '#4a5bd0']
function catColor(i) { return CATS[i % CATS.length] }

onMounted(async () => {
  try {
    const res = await datahubApi.overview()
    const d = res.data || {}
    finance.value = d.finance || null
    stocks.value = d.stocks || null
    travels.value = d.travels || null
    notes.value = d.notes || null
    task.value = d.task || null
    feeds.value = d.feeds || null
    ai_conversations.value = d.ai_conversations ?? null
  } catch (e) {
    /* 数据未就绪保持空态 */
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dh-page {
  position: relative;
  min-height: 100vh;
  padding-top: 84px;
  box-sizing: border-box;
  color: var(--lj-text);
  font-family: var(--font-serif);
  overflow-x: hidden;
}
.dh-inner { position: relative; z-index: 1; max-width: 1080px; margin: 0 auto; padding: 0 24px 60px; }

.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 60% 40% at 18% 6%, var(--glow-rain), transparent 60%),
    radial-gradient(ellipse 50% 40% at 85% 30%, var(--glow-gold), transparent 60%),
    var(--lj-bg);
}
.lj-paper-texture { position: absolute; inset: 0; opacity: 0.5;
  background:
    repeating-linear-gradient(0deg, rgba(127,168,163,0.02) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(127,168,163,0.014) 0 1px, transparent 1px 7px);
}
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4;
  background: radial-gradient(circle, rgba(127,168,163,0.14), transparent 70%); animation: dh-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 440px; height: 380px; top: 10%; left: -6%; }
.lj-wash.w2 { width: 400px; height: 340px; bottom: 4%; right: -5%; animation-delay: 8s; }
@keyframes dh-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(32px,-18px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

.dh-topbar { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.dh-crumb { font-size: 13px; color: var(--lj-text-3); cursor: pointer; letter-spacing: .08em; }
.dh-crumb:hover { color: var(--lj-dai); }

.dh-head { margin-bottom: 22px; }
.dh-title { margin: 0; font-size: 30px; font-weight: 600; letter-spacing: .1em; }
.dh-sub { margin: 8px 0 0; font-size: 12.5px; color: var(--lj-text-2); letter-spacing: .16em; }

.dh-loading { text-align: center; padding: 60px 0; color: var(--lj-text-3); letter-spacing: .2em; }

.dh-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 18px; }
.dh-kpi { padding: 18px 20px; border-radius: 18px; display: flex; flex-direction: column; gap: 6px; }
.dh-kpi-label { font-size: 11.5px; color: var(--lj-text-3); letter-spacing: .14em; }
.dh-kpi-val { font-size: 26px; font-weight: 700; letter-spacing: .02em; }
.dh-kpi-val .dh-unit { font-style: normal; font-size: 14px; color: var(--lj-text-3); margin-left: 3px; }
.dh-kpi-sub { font-size: 12px; color: var(--lj-text-2); }
.pos { color: #c25e4c; }
.neg { color: #2f8077; }

.dh-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.dh-card { padding: 18px 20px 20px; border-radius: 18px; }
.dh-card-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }
.dh-card-title { font-size: 15px; font-weight: 600; letter-spacing: .08em; }
.dh-card-sub { font-size: 11px; color: var(--lj-text-3); }

.dh-chart { width: 100%; height: 128px; display: block; }
.dh-chart-g { stroke: rgba(127,168,163,0.12); stroke-width: 1; }
.dh-chart-poly { fill: none; stroke: var(--lj-dai); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.dh-chart-dot { fill: var(--lj-dai); }
.dh-chart-x { font-size: 9px; fill: var(--lj-text-3); }
.dh-chart-xy { font-size: 9px; fill: var(--lj-text-2); }

.dh-cats { display: flex; flex-direction: column; gap: 10px; }
.dh-cat { display: flex; align-items: center; gap: 10px; }
.dh-cat-icon { width: 30px; height: 30px; flex: none; border-radius: 9px; display: flex; align-items: center; justify-content: center;
  font-size: 16px; border: 1px solid var(--lj-line); background: rgba(127,168,163,.09); }
.dh-cat-mid { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.dh-cat-name { font-size: 12.5px; }
.dh-cat-track { height: 6px; border-radius: 999px; background: rgba(127,168,163,.14); overflow: hidden; }
.dh-cat-fill { display: block; height: 100%; border-radius: 999px; transition: width .5s; }
.dh-cat-val { font-size: 13px; font-weight: 600; }

.dh-donut { display: flex; align-items: center; gap: 18px; }
.dh-donut-svg { width: 90px; height: 90px; transform: rotate(-90deg); }
.dh-donut-ring { fill: none; stroke: rgba(127,168,163,.14); stroke-width: 8; }
.dh-donut-bar { fill: none; stroke: var(--lj-dai); stroke-width: 8; stroke-linecap: round; transition: stroke-dasharray .6s; }
.dh-donut-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.dh-donut-center b { font-size: 18px; }
.dh-donut-center span { font-size: 10px; color: var(--lj-text-3); }
.dh-donut-legend { font-size: 12.5px; color: var(--lj-text-2); display: flex; align-items: center; gap: 8px; }
.dh-legend-dot { width: 9px; height: 9px; border-radius: 3px; display: inline-block; }
.dh-legend-dot.done { background: var(--lj-dai); margin-left: 6px; }
.dh-legend-dot.todo { background: rgba(199,169,107,.55); margin-left: 12px; }

.dh-feeds { display: flex; flex-direction: column; gap: 12px; }
.dh-feed { display: flex; align-items: baseline; gap: 8px; font-size: 14px; }
.dh-feed.big { font-size: 22px; font-weight: 700; align-items: baseline; }
.dh-feed b { font-size: 1.15em; }
.dh-feed em { font-style: normal; font-size: 12px; color: var(--lj-text-3); }
.dh-feed-tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; color: var(--lj-text-2);
  background: rgba(127,168,163,.12); }
.dh-feed-tag.unread { color: #c25e4c; background: rgba(194,94,76,.12); }
.dh-feed-caption { font-size: 11.5px; color: var(--lj-text-3); margin: 0; }

.dh-ai { display: flex; flex-direction: column; gap: 4px; }
.dh-ai-desc { margin: 0; font-size: 12.5px; color: var(--lj-text-2); }
.dh-ai-link { font-size: 13px; text-decoration: none; color: var(--lj-dai); letter-spacing: .06em; }
.dh-ai-link:hover { text-decoration: underline; }
.dh-export { display: flex; flex-direction: column; gap: 12px; }
.dh-export-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.dh-exp { padding: 10px 18px; border-radius: 12px; border: 1px solid var(--lj-line); background: rgba(127,168,163,.10);
  color: var(--lj-text); font-family: var(--font-serif); font-size: 13px; cursor: pointer; transition: all .22s; }
.dh-exp:hover { border-color: var(--lj-dai); color: var(--lj-dai); transform: translateY(-1px); }

@media (max-width: 760px) {
  .dh-grid { grid-template-columns: 1fr; }
  .dh-inner { padding: 0 16px 40px; }
}
</style>
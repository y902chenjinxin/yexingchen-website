<template>
  <!-- 移动端：独立沉浸式工作台首页 -->
  <MobileWorkbenchHome v-if="isMobile" />

  <!-- 桌面端：单屏一体化「数据驾驶舱」——首屏看全部，0 隐藏 -->
  <div v-else class="workbench-page">
    <!-- 顶栏品牌条（极简） -->
    <header class="wb-hero">
      <div class="wb-eyebrow">玄 黄 · 工 作 台</div>
      <h1 class="wb-title">把零散念头，沉淀为数据。</h1>
      <p class="wb-subtitle">今日 · 本月 · 累计，一目了然。</p>
    </header>

    <!-- S1：核心 KPI + 趋势并排（首屏上半） -->
    <section class="wb-grid-top">
      <!-- 左列：4 个 KPI -->
      <div class="wb-kpi-col">
        <KpiTile label="活跃倒计时" :val="kpi.countdown.active_count" sub="含纪念日" @click="$router.push('/tool/countdown')" clickable />
        <KpiTile label="足迹省份" :val="kpi.travel.province_count" :unit="`/ 34`" :sub="`${kpi.travel.travel_count} 段旅程 · ${kpi.travel.city_count} 城`" @click="$router.push('/travels')" clickable />
        <KpiTile label="本月净流入" :val="kpi.finance.net" unit="¥" :delta="`收 ${kpi.finance.month_income} / 支 ${kpi.finance.month_expense}`" :delta-tone="kpi.finance.net >= 0 ? 'up' : 'dn'" @click="$router.push('/finance')" clickable />
        <KpiTile label="笔记" :val="kpi.note_count" sub="最近 5 篇可编辑" @click="$router.push('/notes')" clickable />
      </div>

      <!-- 中列：记账 30 天 -->
      <div class="trend-card wb-trend-mid">
        <div class="trend-head">
          <div class="trend-title">记账 · 最近 30 天</div>
          <div class="trend-meta">
            <span class="trend-meta-item"><i class="trend-dot dot-in"></i>收入</span>
            <span class="trend-meta-item"><i class="trend-dot dot-out"></i>支出</span>
            <RouterLink class="trend-link" to="/finance">详情 →</RouterLink>
          </div>
        </div>
        <TrendBars :data="kpi.finance.trend" :height="160" mode="expense" />
      </div>

      <!-- 右列：倒计时 + 自选股 紧凑双段 -->
      <div class="wb-side-col">
        <div class="trend-card wb-side-card">
          <div class="trend-head">
            <div class="trend-title">即将到来</div>
            <RouterLink class="trend-link" to="/tool/countdown">全部 →</RouterLink>
          </div>
          <ul class="cd-list">
            <li v-for="cd in kpi.countdown.upcoming_top" :key="cd.id" @click="$router.push(`/tool/countdown/${cd.id}`)">
              <span class="cd-dot" :style="{ background: cd.color || 'var(--dp-accent)' }"></span>
              <span class="cd-title">{{ cd.title }}</span>
              <span class="cd-days">{{ cd.days_left }} 天</span>
            </li>
            <li v-if="!kpi.countdown.upcoming_top.length" class="cd-empty">暂无</li>
          </ul>
        </div>
        <div class="trend-card wb-side-card">
          <div class="trend-head">
            <div class="trend-title">自选股</div>
            <RouterLink class="trend-link" to="/stocks">详情 →</RouterLink>
          </div>
          <ul class="stock-list">
            <li v-for="h in kpi.stocks.holdings" :key="h.code">
              <span class="st-name">{{ h.name }}</span>
              <span class="st-meta">{{ h.code }}</span>
              <span class="st-meta">{{ h.shares }} · ¥{{ h.cost }}</span>
            </li>
            <li v-if="!kpi.stocks.holdings.length" class="cd-empty">尚未添加</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- S2：核心信息一体化（笔记 / 任务 / 标签 / 习惯打卡 / AI 简报） -->
    <section class="wb-grid-mid">
      <!-- AI 简报 + 习惯打卡 横排（首屏关键行动） -->
      <div class="wb-action-row">
        <div v-if="moduleVisible.brief" class="wb-action-card">
          <AiBriefCard :summary="summary" />
        </div>
        <div v-if="moduleVisible.habits" class="wb-action-card">
          <HabitsCard />
        </div>
      </div>

      <!-- 笔记 + 任务 + 标签 三栏 -->
      <div class="wb-row">
        <div class="card glass">
          <div class="card-head">
            <div class="card-title">最近笔记</div>
            <RouterLink class="card-link" to="/notes">全部 →</RouterLink>
          </div>
          <ul class="nt-list">
            <li v-for="n in kpi.recent_notes" :key="n.id" @click="$router.push(`/notes/${n.id}`)">
              <span class="nt-dot" :class="n.status === 'completed' ? 'on' : ''"></span>
              <span class="nt-title">{{ n.title || '（无标题）' }}</span>
              <span class="nt-meta">{{ shortTime(n.updated_at || n.created_at) }}</span>
            </li>
            <li v-if="!kpi.recent_notes.length" class="nt-empty">还没有笔记</li>
          </ul>
        </div>

        <div class="card glass">
          <div class="card-head">
            <div class="card-title">今日 · 待办</div>
            <RouterLink class="card-link" to="/tasks">全部 →</RouterLink>
          </div>
          <ul class="ts-list">
            <li v-for="t in kpi.today_tasks" :key="t.id" @click="$router.push('/tasks')">
              <span class="ts-dot" :class="`pri-${t.priority || 'medium'}`"></span>
              <span class="ts-title">{{ t.title }}</span>
              <span v-if="t.due_date" class="ts-meta">{{ shortTime(t.due_date) }}</span>
            </li>
            <li v-if="!kpi.today_tasks.length" class="ts-empty">今日无待办</li>
            <li v-if="kpi.overdue_tasks.length" class="ts-overdue">⚠ 逾期 {{ kpi.overdue_tasks.length }} 条</li>
          </ul>
        </div>

        <div class="card glass">
          <div class="card-head">
            <div class="card-title">标签 · 主题</div>
            <RouterLink class="card-link" to="/notes">管理 →</RouterLink>
          </div>
          <div class="tag-cloud">
            <RouterLink
              v-for="t in kpi.tag_cloud"
              :key="t.name"
              class="tag-chip"
              :to="{ path: '/notes', query: { q: t.name } }"
            >#{{ t.name }}</RouterLink>
            <p v-if="!kpi.tag_cloud.length" class="tag-empty">还没有标签</p>
          </div>
        </div>
      </div>
    </section>

    <!-- S3：资讯流（顶部单一长条，不占首屏） -->
    <div v-if="moduleVisible.feeds" class="wb-feedsbar">
      <WorkbenchFeedsBar :feeds="feeds" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MobileWorkbenchHome from '@/components/mobile/MobileWorkbenchHome.vue'
import KpiTile from '@/components/dashboard/KpiTile.vue'
import TrendBars from '@/components/dashboard/TrendBars.vue'
import AiBriefCard from '@/components/workbench/AiBriefCard.vue'
import HabitsCard from '@/components/workbench/HabitsCard.vue'
import WorkbenchFeedsBar from '@/components/workbench/WorkbenchFeedsBar.vue'
import { useWorkbenchStore } from '@/stores/workbench'
import { usePrefsStore } from '@/stores/prefs'
import { feedsApi } from '@/api/feeds'
import { useIsMobile } from '@/composables/useIsMobile'

const router = useRouter()
const { isMobile } = useIsMobile()
const wbStore = useWorkbenchStore()
const prefs = usePrefsStore()
const moduleVisible = computed(() => prefs.moduleVisible)

const loaded = ref(false)
const summary = ref(null)
const kpi = ref({
  countdown: { active_count: 0, upcoming_top: [] },
  travel: { travel_count: 0, province_count: 0, city_count: 0 },
  finance: { net: 0, month_income: 0, month_expense: 0, trend: [] },
  stocks: { holdings: [] },
  note_count: 0,
  recent_notes: [],
  draft_notes: [],
  today_tasks: [],
  overdue_tasks: [],
  tag_cloud: [],
})
const feeds = ref([])

function shortTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const now = new Date()
    const diff = (now - d) / 1000
    if (diff < 60) return '刚刚'
    if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
    if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
    if (diff < 86400 * 7) return Math.floor(diff / 86400) + ' 天前'
    return d.toISOString().slice(5, 10)
  } catch { return '' }
}

onMounted(async () => {
  // F6 离线快照：先恢复上次成功的 summary 到 UI（≤10 分钟内），立刻可读，再后台拉新数据合并
  try {
    const cached = localStorage.getItem('yx_wb_summary')
    if (cached) {
      const { ts, data } = JSON.parse(cached)
      if (ts && Date.now() - ts < 10 * 60 * 1000 && data) {
        summary.value = data
        loaded.value = true
      }
    }
    const cachedFeeds = localStorage.getItem('yx_wb_feeds')
    if (cachedFeeds) {
      const { ts, data } = JSON.parse(cachedFeeds)
      if (ts && Date.now() - ts < 10 * 60 * 1000 && data) feeds.value = data
    }
  } catch { /* localStorage 不可用或数据损坏，静默 */ }

  try {
    const r = await wbStore.loadSummary()
    summary.value = r || {}
    const s = r || {}
    kpi.value = {
      countdown: s.countdown || kpi.value.countdown,
      travel: s.travel || kpi.value.travel,
      finance: s.finance || kpi.value.finance,
      stocks: s.stocks || kpi.value.stocks,
      note_count: (s.recent_notes || []).length + (s.draft_notes || []).length,
      recent_notes: (s.recent_notes || []).slice(0, 5),
      draft_notes: s.draft_notes || [],
      today_tasks: (s.today_tasks || []).slice(0, 5),
      overdue_tasks: s.overdue_tasks || [],
      tag_cloud: (s.tag_cloud || []).slice(0, 18),
    }
    try { localStorage.setItem('yx_wb_summary', JSON.stringify({ ts: Date.now(), data: summary.value })) } catch {}
  } catch (e) {
    if (!loaded.value) loaded.value = false
  }
  try {
    const r = await feedsApi.dashboard()
    feeds.value = r?.data?.recent || []
    try { localStorage.setItem('yx_wb_feeds', JSON.stringify({ ts: Date.now(), data: feeds.value })) } catch {}
  } catch { /* 静默 */ }
  if (!loaded.value) loaded.value = true
})
</script>

<style scoped>
/* ===== 单页驾驶舱布局 ===== */
.workbench-page {
  position: relative;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  width: 100%;
  padding: 96px 28px 60px;
  box-sizing: border-box;
  color: var(--dp-text);
  min-height: 100vh;
  background: var(--dp-bg);
}

/* ===== Hero 极简 ===== */
.wb-hero { margin: 0 4px 14px; }
.wb-eyebrow { font-size: 11px; letter-spacing: .32em; color: var(--dp-accent); margin-bottom: 4px; }
.wb-title { font-size: 22px; font-weight: 700; margin: 0 0 2px; color: var(--dp-text); letter-spacing: .02em; }
.wb-subtitle { font-size: 12.5px; color: var(--dp-text3); margin: 0; }

/* ===== S1：核心 KPI + 趋势并排（首屏上半） ===== */
.wb-grid-top {
  display: grid;
  /* 左：4 KPI（自适应列）；中：记账趋势；右：倒计时 + 自选股堆叠 */
  grid-template-columns: minmax(280px, 1.1fr) minmax(360px, 1.6fr) minmax(280px, 1.1fr);
  gap: 14px;
  margin-bottom: 14px;
}
.wb-kpi-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 14px;
}
.trend-card {
  background: var(--dp-surface); border: 1px solid var(--dp-line); border-radius: var(--dp-radius);
  padding: 14px 16px 12px; box-shadow: var(--dp-shadow);
}
.trend-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.trend-title { font-size: 13px; font-weight: 600; color: var(--dp-text); letter-spacing: .02em; }
.trend-meta { display: inline-flex; gap: 10px; font-size: 11.5px; color: var(--dp-text3); }
.trend-meta-item { display: inline-flex; align-items: center; gap: 4px; }
.trend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.trend-dot.dot-in { background: #34d399; }
.trend-dot.dot-out { background: #f87171; }
.trend-link { color: var(--dp-accent); font-size: 12px; text-decoration: none; }
.trend-link:hover { text-decoration: underline; }

.wb-trend-mid { min-height: 200px; display: flex; flex-direction: column; }
.wb-trend-mid :deep(.tb-bars) { flex: 1; }

.wb-side-col { display: grid; grid-template-rows: 1fr 1fr; gap: 14px; }
.wb-side-card { display: flex; flex-direction: column; }
.cd-list, .stock-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.cd-list li, .stock-list li {
  display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: 6px;
  cursor: pointer; transition: background .15s; font-size: 12.5px;
}
.cd-list li:hover, .stock-list li:hover { background: var(--dp-accent-faint, rgba(167,139,250,.08)); }
.cd-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.cd-title { flex: 1; color: var(--dp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cd-days { color: var(--dp-accent); font-weight: 600; font-variant-numeric: tabular-nums; }
.st-name { flex: 1; color: var(--dp-text); }
.st-meta { color: var(--dp-text3); font-size: 11px; font-variant-numeric: tabular-nums; margin-left: 4px; }
.cd-empty { color: var(--dp-text3); font-size: 12px; padding: 8px 0; text-align: center; }

/* ===== S2：核心信息一体化 ===== */
.wb-grid-mid { display: flex; flex-direction: column; gap: 14px; margin-bottom: 14px; }

/* AI 简报 + 习惯打卡 横排（一体化行动入口） */
.wb-action-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
}
.wb-action-card > * { height: 100%; }

.wb-row {
  display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 14px;
}
.card {
  background: var(--dp-surface); border: 1px solid var(--dp-line); border-radius: var(--dp-radius);
  padding: 14px 16px 12px; box-shadow: var(--dp-shadow);
}
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.card-title { font-size: 13px; font-weight: 600; color: var(--dp-text); letter-spacing: .02em; }
.card-link { color: var(--dp-accent); font-size: 12px; text-decoration: none; }
.card-link:hover { text-decoration: underline; }

.nt-list, .ts-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
.nt-list li, .ts-list li {
  display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: 6px;
  cursor: pointer; transition: background .15s; font-size: 12.5px;
}
.nt-list li:hover, .ts-list li:hover { background: var(--dp-accent-faint, rgba(167,139,250,.08)); }
.nt-dot, .ts-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--dp-text3); flex-shrink: 0; }
.nt-dot.on { background: var(--dp-accent); }
.ts-dot.pri-high { background: #f87171; }
.ts-dot.pri-medium { background: #fbbf24; }
.ts-dot.pri-low { background: #60a5fa; }
.nt-title, .ts-title { flex: 1; color: var(--dp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nt-meta, .ts-meta { color: var(--dp-text3); font-size: 11px; font-variant-numeric: tabular-nums; }
.nt-empty, .ts-empty { color: var(--dp-text3); font-size: 12px; padding: 8px 0; text-align: center; }
.ts-overdue { color: #f87171; font-size: 11px; padding: 4px 6px; }

.tag-cloud { display: flex; flex-wrap: wrap; gap: 5px; }
.tag-chip {
  font-size: 11px; padding: 3px 9px; border-radius: 12px;
  background: var(--dp-accent-faint, rgba(167,139,250,.14)); color: var(--dp-accent);
  text-decoration: none; transition: background .15s;
}
.tag-chip:hover { background: var(--dp-accent); color: var(--dp-bg, #000); }
.tag-empty { color: var(--dp-text3); font-size: 12px; padding: 6px 0; }

/* ===== S3：资讯流 ===== */
.wb-feedsbar {}

/* ===== 自适应 ===== */
@media (max-width: 1280px) {
  .wb-grid-top { grid-template-columns: minmax(240px, 1fr) minmax(320px, 1.4fr) minmax(240px, 1fr); }
}
@media (max-width: 1024px) {
  .wb-grid-top {
    grid-template-columns: 1fr 1fr;
    grid-template-areas: "kpi trend" "side side";
  }
  .wb-kpi-col { grid-area: kpi; }
  .wb-trend-mid { grid-area: trend; }
  .wb-side-col { grid-area: side; grid-template-columns: 1fr 1fr; grid-template-rows: auto; }
}
@media (max-width: 768px) {
  .workbench-page { padding: 80px 14px 40px; }
  .wb-grid-top { grid-template-columns: 1fr; grid-template-areas: "kpi" "trend" "side"; }
  .wb-kpi-col { grid-area: kpi; }
  .wb-trend-mid { grid-area: trend; }
  .wb-side-col { grid-area: side; grid-template-columns: 1fr; }
  .wb-action-row, .wb-row { grid-template-columns: 1fr; }
}
</style>

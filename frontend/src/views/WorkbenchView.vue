<template>
  <!-- 移动端：独立沉浸式工作台首页 -->
  <MobileWorkbenchHome v-if="isMobile" />

  <div v-else class="workbench-page">
    <!-- S1 高级感视觉锚点：仅保留柔和光斑（已去掉网格 + 散布圆点） -->

    <!-- 顶栏品牌条（替代旧的"玉简 hero"） -->
    <section class="wb-hero">
      <div class="wb-eyebrow"><span>玄 黄 · 工 作 台</span></div>
      <h1 class="wb-title">把零散念头，沉淀为数据。</h1>
      <p class="wb-subtitle">今日 · 本月 · 累计，一目了然。</p>
    </section>

    <!-- 天气小部件（纯前端 / Open-Meteo，独立加载不阻塞主内容） -->
    <section v-if="moduleVisible.weather" class="wb-wx">
      <WeatherCard />
    </section>

    <!-- KPI 4 卡：倒计时 / 足迹 / 记账 / 笔记 -->
    <section class="wb-kpi" v-if="loaded">
      <KpiTile label="活跃倒计时" :val="kpi.countdown.active_count" sub="含纪念日" @click="$router.push('/tool/countdown')" clickable />
      <KpiTile label="足迹省份" :val="kpi.travel.province_count" :unit="`/ 34`" :sub="`${kpi.travel.travel_count} 段旅程 · ${kpi.travel.city_count} 城`" @click="$router.push('/travels')" clickable />
      <KpiTile label="本月净流入" :val="kpi.finance.net" unit="¥" :delta="`收 ${kpi.finance.month_income} / 支 ${kpi.finance.month_expense}`" :delta-tone="kpi.finance.net >= 0 ? 'up' : 'dn'" @click="$router.push('/finance')" clickable />
      <KpiTile label="笔记" :val="kpi.note_count" sub="最近 5 篇可编辑" @click="$router.push('/notes')" clickable />
    </section>
    <section v-else class="wb-kpi">
      <div class="kpi kpi-skel" v-for="i in 4" :key="i">
        <Skeleton type="block" width="40%" height="10px" radius="3px" />
        <Skeleton type="block" width="56%" height="26px" radius="6px" />
        <Skeleton type="block" width="70%" height="10px" radius="3px" />
      </div>
    </section>

    <!-- 趋势图表 3 列：记账 30 天走势 + 倒计时 5 条 + 自选股 -->
    <section class="wb-trend">
      <!-- 记账 30 天 -->
      <div class="trend-card">
        <div class="trend-head">
          <div class="trend-title">记账 · 最近 30 天</div>
          <div class="trend-meta">
            <span class="trend-meta-item"><i class="trend-dot dot-in"></i>收入</span>
            <span class="trend-meta-item"><i class="trend-dot dot-out"></i>支出</span>
            <RouterLink class="trend-link" to="/finance">详情 →</RouterLink>
          </div>
        </div>
        <TrendBars :data="kpi.finance.trend" :height="140" mode="expense" />
      </div>

      <!-- 倒计时最近 5 条 -->
      <div class="trend-card">
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
          <li v-if="!kpi.countdown.upcoming_top.length" class="cd-empty">暂无即将到来的事件</li>
        </ul>
      </div>

      <!-- 自选股 -->
      <div class="trend-card">
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
          <li v-if="!kpi.stocks.holdings.length" class="cd-empty">尚未添加自选</li>
        </ul>
      </div>
    </section>

    <!-- AI 简报卡 -->
    <section v-if="moduleVisible.brief" class="wb-brief">
      <AiBriefCard :summary="summary" />
    </section>

    <!-- 习惯打卡横幅卡 -->
    <section v-if="moduleVisible.habits" class="wb-habits">
      <HabitsCard />
    </section>

    <!-- 笔记 + 自选股 + 任务 三栏 -->
    <section class="wb-row">
      <!-- 笔记 -->
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
          <li v-if="!kpi.recent_notes.length" class="nt-empty">还没有笔记，点右上去写第一篇</li>
        </ul>
      </div>

      <!-- 任务 -->
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
          <li v-if="!kpi.today_tasks.length" class="ts-empty">今日无待办任务</li>
          <li v-if="kpi.overdue_tasks.length" class="ts-overdue">
            ⚠ 逾期 {{ kpi.overdue_tasks.length }} 条
          </li>
        </ul>
      </div>

      <!-- 标签云 -->
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
          <p v-if="!kpi.tag_cloud.length" class="tag-empty">还没有标签，去笔记里打标签</p>
        </div>
      </div>
    </section>

    <!-- 资讯流 -->
    <div v-if="moduleVisible.feeds" class="wb-body wb-feedsbar">
      <WorkbenchFeedsBar :feeds="feeds" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import MobileWorkbenchHome from '@/components/mobile/MobileWorkbenchHome.vue'
import KpiTile from '@/components/dashboard/KpiTile.vue'
import TrendBars from '@/components/dashboard/TrendBars.vue'
import AiBriefCard from '@/components/workbench/AiBriefCard.vue'
import HabitsCard from '@/components/workbench/HabitsCard.vue'
import WeatherCard from '@/components/workbench/WeatherCard.vue'
import WorkbenchFeedsBar from '@/components/workbench/WorkbenchFeedsBar.vue'
import Skeleton from '@/components/Skeleton.vue'
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
    // 网络失败时若已有缓存就保留，无缓存则保持骨架
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
.workbench-page {
  position: relative;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  width: 100%;
  padding: 96px 0 0;
  box-sizing: border-box;
  color: var(--dp-text);
  min-height: 100vh;
  overflow-x: hidden;
  background: var(--dp-bg);
}

/* 工作台 · 顶栏品牌条（替代"玉简 hero"） */
.wb-hero { padding: 8px 32px 18px; position: relative; z-index: 1; }
.wb-eyebrow { font-size: 11px; letter-spacing: .32em; color: var(--dp-accent); margin-bottom: 6px; }
.wb-title { font-size: 22px; font-weight: 700; margin: 0 0 4px; color: var(--dp-text); letter-spacing: .02em; }
.wb-subtitle { font-size: 13px; color: var(--dp-text3); margin: 0; }

/* 天气小部件 */
.wb-wx { padding: 0 32px 14px; position: relative; z-index: 1; }

/* KPI 4 卡 */
.wb-kpi {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
  padding: 0 32px 18px; position: relative; z-index: 1;
}
.kpi.kpi-skel { display: flex; flex-direction: column; gap: 8px; padding: 18px; border-radius: var(--dp-radius); background: var(--dp-surface); border: 1px solid var(--dp-line); }

/* 趋势 3 列 */
.wb-trend {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
  padding: 0 32px 18px; position: relative; z-index: 1;
}
.trend-card {
  background: var(--dp-surface); border: 1px solid var(--dp-line); border-radius: var(--dp-radius);
  padding: 16px 18px 14px; box-shadow: var(--dp-shadow);
}
.trend-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.trend-title { font-size: 13px; font-weight: 600; color: var(--dp-text); letter-spacing: .02em; }
.trend-meta { display: inline-flex; gap: 10px; font-size: 11.5px; color: var(--dp-text3); }
.trend-meta-item { display: inline-flex; align-items: center; gap: 4px; }
.trend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.trend-dot.dot-in { background: #34d399; }
.trend-dot.dot-out { background: #f87171; }
.trend-link { color: var(--dp-accent); font-size: 12px; text-decoration: none; }
.trend-link:hover { text-decoration: underline; }

.cd-list, .stock-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.cd-list li, .stock-list li {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px;
  cursor: pointer; transition: background .15s; font-size: 12.5px;
}
.cd-list li:hover, .stock-list li:hover { background: var(--dp-accent-faint, rgba(167,139,250,.08)); }
.cd-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cd-title { flex: 1; color: var(--dp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cd-days { color: var(--dp-accent); font-weight: 600; font-variant-numeric: tabular-nums; }
.st-name { flex: 1; color: var(--dp-text); }
.st-meta { color: var(--dp-text3); font-size: 11.5px; font-variant-numeric: tabular-nums; margin-left: 6px; }
.cd-empty { color: var(--dp-text3); font-size: 12px; padding: 12px 0; text-align: center; }

/* AI 简报 + 习惯 */
.wb-brief, .wb-habits { padding: 0 32px 18px; position: relative; z-index: 1; }

/* 笔记 + 任务 + 标签 三栏 */
.wb-row {
  display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 14px;
  padding: 0 32px 18px; position: relative; z-index: 1;
}
.card {
  background: var(--dp-surface); border: 1px solid var(--dp-line); border-radius: var(--dp-radius);
  padding: 16px 18px 14px; box-shadow: var(--dp-shadow);
}
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.card-title { font-size: 13px; font-weight: 600; color: var(--dp-text); letter-spacing: .02em; }
.card-link { color: var(--dp-accent); font-size: 12px; text-decoration: none; }
.card-link:hover { text-decoration: underline; }

.nt-list, .ts-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.nt-list li, .ts-list li {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px;
  cursor: pointer; transition: background .15s; font-size: 12.5px;
}
.nt-list li:hover, .ts-list li:hover { background: var(--dp-accent-faint, rgba(167,139,250,.08)); }
.nt-dot, .ts-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--dp-text3); flex-shrink: 0; }
.nt-dot.on { background: var(--dp-accent); }
.ts-dot.pri-high { background: #f87171; }
.ts-dot.pri-medium { background: #fbbf24; }
.ts-dot.pri-low { background: #60a5fa; }
.nt-title, .ts-title { flex: 1; color: var(--dp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nt-meta, .ts-meta { color: var(--dp-text3); font-size: 11.5px; font-variant-numeric: tabular-nums; }
.nt-empty, .ts-empty { color: var(--dp-text3); font-size: 12px; padding: 12px 0; text-align: center; }
.ts-overdue { color: #f87171; font-size: 11.5px; padding: 4px 8px; }

.tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; }
.tag-chip {
  font-size: 11.5px; padding: 3px 9px; border-radius: 12px;
  background: var(--dp-accent-faint, rgba(167,139,250,.14)); color: var(--dp-accent);
  text-decoration: none; transition: background .15s;
}
.tag-chip:hover { background: var(--dp-accent); color: var(--dp-bg, #000); }
.tag-empty { color: var(--dp-text3); font-size: 12px; padding: 8px 0; }

/* 资讯 */
.wb-body { padding: 0 32px 80px; position: relative; z-index: 1; }

/* 自适应：窄屏退化为单列 */
@media (max-width: 1100px) {
  .wb-kpi { grid-template-columns: repeat(2, 1fr); }
  .wb-trend { grid-template-columns: 1fr; }
  .wb-row { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .wb-hero, .wb-wx, .wb-kpi, .wb-trend, .wb-brief, .wb-habits, .wb-row, .wb-body { padding-left: 16px; padding-right: 16px; }
  .wb-kpi { grid-template-columns: 1fr 1fr; }
}
</style>

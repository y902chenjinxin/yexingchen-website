<template>
  <!-- 移动端：独立沉浸式工作台首页 -->
  <MobileWorkbenchHome v-if="isMobile" />

  <!-- 桌面端：Bento Grid 2.0 数据驾驶舱 -->
  <div v-else class="workbench-page">
    <header class="wb-hero">
      <div class="wb-eyebrow">玄 黄 · 工 作 台</div>
      <h1 class="wb-title">把零散念头，沉淀为数据。</h1>
      <p class="wb-subtitle">今日 · 本月 · 累计，一目了然。</p>
    </header>

    <!-- ============ Bento S1：核心数字 + 记账趋势（不对称大块） ============ -->
    <section class="bento-s1">
      <!-- 左列：净流入（大块）+ 足迹 / 笔记（小块） + 倒计时 -->
      <div class="bento-s1-left">
        <!-- Hero KPI：净流入 -->
        <button
          class="bento-hero"
          :class="kpi.finance.net >= 0 ? 'up' : 'dn'"
          @click="$router.push('/finance')"
        >
          <div class="bento-hero-eyebrow">本月净流入</div>
          <div class="bento-hero-num">
            <span class="bento-hero-sign">{{ kpi.finance.net >= 0 ? '+' : '−' }}</span>
            <span class="bento-hero-val">¥{{ Math.abs(kpi.finance.net || 0).toLocaleString() }}</span>
          </div>
          <div class="bento-hero-foot">
            <span><i class="bento-dot dot-in"></i>收 ¥{{ (kpi.finance.month_income || 0).toLocaleString() }}</span>
            <span><i class="bento-dot dot-out"></i>支 ¥{{ (kpi.finance.month_expense || 0).toLocaleString() }}</span>
          </div>
        </button>

        <!-- 小块：足迹 + 笔记 -->
        <button class="bento-mini" @click="$router.push('/travels')">
          <div class="bento-mini-eyebrow">足迹</div>
          <div class="bento-mini-num">{{ kpi.travel.province_count }}<span class="bento-mini-unit">/ 34 省</span></div>
          <div class="bento-mini-foot">{{ kpi.travel.travel_count }} 段旅程 · {{ kpi.travel.city_count }} 城</div>
        </button>
        <button class="bento-mini" @click="$router.push('/notes')">
          <div class="bento-mini-eyebrow">笔记</div>
          <div class="bento-mini-num">{{ kpi.note_count }}</div>
          <div class="bento-mini-foot">最近 5 篇可编辑</div>
        </button>

        <!-- 倒计时：横向列表 -->
        <div class="bento-cd">
          <div class="bento-cd-head">
            <span class="bento-cd-title">即将到来</span>
            <RouterLink class="bento-cd-link" to="/tool/countdown">全部 →</RouterLink>
          </div>
          <ul class="bento-cd-list">
            <li v-for="cd in kpi.countdown.upcoming_top" :key="cd.id" @click="$router.push(`/tool/countdown/${cd.id}`)">
              <span class="cd-dot" :style="{ background: cd.color || 'var(--dp-accent)' }"></span>
              <span class="cd-title">{{ cd.title }}</span>
              <span class="cd-days">{{ cd.days_left }} 天</span>
            </li>
            <li v-if="!kpi.countdown.upcoming_top.length" class="cd-empty">暂无即将到来的事件</li>
          </ul>
        </div>
      </div>

      <!-- 右列：记账 30 天（大块 2 行高）+ 天气（小块） -->
      <div class="bento-s1-right">
        <div class="bento-trend">
          <div class="bento-trend-head">
            <div class="bento-trend-title">记账 · 最近 30 天</div>
            <div class="bento-trend-meta">
              <span class="trend-meta-item"><i class="bento-dot dot-in"></i>收入</span>
              <span class="trend-meta-item"><i class="bento-dot dot-out"></i>支出</span>
              <RouterLink class="trend-link" to="/finance">详情 →</RouterLink>
            </div>
          </div>
          <TrendBars :data="kpi.finance.trend" :height="200" mode="expense" />
        </div>
        <!-- 天气（v2.39.7 新增 Bento 内嵌） -->
        <div v-if="moduleVisible.weather" class="bento-wx">
          <WeatherCard />
        </div>
      </div>
    </section>

    <!-- ============ Bento S2：两卡（自选股 + 今日待办）============ -->
    <section class="bento-s2">
      <div class="bento-card">
        <div class="bento-card-head">
          <div class="bento-card-title">自选股</div>
          <RouterLink class="bento-card-link" to="/stocks">管理 →</RouterLink>
        </div>
        <ul class="bento-card-list stock-list">
          <li v-for="h in kpi.stocks.holdings" :key="h.code">
            <span class="st-name">{{ h.name }}</span>
            <span class="st-code">{{ h.code }}</span>
            <span class="st-meta">{{ h.shares }} · ¥{{ h.cost }}</span>
          </li>
          <li v-if="!kpi.stocks.holdings.length" class="cd-empty">尚未添加</li>
        </ul>
      </div>

      <div class="bento-card">
        <div class="bento-card-head">
          <div class="bento-card-title">今日 · 待办</div>
          <RouterLink class="bento-card-link" to="/tasks">全部 →</RouterLink>
        </div>
        <ul class="bento-card-list ts-list">
          <li v-for="t in kpi.today_tasks" :key="t.id" @click="$router.push('/tasks')">
            <span class="ts-dot" :class="`pri-${t.priority || 'medium'}`"></span>
            <span class="ts-title">{{ t.title }}</span>
            <span v-if="t.due_date" class="ts-meta">{{ shortTime(t.due_date) }}</span>
          </li>
          <li v-if="!kpi.today_tasks.length" class="ts-empty">今日无待办</li>
          <li v-if="kpi.overdue_tasks.length" class="ts-overdue">⚠ 逾期 {{ kpi.overdue_tasks.length }} 条</li>
        </ul>
      </div>
    </section>

    <!-- ============ Bento S3：每日一言 + 历史上的今天（文化小卡） ============ -->
    <section class="bento-s3">
      <div class="bento-card bento-card--zero">
        <DailyQuoteCard />
      </div>
      <div class="bento-card bento-card--zero">
        <OnThisDayCard />
      </div>
    </section>

    <!-- ============ S4：资讯流（v2.39.9 移除 AI 简报独占块，刷新反复报错）============ -->
    <div v-if="moduleVisible.feeds" class="wb-feedsbar">
      <WorkbenchFeedsBar :feeds="feeds" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MobileWorkbenchHome from '@/components/mobile/MobileWorkbenchHome.vue'
import TrendBars from '@/components/dashboard/TrendBars.vue'
import WeatherCard from '@/components/workbench/WeatherCard.vue'
import DailyQuoteCard from '@/components/workbench/DailyQuoteCard.vue'
import OnThisDayCard from '@/components/workbench/OnThisDayCard.vue'
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
  // F6 离线快照
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
  } catch {}

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
  } catch {}
  if (!loaded.value) loaded.value = true
})
</script>

<style scoped>
/* ============ Bento Grid 2.0 数据驾驶舱（v2.39.7） ============ */
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
.wb-hero { margin: 0 4px 18px; }
.wb-eyebrow { font-size: 11px; letter-spacing: .32em; color: var(--dp-accent); margin-bottom: 4px; }
.wb-title { font-size: 22px; font-weight: 700; margin: 0 0 2px; color: var(--dp-text); letter-spacing: .02em; }
.wb-subtitle { font-size: 12.5px; color: var(--dp-text3); margin: 0; }

/* ===== S1：不对称 Bento 核心数字区 ===== */
.bento-s1 {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(420px, 1.4fr);
  gap: 16px;
  margin-bottom: 16px;
}

/* 左列：Hero 净流入（占 2 行）+ 足迹/笔记 + 倒计时 */
.bento-s1-left {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto 1fr;
  gap: 16px;
  min-height: 460px;
}
/* Hero 净流入块：横跨 2 列、占 2 行高——视觉焦点 */
.bento-hero {
  grid-column: span 2;
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: 20px;
  padding: 22px 26px 20px;
  text-align: left;
  cursor: pointer;
  transition: border-color .2s, transform .15s;
  position: relative;
  overflow: hidden;
  box-shadow: var(--dp-shadow);
}
.bento-hero:hover { border-color: var(--dp-accent); transform: translateY(-1px); }
.bento-hero.up .bento-hero-sign { color: #34d399; }
.bento-hero.dn .bento-hero-sign { color: #f87171; }
.bento-hero-eyebrow {
  font-size: 11px; letter-spacing: .28em; text-transform: uppercase;
  color: var(--dp-text3); margin-bottom: 10px;
}
.bento-hero-num {
  display: flex; align-items: baseline; gap: 4px;
  font-variant-numeric: tabular-nums; font-weight: 700;
  margin-bottom: 14px;
}
.bento-hero-sign { font-size: 28px; opacity: 0.85; }
.bento-hero-val { font-size: 48px; line-height: 1.05; letter-spacing: -0.02em; }
.bento-hero-foot {
  display: flex; gap: 16px; font-size: 12.5px; color: var(--dp-text2);
}
.bento-hero-foot span { display: inline-flex; align-items: center; gap: 6px; }
.bento-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.bento-dot.dot-in { background: #34d399; }
.bento-dot.dot-out { background: #f87171; }

/* 小 KPI 块：足迹 / 笔记 */
.bento-mini {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: 16px;
  padding: 16px 18px 14px;
  text-align: left;
  cursor: pointer;
  transition: border-color .2s;
  box-shadow: var(--dp-shadow);
}
.bento-mini:hover { border-color: var(--dp-accent); }
.bento-mini-eyebrow { font-size: 11px; letter-spacing: .12em; color: var(--dp-text3); margin-bottom: 8px; }
.bento-mini-num {
  font-size: 28px; font-weight: 700; line-height: 1.05; color: var(--dp-text);
  font-variant-numeric: tabular-nums;
}
.bento-mini-unit { font-size: 13px; color: var(--dp-text3); font-weight: 400; margin-left: 4px; }
.bento-mini-foot { font-size: 11.5px; color: var(--dp-text3); margin-top: 6px; }

/* 倒计时：Bento 内嵌横排 */
.bento-cd {
  grid-column: span 2;
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: 16px;
  padding: 14px 18px 12px;
  box-shadow: var(--dp-shadow);
}
.bento-cd-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.bento-cd-title { font-size: 12px; font-weight: 600; color: var(--dp-text); letter-spacing: .04em; }
.bento-cd-link { font-size: 11.5px; color: var(--dp-accent); text-decoration: none; }
.bento-cd-link:hover { text-decoration: underline; }
.bento-cd-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.bento-cd-list li {
  display: flex; align-items: center; gap: 8px; padding: 4px 4px; border-radius: 4px;
  cursor: pointer; font-size: 12.5px; transition: background .15s;
}
.bento-cd-list li:hover { background: var(--dp-accent-faint, rgba(167,139,250,.08)); }
.cd-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.cd-title { flex: 1; color: var(--dp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cd-days { color: var(--dp-accent); font-weight: 600; font-variant-numeric: tabular-nums; }
.cd-empty { color: var(--dp-text3); font-size: 12px; padding: 4px 0; text-align: center; }

/* 右列：记账趋势（大块）+ 天气（小块堆叠） */
.bento-s1-right {
  display: grid;
  grid-template-rows: 2fr 1fr;
  gap: 16px;
  min-height: 460px;
}
.bento-trend {
  background: var(--dp-surface); border: 1px solid var(--dp-line); border-radius: 20px;
  padding: 18px 22px 14px; box-shadow: var(--dp-shadow);
  display: flex; flex-direction: column;
}
.bento-trend-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.bento-trend-title { font-size: 14px; font-weight: 600; color: var(--dp-text); letter-spacing: .02em; }
.bento-trend-meta { display: inline-flex; gap: 12px; font-size: 11.5px; color: var(--dp-text3); }
.trend-meta-item { display: inline-flex; align-items: center; gap: 5px; }
.trend-link { color: var(--dp-accent); font-size: 12px; text-decoration: none; }
.trend-link:hover { text-decoration: underline; }
.bento-trend :deep(.tb-bars) { flex: 1; }

/* 天气在 Bento 右列下方 */
.bento-wx {
  background: var(--dp-surface); border: 1px solid var(--dp-line); border-radius: 16px;
  padding: 10px 16px 8px; box-shadow: var(--dp-shadow);
}
.bento-wx :deep(.wx-card) { padding: 0; }
.bento-wx :deep(.wx-head) { margin-bottom: 4px; }
.bento-wx :deep(.wx-now) { margin-bottom: 4px; gap: 10px; }
.bento-wx :deep(.wx-temp) { font-size: 28px; }
.bento-wx :deep(.wx-icon) { font-size: 26px; }
.bento-wx :deep(.wx-meta) { font-size: 11px; margin-bottom: 4px; }
.bento-wx :deep(.wx-day) { padding: 6px 2px; }

/* ===== S2：两卡（自选股 + 今日待办）v2.39.8 移除笔记/标签重复入口 ===== */
.bento-s2 {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 16px;
  margin-bottom: 16px;
}

/* S3：文化小卡（每日一言 + 历史上的今天）—— 平衡 1fr 1.2fr，与 S2 错开节奏 */
.bento-s3 {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 16px;
  margin-bottom: 16px;
}
/* 让子卡片内的卡片自己撑满（去掉 bento-card 自带的 padding 冲突） */
.bento-card--zero { padding: 0; }
.bento-card--zero > :deep(*) { height: 100%; }
.bento-card {
  background: var(--dp-surface); border: 1px solid var(--dp-line); border-radius: 16px;
  padding: 16px 18px 14px; box-shadow: var(--dp-shadow);
  display: flex; flex-direction: column;
}
.bento-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.bento-card-title { font-size: 13px; font-weight: 600; color: var(--dp-text); letter-spacing: .02em; }
.bento-card-link { color: var(--dp-accent); font-size: 11.5px; text-decoration: none; }
.bento-card-link:hover { text-decoration: underline; }
.bento-card-list { list-style: none; margin: 0; padding: 0; flex: 1; display: flex; flex-direction: column; gap: 3px; }
.bento-card-list li {
  display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: 5px;
  cursor: pointer; font-size: 12.5px; transition: background .15s;
}
.bento-card-list li:hover { background: var(--dp-accent-faint, rgba(167,139,250,.08)); }
.st-name { flex: 1; color: var(--dp-text); }
.st-code { color: var(--dp-text3); font-size: 11px; margin-right: 4px; }
.st-meta { color: var(--dp-text3); font-size: 11px; font-variant-numeric: tabular-nums; }
.nt-dot, .ts-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--dp-text3); flex-shrink: 0; }
.nt-dot.on { background: var(--dp-accent); }
.ts-dot.pri-high { background: #f87171; }
.ts-dot.pri-medium { background: #fbbf24; }
.ts-dot.pri-low { background: #60a5fa; }
.nt-title, .ts-title { flex: 1; color: var(--dp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nt-meta, .ts-meta { color: var(--dp-text3); font-size: 11px; font-variant-numeric: tabular-nums; }
.nt-empty, .ts-empty { color: var(--dp-text3); font-size: 12px; padding: 8px 0; text-align: center; }
.ts-overdue { color: #f87171; font-size: 11px; padding: 4px 6px; }

.bento-tag-cloud { display: flex; flex-wrap: wrap; gap: 5px; }
.tag-chip {
  font-size: 11px; padding: 3px 9px; border-radius: 12px;
  background: var(--dp-accent-faint, rgba(167,139,250,.14)); color: var(--dp-accent);
  text-decoration: none; transition: background .15s;
}
.tag-chip:hover { background: var(--dp-accent); color: var(--dp-bg, #000); }
.tag-empty { color: var(--dp-text3); font-size: 12px; padding: 6px 0; }

/* ===== S4：资讯流（v2.39.9 移除 AI 简报块）===== */
.wb-feedsbar {}

/* ===== 自适应 ===== */
@media (max-width: 1280px) {
  .bento-s1 { grid-template-columns: 1fr 1.2fr; }
}
@media (max-width: 1024px) {
  .bento-s1 { grid-template-columns: 1fr; }
  .bento-s1-left, .bento-s1-right { min-height: 0; }
  .bento-s2 { grid-template-columns: 1fr 1fr; }
  .bento-s3 { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 600px) {
  .bento-s2 { grid-template-columns: 1fr; }
  .bento-s3 { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .workbench-page { padding: 80px 14px 40px; }
  .bento-s1-left { grid-template-columns: 1fr; }
  .bento-hero { grid-column: span 1; padding: 18px 20px; }
  .bento-hero-num { font-size: 36px; }
  .bento-cd { grid-column: span 1; }
  .bento-s2 { grid-template-columns: 1fr; }
  .bento-s3 { grid-template-columns: 1fr; }
}
</style>

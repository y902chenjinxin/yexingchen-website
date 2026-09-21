<template>
  <!-- 移动端：独立沉浸式工作台首页 -->
  <MobileWorkbenchHome v-if="isMobile" />

  <div v-else class="workbench-page">
    <!-- S1 高级感视觉锚点：背景细网格 + 浮动光斑（不影响阅读，纯装饰） -->
    <div class="wb-bg" aria-hidden="true">
      <div class="wb-bg-grid"></div>
      <div class="wb-bg-blob wb-bg-blob-1"></div>
      <div class="wb-bg-blob wb-bg-blob-2"></div>
      <div class="wb-bg-blob wb-bg-blob-3"></div>
      <svg class="wb-bg-dots" viewBox="0 0 800 400" preserveAspectRatio="xMidYMid slice">
        <g fill="currentColor">
          <circle cx="120" cy="80" r="1.2" />
          <circle cx="320" cy="40" r="1" />
          <circle cx="540" cy="120" r="1.4" />
          <circle cx="720" cy="60" r="1" />
          <circle cx="80" cy="260" r="1.2" />
          <circle cx="420" cy="320" r="1.4" />
          <circle cx="640" cy="240" r="1" />
          <circle cx="200" cy="360" r="1.2" />
        </g>
      </svg>
    </div>

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

      <!-- 足迹简报 -->
      <div class="trend-card">
        <div class="trend-head">
          <div class="trend-title">足迹 · 最近</div>
          <RouterLink class="trend-link" to="/travels">详情 →</RouterLink>
        </div>
        <ul class="cd-list">
          <li v-for="t in kpi.travel.recent" :key="t.id" @click="$router.push(`/travels`)">
            <span class="cd-dot" style="background: var(--dp-accent)"></span>
            <span class="cd-title">{{ t.title || `旅程 ${t.id}` }}</span>
            <span class="cd-days">{{ t.city_count }} 城</span>
          </li>
          <li v-if="!kpi.travel.recent.length" class="cd-empty">还没有旅程记录</li>
        </ul>
      </div>
    </section>

    <!-- F4 AI 简报卡：单卡横幅，占满首行宽 -->
    <section v-if="moduleVisible.brief" class="wb-brief">
      <AiBriefCard :summary="summary" />
    </section>

    <!-- 习惯打卡横幅卡 -->
    <section v-if="moduleVisible.habits" class="wb-habits">
      <HabitsCard />
    </section>

    <!-- 笔记 + 自选股 + 任务 三栏 -->
    <section class="wb-row">
      <div class="row-card">
        <div class="trend-head">
          <div class="trend-title">最近笔记</div>
          <RouterLink class="trend-link" to="/notes">全部 →</RouterLink>
        </div>
        <ul class="note-list">
          <li v-for="n in kpi.recent_notes" :key="n.id" @click="$router.push(`/notes/${n.id}`)">
            <span class="note-title">{{ n.title || '（无标题）' }}</span>
            <span class="note-meta">{{ formatDate(n.updated_at) }}</span>
          </li>
          <li v-if="!kpi.recent_notes.length" class="cd-empty">还没有笔记</li>
        </ul>
      </div>

      <div class="row-card">
        <div class="trend-head">
          <div class="trend-title">自选股</div>
          <RouterLink class="trend-link" to="/stocks">详情 →</RouterLink>
        </div>
        <ul class="note-list">
          <li v-for="h in kpi.stocks.holdings.slice(0, 5)" :key="h.code" @click="$router.push('/stocks')">
            <span class="note-title">{{ h.name }}</span>
            <span class="note-meta">{{ h.shares }} 股 @ ¥{{ h.cost }}</span>
          </li>
          <li v-if="!kpi.stocks.holdings.length" class="cd-empty">暂无自选股</li>
        </ul>
      </div>

      <div class="row-card">
        <div class="trend-head">
          <div class="trend-title">今日任务</div>
          <RouterLink class="trend-link" to="/tasks">详情 →</RouterLink>
        </div>
        <ul class="note-list">
          <li v-for="t in kpi.today_tasks" :key="t.id" @click="$router.push('/tasks')">
            <span class="note-title">{{ t.title }}</span>
            <span class="note-meta">{{ t.due_date?.slice(5) || '今日' }}</span>
          </li>
          <li v-if="kpi.overdue_tasks.length" class="note-overdue">
            <i class="overdue-dot"></i>{{ kpi.overdue_tasks.length }} 项已逾期
          </li>
          <li v-if="!kpi.today_tasks.length && !kpi.overdue_tasks.length" class="cd-empty">今日无任务</li>
        </ul>
      </div>
    </section>

    <!-- 资讯流（保留原 workbench 信息流） -->
    <div v-if="moduleVisible.feeds" class="wb-body wb-feedsbar">
      <WorkbenchFeedsBar :feeds="feeds" />
    </div>

    <!-- 底部网安/备案标识 -->
    <SiteFooter variant="dark" class="wb-footer" />
  </div>
</template>

<script setup>
defineOptions({ name: 'WorkbenchView' })
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import MobileWorkbenchHome from '@/components/mobile/MobileWorkbenchHome.vue'
import { useIsMobile } from '@/composables/useIsMobile'
import SiteFooter from '@/components/SiteFooter.vue'
import WorkbenchFeedsBar from '@/components/workbench/WorkbenchFeedsBar.vue'
import KpiTile from '@/components/dashboard/KpiTile.vue'
import TrendBars from '@/components/dashboard/TrendBars.vue'
import Skeleton from '@/components/Skeleton.vue'
import AiBriefCard from '@/components/workbench/AiBriefCard.vue'
import WeatherCard from '@/components/workbench/WeatherCard.vue'
import HabitsCard from '@/components/workbench/HabitsCard.vue'
import { usePrefsStore } from '@/stores/prefs'
import { workbenchApi } from '@/api/workbench'
import { feedsApi } from '@/api/feeds'

const { isMobile } = useIsMobile()

// 工作台模块显隐（个人中心可开关）
const prefs = usePrefsStore()
const moduleVisible = computed(() => prefs.moduleVisible)

const loaded = ref(false)
const summary = ref({})
const feeds = ref([])

const kpi = computed(() => {
  const d = summary.value || {}
  const cd = d.countdown || {}
  const tv = d.travel || {}
  const fn = d.finance || {}
  const st = d.stocks || { holdings: [] }
  return {
    countdown: {
      active_count: cd.active_count ?? 0,
      upcoming_count: cd.upcoming_count ?? 0,
      upcoming_top: cd.upcoming_top || [],
    },
    travel: {
      travel_count: tv.travel_count ?? 0,
      province_count: tv.province_count ?? 0,
      city_count: tv.city_count ?? 0,
      recent: tv.recent || [],
    },
    finance: {
      month_count: fn.month_count ?? 0,
      month_income: fn.month_income ?? 0,
      month_expense: fn.month_expense ?? 0,
      net: fn.net ?? 0,
      trend: fn.trend || [],
    },
    stocks: { symbol_count: st.symbol_count ?? 0, holdings: st.holdings || [] },
    note_count: (d.recent_notes || []).length,
    recent_notes: d.recent_notes || [],
    today_tasks: d.today_tasks || [],
    overdue_tasks: d.overdue_tasks || [],
  }
})

function formatDate(s) {
  if (!s) return ''
  try {
    const dt = new Date(s)
    const m = (dt.getMonth() + 1).toString().padStart(2, '0')
    const d = dt.getDate().toString().padStart(2, '0')
    return `${m}-${d}`
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
    const r = await workbenchApi.summary()
    summary.value = r?.data || {}
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

/* S1 视觉锚点：背景细网格 + 三个柔和光斑 + 散布圆点 */
.wb-bg {
  position: absolute;
  inset: 0 0 auto 0;
  height: 540px;
  pointer-events: none;
  z-index: 0;
}
.wb-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, rgba(126, 136, 243, 0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(126, 136, 243, 0.05) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(ellipse 70% 60% at 50% 30%, #000 30%, transparent 90%);
  -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 30%, #000 30%, transparent 90%);
}
.wb-bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(64px);
  opacity: 0.55;
  mix-blend-mode: screen;
}
.wb-bg-blob-1 { top: -120px; left: 8%; width: 360px; height: 360px; background: radial-gradient(circle, rgba(103, 232, 249, 0.55), transparent 70%); animation: wb-float-1 18s ease-in-out infinite; }
.wb-bg-blob-2 { top: -40px; right: 12%; width: 280px; height: 280px; background: radial-gradient(circle, rgba(245, 182, 96, 0.45), transparent 70%); animation: wb-float-2 22s ease-in-out infinite; }
.wb-bg-blob-3 { top: 200px; left: 40%; width: 220px; height: 220px; background: radial-gradient(circle, rgba(126, 136, 243, 0.35), transparent 70%); animation: wb-float-3 26s ease-in-out infinite; }

.wb-bg-dots {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  color: rgba(126, 136, 243, 0.6);
  animation: wb-fade-dots 8s ease-in-out infinite alternate;
}

@keyframes wb-float-1 { 0%,100% { transform: translate(0,0); } 50% { transform: translate(40px, 30px); } }
@keyframes wb-float-2 { 0%,100% { transform: translate(0,0); } 50% { transform: translate(-30px, 40px); } }
@keyframes wb-float-3 { 0%,100% { transform: translate(0,0); } 50% { transform: translate(20px, -25px); } }
@keyframes wb-fade-dots { from { opacity: 0.5; } to { opacity: 0.85; } }

@media (prefers-reduced-motion: reduce) {
  .wb-bg-blob, .wb-bg-dots { animation: none; }
}
:root[data-theme="day"] .wb-bg-grid {
  background-image:
    linear-gradient(to right, rgba(70, 100, 160, 0.07) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(70, 100, 160, 0.07) 1px, transparent 1px);
}
:root[data-theme="day"] .wb-bg-blob { opacity: 0.35; mix-blend-mode: multiply; }
:root[data-theme="day"] .wb-bg-dots { color: rgba(70, 100, 160, 0.5); }

/* hero 区背景层压在 hero 之下，但 z-index 高于 .wb-bg；用 absolute 失效让内容自然排 */
.wb-hero { position: relative; z-index: 1; }

/* ===== 顶部品牌条 ===== */
.wb-hero {
  text-align: center;
  padding: 8px 0 24px;
  max-width: 1248px;
  margin: 0 auto;
}
.wb-eyebrow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  font-size: 11px;
  letter-spacing: .5em;
  color: var(--dp-text3);
  margin-bottom: 10px;
}
.wb-eyebrow::before,
.wb-eyebrow::after { content: ""; height: 1px; width: 52px; background: var(--dp-line-strong); }
.wb-title { font-size: 28px; font-weight: 700; letter-spacing: -.01em; margin: 0; color: var(--dp-text); }
.wb-subtitle { margin: 8px 0 0; font-size: 13px; color: var(--dp-text2); letter-spacing: .04em; }

/* ===== KPI 行 ===== */
.wb-kpi {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  max-width: 1248px;
  margin: 0 auto;
  padding: 0 24px;
}
/* S6 中屏断点：1100-900 三列渐变收，避免 KPI 4 卡挤 */
@media (max-width: 1280px) {
  .wb-kpi { grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 0 20px; }
}
@media (max-width: 1100px) {
  .wb-kpi { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 720px) {
  .wb-kpi { grid-template-columns: 1fr; padding: 0 16px; }
}

/* 骨架占位 KPI：复用 KpiTile 视觉 */
.kpi-skel {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 14px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 92px;
  box-shadow: var(--dp-shadow);
}

/* ===== 趋势 3 列 ===== */
.wb-trend {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 14px;
  max-width: 1248px;
  margin: 20px auto 0;
  padding: 0 24px;
}
@media (max-width: 1280px) {
  .wb-trend { grid-template-columns: 1.6fr 1fr 1fr; padding: 0 20px; }
}
@media (max-width: 1100px) {
  .wb-trend { grid-template-columns: 1fr; }
}

/* ===== 天气小部件（顶置横幅卡） ===== */
.wb-wx,
.wb-habits {
  max-width: 1248px;
  margin: 16px auto 0;
  padding: 0 24px;
}
.wb-wx {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  box-shadow: var(--dp-shadow);
}
.wb-wx :deep(.wx-card) { padding: 14px 18px 12px; }
@media (max-width: 1280px) { .wb-wx, .wb-habits { padding-left: 20px; padding-right: 20px; } }
@media (max-width: 720px)  { .wb-wx, .wb-habits { padding-left: 16px; padding-right: 16px; } }

/* ===== AI 简报横幅 ===== */
.wb-brief {
  max-width: 1248px;
  margin: 18px auto 0;
  padding: 0 24px;
}
@media (max-width: 1280px) { .wb-brief { padding: 0 20px; } }
@media (max-width: 720px)  { .wb-brief { padding: 0 16px; } }

/* ===== 笔记 + 自选 + 任务 3 列 ===== */
.wb-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  max-width: 1248px;
  margin: 14px auto 0;
  padding: 0 24px;
}
@media (max-width: 1280px) {
  .wb-row { gap: 12px; padding: 0 20px; }
}
@media (max-width: 1100px) {
  .wb-row { grid-template-columns: 1fr; }
}

.trend-card,
.row-card {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 14px 16px 12px;
  box-shadow: var(--dp-shadow);
}
.trend-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.trend-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--dp-text2);
  letter-spacing: .04em;
  text-transform: uppercase;
}
.trend-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--dp-text3);
  align-items: center;
}
.trend-meta-item { display: inline-flex; align-items: center; gap: 4px; }
.trend-dot { width: 8px; height: 8px; border-radius: 50%; }
.dot-in { background: #16a34a; }
.dot-out { background: var(--dp-accent-strong); }
:root[data-theme="night"] .dot-in { background: #34d399; }
.trend-link {
  font-size: 11px;
  color: var(--dp-text3);
  text-decoration: none;
  cursor: pointer;
  transition: color .15s;
}
.trend-link:hover { color: var(--dp-accent); }

/* ===== 列表 ===== */
.cd-list,
.note-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cd-list li,
.note-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 6px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--dp-text);
  transition: background .15s;
}
.cd-list li:hover,
.note-list li:hover { background: var(--dp-surface2); }
.cd-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.cd-title,
.note-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cd-days,
.note-meta {
  font-size: 11px;
  color: var(--dp-text3);
  font-variant-numeric: tabular-nums;
}
.cd-empty {
  padding: 14px 6px;
  color: var(--dp-text3);
  font-size: 12px;
  text-align: center;
}
.note-overdue {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 6px;
  font-size: 12px;
  color: #dc2626;
}
:root[data-theme="night"] .note-overdue { color: #fb7185; }
.overdue-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

/* ===== 资讯 + 页脚 ===== */
.wb-body { max-width: 1248px; margin: 18px auto 0; padding: 0 24px; }
.wb-feedsbar { animation: fade-in .6s ease .15s both; }
.wb-footer {
  max-width: 1248px;
  margin: 24px auto 0;
  padding: 12px 24px 60px;
  border-top: 1px solid var(--dp-line);
  position: relative;
  z-index: 1;
}
@keyframes fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>
<template>
  <!-- 移动端：独立沉浸式工作台首页 -->
  <MobileWorkbenchHome v-if="isMobile" />

  <!-- 桌面端：Bento Grid 数据驾驶舱 -->
  <div v-else class="workbench-page">
    <header class="wb-hero">
      <div class="wb-eyebrow">玄 黄 · 工 作 台</div>
      <h1 class="wb-title">把零散念头，沉淀为数据。</h1>
      <p class="wb-subtitle">今日 · 本月 · 累计，一目了然。</p>
    </header>

    <!-- ============ Bento S1：核心数字 + 记账趋势（不对称大块） ============ -->
    <section class="bento-s1">
      <!-- 左列：净流入（大块）+ 足迹 + 自选股
           v2.38 精简：笔记 / 即将到来 / 今日待办 / 资讯流移出工作台，
           待办与即将到来的事件统一收进顶栏「提醒中心」 -->
      <div class="bento-s1-left">
        <!-- Hero KPI：净流入 -->
        <button
          v-mouse-light
          class="bento-hero"
          :class="kpi.finance.net >= 0 ? 'up' : 'dn'"
          @click="$router.push('/finance/book')"
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

        <!-- 足迹 -->
        <button v-mouse-light class="bento-mini" @click="$router.push('/travels')">
          <div class="bento-mini-eyebrow">足迹</div>
          <div class="bento-mini-num">{{ kpi.travel.province_count }}<span class="bento-mini-unit">/ 34 省</span></div>
          <div class="bento-mini-foot">{{ kpi.travel.travel_count }} 段旅程 · {{ kpi.travel.city_count }} 城</div>
        </button>

        <!-- 自选股 -->
        <div v-mouse-light class="bento-card bento-stocks">
          <div class="bento-card-head">
            <div class="bento-card-title">自选股</div>
            <RouterLink class="bento-card-link" to="/finance/market">管理 →</RouterLink>
          </div>
          <ul class="bento-card-list stock-list">
            <li v-for="h in kpi.stocks.holdings" :key="h.code">
              <span class="st-name">{{ h.name }}</span>
              <span class="st-code">{{ h.code }}</span>
              <span class="st-meta">{{ h.shares }} · ¥{{ h.cost }}</span>
            </li>
            <li v-if="!kpi.stocks.holdings.length" class="bento-empty">尚未添加</li>
          </ul>
        </div>
      </div>

      <!-- 右列：记账 30 天（大块）+ 天气（小块） -->
      <div class="bento-s1-right">
        <div v-mouse-light class="bento-trend">
          <div class="bento-trend-head">
            <div class="bento-trend-title">记账 · 最近 30 天</div>
            <div class="bento-trend-meta">
              <span class="trend-meta-item"><i class="bento-dot dot-in"></i>收入</span>
              <span class="trend-meta-item"><i class="bento-dot dot-out"></i>支出</span>
              <RouterLink class="trend-link" to="/finance/book">详情 →</RouterLink>
            </div>
          </div>
          <TrendBars :data="kpi.finance.trend" :height="200" mode="expense" unit="¥" />
        </div>
        <!-- 天气（v2.39.7 新增 Bento 内嵌） -->
        <div v-if="moduleVisible.weather" v-mouse-light class="bento-wx">
          <WeatherCard />
        </div>
      </div>
    </section>

    <!-- ============ Bento S3：每日一言 + 历史上的今天（文化小卡） ============ -->
    <section class="bento-s3">
      <div v-mouse-light class="bento-card bento-card--zero">
        <DailyQuoteCard />
      </div>
      <div v-mouse-light class="bento-card bento-card--zero">
        <OnThisDayCard />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import MobileWorkbenchHome from '@/components/mobile/MobileWorkbenchHome.vue'
import TrendBars from '@/components/dashboard/TrendBars.vue'
import WeatherCard from '@/components/workbench/WeatherCard.vue'
import DailyQuoteCard from '@/components/workbench/DailyQuoteCard.vue'
import OnThisDayCard from '@/components/workbench/OnThisDayCard.vue'
import { useWorkbenchStore } from '@/stores/workbench'
import { usePrefsStore } from '@/stores/prefs'
import { useIsMobile } from '@/composables/useIsMobile'

const { isMobile } = useIsMobile()
const wbStore = useWorkbenchStore()
const prefs = usePrefsStore()
const moduleVisible = computed(() => prefs.moduleVisible)

const kpi = ref({
  travel: { travel_count: 0, province_count: 0, city_count: 0 },
  finance: { net: 0, month_income: 0, month_expense: 0, trend: [] },
  stocks: { holdings: [] },
})

// 只挑工作台用得到的三个区块，其余（笔记 / 待办 / 倒计时）已交给顶栏提醒中心
function applySummary(s) {
  kpi.value = {
    travel: s.travel || kpi.value.travel,
    finance: s.finance || kpi.value.finance,
    stocks: s.stocks || kpi.value.stocks,
  }
}

onMounted(async () => {
  // F6 离线快照：10 分钟内的旧数据先渲染，再被网络结果覆盖
  try {
    const cached = localStorage.getItem('yx_wb_summary')
    if (cached) {
      const { ts, data } = JSON.parse(cached)
      if (ts && Date.now() - ts < 10 * 60 * 1000 && data) applySummary(data)
    }
  } catch { /* 缓存损坏忽略 */ }

  try {
    const s = (await wbStore.loadSummary()) || {}
    applySummary(s)
    try { localStorage.setItem('yx_wb_summary', JSON.stringify({ ts: Date.now(), data: s })) } catch { /* 配额满忽略 */ }
  } catch { /* 未登录 / 网络失败则保留缓存或占位 */ }
})
</script>

<style scoped>
/* ============ Bento Grid 2.0 数据驾驶舱（v2.38 精简版） ============ */
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
  grid-template-columns: minmax(340px, 1fr) minmax(420px, 1.35fr);
  gap: 16px;
  margin-bottom: 16px;
}

/* 左列：Hero 净流入 + 足迹 + 自选股，纵向三段 */
.bento-s1-left {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: auto auto 1fr;
  gap: 16px;
  min-height: 520px;
}
/* Hero 净流入块：视觉焦点 */
.bento-hero {
  background: var(--color-bg-glass, var(--dp-surface));
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
.bento-hero:hover {
  border-color: var(--yq-gold, var(--dp-accent));
  box-shadow: 0 22px 56px rgba(0,0,0,.32), 0 0 0 1px var(--yq-gold-glow, rgba(199,169,107,.35)) inset;
}
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
.bento-hero-val { font-size: 44px; line-height: 1.05; letter-spacing: -0.02em; }
.bento-hero-foot {
  display: flex; gap: 16px; font-size: 12.5px; color: var(--dp-text2);
}
.bento-hero-foot span { display: inline-flex; align-items: center; gap: 6px; }
.bento-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.bento-dot.dot-in { background: #34d399; }
.bento-dot.dot-out { background: #f87171; }

/* 小 KPI 块：足迹 */
.bento-mini {
  background: var(--color-bg-glass, var(--dp-surface));
  border: 1px solid var(--dp-line);
  border-radius: 16px;
  padding: 16px 18px 14px;
  text-align: left;
  cursor: pointer;
  transition: border-color .2s, box-shadow .2s;
  box-shadow: var(--dp-shadow);
}
.bento-mini:hover {
  border-color: var(--yq-gold, var(--dp-accent));
  box-shadow: 0 14px 36px rgba(0,0,0,.28), 0 0 0 1px var(--yq-gold-glow, rgba(199,169,107,.3)) inset;
}
.bento-mini-eyebrow { font-size: 11px; letter-spacing: .12em; color: var(--dp-text3); margin-bottom: 8px; }
.bento-mini-num {
  font-size: 28px; font-weight: 700; line-height: 1.05; color: var(--dp-text);
  font-variant-numeric: tabular-nums;
}
.bento-mini-unit { font-size: 13px; color: var(--dp-text3); font-weight: 400; margin-left: 4px; }
.bento-mini-foot { font-size: 11.5px; color: var(--dp-text3); margin-top: 6px; }

/* 自选股：左列第三段，列表超出时自身滚动 */
.bento-stocks { min-height: 0; }
.stock-list { overflow-y: auto; scrollbar-width: thin; }
.bento-empty { color: var(--dp-text3); font-size: 12px; padding: 8px 0; text-align: center; }

/* 右列：记账趋势（大块）+ 天气（小块堆叠） */
.bento-s1-right {
  display: grid;
  grid-template-rows: 2fr 1fr;
  gap: 16px;
  min-height: 520px;
}
.bento-trend {
  background: var(--color-bg-glass, var(--dp-surface)); border: 1px solid var(--dp-line); border-radius: 20px;
  padding: 18px 22px 14px; box-shadow: var(--dp-shadow);
  display: flex; flex-direction: column;
  transition: border-color .2s, box-shadow .2s;
}
.bento-trend:hover {
  border-color: var(--yq-gold, var(--dp-accent));
  box-shadow: 0 22px 56px rgba(0,0,0,.32), 0 0 0 1px var(--yq-gold-glow, rgba(199,169,107,.35)) inset;
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
  background: var(--color-bg-glass, var(--dp-surface)); border: 1px solid var(--dp-line); border-radius: 16px;
  padding: 10px 16px 8px; box-shadow: var(--dp-shadow);
  transition: border-color .2s, box-shadow .2s;
}
.bento-wx:hover {
  border-color: var(--yq-gold, var(--dp-accent));
  box-shadow: 0 14px 36px rgba(0,0,0,.28), 0 0 0 1px var(--yq-gold-glow, rgba(199,169,107,.3)) inset;
}
.bento-wx :deep(.wx-card) { padding: 0; }
.bento-wx :deep(.wx-head) { margin-bottom: 4px; }
.bento-wx :deep(.wx-now) { margin-bottom: 4px; gap: 10px; }
.bento-wx :deep(.wx-temp) { font-size: 28px; }
.bento-wx :deep(.wx-icon) { font-size: 26px; }
.bento-wx :deep(.wx-meta) { font-size: 11px; margin-bottom: 4px; }
.bento-wx :deep(.wx-day) { padding: 6px 2px; }

/* ===== S3：文化小卡（每日一言 + 历史上的今天） ===== */
.bento-s3 {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 16px;
}
/* 让子卡片内的卡片自己撑满（去掉 bento-card 自带的 padding 冲突） */
.bento-card--zero { padding: 0; }
.bento-card--zero > :deep(*) { height: 100%; }
.bento-card {
  background: var(--color-bg-glass, var(--dp-surface)); border: 1px solid var(--dp-line); border-radius: 16px;
  padding: 16px 18px 14px; box-shadow: var(--dp-shadow);
  display: flex; flex-direction: column;
  transition: border-color .2s, box-shadow .2s;
}
.bento-card:hover {
  border-color: var(--yq-gold, var(--dp-accent));
  box-shadow: 0 14px 36px rgba(0,0,0,.28), 0 0 0 1px var(--yq-gold-glow, rgba(199,169,107,.3)) inset;
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

/* ===== 自适应 ===== */
@media (max-width: 1280px) {
  .bento-s1 { grid-template-columns: 1fr 1.2fr; }
}
@media (max-width: 1024px) {
  .bento-s1 { grid-template-columns: 1fr; }
  .bento-s1-left, .bento-s1-right { min-height: 0; }
  .bento-s3 { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 768px) {
  .workbench-page { padding: 80px 14px 40px; }
  .bento-hero { padding: 18px 20px; }
  .bento-hero-val { font-size: 34px; }
  .bento-s3 { grid-template-columns: 1fr; }
}
</style>

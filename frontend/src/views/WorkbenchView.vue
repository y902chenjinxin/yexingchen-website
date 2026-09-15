<template>
  <div class="workbench-page">
    <!-- 浅底留白背景：宣纸纹理 + 极淡云雾 + 淡墨山峦卷轴收束 -->
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
      <div class="lj-wash w3"></div>
      <!-- 江南山峦剪影（纯代码 SVG，克制的低透明卷轴收束层） -->
      <svg class="lj-mountain lj-mountain--l" viewBox="0 0 640 200" preserveAspectRatio="xMidYMax slice">
        <path d="M0 200 L0 120 L72 62 L138 118 L208 40 L286 120 L348 84 L428 148 L520 76 L640 150 L640 200 Z"
              fill="currentColor" opacity=".5"/>
      </svg>
      <svg class="lj-mountain lj-mountain--r" viewBox="0 0 560 180" preserveAspectRatio="xMidYMax slice">
        <path d="M0 180 L0 120 L96 70 L170 124 L244 62 L330 132 L404 96 L470 150 L560 96 L560 180 Z"
              fill="currentColor" opacity=".42"/>
      </svg>
    </div>

    <!-- 玉简轮播作为主角（岛屿导航核心） -->
    <section class="wb-hero">
      <div class="wb-eyebrow"><span>玄 黄 · 仙 府 一 隅</span></div>
      <h1 class="wb-title">玄黄 · 工作台
        <svg class="wb-seal" viewBox="0 0 32 32" aria-hidden="true">
          <rect x="2.5" y="2.5" width="27" height="27" rx="5" fill="none" stroke="currentColor" stroke-width="1.6"/>
          <rect x="7" y="7" width="18" height="7" rx="2.5" fill="currentColor" opacity=".9"/>
          <path d="M7 17 q4 -3 8 0 q4 -3 8 0 v8 h-16 Z" fill="currentColor" opacity=".9"/>
        </svg>
      </h1>
      <p class="wb-subtitle">把零散念头，沉淀为笔记、AI 与可执之事。</p>
      <JadeCarousel class="wb-jade" />
    </section>

    <!-- 资讯横栏：玉简下 / 常用工具上，自动向上滚动，点击进入资讯页 -->
    <div class="wb-body wb-feedsbar">
      <WorkbenchFeedsBar :feeds="feeds" />
    </div>

    <!-- 常用工具区（工具 + 快捷动作混排） -->
    <div class="wb-body">
      <WorkbenchTools />
    </div>

    <!-- 大数据看板（账本 / 行情 / 足迹 三卡预览） -->
    <div class="wb-body wb-dash">
      <WorkbenchDashboard :empty="empty" :finance="finance" :stocks="stocks" :holdings="holdings" :travels="travels" />
    </div>

    <!-- 底部网安/备案标识（夜色页脚） -->
    <SiteFooter variant="dark" class="wb-footer" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import JadeCarousel from '@/components/JadeCarousel.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import WorkbenchTools from '@/components/workbench/WorkbenchTools.vue'
import WorkbenchDashboard from '@/components/workbench/WorkbenchDashboard.vue'
import WorkbenchFeedsBar from '@/components/workbench/WorkbenchFeedsBar.vue'
import { financeApi } from '@/api/finance'
import { feedsApi } from '@/api/feeds'
import { stocksApi } from '@/api/stocks'
import { listTravels } from '@/api/travels'

const empty = ref(true)
const finance = ref({})
const feeds = ref([])
const stocks = ref({})
const holdings = ref([])
const travels = ref({})

onMounted(async () => {
  try {
    const res = await financeApi.summary()
    if (res?.data?.total_count) {
      empty.value = false
      finance.value = res.data
    }
  } catch (e) {
    /* 未就绪保持空态 */
  }
  try {
    const res = await feedsApi.dashboard()
    if (res?.data) {
      feeds.value = res.data.recent || []
    }
  } catch (e) {
    /* 资讯未就绪忽略 */
  }
  try {
    const res = await stocksApi.dashboard()
    if (res?.data) {
      if (res.data.symbol_count) empty.value = false
      stocks.value = { marketValue: res.data.market_value, profit: res.data.today_pnl }
      holdings.value = res.data.holdings || []
    }
  } catch (e) {
    /* 行情未就绪忽略 */
  }
  try {
    const res = await listTravels()
    if (res?.data?.total) {
      travels.value = { travel_count: res.data.total, province_count: 0, city_count: 0 }
      const prov = new Set(); const cty = new Set()
      for (const it of res.data.list) {
        ;(it.cities || []).forEach((c) => { if (c.province) prov.add(c.province); if (c.city) cty.add(c.city) })
      }
      travels.value = { travel_count: res.data.total, province_count: prov.size, city_count: cty.size }
    }
  } catch (e) {
    /* 足迹未就绪忽略 */
  }
})
</script>

<style scoped>
.workbench-page {
  position: relative;
  font-family: var(--font-serif);
  /* 全宽浅底：收窄视口(桌面放大)或宽屏时，浅色宣纸底铺满视口，避免两侧露出深色产生黑边 */
  width: 100%;
  padding: 96px 0 0;
  box-sizing: border-box;
  color: var(--lj-text);
  min-height: 100vh;
  overflow-x: hidden;
}
/* 内容块与页脚统一在 1200px 内居中，横向留白 24px 与旧版一致 */
.wb-hero,
.wb-body,
.wb-footer {
  width: 100%;
  max-width: 1248px;
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
  padding: 0 24px;
}
.wb-footer {
  position: relative;
  z-index: 1;
  margin-top: 28px;
  padding-bottom: 84px;
}

/* ===== 夜色玻璃底（向晚·雨青） ===== */
.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 60% 40% at 20% 8%, var(--glow-rain), transparent 60%),
    radial-gradient(ellipse 50% 40% at 85% 30%, var(--glow-gold), transparent 60%),
    var(--lj-bg);
}
.lj-paper-texture {
  position: absolute; inset: 0; opacity: 0.55;
  background:
    repeating-linear-gradient(0deg, rgba(127, 168, 163, 0.02) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(127, 168, 163, 0.014) 0 1px, transparent 1px 7px);
}
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4;
  background: radial-gradient(circle, rgba(127, 168, 163, 0.14), transparent 70%); animation: lj-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 480px; height: 420px; top: 12%; left: -6%; }
.lj-wash.w2 { width: 420px; height: 360px; bottom: 6%; right: -5%; animation-delay: 8s; }
.lj-wash.w3 { width: 520px; height: 300px; top: 48%; left: 38%; opacity: 0.24; animation-delay: 16s; }
@keyframes lj-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(36px,-20px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

/* 淡墨山峦剪影：页底卷轴收束层（纯代码、低透明，昼夜自适应） */
.lj-mountain { position: absolute; bottom: -1px; color: var(--lj-ink); pointer-events: none; z-index: 0; height: 200px; }
.lj-mountain--l { left: -2vw; width: 46vw; max-width: 600px; opacity: .055; }
.lj-mountain--r { right: -2vw; width: 40vw; max-width: 540px; height: 170px; opacity: .045; }

.workbench-page > *:not(.lj-bg) { position: relative; z-index: 1; }

/* ===== 主角区：玉简 ===== */
.wb-hero { text-align: center; padding: 6px 0 8px; animation: lj-rise .8s cubic-bezier(.4,0,.2,1) both; }
.wb-eyebrow { display: flex; align-items: center; justify-content: center; gap: 16px; font-size: 11px; letter-spacing: .5em; color: var(--lj-mist); margin-bottom: 12px; }
.wb-eyebrow::before,
.wb-eyebrow::after { content: ""; height: 1px; width: 52px; }
.wb-eyebrow::before { background: linear-gradient(90deg, transparent, var(--lj-line-strong)); }
.wb-eyebrow::after { background: linear-gradient(90deg, var(--lj-line-strong), transparent); }
.wb-eyebrow span { letter-spacing: .5em; margin-right: -.5em; }
.wb-title { display: inline-flex; align-items: center; gap: 12px; font-size: 34px; font-weight: 600; letter-spacing: .1em; margin: 0; color: var(--lj-text); }
.wb-seal { width: 21px; height: 21px; margin-top: 3px; color: var(--lj-seal); opacity: .88; filter: drop-shadow(0 0 4px rgba(181,90,72,.25)); }
.wb-subtitle { margin: 10px 0 0; font-size: 13px; color: var(--lj-text-2); letter-spacing: .18em; }
.wb-jade { margin-top: 8px; }
@keyframes lj-rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }

/* ===== 数据区 ===== */
.wb-body { padding-top: 10px; }
.wb-body + .wb-body { margin-top: 20px; }
/* 楼层式载入：资讯bar → 工具/数据 → 页脚 依次浮现 */
.wb-feedsbar { animation: lj-rise .8s cubic-bezier(.4,0,.2,1) both; animation-delay: .15s; }
.wb-body:not(.wb-feedsbar) { animation: lj-rise .8s cubic-bezier(.4,0,.2,1) both; animation-delay: .3s; }
.wb-footer { animation: lj-rise .8s cubic-bezier(.4,0,.2,1) both; animation-delay: .45s;
  border-top: 1px solid var(--lj-line); padding-top: 22px; }

@media (prefers-reduced-motion: reduce) {
  .workbench-page *, .workbench-page *::before, .workbench-page *::after { animation: none !important; transition: none !important; }
}
@media (max-width: 600px) {
  .wb-title { font-size: 26px; }
  .wb-actions { grid-template-columns: 1fr; }
  .workbench-page { padding: 88px 0 8px; }
  .wb-hero,
  .wb-body,
  .wb-footer { padding: 0 16px; }
  .wb-footer { margin-top: 20px; padding-bottom: 80px; }
}
</style>
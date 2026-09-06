<template>
  <div class="workbench-page">
    <!-- 浅底留白背景：宣纸纹理 + 极淡云雾 -->
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
      <div class="lj-wash w3"></div>
    </div>

    <!-- 玉简轮播作为主角（岛屿导航核心） -->
    <section class="wb-hero">
      <div class="wb-eyebrow">玄 黄 · 仙 府 一 隅</div>
      <h1 class="wb-title">玄黄 · 工作台</h1>
      <p class="wb-subtitle">把零散念头，沉淀为笔记、AI 与可执之事。</p>
      <JadeCarousel class="wb-jade" />
    </section>

    <!-- 常用工具区（工具 + 快捷动作混排） -->
    <div class="wb-body">
      <WorkbenchTools />
    </div>

    <!-- 大数据看板（账本 / 资讯 / 行情 三卡预览） -->
    <div class="wb-body wb-dash">
      <WorkbenchDashboard :empty="empty" :finance="finance" :feeds="feeds" />
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
import { financeApi } from '@/api/finance'
import { feedsApi } from '@/api/feeds'

const empty = ref(true)
const finance = ref({})
const feeds = ref([])

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
      if (res.data.source_count) empty.value = false
      feeds.value = res.data.recent || []
    }
  } catch (e) {
    /* 资讯未就绪忽略 */
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

.workbench-page > *:not(.lj-bg) { position: relative; z-index: 1; }

/* ===== 主角区：玉简 ===== */
.wb-hero { text-align: center; padding: 6px 0 8px; animation: lj-rise .8s cubic-bezier(.4,0,.2,1) both; }
.wb-eyebrow { font-size: 11px; letter-spacing: .5em; color: var(--lj-mist); margin-bottom: 10px; }
.wb-title { font-size: 34px; font-weight: 600; letter-spacing: .1em; margin: 0; color: var(--lj-text); }
.wb-subtitle { margin: 10px 0 0; font-size: 13px; color: var(--lj-text-2); letter-spacing: .18em; }
.wb-jade { margin-top: 8px; }
@keyframes lj-rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }

/* ===== 数据区 ===== */
.wb-body { padding-top: 10px; }
.wb-body + .wb-body { margin-top: 20px; }

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
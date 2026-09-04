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

    <!-- 快捷动作 -->
    <div class="wb-body">
      <section class="wb-actions">
        <router-link to="/notes/new" class="wb-action primary">
          <span class="wb-action-icon"><el-icon><Edit /></el-icon></span>
          <span class="wb-action-text">
            <strong>快速记录</strong>
            <small>新建草稿，自动保存</small>
          </span>
        </router-link>
        <router-link to="/assistant" class="wb-action">
          <span class="wb-action-icon"><el-icon><ChatDotRound /></el-icon></span>
          <span class="wb-action-text">
            <strong>AI 助手</strong>
            <small>整理 · 摘要 · 化虚为实</small>
          </span>
        </router-link>
      </section>
    </div>

    <!-- 底部网安/备案标识（浅色留白页脚，随浅色页面底边展开） -->
    <SiteFooter variant="light" class="wb-footer" />
  </div>
</template>

<script setup>
import { Edit, ChatDotRound } from '@element-plus/icons-vue'
import JadeCarousel from '@/components/JadeCarousel.vue'
import SiteFooter from '@/components/SiteFooter.vue'
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

/* ===== 浅底留白背景 ===== */
.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 60% 40% at 20% 8%, rgba(74, 95, 99, 0.05), transparent 60%),
    radial-gradient(ellipse 50% 40% at 85% 30%, rgba(176, 128, 90, 0.05), transparent 60%),
    var(--lj-bg);
}
.lj-paper-texture {
  position: absolute; inset: 0; opacity: 0.55;
  background:
    repeating-linear-gradient(0deg, rgba(58, 67, 80, 0.012) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(58, 67, 80, 0.008) 0 1px, transparent 1px 7px);
}
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4;
  background: radial-gradient(circle, rgba(74, 95, 99, 0.12), transparent 70%); animation: lj-drift 30s ease-in-out infinite; }
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
.wb-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 0 0 24px; }
.wb-action {
  position: relative; display: flex; gap: 14px; align-items: center; padding: 18px;
  border-radius: 14px; color: var(--lj-text); text-decoration: none;
  background: var(--lj-paper);
  border: 1px solid var(--lj-line); overflow: hidden;
  box-shadow: var(--lj-shadow);
  transition: all 0.3s; animation: lj-rise .7s cubic-bezier(.4,0,.2,1) both;
}
.wb-action::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--lj-dai), transparent); opacity: .6; }
.wb-action-icon {
  width: 46px; height: 46px; flex: none; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: var(--lj-dai); font-size: 22px;
  border: 1px solid var(--lj-line); background: rgba(74, 95, 99, 0.06);
  transition: all 0.3s;
}
.wb-action:hover { transform: translateY(-2px); border-color: var(--lj-line-strong); box-shadow: 0 12px 30px rgba(58, 67, 80, 0.12); }
.wb-action:hover .wb-action-icon { background: rgba(74, 95, 99, 0.1); }
.wb-action-text { display: flex; flex-direction: column; }
.wb-action-text strong { font-size: 16px; letter-spacing: .06em; }
.wb-action-text small { margin-top: 3px; color: var(--lj-text-2); font-size: 12px; }
.wb-action.primary { background: linear-gradient(135deg, var(--lj-paper), #eef0eb); }
.wb-action.primary .wb-action-icon { color: var(--lj-ochre); border-color: rgba(176, 128, 90, 0.25); background: rgba(176, 128, 90, 0.08); }

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
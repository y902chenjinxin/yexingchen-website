<!--
  DecorLoaderRainMatrix.vue
  来源：uiverse.io/Nawsome/blue-dragon-70（MIT License）
  玄黄改造：
    - 颜色全走 --yq-rain（雨青）— 取代原 #fff
    - 9 段 keyframes 矩阵移动 + 4s 循环
    - 昼夜双套：日间加深雨青，夜间保留原质感
  用途：工作台 / 加载密集场景（如 AI 长任务）
-->
<template>
  <div class="dloader dloader--rain-matrix" role="status" aria-label="加载中">
    <div v-for="i in 9" :key="i" class="dloader__box"></div>
  </div>
</template>

<script setup>
// 9 段 keyframes 矩阵，无需 props
</script>

<style scoped>
.dloader {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto;
}
.dloader__box {
  float: left;
  position: relative;
  width: 20px;
  height: 20px;
  margin-right: 6px;
}
.dloader__box::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  /* 玄黄：雨青主体色 + 鎏金辉光 */
  background: var(--yq-rain, #7fa8a3);
  box-shadow: 0 0 8px var(--shadow-glow, rgba(127, 168, 163, 0.55));
  border-radius: 2px;
}
.dloader__box:nth-child(3n) { margin-right: 0; margin-bottom: 6px; }
.dloader__box:nth-child(1)::before,
.dloader__box:nth-child(4)::before { margin-left: 26px; }
.dloader__box:nth-child(3)::before { margin-top: 52px; }
.dloader__box:last-child { margin-bottom: 0; }

@keyframes dloader-mb-1 { 9.0909090909% { transform: translate(-26px, 0); } 18.1818181818% { transform: translate(0px, 0); } 27.2727272727% { transform: translate(0px, 0); } 36.3636363636% { transform: translate(26px, 0); } 45.4545454545% { transform: translate(26px, 26px); } 54.5454545455% { transform: translate(26px, 26px); } 63.6363633636% { transform: translate(26px, 26px); } 72.7272727273% { transform: translate(26px, 0px); } 81.8181818182% { transform: translate(0px, 0px); } 90.9090909091% { transform: translate(-26px, 0px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(1) { animation: dloader-mb-1 4s infinite; }
@keyframes dloader-mb-2 { 9.0909090909% { transform: translate(0, 0); } 18.1818181818% { transform: translate(26px, 0); } 27.2727272727% { transform: translate(0px, 0); } 36.3636363636% { transform: translate(26px, 0); } 45.4545454545% { transform: translate(26px, 26px); } 54.5454545455% { transform: translate(26px, 26px); } 63.6363633636% { transform: translate(26px, 26px); } 72.7272727273% { transform: translate(26px, 26px); } 81.8181818182% { transform: translate(0px, 26px); } 90.9090909091% { transform: translate(0px, 26px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(2) { animation: dloader-mb-2 4s infinite; }
@keyframes dloader-mb-3 { 9.0909090909% { transform: translate(-26px, 0); } 18.1818181818% { transform: translate(-26px, 0); } 27.2727272727% { transform: translate(0px, 0); } 36.3636363636% { transform: translate(-26px, 0); } 45.4545454545% { transform: translate(-26px, 0); } 54.5454545455% { transform: translate(-26px, 0); } 63.6363633636% { transform: translate(-26px, 0); } 72.7272727273% { transform: translate(-26px, 0); } 81.8181818182% { transform: translate(-26px, -26px); } 90.9090909091% { transform: translate(0px, -26px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(3) { animation: dloader-mb-3 4s infinite; }
@keyframes dloader-mb-4 { 9.0909090909% { transform: translate(-26px, 0); } 18.1818181818% { transform: translate(-26px, 0); } 27.2727272727% { transform: translate(-26px, -26px); } 36.3636363636% { transform: translate(0px, -26px); } 45.4545454545% { transform: translate(0px, 0px); } 54.5454545455% { transform: translate(0px, -26px); } 63.6363633636% { transform: translate(0px, -26px); } 72.7272727273% { transform: translate(0px, -26px); } 81.8181818182% { transform: translate(-26px, -26px); } 90.9090909091% { transform: translate(-26px, 0px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(4) { animation: dloader-mb-4 4s infinite; }
@keyframes dloader-mb-5 { 9.0909090909% { transform: translate(0, 0); } 18.1818181818% { transform: translate(0, 0); } 27.2727272727% { transform: translate(0, 0); } 36.3636363636% { transform: translate(26px, 0); } 45.4545454545% { transform: translate(26px, 0); } 54.5454545455% { transform: translate(26px, 0); } 63.6363633636% { transform: translate(26px, 0); } 72.7272727273% { transform: translate(26px, 0); } 81.8181818182% { transform: translate(26px, -26px); } 90.9090909091% { transform: translate(0px, -26px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(5) { animation: dloader-mb-5 4s infinite; }
@keyframes dloader-mb-6 { 9.0909090909% { transform: translate(0, 0); } 18.1818181818% { transform: translate(-26px, 0); } 27.2727272727% { transform: translate(-26px, 0); } 36.3636363636% { transform: translate(0px, 0); } 45.4545454545% { transform: translate(0px, 0); } 54.5454545455% { transform: translate(0px, 0); } 63.6363633636% { transform: translate(0px, 0); } 72.7272727273% { transform: translate(0px, 26px); } 81.8181818182% { transform: translate(-26px, 26px); } 90.9090909091% { transform: translate(-26px, 0px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(6) { animation: dloader-mb-6 4s infinite; }
@keyframes dloader-mb-7 { 9.0909090909% { transform: translate(26px, 0); } 18.1818181818% { transform: translate(26px, 0); } 27.2727272727% { transform: translate(26px, 0); } 36.3636363636% { transform: translate(0px, 0); } 45.4545454545% { transform: translate(0px, -26px); } 54.5454545455% { transform: translate(26px, -26px); } 63.6363633636% { transform: translate(0px, -26px); } 72.7272727273% { transform: translate(0px, -26px); } 81.8181818182% { transform: translate(0px, 0px); } 90.9090909091% { transform: translate(26px, 0px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(7) { animation: dloader-mb-7 4s infinite; }
@keyframes dloader-mb-8 { 9.0909090909% { transform: translate(0, 0); } 18.1818181818% { transform: translate(-26px, 0); } 27.2727272727% { transform: translate(-26px, -26px); } 36.3636363636% { transform: translate(0px, -26px); } 45.4545454545% { transform: translate(0px, -26px); } 54.5454545455% { transform: translate(0px, -26px); } 63.6363633636% { transform: translate(0px, -26px); } 72.7272727273% { transform: translate(0px, -26px); } 81.8181818182% { transform: translate(26px, -26px); } 90.9090909091% { transform: translate(26px, 0px); } 100% { transform: translate(0px, 0px); } }
.dloader__box:nth-child(8) { animation: dloader-mb-8 4s infinite; }
@keyframes dloader-mb-9 { 9.0909090909% { transform: translate(-26px, 0); } 18.1818181818% { transform: translate(-26px, 0); } 27.2727272727% { transform: translate(0px, 0); } 36.3636363636% { transform: translate(-26px, 0); } 45.4545454545% { transform: translate(0px, 0); } 54.5454545455% { transform: translate(0px, 0); } 63.6363633636% { transform: translate(-26px, 0); } 72.7272727273% { transform: translate(-26px, 0); } 81.8181818182% { transform: translate(-52px, 0); } 90.9090909091% { transform: translate(-26px, 0); } 100% { transform: translate(0px, 0); } }
.dloader__box:nth-child(9) { animation: dloader-mb-9 4s infinite; }

/* 日间主题加深雨青 + 投影收敛 */
:global(html[data-theme="day"]) .dloader__box::before {
  background: var(--yq-rain-deep, #22665f);
  box-shadow: 0 0 6px rgba(34, 102, 95, 0.5);
}
@media (prefers-reduced-motion: reduce) {
  .dloader__box { animation: none !important; }
}
</style>
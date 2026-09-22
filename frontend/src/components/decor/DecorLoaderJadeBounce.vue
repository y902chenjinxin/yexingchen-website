<!--
  DecorLoaderJadeBounce.vue
  来源：uiverse.io/alexruix/white-cat-50（MIT License）
  玄黄改造：
    - 颜色：鎏金→雨青双色渐变（替代原 #f08080 红）
    - 投影用玄黄 glass shadow
    - 昼夜双套
  用途：按钮内 / 行内 / 小区块加载
-->
<template>
  <div class="dloader dloader--jade-bounce" role="status" aria-label="加载中">
    <div class="dloader__ball"></div>
    <div class="dloader__shadow"></div>
  </div>
</template>

<script setup>
// 无 props，直接使用
</script>

<style scoped>
.dloader {
  width: 28px;
  height: 36px;
  margin: 0 auto;
  position: relative;
}
/* 原"红色方块" — 玄黄：鎏金→雨青 渐变 */
.dloader__ball {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg,
    var(--yq-gold, #c7a96b) 0%,
    var(--yq-rain, #7fa8a3) 100%);
  position: absolute;
  top: 0;
  left: 0;
  border-radius: 4px;
  box-shadow:
    inset -2px -2px 4px rgba(0, 0, 0, 0.18),
    inset 2px 2px 4px rgba(240, 230, 200, 0.45),
    0 2px 8px var(--shadow-glow, rgba(127, 168, 163, 0.4));
  animation: dloader-bounce 0.5s linear infinite;
  will-change: transform, border-radius;
}
/* 原"投影" — 玄黄：冷色半透明 */
.dloader__shadow {
  content: "";
  width: 100%;
  height: 5px;
  background: rgba(127, 168, 163, 0.35);
  position: absolute;
  top: 31px;
  left: 0;
  border-radius: 50%;
  filter: blur(1px);
  animation: dloader-bounce-shadow 0.5s linear infinite;
  will-change: transform;
}
@keyframes dloader-bounce {
  15% { border-bottom-right-radius: 3px; }
  25% { transform: translateY(9px) rotate(22.5deg); }
  50% { transform: translateY(18px) scale(1, .9) rotate(45deg); border-bottom-right-radius: 12px; }
  75% { transform: translateY(9px) rotate(67.5deg); }
  100% { transform: translateY(0) rotate(90deg); }
}
@keyframes dloader-bounce-shadow {
  0%, 100% { transform: scale(1, 1); }
  50% { transform: scale(1.2, 1); }
}
/* 日间主题：双色更鲜明，投影更深 */
:global(html[data-theme="day"]) .dloader__ball {
  background: linear-gradient(135deg,
    var(--yq-gold, #a9804f) 0%,
    var(--yq-rain-deep, #22665f) 100%);
}
:global(html[data-theme="day"]) .dloader__shadow {
  background: rgba(34, 102, 95, 0.3);
}
@media (prefers-reduced-motion: reduce) {
  .dloader__ball, .dloader__shadow { animation: none; }
}
</style>
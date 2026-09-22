<!--
  DecorLoaderGoldRocker.vue
  来源：uiverse.io/Shoh2008/cold-walrus-85（MIT License）
  玄黄改造：
    - 颜色全走 --yq-gold（鎏金）与 --yq-rain（雨青）变量
    - 昼夜双套自动跟随 data-theme 切换
    - prefers-reduced-motion 收敛动画
  用途：节日级加载 / 大区块（如工作台驾驶舱 / 股票详情卡）
-->
<template>
  <div class="dloader dloader--gold-rocker" :style="sizeStyle" role="status" aria-label="加载中">
    <div class="dloader__bar"></div>
    <div class="dloader__rock"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  size: { type: [Number, String], default: 88 }, // px
})
const sizeStyle = computed(() => ({ fontSize: `${Number(props.size) / 16}px` }))
</script>

<style scoped>
.dloader {
  position: relative;
  width: 5.5em;
  height: 5.5em;
}
/* 中心纵向条纹（原"白色"立柱）— 玄黄：鎏金深浅 */
.dloader__bar {
  position: absolute;
  transform: translate(-50%, -50%) rotate(45deg);
  height: 100%;
  width: 4px;
  left: 50%;
  top: 50%;
  background: linear-gradient(180deg,
    var(--yq-gold-bright, #f0e6c8),
    var(--yq-gold, #c7a96b),
    var(--yq-gold-dark, #8a6d3f));
  border-radius: 2px;
}
/* 跳跃骰子（原 orange）— 玄黄：鎏金 */
.dloader__rock {
  position: absolute;
  left: 0.2em;
  bottom: 0.18em;
  width: 1em;
  height: 1em;
  background-color: var(--yq-gold, #c7a96b);
  box-shadow:
    inset -2px -2px 4px rgba(0, 0, 0, 0.25),
    inset 2px 2px 4px rgba(240, 230, 200, 0.6),
    0 4px 12px var(--shadow-glow, rgba(199, 169, 107, 0.45));
  border-radius: 15%;
  animation: dloader-rock 2.5s cubic-bezier(.79, 0, .47, .97) infinite;
}
@keyframes dloader-rock {
  0%   { transform: translate(0, -1em) rotate(-45deg) }
  5%   { transform: translate(0, -1em) rotate(-50deg) }
  20%  { transform: translate(1em, -2em) rotate(47deg) }
  25%  { transform: translate(1em, -2em) rotate(45deg) }
  30%  { transform: translate(1em, -2em) rotate(40deg) }
  45%  { transform: translate(2em, -3em) rotate(137deg) }
  50%  { transform: translate(2em, -3em) rotate(135deg) }
  55%  { transform: translate(2em, -3em) rotate(130deg) }
  70%  { transform: translate(3em, -4em) rotate(217deg) }
  75%  { transform: translate(3em, -4em) rotate(220deg) }
  100% { transform: translate(0, -1em) rotate(-225deg) }
}
/* 日间（亮底）下，骰子投影偏深、bar 渐变更稳重 */
:global(html[data-theme="day"]) .dloader--gold-rocker .dloader__rock {
  box-shadow:
    inset -2px -2px 4px rgba(0, 0, 0, 0.3),
    inset 2px 2px 4px rgba(240, 230, 200, 0.7),
    0 4px 10px rgba(169, 128, 79, 0.4);
}
:global(html[data-theme="day"]) .dloader--gold-rocker .dloader__bar {
  opacity: 0.85;
}
@media (prefers-reduced-motion: reduce) {
  .dloader__rock { animation: none; }
}
</style>
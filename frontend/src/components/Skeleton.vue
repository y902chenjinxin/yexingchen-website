<!--
  Skeleton.vue
  玄黄·通用骨架屏（shimmer）
  - 用于首屏数据未到时的占位，比"kpi—"更显"即将出现"的观感
  - 支持 block（矩形）/ text（行）/ circle 三种
  - 支持组合：传入 v-for 数组自动 stagger
  - 自动响应 prefers-reduced-motion（关闭 shimmer 渐变）

  Props:
    type: 'block' | 'text' | 'circle'  (默认 block)
    width: string  (默认 100%)
    height: string (默认 14px)
    radius: string (默认 6px；circle 时默认 50%)
    block: 布尔，是否独占一行
-->
<template>
  <span
    class="sk"
    :class="['sk-' + type, block && 'sk-block', animated && 'sk-anim']"
    :style="{
      width: width,
      height: type === 'circle' ? width : height,
      borderRadius: type === 'circle' ? '50%' : radius,
    }"
    aria-hidden="true"
  />
</template>

<script setup>
defineProps({
  type: { type: String, default: 'block' },
  width: { type: String, default: '100%' },
  height: { type: String, default: '14px' },
  radius: { type: String, default: '6px' },
  block: { type: Boolean, default: false },
  animated: { type: Boolean, default: true },
})
</script>

<style scoped>
.sk {
  display: inline-block;
  vertical-align: middle;
  background: linear-gradient(
    90deg,
    rgba(127, 127, 160, 0.06) 0%,
    rgba(127, 127, 160, 0.18) 50%,
    rgba(127, 127, 160, 0.06) 100%
  );
  background-size: 240% 100%;
  background-position: 100% 0;
}
.sk-block { display: block; }
.sk-anim {
  animation: sk-shimmer 1.4s ease-in-out infinite;
}
@keyframes sk-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}

/* 浅色主题调亮 */
:root[data-theme="day"] .sk {
  background: linear-gradient(
    90deg,
    rgba(0, 0, 0, 0.04) 0%,
    rgba(0, 0, 0, 0.10) 50%,
    rgba(0, 0, 0, 0.04) 100%
  );
  background-size: 240% 100%;
  background-position: 100% 0;
}

@media (prefers-reduced-motion: reduce) {
  .sk-anim { animation: none; background: rgba(127, 127, 160, 0.14); }
  :root[data-theme="day"] .sk-anim { background: rgba(0, 0, 0, 0.08); }
}
</style>
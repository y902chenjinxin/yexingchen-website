<!--
  SkeletonBlock.vue
  玄黄 · 通用骨架屏
  - 自动根据 width/height/round 渲染鎏金底色 + 鎏金光扫过的占位
  - theme-aware：跟随 --yq-gold 自动适配昼夜
-->
<template>
  <div
    class="sk"
    :class="{ 'sk-round': round }"
    :style="boxStyle"
    :aria-hidden="true"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  width: { type: [String, Number], default: '100%' }, // '100%' / '60px' / 60
  height: { type: [String, Number], default: '14px' },
  round: { type: Boolean, default: false }, // 圆形（头像）
  block: { type: Boolean, default: false }, // display: block
})

const boxStyle = computed(() => {
  const w = typeof props.width === 'number' ? `${props.width}px` : props.width
  const h = typeof props.height === 'number' ? `${props.height}px` : props.height
  return {
    width: w,
    height: h,
    display: props.block ? 'block' : 'inline-block',
  }
})
</script>

<style scoped>
.sk {
  position: relative;
  background: linear-gradient(
    90deg,
    var(--dp-line, rgba(127, 127, 127, 0.1)) 0%,
    var(--dp-line-strong, rgba(127, 127, 127, 0.18)) 50%,
    var(--dp-line, rgba(127, 127, 127, 0.1)) 100%
  );
  background-size: 200% 100%;
  border-radius: 6px;
  animation: sk-shimmer 1.4s linear infinite;
  overflow: hidden;
  vertical-align: middle;
}

/* 鎏金光斑扫过 */
.sk::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--yq-gold-faint, rgba(199, 169, 107, 0.22)) 50%,
    transparent 100%
  );
  background-size: 60% 100%;
  background-repeat: no-repeat;
  animation: sk-sweep 1.4s ease-in-out infinite;
}

.sk-round { border-radius: 9999px; }

@keyframes sk-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@keyframes sk-sweep {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}

@media (prefers-reduced-motion: reduce) {
  .sk, .sk::after { animation: none; }
}
</style>
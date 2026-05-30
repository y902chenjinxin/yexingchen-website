<template>
  <div class="qi-layer" :class="{ 'breath-active': isBreathing }">
    <div class="qi-flow-container">
      <div
        v-for="i in qiCount"
        :key="i"
        class="qi-particle"
        :style="getQiStyle(i)"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useBreathCycle } from '@/composables/useBreathCycle'

const props = defineProps({
  qiCount: {
    type: Number,
    default: 30
  }
})

const { phase, progress } = useBreathCycle()

const isBreathing = computed(() => true) // 始终活跃

// 种子随机
const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getQiStyle = (i) => {
  const seed = i * 2345.6789
  const random = seededRandom(seed)

  // 粒子起始位置
  const startX = random * 100
  const startY = 100 + seededRandom(seed * 2) * 50 // 从下方开始

  // 移动方向
  const endX = (random + 0.2) * 100
  const endY = seededRandom(seed * 3) * 30 // 向上移动

  // 动画延迟（相位差）
  const delay = seededRandom(seed * 4) * 10

  // 粒子大小
  const size = 20 + seededRandom(seed * 5) * 40

  // 颜色透明度（随呼吸变化）
  const baseOpacity = 0.05 + seededRandom(seed * 6) * 0.1
  const breathMultiplier = phase.value === 'inhale'
    ? 0.5 + progress.value * 0.5
    : phase.value === 'hold'
    ? 1
    : 1 - progress.value * 0.5

  return {
    left: `${startX}%`,
    bottom: `${100 - startY}%`,
    width: `${size}px`,
    height: `${size}px`,
    opacity: baseOpacity * breathMultiplier,
    animationDelay: `${delay}s`,
    // 动画位移
    '--end-x': `${endX - startX}%`,
    '--end-y': `${startY - endY}%`
  }
}
</script>

<style scoped>
.qi-layer {
  position: fixed;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  opacity: var(--layer-3-opacity, 0.7);
}

.qi-flow-container {
  position: absolute;
  inset: 0;
}

.qi-particle {
  position: absolute;
  background: radial-gradient(
    ellipse at center,
    var(--color-gold-light) 0%,
    transparent 70%
  );
  border-radius: 50%;
  filter: blur(10px);
  animation: qi-float 20s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes qi-float {
  0% {
    transform: translate(0, 0) scale(1);
    opacity: 0.1;
  }
  25% {
    transform: translate(var(--end-x), calc(var(--end-y) * 0.5)) scale(1.1);
    opacity: 0.3;
  }
  50% {
    transform: translate(calc(var(--end-x) * 0.5), var(--end-y)) scale(0.9);
    opacity: 0.15;
  }
  75% {
    transform: translate(calc(var(--end-x) * 0.8), calc(var(--end-y) * 0.3)) scale(1.05);
    opacity: 0.25;
  }
  100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.1;
  }
}

/* 呼吸时灵气更活跃 */
.breath-active .qi-particle {
  animation-duration: 15s;
}
</style>
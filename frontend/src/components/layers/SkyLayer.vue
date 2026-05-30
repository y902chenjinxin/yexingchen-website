<template>
  <div class="sky-layer" :class="{ 'breath-active': isBreathing }">
    <div class="stars-container">
      <div
        v-for="i in starCount"
        :key="i"
        class="star"
        :style="getStarStyle(i)"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useBreathCycle } from '@/composables/useBreathCycle'

const props = defineProps({
  starCount: {
    type: Number,
    default: 50
  }
})

// 使用呼吸节奏
const { phase, progress } = useBreathCycle({
  breathIn: 4000,
  breathHold: 7000,
  breathOut: 8000
})

const isBreathing = computed(() => phase.value !== 'hold' || progress.value < 0.9)

// 种子随机函数
const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getStarStyle = (i) => {
  const seed = i * 1234.5678
  const random = seededRandom(seed)

  // 星星位置
  const x = random * 100
  const y = seededRandom(seed * 2) * 100

  // 星星大小
  const size = 1 + seededRandom(seed * 3) * 2

  // 星星透明度（随呼吸变化）
  const baseOpacity = 0.2 + seededRandom(seed * 4) * 0.3
  const breathMultiplier = phase.value === 'inhale'
    ? 0.5 + progress.value * 0.5
    : phase.value === 'hold'
    ? 1
    : 1 - progress.value * 0.5

  return {
    left: `${x}%`,
    top: `${y}%`,
    width: `${size}px`,
    height: `${size}px`,
    opacity: baseOpacity * breathMultiplier,
    animationDelay: `${seededRandom(seed * 5) * 5}s`
  }
}

onMounted(() => {
  // 根据设备性能调整星星数量
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    props.starCount = 20
  }
})
</script>

<style scoped>
.sky-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  opacity: var(--layer-1-opacity, 0.3);
}

.stars-container {
  position: absolute;
  inset: 0;
}

.star {
  position: absolute;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.8) 0%, transparent 70%);
  border-radius: 50%;
  animation: twinkle 4s ease-in-out infinite;
  will-change: opacity, transform;
}

@keyframes twinkle {
  0%, 100% {
    opacity: 0.2;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.2);
  }
}

/* 呼吸状态下星星更亮 */
.breath-active .star {
  animation-duration: 6s;
}
</style>
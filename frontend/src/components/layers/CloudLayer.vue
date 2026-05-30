<template>
  <div class="cloud-layer" :class="{ 'breath-active': isBreathing }">
    <div
      v-for="i in cloudCount"
      :key="i"
      class="cloud"
      :class="`cloud-${i}`"
      :style="getCloudStyle(i)"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useBreathCycle } from '@/composables/useBreathCycle'

const props = defineProps({
  cloudCount: {
    type: Number,
    default: 4
  }
})

const { phase, progress } = useBreathCycle()

const isBreathing = computed(() => phase.value !== 'hold')

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getCloudStyle = (i) => {
  const seed = i * 3456.789
  const random = seededRandom(seed)

  // 云的起始位置
  const top = 10 + random * 70 // 10% - 80%
  const left = -10 + random * 30 // -10% - 20%

  // 云的大小（视口比例）
  const width = 60 + seededRandom(seed * 2) * 30 // 60vw - 90vw
  const height = width * 0.5 // 高宽比0.5

  // 动画延迟
  const delay = i * 5 // 每个云延迟5秒

  // 颜色（随十二时辰变化，使用CSS变量）
  const opacity = 0.3 + seededRandom(seed * 3) * 0.3

  return {
    top: `${top}%`,
    left: `${left}%`,
    width: `${width}vw`,
    height: `${height}vh`,
    opacity: opacity,
    animationDelay: `${delay}s`,
    // 使用运行时CSS变量
    background: `radial-gradient(ellipse at center, var(--color-cloud-current) 0%, transparent 70%)`
  }
}
</script>

<style scoped>
.cloud-layer {
  position: fixed;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  opacity: var(--layer-4-opacity, 0.9);
}

.cloud {
  position: absolute;
  border-radius: 50%;
  transition: background 1s ease, opacity 1s ease;
  animation: cloud-drift 25s linear infinite;
  will-change: transform, opacity;
}

.cloud-1 {
  animation-duration: 25s;
}

.cloud-2 {
  animation-duration: 30s;
  animation-delay: 5s;
}

.cloud-3 {
  animation-duration: 20s;
  animation-delay: 10s;
}

.cloud-4 {
  animation-duration: 28s;
  animation-delay: 3s;
}

@keyframes cloud-drift {
  0% {
    transform: translateX(0);
  }
  50% {
    transform: translateX(50px);
  }
  100% {
    transform: translateX(0);
  }
}

/* 呼吸时云层更浓郁 */
.breath-active .cloud {
  animation-duration: 20s;
}
</style>
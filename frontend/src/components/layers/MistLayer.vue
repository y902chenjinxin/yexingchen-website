<template>
  <div class="mist-layer" :class="{ 'breath-active': isBreathing }">
    <div
      v-for="i in mistCount"
      :key="i"
      class="mist"
      :class="`mist-${i}`"
      :style="getMistStyle(i)"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useBreathCycle } from '@/composables/useBreathCycle'

const props = defineProps({
  mistCount: {
    type: Number,
    default: 3
  }
})

const { phase, progress } = useBreathCycle({
  breathIn: 4000,
  breathHold: 7000,
  breathOut: 8000,
  initialDelay: 500 // 比其他层晚一点启动
})

const isBreathing = computed(() => phase.value !== 'hold')

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getMistStyle = (i) => {
  const seed = i * 4567.89
  const random = seededRandom(seed)

  // 近景薄雾位置（底部）
  const bottom = 5 + random * 15 // 5% - 20%
  const left = random * 100

  // 雾的宽度（覆盖整个视口）
  const width = 100 + seededRandom(seed * 2) * 50 // 100vw - 150vw
  const height = 15 + seededRandom(seed * 3) * 10 // 15vh - 25vh

  // 动画延迟
  const delay = i * 8

  // 透明度（随呼吸变化，更明显）
  const baseOpacity = 0.15 + seededRandom(seed * 4) * 0.15
  const breathMultiplier = phase.value === 'inhale'
    ? 0.4 + progress.value * 0.6
    : phase.value === 'hold'
    ? 1
    : 1 - progress.value * 0.6

  return {
    bottom: `${bottom}%`,
    left: `${left - 25}%`, // 偏移出去一些
    width: `${width}vw`,
    height: `${height}vh`,
    opacity: baseOpacity * breathMultiplier,
    animationDelay: `${delay}s`
  }
}
</script>

<style scoped>
.mist-layer {
  position: fixed;
  inset: 0;
  z-index: 4;
  pointer-events: none;
  opacity: var(--layer-5-opacity, 0.4);
}

.mist {
  position: absolute;
  background: linear-gradient(
    to top,
    rgba(18, 20, 26, 0.8) 0%,
    rgba(18, 20, 26, 0.4) 40%,
    transparent 100%
  );
  filter: blur(20px);
  animation: mist-flow 30s ease-in-out infinite;
  will-change: transform, opacity;
}

.mist-1 {
  animation-duration: 30s;
}

.mist-2 {
  animation-duration: 35s;
  animation-delay: 8s;
}

.mist-3 {
  animation-duration: 28s;
  animation-delay: 16s;
}

@keyframes mist-flow {
  0% {
    transform: translateX(0) scaleY(1);
  }
  33% {
    transform: translateX(30px) scaleY(1.05);
  }
  66% {
    transform: translateX(-20px) scaleY(0.95);
  }
  100% {
    transform: translateX(0) scaleY(1);
  }
}

/* 呼吸时薄雾更飘渺 */
.breath-active .mist {
  animation-duration: 25s;
  filter: blur(15px);
}
</style>
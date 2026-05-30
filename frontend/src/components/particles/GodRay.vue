<template>
  <div class="god-ray-container" v-if="isEnabled">
    <div
      v-for="i in rayCount"
      :key="i"
      class="god-ray"
      :class="`god-ray-${i}`"
      :style="getRayStyle(i)"
    >
      <div class="ray-particles">
        <div
          v-for="j in particleCount"
          :key="j"
          class="ray-particle"
          :style="getParticleStyle(i, j)"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useGracefulDegrade } from '@/composables/useGracefulDegrade'

const props = defineProps({
  rayCount: {
    type: Number,
    default: 4
  },
  particleCount: {
    type: Number,
    default: 8
  }
})

const { isFeatureEnabled } = useGracefulDegrade()
const isEnabled = computed(() => isFeatureEnabled('godRays'))

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getRayStyle = (i) => {
  const seed = i * 7891.234
  const random = seededRandom(seed)

  // 光柱位置
  const left = 10 + random * 80 // 10% - 90%
  const top = -10 - random * 20 // 从上方斜射

  // 光柱倾斜角度
  const angle = -30 + random * 20 // -30deg 到 -10deg

  // 动画延迟
  const delay = i * 2

  // 光柱宽度
  const width = 50 + random * 100

  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${width}px`,
    transform: `rotate(${angle}deg)`,
    animationDelay: `${delay}s`,
    opacity: 0.3 + random * 0.3
  }
}

const getParticleStyle = (i, j) => {
  const seed = i * 1000 + j * 123.456
  const random = seededRandom(seed)

  // 粒子在光柱中的位置
  const y = random * 100 // 0% - 100%
  const x = -20 + random * 40 // 光柱内偏移

  // 动画延迟
  const delay = random * 10

  // 粒子大小
  const size = 2 + random * 4

  return {
    top: `${y}%`,
    left: `${50 + x}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`
  }
}
</script>

<style scoped>
.god-ray-container {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  overflow: hidden;
}

.god-ray {
  position: absolute;
  height: 150vh;
  background: linear-gradient(
    to bottom,
    var(--god-ray-color) 0%,
    transparent 100%
  );
  filter: blur(30px);
  animation: ray-pulse var(--god-ray-animation-duration, 8s) ease-in-out infinite;
  will-change: opacity, transform;
}

@keyframes ray-pulse {
  0%, 100% {
    opacity: 0.3;
    transform: translateX(0) rotate(var(--angle, -20deg));
  }
  50% {
    opacity: 0.6;
    transform: translateX(20px) rotate(var(--angle, -20deg));
  }
}

.ray-particles {
  position: absolute;
  inset: 0;
}

.ray-particle {
  position: absolute;
  background: var(--color-gold);
  border-radius: 50%;
  opacity: var(--god-ray-particle-opacity, 0.5);
  animation: particle-drift 15s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes particle-drift {
  0% {
    transform: translateY(0) translateX(0);
    opacity: 0.3;
  }
  50% {
    transform: translateY(50vh) translateX(10px);
    opacity: 0.6;
  }
  100% {
    transform: translateY(100vh) translateX(0);
    opacity: 0.3;
  }
}
</style>
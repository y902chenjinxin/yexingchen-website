<template>
  <div class="mountain-layer" :class="{ 'breath-active': isBreathing }">
    <svg class="mountain-svg" viewBox="0 0 1440 320" preserveAspectRatio="xMidYMax slice">
      <!-- 远山剪影 - 多层叠加营造纵深 -->
      <path
        class="mountain mountain-1"
        d="M0,320 L0,200 Q180,120 360,180 Q540,100 720,160 Q900,80 1080,140 Q1260,100 1440,160 L1440,320 Z"
        fill="var(--color-bg-dark)"
        opacity="0.6"
      />
      <path
        class="mountain mountain-2"
        d="M0,320 L0,220 Q120,160 240,200 Q360,140 480,180 Q600,120 720,160 Q840,140 960,180 Q1080,130 1200,170 Q1320,150 1440,190 L1440,320 Z"
        fill="var(--color-bg)"
        opacity="0.8"
      />
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useBreathCycle } from '@/composables/useBreathCycle'

const { phase, progress } = useBreathCycle()

const isBreathing = computed(() => phase.value !== 'hold')
</script>

<style scoped>
.mountain-layer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40vh;
  z-index: 1;
  pointer-events: none;
  opacity: var(--layer-2-opacity, 0.5);
  animation: mountain-drift 60s linear infinite;
}

.mountain-svg {
  position: absolute;
  bottom: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mountain {
  transition: opacity 2s ease;
}

/* 呼吸时山脉轮廓更清晰 */
.breath-active .mountain-1 {
  opacity: 0.5;
}

.breath-active .mountain-2 {
  opacity: 0.7;
}

@keyframes mountain-drift {
  0% {
    transform: translateX(0);
  }
  50% {
    transform: translateX(-20px);
  }
  100% {
    transform: translateX(0);
  }
}
</style>
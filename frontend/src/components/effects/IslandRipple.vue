/**
 * IslandRipple.vue
 * 灵气共鸣交互 - 岛屿点击波纹效果
 */
<template>
  <div class="ripple-container" ref="containerRef">
    <div
      v-for="ripple in ripples"
      :key="ripple.id"
      class="ripple"
      :style="ripple.style"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'

const containerRef = ref(null)
const ripples = ref([])
let rippleId = 0

// 岛屿颜色配置
const islandColors = {
  music: 'var(--island-music-glow)',
  novel: 'var(--island-novel-glow)',
  video: 'var(--island-video-glow)',
  log: 'var(--island-log-glow)',
  tool: 'var(--island-tool-glow)'
}

// 创建波纹
function createRipple(x, y, islandType = 'music') {
  const id = rippleId++
  const color = islandColors[islandType] || 'var(--color-gold)'

  const ripple = {
    id,
    style: {
      left: `${x}px`,
      top: `${y}px`,
      '--ripple-color': color
    }
  }

  ripples.value.push(ripple)

  // 0.8s后移除波纹
  setTimeout(() => {
    ripples.value = ripples.value.filter(r => r.id !== id)
  }, 800)
}

defineExpose({ createRipple })
</script>

<style scoped>
.ripple-container {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9990;
  overflow: hidden;
}

.ripple {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--ripple-color);
  transform: translate(-50%, -50%) scale(0);
  animation: ripple-expand 0.8s ease-out forwards;
  pointer-events: none;
}

@keyframes ripple-expand {
  0% {
    transform: translate(-50%, -50%) scale(0);
    opacity: 0.6;
  }
  100% {
    transform: translate(-50%, -50%) scale(15);
    opacity: 0;
  }
}
</style>
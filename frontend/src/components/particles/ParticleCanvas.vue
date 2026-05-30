<template>
  <canvas
    ref="canvasRef"
    class="particle-canvas"
    :class="{ 'cursor-active': hasCursor }"
  ></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useParticleSystem } from '@/composables/useParticleSystem'
import { useGracefulDegrade } from '@/composables/useGracefulDegrade'

const canvasRef = ref(null)
const hasCursor = ref(false)

const { isFeatureEnabled } = useGracefulDegrade()

let particleSystem = null

// 鼠标移动处理
const handleMouseMove = (e) => {
  if (!particleSystem) return

  // 添加粒子
  particleSystem.emit(e.clientX, e.clientY, {
    vx: (Math.random() - 0.5) * 2,
    vy: (Math.random() - 0.5) * 2,
    color: 'rgba(201, 169, 98, 0.6)',
    size: 3 + Math.random() * 3
  })

  hasCursor.value = true
}

// 鼠标离开
const handleMouseLeave = () => {
  hasCursor.value = false
}

onMounted(() => {
  // 检查功能开关
  if (!isFeatureEnabled('cursorTrail')) {
    return
  }

  particleSystem = useParticleSystem(canvasRef, {
    particleCount: 30,
    colors: ['rgba(201, 169, 98, 0.6)', 'rgba(74, 124, 89, 0.5)'],
    lifetime: 1200,
    speed: 1,
    size: 3,
    maxParticles: 30
  })

  window.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseleave', handleMouseLeave)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseleave', handleMouseLeave)
})
</script>

<style scoped>
.particle-canvas {
  position: fixed;
  inset: 0;
  z-index: 100;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.particle-canvas.cursor-active {
  opacity: 1;
}
</style>
/**
 * MouseTrail.vue
 * 鼠标灵气轨迹 - Canvas渲染淡金色粒子
 */
<template>
  <canvas ref="canvasRef" class="mouse-trail-canvas" />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref(null)
let ctx = null
let particles = []
let animationId = null
let lastTime = 0
const MAX_PARTICLES = 30
const PARTICLE_LIFETIME = 1200 // 1.2s

// 粒子类
class TrailParticle {
  constructor(x, y) {
    this.x = x
    this.y = y
    this.size = 2 + Math.random() * 2 // 2-4px
    this.opacity = 0.8
    this.birthTime = Date.now()
    this.lifetime = PARTICLE_LIFETIME
    // 使用seed模式确保动画连贯
    this.vx = (Math.random() - 0.5) * 0.5
    this.vy = (Math.random() - 0.5) * 0.5
  }

  update() {
    const age = Date.now() - this.birthTime
    const progress = age / this.lifetime
    this.opacity = 0.8 * (1 - progress)
    this.x += this.vx
    this.y += this.vy
    return age < this.lifetime
  }

  draw(ctx) {
    ctx.save()
    ctx.globalAlpha = this.opacity
    ctx.fillStyle = 'var(--color-qi-green)'
    ctx.shadowColor = 'var(--color-qi-green)'
    ctx.shadowBlur = 12
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }
}

function animate(currentTime) {
  if (!ctx) return

  const deltaTime = currentTime - lastTime
  lastTime = currentTime

  // 清除画布
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)

  // 更新并绘制粒子
  particles = particles.filter(p => p.update())
  particles.forEach(p => p.draw(ctx))

  animationId = requestAnimationFrame(animate)
}

function handleMouseMove(e) {
  if (!canvasRef.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

  // 节流：每16ms最多添加一个粒子（约60fps）
  const now = Date.now()
  if (now - lastTime < 16) return
  lastTime = now

  // 限制最大粒子数
  if (particles.length < MAX_PARTICLES) {
    particles.push(new TrailParticle(x, y))
  }
}

function resizeCanvas() {
  if (!canvasRef.value) return
  canvasRef.value.width = window.innerWidth
  canvasRef.value.height = window.innerHeight
}

onMounted(() => {
  ctx = canvasRef.value.getContext('2d')
  resizeCanvas()

  window.addEventListener('resize', resizeCanvas)
  window.addEventListener('mousemove', handleMouseMove)

  lastTime = Date.now()
  animationId = requestAnimationFrame(animate)
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', resizeCanvas)
  window.removeEventListener('mousemove', handleMouseMove)
})
</script>

<style scoped>
.mouse-trail-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9998;
}
</style>
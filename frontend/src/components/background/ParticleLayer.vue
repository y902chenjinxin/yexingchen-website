<template>
  <canvas ref="canvasRef" class="particle-layer"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  breathValue: { type: Number, default: 0.5 },
  particleCount: { type: Number, default: 60 }
})

const canvasRef = ref(null)
let ctx = null
let animationId = null
let particles = []

// 水墨国风配色 - 低饱和淡雅
const COLORS = [
  'rgba(58, 107, 107, 0.35)',   // 石青 - 主色
  'rgba(45, 74, 62, 0.3)',      // 松绿
  'rgba(139, 107, 74, 0.28)',   // 赭石黄
  'rgba(212, 201, 184, 0.22)',  // 米白
  'rgba(80, 95, 100, 0.25)'     // 灰蓝
]

// Curl noise for organic spiral motion
const curlNoise = (x, y, seed) => {
  const dx = Math.sin(x * 0.006 + seed) * Math.cos(y * 0.006 + seed * 0.7)
  const dy = Math.cos(x * 0.006 + seed * 0.5) * Math.sin(y * 0.006 + seed * 0.3)
  return { dx: dx * 0.8, dy: dy * 0.8 }
}

class QiParticle {
  constructor(canvasWidth, canvasHeight) {
    this.canvasWidth = canvasWidth
    this.canvasHeight = canvasHeight
    this.reset(true)
  }

  reset(randomY = false) {
    this.x = Math.random() * this.canvasWidth
    this.y = randomY ? Math.random() * this.canvasHeight : this.canvasHeight + 80 + Math.random() * 150
    this.vx = (Math.random() - 0.5) * 0.3
    this.vy = -0.25 - Math.random() * 0.35
    this.size = 6 + Math.random() * 18
    this.color = COLORS[Math.floor(Math.random() * COLORS.length)]
    this.life = 7000 + Math.random() * 5000
    this.maxLife = this.life
    this.seed = Math.random() * 10000
    this.wobbleFreq = 0.0006 + Math.random() * 0.001
    this.wobbleAmp = 0.3 + Math.random() * 0.6
    this.rotation = Math.random() * Math.PI * 2
    this.rotSpeed = (Math.random() - 0.5) * 0.015
    this.alphaMultiplier = 0.3 + Math.random() * 0.4
  }

  update(deltaTime) {
    const curl = curlNoise(this.x, this.y, this.seed)
    this.vx += curl.dx * 0.02
    this.vy += curl.dy * 0.015

    // Wobble
    const wobble = Math.sin(performance.now() * this.wobbleFreq + this.seed) * this.wobbleAmp
    this.x += (this.vx + wobble * 0.08) * deltaTime * 0.05
    this.y += this.vy * deltaTime * 0.05

    this.rotation += this.rotSpeed
    this.life -= deltaTime
    this.vx *= 0.998
    this.vy *= 0.998

    if (this.life <= 0 || this.y < -60) {
      this.reset(false)
    }
  }

  draw(ctx, breathValue) {
    const lifeRatio = this.life / this.maxLife
    const alpha = lifeRatio * this.alphaMultiplier * (0.25 + 0.75 * breathValue)

    ctx.save()
    ctx.translate(this.x, this.y)
    ctx.rotate(this.rotation)

    // Outer glow - large, very soft
    const glowGradient = ctx.createRadialGradient(0, 0, 0, 0, 0, this.size * 3)
    glowGradient.addColorStop(0, this.color.replace(/[\d.]+\)$/, `${alpha * 0.15})`))
    glowGradient.addColorStop(0.4, this.color.replace(/[\d.]+\)$/, `${alpha * 0.08})`))
    glowGradient.addColorStop(1, 'transparent')
    ctx.beginPath()
    ctx.arc(0, 0, this.size * 3, 0, Math.PI * 2)
    ctx.fillStyle = glowGradient
    ctx.fill()

    // Core gradient - soft
    const coreGradient = ctx.createRadialGradient(0, 0, 0, 0, 0, this.size)
    coreGradient.addColorStop(0, this.color.replace(/[\d.]+\)$/, `${alpha * 0.9})`))
    coreGradient.addColorStop(0.5, this.color.replace(/[\d.]+\)$/, `${alpha * 0.5})`))
    coreGradient.addColorStop(1, this.color.replace(/[\d.]+\)$/, `${alpha * 0.1})`))
    ctx.beginPath()
    ctx.arc(0, 0, this.size, 0, Math.PI * 2)
    ctx.fillStyle = coreGradient
    ctx.fill()

    // Inner bright core - small, subtle
    const coreAlpha = alpha * 0.4 * (0.5 + 0.5 * breathValue)
    ctx.beginPath()
    ctx.arc(0, 0, this.size * 0.2, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(220, 225, 230, ${coreAlpha})`
    ctx.fill()

    ctx.restore()
  }
}

const resizeCanvas = () => {
  if (!canvasRef.value) return
  canvasRef.value.width = window.innerWidth
  canvasRef.value.height = window.innerHeight
}

const init = () => {
  resizeCanvas()
  ctx = canvasRef.value.getContext('2d')

  particles = Array.from({ length: props.particleCount }, () => new QiParticle(
    canvasRef.value.width,
    canvasRef.value.height
  ))

  window.addEventListener('resize', resizeCanvas)
}

const animate = () => {
  if (!ctx) return

  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)

  particles.forEach(p => {
    p.update(16)
    p.draw(ctx, props.breathValue)
  })

  animationId = requestAnimationFrame(animate)
}

onMounted(() => {
  init()
  animate()
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<style scoped>
.particle-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 4;
  opacity: 0.6;
}
</style>
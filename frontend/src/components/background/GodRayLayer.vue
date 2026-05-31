<template>
  <canvas ref="canvasRef" class="god-ray-layer"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  breathValue: { type: Number, default: 0.5 },
  rayCount: { type: Number, default: 2 }
})

const canvasRef = ref(null)
let ctx = null
let animationId = null
let rays = []

class GodRay {
  constructor(index, total) {
    this.index = index
    // Position across the top with some randomness
    this.x = (window.innerWidth / (total + 1)) * (index + 1) + (Math.random() - 0.5) * 150
    this.y = -window.innerHeight * 0.2
    this.angle = -8 + Math.random() * 6
    this.length = window.innerHeight * 1.3 + Math.random() * window.innerHeight * 0.4
    this.width = 80 + Math.random() * 60
    this.phase = index * Math.PI * 1.5
    this.breathSpeed = 0.6 + Math.random() * 0.4
    this.baseAlpha = 0.08 + Math.random() * 0.06
  }

  draw(ctx, breathValue) {
    // Soft breathing effect
    const breathMultiplier = 0.4 + 0.6 * Math.sin(this.phase + breathValue * this.breathSpeed * Math.PI * 2)
    const alpha = this.baseAlpha * breathMultiplier

    ctx.save()
    ctx.translate(this.x, this.y)
    ctx.rotate(this.angle * Math.PI / 180)

    // Main ray shaft - soft gradient, no harsh edges
    const gradient = ctx.createLinearGradient(0, 0, 0, this.length)
    gradient.addColorStop(0, `rgba(220, 225, 230, ${alpha})`)
    gradient.addColorStop(0.1, `rgba(200, 210, 220, ${alpha * 0.7})`)
    gradient.addColorStop(0.4, `rgba(150, 170, 180, ${alpha * 0.4})`)
    gradient.addColorStop(0.7, `rgba(100, 120, 140, ${alpha * 0.2})`)
    gradient.addColorStop(1, 'transparent')

    ctx.fillStyle = gradient
    ctx.filter = 'blur(30px)'
    ctx.beginPath()
    ctx.moveTo(-this.width / 2, 0)
    ctx.lineTo(this.width / 2, 0)
    ctx.lineTo(this.width * 0.2, this.length)
    ctx.lineTo(-this.width * 0.2, this.length)
    ctx.closePath()
    ctx.fill()

    // Inner brighter core
    const coreAlpha = alpha * 0.5
    const coreGradient = ctx.createLinearGradient(0, 0, 0, this.length * 0.6)
    coreGradient.addColorStop(0, `rgba(230, 235, 240, ${coreAlpha})`)
    coreGradient.addColorStop(0.5, `rgba(200, 210, 220, ${coreAlpha * 0.5})`)
    coreGradient.addColorStop(1, 'transparent')

    ctx.fillStyle = coreGradient
    ctx.filter = 'blur(15px)'
    ctx.beginPath()
    ctx.moveTo(-this.width * 0.25, 0)
    ctx.lineTo(this.width * 0.25, 0)
    ctx.lineTo(this.width * 0.1, this.length * 0.6)
    ctx.lineTo(-this.width * 0.1, this.length * 0.6)
    ctx.closePath()
    ctx.fill()

    ctx.filter = 'none'
    ctx.restore()
  }
}

class DustParticle {
  constructor() {
    this.reset()
  }

  reset() {
    this.x = (Math.random() - 0.5) * 200
    this.y = Math.random() * window.innerHeight * 1.5
    this.size = 0.5 + Math.random() * 1.5
    this.speed = 0.15 + Math.random() * 0.25
    this.wobble = Math.random() * Math.PI * 2
    this.wobbleSpeed = 0.01 + Math.random() * 0.02
    this.alpha = 0.15 + Math.random() * 0.25
  }

  update() {
    this.y -= this.speed
    this.wobble += this.wobbleSpeed
    this.x += Math.sin(this.wobble) * 0.3

    if (this.y < -20) {
      this.y = window.innerHeight * 1.5
      this.x = (Math.random() - 0.5) * 150
    }
  }

  draw(ctx, rayX, rayAngle, breathMultiplier) {
    const px = rayX + this.x * Math.cos(rayAngle * Math.PI / 180)
    const py = this.y * Math.cos(rayAngle * Math.PI / 180)

    ctx.beginPath()
    ctx.arc(px, py, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(220, 225, 230, ${this.alpha * breathMultiplier})`
    ctx.fill()
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

  rays = []
  for (let i = 0; i < props.rayCount; i++) {
    const dustCount = 8 + Math.floor(Math.random() * 8)
    rays.push({
      ray: new GodRay(i, props.rayCount),
      dustParticles: Array.from({ length: dustCount }, () => new DustParticle())
    })
  }

  window.addEventListener('resize', resizeCanvas)
}

const animate = () => {
  if (!ctx) return

  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)

  const breathMultiplier = 0.3 + 0.7 * props.breathValue

  rays.forEach(({ ray, dustParticles }) => {
    ray.draw(ctx, props.breathValue)

    dustParticles.forEach(p => {
      p.update()
      p.draw(ctx, ray.x, ray.angle, breathMultiplier)
    })
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
.god-ray-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 5;
  opacity: 0.5;
}
</style>
<template>
  <canvas ref="canvasRef" class="cloud-layer"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  breathValue: { type: Number, default: 0.5 },
  cloudCount: { type: Number, default: 3 }
})

const canvasRef = ref(null)
let ctx = null
let animationId = null
let clouds = []
let time = 0

// Simplex noise implementation
const noise = (() => {
  const F2 = 0.5 * (Math.sqrt(3) - 1)
  const G2 = (3 - Math.sqrt(3)) / 6

  function hash(x, y) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453
    return n - Math.floor(n)
  }

  return function(x, y) {
    const s = (x + y) * F2
    const i = Math.floor(x + s)
    const j = Math.floor(y + s)
    const t = (i + j) * G2
    const X0 = i - t
    const Y0 = j - t
    const x0 = x - X0
    const y0 = y - Y0

    const i1 = x0 > y0 ? 1 : 0
    const j1 = x0 > y0 ? 0 : 1

    const x1 = x0 - i1 + G2
    const y1 = y0 - j1 + G2
    const x2 = x0 - 1 + 2 * G2
    const y2 = y0 - 1 + 2 * G2

    const grad = (hash, x, y) => {
      const h = hash & 7
      const u = h < 4 ? x : y
      const v = h < 4 ? y : x
      return ((h & 1) ? -u : u) + ((h & 2) ? -2 * v : 2 * v)
    }

    let n0, n1, n2
    let t0 = 0.5 - x0 * x0 - y0 * y0
    if (t0 < 0) n0 = 0
    else {
      t0 *= t0
      n0 = t0 * t0 * grad(hash(i, j), x0, y0)
    }

    let t1 = 0.5 - x1 * x1 - y1 * y1
    if (t1 < 0) n1 = 0
    else {
      t1 *= t1
      n1 = t1 * t1 * grad(hash(i + i1, j + j1), x1, y1)
    }

    let t2 = 0.5 - x2 * x2 - y2 * y2
    if (t2 < 0) n2 = 0
    else {
      t2 *= t2
      n2 = t2 * t2 * grad(hash(i + 1, j + 1), x2, y2)
    }

    return 70 * (n0 + n1 + n2)
  }
})()

// Fractal Brownian Motion for organic cloud shape
const fbm = (x, y, octaves = 5) => {
  let value = 0
  let amplitude = 0.5
  let frequency = 1

  for (let i = 0; i < octaves; i++) {
    value += amplitude * Math.abs(noise(x * frequency, y * frequency))
    amplitude *= 0.5
    frequency *= 2
  }
  return value
}

class OrganicCloud {
  constructor(index, total) {
    this.index = index
    this.baseWidth = 400 + Math.random() * 500
    this.baseHeight = 180 + Math.random() * 150
    this.width = this.baseWidth
    this.height = this.baseHeight
    this.x = -this.baseWidth
    this.y = window.innerHeight * (0.28 + index * 0.12) + Math.random() * 80
    this.speed = 0.08 + Math.random() * 0.12
    this.direction = 1
    this.seed = Math.random() * 1000
    this.phase = Math.random() * Math.PI * 2
    this.floatSpeed = 0.25 + Math.random() * 0.3
    this.floatAmp = 8 + Math.random() * 12
    this.baseY = this.y
  }

  update(canvasWidth) {
    this.x += this.speed * this.direction

    if (this.x > canvasWidth + 50) {
      this.x = -this.width - 100
    }
  }

  draw(ctx, time, breathValue) {
    const w = this.width
    const h = this.height
    const scale = 0.0025
    const timeOffset = time * 0.00002 * this.speed

    ctx.save()

    // Floating motion
    const floatY = Math.sin(time * this.floatSpeed * 0.001 + this.phase) * this.floatAmp
    ctx.translate(this.x + w * 0.5, this.baseY + floatY + h * 0.5)

    // Draw cloud with noise-based organic shape
    const steps = 64
    const points = []

    for (let i = 0; i < steps; i++) {
      const angle = (i / steps) * Math.PI * 2
      const nx = Math.cos(angle)
      const ny = Math.sin(angle)

      // Get radius using fbm for organic shape
      let radius = 0.4 + fbm(
        nx * 2.5 + timeOffset + this.seed,
        ny * 2.5 + this.seed,
        5
      ) * 0.7

      // Soft edges
      const edgeNoise = noise(nx * 4 + timeOffset * 0.5, ny * 4) * 0.15
      radius += edgeNoise

      // Make it flatter (oval)
      radius *= 0.7 + ny * 0.15

      const px = nx * radius * w * 0.5
      const py = ny * radius * h * 0.5
      points.push({ x: px, y: py })
    }

    // Draw shadow layer (very subtle)
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y + 15)
    points.forEach((p, i) => {
      if (i > 0) {
        const prev = points[i - 1]
        const curr = p
        const cpx = (prev.x + curr.x) * 0.5 + (Math.random() - 0.5) * 5
        const cpy = (prev.y + curr.y) * 0.5 + 15 + (Math.random() - 0.5) * 3
        ctx.quadraticCurveTo(prev.x, prev.y, cpx, cpy)
      }
    })
    ctx.closePath()
    ctx.fillStyle = 'rgba(20, 30, 40, 0.2)'
    ctx.filter = 'blur(25px)'
    ctx.fill()
    ctx.filter = 'none'

    // Draw main cloud layers (outside to inside)
    const layers = [
      { offset: -12, alpha: 0.08, blur: 35, color: [60, 80, 95] },
      { offset: -6, alpha: 0.12, blur: 25, color: [80, 100, 115] },
      { offset: 0, alpha: 0.15, blur: 15, color: [100, 120, 135] }
    ]

    layers.forEach(layer => {
      ctx.beginPath()
      ctx.moveTo(points[0].x + layer.offset * 0.3, points[0].y + layer.offset * 0.5)
      points.forEach((p, i) => {
        if (i > 0) {
          const prev = points[i - 1]
          const curr = p
          const cpx = (prev.x + curr.x) * 0.5 + layer.offset * 0.2
          const cpy = (prev.y + curr.y) * 0.5 + layer.offset * 0.4
          ctx.quadraticCurveTo(prev.x + layer.offset * 0.3, prev.y + layer.offset * 0.5, cpx, cpy)
        }
      })
      ctx.closePath()
      ctx.fillStyle = `rgba(${layer.color.join(',')}, ${layer.alpha * (0.4 + 0.6 * breathValue)})`
      ctx.filter = `blur(${layer.blur}px)`
      ctx.fill()
    })

    // Highlight spots (subtle)
    const highlightAlpha = 0.12 * (0.3 + 0.7 * breathValue)
    ctx.beginPath()
    ctx.arc(-w * 0.15, -h * 0.2, w * 0.18, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(220, 225, 230, ${highlightAlpha})`
    ctx.filter = 'blur(20px)'
    ctx.fill()

    ctx.beginPath()
    ctx.arc(w * 0.1, -h * 0.1, w * 0.1, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(200, 210, 220, ${highlightAlpha * 0.7})`
    ctx.filter = 'blur(15px)'
    ctx.fill()

    ctx.filter = 'none'
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

  clouds = Array.from({ length: props.cloudCount }, (_, i) => new OrganicCloud(i, props.cloudCount))

  window.addEventListener('resize', resizeCanvas)
}

const animate = () => {
  if (!ctx) return

  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)

  time = performance.now()

  clouds.forEach(cloud => {
    cloud.update(canvasRef.value.width)
    cloud.draw(ctx, time, props.breathValue)
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
.cloud-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 3;
  opacity: 0.7;
}
</style>
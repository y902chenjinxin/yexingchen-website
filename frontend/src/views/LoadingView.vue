<template>
  <div class="loading-page">
    <canvas ref="canvasRef" class="loading-canvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { random, randFloat } from '@/utils/random'

const emit = defineEmits(['loaded'])
const canvasRef = ref(null)

// 粒子配置
const PARTICLE_COUNT = 80
const SNAKE_LENGTH = 60
const TAIL_TRAIL = 25

// 进度
const progress = ref(0)
let animationId = null

// 粒子数组
let particles = []
let snakeParticles = []
let stars = []

// 蛇的路径点
let pathPoints = []
let currentPathProgress = 0

// 颜色配置 - 低饱和度青色
const COLORS = {
  bg: '#0a1218',
  star: 'rgba(200, 220, 240, 0.8)',
  snake: 'rgba(127, 255, 212, 0.6)',
  trail: 'rgba(127, 255, 212, 0.2)',
  mist: 'rgba(180, 200, 220, 0.1)'
}

class Particle {
  constructor(x, y, type = 'free') {
    this.x = x
    this.y = y
    this.type = type
    this.vx = (random() - 0.5) * 0.5
    this.vy = (random() - 0.5) * 0.5
    this.life = 1
    this.decay = 0.01 + random() * 0.02
    this.size = 1 + random() * 2
    this.alpha = 0.3 + random() * 0.5
  }

  update() {
    this.x += this.vx
    this.y += this.vy
    this.life -= this.decay
    this.alpha = this.life * 0.5
  }

  draw(ctx) {
    if (this.life <= 0) return
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(127, 255, 212, ${this.alpha})`
    ctx.fill()
  }
}

class Star {
  constructor(canvas) {
    this.x = random() * canvas.width
    this.y = random() * canvas.height
    this.size = 0.5 + random() * 1.5
    this.twinkle = random() * Math.PI * 2
    this.twinkleSpeed = 0.02 + random() * 0.03
    this.baseAlpha = 0.3 + random() * 0.5
  }

  update() {
    this.twinkle += this.twinkleSpeed
  }

  draw(ctx) {
    const alpha = this.baseAlpha * (0.5 + 0.5 * Math.sin(this.twinkle))
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(200, 220, 240, ${alpha})`
    ctx.fill()
  }
}

function initStars(canvas, count = 150) {
  stars = []
  for (let i = 0; i < count; i++) {
    stars.push(new Star(canvas))
  }
}

function initPath(canvas) {
  // 创建蛇游动的曲线路径 - 从左侧蜿蜒进入，盘踞成圆
  const centerX = canvas.width / 2
  const centerY = canvas.height / 2
  const radius = Math.min(canvas.width, canvas.height) * 0.25

  pathPoints = []

  // 左侧进入的蜿蜒路径
  for (let i = 0; i < 50; i++) {
    const t = i / 50
    const x = -50 + t * (centerX + 100)
    const y = centerY + Math.sin(t * Math.PI * 3) * 80
    pathPoints.push({ x, y })
  }

  // 盘踞成圆形
  for (let i = 0; i <= 36; i++) {
    const angle = (i / 36) * Math.PI * 2 - Math.PI / 2
    const x = centerX + Math.cos(angle) * radius
    const y = centerY + Math.sin(angle) * radius
    pathPoints.push({ x, y })
  }
}

function getPointOnPath(progress) {
  const totalPoints = pathPoints.length
  const idx = Math.floor(progress * totalPoints) % totalPoints
  const nextIdx = (idx + 1) % totalPoints
  const t = (progress * totalPoints) % 1

  const p1 = pathPoints[idx]
  const p2 = pathPoints[nextIdx]

  return {
    x: p1.x + (p2.x - p1.x) * t,
    y: p1.y + (p2.y - p1.y) * t
  }
}

function updateSnake() {
  // 更新蛇身位置
  for (let i = snakeParticles.length - 1; i > 0; i--) {
    snakeParticles[i].x = snakeParticles[i - 1].x
    snakeParticles[i].y = snakeParticles[i - 1].y
  }

  // 蛇头跟随路径 - 加快速度以在0.4s内完成
  if (currentPathProgress < 1) {
    currentPathProgress += 0.04
    const head = getPointOnPath(currentPathProgress)
    if (snakeParticles.length > 0) {
      snakeParticles[0].x = head.x
      snakeParticles[0].y = head.y
    }
  }

  // 蛇头位置更新
  progress.value = Math.min(currentPathProgress, 1)

  // 添加拖尾粒子
  if (Math.random() < 0.3 && snakeParticles.length > 0) {
    const tail = snakeParticles[snakeParticles.length - 1]
    particles.push(new Particle(tail.x, tail.y, 'trail'))
  }
}

function drawStars(ctx) {
  stars.forEach(star => {
    star.update()
    star.draw(ctx)
  })
}

function drawMist(ctx, canvas) {
  // 底部云雾
  const gradient = ctx.createLinearGradient(0, canvas.height * 0.6, 0, canvas.height)
  gradient.addColorStop(0, 'rgba(180, 200, 220, 0)')
  gradient.addColorStop(1, 'rgba(180, 200, 220, 0.15)')
  ctx.fillStyle = gradient
  ctx.fillRect(0, canvas.height * 0.6, canvas.width, canvas.height * 0.4)
}

function drawSnake(ctx) {
  // 绘制蛇身粒子
  for (let i = 0; i < snakeParticles.length; i++) {
    const p = snakeParticles[i]
    const ratio = i / snakeParticles.length
    const size = 3 + (1 - ratio) * 4
    const alpha = 0.4 + ratio * 0.4

    // 发光效果
    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, size * 3)
    glow.addColorStop(0, `rgba(127, 255, 212, ${alpha})`)
    glow.addColorStop(0.5, `rgba(127, 255, 212, ${alpha * 0.3})`)
    glow.addColorStop(1, 'rgba(127, 255, 212, 0)')

    ctx.beginPath()
    ctx.arc(p.x, p.y, size * 3, 0, Math.PI * 2)
    ctx.fillStyle = glow
    ctx.fill()

    // 核心点
    ctx.beginPath()
    ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(200, 255, 230, ${alpha})`
    ctx.fill()
  }

  // 绘制蛇头（更亮）
  if (snakeParticles.length > 0) {
    const head = snakeParticles[0]
    const headGlow = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 20)
    headGlow.addColorStop(0, 'rgba(127, 255, 212, 0.8)')
    headGlow.addColorStop(0.3, 'rgba(127, 255, 212, 0.3)')
    headGlow.addColorStop(1, 'rgba(127, 255, 212, 0)')

    ctx.beginPath()
    ctx.arc(head.x, head.y, 20, 0, Math.PI * 2)
    ctx.fillStyle = headGlow
    ctx.fill()
  }
}

function drawParticles(ctx) {
  particles.forEach(p => {
    p.update()
    p.draw(ctx)
  })
  particles = particles.filter(p => p.life > 0)
}

function drawProgressRing(ctx, canvas, centerX, centerY, radius) {
  if (progress.value < 0.3) return

  const ringProgress = (progress.value - 0.3) / 0.7
  const startAngle = -Math.PI / 2
  const endAngle = startAngle + ringProgress * Math.PI * 2

  // 外圈发光
  ctx.beginPath()
  ctx.arc(centerX, centerY, radius + 5, startAngle, endAngle)
  ctx.strokeStyle = 'rgba(127, 255, 212, 0.2)'
  ctx.lineWidth = 8
  ctx.stroke()

  // 主圈
  ctx.beginPath()
  ctx.arc(centerX, centerY, radius, startAngle, endAngle)
  ctx.strokeStyle = 'rgba(127, 255, 212, 0.6)'
  ctx.lineWidth = 3
  ctx.stroke()

  // 进度点
  if (ringProgress < 1) {
    const px = centerX + Math.cos(endAngle) * radius
    const py = centerY + Math.sin(endAngle) * radius

    const pointGlow = ctx.createRadialGradient(px, py, 0, px, py, 15)
    pointGlow.addColorStop(0, 'rgba(127, 255, 212, 1)')
    pointGlow.addColorStop(0.5, 'rgba(127, 255, 212, 0.5)')
    pointGlow.addColorStop(1, 'rgba(127, 255, 212, 0)')

    ctx.beginPath()
    ctx.arc(px, py, 15, 0, Math.PI * 2)
    ctx.fillStyle = pointGlow
    ctx.fill()
  }
}

function drawText(ctx, canvas, text, fontSize, color, y) {
  ctx.font = `${fontSize}px "STKaiti", "KaiTi", serif`
  ctx.fillStyle = color
  ctx.textAlign = 'center'
  ctx.fillText(text, canvas.width / 2, y)
}

function render() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const centerX = canvas.width / 2
  const centerY = canvas.height / 2

  // 清空画布
  ctx.fillStyle = COLORS.bg
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // 绘制星空
  drawStars(ctx)

  // 绘制云雾
  drawMist(ctx, canvas)

  // 更新蛇位置
  updateSnake()

  // 绘制蛇
  drawSnake(ctx)

  // 绘制粒子
  drawParticles(ctx)

  // 绘制进度环（蛇盘踞成圆后）
  if (progress.value > 0.3) {
    const ringRadius = Math.min(canvas.width, canvas.height) * 0.25
    drawProgressRing(ctx, canvas, centerX, centerY, ringRadius)
  }

  // 加载文字
  if (progress.value < 0.5) {
    drawText(ctx, canvas, '灵蛇入境', 24, 'rgba(127, 255, 212, 0.6)', canvas.height * 0.75)
  } else if (progress.value < 0.8) {
    drawText(ctx, canvas, '凝聚灵气', 24, 'rgba(127, 255, 212, 0.6)', canvas.height * 0.75)
  } else {
    drawText(ctx, canvas, '洞天将开', 24, 'rgba(127, 255, 212, 0.8)', canvas.height * 0.75)
  }

  // 完成动画
  if (progress.value >= 1) {
    // 消散效果
    ctx.fillStyle = 'rgba(10, 18, 24, 0.05)'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // 淡出
    setTimeout(() => {
      emit('loaded')
    }, 500)
  } else {
    animationId = requestAnimationFrame(render)
  }
}

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return

  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  // 重新初始化路径
  initPath(canvas)
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return

  resizeCanvas()
  initStars(canvas)

  // 初始化蛇粒子
  snakeParticles = []
  for (let i = 0; i < SNAKE_LENGTH; i++) {
    snakeParticles.push({ x: -100, y: 0 })
  }

  // 开始动画
  render()

  // 监听窗口大小变化
  window.addEventListener('resize', resizeCanvas)
})

// 清理函数
defineExpose({
  cleanup: () => {
    if (animationId) {
      cancelAnimationFrame(animationId)
    }
    window.removeEventListener('resize', resizeCanvas)
  }
})

// 组件卸载时清理
onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<style scoped>
.loading-page {
  position: fixed;
  inset: 0;
  background: #0a1218;
  z-index: 9999;
}

.loading-canvas {
  width: 100%;
  height: 100%;
}
</style>
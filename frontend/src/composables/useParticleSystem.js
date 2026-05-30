/**
 * useParticleSystem.js
 * 粒子系统 composable - 用于鼠标轨迹、灵气效果、流星等
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useParticleSystem(canvasRef, options = {}) {
  const {
    particleCount = 30,
    colors = ['rgba(201, 169, 98, 0.6)', 'rgba(74, 124, 89, 0.5)'],
    lifetime = 1200,
    speed = 1,
    size = 3,
    maxParticles = 50
  } = options

  const particles = ref([])
  const isActive = ref(false)
  const intensity = ref(1)  // 0-1 用于音频驱动

  let ctx = null
  let animationFrame = null
  let lastTime = 0

  // 种子随机（保证连贯性）
  const seededRandom = (seed) => {
    const x = Math.sin(seed * 12.9898) * 43758.5453
    return x - Math.floor(x)
  }

  class Particle {
    constructor(x, y, options = {}) {
      this.x = x
      this.y = y
      this.vx = options.vx || (Math.random() - 0.5) * 2 * speed
      this.vy = options.vy || (Math.random() - 0.5) * 2 * speed
      this.size = options.size || size * (0.5 + seededRandom(Date.now() % 1000) * 0.5)
      this.color = options.color || colors[Math.floor(Math.random() * colors.length)]
      this.life = lifetime
      this.maxLife = lifetime
      this.seed = Date.now() % 10000 + Math.random() * 1000
    }

    update(deltaTime) {
      // 使用种子随机产生微弱的自然运动
      const driftX = (seededRandom(this.seed++) - 0.5) * 0.3
      const driftY = (seededRandom(this.seed++) - 0.5) * 0.3

      this.x += (this.vx + driftX) * intensity.value
      this.y += (this.vy + driftY) * intensity.value
      this.life -= deltaTime

      // 稍微减速
      this.vx *= 0.99
      this.vy *= 0.99
    }

    draw(ctx) {
      const lifeRatio = this.life / this.maxLife
      const currentSize = this.size * lifeRatio

      ctx.beginPath()
      ctx.arc(this.x, this.y, currentSize, 0, Math.PI * 2)
      ctx.fillStyle = this.color.replace(/[\d.]+\)$/, `${lifeRatio * 0.8})`)
      ctx.fill()

      // 发光效果
      ctx.beginPath()
      ctx.arc(this.x, this.y, currentSize * 2, 0, Math.PI * 2)
      ctx.fillStyle = this.color.replace(/[\d.]+\)$/, `${lifeRatio * 0.2})`)
      ctx.fill()
    }

    isDead() {
      return this.life <= 0
    }
  }

  const init = () => {
    if (!canvasRef.value) return

    const canvas = canvasRef.value
    ctx = canvas.getContext('2d')

    // 设置画布尺寸
    const updateSize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    updateSize()
    window.addEventListener('resize', updateSize)

    isActive.value = true
    lastTime = performance.now()
    animate()
  }

  const animate = () => {
    if (!isActive.value) return

    const now = performance.now()
    const deltaTime = now - lastTime
    lastTime = now

    // 清除画布（带淡出效果）
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)

    // 更新所有粒子
    particles.value.forEach(p => p.update(deltaTime))

    // 绘制所有粒子
    particles.value.forEach(p => p.draw(ctx))

    // 移除死亡粒子
    particles.value = particles.value.filter(p => !p.isDead())

    animationFrame = requestAnimationFrame(animate)
  }

  // 添加单个粒子
  const emit = (x, y, options = {}) => {
    if (particles.value.length >= maxParticles) {
      // 移除最老的粒子
      particles.value.shift()
    }

    const particle = new Particle(x, y, options)
    particles.value.push(particle)
  }

  // 批量添加粒子
  const emitBurst = (x, y, count = 10) => {
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2
      const speed = 2 + Math.random() * 2
      emit(x, y, {
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed
      })
    }
  }

  // 设置强度（用于音频驱动）
  const setIntensity = (value) => {
    intensity.value = Math.max(0, Math.min(1, value))
  }

  // 清除所有粒子
  const clear = () => {
    particles.value = []
  }

  const pause = () => {
    isActive.value = false
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }
  }

  const resume = () => {
    if (!isActive.value) {
      isActive.value = true
      lastTime = performance.now()
      animate()
    }
  }

  onMounted(() => {
    init()
  })

  onUnmounted(() => {
    pause()
  })

  return {
    particles,
    isActive,
    intensity,
    emit,
    emitBurst,
    setIntensity,
    clear,
    pause,
    resume
  }
}
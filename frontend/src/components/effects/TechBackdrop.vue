<template>
  <canvas ref="cv" class="tech-backdrop" aria-hidden="true"></canvas>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const cv = ref(null)
let ctx = null
let raf = 0
let particles = []
let w = 0
let h = 0
let dpr = 1
let running = true

const CYAN = '45,226,255'
const VIOLET = '185,139,255'
const BLUE = '106,139,255'

function resize() {
  const el = cv.value
  if (!el) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  // 🔴 clientWidth / clientHeight 是**只读**的计算值：给它们赋值会在严格模式（ES module）
  // 直接抛 TypeError —— 而这里在 onMounted 里调用，异常会中断后续渲染，表现为**整页空白**
  // （v2.46.126 引入，v2.46.135 巡检移动端时才发现：/contacts?m=1 全页空、控制台
  //  "Cannot set property clientWidth of #<Element> which has only a getter"）。
  // 画布尺寸要写 canvas.width / canvas.height（这两个才是可写的）。
  w = window.innerWidth
  h = window.innerHeight
  el.width = Math.round(w * dpr)
  el.height = Math.round(h * dpr)
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  seed()
}

function seed() {
  // 粒子数量随面积收敛，避免移动端/低端机过载
  const count = Math.max(28, Math.min(90, Math.round((w * h) / 26000)))
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.18,
    vy: (Math.random() - 0.5) * 0.18,
    r: Math.random() * 1.6 + 0.6,
    c: [CYAN, VIOLET, BLUE][Math.floor(Math.random() * 3)],
  }))
}

function step() {
  if (!running) return
  ctx.clearRect(0, 0, w, h)
  for (const p of particles) {
    p.x += p.vx
    p.y += p.vy
    if (p.x < -10) p.x = w + 10
    if (p.x > w + 10) p.x = -10
    if (p.y < -10) p.y = h + 10
    if (p.y > h + 10) p.y = -10
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${p.c},0.75)`
    ctx.shadowBlur = 8
    ctx.shadowColor = `rgba(${p.c},0.9)`
    ctx.fill()
  }
  // 近邻连线（克制：仅短距）
  ctx.shadowBlur = 0
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const a = particles[i], b = particles[j]
      const dx = a.x - b.x, dy = a.y - b.y
      const d2 = dx * dx + dy * dy
      if (d2 < 14000) {
        const o = (1 - d2 / 14000) * 0.18
        ctx.strokeStyle = `rgba(${CYAN},${o})`
        ctx.lineWidth = 0.6
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
      }
    }
  }
  raf = requestAnimationFrame(step)
}

function start() {
  if (!cv.value) return
  ctx = cv.value.getContext('2d')
  resize()
  if (!window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    running = true
    step()
  } else {
    // 减少动态效果：只画一帧静态图，不排下一帧。
    // （原写法 running=false 后再 step()，会被开头的 `if (!running) return` 直接吃掉 → 一帧都没有）
    running = true
    step()
    running = false
    if (raf) { cancelAnimationFrame(raf); raf = 0 }
  }
}

let rt = 0
function onResize() {
  clearTimeout(rt)
  rt = setTimeout(resize, 200)
}

onMounted(() => {
  start()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  running = false
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.tech-backdrop {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  pointer-events: none;
}
</style>

<template>
  <DeviceGate need="phone" title="请在手机上打开 3D 粒子">
    <div class="p3d">
      <canvas ref="cv" class="cv" />

      <header class="hd">
        <button type="button" class="back" aria-label="返回" @click="onBack">
          <svg viewBox="0 0 24 24"><path d="M15.4 7.4 14 6l-6 6 6 6 1.4-1.4L10.8 12z" /></svg>
        </button>
        <span class="hd-title">3D 粒子</span>
        <span class="hd-hint">{{ MODES[mode].hint }}</span>
      </header>

      <nav class="modes">
        <button v-for="(m, key) in MODES" :key="key" type="button" class="pill"
                :class="{ on: mode === key }" @click="setMode(key)">
          {{ m.label }}
        </button>
      </nav>

      <transition name="fade">
        <div v-if="toast" class="toast">{{ toast }}</div>
      </transition>
    </div>
  </DeviceGate>
</template>

<script setup>
/**
 * 3D 粒子（v2.46.360）
 *
 * 照夜星的定论重做：「不要魔幻液体，我就要个 3D 粒子」。
 *
 * ## 这次的路线（和上一版失败的复刻划清界限）
 * 不再手写渲染管线，全交给 **three.js**（0.184，几万项目验证过）：
 * 透视相机 / 深度 / 点精灵 / 触屏轨道控制都是库的事，我只写粒子本身。
 * 三个效果都是社区验证过的经典配方，不做 8 档大而全 —— 每个都是完成品。
 *
 *   1. 星系 galaxy：螺旋星系生成器（branches/spin/randomness + 内外色渐变）
 *   2. 原子 atom：三条不同法向的轨道环 + 中心呼吸核 + 球壳星尘
 *   3. 爆发 burst：点哪炸哪，球面速度 + 阻尼 + 微弱向心，寿命渐隐
 *
 * 交互：单指拖 = 旋转视角，双指捏合 = 缩放（OrbitControls 原生支持）；
 * 爆发模式下「短点」（<280ms 且位移 <10px）= 发射，拖动仍然是转视角。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import DeviceGate from '@/components/common/DeviceGate.vue'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import { tick } from '@/utils/haptic'

const router = useRouter()
const cv = ref(null)

// 全屏壳（隐藏 tabbar/音乐条）；绝不能调 exit()，返回走 router.back()
useFullscreenPage()

const MODES = {
  galaxy: { label: '星系', hint: '单指拖转 · 双指缩放' },
  atom: { label: '原子', hint: '单指拖转 · 双指缩放' },
  burst: { label: '爆发', hint: '点屏幕发射 · 拖动旋转' },
}
const mode = ref('galaxy')
const toast = ref('')

let renderer = null
let scene = null
let camera = null
let controls = null
let raf = 0
let lastT = 0
let group = null          // 当前效果的 Points 容器
let updater = null        // 每帧更新函数（可选）
const clock = { t: 0 }

// ---------------- 公共小件 ----------------

/** 径向渐变圆点贴图：发光粒子的标准做法 */
function makeGlowTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const ctx = c.getContext('2d')
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32)
  g.addColorStop(0, 'rgba(255,255,255,1)')
  g.addColorStop(0.3, 'rgba(255,255,255,0.55)')
  g.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, 64, 64)
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

let glowTex = null

/**
 * 统一的点精灵材质：per-point 颜色 + 尺寸，加法混合。
 * gl_PointSize 按透视距离衰减（aSize * uScale / -z），远小近大才有 3D 感。
 */
function makePointsMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: {
      uMap: { value: glowTex },
      uScale: { value: 300 * Math.min(2, window.devicePixelRatio || 1) },
    },
    vertexShader: `
      attribute float aSize;
      attribute vec3 aColor;
      uniform float uScale;
      varying vec3 vColor;
      void main() {
        vColor = aColor;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = aSize * uScale / max(0.2, -mv.z);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      uniform sampler2D uMap;
      varying vec3 vColor;
      void main() {
        float a = texture2D(uMap, gl_PointCoord).a;
        if (a < 0.01) discard;
        gl_FragColor = vec4(vColor * a, a);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })
}

function disposeGroup() {
  if (!group) return
  group.traverse((o) => {
    if (o.geometry) o.geometry.dispose()
    if (o.material) o.material.dispose()
  })
  scene.remove(group)
  group = null
  updater = null
}

function addPoints(geo, mat) {
  const pts = new THREE.Points(geo, mat)
  // 🔴 burst 档初始 position 全在 (9999,9999,9999)（死粒子藏远处），
  // 包围球算在远处、之后挪回原点也不会重算 → 默认的视锥剔除把整个
  // Points 剔掉（数据活着、画面全黑）。这类自己管理包围球的点云一律关掉剔除。
  pts.frustumCulled = false
  group.add(pts)
  return pts
}

// ---------------- 1. 星系 ----------------

function buildGalaxy() {
  const N = 18000
  const RADIUS = 5
  const BRANCHES = 4
  const SPIN = 1.15
  const RANDOM = 0.38
  const POWER = 3.2
  const inside = new THREE.Color('#ffb066')
  const outside = new THREE.Color('#4472e0')

  const pos = new Float32Array(N * 3)
  const col = new Float32Array(N * 3)
  const size = new Float32Array(N)
  const c = new THREE.Color()
  for (let i = 0; i < N; i++) {
    const r = Math.random() * RADIUS
    const branch = ((i % BRANCHES) / BRANCHES) * Math.PI * 2
    const spinA = r * SPIN
    const rand = () => Math.pow(Math.random(), POWER) * (Math.random() < 0.5 ? 1 : -1) * RANDOM * (r + 0.25)
    pos[i * 3] = Math.cos(branch + spinA) * r + rand()
    pos[i * 3 + 1] = rand() * 0.55
    pos[i * 3 + 2] = Math.sin(branch + spinA) * r + rand()
    c.lerpColors(inside, outside, Math.min(1, r / RADIUS))
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
    // 中心密、外围亮星点缀：尺寸随半径轻微变大 + 随机
    size[i] = 0.026 + Math.random() * 0.022 + (r > RADIUS * 0.8 ? 0.02 : 0)
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3))
  geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1))
  addPoints(geo, makePointsMaterial())

  camera.position.set(0, 2.6, 5.4)
  camera.lookAt(0, 0, 0)
  controls.target.set(0, 0, 0)
  updater = (dt) => { group.rotation.y += dt * 0.12 }
}

// ---------------- 2. 原子 ----------------

function buildAtom() {
  // 中心呼吸核：小球状点云
  {
    const N = 420
    const pos = new Float32Array(N * 3)
    const col = new Float32Array(N * 3)
    const size = new Float32Array(N)
    const c = new THREE.Color('#ffe9b8')
    for (let i = 0; i < N; i++) {
      // 球内均匀分布（r = R * cbrt(u)）
      const r = 0.34 * Math.cbrt(Math.random())
      const th = Math.random() * Math.PI * 2
      const ph = Math.acos(2 * Math.random() - 1)
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th)
      pos[i * 3 + 1] = r * Math.cos(ph)
      pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th)
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
      size[i] = 0.05 + Math.random() * 0.05
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3))
    geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1))
    addPoints(geo, makePointsMaterial())
  }

  // 三条轨道环：不同法向 + 环上粒子沿环流动
  const rings = [
    { r: 1.15, tilt: [Math.PI / 2.35, 0, 0.35], color: '#7cf3d0', n: 240, speed: 0.9 },
    { r: 1.62, tilt: [Math.PI / 2.6, 0.9, -0.5], color: '#9b8cff', n: 240, speed: -0.7 },
    { r: 2.1, tilt: [Math.PI / 2.1, -0.8, 0.9], color: '#ff8fb8', n: 260, speed: 0.55 },
  ]
  const moving = []
  for (const rg of rings) {
    const pos = new Float32Array(rg.n * 3)
    const col = new Float32Array(rg.n * 3)
    const size = new Float32Array(rg.n)
    const phases = new Float32Array(rg.n)
    const c = new THREE.Color(rg.color)
    for (let i = 0; i < rg.n; i++) {
      phases[i] = (i / rg.n) * Math.PI * 2 + Math.random() * 0.3
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
      size[i] = 0.045 + Math.random() * 0.045
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3))
    geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1))
    const holder = new THREE.Group()
    holder.rotation.set(...rg.tilt)
    const pts = new THREE.Points(geo, makePointsMaterial())
    holder.add(pts)
    group.add(holder)
    moving.push({ geo, phases, r: rg.r, speed: rg.speed })
  }

  // 外层球壳星尘（背景深度感）
  {
    const N = 700
    const pos = new Float32Array(N * 3)
    const col = new Float32Array(N * 3)
    const size = new Float32Array(N)
    const c = new THREE.Color('#88a8ff')
    for (let i = 0; i < N; i++) {
      const r = 3.4 + Math.random() * 2.2
      const th = Math.random() * Math.PI * 2
      const ph = Math.acos(2 * Math.random() - 1)
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th)
      pos[i * 3 + 1] = r * Math.cos(ph)
      pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th)
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b
      size[i] = 0.02 + Math.random() * 0.03
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3))
    geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1))
    addPoints(geo, makePointsMaterial())
  }

  camera.position.set(0, 1.6, 5)
  camera.lookAt(0, 0, 0)
  controls.target.set(0, 0, 0)
  updater = (dt) => {
    for (const m of moving) {
      const arr = m.geo.attributes.position.array
      for (let i = 0; i < m.phases.length; i++) {
        m.phases[i] += m.speed * dt
        arr[i * 3] = Math.cos(m.phases[i]) * m.r
        arr[i * 3 + 1] = Math.sin(m.phases[i] * 1.0) * m.r * 0.06   // 环带一点厚度
        arr[i * 3 + 2] = Math.sin(m.phases[i]) * m.r
      }
      m.geo.attributes.position.needsUpdate = true
    }
    // 核呼吸
    const core = group.children[0]
    const s = 1 + Math.sin(clock.t * 2.2) * 0.12
    core.scale.setScalar(s)
  }
}

// ---------------- 3. 爆发 ----------------

const burst = {
  N: 6000,
  cursor: 0,
  pos: null, vel: null, life: null, maxLife: null, size0: null,
  geo: null,
}

function buildBurst() {
  const N = burst.N
  burst.pos = new Float32Array(N * 3)
  burst.vel = new Float32Array(N * 3)
  burst.life = new Float32Array(N)
  burst.maxLife = new Float32Array(N)
  burst.size0 = new Float32Array(N)
  const col = new Float32Array(N * 3)
  const size = new Float32Array(N)
  for (let i = 0; i < N; i++) {
    burst.pos[i * 3] = burst.pos[i * 3 + 1] = burst.pos[i * 3 + 2] = 9999
    size[i] = 0
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(burst.pos, 3))
  geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3))
  geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1))
  burst.geo = geo
  addPoints(geo, makePointsMaterial())

  camera.position.set(0, 0.8, 6)
  camera.lookAt(0, 0, 0)
  controls.target.set(0, 0, 0)

  const palette = ['#ff5f6d', '#ffc371', '#7cf3d0', '#9b8cff', '#4fc3f7'].map((h) => new THREE.Color(h))

  /** 在世界坐标 (x,y,z) 发射 n 颗 */
  function emitAt(x, y, z, n) {
    const pos = burst.pos
    const vel = burst.vel
    const life = burst.life
    const maxLife = burst.maxLife
    const size0 = burst.size0
    const colArr = burst.geo.attributes.aColor.array
    const sizeArr = burst.geo.attributes.aSize.array
    for (let k = 0; k < n; k++) {
      const i = burst.cursor
      burst.cursor = (burst.cursor + 1) % N
      // 球面方向 + 幂律速度：慢芯多、快粒少
      const th = Math.random() * Math.PI * 2
      const ph = Math.acos(2 * Math.random() - 1)
      let sp = 0.6 + Math.pow(Math.random(), 2.2) * 3.4
      let sz = 0.05 + Math.random() * 0.05
      let c
      if (Math.random() < 0.22) { sp = 0.1 + Math.random() * 0.5; sz = 0.09 + Math.random() * 0.07; c = new THREE.Color('#fff6e0') }
      else c = palette[(Math.random() * palette.length) | 0]
      pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z
      vel[i * 3] = Math.sin(ph) * Math.cos(th) * sp
      vel[i * 3 + 1] = Math.cos(ph) * sp
      vel[i * 3 + 2] = Math.sin(ph) * Math.sin(th) * sp
      const lf = 1.5 + Math.random() * 1.2
      life[i] = lf; maxLife[i] = lf; size0[i] = sz
      colArr[i * 3] = c.r; colArr[i * 3 + 1] = c.g; colArr[i * 3 + 2] = c.b
      sizeArr[i] = sz
    }
    burst.geo.attributes.aColor.needsUpdate = true
  }
  burst.emit = emitAt

  // 进场先来一发大的，别给黑屏
  setTimeout(() => { if (mode.value === 'burst') { burst.emit(0, 0, 0, 1500); tick(0.5) } }, 350)

  updater = (dt) => {
    const pos = burst.pos
    const vel = burst.vel
    const life = burst.life
    const maxLife = burst.maxLife
    const size0 = burst.size0
    const sizeArr = burst.geo.attributes.aSize.array
    const damp = Math.exp(-1.9 * dt)
    for (let i = 0; i < burst.N; i++) {
      if (life[i] <= 0) continue
      life[i] -= dt
      if (life[i] <= 0) { pos[i * 3] = 9999; sizeArr[i] = 0; continue }
      // 阻尼 + 微弱向心（飘回中心，画面不散）
      vel[i * 3] = vel[i * 3] * damp - pos[i * 3] * 0.12 * dt
      vel[i * 3 + 1] = vel[i * 3 + 1] * damp - pos[i * 3 + 1] * 0.12 * dt
      vel[i * 3 + 2] = vel[i * 3 + 2] * damp - pos[i * 3 + 2] * 0.12 * dt
      pos[i * 3] += vel[i * 3] * dt
      pos[i * 3 + 1] += vel[i * 3 + 1] * dt
      pos[i * 3 + 2] += vel[i * 3 + 2] * dt
      const t = life[i] / maxLife[i]
      sizeArr[i] = size0[i] * (t < 0.3 ? t / 0.3 : 1)
    }
    burst.geo.attributes.position.needsUpdate = true
    burst.geo.attributes.aSize.needsUpdate = true
  }
}

// ---------------- 模式切换 / 生命周期 ----------------

const builders = { galaxy: buildGalaxy, atom: buildAtom, burst: buildBurst }

function setMode(key) {
  if (mode.value === key) return
  mode.value = key
  tick(0.4)
  rebuild()
}

function rebuild() {
  disposeGroup()
  group = new THREE.Group()
  scene.add(group)
  builders[mode.value]()
  controls.update()
}

function onBack() {
  router.back()
}

// 爆发模式：短点 = 发射（拖动交给 OrbitControls 转视角）
let pressAt = 0
let pressXY = [0, 0]
function onPointerDown(e) {
  if (mode.value !== 'burst') return
  pressAt = performance.now()
  pressXY = [e.clientX, e.clientY]
}
function onPointerUp(e) {
  if (mode.value !== 'burst' || !burst.emit) return
  const dt = performance.now() - pressAt
  const dx = e.clientX - pressXY[0]
  const dy = e.clientY - pressXY[1]
  if (dt > 280 || Math.hypot(dx, dy) > 10) return
  // 屏幕点 → NDC → 与 z=0 平面求交
  const rect = cv.value.getBoundingClientRect()
  const ndc = new THREE.Vector2(
    ((e.clientX - rect.left) / rect.width) * 2 - 1,
    -((e.clientY - rect.top) / rect.height) * 2 + 1,
  )
  const ray = new THREE.Raycaster()
  ray.setFromCamera(ndc, camera)
  const hit = new THREE.Vector3()
  if (ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0), hit)) {
    burst.emit(hit.x, hit.y, hit.z, 1100)
    tick(0.5)
  }
}

function resize() {
  if (!renderer) return
  const w = window.innerWidth
  const h = window.innerHeight
  renderer.setSize(w, h, false)
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1))
  camera.aspect = w / h
  camera.updateProjectionMatrix()
}

function loop(now) {
  raf = requestAnimationFrame(loop)
  if (document.visibilityState !== 'visible') { lastT = now; return }
  const dt = Math.min(0.05, Math.max(0.001, (now - lastT) / 1000))
  lastT = now
  clock.t += dt
  updater?.(dt)
  controls.update()
  renderer.render(scene, camera)
}

onMounted(() => {
  const el = cv.value
  renderer = new THREE.WebGLRenderer({ canvas: el, antialias: false, alpha: false, powerPreference: 'high-performance' })
  renderer.setClearColor(0x000005, 1)
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1))
  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x000005, 0.055)
  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 120)
  glowTex = makeGlowTexture()
  controls = new OrbitControls(camera, el)
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.enablePan = false
  controls.minDistance = 2
  controls.maxDistance = 14
  controls.rotateSpeed = 0.85
  el.addEventListener('pointerdown', onPointerDown)
  el.addEventListener('pointerup', onPointerUp)
  window.addEventListener('resize', resize)
  resize()
  rebuild()
  // dev 探针
  if (import.meta.env.DEV) window.__p3d = { get burst() { return burst }, scene, camera }
  lastT = performance.now()
  raf = requestAnimationFrame(loop)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  const el = cv.value
  if (el) {
    el.removeEventListener('pointerdown', onPointerDown)
    el.removeEventListener('pointerup', onPointerUp)
  }
  window.removeEventListener('resize', resize)
  disposeGroup()
  glowTex?.dispose()
  controls?.dispose()
  renderer?.dispose()
  renderer?.forceContextLoss?.()
  renderer = null
})
</script>

<style scoped>
.p3d {
  position: fixed;
  inset: 0;
  background: #000005;
  overflow: hidden;
}
.cv {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  touch-action: none;
}
.hd {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 54px;
  padding: 0 14px;
  padding-top: env(safe-area-inset-top, 0px);
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(rgba(0, 0, 5, 0.72), rgba(0, 0, 5, 0));
}
.back {
  width: 36px; height: 36px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  display: grid;
  place-items: center;
}
.back svg { width: 22px; height: 22px; fill: currentColor; }
.hd-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}
.hd-hint {
  margin-left: auto;
  color: rgba(255, 255, 255, 0.45);
  font-size: 11px;
}
.modes {
  position: absolute;
  left: 0; right: 0;
  bottom: calc(26px + env(safe-area-inset-bottom, 0px));
  display: flex;
  justify-content: center;
  gap: 10px;
}
.pill {
  min-width: 84px;
  height: 40px;
  padding: 0 18px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 255, 255, 0.75);
  font-size: 14px;
  letter-spacing: 2px;
  transition: all 0.18s;
}
.pill.on {
  background: rgba(232, 198, 132, 0.16);
  border-color: rgba(232, 198, 132, 0.65);
  color: #e8c684;
}
.toast {
  position: absolute;
  left: 50%;
  bottom: calc(88px + env(safe-area-inset-bottom, 0px));
  transform: translateX(-50%);
  padding: 8px 18px;
  border-radius: 18px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 13px;
  white-space: nowrap;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

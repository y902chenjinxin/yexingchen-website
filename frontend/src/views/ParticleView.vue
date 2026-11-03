<template>
  <DeviceGate need="phone" title="请在手机上打开 魔幻粒子3D">
    <div class="app">
      <!-- ==================== 播放页（magic3d_main.xml） ==================== -->
      <template v-if="playing">
        <canvas ref="cv" class="cv"
                @pointerdown.prevent="onDown" @pointermove.prevent="onMove"
                @pointerup.prevent="onUp" @pointercancel.prevent="onUp" />

        <!-- 四角热区：布局里是 4 个 1dp 透明按钮 -->
        <button class="hot tl" type="button" aria-label="上一个" @click="stepEffect(-1)" />
        <button class="hot tr" type="button" aria-label="下一个" @click="stepEffect(1)" />
        <button class="hot bl" type="button" aria-label="隐藏菜单" @click="toggleMenu" />
        <button class="hot br" type="button" aria-label="清屏" @click="clearAll" />

        <button class="back" type="button" aria-label="返回" @click="close">
          <svg viewBox="0 0 24 24"><path d="M15.4 7.4 14 6l-6 6 6 6 1.4-1.4L10.8 12z" /></svg>
        </button>

        <div class="effname" :class="{ on: menuHidden }">{{ current.name }}</div>

        <!-- 底部浮动工具栏（FloatingToolbar，menu_demo.xml 的 6 项） -->
        <div class="ftool" :class="{ hide: menuHidden }">
          <button v-for="t in TOOLS" :key="t.key" type="button" class="ft-btn"
                  :class="{ dim: t.dim }" :aria-label="t.label" @click="run(t.key)">
            <svg viewBox="0 0 24 24"><use :href="'#i-' + t.icon" /></svg>
          </button>
        </div>

        <!-- FAB：粒子页原版是白底青绿加号 -->
        <button class="fab" type="button" :class="{ hide: menuHidden }" aria-label="返回列表" @click="close">
          <svg viewBox="0 0 24 24"><use href="#i-plus" /></svg>
        </button>

        <!-- 参数面板（dialog_particle_setting.xml） -->
        <transition name="up">
          <div v-if="panel" class="sheet" @pointerdown.stop>
            <div class="sheet-hd">
              <b>自定义效果</b>
              <button type="button" @click="panel = false">完成</button>
            </div>
            <div v-for="sl in sliders" :key="sl.key" class="sl">
              <span class="sl-lab">{{ sl.label }}</span>
              <input class="sl-range" type="range" :min="sl.min" :max="sl.max" :step="sl.step"
                     :value="cfg[sl.key]" @input="setCfg(sl.key, +$event.target.value)" />
              <span class="sl-val">{{ Number(cfg[sl.key]).toFixed(2) }}</span>
            </div>
            <button class="restore" type="button" aria-label="恢复默认" @click="restore">
              <svg viewBox="0 0 24 24"><use href="#i-reset" /></svg>
            </button>
          </div>
        </transition>

        <!-- 我的截图 -->
        <transition name="up">
          <div v-if="gallery" class="sheet" @pointerdown.stop>
            <div class="sheet-hd">
              <b>我的截图</b>
              <button type="button" @click="gallery = false">关闭</button>
            </div>
            <p v-if="!shots.length" class="empty">还没有截图，点工具栏的「保存图片」</p>
            <div class="shot-grid">
              <div v-for="(s, i) in shots" :key="i" class="shot">
                <img :src="s" alt="" />
                <button type="button" @click="delShot(i)">×</button>
              </div>
            </div>
          </div>
        </transition>

        <transition name="fade">
          <div v-if="toast" class="toast">{{ toast }}</div>
        </transition>
      </template>

      <!-- ==================== 主页（activity_main_tab.xml：Tab + 效果列表） ==================== -->
      <template v-else>
        <div class="home">
          <div class="hd">
            <span class="hd-title">魔幻粒子3D</span>
            <span class="hd-acts">
              <button type="button" aria-label="我的截图" @click="gallery = true">
                <svg viewBox="0 0 24 24"><use href="#i-shots" /></svg>
              </button>
              <button type="button" aria-label="我的录制" @click="toastMsg('先进效果播放页，再点底部录制按钮')">
                <svg viewBox="0 0 24 24"><use href="#i-videos" /></svg>
              </button>
            </span>
          </div>
          <nav class="tabs">
            <button v-for="t in TABS" :key="t" type="button"
                    class="tab" :class="{ on: tab === t }" @click="tab = t">{{ t }}</button>
          </nav>

          <!-- 我的：截图列表 -->
          <div v-if="tab === '我'" class="me">
            <p v-if="!shots.length" class="empty">还没有截图</p>
            <div class="shot-grid">
              <div v-for="(s, i) in shots" :key="i" class="shot">
                <img :src="s" alt="" />
                <button type="button" @click="delShot(i)">×</button>
              </div>
            </div>
          </div>

          <!-- 效果列表：大圆球 + 名字 -->
          <div v-else class="list">
            <button v-for="(e, i) in list" :key="e.key" type="button" class="eff"
                    :style="{ animationDelay: (i * 0.08) + 's' }" @click="open(e)">
              <i class="ball" :style="{ background: ball(e), '--glow': ballGlow(e) }" />
              <span>{{ e.name }}</span>
            </button>
          </div>

          <!-- 背景光斑（原版是动态 BackgroundView，这里用 CSS 渐变 + bokeh 对位） -->
          <i v-for="(b, i) in bokeh" :key="'b' + i" class="bokeh" :style="b" />
        </div>

        <transition name="up">
          <div v-if="gallery" class="sheet" @pointerdown.stop>
            <div class="sheet-hd">
              <b>我的截图</b>
              <button type="button" @click="gallery = false">关闭</button>
            </div>
            <p v-if="!shots.length" class="empty">还没有截图</p>
            <div class="shot-grid">
              <div v-for="(s, i) in shots" :key="i" class="shot">
                <img :src="s" alt="" />
                <button type="button" @click="delShot(i)">×</button>
              </div>
            </div>
          </div>
        </transition>

        <transition name="fade">
          <div v-if="toast" class="toast">{{ toast }}</div>
        </transition>
      </template>
    </div>

    <!-- 图标集 -->
    <svg class="sprite" aria-hidden="true">
      <symbol id="i-settings" viewBox="0 0 24 24">
        <path d="M3 6h8M15 6h6M11 3.6v4.8M3 12h4M11 12h10M7 9.6v4.8M3 18h12M19 18h2M15 15.6v4.8" />
      </symbol>
      <symbol id="i-heart" viewBox="0 0 24 24">
        <path d="M12 20s-7-4.3-7-9a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 4.7-7 9-7 9z" />
      </symbol>
      <symbol id="i-image" viewBox="0 0 24 24">
        <path d="M4 5h16v14H4zM8.5 11a1.4 1.4 0 1 0 0-2.8 1.4 1.4 0 0 0 0 2.8zM5 17l4.5-4.5 3 3 2.5-2.5L19 17" />
      </symbol>
      <symbol id="i-grid" viewBox="0 0 24 24">
        <path d="M5 5h5v5H5zM14 5h5v5h-5zM5 14h5v5H5zM14 14h5v5h-5z" />
      </symbol>
      <symbol id="i-dots" viewBox="0 0 24 24">
        <circle cx="12" cy="5" r="1.7" /><circle cx="12" cy="12" r="1.7" /><circle cx="12" cy="19" r="1.7" />
      </symbol>
      <symbol id="i-reset" viewBox="0 0 24 24">
        <path d="M12 5a7 7 0 1 1-6.6 9.3M5 5v4h4" />
      </symbol>
      <symbol id="i-plus" viewBox="0 0 24 24">
        <path d="M11 4h2v7h7v2h-7v7h-2v-7H4v-2h7z" />
      </symbol>
      <symbol id="i-shots" viewBox="0 0 24 24">
        <path d="M4 7h11v11H4zM9 4h11v11" />
      </symbol>
      <symbol id="i-videos" viewBox="0 0 24 24">
        <path d="M6 5h12v14H6zM10 9.5l4 2.5-4 2.5z" />
      </symbol>
    </svg>
  </DeviceGate>
</template>

<script setup>
/**
 * 魔幻粒子3D（复刻版）v2.46.357
 *
 * 夜星：「现在全是液体，我的原子和粒子呢」「你不是已经逆向了嘛，为什么不是按照人家做的来」
 * 并给了 7 张原版截图 —— 图里大部分档位是**粒子**（彩色星点 / 蓝色细线云 /
 * 原子轨道 / 电光），只有「流动」Tab 是液体。
 *
 * 结构照 activity_main_tab.xml：主页 = 顶栏 + Tab（三维/线性/流动/我）+ 渐变背景效果列表；
 * 点效果进全屏播放页（magic3d_main.xml：工具栏 + FAB）。引擎按档位走：
 * 粒子档走 useParticles（orbit/streak/bolt 三种运动），「流动」才用 useFluid。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import DeviceGate from '@/components/common/DeviceGate.vue'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import { createParticleEngine } from '@/composables/useParticles'
import { createFluidEngine } from '@/composables/useFluid'
import { tick } from '@/utils/haptic'

const { exit: exitFullscreen } = useFullscreenPage()

const TABS = ['三维', '线性', '流动', '我']

/** 效果目录：engine 决定用哪套引擎，cfg 是各档参数 */
const CATALOG = {
  三维: [
    {
      key: 'atom', name: '虚幻原子', engine: 'particles', hue: 160,
      cfg: { style: 'glow', motion: 'orbit', size: 11, count: 3200, bloom: 1.2, trail: 0.5 },
    },
    {
      key: 'beam', name: '奇点与光束', engine: 'particles', hue: 290,
      cfg: { style: 'streak', motion: 'free', size: 9, count: 3600, bloom: 0.9, width: 0.05, trail: 0.95, burst: true },
    },
    {
      key: 'spark', name: '星河', engine: 'particles', hue: 30,
      cfg: { style: 'streak', motion: 'free', size: 6, count: 2600, bloom: 0.7, width: 0.045, trail: 0.85, spark: true },
    },
    {
      key: 'bolt', name: '电光', engine: 'particles', hue: 210,
      cfg: { style: 'streak', motion: 'free', size: 5, count: 2000, bloom: 0.75, width: 0.04, trail: 0.9, bolt: true },
    },
  ],
  线性: [
    {
      key: 'flow', name: '粒子流', engine: 'particles', hue: 215,
      cfg: { style: 'streak', motion: 'free', size: 5, count: 4200, bloom: 0.6, width: 0.035, trail: 0.9, cloud: true },
    },
  ],
  流动: [
    {
      key: 'liquid', name: '魔幻液体', engine: 'fluid', hue: 285,
      cfg: { mode: 0, palette: 'magic', curl: 24, glow: 1.5, detail: 0.55, densityDissipation: 0.6, velocityDissipation: 0.9, splatRadius: 0.0005 },
    },
    {
      key: 'rainbow', name: '七彩流动', engine: 'fluid', hue: 200,
      cfg: { mode: 0, palette: 'rainbow', curl: 20, glow: 1.2, detail: 0.4, densityDissipation: 0.5, velocityDissipation: 0.9, splatRadius: 0.0005 },
    },
    {
      key: 'fire', name: '火魅幻境', engine: 'fluid', hue: 20,
      cfg: { mode: 0, palette: 'fire', curl: 34, glow: 2.2, detail: 0.7, densityDissipation: 0.85, velocityDissipation: 0.8, splatRadius: 0.0005 },
    },
    {
      key: 'trippy', name: '扭曲轨道', engine: 'fluid', hue: 320,
      cfg: { mode: 1, palette: 'neon', curl: 44, glow: 1.4, detail: 0.3, densityDissipation: 0.55, velocityDissipation: 0.8, splatRadius: 0.0005 },
    },
  ],
  我: [],
}

const TOOLS = [
  { key: 'custom', icon: 'settings', label: '自定义效果' },
  { key: 'shots', icon: 'heart', label: '我的截图' },
  { key: 'save', icon: 'image', label: '保存图片' },
  { key: 'wall', icon: 'grid', label: '设为动态壁纸', dim: true },
  { key: 'hide', icon: 'dots', label: '隐藏菜单' },
  { key: 'clear', icon: 'reset', label: '清屏' },
]

const sliders = [
  { key: 'curl', label: '卷曲', min: 0, max: 60, step: 1 },
  { key: 'glow', label: '光晕', min: 0, max: 3, step: 0.05 },
  { key: 'detail', label: '纹理', min: 0, max: 1, step: 0.05 },
  { key: 'densityDissipation', label: '浓度', min: 0.1, max: 3, step: 0.05 },
  { key: 'size', label: '粗细', min: 2, max: 30, step: 0.5 },
]

const cv = ref(null)
const playing = ref(false)
const tab = ref('三维')
const panel = ref(false)
const gallery = ref(false)
const menuHidden = ref(false)
const toast = ref('')
const shots = ref([])
const current = ref(CATALOG['三维'][0])

const list = computed(() => CATALOG[tab.value] || [])

const cfg = reactive({})

let engine = null          // { type: 'particles' | 'fluid', api }
let raf = 0
let lastT = 0
let toastTimer = 0
let idleAcc = 0
let boltAcc = 0

const fingers = new Map()
const downAt = new Map()

// 背景光斑（原版主界面是动态 BackgroundView，这里用 CSS 渐变 + 随机 bokeh 对位）
const bokeh = Array.from({ length: 14 }, () => {
  const s = 26 + Math.random() * 120
  return {
    left: (Math.random() * 100) + '%',
    top: (10 + Math.random() * 90) + '%',
    width: s + 'px',
    height: s + 'px',
    opacity: 0.05 + Math.random() * 0.1,
  }
})

// ---------------- 生命周期 ----------------
onMounted(() => {
  try {
    shots.value = JSON.parse(localStorage.getItem('xh_particle_shots') || '[]').slice(0, 24)
  } catch { /* ignore */ }
})

onBeforeUnmount(() => {
  stopLoop()
  destroyEngine()
})

function stopLoop() {
  if (raf) cancelAnimationFrame(raf)
  raf = 0
}

function destroyEngine() {
  if (engine?.api?.dispose) engine.api.dispose()
  engine = null
}

// ---------------- 打开 / 关闭播放页 ----------------
async function open(e) {
  current.value = e
  playing.value = true
  await nextTick()
  const el = cv.value
  if (!el) return
  const debug = /(?:^|[?&])debug=1/.test(window.location.search)
  const opts = { ...(e.cfg || {}), debug }
  if (e.engine === 'fluid') {
    engine = { type: 'fluid', api: createFluidEngine(el, opts) }
  } else {
    engine = { type: 'particles', api: createParticleEngine(el, opts) }
  }
  if (!engine.api.ok) {
    toastMsg(engine.api.reason === 'no-webgl' ? '这台设备的浏览器不支持 WebGL' : '引擎初始化失败')
    playing.value = false
    return
  }
  if (import.meta.env.DEV) window.__fx = engine.api
  resize()
  applyEngine()
  lastT = performance.now()
  raf = requestAnimationFrame(loop)
  tick(0.4)
}

function close() {
  playing.value = false
  stopLoop()
  destroyEngine()
  exitFullscreen()
}

function resize() {
  if (!engine?.api) return
  engine.api.resize(window.innerWidth, window.innerHeight)
}

function applyEngine() {
  const e = current.value
  if (!engine?.api) return
  if (engine.type === 'fluid') {
    engine.api.applyOptions({ ...e.cfg })
    engine.api.clear()
    // 开场先给两下，别让用户对着黑屏
    for (let i = 0; i < 3; i++) {
      engine.api.splat(
        window.innerWidth * (0.35 + Math.random() * 0.3),
        window.innerHeight * (0.35 + Math.random() * 0.3),
        (Math.random() - 0.5) * 60, (Math.random() - 0.5) * 60,
        engine.api.pointerColor(window.innerWidth / 2, window.innerHeight / 2))
    }
    return
  }
  engine.api.applyOptions({ ...e.cfg, motion: e.cfg.motion || 'free' })
  engine.api.clear()
  seedEffect(e)
}

/** 各粒子档的开场画面 */
function seedEffect(e) {
  const api = engine.api
  const W = window.innerWidth
  const H = window.innerHeight
  if (e.cfg.motion === 'orbit') {
    // 霓虹花瓣：6 圈椭圆环，不同倾角 + 中心亮核（照图 6）
    const rings = []
    for (let k = 0; k < 6; k++) {
      rings.push({
        cx: W / 2, cy: H * 0.44,
        a: 46 + k * 26,
        ratio: 0.34 + (k % 3) * 0.1,
        w: (0.55 + k * 0.22) * (k % 2 ? 1 : -1),
        tilt: (k / 6) * Math.PI,
        count: 64,
        size: 9,
        hue: 150 + k * 18,
        hueSpan: 26,
      })
    }
    api.emitOrbit(rings, { cx: W / 2, cy: H * 0.44, count: 80, size: 9 })
    return
  }
  if (e.cfg.spark) {
    // 星河：全屏随机星点 + 短光线（照图 3）
    for (let i = 0; i < 420; i++) {
      api.emit(Math.random() * W, Math.random() * H, 1, {
        speed: 40 + Math.random() * 220,
        lifeRange: [1.6, 3.4],
        sizeMul: 0.8,
      })
    }
    return
  }
  if (e.cfg.cloud) {
    // 粒子流：蓝色细线云（照图 5）
    for (let i = 0; i < 900; i++) {
      api.emit(Math.random() * W, Math.random() * H, 1, {
        speed: 24 + Math.random() * 130,
        lifeRange: [2.2, 4.2],
        sizeMul: 0.9,
      })
    }
    return
  }
  if (e.cfg.bolt) {
    // 电光：背景细线，主电光在 loop 里周期性劈（照图 7）
    for (let i = 0; i < 500; i++) {
      api.emit(Math.random() * W, Math.random() * H, 1, {
        speed: 20 + Math.random() * 90,
        lifeRange: [1.8, 3.2],
        sizeMul: 0.7,
      })
    }
  }
}

// ---------------- 主循环 ----------------
function loop(now) {
  raf = requestAnimationFrame(loop)
  if (document.visibilityState !== 'visible') { lastT = now; return }
  const dt = Math.min(0.05, Math.max(0.001, (now - lastT) / 1000))
  lastT = now
  pump(dt)
  engine.api.step(dt)
  engine.api.draw()
}

function pump(dt) {
  if (!engine?.api) return
  const api = engine.api
  const e = current.value
  const W = window.innerWidth
  const H = window.innerHeight

  if (engine.type === 'fluid') {
    if (!fingers.size) {
      idleAcc += dt
      if (idleAcc > 4) {
        idleAcc = 0
        api.splat(W * (0.5 + (Math.random() - 0.5) * 0.4), H * (0.5 + (Math.random() - 0.5) * 0.4),
          (Math.random() - 0.5) * 50, (Math.random() - 0.5) * 50, api.pointerColor(W / 2, H / 2))
      }
    }
    for (const f of fingers.values()) {
      const dx = f.x - f.px
      const dy = f.y - f.py
      if (Math.abs(dx) > 0.4 || Math.abs(dy) > 0.4) {
        api.splat(f.x, f.y, dx, dy, api.pointerColor(f.x, f.y))
        f.px = f.x
        f.py = f.y
      }
    }
    return
  }

  // ---- 粒子档 ----
  if (e.cfg.burst) {
    // 奇点与光束：点按从触点爆发，空闲偶尔从中心来一发（照图 4）
    if (!fingers.size) {
      idleAcc += dt
      if (idleAcc > 2.4) { idleAcc = 0; burst(W / 2, H / 2, 1.6) }
    }
    for (const f of fingers.values()) {
      if (!f.burst) { burst(f.x, f.y, 1); f.burst = true }
    }
    return
  }
  if (e.cfg.spark) {
    // 星河：持续补星点，手指处多喷
    const n = fingers.size ? 8 : 3
    for (let i = 0; i < n; i++) {
      if (fingers.size) {
        const f = [...fingers.values()][i % fingers.size]
        api.emit(f.x, f.y, 1, { speed: 90 + Math.random() * 260, lifeRange: [1.4, 2.8], sizeMul: 0.85 })
      } else {
        api.emit(Math.random() * W, Math.random() * H, 1, {
          speed: 40 + Math.random() * 200, lifeRange: [1.6, 3.2], sizeMul: 0.75,
        })
      }
    }
    return
  }
  if (e.cfg.bolt) {
    // 电光：周期性劈一条（照图 7）
    boltAcc += dt
    const every = fingers.size ? 0.32 : 0.85
    if (boltAcc > every) {
      boltAcc = 0
      let sx = W / 2
      let sy = H * 0.62
      if (fingers.size) {
        const f = [...fingers.values()][0]
        sx = f.x
        sy = f.y
      }
      api.bolt(sx, sy, -Math.PI / 2 + (Math.random() - 0.5) * 1.6,
        200 + Math.random() * 220, [1, 1, 1])
    }
    return
  }
  if (e.cfg.cloud) {
    // 粒子流：低速蓝线持续补
    for (let i = 0; i < 4; i++) {
      api.emit(Math.random() * W, Math.random() * H, 1, {
        speed: 24 + Math.random() * 120, lifeRange: [2.2, 4.0], sizeMul: 0.85,
      })
    }
  }
}

/** 白核 + 彩色长尾的爆发（图 4） */
function burst(x, y, mul = 1) {
  const api = engine?.api
  if (!api) return
  api.emit(x, y, Math.round(300 * mul), { speed: 420 * mul, lifeRange: [0.9, 1.7], sizeMul: 1 })
  api.emit(x, y, Math.round(60 * mul), { speed: 120, lifeRange: [0.5, 0.9], sizeMul: 2.4 })
  tick(0.6)
}

// ---------------- 手势 ----------------
function onDown(e) {
  try { e.currentTarget.setPointerCapture?.(e.pointerId) } catch { /* 合成事件没有真 pointerId */ }
  fingers.set(e.pointerId, { x: e.clientX, y: e.clientY, px: e.clientX, py: e.clientY })
  downAt.set(e.pointerId, { x: e.clientX, y: e.clientY, t: performance.now() })
  if (menuHidden.value) { menuHidden.value = false; return }
  if (engine?.type === 'fluid') {
    engine.api.splat(e.clientX, e.clientY, 0, 0, engine.api.pointerColor(e.clientX, e.clientY))
  }
  tick(0.4)
}

function onMove(e) {
  const p = fingers.get(e.pointerId)
  if (!p) return
  p.x = e.clientX
  p.y = e.clientY
}

function onUp(e) {
  const d = downAt.get(e.pointerId)
  const p = fingers.get(e.pointerId)
  if (d && p && engine?.type === 'particles') {
    const dt = performance.now() - d.t
    const dist = Math.hypot(p.x - d.x, p.y - d.y)
    if (dt < 200 && dist < 10 && current.value.cfg.burst) burst(p.x, p.y, 1.2)
  }
  fingers.delete(e.pointerId)
  downAt.delete(e.pointerId)
}

// ---------------- 播放页工具 ----------------
function applyCfg() {
  if (!engine?.api) return
  engine.api.applyOptions({ ...cfg })
}

function setCfg(k, v) {
  cfg[k] = v
  applyCfg()
  tick(0.3)
}

function restore() {
  Object.assign(cfg, current.value.cfg)
  applyCfg()
  showToast('已恢复')
  tick(0.5)
}

function stepEffect(dir) {
  const all = CATALOG['三维'].concat(CATALOG['线性'], CATALOG['流动'])
  const n = all.length
  const i = all.findIndex((x) => x.key === current.value.key)
  const next = all[(i + dir + n) % n]
  current.value = next
  Object.assign(cfg, next.cfg || {})
  applyEngine()
  showToast(next.name)
  tick(0.5)
}

function toggleMenu() {
  menuHidden.value = !menuHidden.value
  tick(0.5)
}

function clearAll() {
  engine?.api?.clear?.()
  if (engine?.type === 'particles') seedEffect(current.value)
  tick(0.5)
}

function run(key) {
  if (key === 'custom') { panel.value = true; gallery.value = false; return }
  if (key === 'save') { saveShot(); return }
  if (key === 'hide') { toggleMenu(); return }
  if (key === 'clear') { clearAll(); return }
  if (key === 'wall') { showToast('网页版做不了动态壁纸，先保存成图片吧', 1900); return }
  if (key === 'shots') { gallery.value = true; panel.value = false; return }
}

function saveShot() {
  const c = cv.value
  if (!c) return
  const data = c.toDataURL('image/png')
  const a = document.createElement('a')
  a.href = data
  a.download = `魔幻粒子3D-${Date.now()}.png`
  a.click()
  shots.value = [data, ...shots.value].slice(0, 24)
  try { localStorage.setItem('xh_particle_shots', JSON.stringify(shots.value)) } catch { /* ignore */ }
  showToast('已保存')
  tick(0.7)
}

function delShot(i) {
  shots.value.splice(i, 1)
  try { localStorage.setItem('xh_particle_shots', JSON.stringify(shots.value)) } catch { /* ignore */ }
}

function toastMsg(msg, ms = 1500) {
  showToast(msg, ms)
}

function showToast(msg, ms = 1500) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toast.value = '' }, ms)
}

// ---------------- 主页视觉 ----------------
function ball(e) {
  const h = e.hue
  return `radial-gradient(circle at 42% 36%,
    hsla(${h}, 70%, 88%, 0.9) 0%,
    hsla(${h}, 76%, 62%, 0.92) 34%,
    hsla(${(h + 28) % 360}, 80%, 44%, 0.88) 68%,
    hsla(${(h + 60) % 360}, 82%, 30%, 0.55) 100%)`
}

function ballGlow(e) {
  return `hsla(${e.hue}, 80%, 60%, 0.55)`
}
</script>

<style scoped>
.sprite { position: absolute; width: 0; height: 0; overflow: hidden; }

.app {
  position: fixed;
  inset: 0;
  background: #000;
  overflow: hidden;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  font-family: 'Roboto', system-ui, -apple-system, 'HarmonyOS Sans', sans-serif;
}

/* ==================== 主页 ==================== */
.home {
  position: absolute;
  inset: 0;
  /* 照原版截图：顶上金橙 → 中绿 → 底部深蓝 */
  background:
    radial-gradient(140% 60% at 50% -10%, rgba(255, 183, 3, 0.9), rgba(255, 183, 3, 0) 60%),
    linear-gradient(180deg, #d99b1c 0%, #7fa03a 26%, #1f6e52 52%, #123c63 78%, #0b1e46 100%);
  overflow: hidden;
}
.hd {
  position: absolute;
  left: 0; right: 0; top: 0;
  height: 52px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(180deg, #e8a41c, #d18f14);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  z-index: 4;
}
.hd-title { color: #fff; font-size: 17px; font-weight: 500; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25); }
.hd-acts { display: flex; gap: 18px; }
.hd-acts button { border: 0; background: transparent; padding: 4px; }
.hd-acts svg { width: 22px; height: 22px; fill: none; stroke: #fff; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }

.tabs {
  position: absolute;
  left: 0; right: 0; top: 52px;
  height: 44px;
  display: flex;
  z-index: 4;
}
.tab {
  flex: 1;
  border: 0;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.68);
  font-size: 15px;
  position: relative;
}
.tab.on { color: #fff; font-weight: 600; background: rgba(255, 255, 255, 0.06); }
.tab.on::after {
  content: '';
  position: absolute;
  left: 25%; right: 25%; bottom: 0;
  height: 3px;
  border-radius: 2px;
  background: #fff;
}

.list {
  position: absolute;
  inset: 96px 0 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 26px;
  padding: 34px 0 60px;
  z-index: 2;
}
.eff {
  border: 0;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  animation: rise 0.5s both;
}
@keyframes rise { from { opacity: 0; transform: translateY(24px); } }
.eff .ball {
  width: 128px; height: 128px;
  border-radius: 50%;
  box-shadow:
    0 0 44px var(--glow),
    0 0 90px var(--glow),
    inset 0 0 30px rgba(255, 255, 255, 0.16);
  transition: transform 0.18s;
}
.eff:active .ball { transform: scale(0.94); }
.eff span {
  color: #fff;
  font-size: 17px;
  letter-spacing: 2px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.55);
}
.bokeh {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0) 70%);
  pointer-events: none;
}

.me {
  position: absolute;
  inset: 96px 0 0;
  overflow-y: auto;
  padding: 16px;
  z-index: 2;
}
.empty { color: rgba(255, 255, 255, 0.55); text-align: center; padding: 40px 0; font-size: 13px; }
.shot-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.shot { position: relative; aspect-ratio: 9 / 16; border-radius: 8px; overflow: hidden; }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.shot button {
  position: absolute; right: 4px; top: 4px;
  width: 20px; height: 20px;
  border: 0; border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff; font-size: 13px; line-height: 18px;
  padding: 0;
}

/* ==================== 播放页 ==================== */
.cv { position: absolute; inset: 0; display: block; width: 100%; height: 100%; }
.hot { position: absolute; width: 44px; height: 44px; padding: 0; border: 0; background: transparent; }
.hot.tl { left: 0; top: 0; }
.hot.tr { right: 0; top: 0; }
.hot.bl { left: 0; bottom: 0; }
.hot.br { right: 0; bottom: 0; }

.back {
  position: absolute;
  left: 8px; top: 8px;
  width: 40px; height: 40px;
  border: 0; padding: 0;
  background: transparent;
  display: grid; place-items: center;
  z-index: 6;
}
.back svg { width: 24px; height: 24px; fill: rgba(255, 255, 255, 0.85); }

.effname {
  position: absolute;
  left: 0; right: 0;
  bottom: 100px;
  text-align: center;
  color: #fff;
  font-size: 14px;
  letter-spacing: 1px;
  opacity: 0;
  transition: opacity 0.25s;
  pointer-events: none;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.7);
}
.effname.on { opacity: 0.9; }

.ftool {
  position: absolute;
  left: 12px;
  right: 84px;
  bottom: calc(52px + env(safe-area-inset-bottom, 0px));
  height: 64px;
  border-radius: 10px;
  background: rgba(22, 22, 24, 0.86);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 8px 26px rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: space-evenly;
  transition: transform 0.24s ease, opacity 0.24s ease;
  z-index: 5;
}
.ftool.hide { transform: translateY(28px); opacity: 0; pointer-events: none; }
.ft-btn {
  width: 44px; height: 44px;
  border: 0; padding: 0;
  background: transparent;
  display: grid; place-items: center;
  border-radius: 50%;
}
.ft-btn:active { background: rgba(255, 255, 255, 0.12); }
.ft-btn svg {
  width: 22px; height: 22px;
  fill: none;
  stroke: rgba(255, 255, 255, 0.95);
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.ft-btn.dim svg { stroke: rgba(255, 255, 255, 0.45); }
.ft-btn svg circle { stroke: none; fill: rgba(255, 255, 255, 0.95); }
.ft-btn.dim svg circle { fill: rgba(255, 255, 255, 0.45); }

/* FAB：粒子页原版是白底青绿加号 */
.fab {
  position: absolute;
  right: 16px;
  bottom: calc(84px + env(safe-area-inset-bottom, 0px));
  width: 56px; height: 56px;
  border-radius: 50%;
  border: 0;
  background: #fff;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  display: grid; place-items: center;
  transition: transform 0.2s ease, opacity 0.2s ease;
  z-index: 6;
}
.fab svg { width: 26px; height: 26px; fill: #00bfa5; }
.fab:active { transform: scale(0.94); }
.fab.hide { transform: scale(0.4); opacity: 0; pointer-events: none; }

/* ---------- 面板 ---------- */
.sheet {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  background: #16171a;
  border-radius: 18px 18px 0 0;
  padding: 6px 16px 22px;
  box-shadow: 0 -12px 40px rgba(0, 0, 0, 0.6);
  z-index: 10;
  max-height: 76vh;
  overflow-y: auto;
}
.sheet-hd { display: flex; align-items: center; justify-content: space-between; padding: 12px 0 14px; }
.sheet-hd b { color: #fff; font-size: 15px; font-weight: 500; }
.sheet-hd button { border: 0; background: transparent; color: #00bfa5; font-size: 14px; padding: 6px 4px; }

.sl { display: flex; align-items: center; gap: 10px; padding: 10px 0; }
.sl-lab { width: 42px; color: rgba(255, 255, 255, 0.82); font-size: 13px; flex: none; }
.sl-val {
  width: 42px; text-align: right;
  color: rgba(255, 255, 255, 0.5); font-size: 12px;
  font-variant-numeric: tabular-nums;
  flex: none;
}
.sl-range {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 2px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.18);
}
.sl-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #00bfa5;
  box-shadow: 0 0 0 6px rgba(0, 191, 165, 0.14);
}
.sl-range::-moz-range-thumb {
  width: 16px; height: 16px; border: 0;
  border-radius: 50%; background: #00bfa5;
}
.restore {
  display: block;
  margin: 16px auto 0;
  width: 44px; height: 44px;
  border: 0; border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
}
.restore svg {
  width: 22px; height: 22px;
  fill: none; stroke: #fff; stroke-width: 1.7;
  stroke-linecap: round; stroke-linejoin: round;
}

.toast {
  position: absolute;
  left: 50%;
  bottom: 148px;
  transform: translateX(-50%);
  padding: 9px 16px;
  border-radius: 20px;
  background: rgba(0, 0, 0, 0.72);
  color: #fff;
  font-size: 13px;
  white-space: nowrap;
  z-index: 20;
  pointer-events: none;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.up-enter-active, .up-leave-active { transition: transform 0.24s ease, opacity 0.24s ease; }
.up-enter-from, .up-leave-to { transform: translateY(100%); opacity: 0.6; }
</style>

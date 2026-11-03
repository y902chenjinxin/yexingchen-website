<template>
  <DeviceGate need="phone" title="请在手机上打开 3D 粒子">
    <div class="pt" :class="{ 'no-hud': !showHud }">
      <!-- 全屏画布。pointer-events 要开着（要收手势），HUD 用 pointer-events:none 盖在上面 -->
      <canvas ref="cv" class="pt-cv" @pointerdown.prevent="onDown" @pointermove.prevent="onMove"
              @pointerup.prevent="onUp" @pointercancel.prevent="onUp" @pointerleave.prevent="onUp" />

      <!-- 顶部信息条：只在第一次进来显示几秒 -->
      <div class="pt-hud">
        <span class="pt-tip">{{ tip }}</span>
        <span class="pt-num">{{ aliveText }}</span>
      </div>

      <button class="pt-gear" type="button" aria-label="设置" @click.stop="panelOpen = !panelOpen">
        <span>⚙</span>
      </button>

      <button class="pt-exit" type="button" aria-label="退出" @click.stop="exit">←</button>

      <!-- 设置面板（参考图那样从底部起，毛玻璃） -->
      <transition name="pt-sheet">
        <div v-if="panelOpen" class="pt-sheet" @pointerdown.stop>
          <div class="pt-sheet-hd">
            <b>粒子</b>
            <button class="pt-sheet-x" type="button" @click="panelOpen = false">完成</button>
          </div>

          <div class="pt-sec">
            <span class="pt-lab">风格</span>
            <div class="pt-pals">
              <button type="button" class="pt-pal" :class="{ on: cfg.style === 'glow' }"
                      @click="set('style', 'glow')">
                <i class="pt-pal-dot" style="background:radial-gradient(circle at 40% 36%,#fff,hsl(286 96% 62%) 46%,hsl(196 96% 56%) 78%)" />
                <span>光晕</span>
              </button>
              <button type="button" class="pt-pal" :class="{ on: cfg.style === 'streak' }"
                      @click="set('style', 'streak')">
                <i class="pt-pal-dot" style="background:linear-gradient(160deg,#fff,hsl(48 100% 58%) 40%,hsl(348 92% 52%))" />
                <span>光轨</span>
              </button>
            </div>
          </div>

          <div class="pt-sec">
            <span class="pt-lab">配色</span>
            <div class="pt-pals">
              <button
                v-for="(p, k) in PALETTES" :key="k"
                type="button" class="pt-pal" :class="{ on: cfg.palette === k }"
                @click="setPalette(k)"
              >
                <i class="pt-pal-dot" :style="{ background: palPreview(k) }" />
                <span>{{ p.name }}</span>
              </button>
            </div>
          </div>

          <label class="pt-row">
            <span>反转颜色</span>
            <input type="checkbox" :checked="cfg.invert" class="pt-switch" @change="set('invert', $event.target.checked)" />
          </label>
          <label class="pt-row">
            <span>自动播放</span>
            <input type="checkbox" :checked="cfg.auto" class="pt-switch" @change="set('auto', $event.target.checked)" />
          </label>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">数量</span>
              <span class="pt-val">{{ cfg.count.toLocaleString() }}</span>
            </div>
            <input type="range" min="400" max="6000" step="100" :value="cfg.count"
                   class="pt-range" @input="set('count', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">粗细</span>
              <span class="pt-val">{{ cfg.size.toFixed(1) }}</span>
            </div>
            <input type="range" min="4" max="40" step="0.5" :value="cfg.size"
                   class="pt-range" @input="set('size', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">拖尾长度</span>
              <span class="pt-val">{{ cfg.trail.toFixed(2) }}</span>
            </div>
            <input type="range" min="0.05" max="1" step="0.01" :value="cfg.trail"
                   class="pt-range" @input="set('trail', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">光晕</span>
              <span class="pt-val">{{ cfg.bloom.toFixed(2) }}</span>
            </div>
            <input type="range" min="0" max="1.5" step="0.05" :value="cfg.bloom"
                   class="pt-range" @input="set('bloom', +$event.target.value)" />
          </div>

          <p class="pt-note">
            一个手指喷一束，两个手指对撞，三个手指转圈，四个以上全屏炸。
          </p>
        </div>
      </transition>
    </div>
  </DeviceGate>
</template>

<script setup>
/**
 * 3D 粒子（v2.46.347）
 *
 * 夜星：「娱乐模块加个 3D 粒子、魔幻粒子的小游戏，只支持手机端打开」
 *       「支持设置粒子数量、尺寸、颜色」「不同的手指数量按压实现不同的效果」。
 *
 * 视觉照着参考图做：粒子是**速度线**不是圆点，中心靠加法混合过曝成白，
 * 外圈才显色相。实现见 composables/useParticles.js。
 *
 * 手势（Pointer Events，天然支持多点）：
 *   1 指 → 从指尖向外喷射
 *   2 指 → 两股朝对方打，中点炸出火花
 *   3 指 → 绕三角中心切向喷（漩涡）
 *   4 指+ → 每个手指全向爆发，速度更快
 *   快速点一下 → 一次性小爆炸
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import DeviceGate from '@/components/common/DeviceGate.vue'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import { createParticleEngine, PALETTES } from '@/composables/useParticles'
import { tick } from '@/utils/haptic'

// useFullscreenPage 自己会在 onMounted 进全屏外壳、onBeforeUnmount 退出，
// 只返回一个 exit（走浏览器历史，跟系统返回键同一条路径）。不用再手动调。
const { exit: exitFullscreen } = useFullscreenPage()

const cv = ref(null)
const panelOpen = ref(false)
const showHud = ref(true)
const alive = ref(0)
const tip = ref('按住屏幕试试')
const aliveText = computed(() => (alive.value ? `${alive.value.toLocaleString()} 粒` : ''))

const cfg = reactive({
  count: 3200,
  size: 26,
  trail: 0.92,
  width: 0.055,
  style: 'glow',      // glow（光晕，照「魔幻粒子3D」）/ streak（光轨，老版）
  palette: 'magic',
  invert: false,
  bloom: 0.85,        // 0 = 关后处理
  auto: false,
})

let engine = null
let raf = 0
let lastT = 0
let hudTimer = 0
let emitAcc = 0

/** 手指：pointerId -> { x, y, px, py, t, moved } */
const fingers = new Map()
/** 按下的瞬间点（判断"点击"而不是"拖动"） */
const downAt = new Map()

// ---------- 生命周期 ----------
onMounted(async () => {
  await nextTick()
  const el = cv.value
  if (!el) return
  // ?debug=1 时保留绘图缓冲，方便探针/录制取像素（生产不带这个参数，省一次缓冲复制）
  const debug = /(?:^|[?&])debug=1/.test(window.location.search)
  engine = createParticleEngine(el, { ...cfg, debug })
  if (!engine.ok) {
    tip.value = engine.reason === 'no-webgl' ? '这台设备的浏览器不支持 WebGL' : '粒子引擎初始化失败'
    return
  }
  resize()
  window.addEventListener('resize', resize)
  window.addEventListener('orientationchange', resize)
  document.addEventListener('visibilitychange', onVis)
  lastT = performance.now()
  raf = requestAnimationFrame(loop)

  hudTimer = window.setTimeout(() => { showHud.value = false }, 5200)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  window.removeEventListener('orientationchange', resize)
  document.removeEventListener('visibilitychange', onVis)
  clearTimeout(hudTimer)
  if (raf) cancelAnimationFrame(raf)
  engine?.dispose()
  engine = null
})

function resize() {
  if (!engine) return
  const w = window.innerWidth
  const h = window.innerHeight
  engine.resize(w, h)
}

function onVis() {
  // 切后台回来 dt 会很大（几秒），一帧推进几秒 = 粒子瞬移，画面直接崩
  if (document.visibilityState === 'visible') lastT = performance.now()
}

function exit() {
  exitFullscreen()
}

// ---------- 手势 ----------
function onDown(e) {
  e.currentTarget.setPointerCapture?.(e.pointerId)
  const p = { x: e.clientX, y: e.clientY, px: e.clientX, py: e.clientY, t: performance.now() }
  fingers.set(e.pointerId, p)
  downAt.set(e.pointerId, { x: e.clientX, y: e.clientY, t: performance.now() })
  tip.value = fingerTip()
  showHud.value = true
  clearTimeout(hudTimer)
  hudTimer = window.setTimeout(() => { showHud.value = false }, 3200)
  tick(0.5)
  burst(e.clientX, e.clientY, 26, 260)
}

function onMove(e) {
  const p = fingers.get(e.pointerId)
  if (!p) return
  p.px = p.x
  p.py = p.y
  p.x = e.clientX
  p.y = e.clientY
}

function onUp(e) {
  const down = downAt.get(e.pointerId)
  const p = fingers.get(e.pointerId)
  // 点一下就抬起（<220ms 且位移 <12px）→ 当作"戳一下"，给一次明显的爆炸
  if (down && p) {
    const dt = performance.now() - down.t
    const dist = Math.hypot(p.x - down.x, p.y - down.y)
    if (dt < 220 && dist < 12) {
      burst(p.x, p.y, 140, 420)
      tick(0.8)
    }
  }
  fingers.delete(e.pointerId)
  downAt.delete(e.pointerId)
  tip.value = fingerTip()
}

function fingerTip() {
  const n = fingers.size
  if (n <= 0) return '按住屏幕试试'
  if (n === 1) return '一根手指：向外喷'
  if (n === 2) return '两根手指：对撞'
  if (n === 3) return '三根手指：漩涡'
  return '四指以上：全屏爆发'
}

/** 一次性爆发 */
function burst(x, y, n, speed) {
  if (!engine) return
  engine.emit(x, y, Math.max(6, Math.round(n * (engine.cfg.count / 3200))), {
    speed,
    spread: Math.PI * 2,
    lifeRange: [0.9, 1.8],
  })
}

// ---------- 主循环 ----------
function loop(now) {
  raf = requestAnimationFrame(loop)
  if (document.visibilityState !== 'visible') {
    lastT = now
    return
  }
  const dt = Math.min(0.05, Math.max(0.001, (now - lastT) / 1000))
  lastT = now

  pump(dt)
  engine.step(dt)
  engine.draw()
  alive.value = engine.alive
}

/**
 * 按当前手指数发射。
 *
 * 总量按 cfg.count 分配，指数越多每指越少 —— 否则十根手指（多人玩）时
 * 瞬间喷出十倍粒子，直接掉帧。
 */
function pump(dt) {
  if (!engine) return
  const n = fingers.size
  const budget = cfg.count * (cfg.style === 'streak' ? 2.4 : 1.7)       // 每秒总发射量上限（够填满池子，又不会瞬间爆）

  if (n === 0) {
    if (!cfg.auto) return
    // 自动播放：从中心缓慢旋转喷
    emitAcc += dt * budget * 0.55
    const a = performance.now() / 2600
    const cx = window.innerWidth / 2 + Math.cos(a) * 40
    const cy = window.innerHeight / 2 + Math.sin(a * 1.3) * 40
    if (emitAcc >= 1) {
      const k = Math.min(60, Math.floor(emitAcc))
      emitAcc -= k
      engine.emit(cx, cy, k, { speed: 520, spread: Math.PI * 2, lifeRange: [1.1, 2.2] })
    }
    return
  }

  emitAcc += dt * budget
  if (emitAcc < 1) return
  // 上限 220 而不是 90：帧率低的时候（老机器 / 软件渲染）每帧只能跑几次，
  // 90 会让实际发射率被帧率卡死（5fps 就只有 450/s，画面稀得像坏了）。
  // 按 dt 累积的 emitAcc 本来就限住了总量，所以放大上限不会瞬间爆。
  const total = Math.min(220, Math.floor(emitAcc))
  emitAcc -= total
  const per = Math.max(1, Math.round(total / n))
  const list = [...fingers.values()]

  if (n === 1) {
    const f = list[0]
    // 拖动时沿着移动方向甩，静止时全向 —— 拖动的手感像"挥光剑"
    const vx = f.x - f.px
    const vy = f.y - f.py
    const moving = Math.hypot(vx, vy) > 2
    engine.emit(f.x, f.y, per, {
      speed: moving ? 760 : 520,
      spread: moving ? Math.PI * 0.5 : Math.PI * 2,
      angle: moving ? Math.atan2(vy, vx) : 0,
      lifeRange: [1.5, 3.0],
    })
    return
  }

  if (n === 2) {
    const [a, b] = list
    // 各自朝对方打，中点会撞出一团更亮的火花（加法混合自动变白）
    for (const [from, to] of [[a, b], [b, a]]) {
      const ang = Math.atan2(to.y - from.y, to.x - from.x)
      engine.emit(from.x, from.y, Math.max(1, Math.round(per * 0.85)), {
        speed: 820,
        spread: Math.PI * 0.3,
        angle: ang,
        lifeRange: [1.4, 2.8],
      })
    }
    const mx = (a.x + b.x) / 2
    const my = (a.y + b.y) / 2
    engine.emit(mx, my, Math.max(1, Math.round(per * 0.5)), {
      speed: 560, spread: Math.PI * 2, lifeRange: [0.8, 1.5],
    })
    return
  }

  if (n === 3) {
    // 绕三角中心切向喷 → 旋涡
    const cx = (list[0].x + list[1].x + list[2].x) / 3
    const cy = (list[0].y + list[1].y + list[2].y) / 3
    for (const f of list) {
      const ang = Math.atan2(f.y - cy, f.x - cx) + Math.PI / 2
      engine.emit(f.x, f.y, per, {
        speed: 700,
        spread: Math.PI * 0.55,
        angle: ang,
        lifeRange: [1.5, 3.0],
      })
    }
    engine.emit(cx, cy, Math.max(1, Math.round(per * 0.6)), {
      speed: 460, spread: Math.PI * 2, lifeRange: [0.9, 1.7],
    })
    return
  }

  // 4 指以上：每指全向爆发，速度更快、寿命更短（画面更"炸"）
  for (const f of list) {
    engine.emit(f.x, f.y, Math.max(1, Math.round(per * 0.8)), {
      speed: 900,
      spread: Math.PI * 2,
      lifeRange: [1.3, 2.6],
      sizeMul: 1.1,
    })
  }
}

// ---------- 设置 ----------
function set(key, val) {
  cfg[key] = val
  if (key === 'invert' || key === 'palette') {
    // 颜色是发射时算的，已有粒子保持原色（这其实是想要的：改配色不回炉旧粒子）
    engine?.applyOptions({ [key]: val })
    return
  }
  engine?.applyOptions({ [key]: val })
}

function setPalette(k) {
  set('palette', k)
  tick(0.6)
}

/** 配色按钮的预览球：取该配色中间色相 + 高饱和，跟实际粒子同一套参数 */
function palPreview(k) {
  const p = PALETTES[k]
  const h = (p.hues[0] + p.hues[1]) / 2
  return `radial-gradient(circle at 34% 30%,
    hsl(${h} ${p.sat[1]}% ${Math.min(92, p.light[1] + 18)}%),
    hsl(${(h + 45) % 360} ${p.sat[0]}% ${p.light[0]}%) 62%,
    hsl(${(h + 300) % 360} ${p.sat[1]}% ${p.light[0] - 8}%))`
}

// 设置改动后如果面板关着，2 秒后自动收起提示条
watch(panelOpen, (v) => {
  if (!v) return
  showHud.value = false
})

// 进页面先把「按住屏幕」的提示留在中间一会儿
onMounted(() => {
  setTimeout(() => {
    if (!fingers.size) showHud.value = false
  }, 5200)
})
</script>

<style scoped>
.pt {
  position: fixed;
  inset: 0;
  background: #000;
  overflow: hidden;
  touch-action: none;      /* 手指滑动不要触发页面滚动/缩放 */
  user-select: none;
  -webkit-user-select: none;
  color: #f4f0e8;
}
.pt-cv { display: block; width: 100%; height: 100%; }

/* ---------- 提示条 ---------- */
.pt-hud {
  position: absolute;
  top: calc(env(safe-area-inset-top, 0px) + 14px);
  left: 0; right: 0;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  pointer-events: none;
  transition: opacity .5s ease;
}
.no-hud .pt-hud { opacity: 0; }
.pt-tip {
  font-size: 13px; letter-spacing: .04em;
  color: rgba(255, 255, 255, .72);
  text-shadow: 0 1px 6px rgba(0, 0, 0, .8);
  transition: opacity .2s;
}
.pt-num {
  font-size: 11px; font-variant-numeric: tabular-nums;
  color: rgba(255, 255, 255, .38);
  letter-spacing: .06em;
}

/* ---------- 角上的两个按钮 ---------- */
.pt-gear, .pt-exit {
  position: absolute;
  width: 40px; height: 40px; border-radius: 50%;
  display: grid; place-items: center;
  border: 1px solid rgba(255, 255, 255, .14);
  background: rgba(255, 255, 255, .07);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: rgba(255, 255, 255, .82);
  font-size: 17px; cursor: pointer;
  transition: background-color .16s, transform .16s;
}
.pt-gear:active, .pt-exit:active { transform: scale(.93); background: rgba(255, 255, 255, .16); }
.pt-gear { right: calc(env(safe-area-inset-right, 0px) + 14px); bottom: calc(env(safe-area-inset-bottom, 0px) + 20px); }
.pt-exit { left: calc(env(safe-area-inset-left, 0px) + 14px); top: calc(env(safe-area-inset-top, 0px) + 14px); font-size: 15px; }

/* ---------- 设置面板 ---------- */
.pt-sheet {
  position: absolute;
  left: 10px; right: 10px;
  bottom: calc(env(safe-area-inset-bottom, 0px) + 10px);
  max-height: 76dvh;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 14px 16px 20px;
  border-radius: 20px;
  background: rgba(22, 22, 26, .82);
  border: 1px solid rgba(255, 255, 255, .1);
  backdrop-filter: blur(22px) saturate(1.2);
  -webkit-backdrop-filter: blur(22px) saturate(1.2);
  box-shadow: 0 -8px 40px rgba(0, 0, 0, .5);
}
.pt-sheet-hd {
  display: flex; align-items: center; justify-content: space-between;
  padding-bottom: 10px; margin-bottom: 4px;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
}
.pt-sheet-hd b { font-size: 15px; font-weight: 700; }
.pt-sheet-x {
  border: 0; background: transparent; cursor: pointer;
  color: #a9c8ff; font: inherit; font-size: 13.5px; font-weight: 600;
}

.pt-sec { margin-top: 14px; }
.pt-lab { font-size: 12.5px; color: rgba(255, 255, 255, .62); letter-spacing: .03em; }
.pt-lab-row { display: flex; align-items: baseline; justify-content: space-between; }
.pt-val {
  font-size: 12px; color: rgba(255, 255, 255, .5);
  font-variant-numeric: tabular-nums;
}

.pt-pals { display: flex; gap: 8px; margin-top: 9px; }
.pt-pal {
  flex: 1 1 0; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 10px 4px 8px; border-radius: 13px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, .1);
  background: rgba(255, 255, 255, .04);
  color: rgba(255, 255, 255, .68); font: inherit; font-size: 12px;
  transition: border-color .16s, background-color .16s;
}
.pt-pal.on { border-color: rgba(255, 255, 255, .6); background: rgba(255, 255, 255, .1); color: #fff; }
.pt-pal-dot {
  width: 34px; height: 34px; border-radius: 50%;
  box-shadow: inset 0 0 6px rgba(0, 0, 0, .35), 0 2px 8px rgba(0, 0, 0, .35);
}

.pt-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 0; margin-top: 4px;
  border-bottom: 1px solid rgba(255, 255, 255, .07);
  font-size: 13.5px; color: rgba(255, 255, 255, .82);
}
/* 开关：用原生 checkbox 改外观，避免为一个面板引入组件库控件 */
.pt-switch {
  appearance: none; -webkit-appearance: none;
  width: 46px; height: 27px; border-radius: 999px; margin: 0;
  background: rgba(255, 255, 255, .16); position: relative; cursor: pointer;
  transition: background-color .2s;
}
.pt-switch::after {
  content: ''; position: absolute; top: 3px; left: 3px;
  width: 21px; height: 21px; border-radius: 50%;
  background: #fff; transition: transform .2s cubic-bezier(.2, .8, .3, 1);
}
.pt-switch:checked { background: #7aa2ff; }
.pt-switch:checked::after { transform: translateX(19px); }

.pt-range {
  width: 100%; margin-top: 10px; height: 22px;
  appearance: none; -webkit-appearance: none; background: transparent;
}
.pt-range::-webkit-slider-runnable-track {
  height: 5px; border-radius: 999px;
  background: rgba(255, 255, 255, .16);
}
.pt-range::-webkit-slider-thumb {
  appearance: none; -webkit-appearance: none;
  width: 16px; height: 16px; margin-top: -5.5px; border-radius: 50%;
  background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, .45);
}
.pt-note {
  margin: 16px 0 0; font-size: 11.5px; line-height: 1.7;
  color: rgba(255, 255, 255, .38);
}

/* 抽屉进出 */
.pt-sheet-enter-active, .pt-sheet-leave-active { transition: transform .26s cubic-bezier(.2, .8, .3, 1), opacity .26s; }
.pt-sheet-enter-from, .pt-sheet-leave-to { transform: translateY(24px); opacity: 0; }
</style>

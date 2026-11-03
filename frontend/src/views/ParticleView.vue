<template>
  <DeviceGate need="phone" title="请在手机上打开 3D 粒子">
    <div class="pt" :class="{ 'no-hud': !showHud }">
      <!-- 全屏画布。pointer-events 要开着（要收手势），HUD 用 pointer-events:none 盖在上面 -->
      <canvas ref="cv" class="pt-cv" @pointerdown.prevent="onDown" @pointermove.prevent="onMove"
              @pointerup.prevent="onUp" @pointercancel.prevent="onUp" @pointerleave.prevent="onUp" />

      <!-- 顶部信息条：只在第一次进来显示几秒 -->
      <div class="pt-hud">
        <span class="pt-tip">{{ tip }}</span>
        <span class="pt-num">{{ fpsText }}</span>
      </div>

      <button class="pt-gear" type="button" aria-label="设置" @click.stop="panelOpen = !panelOpen">
        <span>⚙</span>
      </button>

      <button class="pt-exit" type="button" aria-label="退出" @click.stop="exit">←</button>

      <!-- 设置面板（从底部起，毛玻璃） -->
      <transition name="pt-sheet">
        <div v-if="panelOpen" class="pt-sheet" @pointerdown.stop>
          <div class="pt-sheet-hd">
            <b>流体</b>
            <button class="pt-sheet-x" type="button" @click="panelOpen = false">完成</button>
          </div>

          <div class="pt-sec">
            <span class="pt-lab">质感</span>
            <div class="pt-pals">
              <button type="button" class="pt-pal" :class="{ on: cfg.mode === 0 }"
                      @click="set('mode', 0)">
                <i class="pt-pal-dot" style="background:radial-gradient(circle at 36% 32%,#fff 4%,hsl(286 96% 60%) 38%,hsl(196 96% 54%) 78%)" />
                <span>浓郁</span>
              </button>
              <button type="button" class="pt-pal" :class="{ on: cfg.mode === 1 }"
                      @click="set('mode', 1)">
                <i class="pt-pal-dot" style="background:conic-gradient(from 20deg,#ff2d55,#ffcc00,#34c759,#00c7be,#5e5ce6,#ff2d55)" />
                <span>油膜</span>
              </button>
            </div>
          </div>

          <div class="pt-sec">
            <span class="pt-lab">配色</span>
            <div class="pt-pals">
              <button v-for="(p, k) in PALETTES" :key="k"
                      type="button" class="pt-pal" :class="{ on: cfg.palette === k }"
                      @click="setPalette(k)">
                <i class="pt-pal-dot" :style="{ background: palPreview(k) }" />
                <span>{{ p.name }}</span>
              </button>
            </div>
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">浓度</span>
              <span class="pt-val">{{ cfg.densityDissipation.toFixed(2) }}</span>
            </div>
            <input type="range" min="0.2" max="4" step="0.05" :value="cfg.densityDissipation"
                   class="pt-range" @input="set('densityDissipation', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">流速</span>
              <span class="pt-val">{{ cfg.velocityDissipation.toFixed(2) }}</span>
            </div>
            <input type="range" min="0.02" max="1" step="0.02" :value="cfg.velocityDissipation"
                   class="pt-range" @input="set('velocityDissipation', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">卷曲</span>
              <span class="pt-val">{{ cfg.curl.toFixed(0) }}</span>
            </div>
            <input type="range" min="0" max="60" step="1" :value="cfg.curl"
                   class="pt-range" @input="set('curl', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">笔触</span>
              <span class="pt-val">{{ brushPx }}px</span>
            </div>
            <input type="range" min="0.0001" max="0.002" step="0.00005" :value="cfg.splatRadius"
                   class="pt-range" @input="set('splatRadius', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">光晕</span>
              <span class="pt-val">{{ cfg.glow.toFixed(2) }}</span>
            </div>
            <input type="range" min="0" max="3" step="0.05" :value="cfg.glow"
                   class="pt-range" @input="set('glow', +$event.target.value)" />
          </div>

          <div class="pt-sec">
            <div class="pt-lab-row">
              <span class="pt-lab">纹理</span>
              <span class="pt-val">{{ cfg.detail.toFixed(2) }}</span>
            </div>
            <input type="range" min="0" max="1" step="0.05" :value="cfg.detail"
                   class="pt-range" @input="set('detail', +$event.target.value)" />
          </div>

          <label class="pt-row">
            <span>反转颜色</span>
            <input type="checkbox" :checked="cfg.invert" class="pt-switch" @change="set('invert', $event.target.checked)" />
          </label>

          <p class="pt-note">
            手指划过的痕迹会像墨一样被推开、卷起来，松手后靠惯性继续流。
          </p>
        </div>
      </transition>
    </div>
  </DeviceGate>
</template>

<script setup>
/**
 * 3D 粒子 → 流体（v2.46.355）
 *
 * 夜星：「不行，你这个设计太粗糙了，我现在就要跟逆向的 apk 一模一样的效果」。
 *
 * 上一版是粒子 + 辉光后处理。粒子系统本质是「一堆点各自飞」，做不出
 * 「黏稠、卷曲、被推开」的观感。那个 APK 用的是 Stable Fluids：
 * 速度场 + 压力投影 + 半拉格朗日平流，见 composables/useFluid.js 顶部注释。
 *
 * 手势还是那套 Pointer Events（天然多点）：
 *   单指拖动 → 注入速度和染料
 *   多指同时 → 每根手指各自一股
 *   点一下   → 原地一滴浓墨（给一点随机初速，会自己散开）
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import DeviceGate from '@/components/common/DeviceGate.vue'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import { createFluidEngine, PALETTES } from '@/composables/useFluid'
import { tick } from '@/utils/haptic'

const { exit: exitFullscreen } = useFullscreenPage()

const cv = ref(null)
const panelOpen = ref(false)
const showHud = ref(true)
const fps = ref(0)
const tip = ref('按住屏幕试试')

const cfg = reactive({
  mode: 0,
  palette: 'magic',
  densityDissipation: 0.6,
  velocityDissipation: 0.9,
  curl: 24,
  splatRadius: 0.0005,
  glow: 1.5,
  detail: 0.55,
  invert: false,
})

const fpsText = computed(() => (fps.value ? `${fps.value} fps` : ''))
/** 笔触半径从 uv 换算成屏幕像素，面板上给人看得懂的数 */
const brushPx = computed(() => Math.round(Math.sqrt(cfg.splatRadius) * 800))

let engine = null
let raf = 0
let lastT = 0
let hudTimer = 0
let idleAcc = 0
let frameAcc = 0
let frameCnt = 0

/** pointerId -> { x, y, px, py, t } */
const fingers = new Map()
const downAt = new Map()

onMounted(async () => {
  await nextTick()
  const el = cv.value
  if (!el) return
  // ?debug=1 时保留绘图缓冲，方便探针取像素
  const debug = /(?:^|[?&])debug=1/.test(window.location.search)
  engine = createFluidEngine(el, { ...cfg, debug })
  if (!engine.ok) {
    tip.value = engine.reason === 'no-webgl' ? '这台设备的浏览器不支持 WebGL' : '流体引擎初始化失败'
    return
  }
  // 探针/调试用：dev 下把引擎挂到 window，方便直接调 splat 验证
  if (import.meta.env.DEV) window.__fluid = engine
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
  engine.resize(window.innerWidth, window.innerHeight)
}

function onVis() {
  // 切后台回来 dt 会很大，一帧推进几秒 = 整锅汤瞬移，直接跳过
  if (document.visibilityState === 'visible') lastT = performance.now()
}

function exit() {
  exitFullscreen()
}

function onDown(e) {
  try { e.currentTarget.setPointerCapture?.(e.pointerId) } catch { /* 合成事件没有真实 pointerId */ }
  const p = { x: e.clientX, y: e.clientY, px: e.clientX, py: e.clientY, t: performance.now() }
  fingers.set(e.pointerId, p)
  downAt.set(e.pointerId, { x: e.clientX, y: e.clientY, t: performance.now() })
  tip.value = fingerTip()
  showHud.value = true
  clearTimeout(hudTimer)
  hudTimer = window.setTimeout(() => { showHud.value = false }, 3200)
  tick(0.5)
  drop(e.clientX, e.clientY)
}

function onMove(e) {
  const p = fingers.get(e.pointerId)
  if (!p) return
  p.x = e.clientX
  p.y = e.clientY
}

function onUp(e) {
  const down = downAt.get(e.pointerId)
  const p = fingers.get(e.pointerId)
  // 点一下就抬起（<220ms、位移 <12px）→ 再来一滴大的
  if (down && p) {
    const dt = performance.now() - down.t
    const dist = Math.hypot(p.x - down.x, p.y - down.y)
    if (dt < 220 && dist < 12) {
      drop(p.x, p.y, 2.2)
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
  if (n === 1) return '拖动：把颜色推开'
  return `${n} 根手指：几股一起搅`
}

/** 原地一滴：给一点随机初速，它自己会被卷开 */
function drop(x, y, mul = 1) {
  if (!engine) return
  const a = Math.random() * Math.PI * 2
  const s = 26 * mul
  engine.splat(x, y, Math.cos(a) * s, Math.sin(a) * s, engine.pointerColor(x, y))
}

/** 按手指位移注入速度 + 染料 */
function pump() {
  if (!engine) return
  if (!fingers.size) {
    // 没人碰的时候让画面别死：偶尔在中间附近滴一滴
    idleAcc += 1
    if (idleAcc > 200) {
      idleAcc = 0
      const cx = window.innerWidth * (0.5 + (Math.random() - 0.5) * 0.35)
      const cy = window.innerHeight * (0.5 + (Math.random() - 0.5) * 0.35)
      drop(cx, cy, 0.5)
    }
    return
  }
  for (const f of fingers.values()) {
    const dx = f.x - f.px
    const dy = f.y - f.py
    if (import.meta.env.DEV) {
      window.__dbg = window.__dbg || { splats: 0, sumDx: 0 }
      window.__dbg.splats++
      window.__dbg.sumDx += Math.abs(dx)
    }
    if (Math.abs(dx) > 0.4 || Math.abs(dy) > 0.4) {
      engine.splat(f.x, f.y, dx, dy, engine.pointerColor(f.x, f.y))
      f.px = f.x
      f.py = f.y
    }
  }
}

function loop(now) {
  raf = requestAnimationFrame(loop)
  if (document.visibilityState !== 'visible') {
    lastT = now
    return
  }
  const dt = Math.min(0.05, Math.max(0.001, (now - lastT) / 1000))
  lastT = now

  pump()
  engine.step(dt)
  engine.draw()

  frameAcc += dt
  frameCnt++
  if (frameAcc >= 0.5) {
    fps.value = Math.round(frameCnt / frameAcc)
    frameAcc = 0
    frameCnt = 0
  }
}

function set(key, val) {
  cfg[key] = val
  engine?.applyOptions({ [key]: val })
  if (key === 'mode' || key === 'palette') tick(0.6)
}

function setPalette(k) {
  set('palette', k)
}

/** 配色按钮的预览球：跟 splat 用的是同一套 HSV 参数 */
function palPreview(k) {
  const p = PALETTES[k]
  const h0 = p.hues[0]
  const h1 = p.hues[1] > p.hues[0] ? p.hues[1] : p.hues[0]
  const h = (h0 + h1) / 2
  return `radial-gradient(circle at 36% 32%,
    #fff 3%,
    hsl(${h} ${98 * p.sat}% 56%) 42%,
    hsl(${(h + 55) % 360} ${98 * p.sat}% 44%) 82%)`
}

watch(panelOpen, (v) => {
  if (!v) return
  showHud.value = false
})

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


<template>
  <DeviceGate need="phone" title="请在手机上打开 魔幻粒子3D">
    <!-- ========== 启动页（splash.xml：纯黑 + 居中内容） ========== -->
    <transition name="fade">
      <div v-if="splashing" class="sp">
        <div class="sp-logo">魔幻粒子3D</div>
        <div class="sp-sub">不可错过的视觉盛宴</div>
        <div class="sp-spin" />
      </div>
    </transition>

    <!-- ========== 主界面（magic3d_main.xml） ========== -->
    <div v-show="!splashing" class="app">
      <canvas ref="cv" class="cv"
              @pointerdown.prevent="onDown" @pointermove.prevent="onMove"
              @pointerup.prevent="onUp" @pointercancel.prevent="onUp" @pointerleave.prevent="onUp" />

      <!-- 四角热区：布局里就是 4 个 1dp 的透明 Button，不抢视觉只接手势 -->
      <button class="hotzone tl" type="button" aria-label="上一个" @click="stepEffect(-1)" />
      <button class="hotzone tr" type="button" aria-label="下一个" @click="stepEffect(1)" />
      <button class="hotzone bl" type="button" aria-label="清屏" @click="clearAll" />
      <button class="hotzone br" type="button" aria-label="菜单" @click="toggleMenu" />

      <!-- 左上返回（网站需要，原 App 的二级页也是这个位置这个图标） -->
      <button class="back" type="button" aria-label="返回" @click="exit">
        <svg viewBox="0 0 24 24"><path d="M15.4 7.4 14 6l-6 6 6 6 1.4-1.4L10.8 12z" /></svg>
      </button>

      <!-- 效果名 + 录制按钮（布局里是 visibility=gone，隐藏菜单后才出现） -->
      <div class="effname" :class="{ on: menuHidden }">{{ preset.name }}</div>
      <button class="rec" type="button" :class="{ on: menuHidden }" aria-label="录制" @click="toggleRec">
        <i />
      </button>

      <!-- 底部浮动工具栏（FloatingToolbar：64dp、底边 52dp、6 个图标） -->
      <div class="ftool" :class="{ hide: menuHidden }">
        <button v-for="t in TOOLS" :key="t.key" type="button"
                class="ft-btn" :class="{ dim: t.dim }" :aria-label="t.label"
                @click="run(t.key)">
          <svg viewBox="0 0 24 24"><use :href="'#i-' + t.icon" /></svg>
        </button>
      </div>

      <!-- 右下 FAB（ic_plus，青绿） -->
      <button class="fab" type="button" :class="{ hide: menuHidden }" aria-label="选择效果" @click="openPicker">
        <svg viewBox="0 0 24 24"><use href="#i-plus" /></svg>
      </button>

      <!-- ========== 效果选择（FAB 呼出） ========== -->
      <transition name="up">
        <div v-if="picker" class="sheet pick" @pointerdown.stop>
          <div class="sheet-hd">
            <b>选择效果</b>
            <button type="button" @click="picker = false">关闭</button>
          </div>
          <div class="pick-grid">
            <button v-for="p in PRESETS" :key="p.key" type="button"
                    class="pick-item" :class="{ on: p.key === preset.key }"
                    @click="choosePreset(p)">
              <i :style="{ background: swatch(p) }" />
              <span>{{ p.name }}</span>
            </button>
          </div>
        </div>
      </transition>

      <!-- ========== 自定义效果（dialog_particle_setting：卡片 + 滑杆 + 恢复） ========== -->
      <transition name="up">
        <div v-if="panel" class="sheet panel" @pointerdown.stop>
          <div class="sheet-hd">
            <b>自定义效果</b>
            <button type="button" @click="panel = false">完成</button>
          </div>
          <div v-for="s in SLIDERS" :key="s.key" class="sl">
            <span class="sl-lab">{{ s.label }}</span>
            <input class="sl-range" type="range" :min="s.min" :max="s.max" :step="s.step"
                   :value="cfg[s.key]" @input="setCfg(s.key, +$event.target.value)" />
            <span class="sl-val">{{ fmt(s) }}</span>
          </div>
          <div class="sl">
            <span class="sl-lab">颜色</span>
            <div class="colors">
              <button v-for="(p, k) in PALETTES" :key="k" type="button"
                      class="dot" :class="{ on: cfg.palette === k }"
                      :style="{ background: swatch({ palette: k }) }"
                      @click="setCfg('palette', k)" />
            </div>
          </div>
          <button class="restore" type="button" aria-label="恢复默认" @click="restore">
            <svg viewBox="0 0 24 24"><use href="#i-restore" /></svg>
          </button>
        </div>
      </transition>

      <!-- ========== 我的截图 ========== -->
      <transition name="up">
        <div v-if="gallery" class="sheet shots" @pointerdown.stop>
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

      <!-- 轻提示 -->
      <transition name="fade">
        <div v-if="toast" class="toast">{{ toast }}</div>
      </transition>
    </div>

    <!-- 图标集：照 APK 里那几个 PNG 的形状重画 -->
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
      <symbol id="i-restore" viewBox="0 0 24 24">
        <path d="M12 5a7 7 0 1 1-6.6 9.3M5 5v4h4" />
      </symbol>
    </svg>
  </DeviceGate>
</template>

<script setup>
/**
 * 魔幻粒子3D（复刻版）v2.46.356
 *
 * 夜星：「你给我把之前的全部删除，按照逆向的，全盘照抄它的设计，
 *        一摸一样的界面，一摸一样的交互，功能全都一摸一样」。
 *
 * 界面全部照 res/layout/ 里的布局还原：
 *   · magic3d_main.xml   —— 全屏画布 + 底部 FloatingToolbar(64dp/底 52dp)
 *                            + 右下 FAB(ic_plus，青绿) + 录制按钮(48dp) + 四角 1dp 热区
 *   · menu_demo.xml      —— 工具栏 6 项：自定义效果 / 购买 / 保存图片 /
 *                            设为动态壁纸 / 隐藏菜单 / 清屏（图标照 icon_*.png）
 *   · dialog_particle_setting.xml —— 卡片 + 滑杆 + 底部「恢复默认」
 *   · splash.xml         —— 纯黑启动页
 *   · resources.arsc     —— 8 个档位名
 *
 * 渲染是 GPU 流体（composables/useFluid.js），8 档用同一套管线配不同参数对位。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import DeviceGate from '@/components/common/DeviceGate.vue'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import { createFluidEngine, PALETTES, PRESETS } from '@/composables/useFluid'
import { tick } from '@/utils/haptic'

const { exit: exitFullscreen } = useFullscreenPage()

/** 工具栏 6 项，顺序照 menu_demo.xml */
const TOOLS = [
  { key: 'custom', icon: 'settings', label: '自定义效果' },
  { key: 'buy', icon: 'heart', label: '我的截图', dim: true },
  { key: 'save', icon: 'image', label: '保存图片' },
  { key: 'wall', icon: 'grid', label: '设为动态壁纸', dim: true },
  { key: 'hide', icon: 'dots', label: '隐藏菜单' },
  { key: 'clear', icon: 'reset', label: '清屏', dim: true },
]

const SLIDERS = [
  { key: 'curl', label: '卷曲', min: 0, max: 60, step: 1 },
  { key: 'glow', label: '光晕', min: 0, max: 3, step: 0.05 },
  { key: 'detail', label: '纹理', min: 0, max: 1, step: 0.05 },
  { key: 'densityDissipation', label: '浓度', min: 0.1, max: 3, step: 0.05 },
]

const cv = ref(null)
const splashing = ref(true)
const picker = ref(false)
const panel = ref(false)
const gallery = ref(false)
const menuHidden = ref(false)
const toast = ref('')
const shots = ref([])
const idx = ref(0)

const preset = computed(() => PRESETS[idx.value])

const cfg = reactive({
  mode: 0,
  palette: 'magic',
  curl: 24,
  glow: 1.5,
  detail: 0.55,
  densityDissipation: 0.6,
  velocityDissipation: 0.9,
  splatRadius: 0.0005,
  rim: 18,
  invert: false,
})

let engine = null
let raf = 0
let lastT = 0
let toastTimer = 0
let idleAcc = 0
let recorder = null
let recChunks = []

const fingers = new Map()
const downAt = new Map()

// ---------------- 生命周期 ----------------
onMounted(async () => {
  await nextTick()
  const el = cv.value
  if (!el) return
  const debug = /(?:^|[?&])debug=1/.test(window.location.search)
  engine = createFluidEngine(el, { ...cfg, debug })
  if (!engine.ok) {
    toast.value = engine.reason === 'no-webgl' ? '这台设备的浏览器不支持 WebGL' : '引擎初始化失败'
    return
  }
  if (import.meta.env.DEV) window.__fluid = engine
  resize()
  applyPreset(PRESETS[0])

  window.addEventListener('resize', resize)
  window.addEventListener('orientationchange', resize)
  document.addEventListener('visibilitychange', onVis)
  lastT = performance.now()
  raf = requestAnimationFrame(loop)

  try {
    shots.value = JSON.parse(localStorage.getItem('xh_particle_shots') || '[]').slice(0, 24)
  } catch { /* ignore */ }

  // 启动页留 1.3 秒，跟原版一样先进黑屏再进主界面
  window.setTimeout(() => { splashing.value = false }, 1300)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  window.removeEventListener('orientationchange', resize)
  document.removeEventListener('visibilitychange', onVis)
  clearTimeout(toastTimer)
  if (raf) cancelAnimationFrame(raf)
  if (recorder && recorder.state === 'recording') recorder.stop()
  engine?.dispose()
  engine = null
})

function resize() {
  if (!engine) return
  engine.resize(window.innerWidth, window.innerHeight)
}

function onVis() {
  if (document.visibilityState === 'visible') lastT = performance.now()
}

function exit() {
  exitFullscreen()
}

// ---------------- 手势 ----------------
function onDown(e) {
  try { e.currentTarget.setPointerCapture?.(e.pointerId) } catch { /* 合成事件没有真 pointerId */ }
  fingers.set(e.pointerId, { x: e.clientX, y: e.clientY, px: e.clientX, py: e.clientY })
  downAt.set(e.pointerId, { x: e.clientX, y: e.clientY, t: performance.now() })
  if (menuHidden.value) {
    menuHidden.value = false
    return
  }
  drop(e.clientX, e.clientY, 1)
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
  if (d && p) {
    const dt = performance.now() - d.t
    const dist = Math.hypot(p.x - d.x, p.y - d.y)
    // 轻点再来一下，跟原版一样"点一下就散开"
    if (dt < 200 && dist < 10) drop(p.x, p.y, 1.8)
  }
  fingers.delete(e.pointerId)
  downAt.delete(e.pointerId)
}

function drop(x, y, mul = 1) {
  if (!engine) return
  const a = Math.random() * Math.PI * 2
  const s = 24 * mul
  engine.splat(x, y, Math.cos(a) * s, Math.sin(a) * s, engine.pointerColor(x, y))
}

function pump() {
  if (!engine) return
  if (!fingers.size) {
    idleAcc++
    if (idleAcc > 160) {
      idleAcc = 0
      const cx = window.innerWidth * (0.5 + (Math.random() - 0.5) * 0.4)
      const cy = window.innerHeight * (0.5 + (Math.random() - 0.5) * 0.4)
      drop(cx, cy, 0.55)
    }
    return
  }
  for (const f of fingers.values()) {
    const dx = f.x - f.px
    const dy = f.y - f.py
    if (Math.abs(dx) > 0.4 || Math.abs(dy) > 0.4) {
      engine.splat(f.x, f.y, dx, dy, engine.pointerColor(f.x, f.y))
      f.px = f.x
      f.py = f.y
    }
  }
}

function loop(now) {
  raf = requestAnimationFrame(loop)
  if (document.visibilityState !== 'visible') { lastT = now; return }
  const dt = Math.min(0.05, Math.max(0.001, (now - lastT) / 1000))
  lastT = now
  pump()
  engine.step(dt)
  engine.draw()
}

// ---------------- 档位 ----------------
function applyPreset(p) {
  if (!p) return
  idx.value = Math.max(0, PRESETS.findIndex((x) => x.key === p.key))
  Object.assign(cfg, {
    mode: p.mode,
    palette: p.palette,
    curl: p.curl,
    glow: p.glow,
    detail: p.detail,
    densityDissipation: p.density,
  })
  engine?.applyOptions({ ...cfg })
  engine?.clear()
}

function choosePreset(p) {
  applyPreset(p)
  picker.value = false
  showToast(p.name)
  tick(0.6)
}

function stepEffect(dir) {
  const n = PRESETS.length
  applyPreset(PRESETS[(idx.value + dir + n) % n])
  showToast(preset.value.name)
  tick(0.5)
}

function showToast(msg, ms = 1200) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toast.value = '' }, ms)
}

// ---------------- 工具栏 ----------------
function run(key) {
  if (key === 'custom') { panel.value = true; picker.value = false; gallery.value = false; return }
  if (key === 'save') { saveShot(); return }
  if (key === 'hide') { toggleMenu(); return }
  if (key === 'clear') { clearAll(); return }
  if (key === 'wall') { showToast('网页版做不了动态壁纸，先保存成图片吧', 1900); return }
  if (key === 'buy') { gallery.value = true; panel.value = false; picker.value = false; return }
}

function toggleMenu() {
  menuHidden.value = !menuHidden.value
  tick(0.5)
}

function clearAll() {
  engine?.clear()
  tick(0.5)
}

function openPicker() {
  picker.value = true
  panel.value = false
  gallery.value = false
  tick(0.4)
}

// ---------------- 保存 / 截图 ----------------
function saveShot() {
  const c = cv.value
  if (!c) return
  const data = c.toDataURL('image/png')
  const a = document.createElement('a')
  a.href = data
  a.download = `魔幻粒子3D-${Date.now()}.png`
  a.click()
  shots.value = [data, ...shots.value].slice(0, 24)
  try { localStorage.setItem('xh_particle_shots', JSON.stringify(shots.value)) } catch { /* 满了就算了 */ }
  showToast('已保存')
  tick(0.7)
}

function delShot(i) {
  shots.value.splice(i, 1)
  try { localStorage.setItem('xh_particle_shots', JSON.stringify(shots.value)) } catch { /* ignore */ }
}

// ---------------- 录制（MediaRecorder，网页版能做的部分） ----------------
function toggleRec() {
  if (!cv.value || !cv.value.captureStream || typeof MediaRecorder === 'undefined') {
    showToast('这台设备的浏览器不支持录制', 1800)
    return
  }
  if (recorder && recorder.state === 'recording') {
    recorder.stop()
    return
  }
  try {
    const stream = cv.value.captureStream(30)
    recorder = new MediaRecorder(stream, { mimeType: 'video/webm' })
    recChunks = []
    recorder.ondataavailable = (e) => { if (e.data.size) recChunks.push(e.data) }
    recorder.onstop = () => {
      const blob = new Blob(recChunks, { type: 'video/webm' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `魔幻粒子3D-${Date.now()}.webm`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 4000)
      showToast('录制完成')
    }
    recorder.start()
    showToast('录制中，再点一次结束', 2000)
    tick(0.7)
  } catch {
    showToast('录制启动失败', 1600)
  }
}

// ---------------- 参数 ----------------
function setCfg(k, v) {
  cfg[k] = v
  engine?.applyOptions({ [k]: v })
  if (k === 'palette') tick(0.4)
}

function restore() {
  applyPreset(preset.value)
  showToast('已恢复')
  tick(0.5)
}

function fmt(s) {
  return Number(cfg[s.key]).toFixed(2)
}

function swatch(p) {
  const pal = PALETTES[p.palette] || PALETTES.magic
  const h = (pal.hues[0] + Math.min(pal.hues[1], pal.hues[0] + 60)) / 2
  return `radial-gradient(circle at 34% 30%, #fff 4%,
    hsl(${h} ${Math.round(96 * pal.sat)}% 58%) 45%,
    hsl(${(h + 46) % 360} ${Math.round(96 * pal.sat)}% 44%) 85%)`
}
</script>

<style scoped>
.sprite { position: absolute; width: 0; height: 0; overflow: hidden; }

/* ---------- 启动页 ---------- */
.sp {
  position: fixed;
  inset: 0;
  background: #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  z-index: 30;
}
.sp-logo { color: #fff; font-size: 22px; letter-spacing: 3px; font-weight: 300; }
.sp-sub { color: rgba(255, 255, 255, 0.45); font-size: 12px; letter-spacing: 1px; }
.sp-spin {
  position: absolute;
  bottom: 64px;
  width: 26px; height: 26px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.16);
  border-top-color: #00bfa5;
  animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ---------- 主界面 ---------- */
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
.cv { position: absolute; inset: 0; display: block; width: 100%; height: 100%; }

/* 四角热区：布局里就是 4 个 1dp 的透明 Button */
.hotzone {
  position: absolute;
  width: 44px; height: 44px;
  padding: 0; border: 0;
  background: transparent;
}
.hotzone.tl { left: 0; top: 0; }
.hotzone.tr { right: 0; top: 0; }
.hotzone.bl { left: 0; bottom: 0; }
.hotzone.br { right: 0; bottom: 0; }

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

/* 效果名：TextView 14sp 白色，居中偏下 */
.effname {
  position: absolute;
  left: 0; right: 0;
  bottom: 96px;
  text-align: center;
  color: #fff;
  font-size: 14px;
  letter-spacing: 0.5px;
  opacity: 0;
  transition: opacity 0.25s;
  pointer-events: none;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.7);
}
.effname.on { opacity: 0.9; }

/* 录制按钮：48dp 圆环 + 内点 */
.rec {
  position: absolute;
  left: 50%;
  bottom: calc(26px + env(safe-area-inset-bottom, 0px));
  transform: translateX(-50%);
  width: 48px; height: 48px;
  border-radius: 50%;
  border: 3px solid #ff5a4e;
  background: transparent;
  display: grid; place-items: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
}
.rec.on { opacity: 1; pointer-events: auto; }
.rec i {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #ff5a4e;
  animation: pulse 1.1s ease-in-out infinite;
}
@keyframes pulse { 50% { transform: scale(0.72); opacity: 0.6; } }

/* 底部浮动工具栏：64dp 高、底边 52dp、圆角、投影 */
.ftool {
  position: absolute;
  left: 12px;
  right: 84px;           /* 原布局是 match_parent + FAB 浮在上面，第 6 个图标会被 FAB 压住，这里让位 */
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
  transition: background 0.15s;
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

/* FAB：ic_plus，青绿 */
.fab {
  position: absolute;
  right: 16px;
  bottom: calc(84px + env(safe-area-inset-bottom, 0px));
  width: 56px; height: 56px;
  border-radius: 50%;
  border: 0;
  background: #00bfa5;
  box-shadow: 0 6px 18px rgba(0, 191, 165, 0.45);
  display: grid; place-items: center;
  transition: transform 0.2s ease, opacity 0.2s ease;
  z-index: 6;
}
.fab svg { width: 26px; height: 26px; fill: #fff; }
.fab:active { transform: scale(0.94); }
.fab.hide { transform: scale(0.4); opacity: 0; pointer-events: none; }

/* ---------- 底部面板 ---------- */
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
.sheet-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 14px;
}
.sheet-hd b { color: #fff; font-size: 15px; font-weight: 500; }
.sheet-hd button {
  border: 0; background: transparent;
  color: #00bfa5; font-size: 14px;
  padding: 6px 4px;
}

.pick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px 8px;
  padding-bottom: 6px;
}
.pick-item {
  border: 0; background: transparent;
  display: flex; flex-direction: column; align-items: center; gap: 7px;
}
.pick-item i {
  width: 54px; height: 54px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12);
  transition: box-shadow 0.18s, transform 0.18s;
}
.pick-item span { color: rgba(255, 255, 255, 0.62); font-size: 11px; }
.pick-item.on i {
  box-shadow: 0 0 0 2px #00bfa5, 0 0 18px rgba(0, 191, 165, 0.5);
  transform: scale(1.06);
}
.pick-item.on span { color: #fff; }

/* 自定义效果：一行 = 标签 + 滑杆 + 数值 */
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
.colors { display: flex; gap: 12px; flex: 1; }
.dot {
  width: 26px; height: 26px;
  border-radius: 50%;
  border: 0;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.16);
}
.dot.on { box-shadow: 0 0 0 2px #fff; }
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

/* 我的截图 */
.empty { color: rgba(255, 255, 255, 0.4); font-size: 13px; text-align: center; padding: 28px 0; }
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

/* 轻提示 */
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

/* 过渡 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.35s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.up-enter-active, .up-leave-active { transition: transform 0.24s ease, opacity 0.24s ease; }
.up-enter-from, .up-leave-to { transform: translateY(100%); opacity: 0.6; }
</style>

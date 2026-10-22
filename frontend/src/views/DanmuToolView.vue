<template>
  <IslandInnerBase type="tool" title="手持弹幕" subtitle="全屏滚动字幕 · 演唱会 / 接机 / 应援">
    <div class="dm-tool">
      <!-- 内容 -->
      <div class="dm-field">
        <div class="dm-field-head">
          <label class="dm-label" for="dm-text">弹幕内容</label>
          <span class="dm-count" :class="{ warn: text.length > 180 }">{{ text.length }} / 200</span>
        </div>
        <div class="dm-input-wrap">
          <input
            id="dm-text"
            v-model="text"
            class="dm-input"
            type="text"
            placeholder="请输入弹幕内容…"
            maxlength="200"
            @keydown.enter="show"
          />
          <button v-if="text" class="dm-clear" aria-label="清空内容" @click="text = ''"><AppIcon icon="×" :size="14" /></button>
        </div>
      </div>

      <!-- 字体大小 -->
      <div class="dm-field">
        <label class="dm-label" for="dm-size">字体大小</label>
        <div class="dm-slider-row">
          <input id="dm-size" v-model.number="fontSize" class="dm-range" type="range" min="40" max="260" step="2" />
          <b class="dm-slider-val">{{ fontSize }}</b>
        </div>
      </div>

      <!-- 滚动速度 -->
      <div class="dm-field" :class="{ 'is-off': type === 'still' }">
        <label class="dm-label" for="dm-speed">滚动速度</label>
        <div class="dm-slider-row">
          <input id="dm-speed" v-model.number="speed" class="dm-range" type="range" min="40" max="400" step="1" :disabled="type === 'still'" />
          <b class="dm-slider-val">{{ speed }}</b>
        </div>
      </div>

      <!-- 展示方向（v2.46.78：横屏支持；APK 锁竖屏时用 rotate90 兜底，手机横持即可） -->
      <div class="dm-field">
        <span class="dm-label">展示方向</span>
        <div class="dm-dirs" role="radiogroup" aria-label="展示方向">
          <label class="dm-dir" :class="{ on: dir === 'portrait' }">
            <input v-model="dir" type="radio" value="portrait" name="dm-dir" />
            竖屏
          </label>
          <label class="dm-dir" :class="{ on: dir === 'landscape' }">
            <input v-model="dir" type="radio" value="landscape" name="dm-dir" />
            横屏
          </label>
          <label class="dm-dir" :class="{ on: dir === 'auto' }">
            <input v-model="dir" type="radio" value="auto" name="dm-dir" />
            跟随设备
          </label>
        </div>
      </div>

      <!-- 颜色（v2.46.80：预设色板 + 手动输入颜色值（hex / rgb）+ 取色器） -->
      <div class="dm-field">
        <span class="dm-label">选择颜色</span>

        <div class="dm-color-block">
          <div class="dm-color-head">
            <span class="dm-color-name">前景色</span>
            <i class="dm-color-cur" :style="{ background: fg }" aria-hidden="true"></i>
            <input
              class="dm-color-text"
              :class="{ bad: fgBad }"
              :value="fgInput"
              spellcheck="false"
              autocomplete="off"
              placeholder="#ffffff 或 rgb(255,255,255)"
              aria-label="前景色颜色值，支持 hex 或 rgb 手动输入"
              @input="onColorInput('fg', $event)"
              @blur="commitColor('fg')"
            />
          </div>
          <div class="dm-swatches">
            <button
              v-for="c in FG_PRESETS"
              :key="c"
              class="dm-swatch"
              :class="{ on: fg.toLowerCase() === c }"
              :style="{ background: c }"
              :aria-label="'前景色 ' + c"
              @click="fg = c"
            ></button>
            <label class="dm-swatch dm-swatch-custom" title="自定义颜色">
              <input v-model="fg" type="color" aria-label="前景色自定义" />
            </label>
          </div>
        </div>

        <div class="dm-color-block">
          <div class="dm-color-head">
            <span class="dm-color-name">背景色</span>
            <i class="dm-color-cur" :style="{ background: bg }" aria-hidden="true"></i>
            <input
              class="dm-color-text"
              :class="{ bad: bgBad }"
              :value="bgInput"
              spellcheck="false"
              autocomplete="off"
              placeholder="#000000 或 rgb(0,0,0)"
              aria-label="背景色颜色值，支持 hex 或 rgb 手动输入"
              @input="onColorInput('bg', $event)"
              @blur="commitColor('bg')"
            />
          </div>
          <div class="dm-swatches">
            <button
              v-for="c in BG_PRESETS"
              :key="c"
              class="dm-swatch"
              :class="{ on: bg.toLowerCase() === c }"
              :style="{ background: c }"
              :aria-label="'背景色 ' + c"
              @click="bg = c"
            ></button>
            <label class="dm-swatch dm-swatch-custom" title="自定义颜色">
              <input v-model="bg" type="color" aria-label="背景色自定义" />
            </label>
          </div>
        </div>
        <p class="dm-color-tip">手动输入支持 <code>#e9c877</code>、<code>rgb(233,200,119)</code>、<code>233,200,119</code> 三种写法</p>
      </div>

      <!-- 类型 -->
      <div class="dm-field">
        <span class="dm-label">弹幕类型</span>
        <div class="dm-types" role="radiogroup" aria-label="弹幕类型">
          <label class="dm-type" :class="{ on: type === 'still' }">
            <input v-model="type" type="radio" value="still" name="dm-type" />
            静止弹幕
          </label>
          <label class="dm-type" :class="{ on: type === 'roll' }">
            <input v-model="type" type="radio" value="roll" name="dm-type" />
            滚动弹幕
          </label>
        </div>
      </div>

      <button class="dm-show-btn" :disabled="!text.trim()" @click="show">
        <AppIcon icon="📱" :size="16" /> 显示弹幕
      </button>
      <p class="dm-hint">展示模式下：双击屏幕或点右上角 × 退出；横屏时把手机横持观看</p>
    </div>

    <!-- 全屏弹幕层：fixed 覆盖，z-index 与牌桌全屏同级（1600），双击 / × / Esc 退出；
         横屏且设备仍竖屏（APK 锁竖屏 / 浏览器不允许 lock）时整层 rotate90 兜底 -->
    <Teleport to="body">
      <div
        v-if="playing"
        class="dm-stage"
        :class="{ 'is-rot': rotated }"
        :style="stageStyle"
        role="dialog"
        aria-label="弹幕展示"
        @dblclick="stop"
        @pointerdown="onStagePointer"
      >
        <button class="dm-exit" aria-label="退出展示" @click.stop="stop"><AppIcon icon="×" :size="20" /></button>
        <!-- 静止：正中常亮；滚动：右缘进左缘出，时长 = 距离 / 速度 -->
        <div
          ref="marqueeRef"
          class="dm-text"
          :class="type === 'roll' ? 'is-roll' : 'is-still'"
          :style="textStyle"
        >{{ text }}</div>
      </div>
    </Teleport>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { enterFullscreenShell, exitFullscreenShell, pushFullscreenHistory } from '@/composables/useFullscreenPage'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { haptic } from '@/utils/haptic'
import AppIcon from '@/components/common/AppIcon.vue'

/* ---------- 配置态（本地记忆，不落库） ---------- */
const KEY = 'xuanhuang-danmu-v2'
const DEFAULTS = { text: '', fontSize: 130, speed: 177, fg: '#ffffff', bg: '#000000', type: 'roll', dir: 'auto' }
let saved = {}
try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') } catch { /* 忽略坏档 */ }
const text = ref(typeof saved.text === 'string' ? saved.text : DEFAULTS.text)
const fontSize = ref(Number(saved.fontSize) || DEFAULTS.fontSize)
const speed = ref(Number(saved.speed) || DEFAULTS.speed)
const fg = ref(saved.fg || DEFAULTS.fg)
const bg = ref(saved.bg || DEFAULTS.bg)
const type = ref(saved.type === 'still' ? 'still' : DEFAULTS.type)
const dir = ref(['portrait', 'landscape', 'auto'].includes(saved.dir) ? saved.dir : DEFAULTS.dir)

/* 前景预设：白 → 鎏金 → 常规应援色（深字给浅底场景留了黑/灰） */
const FG_PRESETS = [
  '#ffffff', '#f5e6c8', '#e9c877', '#ffd54f', '#ff8a80',
  '#ff80ab', '#b388ff', '#80d8ff', '#a5d6a7', '#f2b8a0',
  '#1a1a1a', '#9e9e9e',
]
/* 背景预设：深色为主（弹幕场景），补三张浅色给「接机牌/白底应援」 */
const BG_PRESETS = [
  '#000000', '#101820', '#1b2a4a', '#0f2e26', '#3b1f2b',
  '#2b2440', '#4a3520', '#5a1f1f', '#f7f3ea', '#ffffff',
]

/* ---------- 手动输入颜色值（v2.46.80 夜星：支持 rgb 手动输入） ----------
 * 输入框与 fg/bg 双向：输入合法值实时生效（预览同步），非法只标红不动值，
 * 失焦时归一化（合法 → 规范 hex；非法 → 回滚当前色）。点色板 / 取色器
 * 改色时 watch 反向同步输入框文本。 */
const fgInput = ref(fg.value)
const bgInput = ref(bg.value)
const fgBad = ref(false)
const bgBad = ref(false)
watch([fg, bg], ([f, b]) => { fgInput.value = f; bgInput.value = b })

/** 解析颜色值：#abc / #aabbcc / rgb(r,g,b) / r,g,b → #rrggbb；非法返回 null */
function parseColor(s) {
  const t = String(s || '').trim().toLowerCase()
  let m = t.match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/)
  if (m) {
    const h = m[1]
    return h.length === 3 ? `#${h[0]}${h[0]}${h[1]}${h[1]}${h[2]}${h[2]}` : `#${h}`
  }
  m = t.match(/^rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})/)
  if (m) return rgbToHex(m[1], m[2], m[3])
  m = t.match(/^(\d{1,3})\s*[,，]\s*(\d{1,3})\s*[,，]\s*(\d{1,3})$/)
  if (m) return rgbToHex(m[1], m[2], m[3])
  return null
}
function rgbToHex(r, g, b) {
  const c = (v) => Math.max(0, Math.min(255, parseInt(v, 10) || 0))
  return `#${[c(r), c(g), c(b)].map((v) => v.toString(16).padStart(2, '0')).join('')}`
}
function onColorInput(which, e) {
  const raw = e.target.value
  if (which === 'fg') fgInput.value = raw; else bgInput.value = raw
  const hex = parseColor(raw)
  if (hex) {
    if (which === 'fg') { fg.value = hex; fgBad.value = false } else { bg.value = hex; bgBad.value = false }
  } else if (which === 'fg') { fgBad.value = true } else { bgBad.value = true }
}
function commitColor(which) {
  const raw = which === 'fg' ? fgInput.value : bgInput.value
  const hex = parseColor(raw)
  if (hex) {
    if (which === 'fg') { fg.value = hex; fgInput.value = hex; fgBad.value = false }
    else { bg.value = hex; bgInput.value = hex; bgBad.value = false }
  } else {
    if (which === 'fg') { fgInput.value = fg.value; fgBad.value = false }
    else { bgInput.value = bg.value; bgBad.value = false }
  }
}

function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify({ text: text.value, fontSize: fontSize.value, speed: speed.value, fg: fg.value, bg: bg.value, type: type.value, dir: dir.value }))
  } catch { /* 隐私模式等场景静默 */ }
}

/* ---------- 展示态 ---------- */
const playing = ref(false)
const marqueeRef = ref(null)
let fsOpened = false
let lastTap = 0
/* rotated：设备实际仍是竖屏但用户要横屏 → 整层 rotate90（手机横持阅读）。
   只有「横屏」模式且 viewport 为竖屏时才兜底；设备真转了 / 浏览器允许 lock 时不转。 */
const rotated = ref(false)
const rollDuration = ref(12)

const stageStyle = computed(() => {
  const base = { background: bg.value }
  if (!rotated.value) return base
  // 元素宽高对调后绕中心旋转 90°：宽度取视口高、高度取视口宽，正好铺满竖屏
  return {
    ...base,
    width: window.innerHeight + 'px',
    height: window.innerWidth + 'px',
    left: '50%',
    top: '50%',
    transform: 'translate(-50%, -50%) rotate(90deg)',
  }
})

const textStyle = computed(() => {
  const s = { color: fg.value, fontSize: fontSize.value + 'px' }
  if (type.value === 'roll') s.animationDuration = rollDuration.value + 's'
  return s
})

function isPortraitViewport() {
  return window.innerHeight >= window.innerWidth
}

/** 决定是否 rotate90 兜底：横屏模式 + 设备实际竖屏 → 转 */
function syncRotation() {
  if (!playing.value) { rotated.value = false; return }
  rotated.value = dir.value === 'landscape' && isPortraitViewport()
}

/* v2.46.217 真全屏：弹幕舞台以前只是组件状态，手机系统返回键会直接退出整个工具页。
   现在进展示时压一条 history 记录 → 返回键先退出展示；同时隐藏站点外壳。 */
let disposeFsHistory = null
let fsPopping = false

function show() {
  if (!text.value.trim()) return
  haptic.light()
  persist()
  playing.value = true
  enterFullscreenShell()
  disposeFsHistory = pushFullscreenHistory()
  if (dir.value === 'landscape') {
    // 能锁就锁（真实浏览器全屏下有效）；失败静默，靠 rotate90 兜底
    try { screen.orientation?.lock?.('landscape')?.catch?.(() => {}) } catch { /* 忽略 */ }
  }
  nextTick(() => {
    syncRotation()
    startRoll()
  })
}

function stop() {
  playing.value = false
  rotated.value = false
  exitFullscreenShell()
  // popstate 已经消费掉那条记录，不能再 back（否则连退两页）
  if (fsPopping) { fsPopping = false; disposeFsHistory = null }
  else { disposeFsHistory?.(); disposeFsHistory = null }
  if (fsOpened && document.fullscreenElement) { try { document.exitFullscreen() } catch { /* 忽略 */ } }
  fsOpened = false
  try { screen.orientation?.unlock?.() } catch { /* 忽略 */ }
}

/** 移动端无 dblclick：pointerdown 300ms 内两击视为双击退出 */
function onStagePointer() {
  const now = Date.now()
  if (now - lastTap < 300) stop()
  lastTap = now
}

function onKey(e) {
  if (e.key === 'Escape' && playing.value) stop()
}
window.addEventListener('keydown', onKey)

/** 系统返回键 / 浏览器箭头：先退出弹幕展示 */
function onFsPop() {
  if (!playing.value) return
  fsPopping = true
  stop()
}
window.addEventListener('popstate', onFsPop)

/* 展示中转屏 / 改方向：重判 rotate 兜底 + 重算滚动时长 */
function onViewportChange() {
  if (!playing.value) return
  syncRotation()
  startRoll()
}
window.addEventListener('resize', onViewportChange)
window.addEventListener('orientationchange', onViewportChange)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('orientationchange', onViewportChange)
  stop()
})

/* 滚动时长：跑完「可视宽 + 文字宽」全程；文字宽度用 offsetWidth（不受旋转 transform 影响） */
function startRoll() {
  if (type.value !== 'roll') return
  nextTick(() => {
    const el = marqueeRef.value
    const tw = el ? el.offsetWidth : 300
    const vw = rotated.value ? window.innerHeight : window.innerWidth
    const dist = vw + tw
    rollDuration.value = Math.max(1.5, +(dist / Math.max(20, speed.value)).toFixed(2))
  })
}
</script>

<style scoped>
.dm-tool { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px; padding-bottom: 24px; }
.dm-field { display: flex; flex-direction: column; gap: 8px; }
.dm-field.is-off { opacity: .45; }
.dm-field-head { display: flex; align-items: baseline; justify-content: space-between; }
.dm-count { font-size: 11px; color: var(--color-ink-dim, #7a8087); font-variant-numeric: tabular-nums; }
.dm-count.warn { color: #c08a1e; }
.dm-label { font-size: 13px; font-weight: 600; color: var(--color-ink, #3a3f45); }
.dm-input-wrap { position: relative; }
.dm-input {
  width: 100%; box-sizing: border-box; padding: 12px 40px 12px 14px;
  font-size: 15px; color: var(--color-ink, #3a3f45);
  background: var(--ls-card, #fff); border: 1px solid var(--ls-line, rgba(0,0,0,.08));
  border-radius: 12px; outline: none; transition: border-color .2s;
}
.dm-input:focus { border-color: var(--color-accent); }
.dm-clear {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  width: 26px; height: 26px; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(0,0,0,.08); color: inherit; font-size: 15px; line-height: 1;
}
.dm-slider-row { display: flex; align-items: center; gap: 14px; }
.dm-range { flex: 1; accent-color: var(--color-accent); height: 4px; }
.dm-slider-val {
  min-width: 44px; text-align: center; font-size: 14px; font-variant-numeric: tabular-nums;
  color: var(--color-accent); border-bottom: 2px solid currentColor; padding-bottom: 1px;
}

/* 方向 / 类型：胶囊单选组 */
.dm-dirs, .dm-types { display: flex; gap: 10px; }
.dm-dir, .dm-type {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 7px;
  padding: 10px 0; border-radius: 999px; cursor: pointer; font-size: 14px;
  color: var(--color-ink-dim, #7a8087);
  background: var(--ls-card, #fff);
  border: 1px solid var(--ls-line, rgba(0,0,0,.1));
  transition: color .2s, border-color .2s, background .2s;
}
.dm-dir input, .dm-type input { position: absolute; opacity: 0; pointer-events: none; }
.dm-dir.on, .dm-type.on {
  color: var(--color-accent); font-weight: 700;
  border-color: color-mix(in srgb, var(--color-accent) 55%, transparent);
  background: color-mix(in srgb, var(--color-accent) 10%, var(--ls-card, #fff));
}

/* 颜色：前景/背景两块，块内 = 名称 + 当前色 + 手动输入框 + 预设色板 + 取色器 */
.dm-color-block {
  padding: 12px 14px 14px; border-radius: 14px;
  background: var(--ls-card, #fff);
  border: 1px solid var(--ls-line, rgba(0,0,0,.08));
  display: flex; flex-direction: column; gap: 10px;
}
.dm-color-head { display: flex; align-items: center; gap: 8px; }
.dm-color-name { font-size: 13px; font-weight: 600; color: var(--color-ink, #3a3f45); }
.dm-color-tip { margin: 2px 2px -4px; font-size: 11px; line-height: 1.6; color: var(--color-ink-dim, #7a8087); }
.dm-color-tip code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  padding: 1px 5px; border-radius: 5px; background: rgba(0, 0, 0, .05);
}
.dm-color-text {
  margin-left: auto; width: 150px; box-sizing: border-box;
  padding: 5px 9px; font-size: 11.5px; letter-spacing: .02em;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--color-ink, #3a3f45);
  background: var(--ls-card, #fff);
  border: 1px solid var(--ls-line, rgba(0,0,0,.12)); border-radius: 8px;
  outline: none; transition: border-color .2s, color .2s;
}
.dm-color-text:focus { border-color: var(--color-accent); }
.dm-color-text.bad { border-color: #e5484d; color: #e5484d; }
.dm-color-cur {
  width: 22px; height: 22px; border-radius: 50%;
  border: 1px solid rgba(0,0,0,.14);
  box-shadow: inset 0 0 0 2px rgba(255,255,255,.9);
}
.dm-swatches { display: flex; flex-wrap: wrap; gap: 10px; }
.dm-swatch {
  width: 28px; height: 28px; border-radius: 50%; padding: 0; cursor: pointer;
  border: 1px solid rgba(0,0,0,.12);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.35);
  transition: transform .15s ease;
}
.dm-swatch:active { transform: scale(.92); }
.dm-swatch.on {
  box-shadow: 0 0 0 2px var(--ls-card, #fff), 0 0 0 3.5px var(--color-accent);
}
.dm-swatch-custom {
  display: grid; place-items: center; overflow: hidden;
  background: conic-gradient(#f66, #fc3, #6f6, #6cf, #66f, #f66);
}
.dm-swatch-custom input {
  width: 200%; height: 200%; border: none; padding: 0; background: none; cursor: pointer;
  opacity: 0;
}
.dm-show-btn {
  margin-top: 8px; padding: 14px 0; border: none; border-radius: 14px; cursor: pointer;
  font-size: 16px; font-weight: 700; letter-spacing: .04em;
  color: var(--color-accent);
  background: color-mix(in srgb, var(--color-accent) 14%, transparent);
  transition: filter .2s, opacity .2s;
}
.dm-show-btn:not(:disabled):hover { filter: brightness(1.06); }
.dm-show-btn:disabled { opacity: .4; cursor: not-allowed; }
.dm-hint { text-align: center; font-size: 12px; color: var(--color-ink-dim, #7a8087); }

/* ===== 全屏弹幕层 ===== */
.dm-stage {
  position: fixed; inset: 0; z-index: 1600;
  overflow: hidden; user-select: none; -webkit-user-select: none;
  touch-action: manipulation;
}
/* rotate90 兜底（JS 已内联宽高/位移，这里只做旋转与层级兜底） */
.dm-stage.is-rot { inset: auto; }
.dm-exit {
  position: absolute; right: 14px; top: 10px; z-index: 2;
  width: 40px; height: 40px; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(255, 255, 255, .12); color: rgba(255, 255, 255, .8);
  font-size: 22px; line-height: 1;
}
.dm-text {
  position: absolute; top: 50%; left: 50%; white-space: nowrap;
  font-weight: 800; letter-spacing: .06em; line-height: 1.1;
}
.dm-text.is-still { transform: translate(-50%, -50%); }
.dm-text.is-roll {
  left: 100%; top: 50%; transform: translateY(-50%);
  animation: dm-roll linear both;
}
@keyframes dm-roll {
  from { left: 100%; }
  to { left: -100%; }
}
@media (prefers-reduced-motion: reduce) {
  .dm-text.is-roll { animation: none; left: 50%; transform: translate(-50%, -50%); }
}
</style>

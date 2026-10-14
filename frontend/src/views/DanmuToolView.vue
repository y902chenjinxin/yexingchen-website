<template>
  <IslandInnerBase type="tool" title="手持弹幕" subtitle="全屏滚动字幕 · 演唱会 / 接机 / 应援">
    <div class="dm-tool">
      <!-- 内容 -->
      <div class="dm-field">
        <label class="dm-label" for="dm-text">弹幕内容</label>
        <div class="dm-input-wrap">
          <input
            id="dm-text"
            v-model="text"
            class="dm-input"
            type="text"
            placeholder="请输入弹幕内容…"
            maxlength="60"
            @keydown.enter="show"
          />
          <button v-if="text" class="dm-clear" aria-label="清空内容" @click="text = ''">×</button>
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

      <!-- 颜色（v2.46.78：预设色板 + 十六进制 + 自定义，替代粗糙的系统取色弹窗） -->
      <div class="dm-field">
        <span class="dm-label">选择颜色</span>

        <div class="dm-color-block">
          <div class="dm-color-head">
            <span class="dm-color-name">前景色</span>
            <i class="dm-color-cur" :style="{ background: fg }" aria-hidden="true"></i>
            <code class="dm-color-hex">{{ fg }}</code>
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
            <code class="dm-color-hex">{{ bg }}</code>
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
        <span aria-hidden="true">📱</span> 显示弹幕
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
        <button class="dm-exit" aria-label="退出展示" @click.stop="stop">×</button>
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
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { haptic } from '@/utils/haptic'

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

function show() {
  if (!text.value.trim()) return
  haptic.light()
  persist()
  playing.value = true
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
.dm-label { font-size: 13px; font-weight: 600; color: var(--color-ink, #3a3f45); }
.dm-input-wrap { position: relative; }
.dm-input {
  width: 100%; box-sizing: border-box; padding: 12px 40px 12px 14px;
  font-size: 15px; color: var(--color-ink, #3a3f45);
  background: var(--ls-card, #fff); border: 1px solid var(--ls-line, rgba(0,0,0,.08));
  border-radius: 12px; outline: none; transition: border-color .2s;
}
.dm-input:focus { border-color: var(--color-accent, #c7a96b); }
.dm-clear {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  width: 26px; height: 26px; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(0,0,0,.08); color: inherit; font-size: 15px; line-height: 1;
}
.dm-slider-row { display: flex; align-items: center; gap: 14px; }
.dm-range { flex: 1; accent-color: var(--color-accent, #c7a96b); height: 4px; }
.dm-slider-val {
  min-width: 44px; text-align: center; font-size: 14px; font-variant-numeric: tabular-nums;
  color: var(--color-accent, #c7a96b); border-bottom: 2px solid currentColor; padding-bottom: 1px;
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
  color: var(--color-accent, #c7a96b); font-weight: 700;
  border-color: color-mix(in srgb, var(--color-accent, #c7a96b) 55%, transparent);
  background: color-mix(in srgb, var(--color-accent, #c7a96b) 10%, var(--ls-card, #fff));
}

/* 颜色：前景/背景两块，块内 = 名称 + 当前色 + 十六进制 + 预设色板 + 自定义 */
.dm-color-block {
  padding: 12px 14px 14px; border-radius: 14px;
  background: var(--ls-card, #fff);
  border: 1px solid var(--ls-line, rgba(0,0,0,.08));
  display: flex; flex-direction: column; gap: 10px;
}
.dm-color-head { display: flex; align-items: center; gap: 8px; }
.dm-color-name { font-size: 13px; font-weight: 600; color: var(--color-ink, #3a3f45); }
.dm-color-hex {
  font-size: 11px; color: var(--color-ink-dim, #7a8087);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .02em;
}
.dm-color-cur {
  margin-left: auto; width: 22px; height: 22px; border-radius: 50%;
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
  box-shadow: 0 0 0 2px var(--ls-card, #fff), 0 0 0 3.5px var(--color-accent, #c7a96b);
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
  color: var(--color-accent, #c7a96b);
  background: color-mix(in srgb, var(--color-accent, #c7a96b) 14%, transparent);
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

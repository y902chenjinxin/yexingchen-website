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

      <!-- 颜色 -->
      <div class="dm-field">
        <span class="dm-label">选择颜色</span>
        <div class="dm-colors">
          <label class="dm-color-item">
            <input v-model="fg" type="color" class="dm-color-input" aria-label="前景色" />
            <span>前景色</span>
          </label>
          <i class="dm-color-divider" aria-hidden="true"></i>
          <label class="dm-color-item">
            <input v-model="bg" type="color" class="dm-color-input" aria-label="背景色" />
            <span>背景色</span>
          </label>
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
      <p class="dm-hint">展示模式下：双击屏幕或点右上角 × 退出</p>
    </div>

    <!-- 全屏弹幕层：fixed 覆盖，z-index 与牌桌全屏同级（1600），双击 / × / Esc 退出 -->
    <Teleport to="body">
      <div
        v-if="playing"
        class="dm-stage"
        :style="{ background: bg }"
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
const KEY = 'xuanhuang-danmu-v1'
const DEFAULTS = { text: '', fontSize: 130, speed: 177, fg: '#ffffff', bg: '#000000', type: 'roll' }
let saved = {}
try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') } catch { /* 忽略坏档 */ }
const text = ref(typeof saved.text === 'string' ? saved.text : DEFAULTS.text)
const fontSize = ref(Number(saved.fontSize) || DEFAULTS.fontSize)
const speed = ref(Number(saved.speed) || DEFAULTS.speed)
const fg = ref(saved.fg || DEFAULTS.fg)
const bg = ref(saved.bg || DEFAULTS.bg)
const type = ref(saved.type === 'still' ? 'still' : DEFAULTS.type)

function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify({ text: text.value, fontSize: fontSize.value, speed: speed.value, fg: fg.value, bg: bg.value, type: type.value }))
  } catch { /* 隐私模式等场景静默 */ }
}

/* ---------- 展示态 ---------- */
const playing = ref(false)
const marqueeRef = ref(null)
let fsOpened = false
let lastTap = 0

function show() {
  if (!text.value.trim()) return
  haptic.light()
  persist()
  playing.value = true
  nextTick(startRoll)
  // 能进全屏就进（双端 WebView 支持度不一，失败静默降级为 fixed 覆盖层）
  const el = document.documentElement
  if (el.requestFullscreen) {
    el.requestFullscreen().then(() => { fsOpened = true }).catch(() => { fsOpened = false })
  }
}

function stop() {
  playing.value = false
  if (fsOpened && document.fullscreenElement) { try { document.exitFullscreen() } catch { /* 忽略 */ } }
  fsOpened = false
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
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  stop()
})

/* 滚动时长：跑完「屏宽 + 文字宽」全程；文字宽度在入屏后实测 */
const rollDuration = ref(12)
const textStyle = computed(() => {
  if (type.value === 'still') {
    return { color: fg.value, fontSize: fontSize.value + 'px' }
  }
  return { color: fg.value, fontSize: fontSize.value + 'px', animationDuration: rollDuration.value + 's' }
})

function startRoll() {
  if (type.value !== 'roll') return
  nextTick(() => {
    const el = marqueeRef.value
    const w = el ? el.getBoundingClientRect().width : 300
    const dist = window.innerWidth + w
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
.dm-colors { display: flex; align-items: center; gap: 22px; }
.dm-color-item { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--color-ink, #3a3f45); cursor: pointer; }
.dm-color-input {
  width: 34px; height: 34px; padding: 0; border: none; border-radius: 50%;
  background: none; cursor: pointer;
}
.dm-color-input::-webkit-color-swatch-wrapper { padding: 0; }
.dm-color-input::-webkit-color-swatch { border: 1px solid var(--ls-line, rgba(0,0,0,.12)); border-radius: 50%; }
.dm-color-divider { width: 1px; height: 26px; background: var(--ls-line, rgba(0,0,0,.12)); }
.dm-types { display: flex; gap: 20px; }
.dm-type {
  display: flex; align-items: center; gap: 7px; font-size: 14px; cursor: pointer;
  color: var(--color-ink-dim, #7a8087);
}
.dm-type input { accent-color: var(--color-accent, #c7a96b); width: 16px; height: 16px; }
.dm-type.on { color: var(--color-ink, #3a3f45); font-weight: 600; }
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

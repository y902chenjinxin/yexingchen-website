<!--
  NoteEditorToolbar.vue
  玄黄 · 笔记富文本工具栏
  - 鎏金主色 + hover 动效 + v-mouse-light
  - 颜色面板支持 preset / 取色 / HEX / RGB
-->
<template>
  <div class="ne-toolbar" @mousedown="onToolbarMousedown">
    <button v-mouse-light="{ tilt: 0 }" type="button" title="标题" @click="$emit('exec', 'formatBlock', 'H2')"><b>H</b></button>
    <button v-mouse-light="{ tilt: 0 }" type="button" title="加粗" @click="$emit('exec', 'bold')"><b>B</b></button>
    <button v-mouse-light="{ tilt: 0 }" type="button" title="斜体" @click="$emit('exec', 'italic')"><i>I</i></button>
    <button v-mouse-light="{ tilt: 0 }" type="button" title="下划线" @click="$emit('exec', 'underline')"><u>U</u></button>

    <div class="ne-color-wrap">
      <button
        v-mouse-light="{ tilt: 0 }"
        type="button"
        class="ne-color-btn"
        :class="{ active: colorPanelOpen }"
        title="文字颜色"
        @mousedown.stop.prevent="toggleColorPanel"
      >A</button>
      <div
        v-if="colorPanelOpen"
        class="ne-color-panel"
        @mousedown.stop
        @click.prevent
      >
        <div class="ne-color-presets">
          <span
            v-for="c in paletteColors"
            :key="c"
            class="ne-color-swatch"
            :style="{ background: c }"
            :title="c"
            @click="applyColor(c)"
          />
        </div>
        <div class="ne-color-actions">
          <input
            type="color"
            title="自由取色"
            @input="$emit('exec', 'foreColor', $event.target.value)"
          />
          <button v-mouse-light="{ tilt: 0 }" type="button" title="吸色（针管光标，在页面内点击取色）" @click="$emit('pick-color')">
            吸色
          </button>
          <input
            v-model="hexColor"
            class="ne-hex-input"
            placeholder="#RRGGBB"
            maxlength="7"
            @keydown.enter.prevent="applyHex"
          />
          <button v-mouse-light="{ tilt: 0 }" type="button" title="应用HEX颜色" @click="applyHex">应用</button>
          <span class="ne-color-rgb">
            <input v-model.number="rgb.r" type="number" min="0" max="255" placeholder="R" />
            <input v-model.number="rgb.g" type="number" min="0" max="255" placeholder="G" />
            <input v-model.number="rgb.b" type="number" min="0" max="255" placeholder="B" />
          </span>
          <button v-mouse-light="{ tilt: 0 }" type="button" title="应用RGB颜色" @click="applyRgb">RGB</button>
        </div>
      </div>
    </div>

    <button v-mouse-light="{ tilt: 0 }" type="button" @click="$emit('exec', 'insertUnorderedList')">• 列表</button>
    <button v-mouse-light="{ tilt: 0 }" type="button" @click="$emit('exec', 'insertOrderedList')">1. 列表</button>
    <button v-mouse-light="{ tilt: 0 }" type="button" @click="$emit('exec', 'formatBlock', 'BLOCKQUOTE')">引用</button>
    <button v-mouse-light="{ tilt: 0 }" type="button" @click="$emit('exec', 'formatBlock', 'PRE')">代码块</button>
    <button v-mouse-light="{ tilt: 0 }" type="button" @click="$emit('insert-link')">链接</button>
    <label v-mouse-light="{ tilt: 0 }" class="ne-upload-btn">
      图片
      <input type="file" accept="image/*" hidden @change="$emit('pick-image', $event)" />
    </label>
    <label v-mouse-light="{ tilt: 0 }" class="ne-upload-btn">
      PDF
      <input type="file" accept="application/pdf" hidden @change="$emit('pick-pdf', $event)" />
    </label>
    <button v-mouse-light="{ tilt: 0 }" type="button" title="撤销" @click="$emit('exec', 'undo')">↶</button>
    <button v-mouse-light="{ tilt: 0 }" type="button" title="重做" @click="$emit('exec', 'redo')">↷</button>
  </div>
</template>

<script setup>
/**
 * 富文本工具栏：粗体/列表/链接/上传/撤销重做 + 文字颜色面板（palette / 取色 / HEX / RGB）。
 *
 * 大部分事件通过 emit 上抛到容器 NoteEditorView，由容器调用 exec() 触发浏览器命令；
 * 颜色面板自身管理 HEX / RGB / panel 状态，避免污染容器。
 */
import { inject, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'

defineProps({
  paletteColors: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'exec',          // (command, value)
  'insert-link',
  'pick-image',    // (event)
  'pick-pdf',      // (event)
  'pick-color',
])

const ctx = inject('editorContext')

// 颜色面板本地状态
const colorPanelOpen = ref(false)
const hexColor = ref('')
const rgb = ref({ r: 120, g: 120, b: 120 })

function toggleColorPanel() {
  colorPanelOpen.value = !colorPanelOpen.value
  if (colorPanelOpen.value && ctx?.editorEl) {
    ctx.saveSelection(ctx.editorEl)
  }
}

function applyColor(color) {
  emit('exec', 'foreColor', color)
}

function applyHex() {
  const v = (hexColor.value || '').trim().replace(/^#/, '')
  let hex = v
  if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('')
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
    ElMessage.warning('请输入有效的HEX颜色，如 #5ce0d8')
    return
  }
  emit('exec', 'foreColor', '#' + hex.toLowerCase())
}

function clamp255(n) {
  const v = Number(n)
  return Number.isFinite(v) ? Math.max(0, Math.min(255, Math.round(v))) : 0
}

function applyRgb() {
  const r = clamp255(rgb.value.r)
  const g = clamp255(rgb.value.g)
  const b = clamp255(rgb.value.b)
  emit('exec', 'foreColor', `rgb(${r}, ${g}, ${b})`)
}

function onToolbarMousedown(e) {
  ctx?.onToolbarMousedown?.(e)
}

// 点面板外关闭
function onDocPointer(e) {
  const panel = document.querySelector('.ne-color-panel')
  const btn = document.querySelector('.ne-color-btn')
  if (panel && panel.contains(e.target)) return
  if (btn && btn.contains(e.target)) return
  colorPanelOpen.value = false
}

document.addEventListener('pointerdown', onDocPointer)
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocPointer))
</script>

<style scoped>
.ne-toolbar {
  display: flex; flex-wrap: wrap; gap: 4px; padding: 8px;
  margin-top: 8px;
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.04));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  border-radius: 10px;
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

/* 按钮：玄黄主题 + hover 微动效 */
.ne-toolbar button, .ne-toolbar .ne-upload-btn {
  position: relative;
  padding: 5px 10px;
  background: transparent;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.22));
  color: var(--lj-text-2);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: all .15s ease;
  overflow: hidden;
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
}
.ne-toolbar button:hover, .ne-toolbar .ne-upload-btn:hover {
  color: var(--yq-gold, #c7a96b);
  border-color: var(--yq-gold-glow, rgba(199, 169, 107, 0.5));
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.08));
  transform: translateY(-1px);
  box-shadow: 0 4px 10px var(--yq-gold-glow, rgba(199, 169, 107, 0.15));
}
.ne-toolbar button:active, .ne-toolbar .ne-upload-btn:active {
  transform: translateY(0);
}
.ne-toolbar b, .ne-toolbar i, .ne-toolbar u {
  font-style: normal;
  text-decoration: none;
  font-weight: 700;
}
.ne-toolbar i { font-style: italic; }
.ne-toolbar u { text-decoration: underline; }

/* 颜色按钮 active */
.ne-color-wrap { position: relative; display: inline-block; }
.ne-color-btn.active {
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.18));
  color: var(--yq-gold, #c7a96b);
  border-color: var(--yq-gold, #c7a96b);
  box-shadow: 0 0 0 2px var(--yq-gold-glow, rgba(199, 169, 107, 0.18));
}

/* 颜色面板：主题感知玻璃 */
.ne-color-panel {
  position: absolute; top: 36px; left: 0; z-index: 50;
  min-width: 320px; padding: 12px;
  background: var(--color-bg-glass, rgba(10, 16, 26, 0.92));
  border: 1px solid var(--dp-line-strong, rgba(199, 169, 107, 0.3));
  border-radius: 12px;
  box-shadow: 0 12px 36px rgba(0, 0, 0, .4), 0 0 0 1px var(--yq-gold-glow, rgba(199, 169, 107, 0.12));
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  /* 入场动效 */
  animation: ne-color-pop .18s cubic-bezier(.2,.8,.2,1);
}
@keyframes ne-color-pop {
  from { opacity: 0; transform: translateY(-4px) scale(.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.ne-color-presets { display: grid; grid-template-columns: repeat(8, 22px); gap: 6px; }
.ne-color-swatch {
  width: 22px; height: 22px; border-radius: 5px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, .12);
  transition: transform .15s, border-color .15s;
}
.ne-color-swatch:hover {
  transform: scale(1.18) rotate(-4deg);
  border-color: var(--yq-gold, #c7a96b);
  box-shadow: 0 4px 10px rgba(0, 0, 0, .35);
}

.ne-color-actions { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.ne-color-actions input[type="color"] {
  width: 32px; height: 26px; padding: 0;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.22));
  background: transparent; border-radius: 6px; cursor: pointer;
}
.ne-hex-input {
  width: 90px; padding: 3px 6px;
  background: var(--dp-glass, rgba(0, 0, 0, .25));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.22));
  border-radius: 6px; color: var(--lj-text); font-size: 12px;
  transition: border-color .15s;
}
.ne-hex-input:focus { outline: none; border-color: var(--yq-gold, #c7a96b); }

.ne-color-rgb { display: inline-flex; gap: 3px; }
.ne-color-rgb input {
  width: 40px; padding: 3px 4px;
  background: var(--dp-glass, rgba(0, 0, 0, .25));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.22));
  border-radius: 6px; color: var(--lj-text); font-size: 12px;
}

.ne-upload-btn {
  position: relative;
  display: inline-flex; align-items: center;
}
.ne-upload-btn input { cursor: pointer; }

@media (max-width: 600px) {
  .ne-toolbar { gap: 2px; }
  .ne-toolbar button, .ne-toolbar input { font-size: 12px; padding: 3px 6px; }
}
</style>
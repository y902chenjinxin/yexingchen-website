<template>
  <div class="ne-toolbar" @mousedown="onToolbarMousedown">
    <button type="button" title="标题" @click="$emit('exec', 'formatBlock', 'H2')">H</button>
    <button type="button" title="加粗" @click="$emit('exec', 'bold')"><b>B</b></button>
    <button type="button" title="斜体" @click="$emit('exec', 'italic')"><i>I</i></button>
    <button type="button" title="下划线" @click="$emit('exec', 'underline')"><u>U</u></button>

    <div class="ne-color-wrap">
      <button
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
          <button type="button" title="吸色（针管光标，在页面内点击取色）" @click="$emit('pick-color')">
            吸色
          </button>
          <input
            v-model="hexColor"
            class="ne-hex-input"
            placeholder="#RRGGBB"
            maxlength="7"
            @keydown.enter.prevent="applyHex"
          />
          <button type="button" title="应用HEX颜色" @click="applyHex">应用</button>
          <span class="ne-color-rgb">
            <input v-model.number="rgb.r" type="number" min="0" max="255" placeholder="R" />
            <input v-model.number="rgb.g" type="number" min="0" max="255" placeholder="G" />
            <input v-model.number="rgb.b" type="number" min="0" max="255" placeholder="B" />
          </span>
          <button type="button" title="应用RGB颜色" @click="applyRgb">RGB</button>
        </div>
      </div>
    </div>

    <button type="button" @click="$emit('exec', 'insertUnorderedList')">• 列表</button>
    <button type="button" @click="$emit('exec', 'insertOrderedList')">1. 列表</button>
    <button type="button" @click="$emit('exec', 'formatBlock', 'BLOCKQUOTE')">引用</button>
    <button type="button" @click="$emit('exec', 'formatBlock', 'PRE')">代码块</button>
    <button type="button" @click="$emit('insert-link')">链接</button>
    <label class="ne-upload-btn">
      图片
      <input type="file" accept="image/*" hidden @change="$emit('pick-image', $event)" />
    </label>
    <label class="ne-upload-btn">
      PDF
      <input type="file" accept="application/pdf" hidden @change="$emit('pick-pdf', $event)" />
    </label>
    <button type="button" title="撤销" @click="$emit('exec', 'undo')">↶</button>
    <button type="button" title="重做" @click="$emit('exec', 'redo')">↷</button>
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

const props = defineProps({
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
    // 记录当前选区（供 applyColor 选区已丢失时回退）
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
  // 委托给容器统一处理：仅阻止默认以保留选区
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
.ne-toolbar { display: flex; flex-wrap: wrap; gap: 4px; padding: 8px; margin-top: 8px; background: var(--xiu-card); border: 1px solid var(--xiu-line); border-radius: 10px; backdrop-filter: blur(10px); }
.ne-toolbar button { padding: 4px 8px; background: rgba(255,255,255,.04); border: 1px solid var(--xiu-line); color: var(--xiu-text); border-radius: 6px; cursor: pointer; font-size: 13px; transition: var(--transition); }
.ne-toolbar button:hover { color: var(--xiu-gold-bright); border-color: rgba(201, 169, 110, .4); background: rgba(201, 169, 110, .1); }
.ne-color-wrap { position: relative; display: inline-block; }
.ne-color-btn.active { background: rgba(201, 169, 110, .18); color: var(--xiu-gold-bright); border-color: rgba(201, 169, 110, .55); }
.ne-color-panel { position: absolute; top: 36px; left: 0; z-index: 50; min-width: 320px; padding: 10px; background: rgba(10, 16, 26, .92); border: 1px solid var(--xiu-line); border-radius: 10px; box-shadow: 0 8px 32px rgba(0, 0, 0, .35); backdrop-filter: blur(14px); }
.ne-color-presets { display: grid; grid-template-columns: repeat(8, 22px); gap: 6px; }
.ne-color-swatch { width: 22px; height: 22px; border-radius: 5px; cursor: pointer; border: 1px solid rgba(255, 255, 255, .12); transition: transform .12s; }
.ne-color-swatch:hover { transform: scale(1.12); border-color: rgba(255, 255, 255, .5); }
.ne-color-actions { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.ne-color-actions input[type="color"] { width: 32px; height: 26px; padding: 0; border: 1px solid var(--xiu-line); background: transparent; border-radius: 6px; cursor: pointer; }
.ne-hex-input { width: 90px; padding: 3px 6px; background: rgba(0,0,0,.25); border: 1px solid var(--xiu-line); border-radius: 6px; color: var(--xiu-text); font-size: 12px; }
.ne-color-rgb { display: inline-flex; gap: 3px; }
.ne-color-rgb input { width: 40px; padding: 3px 4px; background: rgba(0,0,0,.25); border: 1px solid var(--xiu-line); border-radius: 6px; color: var(--xiu-text); font-size: 12px; }
.ne-upload-btn { padding: 4px 8px; background: rgba(255,255,255,.04); border: 1px solid var(--xiu-line); border-radius: 6px; cursor: pointer; font-size: 13px; color: var(--xiu-text-2); transition: var(--transition); }
.ne-upload-btn:hover { color: var(--xiu-gold-bright); border-color: rgba(201, 169, 110, .4); background: rgba(201, 169, 110, .1); }
@media (max-width: 600px) { .ne-toolbar { gap: 2px; } .ne-toolbar button, .ne-toolbar input { font-size: 12px; padding: 3px 6px; } }
</style>

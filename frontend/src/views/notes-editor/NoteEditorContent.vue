<template>
  <div
    ref="editorElRef"
    class="ne-content"
    contenteditable="true"
    spellcheck="false"
    @input="$emit('update', $event)"
    @paste="$emit('paste', $event)"
    @mousedown="$emit('content-click', $event)"
  ></div>
</template>

<script setup>
/**
 * 编辑器主体（contenteditable）。
 *
 * 仅负责挂载 DOM 节点与转发浏览器事件；
 * HTML 注入、保存、selection 恢复等均由 NoteEditorView 容器负责。
 */
import { onMounted, ref } from 'vue'

const editorElRef = ref(null)
const emit = defineEmits(['editor-ready', 'update', 'paste', 'content-click'])

onMounted(() => {
  emit('editor-ready', editorElRef.value)
})
</script>

<style scoped>
.ne-content { min-height: 320px; padding: 14px; border: 1px solid var(--xiu-line); border-radius: 10px; outline: none; line-height: 1.7; background: var(--xiu-card); color: var(--xiu-text); word-break: break-word; backdrop-filter: blur(10px); }
.ne-content :deep(a) { color: var(--xiu-primary-bright); }
.ne-content :deep(img) { max-width: 100%; height: auto; }
.ne-content :deep(h1) { font-size: 1.8em; font-weight: 700; color: var(--xiu-gold-bright); margin: .6em 0 .4em; line-height: 1.35; }
.ne-content :deep(h2) { font-size: 1.5em; font-weight: 700; color: var(--xiu-gold-bright); margin: .6em 0 .4em; line-height: 1.35; }
.ne-content :deep(h3) { font-size: 1.25em; font-weight: 600; color: var(--xiu-gold); margin: .5em 0 .35em; line-height: 1.4; }
.ne-content :deep(h4), .ne-content :deep(h5), .ne-content :deep(h6) { font-size: 1.08em; font-weight: 600; color: var(--xiu-gold); margin: .5em 0 .35em; }
.ne-content :deep(blockquote) { margin: .6em 0; padding: 8px 14px; border-left: 3px solid var(--xiu-primary-bright); background: rgba(61, 184, 176, .1); border-radius: 0 8px 8px 0; color: var(--xiu-text-2); }
.ne-content :deep(blockquote p) { margin: 0; }
.ne-content :deep(pre) { margin: .6em 0; padding: 12px 14px; background: rgba(10, 16, 26, .6); border: 1px solid var(--xiu-line); border-radius: 8px; font-family: Consolas, 'Source Code Pro', 'Courier New', monospace; font-size: 13px; line-height: 1.6; color: var(--xiu-primary-bright); overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
.ne-content :deep(code) { font-family: Consolas, 'Source Code Pro', 'Courier New', monospace; background: rgba(61, 184, 176, .12); padding: 1px 5px; border-radius: 4px; color: var(--xiu-primary-bright); }
.ne-content :deep(pre code) { background: none; padding: 0; }
</style>

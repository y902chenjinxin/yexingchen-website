<template>
  <div v-if="assets.length" class="ne-assets">
    <h4>已附加（{{ assets.length }} / 共 {{ totalSizeText }}）</h4>
    <ul>
      <li v-for="a in assets" :key="a.id">
        <span class="asset-thumb">
          <img
            v-if="a.type === 'image'"
            :src="a.previewUrl"
            :alt="a.title"
            @load="a.objectUrl && URL.revokeObjectURL(a.objectUrl)"
          />
          <span v-else-if="a.type === 'pdf'" class="pdf-chip">
            <el-icon class="inline-icon"><Document /></el-icon>
            {{ a.title }}
          </span>
          <span v-else>
            <el-icon class="inline-icon"><Link /></el-icon>
            {{ a.title }}
          </span>
        </span>
        <span class="asset-title">{{ a.title }}</span>
        <span class="asset-size">{{ humanSize(a.file_size) }}</span>
        <button class="detach-btn" @click="$emit('detach', a.id)">解除</button>
      </li>
    </ul>
  </div>
</template>

<script setup>
/**
 * 附件面板：列出当前笔记的所有附件（image/pdf/link），允许解除。
 *
 * 数据由 NoteEditorView 提供；humanSize 也只在面板用到，独立实现避免污染容器。
 */
import { Document, Link } from '@element-plus/icons-vue'

const props = defineProps({
  assets: { type: Array, required: true },
  totalSizeText: { type: String, required: true },
})

defineEmits(['detach'])

function humanSize(n) {
  if (!n || n < 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`
}
</script>

<style scoped>
.ne-assets { margin-top: 16px; padding: 12px; background: var(--xiu-card); border: 1px solid var(--xiu-line); border-radius: 10px; backdrop-filter: blur(10px); }
.ne-assets h4 { margin: 0 0 8px; font-size: 14px; color: var(--xiu-gold); letter-spacing: .08em; }
.ne-assets ul { list-style: none; margin: 0; padding: 0; }
.ne-assets li { display: flex; gap: 8px; align-items: center; padding: 6px 0; border-top: 1px dashed rgba(201, 169, 110, .15); }
.ne-assets li:first-child { border-top: 0; }
.asset-thumb img { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; border: 1px solid var(--xiu-line); }
.pdf-chip { display: inline-block; padding: 4px 8px; background: rgba(61, 184, 176, .12); border: 1px solid rgba(61, 184, 176, .2); border-radius: 6px; font-size: 12px; color: var(--xiu-text-2); }
.asset-title { flex: 1; font-size: 13px; word-break: break-word; color: var(--xiu-text); }
.asset-size { font-size: 11px; color: var(--xiu-text-3); }
.detach-btn { padding: 2px 8px; background: transparent; border: 1px solid var(--xiu-line); color: var(--xiu-text-2); cursor: pointer; border-radius: 6px; font-size: 12px; transition: var(--transition); }
.detach-btn:hover { color: var(--xiu-danger); border-color: rgba(224, 138, 122, .4); }
</style>

<script setup>
/**
 * PDF 工具通用文件列表：拖拽序号 + 删除 + 条件性重排序。
 * props.files 形如 [{ name, size, file, error }]
 * emit: remove(index), move(index, delta)
 */
defineProps({
  files: { type: Array, required: true },
  processing: { type: Boolean, default: false },
  showReorder: { type: Boolean, default: true },
})

defineEmits(['remove', 'move'])

function sizeStr(n) {
  if (n == null) return '-'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(2) + ' MB'
}
</script>

<template>
  <div v-if="files.length" class="file-list">
    <div v-for="(f, i) in files" :key="i" class="file-row">
      <span class="fr-idx">{{ i + 1 }}</span>
      <span class="fr-name" :title="f.name">{{ f.name }}</span>
      <span class="fr-size">{{ sizeStr(f.size) }}</span>
      <span class="fr-status" :class="f.error ? 'err' : ''">{{ f.error || '待处理' }}</span>
      <span class="fr-ops">
        <template v-if="showReorder">
          <button class="op" :disabled="i === 0 || processing" @click="$emit('move', i, -1)">上移</button>
          <button class="op" :disabled="i === files.length - 1 || processing" @click="$emit('move', i, 1)">下移</button>
        </template>
        <button class="op danger" @click="$emit('remove', i)">删除</button>
      </span>
    </div>
  </div>
</template>

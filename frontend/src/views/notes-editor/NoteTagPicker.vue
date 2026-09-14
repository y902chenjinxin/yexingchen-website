<template>
  <div class="ne-tags">
    <h4>标签</h4>
    <div class="ne-tags-list">
      <el-tag
        v-for="t in tags"
        :key="t"
        closable
        @close="$emit('remove', t)"
      >#{{ t }}</el-tag>
      <el-input
        :model-value="draft"
        size="small"
        style="width: 140px"
        @update:model-value="(v) => $emit('update:draft', v)"
        @keyup.enter="$emit('add')"
      />
      <el-button size="small" @click="$emit('add')">添加</el-button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tags: { type: Array, required: true },
  draft: { type: String, required: true },
})

defineEmits(['add', 'remove', 'update:draft'])
</script>

<style scoped>
.ne-tags { margin-top: 16px; padding: 12px; background: var(--xiu-card); border: 1px solid var(--xiu-line); border-radius: 10px; backdrop-filter: blur(10px); }
.ne-tags h4 { margin: 0 0 8px; font-size: 14px; color: var(--xiu-gold); letter-spacing: .08em; }
.ne-tags-list { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
</style>

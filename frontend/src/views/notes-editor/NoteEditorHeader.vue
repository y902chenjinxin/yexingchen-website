<template>
  <header class="ne-header">
    <BackButton fallback="/notes" style="margin-right: 8px;" />
    <input
      :value="title"
      class="ne-title-input"
      placeholder="标题"
      @input="onTitleInput"
    />
    <VoiceInputButton class="ne-voice" @result="(t) => $emit('voice', t)" />
    <div class="ne-status">
      <span v-if="saveState === 'saving'" class="state saving">保存中…</span>
      <span v-else-if="saveState === 'saved'" class="state saved">已保存</span>
      <span v-else-if="saveState === 'error'" class="state error">保存失败：{{ saveError }}</span>
      <el-button
        v-if="hasNote && status === 'draft'"
        type="primary"
        size="small"
        @click="$emit('complete')"
      >完成</el-button>
      <el-button
        v-if="hasNote && status === 'completed'"
        size="small"
        @click="$emit('revert')"
      >恢复为草稿</el-button>
      <el-button size="small" type="danger" plain @click="$emit('delete')">删除</el-button>
    </div>
  </header>
</template>

<script setup>
import BackButton from '@/components/BackButton.vue'
import VoiceInputButton from '@/components/VoiceInputButton.vue'

const props = defineProps({
  title: { type: String, required: true },
  status: { type: String, required: true },
  saveState: { type: String, required: true }, // idle | saving | saved | error
  saveError: { type: String, required: true },
  hasNote: { type: Boolean, required: true },
})

const emit = defineEmits([
  'update:title',
  'voice',
  'save',
  'complete',
  'revert',
  'delete',
])

function onTitleInput(e) {
  emit('update:title', e.target.value)
  emit('save')
}
</script>

<style scoped>
.ne-header { display: flex; gap: 8px; align-items: center; padding: 10px 12px; background: var(--xiu-card); border: 1px solid var(--xiu-line); border-radius: 10px; backdrop-filter: blur(10px); }
.ne-title-input { flex: 1; background: transparent; border: 0; outline: none; color: var(--xiu-text); font-size: 18px; font-weight: 600; padding: 6px 8px; border-radius: 6px; transition: var(--transition); }
.ne-title-input:focus { background: rgba(255, 255, 255, .04); box-shadow: inset 0 0 0 1px rgba(201, 169, 110, .35); }
.ne-voice { margin-right: 4px; }
.ne-status { display: flex; gap: 6px; align-items: center; }
.state { font-size: 12px; color: var(--xiu-text-3); padding: 2px 8px; border-radius: 4px; }
.state.saving { color: var(--xiu-primary-bright); }
.state.saved { color: var(--xiu-gold-bright); }
.state.error { color: var(--xiu-danger); }
@media (max-width: 600px) { .ne-header { flex-wrap: wrap; } }
</style>

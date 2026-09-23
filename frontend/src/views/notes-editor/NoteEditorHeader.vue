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
      <transition name="ne-state" mode="out-in">
        <span v-if="saveState === 'saving'" key="saving" class="state saving">
          <span class="state-dot" aria-hidden="true"></span>保存中…
        </span>
        <span v-else-if="saveState === 'saved'" key="saved" class="state saved">
          <span class="state-check" aria-hidden="true">✓</span>已保存
        </span>
        <span v-else-if="saveState === 'error'" key="error" class="state error">
          <span aria-hidden="true">⚠</span>保存失败：{{ saveError }}
        </span>
      </transition>
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
.ne-header {
  display: flex; gap: 8px; align-items: center; padding: 10px 12px;
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.04));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  border-radius: 12px;
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}
.ne-title-input {
  flex: 1; background: transparent; border: 0; outline: none;
  color: var(--lj-text); font-size: 18px; font-weight: 600;
  padding: 6px 10px; border-radius: 6px;
  transition: all .15s ease;
}
.ne-title-input:focus {
  background: var(--dp-glass, rgba(255, 255, 255, 0.04));
  box-shadow: inset 0 0 0 1px var(--yq-gold-glow, rgba(199, 169, 107, 0.4));
}
.ne-voice { margin-right: 4px; }
.ne-status { display: flex; gap: 6px; align-items: center; }

/* 状态：鎏金过渡 + 状态色 + 微动效 */
.state {
  font-size: 12px; padding: 4px 10px; border-radius: 999px;
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--dp-glass, rgba(127, 127, 127, 0.06));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.2));
  letter-spacing: .04em;
}
.state.saving {
  color: var(--yq-rain, #7fa8a3);
  border-color: var(--yq-rain-glow, rgba(127, 168, 163, 0.4));
}
.state.saved {
  color: var(--yq-gold, #c7a96b);
  border-color: var(--yq-gold-glow, rgba(199, 169, 107, 0.4));
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.1));
}
.state.error {
  color: var(--dp-danger, #fb7185);
  border-color: var(--dp-danger, #fb7185);
  background: var(--dp-danger-faint, rgba(251, 113, 133, 0.1));
}

/* 保存中：鎏金小点跳动 */
.state-dot {
  display: inline-block;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--yq-rain, #7fa8a3);
  box-shadow: 0 0 8px var(--yq-rain-glow, rgba(127, 168, 163, 0.6));
  animation: ne-state-pulse 1.2s ease-in-out infinite;
}
@keyframes ne-state-pulse {
  0%, 100% { transform: scale(1); opacity: .85; }
  50%      { transform: scale(1.35); opacity: 1; }
}

/* 已保存：✓ 鎏金勾动画 */
.state-check {
  display: inline-flex; align-items: center; justify-content: center;
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--yq-gold, #c7a96b);
  color: var(--yq-gold-fg, #0b0f14);
  font-size: 9px; font-weight: 700;
  animation: ne-state-check .35s cubic-bezier(.2,.8,.2,1.4);
}
@keyframes ne-state-check {
  0% { transform: scale(0); opacity: 0; }
  60% { transform: scale(1.25); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

/* 状态切换动效 */
.ne-state-enter-active, .ne-state-leave-active {
  transition: all .25s cubic-bezier(.2,.8,.2,1);
}
.ne-state-enter-from { opacity: 0; transform: translateY(-4px) scale(.95); }
.ne-state-leave-to   { opacity: 0; transform: translateY(4px) scale(.95); }

@media (max-width: 600px) { .ne-header { flex-wrap: wrap; } }
</style>

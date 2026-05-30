<template>
  <Teleport to="body">
    <Transition name="help-fade">
      <div v-if="isHelpVisible" class="keyboard-help-overlay" @click.self="close">
        <div class="keyboard-help-panel">
          <div class="help-header">
            <h3>⌨️ 键盘快捷键</h3>
            <button class="help-close" @click="close">✕</button>
          </div>
          <div class="help-content">
            <div class="help-item">
              <kbd>Tab</kbd>
              <span>遍历岛屿</span>
            </div>
            <div class="help-item">
              <kbd>Shift</kbd>+<kbd>Tab</kbd>
              <span>反向遍历</span>
            </div>
            <div class="help-item">
              <kbd>1</kbd>-<kbd>5</kbd>
              <span>数字快捷跳转</span>
            </div>
            <div class="help-item">
              <kbd>Enter</kbd>
              <span>进入选中岛屿</span>
            </div>
            <div class="help-item">
              <kbd>Esc</kbd>
              <span>取消聚焦 / 返回</span>
            </div>
            <div class="help-item">
              <kbd>?</kbd>
              <span>显示/隐藏帮助</span>
            </div>
          </div>
          <div class="help-footer">
            <span>按 <kbd>?</kbd> 关闭</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch } from 'vue'

const props = defineProps({
  isHelpVisible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

function close() {
  emit('close')
}

watch(() => props.isHelpVisible, (val) => {
  if (val) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.keyboard-help-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.keyboard-help-panel {
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 24px;
  min-width: 360px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.help-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--color-text-primary);
}

.help-close {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.help-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.help-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.help-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.help-item kbd {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 4px 10px;
  font-family: inherit;
  font-size: 13px;
  color: var(--color-accent);
  min-width: 32px;
  text-align: center;
}

.help-item span {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.help-footer {
  margin-top: 20px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.help-footer kbd {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: inherit;
}

/* 过渡动画 */
.help-fade-enter-active,
.help-fade-leave-active {
  transition: opacity 0.3s ease;
}

.help-fade-enter-from,
.help-fade-leave-to {
  opacity: 0;
}

.help-fade-enter-active .keyboard-help-panel,
.help-fade-leave-active .keyboard-help-panel {
  transition: transform 0.3s ease;
}

.help-fade-enter-from .keyboard-help-panel,
.help-fade-leave-to .keyboard-help-panel {
  transform: scale(0.95);
}
</style>
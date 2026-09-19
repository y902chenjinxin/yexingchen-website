<template>
  <button
    class="fab-ai"
    :class="{ active: isActive }"
    title="AI 对话"
    aria-label="AI 对话"
    @click="go"
  >
    <el-icon class="fab-ai-ic"><MagicStick /></el-icon>
    <span class="fab-ai-text">AI</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MagicStick } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const isActive = computed(() => route.path === '/assistant')
function go() { router.push('/assistant') }
</script>

<style scoped>
/* 悬浮 AI 入口：每个页面右下角常驻（在播放条之上） */
.fab-ai {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1500;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 46px;
  padding: 0 16px 0 14px;
  border-radius: 999px;
  cursor: pointer;
  border: 1px solid var(--dp-line-strong);
  background: var(--dp-surface);
  color: var(--dp-text);
  box-shadow: var(--dp-raised, var(--dp-shadow));
  transition: transform .16s, box-shadow .16s, border-color .16s, background .16s;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: .02em;
}
.fab-ai:hover {
  transform: translateY(-2px);
  border-color: var(--dp-accent);
  color: var(--dp-accent);
  box-shadow: 0 6px 22px var(--dp-accent-faint), var(--dp-shadow);
}
.fab-ai.active {
  background: var(--dp-accent-strong);
  border-color: var(--dp-accent-strong);
  color: #fff;
}
.fab-ai-ic { font-size: 17px; }
.fab-ai-text { line-height: 1; }

:root[data-theme="night"] .fab-ai {
  background: rgba(28, 24, 46, .9);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
}
:root[data-theme="night"] .fab-ai.active { background: var(--dp-accent-strong); }
</style>

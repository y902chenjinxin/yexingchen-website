<!--
  AiBriefCard.vue
  玄黄·工作台 AI 简报卡片
  - 拉取用户的当日 KPI 数据 → 调用 workbenchApi.ai.preview 生成 1 段 ≤120 字的简报
  - 缓存到 localStorage（4 小时），避免每次进工作台都打 AI
  - "重新生成" 按钮触发 fetch
-->
<template>
  <div class="ai-brief" :class="{ loading, hasText: !!brief }">
    <div class="ai-brief-head">
      <span class="ai-brief-mark" aria-hidden="true">✺</span>
      <span class="ai-brief-title">今日简报</span>
      <span v-if="updatedAt" class="ai-brief-time">{{ updatedLabel }}</span>
      <button class="ai-brief-refresh" :disabled="loading" @click="refresh" :title="loading ? '生成中' : '重新生成'">
        <el-icon><Refresh /></el-icon>
      </button>
    </div>
    <div class="ai-brief-body">
      <template v-if="brief">
        <p class="ai-brief-text">{{ brief }}</p>
      </template>
      <template v-else-if="loading">
        <Skeleton type="block" width="92%" height="14px" radius="4px" />
        <Skeleton type="block" width="78%" height="14px" radius="4px" />
        <Skeleton type="block" width="64%" height="14px" radius="4px" />
      </template>
      <template v-else>
        <p class="ai-brief-empty">点刷新生成今日简报</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/index'
import Skeleton from '@/components/Skeleton.vue'
import { Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  // 当前工作台 summary 对象
  summary: { type: Object, default: () => ({}) },
})

const CACHE_KEY = 'yx_ai_brief_v1'
const brief = ref('')
const loading = ref(false)
const updatedAt = ref(0)

const updatedLabel = computed(() => {
  if (!updatedAt.value) return ''
  const d = new Date(updatedAt.value)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  return sameDay ? `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}` : `${d.getMonth() + 1}/${d.getDate()}`
})

function loadCache() {
  try {
    const c = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}')
    if (c && c.ts && c.text) {
      // 4 小时内命中即复用
      if (Date.now() - c.ts < 4 * 60 * 60 * 1000) {
        brief.value = c.text
        updatedAt.value = c.ts
        return true
      }
    }
  } catch {}
  return false
}

function saveCache(text) {
  const ts = Date.now()
  brief.value = text
  updatedAt.value = ts
  try { localStorage.setItem(CACHE_KEY, JSON.stringify({ ts, text })) } catch {}
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  try {
    // 用专用轻量端点：/api/workbench/dashboard/brief（不需要 ability/conversation_id）
    // 后端会基于用户的近期笔记 + 默认 AI Provider 自动生成 ≤120 字简报
    const r = await api.get('/workbench/dashboard/brief')
    const text = (r?.data?.text || '').trim()
    if (text) saveCache(text)
  } catch (e) {
    // 失败时不覆盖缓存（保留旧的）
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (!loadCache()) refresh()
})
</script>

<style scoped>
.ai-brief {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 16px 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 132px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--dp-shadow);
  transition: border-color .2s ease;
}
.ai-brief::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 100% at 100% 0%, rgba(126, 136, 243, 0.10), transparent 70%),
    radial-gradient(ellipse 50% 80% at 0% 100%, rgba(103, 232, 249, 0.08), transparent 70%);
  pointer-events: none;
}
.ai-brief:hover { border-color: var(--dp-line-strong); }
.ai-brief-head {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 1;
}
.ai-brief-mark {
  color: var(--dp-accent, #67e8f9);
  font-size: 16px;
  line-height: 1;
}
.ai-brief-title {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--dp-text2);
  font-weight: 600;
}
.ai-brief-time {
  margin-left: auto;
  font-size: 11px;
  color: var(--dp-text3);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}
.ai-brief-refresh {
  border: 0;
  background: transparent;
  color: var(--dp-text3);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color .15s, background .15s;
}
.ai-brief-refresh:hover { color: var(--dp-accent); background: var(--dp-accent-faint, rgba(127, 168, 163, 0.12)); }
.ai-brief-refresh:disabled { cursor: not-allowed; opacity: 0.6; }
.ai-brief-body {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-brief-text {
  font-size: 14.5px;
  line-height: 1.7;
  color: var(--dp-text);
  margin: 0;
  letter-spacing: 0.01em;
}
.ai-brief-empty {
  font-size: 13px;
  color: var(--dp-text3);
  margin: 0;
}
.loading::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(127,127,160,0.06), transparent);
  animation: ai-shimmer 1.4s linear infinite;
  pointer-events: none;
}
@keyframes ai-shimmer { from { transform: translateX(-100%); } to { transform: translateX(100%); } }
@media (prefers-reduced-motion: reduce) {
  .loading::after { animation: none; }
}
</style>
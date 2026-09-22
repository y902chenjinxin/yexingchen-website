<!--
  OnThisDayCard.vue
  玄黄・工作台"历史上的今天"卡片
  - 优先用后端内置精选（中文友好），不足则 Wikipedia OnThisDay API 兜底
  - 同一天顺序稳定（hash 种子），点"换一组"打乱
  - 列表展开/收起，避免首屏过挤
-->
<template>
  <div class="od-card" :class="{ 'od-card--loading': loading && !items.length }">
    <header class="od-head">
      <div class="od-head-left">
        <span class="od-eyebrow">历史上的今天</span>
        <span class="od-date">{{ dateLabel }}</span>
      </div>
      <button
        class="od-refresh"
        :class="{ spinning: refreshing }"
        :disabled="refreshing"
        @click="goHistory"
        title="打开独立历史页面（带横向时间轴）"
        aria-label="打开历史页面"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 17L17 7M17 7H8M17 7V16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </header>

    <ul v-if="items.length" class="od-list" :class="{ collapsed }">
      <li v-for="(it, idx) in displayItems" :key="`${it.year}-${idx}`" class="od-item">
        <span class="od-year">{{ it.year || '—' }}</span>
        <span class="od-text">
          <span class="od-title">{{ it.title }}</span>
          <span v-if="it.desc && !collapsed" class="od-desc">{{ it.desc }}</span>
        </span>
      </li>
    </ul>

    <div v-if="items.length > 3" class="od-toggle">
      <button class="od-toggle-btn" @click="collapsed = !collapsed">
        {{ collapsed ? `展开剩余 ${items.length - 3} 条` : '收起' }}
        <span class="od-toggle-arrow" :class="{ up: !collapsed }">▾</span>
      </button>
    </div>

    <div v-else-if="!loading && !items.length" class="od-empty">今日暂无记录</div>
    <div v-else-if="loading" class="od-loading">
      <span class="od-dot"></span><span class="od-dot"></span><span class="od-dot"></span>
    </div>
  </div>
</template>

<script>
export default { name: 'OnThisDayCard' }
</script>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { workbenchApi } from '@/api/workbench'

const router = useRouter()

const items = ref([])
const loading = ref(true)
const refreshing = ref(false)
const collapsed = ref(true)
const date = ref(new Date())

async function load(refresh = false) {
  if (refresh) refreshing.value = true
  else loading.value = true
  try {
    const res = await workbenchApi.todayInHistory(refresh ? { refresh: true } : {})
    // workbenchApi 拦截器返回的 res 已经是 {code, msg, data: {...业务字段}}，直接读 res.data 拿业务对象
    const data = (res && typeof res === 'object' && 'data' in res) ? (res.data || {}) : (res || {})
    items.value = Array.isArray(data.items) ? data.items : []
    if (data.date) date.value = new Date(data.date)
  } catch {
    /* 静默 */
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function refresh() { await load(true) }
function goHistory() {
  router.push('/history')
}

const dateLabel = computed(() => {
  const d = date.value
  if (!(d instanceof Date) || isNaN(d)) return ''
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

const displayItems = computed(() => collapsed.value ? items.value.slice(0, 3) : items.value)

onMounted(load)
</script>

<style scoped>
.od-card {
  padding: 20px 22px 18px;
  border-radius: 16px;
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  box-shadow: var(--dp-shadow);
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}
/* 暗纹 */
.od-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 100% 0%, rgba(99, 102, 241, 0.06), transparent 60%);
  pointer-events: none;
}

.od-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
  position: relative;
}
.od-head-left { display: flex; align-items: baseline; gap: 10px; }
.od-eyebrow {
  font-size: 12px;
  letter-spacing: .12em;
  color: var(--dp-text2);
  text-transform: uppercase;
}
.od-date {
  font-size: 13px;
  color: var(--dp-accent);
  font-weight: 600;
  letter-spacing: .04em;
}

.od-refresh {
  width: 26px; height: 26px;
  border: 1px solid var(--dp-line);
  border-radius: 50%;
  background: transparent;
  color: var(--dp-text2);
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  transition: all .2s ease;
}
.od-refresh:hover {
  background: var(--dp-accent-faint);
  color: var(--dp-accent);
  border-color: var(--dp-accent);
}
.od-refresh svg { width: 14px; height: 14px; }
.od-refresh.spinning svg { animation: od-spin 0.9s linear infinite; }
@keyframes od-spin { to { transform: rotate(360deg); } }
.od-refresh:disabled { opacity: 0.6; cursor: not-allowed; }

.od-list {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column;
  gap: 10px;
  position: relative;
  flex: 1;
}
.od-list.collapsed { flex: none; }

.od-item {
  display: flex; gap: 12px;
  font-size: 13px;
  line-height: 1.6;
  align-items: flex-start;
}
.od-year {
  flex-shrink: 0;
  min-width: 44px;
  padding-top: 1px;
  font-family: Georgia, serif;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: var(--dp-accent);
  font-weight: 600;
}
.od-text {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column;
  gap: 2px;
}
.od-title {
  color: var(--dp-text);
  font-weight: 500;
}
.od-desc {
  color: var(--dp-text3);
  font-size: 12px;
  line-height: 1.6;
}

.od-toggle {
  margin-top: 10px;
  display: flex; justify-content: center;
}
.od-toggle-btn {
  background: transparent;
  border: 1px dashed var(--dp-line);
  color: var(--dp-text2);
  font-size: 12px;
  padding: 4px 14px;
  border-radius: 999px;
  cursor: pointer;
  display: inline-flex; align-items: center; gap: 4px;
  transition: all .2s;
}
.od-toggle-btn:hover {
  color: var(--dp-accent);
  border-color: var(--dp-accent);
  border-style: solid;
}
.od-toggle-arrow { display: inline-block; transition: transform .2s; }
.od-toggle-arrow.up { transform: rotate(180deg); }

.od-empty { font-size: 13px; color: var(--dp-text3); margin: auto 0; text-align: center; }
.od-loading { display: flex; gap: 6px; padding: 20px 0; justify-content: center; }
.od-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--dp-accent);
  animation: od-bounce 1s ease-in-out infinite;
}
.od-dot:nth-child(2) { animation-delay: .15s; }
.od-dot:nth-child(3) { animation-delay: .3s; }
@keyframes od-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .4; }
  40% { transform: translateY(-4px); opacity: 1; }
}

@media (max-width: 600px) {
  .od-card { padding: 16px 16px 14px; }
  .od-item { gap: 8px; font-size: 12px; }
  .od-year { min-width: 38px; font-size: 11px; }
}
</style>
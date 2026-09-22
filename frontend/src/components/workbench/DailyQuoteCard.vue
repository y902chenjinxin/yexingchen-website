<!--
  DailyQuoteCard.vue
  玄黄・工作台"每日一言"卡片
  - 后端代理 hitokoto.cn，无 key、无频限；外网挂时降级到内置金句
  - 一日一换：当日同用户拿到同一句；点"换一句"可强制刷新
  - 折角信纸风格（柔和纸张色 + 折角 + 提引号），契合工作台古朴基调
-->
<template>
  <div class="dq-card" :class="{ 'dq-card--loading': loading && !quote }">
    <header class="dq-head">
      <span class="dq-eyebrow">每日一言</span>
      <button
        class="dq-refresh"
        :class="{ spinning: refreshing }"
        :disabled="refreshing"
        @click="refresh"
        title="换一句"
        aria-label="换一句"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M18 3v4h-4M6 21v-4h4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </header>

    <div v-if="loading && !quote" class="dq-loading">
      <span class="dq-dot"></span><span class="dq-dot"></span><span class="dq-dot"></span>
    </div>

    <template v-else-if="quote">
      <div class="dq-body">
        <span class="dq-quote-mark" aria-hidden="true">"</span>
        <p class="dq-text">{{ quote.hitokoto }}</p>
      </div>
      <footer class="dq-foot">
        <span class="dq-from">
          —— {{ quote.from_who || '佚名' }}
          <i v-if="quote.from && quote.from !== (quote.from_who || '佚名')">《{{ quote.from }}》</i>
        </span>
        <span v-if="quote.fallback" class="dq-tag">离线</span>
      </footer>
    </template>

    <p v-else class="dq-tip">今日一句准备中…</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { workbenchApi } from '@/api/workbench'

const quote = ref(null)
const loading = ref(true)
const refreshing = ref(false)

// 前端兜底金句：万一后端代理超时 / 跨域失败，6s 内一定要展示内容
const FRONTEND_FALLBACK = [
  { hitokoto: '万物皆有裂痕，那是光照进来的地方。', from_who: '莱昂纳德·科恩', from: 'Anthem', type: 'k' },
  { hitokoto: '凡是过往，皆为序章。', from_who: '莎士比亚', from: '暴风雨', type: 'k' },
  { hitokoto: '愿你成为自己的太阳，无需凭借谁的光。', from_who: '', from: '网络', type: 'f' },
  { hitokoto: '慢慢来，比较快。', from_who: '', from: '网络', type: 'f' },
  { hitokoto: '路虽远，行则将至；事虽难，做则必成。', from_who: '荀子', from: '劝学', type: 'i' },
  { hitokoto: '且将新火试新茶，诗酒趁年华。', from_who: '苏轼', from: '望江南·超然台作', type: 'i' },
  { hitokoto: '最清晰的脚印，踩在最泥泞的路上。', from_who: '', from: '网络', type: 'f' },
]
function pickFrontendFallback() {
  const today = new Date().toISOString().slice(0, 10)
  let h = 0
  for (const c of today) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return { ...FRONTEND_FALLBACK[h % FRONTEND_FALLBACK.length], fallback: true, date: today }
}

async function load(refresh = false) {
  if (refresh) refreshing.value = true
  else loading.value = true
  // 6s 兜底：超时直接展示前端内置，避免「今日一句准备中…」卡住
  const timer = setTimeout(() => {
    if (loading.value && !quote.value) {
      quote.value = pickFrontendFallback()
      loading.value = false
    }
  }, 6000)
  try {
    const res = await workbenchApi.dailyQuote(refresh ? { refresh: true } : {})
    const data = res?.data?.data
    if (data && data.hitokoto) {
      quote.value = data
    } else if (!quote.value) {
      quote.value = pickFrontendFallback()
    }
  } catch {
    if (!quote.value) quote.value = pickFrontendFallback()
  } finally {
    clearTimeout(timer)
    loading.value = false
    refreshing.value = false
  }
}

async function refresh() { await load(true) }

onMounted(load)
</script>

<style scoped>
.dq-card {
  position: relative;
  padding: 20px 22px 18px;
  border-radius: 16px;
  background:
    radial-gradient(ellipse at 0% 0%, rgba(255, 244, 220, 0.08), transparent 60%),
    var(--dp-surface);
  border: 1px solid var(--dp-line);
  box-shadow: var(--dp-shadow);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* 折角装饰 */
.dq-card::before {
  content: "";
  position: absolute;
  top: 0; right: 0;
  width: 28px; height: 28px;
  background: linear-gradient(225deg, transparent 50%, var(--dp-surface2) 50%);
  border-bottom-left-radius: 6px;
}

.dq-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px;
}
.dq-eyebrow {
  font-size: 12px;
  letter-spacing: .12em;
  color: var(--dp-text2);
  text-transform: uppercase;
}

.dq-refresh {
  width: 26px; height: 26px;
  border: 1px solid var(--dp-line);
  border-radius: 50%;
  background: transparent;
  color: var(--dp-text2);
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  transition: all .2s ease;
}
.dq-refresh:hover {
  background: var(--dp-accent-faint);
  color: var(--dp-accent);
  border-color: var(--dp-accent);
}
.dq-refresh svg { width: 14px; height: 14px; }
.dq-refresh.spinning svg { animation: dq-spin 0.9s linear infinite; }
@keyframes dq-spin { to { transform: rotate(360deg); } }
.dq-refresh:disabled { opacity: 0.6; cursor: not-allowed; }

.dq-body {
  flex: 1;
  display: flex; align-items: flex-start;
  gap: 6px;
  margin: 6px 0 8px;
  min-height: 88px;
}
.dq-quote-mark {
  font-family: Georgia, serif;
  font-size: 32px;
  line-height: 1;
  color: var(--dp-accent);
  flex-shrink: 0;
  margin-top: -2px;
  opacity: 0.7;
}
.dq-text {
  margin: 0;
  flex: 1;
  font-size: 15px;
  line-height: 1.75;
  color: var(--dp-text);
  font-weight: 500;
  letter-spacing: .01em;
}

.dq-foot {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px;
  color: var(--dp-text2);
  padding-top: 8px;
  border-top: 1px dashed var(--dp-line);
}
.dq-from i { font-style: normal; opacity: 0.8; }
.dq-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.15);
  color: var(--dp-warning, #f59e0b);
  letter-spacing: .04em;
}

.dq-tip { font-size: 13px; color: var(--dp-text3); margin: auto 0; }

.dq-loading { display: flex; gap: 6px; padding: 20px 0; justify-content: center; }
.dq-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--dp-accent);
  animation: dq-bounce 1s ease-in-out infinite;
}
.dq-dot:nth-child(2) { animation-delay: .15s; }
.dq-dot:nth-child(3) { animation-delay: .3s; }
@keyframes dq-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .4; }
  40% { transform: translateY(-4px); opacity: 1; }
}

/* 移动端稍微压缩 */
@media (max-width: 600px) {
  .dq-card { padding: 16px 16px 14px; }
  .dq-text { font-size: 14px; }
}
</style>
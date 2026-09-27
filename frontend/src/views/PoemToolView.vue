<template>
  <IslandInnerBase type="tool" title="AI 诗签" subtitle="每日一签 · 当天恒定 · 可重掷">
    <div class="poem-tool">
      <div class="pt-paper" :class="{ 'is-loading': loading }">
        <div class="pt-date">{{ dateStr }}</div>
        <div v-if="loading" class="pt-loading">研墨中…</div>
        <div v-else-if="text" class="pt-text">{{ text }}</div>
        <div v-else class="pt-loading">今日尚未求签</div>
        <div class="pt-seal">玄黄</div>
      </div>
      <div class="pt-actions">
        <button class="pt-btn primary" :disabled="loading" @click="draw(false)">{{ text ? '查看今日' : '求一签' }}</button>
        <button class="pt-btn" :disabled="loading" @click="draw(true)">重掷一签</button>
        <button v-if="text" class="pt-btn" @click="copy">复制</button>
      </div>
      <div class="pt-note">配置过 AI Provider 时由 AI 生成；未配置时从内置诗池取。同一天同一签，重掷会覆盖。</div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'
import { getPoem } from '@/api/toolkit'
import { copyText as copyToClipboard } from '@/utils/clipboard'

const text = ref('')
const dateStr = ref('')
const loading = ref(false)

async function draw(refresh) {
  loading.value = true
  try {
    const body = await getPoem(refresh ? 1 : 0)
    text.value = body?.data?.text || ''
    dateStr.value = body?.data?.date || ''
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '求签失败')
  } finally {
    loading.value = false
  }
}
async function copy() {
  await copyToClipboard(text.value)
}
onMounted(() => draw(false))
</script>

<style scoped>
.pt-paper {
  max-width: 420px; margin: 0 auto; padding: 34px 30px; border-radius: 4px; text-align: center;
  background: linear-gradient(160deg, #faf6ec, #f3ecd9);
  border: 1px solid rgba(142, 106, 44, .25);
  box-shadow: 0 3px 18px rgba(142, 106, 44, .12);
  position: relative; min-height: 220px;
  display: flex; flex-direction: column; justify-content: center; gap: 16px;
}
.pt-date { font-size: 12px; color: #a08a5a; letter-spacing: .2em; }
.pt-text {
  font-family: "Kaiti SC", "STKaiti", KaiTi, serif;
  font-size: 19px; line-height: 2.1; color: #4a3b22; white-space: pre-wrap;
}
.pt-loading { color: #b0a480; font-size: 14px; }
.pt-seal {
  position: absolute; right: 18px; bottom: 14px;
  width: 34px; height: 34px; border-radius: 6px; background: #b03a2e; color: #fff;
  font-size: 12px; line-height: 1.1; display: flex; align-items: center; justify-content: center;
  writing-mode: vertical-rl; opacity: .85;
}
.pt-actions { display: flex; gap: 10px; justify-content: center; margin-top: 18px; flex-wrap: wrap; }
.pt-btn {
  padding: 9px 22px; border-radius: 10px; font-size: 13.5px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a);
}
.pt-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.pt-btn:disabled { opacity: .55; }
.pt-note { margin-top: 12px; text-align: center; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>

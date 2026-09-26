<template>
  <IslandInnerBase type="tool" title="OCR 文字识别" subtitle="本地推理 · 中文优先 · 无需外部服务">
    <div class="ocr-tool">
      <div class="ot-head">
        <span class="ot-badge">🖥 图片上传到服务器后由本地引擎识别（不调用第三方 API），识别完即刻释放。</span>
      </div>

      <div
        class="ot-drop"
        :class="{ drag }"
        @click="!processing && $refs.fileInput.click()"
        @dragover.prevent="drag = true"
        @dragleave="drag = false"
        @drop.prevent="onDrop"
      >
        <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" class="ot-file" @change="onPick">
        <p v-if="!srcUrl">{{ processing ? '识别中…' : '点击选择 / 拖入 / 粘贴（Ctrl+V）图片（≤ 12MB）' }}</p>
        <img v-else class="ot-preview" :src="srcUrl" alt="待识别图片">
      </div>

      <div v-if="processing" class="ot-status">识别中，通常 1~3 秒…</div>
      <div v-if="error" class="ot-err">{{ error }}</div>

      <div v-if="resultText !== null" class="ot-result">
        <div class="ot-meta">
          共 {{ lineCount }} 行 · 引擎 rapidocr
          <button class="ot-mini-btn" @click="copyText">复制全文</button>
        </div>
        <div v-if="resultText" class="ot-text">{{ resultText }}</div>
        <div v-else class="ot-empty">没有识别到文字 —— 试试更清晰的图片？</div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'
import { ocrImage } from '@/api/toolkit'

const fileInput = ref(null)
const srcUrl = ref('')
const processing = ref(false)
const error = ref('')
const resultText = ref(null)
const lineCount = ref(0)
const drag = ref(false)

function onPick(e) {
  const f = e.target.files?.[0]
  if (f) recognize(f)
  e.target.value = ''
}
function onDrop(e) {
  drag.value = false
  const f = e.dataTransfer.files?.[0]
  if (f) recognize(f)
}
function onPaste(e) {
  const item = [...(e.clipboardData?.items || [])].find(i => i.type.startsWith('image/'))
  if (item && !processing.value) recognize(item.getAsFile())
}

async function recognize(file) {
  error.value = ''
  resultText.value = null
  srcUrl.value = URL.createObjectURL(file)
  processing.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    // 拦截器 return response.data → {code, msg, data}
    const body = await ocrImage(fd)
    if (!body || body.code !== 0) throw new Error(body?.msg || '识别失败')
    resultText.value = body.data.text
    lineCount.value = body.data.lines
    ElMessage.success(`识别完成，共 ${body.data.lines} 行`)
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.msg || e?.message || '识别失败，请稍后再试'
  } finally {
    processing.value = false
  }
}

async function copyText() {
  try { await navigator.clipboard.writeText(resultText.value); ElMessage.success('已复制') } catch { /* 忽略 */ }
}

onMounted(() => document.addEventListener('paste', onPaste))
onBeforeUnmount(() => document.removeEventListener('paste', onPaste))
</script>

<style scoped>
.ot-head { margin-bottom: 14px; }
.ot-badge {
  display: inline-block; font-size: 12.5px; padding: 8px 14px; border-radius: 10px;
  background: rgba(127, 168, 163, 0.12); color: var(--dp-text2, #45505b); line-height: 1.6;
}
.ot-drop {
  border: 1.5px dashed var(--dp-line, rgba(0,0,0,.18)); border-radius: 14px;
  padding: 34px 20px; text-align: center; cursor: pointer; color: var(--dp-text3, #8a8f98); font-size: 13.5px;
  transition: border-color .15s, background .15s;
}
.ot-drop.drag { border-color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.06); }
.ot-file { display: none; }
.ot-preview { max-width: 100%; max-height: 420px; border-radius: 10px; }
.ot-status { margin-top: 12px; font-size: 13px; color: var(--dp-text3, #8a8f98); }
.ot-err { margin-top: 12px; color: #e5484d; font-size: 13px; }
.ot-result { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
.ot-meta { display: flex; align-items: center; gap: 12px; font-size: 12.5px; color: var(--dp-text3, #8a8f98); }
.ot-mini-btn {
  padding: 4px 12px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b);
}
.ot-mini-btn:hover { background: rgba(199,169,107,.14); }
.ot-text {
  padding: 14px 16px; border-radius: 12px; font-size: 14px; line-height: 1.8;
  background: var(--dp-bg2, rgba(0,0,0,.03)); border: 1px solid var(--dp-line, rgba(0,0,0,.08));
  white-space: pre-wrap; word-break: break-all; color: var(--dp-text, #18202a);
  max-height: 420px; overflow-y: auto;
}
.ot-empty { font-size: 13px; color: var(--dp-text3, #8a8f98); }
</style>

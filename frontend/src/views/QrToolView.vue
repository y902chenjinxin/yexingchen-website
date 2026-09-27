<template>
  <IslandInnerBase type="tool" title="二维码" subtitle="生成 · 解析 · 纯本地处理">
    <div class="qr-tool">
      <div class="qt-head">
        <span class="qt-badge">🔒 全部在浏览器本地完成，内容不经过服务器。</span>
      </div>

      <div class="qt-tabs">
        <button class="qt-tab" :class="{ active: tab === 'gen' }" @click="tab = 'gen'">生成</button>
        <button class="qt-tab" :class="{ active: tab === 'parse' }" @click="tab = 'parse'">解析</button>
      </div>

      <!-- ===== 生成 ===== -->
      <div v-if="tab === 'gen'" class="qt-pane">
        <textarea
          v-model="genText"
          class="qt-input"
          rows="4"
          placeholder="输入文字、链接、WiFi 信息…（支持中文，自动按 UTF-8 编码）"
        ></textarea>
        <div class="qt-gen-opts">
          <label class="qt-opt">尺寸
            <b class="hl">{{ genSize }}px</b>
            <input v-model.number="genSize" type="range" min="180" max="520" step="20">
          </label>
          <label class="qt-opt">纠错级别
            <select v-model="genLevel">
              <option value="L">L（7%）</option>
              <option value="M">M（15%）</option>
              <option value="Q">Q（25%）</option>
              <option value="H">H（30%，最抗遮挡）</option>
            </select>
          </label>
        </div>
        <div v-if="genError" class="qt-err">{{ genError }}</div>
        <div v-if="dataUrl" class="qt-result">
          <img class="qt-img" :src="dataUrl" alt="二维码预览">
          <div class="qt-actions">
            <button class="qt-btn primary" @click="downloadQr">下载 PNG</button>
            <button class="qt-btn" @click="copyImage">复制图片</button>
          </div>
        </div>
      </div>

      <!-- ===== 解析 ===== -->
      <div v-else class="qt-pane">
        <div
          class="qt-drop"
          :class="{ drag }"
          @click="$refs.fileInput.click()"
          @dragover.prevent="drag = true"
          @dragleave="drag = false"
          @drop.prevent="onDrop"
        >
          <input ref="fileInput" type="file" accept="image/*" class="qt-file" @change="onPick">
          <p v-if="!parseSrc">点击选择 / 拖入 / 粘贴（Ctrl+V）含二维码的图片</p>
          <img v-else class="qt-preview" :src="parseSrc" alt="待解析图片">
        </div>
        <div v-if="parseError" class="qt-err">{{ parseError }}</div>
        <div v-if="parsedText !== null" class="qt-result">
          <div class="qt-parsed">{{ parsedText }}</div>
          <div class="qt-actions">
            <button class="qt-btn primary" @click="copyText(parsedText)">复制内容</button>
            <a v-if="isUrl(parsedText)" class="qt-btn" :href="parsedText" target="_blank" rel="noopener">打开链接</a>
          </div>
        </div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import QRCode from 'qrcode'
import jsQR from 'jsqr'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'
// 复制统一走 utils（含降级 + 失败提示），别再用各页自己的 catch 忽略
import { copyText as copyToClipboard, copyImage as copyImageToClipboard } from '@/utils/clipboard'

const tab = ref('gen')

// ---- 生成 ----
const genText = ref('')
const genSize = ref(300)
const genLevel = ref('M')
const dataUrl = ref('')
const genError = ref('')

async function renderGen() {
  genError.value = ''
  dataUrl.value = ''
  if (!genText.value.trim()) return
  try {
    dataUrl.value = await QRCode.toDataURL(genText.value, {
      width: genSize.value,
      errorCorrectionLevel: genLevel.value,
      margin: 2,
      color: { dark: '#0f1530', light: '#ffffff' },
    })
  } catch (e) {
    genError.value = '生成失败：' + (e?.message || '内容过长或含无法编码的字符')
  }
}
watch([genText, genSize, genLevel], renderGen, { immediate: false })

async function downloadQr() {
  const a = document.createElement('a')
  a.href = dataUrl.value
  a.download = `qrcode-${Date.now()}.png`
  a.click()
}
async function copyImage() {
  await copyImageToClipboard(dataUrl.value)
}

// ---- 解析 ----
const parseSrc = ref('')
const parsedText = ref(null)
const parseError = ref('')
const drag = ref(false)
const fileInput = ref(null)

function isUrl(s) { return /^https?:\/\//i.test(s || '') }
async function copyText(s) {
  await copyToClipboard(s)
}

function onPick(e) {
  const f = e.target.files?.[0]
  if (f) decodeFile(f)
  e.target.value = ''
}
function onDrop(e) {
  drag.value = false
  const f = e.dataTransfer.files?.[0]
  if (f) decodeFile(f)
}
function onPaste(e) {
  const item = [...(e.clipboardData?.items || [])].find(i => i.type.startsWith('image/'))
  if (item) decodeFile(item.getAsFile())
}

function decodeFile(file) {
  parseError.value = ''
  parsedText.value = null
  const reader = new FileReader()
  reader.onload = () => {
    parseSrc.value = reader.result
    const img = new Image()
    img.onload = () => {
      const cv = document.createElement('canvas')
      // 上限 1600px，jsQR 对超大图反而慢且易失败
      const scale = Math.min(1, 1600 / Math.max(img.width, img.height))
      cv.width = Math.max(1, Math.round(img.width * scale))
      cv.height = Math.max(1, Math.round(img.height * scale))
      const ctx = cv.getContext('2d')
      ctx.drawImage(img, 0, 0, cv.width, cv.height)
      const res = jsQR(ctx.getImageData(0, 0, cv.width, cv.height).data, cv.width, cv.height)
      if (res?.data) {
        parsedText.value = res.data
        ElMessage.success('解析成功')
      } else {
        parseError.value = '未识别到二维码：请确保二维码清晰、完整，且图片不要太模糊'
      }
    }
    img.onerror = () => { parseError.value = '图片无法加载' }
    img.src = reader.result
  }
  reader.readAsDataURL(file)
}

onMounted(() => document.addEventListener('paste', onPaste))
onBeforeUnmount(() => document.removeEventListener('paste', onPaste))
</script>

<style scoped>
.qt-head { margin-bottom: 14px; }
.qt-badge {
  display: inline-block; font-size: 12.5px; padding: 8px 14px; border-radius: 10px;
  background: rgba(127, 168, 163, 0.12); color: var(--dp-text2, #45505b); line-height: 1.6;
}
.qt-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.qt-tab {
  padding: 8px 22px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 13.5px;
}
.qt-tab.active {
  background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600;
}
.qt-pane { display: flex; flex-direction: column; gap: 14px; }
.qt-input, .qt-opt select {
  width: 100%; padding: 10px 12px; border-radius: 10px; font-size: 14px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.12)); background: var(--dp-surface, #fff);
  color: var(--dp-text, #18202a); resize: vertical;
}
.qt-gen-opts { display: flex; gap: 18px; flex-wrap: wrap; }
.qt-opt { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--dp-text2, #45505b); }
.qt-opt input[type=range] { width: 160px; }
.qt-opt select { width: auto; }
.hl { color: var(--yq-gold, #c7a96b); }
.qt-result { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.qt-img {
  background: #fff; padding: 12px; border-radius: 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,.08); max-width: 100%;
}
.qt-preview { max-width: 100%; max-height: 320px; border-radius: 10px; }
.qt-parsed {
  width: 100%; padding: 12px 14px; border-radius: 10px; font-size: 14px; line-height: 1.7;
  background: var(--dp-bg2, rgba(0,0,0,.03)); border: 1px solid var(--dp-line, rgba(0,0,0,.08));
  word-break: break-all; white-space: pre-wrap; color: var(--dp-text, #18202a);
}
.qt-actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.qt-btn {
  padding: 9px 20px; border-radius: 10px; font-size: 13.5px; cursor: pointer; text-decoration: none;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text, #18202a);
}
.qt-btn.primary {
  background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600;
}
.qt-drop {
  border: 1.5px dashed var(--dp-line, rgba(0,0,0,.18)); border-radius: 14px;
  padding: 34px 20px; text-align: center; cursor: pointer; color: var(--dp-text3, #8a8f98); font-size: 13.5px;
  transition: border-color .15s, background .15s;
}
.qt-drop.drag { border-color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.06); }
.qt-file { display: none; }
.qt-err { color: #e5484d; font-size: 13px; }
</style>

<template>
  <IslandInnerBase type="tool" title="语音转文字" subtitle="SenseVoice 本地推理 · 中文优先 · 支持录音/上传">
    <div class="asr-tool">
      <div class="at-head">
        <span class="at-badge" :class="{ ok: engineReady === true, warn: engineReady === false }">
          {{ engineText }}
        </span>
      </div>

      <!-- 输入区 -->
      <div class="at-inputs">
        <button
          class="at-record"
          :class="{ recording }"
          :disabled="processing"
          @click="toggleRecord"
        >
          <span class="at-record-dot"></span>
          {{ recording ? `停止录音（${recordSeconds}s）` : '开始录音' }}
        </button>
        <button class="at-upload-btn" :disabled="processing" @click="$refs.fileInput.click()">
          {{ processing ? '识别中…' : '上传音频文件' }}
        </button>
        <input ref="fileInput" type="file" accept="audio/*,video/mp4" class="at-file" @change="onPick">
      </div>
      <div class="at-note">上传的任意格式（mp3 / m4a / webm…）会先在浏览器本地转成 16k 单声道 WAV 再上传，服务端不需要 ffmpeg。</div>

      <div v-if="processing" class="at-status">{{ statusText }}</div>
      <div v-if="error" class="at-err">{{ error }}</div>

      <!-- 结果 -->
      <div v-if="resultText !== null" class="at-result">
        <div class="at-meta">
          时长 {{ resultSeconds }}s · 引擎 SenseVoice
          <button class="at-mini-btn" @click="copyText">复制</button>
          <button class="at-mini-btn" @click="appendTo(resultText)">追加到闪念</button>
        </div>
        <div v-if="resultText" class="at-text">{{ resultText }}</div>
        <div v-else class="at-empty">没有识别到语音内容 —— 录音再长一点试试？</div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'
import { asrStatus, asrTranscribe } from '@/api/toolkit'
import { copyText as copyToClipboard } from '@/utils/clipboard'
import { quickApi } from '@/api/quick'

const engineReady = ref(null)   // null=查询中 true/false
const engineText = computed(() => {
  if (engineReady.value === null) return '正在检查服务端引擎…'
  return engineReady.value
    ? '🟢 服务端引擎就绪（SenseVoice · 纯 CPU 本地推理，音频不经过第三方）'
    : '🟡 服务端未部署识别模型，暂不可用 —— 请联系管理员部署（backend/models/sherpa-onnx-sense-voice）'
})

const recording = ref(false)
const recordSeconds = ref(0)
const processing = ref(false)
const statusText = ref('')
const error = ref('')
const resultText = ref(null)
const resultSeconds = ref(0)
const fileInput = ref(null)

let mediaRecorder = null
let chunks = []
let timerId = 0
let audioCtx = null

asrStatus().then((body) => { engineReady.value = !!body?.data?.ready }).catch(() => { engineReady.value = false })

// ---- 录音 ----
async function toggleRecord() {
  if (recording.value) {
    mediaRecorder.stop()
    return
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    chunks = []
    mediaRecorder = new MediaRecorder(stream)
    mediaRecorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      clearInterval(timerId)
      recording.value = false
      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' })
      await transcribeBlob(blob)
    }
    mediaRecorder.start()
    recording.value = true
    recordSeconds.value = 0
    timerId = setInterval(() => { recordSeconds.value++ }, 1000)
  } catch {
    ElMessage.error('无法访问麦克风：请检查浏览器权限')
  }
}

function onPick(e) {
  const f = e.target.files?.[0]
  if (f) transcribeBlob(f)
  e.target.value = ''
}

// ---- 浏览器本地转 16k 单声道 WAV（免去服务端 ffmpeg）----
async function blobToWav16k(blob) {
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
  const buf = await audioCtx.decodeAudioData(await blob.arrayBuffer())
  // OfflineAudioContext 重采样到 16k 单声道
  const length = Math.max(1, Math.ceil(buf.duration * 16000))
  const offline = new OfflineAudioContext(1, length, 16000)
  const src = offline.createBufferSource()
  src.buffer = buf
  src.connect(offline.destination)
  src.start()
  const rendered = await offline.startRendering()
  const samples = rendered.getChannelData(0)
  // 编码 PCM16 WAV
  const wav = new DataView(new ArrayBuffer(44 + samples.length * 2))
  const w = (off, s) => { for (let i = 0; i < s.length; i++) wav.setUint8(off + i, s.charCodeAt(i)) }
  w(0, 'RIFF'); wav.setUint32(4, 36 + samples.length * 2, true); w(8, 'WAVE')
  w(12, 'fmt '); wav.setUint32(16, 16, true); wav.setUint16(20, 1, true); wav.setUint16(22, 1, true)
  wav.setUint32(24, 16000, true); wav.setUint32(28, 32000, true); wav.setUint16(32, 2, true); wav.setUint16(34, 16, true)
  w(36, 'data'); wav.setUint32(40, samples.length * 2, true)
  let off = 44
  for (let i = 0; i < samples.length; i++, off += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    wav.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([wav.buffer], { type: 'audio/wav' })
}

async function transcribeBlob(blob) {
  error.value = ''
  resultText.value = null
  processing.value = true
  statusText.value = '正在本地转换音频（16k 单声道）…'
  try {
    const wav = await blobToWav16k(blob)
    statusText.value = '已上传，服务器识别中…'
    const fd = new FormData()
    fd.append('file', wav, 'audio.wav')
    const body = await asrTranscribe(fd)
    if (!body || body.code !== 0) throw new Error(body?.msg || '识别失败')
    resultText.value = body.data.text
    resultSeconds.value = body.data.seconds
    ElMessage.success('识别完成')
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.msg || e?.message || '识别失败，请稍后再试'
  } finally {
    processing.value = false
    statusText.value = ''
  }
}

async function copyText() {
  await copyToClipboard(resultText.value)
}

/** 追加到闪念 · 日记（站点已有能力，顺手的闭环） */
async function appendTo(text) {
  try {
    await quickApi.create(text)
    ElMessage.success('已追加到闪念 · 日记')
  } catch {
    ElMessage.warning('追加失败，请手动复制')
  }
}

onBeforeUnmount(() => {
  clearInterval(timerId)
  if (recording.value && mediaRecorder) { try { mediaRecorder.stop() } catch { /* 忽略 */ } }
})
</script>

<style scoped>
.at-head { margin-bottom: 14px; }
.at-badge {
  display: inline-block; font-size: 12.5px; padding: 8px 14px; border-radius: 10px; line-height: 1.6;
  background: rgba(127, 168, 163, 0.12); color: var(--dp-text2, #45505b);
}
.at-badge.ok { background: rgba(26, 168, 106, 0.12); color: #157a4c; }
.at-badge.warn { background: rgba(226, 185, 59, 0.15); color: #8a6d1a; }
.at-inputs { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.at-record {
  display: inline-flex; align-items: center; gap: 10px; padding: 12px 26px; border-radius: 999px;
  border: none; cursor: pointer; font-size: 14.5px; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #c7a96b, #b08d4f);
}
.at-record:disabled { opacity: .55; cursor: not-allowed; }
.at-record.recording { background: linear-gradient(135deg, #e5484d, #c93a3f); }
.at-record-dot { width: 9px; height: 9px; border-radius: 50%; background: #fff; }
.at-record.recording .at-record-dot { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: .25; } }
@media (prefers-reduced-motion: reduce) { .at-record.recording .at-record-dot { animation: none; } }
.at-upload-btn {
  padding: 12px 22px; border-radius: 999px; font-size: 14px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text, #18202a);
}
.at-upload-btn:disabled { opacity: .55; cursor: not-allowed; }
.at-file { display: none; }
.at-note { margin-top: 10px; font-size: 12px; color: var(--dp-text3, #8a8f98); line-height: 1.6; }
.at-status { margin-top: 14px; font-size: 13px; color: var(--dp-text3, #8a8f98); }
.at-err { margin-top: 12px; color: #e5484d; font-size: 13px; }
.at-result { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
.at-meta { display: flex; align-items: center; gap: 10px; font-size: 12.5px; color: var(--dp-text3, #8a8f98); }
.at-mini-btn {
  padding: 4px 12px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b);
}
.at-mini-btn:hover { background: rgba(199,169,107,.14); }
.at-text {
  padding: 14px 16px; border-radius: 12px; font-size: 14.5px; line-height: 1.9;
  background: var(--dp-bg2, rgba(0,0,0,.03)); border: 1px solid var(--dp-line, rgba(0,0,0,.08));
  white-space: pre-wrap; word-break: break-all; color: var(--dp-text, #18202a);
  max-height: 420px; overflow-y: auto;
}
.at-empty { font-size: 13px; color: var(--dp-text3, #8a8f98); }
</style>

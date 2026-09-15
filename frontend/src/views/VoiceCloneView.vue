<template>
  <IslandInnerBase type="tool" title="音色克隆" subtitle="上传一段录音，复刻专属音色 · 输入文字即可开口说话">
    <!-- 未就绪：无 MiniMax Provider -->
    <div v-if="ready === false" class="vc-empty">
      <div class="vc-empty-icon">🎙️</div>
      <p>音色克隆需要 MiniMax Provider 支持</p>
      <p class="vc-empty-sub">请先到「AI 对话 → 配置 AI Provider」切换或配置 MiniMax（超管共享配置即可用）</p>
    </div>

    <div v-else class="vc-tool">
      <!-- 左：克隆与合成 -->
      <section class="vc-form">
        <div class="vc-block">
          <h3 class="vc-block-title">① 复刻音色</h3>
          <label class="vc-label">
            <span>音色名称</span>
            <input v-model="name" class="vc-input" maxlength="64" placeholder="如：爸爸 / 我的声音" />
          </label>
          <label class="vc-label">
            <span>样本录音 <i class="vc-dim">mp3 / m4a / wav，10 秒～5 分钟，≤20MB</i></span>
            <div class="vc-file" :class="{ has: sampleFile }" @click="$refs.fileRef.click()">
              {{ sampleFile ? `已选择：${sampleFile.name}` : '点击选择音频文件' }}
            </div>
            <input ref="fileRef" type="file" accept=".mp3,.m4a,audio/mpeg,audio/x-m4a,audio/wav" hidden @change="onFile" />
          </label>
          <label class="vc-label">
            <span>试听文本 <i class="vc-dim">复刻完成后用该文本生成试听</i></span>
            <input v-model="previewText" class="vc-input" maxlength="200" />
          </label>
          <button class="vc-btn" :disabled="cloning || !sampleFile" @click="doClone">
            {{ cloning ? (progress ? `上传中 ${progress}%` : '复刻中，约需十几秒…') : '开始复刻' }}
          </button>
          <p class="vc-notice">复刻本身不收费；7 天内合成一次即可永久保留音色。请仅复刻本人或已获授权的声音。</p>
        </div>

        <div class="vc-block">
          <h3 class="vc-block-title">② 文字转语音</h3>
          <label class="vc-label">
            <span>选择音色</span>
            <select v-model="selectedId" class="vc-input">
              <option v-for="v in voices" :key="v.id" :value="v.id">
                {{ v.name }}（剩 {{ v.hours_left }} 小时保留期）
              </option>
            </select>
          </label>
          <label class="vc-label">
            <span>合成文本 <i class="vc-dim">{{ speakText.length }}/2000</i></span>
            <textarea v-model="speakText" class="vc-input vc-area" rows="4" maxlength="2000"
              placeholder="输入想让这个声音读出来的文字"></textarea>
          </label>
          <div class="vc-row">
            <button class="vc-btn" :disabled="speaking || !selectedId || !speakText.trim()" @click="doSpeak">
              {{ speaking ? '合成中…' : '生成语音' }}
            </button>
            <button v-if="audioUrl" class="vc-btn ghost" @click="downloadAudio">下载 MP3</button>
          </div>
          <audio v-if="audioUrl" :src="audioUrl" controls class="vc-audio"></audio>
          <p v-if="speakErr" class="vc-err">{{ speakErr }}</p>
        </div>
      </section>

      <!-- 右：我的音色 -->
      <section class="vc-side">
        <h3 class="vc-block-title">我的音色</h3>
        <div v-if="!voices.length" class="vc-empty-sub">还没有克隆过音色</div>
        <div v-for="v in voices" :key="v.id" class="vc-voice-card">
          <div class="vc-voice-main">
            <span class="vc-voice-name">{{ v.name }}</span>
            <span class="vc-voice-meta" :class="{ expiring: v.hours_left < 24 }">
              {{ v.hours_left >= 168 ? '刚刚复刻' : `保留期剩 ${v.hours_left} 小时` }}
            </span>
          </div>
          <div class="vc-voice-actions">
            <button class="vc-mini" @click="useVoice(v)">用于合成</button>
            <button class="vc-mini danger" @click="doDelete(v)">删除</button>
          </div>
        </div>
      </section>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { getVoiceStatus, cloneVoice, deleteVoice, speakVoice, voiceErrorMsg } from '@/api/voiceClone'

const ready = ref(null)
const voices = ref([])

const name = ref('')
const sampleFile = ref(null)
const previewText = ref('你好，这是我复刻的声音，很高兴认识你。')
const cloning = ref(false)
const progress = ref(0)

const selectedId = ref(null)
const speakText = ref('')
const speaking = ref(false)
const audioUrl = ref('')
const speakErr = ref('')

const fileRef = ref(null)
let lastBlob = null

function onFile(e) {
  const f = e.target.files?.[0]
  if (!f) return
  if (f.size > 20 * 1024 * 1024) { ElMessage.warning('样本音频不能超过 20MB'); e.target.value = ''; return }
  sampleFile.value = f
}

async function refresh() {
  try {
    const res = await getVoiceStatus()
    ready.value = !!res.data?.ready
    voices.value = res.data?.voices || []
    if (!selectedId.value && voices.value.length) selectedId.value = voices.value[0].id
  } catch {
    ready.value = false
  }
}

async function doClone() {
  if (!sampleFile.value || cloning.value) return
  cloning.value = true
  progress.value = 0
  try {
    const fd = new FormData()
    fd.append('file', sampleFile.value)
    fd.append('name', name.value || '我的音色')
    fd.append('preview_text', previewText.value || '')
    const res = await cloneVoice(fd, (e) => {
      if (e.total) progress.value = Math.round((e.loaded / e.total) * 100)
    })
    ElMessage.success('复刻完成，可试听或直接用于合成')
    if (res.data?.id) {
      selectedId.value = res.data.id
      speakText.value = previewText.value
    }
    sampleFile.value = null
    if (fileRef.value) fileRef.value.value = ''
    await refresh()
  } catch (e) {
    ElMessage.error(voiceErrorMsg(e))
  } finally {
    cloning.value = false
    progress.value = 0
  }
}

function useVoice(v) {
  selectedId.value = v.id
  ElMessage.success(`已选择「${v.name}」`)
}

async function doSpeak() {
  if (speaking.value || !selectedId.value) return
  speaking.value = true
  speakErr.value = ''
  try {
    const blob = await speakVoice({ voice_record_id: selectedId.value, text: speakText.value })
    if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
    lastBlob = blob
    audioUrl.value = URL.createObjectURL(blob)
  } catch (e) {
    speakErr.value = voiceErrorMsg(e)
  } finally {
    speaking.value = false
  }
}

function downloadAudio() {
  if (!lastBlob) return
  const a = document.createElement('a')
  a.href = audioUrl.value
  a.download = `语音-${new Date().toISOString().slice(0, 10)}.mp3`
  document.body.appendChild(a)
  a.click()
  a.remove()
}

async function doDelete(v) {
  if (!window.confirm(`删除音色「${v.name}」？MiniMax 侧同步失效，不可恢复`)) return
  try {
    await deleteVoice(v.id)
    if (selectedId.value === v.id) selectedId.value = null
    await refresh()
  } catch (e) {
    ElMessage.error(voiceErrorMsg(e))
  }
}

onMounted(refresh)
onUnmounted(() => { if (audioUrl.value) URL.revokeObjectURL(audioUrl.value) })
</script>

<style scoped>
.vc-tool {
  display: grid;
  grid-template-columns: minmax(320px, 480px) minmax(240px, 1fr);
  gap: 28px;
  align-items: start;
}
@media (max-width: 900px) {
  .vc-tool { grid-template-columns: 1fr; }
}

.vc-block {
  background: var(--ls-glass, rgba(18, 26, 34, 0.5));
  border: 1px solid var(--lj-line);
  border-radius: 14px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.vc-block + .vc-block { margin-top: 18px; }
.vc-block-title { margin: 0; font-size: 15px; color: var(--lj-text); font-weight: 600; letter-spacing: 0.05em; }

.vc-label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--lj-text-2); }
.vc-label > span .vc-dim { font-style: normal; font-size: 11px; color: var(--lj-text-3); margin-left: 4px; }
.vc-input {
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01)), rgba(18, 26, 34, 0.5);
  border: 1px solid var(--lj-line);
  border-radius: 10px;
  color: var(--lj-text);
  padding: 9px 12px;
  font-size: 13px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}
.vc-input:focus { border-color: var(--lj-seal); box-shadow: 0 0 0 3px var(--lj-seal-soft); }
.vc-area { resize: vertical; min-height: 90px; font-family: inherit; }

.vc-file {
  border: 1px dashed var(--lj-line-strong);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
  font-size: 13px;
  color: var(--lj-text-3);
  cursor: pointer;
  transition: all 0.2s;
}
.vc-file:hover { border-color: var(--lj-seal); color: var(--lj-seal); }
.vc-file.has { border-style: solid; color: var(--lj-dai); border-color: var(--lj-dai); }

.vc-row { display: flex; gap: 10px; flex-wrap: wrap; }
.vc-btn {
  padding: 9px 20px;
  border: 1px solid var(--lj-seal);
  border-radius: 10px;
  background: linear-gradient(135deg, var(--lj-seal), var(--lj-seal-hover));
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  align-self: flex-start;
}
.vc-btn:hover:not(:disabled) { box-shadow: 0 6px 16px rgba(217, 138, 118, 0.3); transform: translateY(-1px); }
.vc-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.vc-btn.ghost { background: transparent; color: var(--lj-text-2); border-color: var(--lj-line); }
.vc-btn.ghost:hover:not(:disabled) { color: var(--lj-seal); border-color: var(--lj-seal); }

.vc-notice { font-size: 11px; color: var(--lj-text-3); margin: 0; }
.vc-err { font-size: 12px; color: var(--lj-vermilion); margin: 0; }
.vc-audio { width: 100%; margin-top: 4px; }

/* 右侧音色列表 */
.vc-side { display: flex; flex-direction: column; gap: 10px; }
.vc-voice-card {
  border: 1px solid var(--lj-line);
  border-radius: 12px;
  padding: 12px 14px;
  background: rgba(127, 168, 163, 0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.vc-voice-main { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.vc-voice-name { font-size: 14px; color: var(--lj-text); }
.vc-voice-meta { font-size: 11px; color: var(--lj-text-3); white-space: nowrap; }
.vc-voice-meta.expiring { color: var(--lj-vermilion); }
.vc-voice-actions { display: flex; gap: 8px; }
.vc-mini {
  padding: 5px 12px;
  border: 1px solid var(--lj-line);
  border-radius: 8px;
  background: transparent;
  color: var(--lj-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.vc-mini:hover { color: var(--lj-seal); border-color: var(--lj-seal); }
.vc-mini.danger:hover { color: var(--lj-vermilion); border-color: var(--lj-vermilion); }

.vc-empty { text-align: center; padding: 60px 0; color: var(--lj-text-2); }
.vc-empty-icon { font-size: 42px; margin-bottom: 12px; }
.vc-empty p { margin: 4px 0; font-size: 14px; }
.vc-empty-sub { font-size: 12px; color: var(--lj-text-3); }
</style>

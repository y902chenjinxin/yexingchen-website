<!--
  VoiceCloneView.vue
  玄黄・音色克隆工具
  - 三块面板：① 复刻音色（左）/ ② 文字转语音（左下）/ ③ 我的音色（右）
  - 全部控件统一为 ElementPlus（移动端有 native-glass 兜底）
  - 玄黄主题：鎏金主色 + 雨青辅色 + 玄灰描边
-->
<template>
  <IslandInnerBase type="tool" title="音色克隆" subtitle="上传一段录音，复刻专属音色 · 输入文字即可开口说话">
    <!-- 未就绪：无 MiniMax Provider -->
    <div v-if="ready === false" class="vc-empty">
      <div class="vc-empty-icon">🎙️</div>
      <p>音色克隆需要 MiniMax Provider 支持</p>
      <p class="vc-empty-sub">请先到「AI 对话 → 配置 AI Provider」切换或配置 MiniMax（超管共享配置即可用）</p>
    </div>

    <div v-else class="vc-tool">
      <!-- ============ 左栏：复刻 + 合成 ============ -->
      <div class="vc-main">
        <!-- ① 复刻音色 -->
        <section class="vc-card">
          <header class="vc-card-head">
            <span class="vc-card-step">1</span>
            <div>
              <h3 class="vc-card-title">复刻音色</h3>
              <p class="vc-card-sub">10 秒～5 分钟的清晰朗读，效果最佳</p>
            </div>
          </header>

          <div class="vc-field">
            <label class="vc-label">音色名称</label>
            <el-input v-model="name" maxlength="64" placeholder="如：爸爸 / 我的声音" clearable />
          </div>

          <div class="vc-field">
            <label class="vc-label">
              样本录音
              <i class="vc-dim">mp3 / m4a / wav，10 秒～5 分钟，≤20MB</i>
            </label>
            <div class="vc-drop" :class="{ has: !!sampleFile }" @click="$refs.fileRef?.click()">
              <input
                ref="fileRef"
                type="file"
                accept=".mp3,.m4a,audio/mpeg,audio/x-m4a,audio/wav"
                hidden
                @change="onFile"
              />
              <template v-if="!sampleFile">
                <div class="vc-drop-icon" aria-hidden="true">↑</div>
                <div class="vc-drop-text">点击选择音频文件 / 拖到此处</div>
                <div class="vc-drop-hint">支持 mp3 / m4a / wav</div>
              </template>
              <template v-else>
                <div class="vc-file-info">
                  <span class="vc-file-icon" aria-hidden="true">♪</span>
                  <div class="vc-file-meta">
                    <span class="vc-file-name">{{ sampleFile.name }}</span>
                    <span class="vc-file-size">{{ formatSize(sampleFile.size) }} · 时长待识别</span>
                  </div>
                  <button class="vc-file-remove" type="button" @click.stop="clearFile" aria-label="移除文件">×</button>
                </div>
              </template>
            </div>
          </div>

          <div class="vc-field">
            <label class="vc-label">
              试听文本
              <i class="vc-dim">复刻完成后用该文本生成试听</i>
            </label>
            <el-input
              v-model="previewText"
              type="textarea"
              :rows="2"
              maxlength="200"
              show-word-limit
              resize="none"
            />
            <div class="vc-presets">
              <button v-for="p in presetTexts" :key="p" class="vc-chip" type="button" @click="previewText = p">
                {{ p }}
              </button>
            </div>
          </div>

          <div class="vc-actions">
            <button class="vc-btn vc-btn-primary" :disabled="cloning || !sampleFile" @click="doClone">
              <span v-if="cloning" class="vc-spin" aria-hidden="true"></span>
              <span v-if="!cloning">开始复刻</span>
              <span v-else>{{ progress ? `上传中 ${progress}%` : '复刻中，约需十几秒…' }}</span>
            </button>
            <div v-if="cloning && progress" class="vc-progress" :style="{ width: progress + '%' }"></div>
          </div>

          <p class="vc-notice">复刻本身不收费；7 天内合成一次即可永久保留音色。请仅复刻本人或已获授权的声音。</p>
        </section>

        <!-- ② 文字转语音 -->
        <section class="vc-card">
          <header class="vc-card-head">
            <span class="vc-card-step">2</span>
            <div>
              <h3 class="vc-card-title">文字转语音</h3>
              <p class="vc-card-sub">选择已复刻的音色，让它读出文字</p>
            </div>
          </header>

          <div class="vc-field">
            <label class="vc-label">选择音色</label>
            <el-select v-model="selectedId" placeholder="请选择音色" class="vc-select-full" :empty-text="voices.length ? '暂无音色' : '请先复刻一个音色'">
              <el-option
                v-for="v in voices"
                :key="v.id"
                :value="v.id"
                :label="`${v.name} · 剩 ${v.hours_left} 小时`"
              />
            </el-select>
          </div>

          <div class="vc-field">
            <label class="vc-label">
              合成文本
              <i class="vc-dim">最多 2000 字</i>
            </label>
            <el-input
              v-model="speakText"
              type="textarea"
              :rows="5"
              maxlength="2000"
              show-word-limit
              resize="vertical"
              placeholder="输入想让这个声音读出来的文字"
            />
          </div>

          <div class="vc-actions vc-actions-row">
            <button class="vc-btn vc-btn-primary" :disabled="speaking || !selectedId || !speakText.trim()" @click="doSpeak">
              <span v-if="speaking" class="vc-spin" aria-hidden="true"></span>
              <span v-if="!speaking">生成语音</span>
              <span v-else>合成中…</span>
            </button>
            <button v-if="audioUrl" class="vc-btn vc-btn-ghost" @click="downloadAudio">
              下载 MP3
            </button>
          </div>

          <div v-if="audioUrl" class="vc-player">
            <div class="vc-player-badge">已生成</div>
            <audio :src="audioUrl" controls class="vc-audio"></audio>
          </div>
          <p v-if="speakErr" class="vc-err">{{ speakErr }}</p>
        </section>
      </div>

      <!-- ============ 右栏：我的音色 ============ -->
      <aside class="vc-side">
        <section class="vc-card">
          <header class="vc-card-head">
            <span class="vc-card-step vc-card-step--alt">3</span>
            <div>
              <h3 class="vc-card-title">我的音色</h3>
              <p class="vc-card-sub">点「用于合成」即可在左侧使用</p>
            </div>
          </header>

          <div v-if="!voices.length" class="vc-side-empty">
            <div class="vc-side-empty-icon" aria-hidden="true">🎙️</div>
            <p>还没有克隆过音色</p>
            <p class="vc-empty-sub">上传一段录音，几秒即可生成</p>
          </div>

          <ul v-else class="vc-voice-list">
            <li
              v-for="v in voices"
              :key="v.id"
              class="vc-voice-card"
              :class="{ active: selectedId === v.id }"
            >
              <div class="vc-voice-main">
                <span class="vc-voice-name">{{ v.name }}</span>
                <span class="vc-voice-meta" :class="{ expiring: v.hours_left < 24 }">
                  <span class="vc-dot" aria-hidden="true"></span>
                  {{ v.hours_left >= 168 ? '刚刚复刻' : `剩 ${v.hours_left} 小时` }}
                </span>
              </div>
              <div class="vc-voice-actions">
                <button class="vc-mini" type="button" @click="useVoice(v)">用于合成</button>
                <button class="vc-mini danger" type="button" @click="doDelete(v)">删除</button>
              </div>
            </li>
          </ul>
        </section>
      </aside>
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

const presetTexts = [
  '你好，很高兴见到你。',
  '今天天气真好，适合出门走走。',
  '愿你成为自己的太阳。',
]

function formatSize(b) {
  if (!b) return ''
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

function onFile(e) {
  const f = e.target.files?.[0]
  if (!f) return
  if (f.size > 20 * 1024 * 1024) {
    ElMessage.warning('样本音频不能超过 20MB')
    e.target.value = ''
    return
  }
  sampleFile.value = f
}

function clearFile() {
  sampleFile.value = null
  if (fileRef.value) fileRef.value.value = ''
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
    clearFile()
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
/* ============ 两栏布局 ============ */
.vc-tool {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 1fr);
  gap: 20px;
  align-items: start;
}
.vc-main { display: flex; flex-direction: column; gap: 20px; }
.vc-side { display: flex; flex-direction: column; gap: 20px; }
@media (max-width: 980px) {
  .vc-tool { grid-template-columns: 1fr; }
}

/* ============ 卡片：玻璃 + 主题感知 ============ */
.vc-card {
  position: relative;
  padding: 22px 22px 20px;
  border-radius: 18px;
  /* 玻璃底色：使用项目自带 --color-bg-glass（夜间极淡紫/白天 72% 白） */
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.06));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  box-shadow: var(--dp-shadow, 0 6px 24px rgba(0, 0, 0, 0.18));
  display: flex;
  flex-direction: column;
  gap: 16px;
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}
.vc-card-head {
  display: flex; align-items: center; gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--dp-line, rgba(127, 127, 127, 0.12));
}
/* 步骤徽章：鎏金→雨青渐变（两主题通用，文字色由主题感知决定） */
.vc-card-step {
  flex: none;
  width: 28px; height: 28px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  font-size: 13px; font-weight: 700;
  box-shadow: 0 2px 8px var(--yq-gold-glow, rgba(199, 169, 107, 0.3));
}
.vc-card-step--alt {
  background: linear-gradient(135deg, var(--yq-rain, #7fa8a3), var(--yq-gold, #c7a96b));
}
.vc-card-title { margin: 0; font-size: 16px; color: var(--lj-text); letter-spacing: .04em; font-weight: 600; }
.vc-card-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-3); letter-spacing: .04em; }

/* ============ 字段 ============ */
.vc-field { display: flex; flex-direction: column; gap: 8px; }
.vc-label {
  font-size: 12px;
  color: var(--lj-text-2);
  letter-spacing: .08em;
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
}
.vc-dim { font-style: normal; font-size: 11px; color: var(--lj-text-3); letter-spacing: .04em; }

/* ============ ElementPlus 控件：主题感知玻璃态 ============
   关键：使用 --color-bg-glass（昼夜已不同），禁用硬色覆盖
   夜间：透明深空；白天：浅米白玻璃，不再刺眼 */
.vc-card :deep(.el-input__wrapper),
.vc-card :deep(.el-textarea__inner) {
  background: var(--color-bg-glass) !important;
  box-shadow: 0 0 0 1px var(--dp-line) inset !important;
  border-radius: 10px !important;
  padding: 2px 12px !important;
}
.vc-card :deep(.el-input__wrapper.is-focus),
.vc-card :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px var(--yq-gold) inset, 0 0 0 3px var(--yq-gold-faint, rgba(199, 169, 107, 0.18)) !important;
}
.vc-card :deep(.el-input__inner),
.vc-card :deep(.el-textarea__inner) {
  color: var(--lj-text) !important;
  -webkit-text-fill-color: var(--lj-text);
}
.vc-card :deep(.el-input__inner::placeholder),
.vc-card :deep(.el-textarea__inner::placeholder) {
  color: var(--lj-text-3) !important;
  -webkit-text-fill-color: var(--lj-text-3);
}
.vc-card :deep(.el-textarea__inner) { padding: 10px 12px !important; }
.vc-card :deep(.el-select__wrapper) {
  background: var(--color-bg-glass) !important;
  box-shadow: 0 0 0 1px var(--dp-line) inset !important;
  border-radius: 10px !important;
}
.vc-card :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--yq-gold) inset, 0 0 0 3px var(--yq-gold-faint, rgba(199, 169, 107, 0.18)) !important;
}
.vc-card :deep(.el-select__placeholder),
.vc-card :deep(.el-select__selected-item) { color: var(--lj-text) !important; }
/* word-limit 计数颜色 */
.vc-card :deep(.el-input__count .el-input__count-inner),
.vc-card :deep(.el-textarea__count) { color: var(--lj-text-3) !important; background: transparent !important; }
.vc-select-full { width: 100%; }

/* ============ 上传区：玻璃底（昼夜不同） ============ */
.vc-drop {
  position: relative;
  border: 1.5px dashed var(--dp-line-strong, rgba(127, 127, 127, 0.32));
  border-radius: 14px;
  padding: 22px 16px;
  text-align: center;
  background: var(--yq-rain-faint, rgba(127, 168, 163, 0.04));
  cursor: pointer;
  transition: all .2s ease;
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  min-height: 96px;
}
.vc-drop:hover {
  border-color: var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.08));
}
.vc-drop.has {
  border-style: solid;
  border-color: var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.12));
  padding: 14px 16px;
}
.vc-drop-icon {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg,
    var(--yq-gold-faint, rgba(199, 169, 107, 0.22)),
    var(--yq-rain-faint, rgba(127, 168, 163, 0.22)));
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 18px;
  color: var(--yq-gold, #c7a96b);
}
.vc-drop-text { font-size: 14px; color: var(--lj-text); letter-spacing: .04em; }
.vc-drop-hint { font-size: 11px; color: var(--lj-text-3); letter-spacing: .06em; }

.vc-file-info {
  display: flex; align-items: center; gap: 12px; width: 100%;
}
.vc-file-icon {
  flex: none;
  width: 36px; height: 36px; border-radius: 10px;
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 18px;
}
.vc-file-meta { display: flex; flex-direction: column; align-items: flex-start; min-width: 0; flex: 1; }
.vc-file-name {
  font-size: 14px; color: var(--lj-text); max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.vc-file-size { font-size: 11px; color: var(--lj-text-3); letter-spacing: .04em; margin-top: 2px; }
.vc-file-remove {
  flex: none;
  width: 26px; height: 26px; border-radius: 50%;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.2));
  background: transparent;
  color: var(--lj-text-2);
  font-size: 14px; line-height: 1; cursor: pointer;
  transition: all .15s;
}
.vc-file-remove:hover {
  color: var(--dp-danger, #fb7185);
  border-color: var(--dp-danger, #fb7185);
  background: var(--dp-danger-faint, rgba(251, 113, 133, 0.08));
}

/* ============ 预设 chip ============ */
.vc-presets { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }
.vc-chip {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  background: transparent;
  color: var(--lj-text-2);
  font-size: 11px;
  cursor: pointer;
  transition: all .15s;
  letter-spacing: .04em;
}
.vc-chip:hover {
  color: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b);
}

/* ============ 按钮 ============ */
.vc-actions { position: relative; display: flex; gap: 10px; flex-wrap: wrap; }
.vc-actions-row { align-items: center; }
.vc-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  min-height: 40px;
  padding: 9px 22px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
  letter-spacing: .04em;
  transition: all .18s ease;
  font-family: inherit;
}
/* 主按钮：金绿渐变 + 主题感知字色与光晕 */
.vc-btn-primary {
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  font-weight: 600;
  box-shadow: 0 4px 14px var(--yq-gold-glow, rgba(199, 169, 107, 0.28));
}
.vc-btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px var(--yq-gold-glow-strong, rgba(199, 169, 107, 0.42));
}
.vc-btn-primary:active:not(:disabled) { transform: translateY(0); }
.vc-btn-primary:disabled {
  opacity: .45; cursor: not-allowed; box-shadow: none;
}
.vc-btn-ghost {
  background: transparent;
  color: var(--lj-text-2);
  border-color: var(--dp-line, rgba(127, 127, 127, 0.3));
}
.vc-btn-ghost:hover { color: var(--lj-text); border-color: var(--yq-gold, #c7a96b); }

.vc-spin {
  width: 14px; height: 14px;
  border: 2px solid var(--yq-gold-fg-faint, rgba(11, 15, 20, 0.3));
  border-top-color: var(--yq-gold-fg, #0b0f14);
  border-radius: 50%;
  animation: vc-rot .7s linear infinite;
}
@keyframes vc-rot { to { transform: rotate(360deg); } }

.vc-progress {
  position: absolute; left: 0; bottom: -4px; height: 2px;
  background: linear-gradient(90deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  border-radius: 2px;
  transition: width .2s ease;
  box-shadow: 0 0 8px var(--yq-gold-glow, rgba(199, 169, 107, 0.5));
}

.vc-notice { font-size: 11px; color: var(--lj-text-3); margin: -4px 0 0; line-height: 1.6; letter-spacing: .04em; }
.vc-err { font-size: 12px; color: var(--dp-danger, #fb7185); margin: 0; }

/* ============ 播放器 ============ */
.vc-player {
  position: relative;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--yq-rain-faint, rgba(127, 168, 163, 0.06));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
}
.vc-player-badge {
  position: absolute; top: -8px; left: 14px;
  padding: 2px 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  font-size: 10px;
  letter-spacing: .08em;
}
.vc-audio { width: 100%; }

/* ============ 右侧音色列表 ============ */
.vc-side-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 4px; padding: 28px 0;
  color: var(--lj-text-3);
  font-size: 13px;
  text-align: center;
}
.vc-side-empty-icon { font-size: 32px; opacity: .55; }
.vc-side-empty p { margin: 0; }
.vc-empty-sub { font-size: 11px; color: var(--lj-text-3); }

.vc-voice-list {
  margin: 0; padding: 0; list-style: none;
  display: flex; flex-direction: column; gap: 10px;
}
.vc-voice-card {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  background: var(--yq-rain-faint, rgba(127, 168, 163, 0.04));
  display: flex; flex-direction: column; gap: 8px;
  transition: all .15s;
}
.vc-voice-card.active {
  border-color: var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.1));
  box-shadow: 0 2px 10px var(--yq-gold-glow, rgba(199, 169, 107, 0.22));
}
.vc-voice-main {
  display: flex; justify-content: space-between; align-items: center;
  gap: 10px;
}
.vc-voice-name {
  font-size: 14px;
  color: var(--lj-text);
  font-weight: 500;
  letter-spacing: .04em;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
}
.vc-voice-meta {
  display: inline-flex; align-items: center; gap: 5px;
  flex: none;
  font-size: 11px;
  color: var(--lj-text-3);
  letter-spacing: .04em;
}
.vc-voice-meta .vc-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--yq-rain, #7fa8a3);
  box-shadow: 0 0 6px var(--yq-rain-glow, rgba(127, 168, 163, 0.6));
}
.vc-voice-meta.expiring { color: var(--dp-danger, #fb7185); }
.vc-voice-meta.expiring .vc-dot {
  background: var(--dp-danger, #fb7185);
  box-shadow: 0 0 6px var(--dp-danger-glow, rgba(251, 113, 133, 0.5));
}

.vc-voice-actions { display: flex; gap: 8px; }
.vc-mini {
  flex: 1;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.22));
  background: transparent;
  color: var(--lj-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
  font-family: inherit;
}
.vc-mini:hover {
  color: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.06));
}
.vc-mini.danger:hover {
  color: var(--dp-danger, #fb7185); border-color: var(--dp-danger, #fb7185);
  background: var(--dp-danger-faint, rgba(251, 113, 133, 0.06));
}

/* ============ Provider 未就绪 ============ */
.vc-empty { text-align: center; padding: 80px 0; color: var(--lj-text-2); }
.vc-empty-icon { font-size: 48px; margin-bottom: 14px; opacity: .6; }
.vc-empty p { margin: 6px 0; font-size: 14px; }

/* ============ 移动端微调 ============ */
@media (max-width: 600px) {
  .vc-card { padding: 18px 16px; border-radius: 16px; gap: 14px; }
  .vc-card-title { font-size: 15px; }
  .vc-btn { width: 100%; }
  .vc-voice-actions .vc-mini { padding: 8px 12px; }
}
</style>
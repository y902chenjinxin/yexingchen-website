<template>
  <IslandInnerBase type="tool" title="视频去水印" subtitle="粘贴分享链接或 B 站 BV 号，去除水印并下载">
    <div class="wt-stepper-wrap">
      <StepIndicator :steps="[
        { key: 'paste', label: '粘贴链接' },
        { key: 'parse', label: '解析素材' },
        { key: 'download', label: '下载保存' },
      ]" :current="result ? 'download' : (parsing ? 'parse' : 'paste')" />
    </div>
    <div class="parse-area">
      <div class="parse-head">
        <span class="parse-title"><AppIcon icon="🎬" :size="17" /> 视频去水印</span>
        <span class="parse-sub">支持抖音 / 快手 / 小红书 / B 站（b23.tv 短链、BV 号均可）等平台分享链接</span>
      </div>
      <div class="parse-input-row">
        <input
          v-model="link"
          class="parse-input"
          type="text"
          placeholder="粘贴视频分享链接或 B 站 BV 号，如 https://v.douyin.com/xxxx"
          @keyup.enter="doParse"
        />
        <button class="parse-btn" :disabled="parsing" @click="doParse">
          {{ parsing ? '解析中…' : '解析' }}
        </button>
      </div>

      <transition name="fade-drop">
        <div v-if="errorMsg" class="parse-error">{{ errorMsg }}</div>
      </transition>

      <transition name="fade-drop">
        <div v-if="result" class="parse-result">
          <div class="parse-meta">
            <span class="parse-name">{{ result.title || '（无标题）' }}</span>
            <span v-if="result.author && result.author.name" class="parse-author">@{{ result.author.name }}</span>
          </div>
          <video v-if="result.video_url" :src="result.video_url" controls playsinline class="parse-video" />
          <div v-else-if="result.images && result.images.length" class="parse-grid">
            <img v-for="(img, i) in result.images" :key="i" :src="img.url || img" class="parse-thumb" alt="图集图片" />
          </div>
          <div class="parse-actions">
            <a v-if="result.video_url" class="parse-dl" :href="result.video_url" target="_blank" rel="noopener noreferrer" @click.prevent="download($event, result.video_url)"><AppIcon icon="⬇" :size="14" /> 下载视频</a>
            <button class="parse-dl btn-dl" :disabled="audioing" @click="downloadAudio">
              <AppIcon v-if="!audioing" icon="🎵" :size="14" /> {{ audioing ? '抽取中…' : '下载音频' }}
            </button>
            <a v-if="result.cover_url" class="parse-dl" :href="result.cover_url" target="_blank" rel="noopener noreferrer" @click.prevent="download($event, result.cover_url)"><AppIcon icon="🖼" :size="14" /> 下载封面</a>
          </div>
          <div v-if="audioErr" class="audio-err">{{ audioErr }}</div>
          <div class="parse-note">请在权利允许范围内使用，仅供个人学习参考。预览为内联播放，不会跳转外部。</div>
        </div>
      </transition>
    </div>

    <!-- v2.46.343 上传音频 → 生成对得上的歌词 -->
    <div class="parse-area ly-area">
      <div class="parse-head">
        <span class="parse-title"><AppIcon icon="🎧" :size="17" /> 音频配歌词</span>
        <span class="parse-sub">
          上传你手上的音频，用语音识别<b>从这段音频本身</b>定时间轴 —— 网上抓的歌词是官方版，
          你的 DJ 版 / 翻唱版对不上
        </span>
      </div>

      <label
        class="ly-drop"
        :class="{ 'has-file': lyFile }"
        @dragover.prevent
        @drop.prevent="onLyDrop"
      >
        <input type="file" hidden accept="audio/*,video/*,.mp3,.wav,.flac,.m4a,.aac,.ogg" @change="onLyPick" />
        <template v-if="lyFile">
          <b>{{ lyFile.name }}</b>
          <span>{{ (lyFile.size / 1048576).toFixed(1) }} MB · 点这里换一个</span>
        </template>
        <template v-else>
          <b>点这里选音频，或把文件拖进来</b>
          <span>mp3 / wav / flac / m4a / aac / ogg，也能直接丢视频进去</span>
        </template>
      </label>

      <div class="ly-hint-row">
        <span class="ly-lab">歌词文本（可选）</span>
        <span class="ly-sub">
          贴了就以你的文本为准，识别只用来定时间；不贴就直接用识别结果（会有错别字，但时间是准的）
        </span>
      </div>
      <textarea
        v-model="lyText"
        class="ly-textarea"
        rows="5"
        placeholder="把歌词粘在这里（一行一句，带不带 [00:12.34] 时间都行）&#10;不填也能生成，只是会有识别错字"
      />

      <div class="parse-actions">
        <button class="parse-btn ly-go" :disabled="lyBusy || !lyFile" @click="doAlignUpload">
          {{ lyBusy ? `识别中… ${lyElapsed}s（一首约 20~60 秒）` : '生成歌词' }}
        </button>
        <button v-if="lyResult" class="parse-dl" type="button" @click="downloadLrc">
          <AppIcon icon="⬇" :size="14" /> 下载 .lrc
        </button>
      </div>

      <div v-if="lyErr" class="parse-error">{{ lyErr }}</div>

      <div v-if="lyResult" class="ly-result">
        <div class="ly-stat">
          共 <b>{{ lyStats.lines }}</b> 行 · 识别 {{ lyStats.segments }} 段 ·
          时长 {{ Math.round(lyStats.duration || 0) }}s ·
          <template v-if="lyStats.mode === 'asr-only'">纯识别（文本可能有错字）</template>
          <template v-else>按你的文本对齐</template>
        </div>
        <pre class="ly-preview">{{ lyPreview }}</pre>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { computed, ref } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import StepIndicator from '@/components/common/StepIndicator.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { parseVideoUrl, parseErrorMsg } from '@/api/videoParse'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const link = ref('')
const parsing = ref(false)
const errorMsg = ref('')
const result = ref(null)
const audioing = ref(false)
const audioErr = ref('')

/* ---------- 音频配歌词（v2.46.343）----------
 * 夜星：「有些资源是我在网上找的，不是原版」「现在歌词老是慢了一拍」。
 * 网上抓的 LRC 是官方版时间轴，他的音频是 DJ/翻唱版 —— 只能拿音频本身定时间。
 * 后端 services/lyric_align.py 做 SenseVoice 逐段识别 + 对齐，约 19x 实时。
 */
const lyFile = ref(null)
const lyText = ref('')
const lyBusy = ref(false)
const lyErr = ref('')
const lyResult = ref('')
const lyStats = ref({})
const lyElapsed = ref(0)
let lyTimer = 0

const lyPreview = computed(() => {
  const all = (lyResult.value || '').split('\n').filter(Boolean)
  return all.slice(0, 12).join('\n') + (all.length > 12 ? `\n… 共 ${all.length} 行` : '')
})

function onLyPick(e) {
  const f = e.target.files?.[0]
  if (f) { lyFile.value = f; lyResult.value = ''; lyErr.value = '' }
  e.target.value = ''
}
function onLyDrop(e) {
  const f = e.dataTransfer?.files?.[0]
  if (f) { lyFile.value = f; lyResult.value = ''; lyErr.value = '' }
}

async function doAlignUpload() {
  if (!lyFile.value || lyBusy.value) return
  lyBusy.value = true
  lyErr.value = ''
  lyResult.value = ''
  lyElapsed.value = 0
  lyTimer = setInterval(() => { lyElapsed.value += 1 }, 1000)
  try {
    const fd = new FormData()
    fd.append('file', lyFile.value)
    if (lyText.value.trim()) fd.append('lyrics', lyText.value.trim())
    const token = localStorage.getItem('token')
    const res = await axios.post('/api/music/lyric/align-upload', fd, {
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      timeout: 15 * 60 * 1000,
    })
    const d = res?.data?.data || {}
    if (!d.lyric) throw new Error('没生成出歌词')
    lyResult.value = d.lyric
    lyStats.value = d.stats || {}
    ElMessage.success(`生成 ${d.stats?.lines || 0} 行歌词`)
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '生成失败'
    lyErr.value = typeof msg === 'string' ? msg : '生成失败，检查音频格式'
  } finally {
    lyBusy.value = false
    clearInterval(lyTimer)
  }
}

function downloadLrc() {
  const name = (lyFile.value?.name || 'lyric').replace(/\.[^.]+$/, '')
  const blob = new Blob([lyResult.value], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${name}.lrc`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 4000)
}

async function doParse() {
  const url = (link.value || '').trim()
  if (!url) { errorMsg.value = '请先粘贴视频分享链接'; return }
  parsing.value = true
  errorMsg.value = ''
  result.value = null
  audioErr.value = ''
  try {
    const res = await parseVideoUrl(url)
    result.value = res.data || {}
  } catch (e) {
    errorMsg.value = parseErrorMsg(e)
  } finally {
    parsing.value = false
  }
}

function download(e, url) {
  e.preventDefault()
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

/** 文件名安全化：标题里常有 / : ? 这类不能做文件名的字符 */
function safeName(s) {
  return String(s || 'audio').replace(/[\\/:*?"<>|\n\r]/g, '_').trim().slice(0, 60) || 'audio'
}

/**
 * 顺手把同名歌词也下下来（v2.46.327）。
 * 夜星：「在下载音频的时候能自动下载歌词文件，在导入音乐模块时，能与歌曲对应位置匹配上」。
 * 做法：音频存成「歌名.mp3」、歌词存成「歌名.lrc」——导入音乐模块时同名自动配对，
 * LRC 里的时间轴原样保留，播放页就能按位置高亮。
 */
async function downloadLyricFile(title, artist) {
  try {
    const token = localStorage.getItem('token')
    const res = await axios.post('/api/music/lyric/lookup',
      { title, artist: artist || '' },
      { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    const d = res?.data?.data || res?.data || {}
    if (!d.found || !d.content) return false
    const blob = new Blob([d.content], { type: 'text/plain;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${safeName(title)}.lrc`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(a.href), 4000)
    return true
  } catch {
    return false
  }
}

async function downloadAudio() {
  const url = (link.value || '').trim()
  if (!url) { audioErr.value = '请先粘贴链接'; return }
  const title = result.value?.title || ''
  const artist = result.value?.author?.name || ''
  if (result.value?.music_url) {
    window.open(result.value.music_url, '_blank')
    // 直链模式下浏览器自己接管下载，我们只能补一份歌词
    if (await downloadLyricFile(title, artist)) audioErr.value = ''
    return
  }
  if (audioing.value) return
  audioing.value = true
  audioErr.value = ''
  try {
    const token = localStorage.getItem('token')
    const resp = await axios.post('/api/video_parse/audio', { url }, {
      responseType: 'blob',
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    const blob = new Blob([resp.data], { type: 'audio/mpeg' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    // 用歌名命名：导入音乐模块时「歌名.mp3 + 歌名.lrc」才能同名配对
    a.download = `${safeName(title)}.mp3`
    document.body.appendChild(a)
    a.click()
    a.remove()
    const gotLyric = await downloadLyricFile(title, artist)
    if (gotLyric) {
      ElMessage.success('音频和歌词都已下载，导入音乐模块会自动关联')
    } else {
      ElMessage.warning('音频已下载，但没找到这首歌的歌词（导入后可在音乐页手动补）')
    }
  } catch (e) {
    audioErr.value = e?.response?.data?.detail || '音频抽取失败，请重试'
  } finally {
    audioing.value = false
  }
}
</script>

<style scoped>
.wt-stepper-wrap {
  padding: 16px 18px 14px;
  margin-bottom: 16px;
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.04));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  border-radius: 14px;
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

.parse-area {
  background: var(--ls-glass);
  backdrop-filter: saturate(160%) blur(14px);
  -webkit-backdrop-filter: saturate(160%) blur(14px);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius);
  padding: 24px 28px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}

.parse-head { display: flex; align-items: baseline; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.parse-title { font-family: var(--font-serif); font-size: 17px; color: var(--ls-text); letter-spacing: 0.04em; }
.parse-sub { font-size: 12px; color: var(--ls-text-3); }

.parse-input-row { display: flex; gap: 12px; }
.parse-input {
  flex: 1;
  padding: 11px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--ls-line);
  /* v2.46.314：--ls-paper-1 全站从未定义且没写 fallback → 整条声明失效（输入框变透明）。
     归并到已定义的 --ls-paper-2（浮层/hover 底）。 */
  background: var(--ls-paper-2);
  color: var(--ls-text);
  font-size: 14px;
  outline: none;
  transition: border-color var(--transition);
}
.parse-input:focus { border-color: var(--ls-dai); }
.parse-input::placeholder { color: var(--ls-text-3); }

.parse-btn {
  flex: none;
  padding: 0 22px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--ls-dai);
  color: var(--ls-bg1);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition);
}
.parse-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(112, 192, 214, 0.4); }
.parse-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; box-shadow: none; }

.parse-error {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: rgba(200, 80, 60, 0.12);
  border: 1px solid rgba(200, 80, 60, 0.35);
  color: #e28a78;
  font-size: 13px;
}

.parse-result { margin-top: 18px; }
.parse-meta { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.parse-name { font-family: var(--font-serif); font-size: 15px; color: var(--ls-text); }
.parse-author { font-size: 12px; color: var(--ls-text-2); }

.parse-video {
  width: 100%;
  max-height: 320px;
  border-radius: var(--radius-sm);
  background: #000;
  outline: none;
}

.parse-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }
.parse-thumb { width: 100%; aspect-ratio: 3/4; object-fit: cover; border-radius: var(--radius-sm); }

.parse-actions { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.parse-dl {
  display: inline-block;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  background: var(--ls-paper-2);
  border: 1px solid var(--ls-line-strong);
  color: var(--ls-dai);
  font-size: 13px;
  text-decoration: none;
  transition: all var(--transition);
}
.parse-dl:hover { border-color: var(--ls-dai); transform: translateY(-1px); }
.btn-dl {
  cursor: pointer;
  line-height: 1.2;
}
.btn-dl:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.audio-err { margin-top: 10px; font-size: 12px; color: #e28a78; }
.parse-note { margin-top: 12px; font-size: 12px; color: var(--ls-text-3); }

/* ---------- 音频配歌词（v2.46.343） ---------- */
.ly-area { margin-top: 16px; }
.ly-drop {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  padding: 22px 16px; margin-bottom: 14px;
  border: 1px dashed var(--lj-line-strong, rgba(21, 48, 59, .26));
  border-radius: 12px; cursor: pointer; text-align: center;
  background: color-mix(in srgb, currentColor 3%, transparent);
  transition: border-color .16s, background-color .16s;
}
.ly-drop:hover { border-color: var(--lj-seal, #c7a96b); }
.ly-drop.has-file { border-style: solid; border-color: var(--lj-seal, #c7a96b); }
.ly-drop b { font-size: 14px; font-weight: 600; word-break: break-all; }
.ly-drop span { font-size: 12px; opacity: .62; }

.ly-hint-row { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.ly-lab { font-size: 12.5px; font-weight: 600; }
.ly-sub { font-size: 11.5px; opacity: .58; line-height: 1.5; flex: 1 1 240px; }
.ly-textarea {
  width: 100%; box-sizing: border-box; resize: vertical;
  padding: 10px 12px; margin-bottom: 12px;
  border-radius: 10px; font: inherit; font-size: 12.5px; line-height: 1.7;
  border: 1px solid var(--lj-line, rgba(21, 48, 59, .16));
  background: color-mix(in srgb, currentColor 3%, transparent);
  color: inherit;
}
.ly-textarea:focus { outline: none; border-color: var(--lj-seal, #c7a96b); }
.ly-go { min-width: 120px; }

.ly-result { margin-top: 12px; }
.ly-stat { font-size: 12px; opacity: .72; margin-bottom: 8px; }
.ly-stat b { color: var(--lj-seal, #c7a96b); }
.ly-preview {
  margin: 0; padding: 10px 12px; max-height: 220px; overflow: auto;
  border-radius: 10px; font-size: 12px; line-height: 1.75;
  background: color-mix(in srgb, currentColor 4%, transparent);
  border: 1px solid var(--lj-line, rgba(21, 48, 59, .12));
  white-space: pre-wrap; word-break: break-all;
}
</style>
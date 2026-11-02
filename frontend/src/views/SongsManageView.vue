<template>
  <IslandInnerBase type="tool" title="曲库" subtitle="MIDI 拖进来就能弹 · 曲谱只存你自己的账号">
    <div class="sm">
      <!-- 上传区 -->
      <div
        class="sm-drop glass"
        :class="{ over: dragging }"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
        @click="pick"
      >
        <input ref="fileEl" type="file" multiple accept=".mid,.midi,.json" hidden @change="onPick" />
        <b>把 .mid / .midi / .json 拖到这里</b>
        <span>会自动挑出主旋律、量化、映射到 28 个键；也可以点这里选文件</span>
        <em>批量转换也可以走本地脚本：scripts/midi2song.mjs（见下方说明）</em>
      </div>

      <!-- 待导入 -->
      <section v-if="queue.length" class="sm-queue">
        <header class="sm-sec-hd">
          <b>待导入 {{ queue.length }} 首</b>
          <button class="sm-btn ghost" type="button" @click="queue = []">清空</button>
          <button class="sm-btn primary" type="button" :disabled="importing" @click="importAll">
            {{ importing ? `导入中 ${doneCount}/${queue.length}` : '全部导入' }}
          </button>
        </header>
        <ul class="sm-list">
          <li v-for="(q, i) in queue" :key="q.uid" class="sm-item" :class="{ bad: !!q.error }">
            <input v-model="q.title" class="sm-title" maxlength="60" :disabled="!!q.error" />
            <span v-if="q.error" class="sm-err">{{ q.error }}</span>
            <span v-else class="sm-meta">
              <em>{{ q.bpm }} BPM</em><em>{{ q.notes.length }} 音</em>
              <em>{{ fmtDur(q.duration) }}</em><em>{{ q.source === 'midi' ? 'MIDI' : 'JSON' }}</em>
            </span>
            <button class="sm-x" type="button" aria-label="移除" @click="queue.splice(i, 1)">×</button>
          </li>
        </ul>
      </section>

      <!-- 已入库 -->
      <section class="sm-saved">
        <header class="sm-sec-hd">
          <b>我的曲库（{{ songs.length }}）</b>
          <button class="sm-btn ghost" type="button" @click="load">刷新</button>
        </header>
        <div v-if="loading" class="sm-empty">正在读取…</div>
        <div v-else-if="!songs.length" class="sm-empty">还没有曲子，先拖一个 MIDI 上来</div>
        <ul v-else class="sm-list">
          <li v-for="s in songs" :key="s.id" class="sm-item">
            <b class="sm-name">{{ s.title }}</b>
            <span class="sm-meta">
              <em v-if="s.artist">{{ s.artist }}</em>
              <em>{{ s.bpm }} BPM</em><em>{{ s.note_count }} 音</em>
              <em>{{ fmtDur(s.duration) }}</em><em class="dim">{{ s.created_at }}</em>
            </span>
            <button class="sm-btn xs" type="button" @click="$router.push(`/piano/${s.id}`)">演奏</button>
            <button class="sm-x" type="button" aria-label="删除" @click="remove(s)">×</button>
          </li>
        </ul>
      </section>

      <p class="sm-tip">
        本地批量转换：把 .mid 放到桌面某个文件夹，然后
        <code>node scripts/midi2song.mjs "文件夹路径"</code>
        （需先 <code>cd frontend && npx esbuild …</code>，脚本头部有完整命令），
        生成的一批 .json 再拖回这里即可。转换逻辑与网页里完全一致。
      </p>
    </div>
  </IslandInnerBase>
</template>

<script setup>
/**
 * 曲库管理（v2.46.334）
 *
 * 为什么解析放在前端：.mid 本身就有全部信息，服务端再解析一遍等于
 * 维护两套 MIDI 解析器。前端解析 → 规范化 → 只把最终 JSON 落库，
 * 和后端存储格式完全解耦（以后换 MIDI 库或换曲谱格式都只动前端）。
 */
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { buildSongFromMidi, validateSong } from '@/utils/song'
import { createSong, deleteSong, getSongs } from '@/api/songs'

const fileEl = ref(null)
const dragging = ref(false)
const queue = ref([])
const songs = ref([])
const loading = ref(false)
const importing = ref(false)
const doneCount = ref(0)
let uid = 0

const fmtDur = (sec) => {
  const s = Math.max(0, Math.round(sec || 0))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

function pick() { fileEl.value?.click() }

function onPick(e) {
  addFiles([...e.target.files])
  e.target.value = ''
}

function onDrop(e) {
  dragging.value = false
  addFiles([...e.dataTransfer.files])
}

async function addFiles(files) {
  const usable = files.filter((f) => /\.(mid|midi|json)$/i.test(f.name))
  if (!usable.length) {
    ElMessage.warning('只支持 .mid / .midi / .json')
    return
  }
  for (const f of usable) {
    const title = f.name.replace(/\.[^.]+$/, '')
    const row = { uid: ++uid, title, bpm: 0, notes: [], duration: 0, source: '', error: '' }
    try {
      if (/\.json$/i.test(f.name)) {
        const text = await f.text()
        const obj = JSON.parse(text)
        const bad = validateSong(obj)
        if (bad) throw new Error(bad)
        row.notes = obj.notes
        row.bpm = obj.bpm || 100
        row.title = (obj.songName || title).slice(0, 60)
        row.source = 'json'
      } else {
        const buf = await f.arrayBuffer()
        const song = buildSongFromMidi(buf, { name: title })
        row.notes = song.notes
        row.bpm = song.bpm
        row.source = 'midi'
      }
      row.duration = Math.max(...row.notes.map((n) => n.time + (n.dur || 0)))
    } catch (e) {
      row.error = e.message || '解析失败'
    }
    queue.value.push(row)
  }
}

async function importAll() {
  const valid = queue.value.filter((q) => !q.error)
  if (!valid.length) return
  importing.value = true
  doneCount.value = 0
  let ok = 0
  for (const q of valid) {
    try {
      await createSong({
        title: q.title || '未命名',
        artist: '',
        bpm: q.bpm,
        notes: q.notes,
        source: q.source,
      })
      ok++
      queue.value = queue.value.filter((x) => x.uid !== q.uid)
    } catch (e) {
      q.error = e?.response?.data?.msg || '保存失败'
    }
    doneCount.value++
  }
  importing.value = false
  ElMessage[ok ? 'success' : 'error'](ok ? `已导入 ${ok} 首` : '导入失败')
  if (ok) load()
}

async function load() {
  loading.value = true
  try {
    const res = await getSongs()
    songs.value = res?.data?.items || []
  } finally {
    loading.value = false
  }
}

async function remove(s) {
  try {
    await ElMessageBox.confirm(`删除「${s.title}」？`, '删除曲谱', { type: 'warning' })
  } catch {
    return
  }
  await deleteSong(s.id)
  load()
}

onMounted(load)
</script>

<style scoped>
.sm { max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px; padding-bottom: 24px; }
.sm-drop {
  display: flex; flex-direction: column; align-items: center; gap: 7px;
  padding: 34px 20px; border-radius: 16px; cursor: pointer; text-align: center;
  border: 1.5px dashed var(--glass-border, color-mix(in srgb, var(--ls-text) 20%, transparent));
  transition: border-color .18s ease, background-color .18s ease;
}
.sm-drop:hover, .sm-drop.over {
  border-color: var(--color-accent);
  background: color-mix(in srgb, var(--color-accent) 7%, transparent);
}
.sm-drop b { font-size: 15px; color: var(--ls-text); }
.sm-drop span { font-size: 12.5px; color: var(--ls-text-3); }
.sm-drop em { font-style: normal; font-size: 11.5px; color: var(--ls-text-3); opacity: .8; }

.sm-sec-hd { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.sm-sec-hd b { font-size: 13.5px; color: var(--ls-text); }
.sm-sec-hd .sm-btn { margin-left: auto; }
.sm-sec-hd .sm-btn + .sm-btn { margin-left: 0; }

.sm-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 7px; }
.sm-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 11px;
  border: 1px solid var(--glass-border, color-mix(in srgb, var(--ls-text) 14%, transparent));
  background: color-mix(in srgb, var(--ls-text) 4%, transparent);
}
.sm-item.bad { border-color: rgba(255, 120, 100, .5); }
.sm-title {
  flex: 1; min-width: 0; height: 30px; padding: 0 10px; border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--ls-text) 14%, transparent);
  background: transparent; color: var(--ls-text); font-size: 13.5px; outline: none;
}
.sm-title:focus { border-color: var(--color-accent); }
.sm-name { flex: 1; min-width: 0; font-size: 13.5px; color: var(--ls-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sm-meta { display: flex; gap: 9px; font-size: 11.5px; color: var(--ls-text-3); white-space: nowrap; }
.sm-meta em { font-style: normal; }
.sm-meta em.dim { opacity: .65; }
.sm-err { flex: 1; font-size: 12px; color: #e5735f; }
.sm-x {
  flex: none; width: 26px; height: 26px; border-radius: 7px; cursor: pointer;
  border: none; background: transparent; color: var(--ls-text-3); font-size: 16px; line-height: 1;
}
.sm-x:hover { background: color-mix(in srgb, var(--ls-text) 10%, transparent); color: var(--ls-text); }

.sm-btn {
  height: 32px; padding: 0 14px; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--glass-border, color-mix(in srgb, var(--ls-text) 16%, transparent));
  background: transparent; color: var(--ls-text); font-size: 12.5px; font-weight: 600;
}
.sm-btn:hover { background: color-mix(in srgb, var(--ls-text) 8%, transparent); }
.sm-btn.primary { border-color: transparent; background: var(--color-accent); color: #2c1d04; }
.sm-btn.xs { height: 26px; padding: 0 10px; font-size: 11.5px; }
.sm-btn:disabled { opacity: .5; cursor: default; }

.sm-empty {
  padding: 30px; text-align: center; font-size: 13px; color: var(--ls-text-3);
  border-radius: 12px; border: 1px dashed var(--glass-border, color-mix(in srgb, var(--ls-text) 14%, transparent));
}
.sm-tip { margin: 0; font-size: 11.5px; line-height: 1.9; color: var(--ls-text-3); }
.sm-tip code {
  padding: 1px 5px; border-radius: 4px; font-size: 11px;
  background: color-mix(in srgb, var(--ls-text) 10%, transparent);
}
</style>

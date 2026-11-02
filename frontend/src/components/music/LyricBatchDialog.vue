<template>
  <!-- 歌词总览：批量上传（同名自动关联）+ 批量在线抓取 + 未匹配手动指定（v2.46.327）
       夜星：「支持批量上传和单个上传，同名即可关联」「也可单个编辑，手动做关联」。 -->
  <el-dialog
    :model-value="modelValue"
    title="歌词管理"
    width="min(680px, calc(100vw - 28px))"
    append-to-body
    class="lyb-dlg"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div class="lyb">
      <!-- 概览 -->
      <div class="lyb-stats">
        <div class="lyb-stat">
          <b>{{ stats.total }}</b><span>曲目</span>
        </div>
        <div class="lyb-stat ok">
          <b>{{ stats.with_lyric }}</b><span>已有歌词</span>
        </div>
        <div class="lyb-stat warn">
          <b>{{ stats.missing }}</b><span>还没有</span>
        </div>
      </div>

      <!-- 两个批量动作 -->
      <div class="lyb-acts">
        <label class="lyb-btn lyb-btn--primary">
          <AppIcon icon="📄" :size="15" />批量上传歌词
          <input
            type="file" multiple hidden
            accept=".lrc,.txt,.krc,.srt,.ass"
            @change="onPickFiles"
          />
        </label>
        <button class="lyb-btn" type="button" :disabled="busy || !stats.missing" @click="onFetchAll">
          <AppIcon icon="✨" :size="15" />
          {{ busy ? fetchingLabel || '抓取中…' : `在线补全（还剩 ${stats.missing} 首）` }}
        </button>
        <button class="lyb-btn lyb-btn--align" type="button" :disabled="alignJob.running" @click="startAlign">
          <AppIcon icon="🎧" :size="15" />
          {{ alignJob.running ? '对齐中…' : '按音频重新对齐' }}
        </button>
        <span class="lyb-spacer"></span>
        <button class="lyb-btn" type="button" @click="reload">刷新</button>
      </div>

      <!-- v2.46.343 按音频重新对齐：网上抓的时间轴对不上 DJ/翻唱版，用识别重算 -->
      <p class="lyb-tip lyb-tip--align">
        在线补全拿的是<strong>官方版时间轴</strong>，你的音频如果是 DJ 版 / 翻唱版 / 钢琴版，
        歌词就会整体偏 0.2~1.5 秒、每句还各偏各的。「按音频重新对齐」会用语音识别
        找出<strong>每一句在这段音频里真正被唱出来的时刻</strong>，文本不动、只改时间。
      </p>

      <div v-if="alignJob.running || alignJob.done" class="lyb-progress lyb-progress--align">
        <div class="lyb-bar"><i :style="{ width: alignPercent + '%' }"></i></div>
        <span>
          {{ alignJob.done }} / {{ alignJob.total }} 首
          <template v-if="alignJob.running && alignJob.eta"> · 剩余约 {{ Math.ceil(alignJob.eta / 60) }} 分钟</template>
          <template v-if="!alignJob.running && alignJob.done"> · 已完成</template>
        </span>
        <button v-if="alignJob.running" class="lyb-mini" type="button" @click="stopAlignNow">停止</button>
      </div>
      <div v-if="alignJob.running && alignJob.current" class="lyb-current">正在处理：{{ alignJob.current }}</div>
      <div v-if="alignJob.last_error" class="lyb-err">{{ alignJob.last_error }}</div>

      <p class="lyb-tip">
        文件名与歌名相同即可自动关联（「晴天.lrc」「01 晴天 - 周杰伦.lrc」都认）。
        没匹配上的会列在下面，手动选一首歌就能挂上去。只支持 txt / lrc / krc / srt / ass。
      </p>

      <!-- 批量抓取进度条 -->
      <div v-if="busy" class="lyb-progress">
        <div class="lyb-bar"><i :style="{ width: fetchPercent + '%' }"></i></div>
        <span>{{ fetchedOk }} / {{ fetchedTotal }} 首已补</span>
      </div>

      <!-- 上传结果 -->
      <div v-if="results.length" class="lyb-results">
        <div class="lyb-res-head">
          <span>上传结果</span>
          <em>成功 {{ okCount }} / 共 {{ results.length }}</em>
        </div>
        <ul class="lyb-list">
          <li v-for="(r, i) in results" :key="i" class="lyb-item" :class="{ fail: !r.ok }">
            <span class="lyb-file">{{ r.file }}</span>
            <template v-if="r.ok">
              <span class="lyb-ok">→ {{ r.title }}</span>
              <span v-if="!r.has_timeline" class="lyb-nt">纯文本</span>
            </template>
            <template v-else>
              <span class="lyb-why">{{ r.reason }}</span>
              <template v-if="r.content">
                <select v-model="assign[i]" class="lyb-sel">
                  <option value="">选择歌曲…</option>
                  <option v-for="t in tracks" :key="t.id" :value="t.id">
                    {{ t.title }}{{ t.artist ? ` · ${t.artist}` : '' }}
                  </option>
                </select>
                <button class="lyb-mini" type="button" :disabled="!assign[i]" @click="assignTo(r, i)">关联</button>
              </template>
            </template>
          </li>
        </ul>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppIcon from '@/components/common/AppIcon.vue'
import {
  getLyricStats, fetchLyricMissing, uploadLyricFiles, saveLyric, getMusicList,
  alignAllLyrics, getAlignProgress, stopAlignLyrics,
} from '@/api/music'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'changed'])

const stats = ref({ total: 0, with_lyric: 0, missing: 0 })
const results = ref([])
const tracks = ref([])
const assign = reactive({})
const busy = ref(false)
const fetchingLabel = ref('')
const fetchedOk = ref(0)
const fetchedTotal = ref(0)

const okCount = computed(() => results.value.filter((r) => r.ok).length)

/* ---------- 按音频重新对齐（v2.46.343）---------- */
const alignJob = ref({ running: false, total: 0, done: 0, ok: 0, fail: 0, current: '', eta: 0, last_error: '' })
const alignPercent = computed(() =>
  alignJob.value.total ? Math.round((alignJob.value.done / alignJob.value.total) * 100) : 0
)
let alignTimer = 0

/**
 * @param {boolean} silent 打开弹窗时的「看一眼状态」不该弹提示
 *   （否则关掉页面再回来，每次都弹一句「对齐完成」）
 */
async function pollAlign(silent = false) {
  try {
    const res = await getAlignProgress()
    alignJob.value = res?.data || res || {}
    if (!alignJob.value.running) {
      clearInterval(alignTimer)
      alignTimer = 0
      if (!silent && alignJob.value.done) {
        ElMessage.success(`对齐完成：成功 ${alignJob.value.ok} 首${alignJob.value.fail ? `，失败 ${alignJob.value.fail} 首` : ''}`)
        reload()
        emit('changed')
      }
    }
  } catch { /* 轮询失败静默，下一轮再试 */ }
}

function ensurePoll() {
  if (!alignTimer) alignTimer = setInterval(() => pollAlign(), 3000)
}

async function startAlign() {
  const ok = await ElMessageBox.confirm(
    '会用语音识别逐首重新计算时间轴（文本不变）。整库约 1~2 小时，跑在服务器后台，可以关掉页面。如果音频不是原唱（纯音乐/伴奏），那首会保留原时间。',
    '按音频重新对齐',
    { confirmButtonText: '开始', cancelButtonText: '取消', type: 'info' },
  ).catch(() => false)
  if (!ok) return
  try {
    const res = await alignAllLyrics()
    const d = res?.data || res || {}
    if (d.running === false && d.done === 0 && res?.msg === '已经在跑了') {
      ElMessage.info('已经在跑了')
    } else {
      ElMessage.success('已开始，可以关掉这个页面')
    }
    await pollAlign()
    ensurePoll()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '启动失败')
  }
}

async function stopAlignNow() {
  try {
    await stopAlignLyrics()
    ElMessage.info('已请求停止，当前这首跑完就停')
  } catch { /* 忽略 */ }
}
const fetchPercent = computed(() =>
  fetchedTotal.value ? Math.round((fetchedOk.value / fetchedTotal.value) * 100) : 0
)

async function reload() {
  try {
    const res = await getLyricStats()
    stats.value = res?.data || res || stats.value
  } catch { /* 概览失败不挡事 */ }
}

async function loadTracks() {
  if (tracks.value.length) return
  try {
    const res = await getMusicList({ size: 0 })   // size=0 = 一次拉全（后端上限 1000）
    const list = res?.data?.list || res?.list || []
    tracks.value = list.map((m) => ({ id: m.id, title: m.title, artist: m.artist || '' }))
  } catch { /* 下拉失败就手动输入不了，但不影响批量 */ }
}

watch(() => props.modelValue, (v) => {
  if (v) {
    // 关掉页面再回来：先看一眼后台还在不在跑，在跑才开轮询
    pollAlign(true).then(() => { if (alignJob.value.running) ensurePoll() })
  }
  if (v) {
    results.value = []
    fetchedOk.value = 0
    fetchedTotal.value = 0
    reload()
    loadTracks()
  }
})

async function onPickFiles(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  busy.value = true
  fetchingLabel.value = '解析中…'
  try {
    const res = await uploadLyricFiles({ files })
    const d = res?.data || res || {}
    results.value = d.results || []
    Object.keys(assign).forEach((k) => delete assign[k])
    const ok = results.value.filter((r) => r.ok).length
    ElMessage.success(`已关联 ${ok} / ${results.value.length} 份歌词`)
    await reload()
    emit('changed')
  } catch (err) {
    ElMessage.error(err?.response?.data?.msg || '上传失败')
  } finally {
    busy.value = false
    fetchingLabel.value = ''
  }
}

async function assignTo(r, i) {
  const id = Number(assign[i])
  if (!id) return
  try {
    await saveLyric(id, r.content, 'upload')
    r.ok = true
    r.reason = ''
    delete assign[i]
    ElMessage.success('已关联')
    await reload()
    emit('changed')
  } catch {
    ElMessage.error('关联失败')
  }
}

/**
 * 批量在线抓取：后端一次只处理 20 首（单次要打 20 次外部接口，
 * 一次全跑前端请求会超时），这里循环调直到补完或连续两轮没有新增。
 */
async function onFetchAll() {
  if (busy.value) return
  busy.value = true
  fetchedOk.value = 0
  fetchedTotal.value = stats.value.missing
  let idle = 0
  try {
    for (let round = 0; round < 30; round++) {
      fetchingLabel.value = `第 ${round + 1} 轮 · 已补 ${fetchedOk.value} 首`
      const res = await fetchLyricMissing(20)
      const d = res?.data || res || {}
      const got = (d.ok || []).length
      fetchedOk.value += got
      emit('changed')
      if (!d.remaining || d.remaining <= 0) break
      if (got === 0) {
        idle += 1
        if (idle >= 2) break        // 连续两轮一首都没补上，剩下的基本没资源
      } else {
        idle = 0
      }
      fetchedTotal.value = fetchedOk.value + Number(d.remaining || 0)
    }
    ElMessage.success(`本次补全 ${fetchedOk.value} 首歌词`)
    await reload()
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || '批量抓取中断')
  } finally {
    busy.value = false
    fetchingLabel.value = ''
  }
}
</script>

<style scoped>
.lyb { display: flex; flex-direction: column; gap: 12px; }
.lyb-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.lyb-stat {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 12px 8px; border-radius: 12px;
  background: var(--tc-surface-2, rgba(120, 140, 160, .08));
}
.lyb-stat b { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
.lyb-stat span { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }
.lyb-stat.ok b { color: #0f7a56; }
.lyb-stat.warn b { color: #b4513f; }
.lyb-acts { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.lyb-spacer { flex: 1 1 auto; }
.lyb-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 34px; padding: 0 14px; border-radius: 10px; cursor: pointer;
  border: 1px solid var(--tc-line-strong, rgba(21, 48, 59, .2));
  background: transparent; color: var(--tc-text-2, #46586e);
  font: inherit; font-size: 12.5px; line-height: 1;
  transition: color .15s, border-color .15s, background-color .15s;
}
.lyb-btn:hover { color: var(--yq-rain, #0a708c); border-color: var(--yq-rain, #0a708c); }
.lyb-btn:disabled { opacity: .55; cursor: default; }
.lyb-btn--primary { background: var(--yq-rain, #0a708c); border-color: transparent; color: #fff; font-weight: 600; }
.lyb-btn--primary:hover { color: #fff; filter: brightness(1.05); }
.lyb-tip { margin: 0; font-size: 11.5px; line-height: 1.7; color: var(--tc-text-3, #5b6f8a); }
.lyb-progress { display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--tc-text-2, #46586e); }
.lyb-bar {
  flex: 1; height: 5px; border-radius: 999px; overflow: hidden;
  background: rgba(120, 140, 160, .18);
}
.lyb-bar i { display: block; height: 100%; border-radius: 999px; background: var(--yq-rain, #0a708c); transition: width .3s; }
.lyb-results { border-top: 1px solid var(--tc-line, rgba(21, 48, 59, .1)); padding-top: 10px; }
.lyb-res-head { display: flex; justify-content: space-between; font-size: 12.5px; margin-bottom: 6px; }
.lyb-res-head em { font-style: normal; color: var(--tc-text-3, #5b6f8a); }
.lyb-list { list-style: none; margin: 0; padding: 0; max-height: 220px; overflow-y: auto; }
.lyb-item {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 7px 2px; font-size: 12px;
  border-bottom: 1px dashed var(--tc-line, rgba(21, 48, 59, .1));
}
.lyb-file { font-family: ui-monospace, Consolas, Menlo, monospace; color: var(--tc-text-2, #46586e); }
.lyb-ok { color: #0f7a56; }
.lyb-nt { color: #ae7522; font-size: 11px; }
.lyb-why { color: #b4513f; }
.lyb-sel {
  height: 26px; max-width: 200px; border-radius: 7px; font-size: 12px;
  border: 1px solid var(--tc-line-strong, rgba(21, 48, 59, .2));
  background: transparent; color: inherit;
}
.lyb-mini {
  height: 26px; padding: 0 10px; border-radius: 7px; cursor: pointer; font-size: 12px;
  border: 1px solid var(--yq-rain, #0a708c); background: transparent; color: var(--yq-rain, #0a708c);
}
.lyb-mini:disabled { opacity: .45; cursor: default; }
.lyb-tip--align { margin-top: 6px; }
.lyb-btn--align { border-color: var(--lj-seal, #c7a96b); color: var(--lj-seal, #c7a96b); }
.lyb-btn--align:hover:not(:disabled) { background: color-mix(in srgb, var(--lj-seal, #c7a96b) 12%, transparent); }
.lyb-progress--align { margin-top: 8px; flex-wrap: wrap; }
.lyb-current { margin-top: 4px; font-size: 12px; opacity: .68; }
.lyb-err { margin-top: 4px; font-size: 12px; color: var(--lj-vermilion, #b4513f); }
</style>

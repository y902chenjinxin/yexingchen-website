<template>
  <!-- 单曲歌词：编辑 / 上传 / 在线抓取 / 清空（v2.46.327）
       夜星：「也可单个编辑，手动做关联」—— 所以这里最主要的是一块能直接改的文本框，
       其它按钮都只是往这块框里填内容的快捷方式。 -->
  <el-dialog
    :model-value="modelValue"
    :title="`歌词 · ${track?.title || ''}`"
    width="min(620px, calc(100vw - 28px))"
    append-to-body
    class="ly-dlg"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div class="ly-body">
      <div class="ly-meta">
        <span class="ly-artist">{{ track?.artist || '佚名' }}</span>
        <span v-if="source" class="ly-src">来源：{{ sourceLabel }}</span>
        <span v-if="content" class="ly-flag" :class="{ ok: hasTimeline }">
          {{ hasTimeline ? '带时间轴' : '纯文本（不跟随播放）' }}
        </span>
        <span v-else class="ly-flag">暂无歌词</span>
      </div>

      <el-input
        v-model="content"
        type="textarea"
        :rows="14"
        resize="vertical"
        class="ly-text"
        placeholder="粘贴 LRC 歌词，例如：[00:12.30]第一句歌词&#10;没有时间轴也可以保存，播放页会当作静态歌词展示"
      />

      <div class="ly-actions">
        <button class="ly-btn" type="button" :disabled="fetching" @click="onFetch">
          <AppIcon icon="🎵" :size="14" />{{ fetching ? '抓取中…' : '在线抓取' }}
        </button>
        <label class="ly-btn ly-btn--up">
          <AppIcon icon="📄" :size="14" />上传文件
          <input type="file" accept=".lrc,.txt,.krc,.srt,.ass" hidden @change="onPickFile" />
        </label>
        <span class="ly-spacer"></span>
        <button v-if="content" class="ly-btn ly-btn--danger" type="button" @click="onClear">清空</button>
        <button class="ly-btn ly-btn--primary" type="button" :disabled="saving" @click="onSave">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>

      <p class="ly-tip">
        在线抓取走「网易云 → 酷狗」，只接受带时间轴的结果；抓不到就自己粘一次，粘完存下来以后都在。
      </p>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/common/AppIcon.vue'
import { getLyric, saveLyric, deleteLyric, fetchLyric } from '@/api/music'
import { parseLrc } from '@/utils/lrc'

const props = defineProps({
  modelValue: Boolean,
  track: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const content = ref('')
const source = ref('')
const loading = ref(false)
const saving = ref(false)
const fetching = ref(false)

const hasTimeline = computed(() => parseLrc(content.value).length > 0)
const SOURCE_LABEL = {
  manual: '手动编辑',
  upload: '上传文件',
  netease: '网易云音乐',
  kugou: '酷狗音乐',
  import: '随音频导入',
}
const sourceLabel = computed(() => SOURCE_LABEL[source.value] || source.value || '未知')

async function load(id) {
  content.value = ''
  source.value = ''
  if (!id) return
  loading.value = true
  try {
    const res = await getLyric(id)
    const d = res?.data || res || {}
    content.value = d.content || ''
    source.value = d.source || ''
  } catch {
    /* 没歌词就是空 */
  } finally {
    loading.value = false
  }
}

watch(() => [props.modelValue, props.track?.id], ([open, id]) => {
  if (open) load(id)
}, { immediate: true })

async function onFetch() {
  if (!props.track?.id) return
  fetching.value = true
  try {
    const res = await fetchLyric(props.track.id)
    const d = res?.data || res || {}
    content.value = d.content || ''
    source.value = d.source || 'netease'
    ElMessage.success(`已从 ${sourceLabel.value} 获取${d.matched_title ? `：《${d.matched_title}》` : ''}`)
    emit('saved', props.track.id)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.msg || '没抓到带时间轴的歌词，可以手动粘贴或上传文件')
  } finally {
    fetching.value = false
  }
}

async function onPickFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  const text = await file.text()
  content.value = text
  source.value = 'upload'
  ElMessage.info('已读入文件，记得点保存')
}

async function onSave() {
  if (!props.track?.id) return
  saving.value = true
  try {
    await saveLyric(props.track.id, content.value, source.value || 'manual')
    ElMessage.success(content.value ? '歌词已保存' : '已清空歌词')
    emit('saved', props.track.id)
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onClear() {
  if (!props.track?.id) return
  content.value = ''
  source.value = ''
  try {
    await deleteLyric(props.track.id)
    ElMessage.success('已清空')
    emit('saved', props.track.id)
  } catch {
    ElMessage.error('清空失败')
  }
}
</script>

<style scoped>
.ly-body { display: flex; flex-direction: column; gap: 10px; }
.ly-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; font-size: 12.5px; }
.ly-artist { color: var(--tc-text-2, #46586e); }
.ly-src { color: var(--tc-text-3, #5b6f8a); }
.ly-flag {
  padding: 1px 8px; border-radius: 999px; font-size: 11.5px;
  background: rgba(120, 140, 160, .14); color: var(--tc-text-2, #46586e);
}
.ly-flag.ok { background: rgba(15, 122, 86, .14); color: #0f7a56; }
.ly-text :deep(textarea) { font-family: ui-monospace, Consolas, Menlo, monospace; font-size: 12.5px; line-height: 1.7; }
.ly-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ly-spacer { flex: 1 1 auto; }
.ly-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 32px; padding: 0 12px; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--tc-line-strong, rgba(21, 48, 59, .2));
  background: transparent; color: var(--tc-text-2, #46586e);
  font: inherit; font-size: 12.5px; line-height: 1;
  transition: color .15s, border-color .15s, background-color .15s;
}
.ly-btn:hover { color: var(--yq-rain, #0a708c); border-color: var(--yq-rain, #0a708c); }
.ly-btn:disabled { opacity: .55; cursor: default; }
.ly-btn--up { position: relative; }
.ly-btn--primary { background: var(--yq-rain, #0a708c); border-color: transparent; color: #fff; font-weight: 600; }
.ly-btn--primary:hover { color: #fff; filter: brightness(1.05); }
.ly-btn--danger { color: #b4513f; border-color: rgba(180, 81, 63, .38); }
.ly-btn--danger:hover { color: #fff; background: #b4513f; border-color: #b4513f; }
.ly-tip { margin: 0; font-size: 11.5px; line-height: 1.6; color: var(--tc-text-3, #5b6f8a); }
</style>

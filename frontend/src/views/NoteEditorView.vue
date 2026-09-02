<template>
  <div
    class="note-editor"
    :class="{ 'drop-active': dropActive }"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <header class="ne-header">
      <input
        v-model="title"
        class="ne-title-input"
        placeholder="标题"
        @input="scheduleSave"
      />
      <div class="ne-status">
        <span v-if="saveState === 'saving'" class="state saving">保存中…</span>
        <span v-else-if="saveState === 'saved'" class="state saved">已保存</span>
        <span v-else-if="saveState === 'error'" class="state error">保存失败：{{ saveError }}</span>
        <el-button
          v-if="noteId && status === 'draft'"
          type="primary"
          size="small"
          @click="markCompleted"
        >完成</el-button>
        <el-button
          v-if="noteId && status === 'completed'"
          size="small"
          @click="markDraft"
        >恢复为草稿</el-button>
        <el-button size="small" @click="remove" type="danger" plain>删除</el-button>
      </div>
    </header>

    <div class="ne-toolbar">
      <button type="button" title="标题" @click="exec('formatBlock', 'H2')">H</button>
      <button type="button" title="加粗" @click="exec('bold')"><b>B</b></button>
      <button type="button" title="斜体" @click="exec('italic')"><i>I</i></button>
      <button type="button" title="下划线" @click="exec('underline')"><u>U</u></button>
      <input type="color" title="文字颜色" @input="exec('foreColor', $event.target.value)" />
      <button type="button" @click="exec('insertUnorderedList')">• 列表</button>
      <button type="button" @click="exec('insertOrderedList')">1. 列表</button>
      <button type="button" @click="exec('formatBlock', 'BLOCKQUOTE')">引用</button>
      <button type="button" @click="exec('formatBlock', 'PRE')">代码块</button>
      <button type="button" @click="insertLink">链接</button>
      <label class="ne-upload-btn">
        图片
        <input type="file" accept="image/*" hidden @change="onImagePick" />
      </label>
      <label class="ne-upload-btn">
        PDF
        <input type="file" accept="application/pdf" hidden @change="onPdfPick" />
      </label>
      <button type="button" title="撤销" @click="exec('undo')">↶</button>
      <button type="button" title="重做" @click="exec('redo')">↷</button>
    </div>

    <div
      ref="editorEl"
      class="ne-content"
      contenteditable="true"
      spellcheck="false"
      @input="scheduleSave"
      @paste="onPaste"
      @click="onContentClick"
    ></div>

    <div v-if="assets.length" class="ne-assets">
      <h4>已附加（{{ assets.length }} / 共 {{ assetTotalSizeHuman }}）</h4>
      <ul>
        <li v-for="a in assets" :key="a.id">
          <span class="asset-thumb">
            <img v-if="a.type === 'image'" :src="a.previewUrl" :alt="a.title" @load="a.objectUrl && URL.revokeObjectURL(a.objectUrl)" />
            <span v-else-if="a.type === 'pdf'" class="pdf-chip"><el-icon class="inline-icon"><Document /></el-icon> {{ a.title }}</span>
            <span v-else><el-icon class="inline-icon"><Link /></el-icon> {{ a.title }}</span>
          </span>
          <span class="asset-title">{{ a.title }}</span>
          <span class="asset-size">{{ humanSize(a.file_size) }}</span>
          <button class="detach-btn" @click="detach(a.id)">解除</button>
        </li>
      </ul>
    </div>

    <div class="ne-tags">
      <h4>标签</h4>
      <div class="ne-tags-list">
        <el-tag v-for="t in tags" :key="t" closable @close="removeTag(t)">#{{ t }}</el-tag>
        <el-input
          v-model="tagDraft"
          size="small"
          style="width: 140px"
          @keyup.enter="addTag"
        />
        <el-button size="small" @click="addTag">添加</el-button>
      </div>
    </div>

    <div class="ne-ai">
      <h4>AI 操作（需用户确认）</h4>
      <el-button size="small" :disabled="!hasContent" @click="openAiPreview('summarize')">生成摘要</el-button>
      <el-button size="small" :disabled="!hasContent" @click="openAiPreview('organize')">整理笔记</el-button>
      <el-button size="small" :disabled="!hasContent" @click="openAiPreview('suggest_tags')">建议标签</el-button>
      <el-button size="small" :disabled="!hasContent" @click="openAiPreview('suggest_task')">生成任务草稿</el-button>
      <el-button size="small" :disabled="!hasContent" @click="linkToConversation">关联到对话</el-button>
    </div>

    <el-dialog v-model="aiDialog" title="AI 调用确认" width="600px" :close-on-click-modal="false">
      <p>将发送以下内容到 AI：</p>
      <pre class="ai-scope">{{ aiPreview }}</pre>
      <p v-if="aiSending" class="ai-status">正在调用 AI…</p>
      <div v-if="aiResult" class="ai-result-block">
        <h4>AI 返回结果（应用前需你确认）</h4>
        <pre class="ai-result">{{ aiResult }}</pre>
      </div>
      <template #footer>
        <el-button @click="cancelAi" :disabled="aiSending">取消</el-button>
        <el-button
          v-if="!aiResult"
          type="primary"
          :disabled="aiSending"
          @click="confirmAiInvoke"
        >确认发送</el-button>
        <el-button
          v-else
          type="primary"
          @click="applyAiResult"
        >已确认，写入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="linkDialog" title="选择 AI 对话" width="480px">
      <el-select v-model="linkConvId" placeholder="选择对话" filterable style="width:100%">
        <el-option
          v-for="c in conversations"
          :key="c.id"
          :label="c.title || '新对话'"
          :value="c.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="linkDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!linkConvId" @click="confirmLink">关联</el-button>
      </template>
    </el-dialog>

    <div v-if="dropActive" class="drop-overlay">松开以上传图片/PDF</div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'
import BackButton from '@/components/BackButton.vue'
import { classifyPaste, pickAcceptedFromDrop, summarizeIgnored } from '@/utils/paste-drop'
import { Document, Link } from '@element-plus/icons-vue'
import {
  hydrateNoteImages,
  imagePlaceholderHtml,
  pdfPlaceholderHtml,
  revokeAllNoteImages,
  sanitizeNoteHtml,
} from '@/utils/note-assets'

const route = useRoute()
const router = useRouter()

const noteId = ref(null)
const title = ref('')
const status = ref('draft')
const editorEl = ref(null)
const assets = ref([])
const tags = ref([])
const tagDraft = ref('')
const saveState = ref('idle')
const saveError = ref('')

// object URL 缓存：assetId -> objectUrl
const objectUrls = new Map()

// 自动保存：1.2s 防抖 + token 序号防 race
let saveTimer = null
let inflightToken = 0

// AI 流程：openAiPreview → confirmAiInvoke → aiResult → applyAiResult
const aiDialog = ref(false)
const aiAbility = ref('summarize')
const aiConversationId = ref(null)
const aiPreview = ref('')
const aiSending = ref(false)
const aiResult = ref('')
const aiResultPayload = ref({})

// 关联到对话
const linkDialog = ref(false)
const linkConvId = ref(null)
const conversations = ref([])

// 拖拽
const dropActive = ref(false)

// 图片/PDF 资源链接需要的鉴权 object URL（由 fetchBlob 创建）
async function refreshAssets() {
  if (!noteId.value) return
  try {
    const res = await workbenchApi.notes.listAssets(noteId.value)
    const list = (res.data && res.data.list) || []
    // 释放旧 object URL
    for (const a of assets.value) {
      if (a.objectUrl) URL.revokeObjectURL(a.objectUrl)
      objectUrls.delete(a.id)
    }
    // 为图片/PDF 生成鉴权 object URL
    const next = []
    for (const item of list) {
      let objectUrl = null
      if (item.type === 'image' || item.type === 'pdf') {
        try {
          const { objectUrl: url } = await workbenchApi.assets.fetchBlob(item.id, 'preview')
          objectUrl = url
          objectUrls.set(item.id, url)
        } catch (err) {
          ElMessage.warning('附件预览加载失败：' + item.title)
        }
      }
      next.push({ ...item, objectUrl, previewUrl: objectUrl })
    }
    assets.value = next
  } catch (e) {
    ElMessage.error('加载附件失败')
  }
}

const assetTotalSize = computed(() => assets.value.reduce((s, a) => s + (a.file_size || 0), 0))
function humanSize(n) {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let s = n
  for (const u of units) {
    if (s < 1024) return `${s.toFixed(1)} ${u}`
    s /= 1024
  }
  return `${s.toFixed(1)} TB`
}
const assetTotalSizeHuman = computed(() => humanSize(assetTotalSize.value))
const hasContent = computed(() => (title.value || '').trim() !== '' || (editorEl.value?.innerText || '').trim() !== '')

async function ensureNote() {
  if (noteId.value) return noteId.value
  const res = await workbenchApi.notes.create({ title: title.value || '未命名草稿', content: '', status: 'draft' })
  noteId.value = res.data.id
  status.value = res.data.status
  return noteId.value
}

async function loadNote() {
  const id = route.params.id
  if (id === 'new' || !id) {
    const res = await workbenchApi.notes.create({ title: '', content: '', status: 'draft' })
    noteId.value = res.data.id
    title.value = res.data.title || ''
    status.value = res.data.status
    router.replace(`/notes/${noteId.value}`)
    return
  }
  noteId.value = parseInt(id, 10)
  const res = await workbenchApi.notes.get(noteId.value)
  const d = res.data
  title.value = d.title || ''
  status.value = d.status || 'draft'
  if (editorEl.value) {
    // 服务端可能包含历史 blob:，先 sanitize 再注入
    editorEl.value.innerHTML = sanitizeNoteHtml(d.content || '')
    // 立即为所有 [data-asset-id] 图片通过 fetchBlob 注入 src
    await hydrateNoteImages(editorEl.value, workbenchApi.assets.fetchBlob)
  }
  tags.value = d.tags || []
  await refreshAssets()
}

async function doSave() {
  const token = ++inflightToken
  try {
    saveState.value = 'saving'
    await ensureNote()
    const rawHtml = editorEl.value ? editorEl.value.innerHTML : ''
    // 持久化：保存前清理任何残留 blob: 永久 URL，仅保留 [data-asset-id] 引用
    const cleanHtml = sanitizeNoteHtml(rawHtml)
    const res = await workbenchApi.notes.update(noteId.value, {
      title: title.value || '未命名草稿',
      content: cleanHtml,
      status: status.value,
    })
    if (token !== inflightToken) return
    status.value = res.data.status
    saveState.value = 'saved'
    setTimeout(() => { if (saveState.value === 'saved') saveState.value = 'idle' }, 1500)
  } catch (e) {
    if (token !== inflightToken) return
    saveState.value = 'error'
    saveError.value = e?.response?.data?.msg || e.message || '未知错误'
  }
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(doSave, 1200)
}

async function markCompleted() {
  status.value = 'completed'
  await doSave()
}
async function markDraft() {
  status.value = 'draft'
  await doSave()
}

async function remove() {
  if (!noteId.value) { router.push('/notes'); return }
  try {
    await ElMessageBox.confirm('确认删除？将进入回收站。', '提示', { type: 'warning' })
  } catch { return }
  await workbenchApi.notes.delete(noteId.value)
  router.push('/notes')
}

function exec(command, value = null) {
  document.execCommand(command, false, value)
  scheduleSave()
}

function insertLink() {
  const url = window.prompt('请输入链接 URL：')
  if (!url) return
  exec('createLink', url)
}

async function uploadFile(file) {
  if (!file) return null
  await ensureNote()
  const form = new FormData()
  form.append('file', file)
  form.append('title', file.name)
  try {
    const res = await workbenchApi.assets.upload(form)
    // 关联到当前笔记
    await workbenchApi.notes.attachAsset(noteId.value, res.data.id)
    return res.data
  } catch (e) {
    const msg = e?.response?.data?.msg || e.message
    ElMessage.error('上传失败：' + msg)
    return null
  }
}

async function onImagePick(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) return
  const asset = await uploadFile(f)
  if (!asset) return
  // 持久化：正文保存 data-asset-id 引用，不写 blob: 永久 URL。
  // 加载时由 hydrateNoteImages 通过 fetchBlob 重新生成 object URL。
  const ok = insertImageToEditor(asset)
  if (!ok) {
    ElMessage.error('插入图片失败：' + asset.title)
    return
  }
  scheduleSave()
  refreshAssets()
}

/** 把图片资产以 data-asset-id 占位插入正文，并立即渲染一次。 */
function insertImageToEditor(asset) {
  if (!editorEl.value) return false
  const html = imagePlaceholderHtml(asset.id, asset.title)
  exec('insertHTML', html)
  // 立即为刚插入的、未 hydrate 的图片注入 src，便于当前会话预览
  const candidates = Array.from(
    editorEl.value.querySelectorAll(`img[data-asset-id="${asset.id}"]`),
  ).filter((img) => img.dataset.hydrated !== '1')
  const lastImg = candidates[candidates.length - 1]
  if (lastImg) {
    // eslint-disable-next-line no-void
    void workbenchApi.assets
      .fetchBlob(asset.id, 'preview')
      .then(({ objectUrl }) => {
        lastImg.src = objectUrl
        lastImg.dataset.hydrated = '1'
      })
      .catch(() => { /* 保持占位，等待下次 hydrate */ })
  }
  return true
}

/** 把 PDF 资产以占位链接插入正文。 */
function insertPdfToEditor(asset) {
  if (!editorEl.value) return false
  const html = pdfPlaceholderHtml(asset.id, asset.title)
  exec('insertHTML', html)
  return true
}

async function onPdfPick(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) return
  const asset = await uploadFile(f)
  if (!asset) return
  if (!insertPdfToEditor(asset)) {
    ElMessage.error('插入 PDF 失败：' + asset.title)
    return
  }
  scheduleSave()
  refreshAssets()
}

// 粘贴：图片通过 clipboardData.items/files 上传 + 插入；文本按纯文本插入
async function onPaste(e) {
  e.preventDefault()
  const cd = e.clipboardData || window.clipboardData
  if (!cd) return

  const picked = classifyPaste(cd)
  if (picked.kind === 'image' && picked.file) {
    const asset = await uploadFile(picked.file)
    if (asset) {
      // 持久化：粘贴图片也写 data-asset-id，正文不带 blob: 永久 URL
      if (!insertImageToEditor(asset)) {
        ElMessage.error('粘贴图片失败：' + asset.title)
        return
      }
      scheduleSave()
      refreshAssets()
      return
    }
  }
  // 非图片粘贴：纯文本
  if (picked.text) document.execCommand('insertText', false, picked.text)
}

// 拖拽
function onDragOver() {
  dropActive.value = true
}
function onDragLeave(e) {
  // 仅在真正离开容器时关闭
  if (!e.currentTarget.contains(e.relatedTarget)) {
    dropActive.value = false
  }
}
async function onDrop(e) {
  dropActive.value = false
  const all = e.dataTransfer?.files
  const accepted = pickAcceptedFromDrop(e.dataTransfer || {})
  if (!accepted.length) {
    const summary = summarizeIgnored(all)
    if (summary) ElMessage.warning('仅支持图片或 PDF，已忽略：' + summary)
    return
  }
  for (const f of accepted) {
    const asset = await uploadFile(f)
    if (!asset) continue  // 上传失败已 toast
    if (f.type && f.type.startsWith('image/')) {
      insertImageToEditor(asset)
    } else if (f.type === 'application/pdf') {
      insertPdfToEditor(asset)
    }
    refreshAssets()
  }
  scheduleSave()
}

// 编辑区内点击占位 PDF 链接 → 走 fetchBlob 触发浏览器下载（避免裸 URL 缺鉴权）
async function onContentClick(e) {
  const a = e.target?.closest?.('a.xuanhuang-asset-link')
  if (!a) return
  e.preventDefault()
  const id = a.getAttribute('data-asset-id')
  const title = a.getAttribute('data-asset-title') || 'asset.pdf'
  if (!id) return
  try {
    const { blob } = await workbenchApi.assets.fetchBlob(id, 'download')
    const url = URL.createObjectURL(blob)
    const tmp = document.createElement('a')
    tmp.href = url
    tmp.download = title
    document.body.appendChild(tmp)
    tmp.click()
    document.body.removeChild(tmp)
    // 给浏览器一点时间触发下载再 revoke
    setTimeout(() => URL.revokeObjectURL(url), 5000)
  } catch (err) {
    ElMessage.error('下载失败：' + (err?.message || err))
  }
}

// 标签
async function addTag() {
  const name = (tagDraft.value || '').trim()
  if (!name || tags.value.includes(name)) { tagDraft.value = ''; return }
  await ensureNote()
  const next = [...tags.value, name]
  const res = await workbenchApi.notes.setTags(noteId.value, next)
  tags.value = res.data.tags || []
  tagDraft.value = ''
}
async function removeTag(t) {
  const next = tags.value.filter(x => x !== t)
  const res = await workbenchApi.notes.setTags(noteId.value, next)
  tags.value = res.data.tags || []
}

// 解除附件（真实调用后端）
async function detach(aid) {
  if (!noteId.value) return
  await workbenchApi.notes.detachAsset(noteId.value, aid)
  // 释放 object URL
  if (objectUrls.has(aid)) {
    URL.revokeObjectURL(objectUrls.get(aid))
    objectUrls.delete(aid)
  }
  assets.value = assets.value.filter(a => a.id !== aid)
  ElMessage.success('已解除附件')
}

// AI 流程：严格 preview → 用户确认 → invoke → 用户确认应用
async function openAiPreview(ability) {
  if (!hasContent.value) {
    ElMessage.warning('无内容可发送给 AI')
    return
  }
  await ensureNote()
  // 默认关联到当前用户最近一个对话；如无则创建
  if (!aiConversationId.value) {
    const listRes = await workbenchApi.ai.conversations()
    const list = (listRes.data && listRes.data.list) || []
    if (list.length) aiConversationId.value = list[0].id
    else {
      const created = await workbenchApi.ai.createConversation({ title: title.value || '新对话' })
      aiConversationId.value = created.data.id
    }
  }
  aiAbility.value = ability
  aiResult.value = ''
  aiResultPayload.value = {}
  aiSending.value = false
  try {
    const res = await workbenchApi.ai.preview({ ability, note_id: noteId.value })
    aiPreview.value = res.data.preview + (res.data.has_more ? '…' : '')
    aiDialog.value = true
  } catch (e) {
    ElMessage.error('预览失败：' + (e?.response?.data?.msg || e.message))
  }
}

async function confirmAiInvoke() {
  aiSending.value = true
  try {
    const res = await workbenchApi.ai.invoke({
      ability: aiAbility.value,
      note_id: noteId.value,
      conversation_id: aiConversationId.value,
    })
    aiResult.value = res.data.text + '\n\n' + JSON.stringify(res.data.data || {}, null, 2)
    aiResultPayload.value = res.data.data || {}
  } catch (e) {
    ElMessage.error('调用失败：' + (e?.response?.data?.msg || e.message))
    cancelAi()
  } finally {
    aiSending.value = false
  }
}

async function applyAiResult() {
  if (!aiResultPayload.value || !Object.keys(aiResultPayload.value).length) {
    ElMessage.warning('无结果可应用')
    return
  }
  let targetType = 'note'
  if (aiAbility.value === 'suggest_task') {
    targetType = 'task'
  }
  try {
    const res = await workbenchApi.ai.apply({
      ability: aiAbility.value,
      target_type: targetType,
      target_id: noteId.value,  // suggest_task 时后端忽略 target_id（创建任务）
      conversation_id: aiConversationId.value,
      payload: aiResultPayload.value,
    })
    if (targetType === 'task') {
      // 后端创建任务并返回 task.id / task 结构
      const newTask = (res && res.data && res.data.task) || {}
      if (newTask.id) {
        ElMessage.success(`任务已创建：${newTask.title || ''}（#${newTask.id}）`)
      } else {
        ElMessage.success('任务已创建，请到 /tasks 确认')
      }
    } else {
      ElMessage.success('已应用到笔记')
      // 整理结果可能改写 title/content，重新拉取并 sanitize + hydrate
      const refreshed = await workbenchApi.notes.get(noteId.value)
      title.value = refreshed.data.title || ''
      if (editorEl.value) {
        editorEl.value.innerHTML = sanitizeNoteHtml(refreshed.data.content || '')
        await hydrateNoteImages(editorEl.value, workbenchApi.assets.fetchBlob)
      }
      tags.value = refreshed.data.tags || []
    }
    aiDialog.value = false
  } catch (e) {
    ElMessage.error('应用失败：' + (e?.response?.data?.msg || e.message))
  }
}

function cancelAi() {
  aiDialog.value = false
  aiResult.value = ''
  aiResultPayload.value = {}
  aiPreview.value = ''
}

// 关联到对话
async function linkToConversation() {
  await ensureNote()
  // 加载对话列表
  const listRes = await workbenchApi.ai.conversations()
  conversations.value = (listRes.data && listRes.data.list) || []
  linkConvId.value = aiConversationId.value
  linkDialog.value = true
}

async function confirmLink() {
  if (!linkConvId.value || !noteId.value) return
  try {
    await workbenchApi.ai.link(linkConvId.value, { target_type: 'note', target_id: noteId.value })
    ElMessage.success('已关联到对话')
    aiConversationId.value = linkConvId.value
    linkDialog.value = false
  } catch (e) {
    ElMessage.error('关联失败：' + (e?.response?.data?.msg || e.message))
  }
}

onBeforeUnmount(() => {
  if (saveTimer) clearTimeout(saveTimer)
  // 释放正文里 hydrate 出来的 object URL
  revokeAllNoteImages(editorEl.value)
  // 释放附件缩略图 object URL
  for (const url of objectUrls.values()) URL.revokeObjectURL(url)
  objectUrls.clear()
})

onMounted(loadNote)
watch(() => route.params.id, loadNote)
</script>

<style scoped>
.note-editor { max-width: 880px; margin: 0 auto; padding: 24px 16px 80px; position: relative; font-family: var(--font-serif); color: var(--xiu-text); }
.ne-header { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.ne-title-input { flex: 1; min-width: 200px; font-size: 26px; padding: 6px 8px; border: 0; border-bottom: 1px solid var(--xiu-line); background: transparent; outline: none; color: var(--xiu-text); letter-spacing: .06em; }
.ne-title-input::placeholder { color: var(--xiu-text-3); }
.ne-status { display: flex; gap: 8px; align-items: center; }
.state { font-size: 12px; }
.state.saving { color: var(--xiu-primary-bright); }
.state.saved { color: var(--xiu-primary); }
.state.error { color: var(--xiu-danger); }
.ne-toolbar { display: flex; flex-wrap: wrap; gap: 4px; padding: 6px; background: var(--xiu-card-strong); border: 1px solid var(--xiu-line); border-radius: 10px; margin-bottom: 8px; backdrop-filter: blur(12px); }
.ne-toolbar button, .ne-toolbar input { padding: 4px 8px; background: rgba(255,255,255,.04); border: 1px solid var(--xiu-line); border-radius: 6px; cursor: pointer; font-size: 13px; color: var(--xiu-text-2); transition: var(--transition); }
.ne-toolbar button:hover { color: var(--xiu-gold-bright); border-color: rgba(201, 169, 110, .4); background: rgba(201, 169, 110, .1); }
.ne-toolbar input[type=color] { padding: 0; width: 28px; height: 28px; }
.ne-upload-btn { padding: 4px 8px; background: rgba(255,255,255,.04); border: 1px solid var(--xiu-line); border-radius: 6px; cursor: pointer; font-size: 13px; color: var(--xiu-text-2); transition: var(--transition); }
.ne-upload-btn:hover { color: var(--xiu-gold-bright); border-color: rgba(201, 169, 110, .4); background: rgba(201, 169, 110, .1); }
.ne-content { min-height: 320px; padding: 14px; border: 1px solid var(--xiu-line); border-radius: 10px; outline: none; line-height: 1.7; background: var(--xiu-card); color: var(--xiu-text); word-break: break-word; backdrop-filter: blur(10px); }
.ne-content :deep(a) { color: var(--xiu-primary-bright); }
.ne-content :deep(img) { max-width: 100%; height: auto; }
.ne-assets, .ne-tags, .ne-ai { margin-top: 16px; padding: 12px; background: var(--xiu-card); border: 1px solid var(--xiu-line); border-radius: 10px; backdrop-filter: blur(10px); }
.ne-assets h4, .ne-tags h4, .ne-ai h4 { margin: 0 0 8px; font-size: 14px; color: var(--xiu-gold); letter-spacing: .08em; }
.ne-assets ul { list-style: none; margin: 0; padding: 0; }
.ne-assets li { display: flex; gap: 8px; align-items: center; padding: 6px 0; border-top: 1px dashed rgba(201, 169, 110, .15); }
.ne-assets li:first-child { border-top: 0; }
.asset-thumb img { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; border: 1px solid var(--xiu-line); }
.pdf-chip { display: inline-block; padding: 4px 8px; background: rgba(61, 184, 176, .12); border: 1px solid rgba(61, 184, 176, .2); border-radius: 6px; font-size: 12px; color: var(--xiu-text-2); }
.asset-title { flex: 1; font-size: 13px; word-break: break-word; color: var(--xiu-text); }
.asset-size { font-size: 11px; color: var(--xiu-text-3); }
.detach-btn { padding: 2px 8px; background: transparent; border: 1px solid var(--xiu-line); color: var(--xiu-text-2); cursor: pointer; border-radius: 6px; font-size: 12px; transition: var(--transition); }
.detach-btn:hover { color: var(--xiu-danger); border-color: rgba(224, 138, 122, .4); }
.ne-tags-list { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.ne-ai .el-button { margin-right: 6px; margin-bottom: 6px; }
.ai-scope { background: rgba(0,0,0,.2); border: 1px solid var(--xiu-line); padding: 8px; border-radius: 8px; font-size: 12px; max-height: 160px; overflow: auto; white-space: pre-wrap; word-break: break-word; color: var(--xiu-text-2); }
.ai-status { color: var(--xiu-primary-bright); font-size: 13px; margin-top: 8px; }
.ai-result-block { margin-top: 12px; }
.ai-result { background: rgba(61, 184, 176, .08); border: 1px solid rgba(61, 184, 176, .15); padding: 8px; border-radius: 8px; font-size: 12px; max-height: 200px; overflow: auto; white-space: pre-wrap; word-break: break-word; color: var(--xiu-text); }
.drop-active { outline: 2px dashed var(--xiu-primary); outline-offset: -8px; }
.drop-overlay { position: fixed; inset: 0; background: rgba(61, 184, 176, .15); display: flex; align-items: center; justify-content: center; color: var(--xiu-primary-bright); font-size: 20px; z-index: 1000; pointer-events: none; }
@media (max-width: 600px) {
  .ne-toolbar { gap: 2px; }
  .ne-toolbar button, .ne-toolbar input { font-size: 12px; padding: 3px 6px; }
}
</style>

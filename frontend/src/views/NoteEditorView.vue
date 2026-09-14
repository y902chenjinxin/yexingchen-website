<template>
  <div
    class="note-editor"
    :class="{ 'drop-active': dropActive }"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <NoteEditorHeader
      v-model:title="title"
      :status="status"
      :save-state="saveState"
      :save-error="saveError"
      :has-note="!!noteId"
      @voice="onVoiceTitle"
      @save="scheduleSave"
      @complete="markCompleted"
      @revert="markDraft"
      @delete="remove"
    />

    <NoteEditorToolbar
      :palette-colors="paletteColors"
      @exec="exec"
      @insert-link="insertLink"
      @pick-image="onImagePick"
      @pick-pdf="onPdfPick"
      @pick-color="pickColor"
    />

    <NoteEditorContent
      @editor-ready="onEditorReady"
      @update="scheduleSave"
      @paste="onPaste"
      @content-click="onContentClick"
    />

    <NoteAttachmentPanel
      :assets="assets"
      :total-size-text="assetTotalSizeHuman"
      @detach="detach"
    />

    <NoteTagPicker
      v-model:draft="tagDraft"
      :tags="tags"
      @add="addTag"
      @remove="removeTag"
    />

    <NoteAiActions
      :disabled="!hasContent"
      :ai-dialog="aiDialog"
      :ai-ability="aiAbility"
      :ai-preview="aiPreview"
      :ai-sending="aiSending"
      :ai-result="aiResult"
      :ai-has-result="!!aiResult"
      :link-dialog="linkDialog"
      :link-conv-id="linkConvId"
      :conversations="conversations"
      @preview="openAiPreview"
      @confirm="confirmAiInvoke"
      @apply="applyAiResult"
      @cancel="cancelAi"
      @link-open="linkToConversation"
      @link-update="linkConvId = $event"
      @link-confirm="confirmLink"
      @link-close="linkDialog = false"
    />

    <div v-if="dropActive" class="drop-overlay">松开以上传图片/PDF</div>
  </div>
</template>

<script setup>
/**
 * 玄黄工作台 · 笔记编辑器（容器组件）。
 *
 * - 持有编辑器 DOM ref、当前选区、保存状态、AI 状态等共享数据；
 * - 暴露 exec / saveSelection / restoreSelection / ensureNote 等核心能力；
 * - 通过 provide 供子组件（工具栏、内容、颜色面板、附件、标签、AI）使用；
 * - 子组件通过 emit 把"上传图片 / 删除附件 / 调起 AI"等用户操作回传到容器统一处理。
 */
import { computed, onBeforeUnmount, onMounted, provide, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'
import {
  hydrateNoteImages,
  imagePlaceholderHtml,
  pdfPlaceholderHtml,
  revokeAllNoteImages,
  sanitizeNoteHtml,
} from '@/utils/note-assets'
import {
  classifyPaste,
  pickAcceptedFromDrop,
  summarizeIgnored,
} from '@/utils/paste-drop'
import NoteEditorHeader from './notes-editor/NoteEditorHeader.vue'
import NoteEditorToolbar from './notes-editor/NoteEditorToolbar.vue'
import NoteEditorContent from './notes-editor/NoteEditorContent.vue'
import NoteAttachmentPanel from './notes-editor/NoteAttachmentPanel.vue'
import NoteTagPicker from './notes-editor/NoteTagPicker.vue'
import NoteAiActions from './notes-editor/NoteAiActions.vue'

const route = useRoute()
const router = useRouter()

// ---------- 共享状态 ----------
const noteId = ref(null)
const title = ref('')
const status = ref('draft')
const editorEl = ref(null)
const assets = ref([])
const tags = ref([])
const tagDraft = ref('')
const saveState = ref('idle') // idle | saving | saved | error
const saveError = ref('')

const objectUrls = new Map()
let saveTimer = null
let inflightToken = 0

// AI 对话状态
const aiDialog = ref(false)
const aiAbility = ref('summarize')
const aiConversationId = ref(null)
const aiPreview = ref('')
const aiSending = ref(false)
const aiResult = ref('')
const aiResultPayload = ref({})

// 关联对话状态
const linkDialog = ref(false)
const linkConvId = ref(null)
const conversations = ref([])

// 拖拽
const dropActive = ref(false)

// ---------- 调色板（28 色修仙主题色） ----------
const paletteColors = [
  '#ffffff', '#e8e8e8', '#c0c0c0', '#888888',
  '#000000', '#ff0000', '#ff6b35', '#ffb300',
  '#f2e37f', '#8bc34a', '#00b894', '#00bcd4',
  '#4a90d9', '#7b68ee', '#9c27b0', '#e91e63',
  // 修仙主题加成色
  '#5ce0d8', '#3db8b0', '#c9a96e', '#d4af37',
  '#e08a7a', '#b06ab3', '#e5d5b8', '#5b7fb0',
]

// ---------- 计算属性 ----------
const assetTotalSize = computed(() => assets.value.reduce((s, a) => s + (a.file_size || 0), 0))
const assetTotalSizeHuman = computed(() => humanSize(assetTotalSize.value))
const hasContent = computed(
  () => (title.value || '').trim() !== '' || (editorEl.value?.innerText || '').trim() !== '',
)

function humanSize(n) {
  if (!n || n < 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`
}

// ---------- 选区记忆 ----------
let savedRange = null

function saveSelection(container) {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return null
  const range = sel.getRangeAt(0)
  if (container.contains(range.commonAncestorContainer)) return range.cloneRange()
  return null
}

function restoreSelection() {
  if (!savedRange || !editorEl.value) return false
  editorEl.value.focus()
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(savedRange)
  return true
}

/** 工具栏 mousedown：仅对格式化按钮阻止默认（防失焦），放行 color/file 控件 */
function onToolbarMousedown(e) {
  const t = e.target
  if (!t || t.tagName === 'INPUT' || t.tagName === 'LABEL') return
  e.preventDefault()
  if (editorEl.value) {
    savedRange = saveSelection(editorEl.value)
  }
}

/** 返回编辑器当前实时选区；若选区为空/不在编辑器内则返回 null */
function liveSelection(container) {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return null
  const range = sel.getRangeAt(0)
  if (range.collapsed) return null
  if (container.contains(range.commonAncestorContainer)) return range.cloneRange()
  return null
}

function exec(command, value = null) {
  if (editorEl.value) {
    const live = liveSelection(editorEl.value)
    if (live) {
      const sel = window.getSelection()
      sel.removeAllRanges()
      sel.addRange(live)
    } else {
      restoreSelection()
    }
  }
  document.execCommand(command, false, value)
  scheduleSave()
}

function insertLink() {
  const url = window.prompt('请输入链接 URL：')
  if (!url) return
  exec('createLink', url)
}

// ---------- 数据加载 / 保存 ----------
async function refreshAssets() {
  if (!noteId.value) return
  const res = await workbenchApi.notes.listAssets(noteId.value)
  const list = (res.data && res.data.list) || []
  // 释放旧的 object URL
  for (const a of list) {
    if (objectUrls.has(a.id)) {
      URL.revokeObjectURL(objectUrls.get(a.id))
      objectUrls.delete(a.id)
    }
  }
  // 为新条目申请 object URL（图片预览）
  const next = []
  for (const a of list) {
    if (a.type === 'image') {
      try {
        const { objectUrl } = await workbenchApi.assets.fetchBlob(a.id, 'preview')
        objectUrls.set(a.id, objectUrl)
        next.push({ ...a, previewUrl: objectUrl })
        continue
      } catch {
        // 失败时不带预览
      }
    }
    next.push(a)
  }
  assets.value = next
}

async function ensureNote() {
  if (noteId.value) return noteId.value
  if (!editorEl.value) return null
  const res = await workbenchApi.notes.create({
    title: title.value || '未命名草稿',
    content: '',
    status: 'draft',
  })
  noteId.value = res.data.id
  title.value = res.data.title || ''
  status.value = res.data.status
  router.replace(`/notes/${noteId.value}`)
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
  let d
  try {
    const res = await workbenchApi.notes.get(noteId.value)
    d = res.data
  } catch (e) {
    noteId.value = null
    title.value = ''
    status.value = 'draft'
    router.replace('/notes')
    ElMessage.warning('笔记不存在或已删除，已返回列表')
    return
  }
  title.value = d.title || ''
  status.value = d.status || 'draft'
  if (editorEl.value) {
    editorEl.value.innerHTML = sanitizeNoteHtml(d.content || '')
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

function onVoiceTitle(text) {
  title.value = title.value.trim() ? `${title.value.trim()} ${text}` : text
  scheduleSave()
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
  if (!noteId.value) { router.replace('/notes'); return }
  try {
    await ElMessageBox.confirm('确认删除该笔记？删除后进入回收站，可在回收站中恢复。', '删除确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    })
  } catch { return }
  await workbenchApi.notes.delete(noteId.value)
  ElMessage.success('已删除')
  router.replace('/notes')
}

// ---------- 文件上传 / 粘贴 / 拖拽 ----------
async function uploadFile(file) {
  if (!file) return null
  await ensureNote()
  const form = new FormData()
  form.append('file', file)
  form.append('title', file.name)
  try {
    const res = await workbenchApi.assets.upload(form)
    await workbenchApi.notes.attachAsset(noteId.value, res.data.id)
    return res.data
  } catch (e) {
    const msg = e?.response?.data?.msg || e.message
    ElMessage.error('上传失败：' + msg)
    return null
  }
}

function insertImageToEditor(asset) {
  if (!editorEl.value) return false
  const html = imagePlaceholderHtml(asset.id, asset.title)
  exec('insertHTML', html)
  const candidates = Array.from(
    editorEl.value.querySelectorAll(`img[data-asset-id="${asset.id}"]`),
  ).filter((img) => img.dataset.hydrated !== '1')
  const lastImg = candidates[candidates.length - 1]
  if (lastImg) {
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

function insertPdfToEditor(asset) {
  if (!editorEl.value) return false
  const html = pdfPlaceholderHtml(asset.id, asset.title)
  exec('insertHTML', html)
  return true
}

async function onImagePick(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) return
  const asset = await uploadFile(f)
  if (!asset) return
  if (!insertImageToEditor(asset)) {
    ElMessage.error('插入图片失败：' + asset.title)
    return
  }
  scheduleSave()
  refreshAssets()
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

async function onPaste(e) {
  e.preventDefault()
  const cd = e.clipboardData || window.clipboardData
  if (!cd) return

  const picked = classifyPaste(cd)
  if (picked.kind === 'image' && picked.file) {
    const asset = await uploadFile(picked.file)
    if (asset) {
      if (!insertImageToEditor(asset)) {
        ElMessage.error('粘贴图片失败：' + asset.title)
        return
      }
      scheduleSave()
      refreshAssets()
      return
    }
  }
  if (picked.text) document.execCommand('insertText', false, picked.text)
}

function onDragOver() { dropActive.value = true }
function onDragLeave(e) {
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
    if (!asset) continue
    if (f.type && f.type.startsWith('image/')) insertImageToEditor(asset)
    else if (f.type === 'application/pdf') insertPdfToEditor(asset)
    refreshAssets()
  }
  scheduleSave()
}

async function onContentClick(e) {
  if (editorEl.value) savedRange = saveSelection(editorEl.value)
  const a = e.target?.closest?.('a.xuanhuang-asset-link')
  if (!a) return
  e.preventDefault()
  const id = a.getAttribute('data-asset-id')
  const titleAttr = a.getAttribute('data-asset-title') || 'asset.pdf'
  if (!id) return
  try {
    const { blob } = await workbenchApi.assets.fetchBlob(id, 'download')
    const url = URL.createObjectURL(blob)
    const tmp = document.createElement('a')
    tmp.href = url
    tmp.download = titleAttr
    document.body.appendChild(tmp)
    tmp.click()
    document.body.removeChild(tmp)
    setTimeout(() => URL.revokeObjectURL(url), 5000)
  } catch (err) {
    ElMessage.error('下载失败：' + (err?.message || err))
  }
}

function onEditorReady(el) {
  editorEl.value = el
}

// ---------- 标签 ----------
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

// ---------- 附件解除 ----------
async function detach(aid) {
  if (!noteId.value) return
  await workbenchApi.notes.detachAsset(noteId.value, aid)
  if (objectUrls.has(aid)) {
    URL.revokeObjectURL(objectUrls.get(aid))
    objectUrls.delete(aid)
  }
  assets.value = assets.value.filter(a => a.id !== aid)
  ElMessage.success('已解除附件')
}

// ---------- AI 流程 ----------
async function openAiPreview(ability) {
  if (!hasContent.value) {
    ElMessage.warning('无内容可发送给 AI')
    return
  }
  await ensureNote()
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
    aiResult.value = res.data.text || '（AI 未返回可展示的文本）'
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
  const targetType = aiAbility.value === 'suggest_task' ? 'task' : 'note'
  try {
    const res = await workbenchApi.ai.apply({
      ability: aiAbility.value,
      target_type: targetType,
      target_id: noteId.value,
      conversation_id: aiConversationId.value,
      payload: aiResultPayload.value,
    })
    if (targetType === 'task') {
      const newTask = (res && res.data && res.data.task) || {}
      if (newTask.id) {
        ElMessage.success(`任务已创建：${newTask.title || ''}（#${newTask.id}）`)
      } else {
        ElMessage.success('任务已创建，请到 /tasks 确认')
      }
    } else {
      ElMessage.success('已应用到笔记')
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

async function linkToConversation() {
  await ensureNote()
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

// ---------- 颜色面板：吸色器 ----------
let pipetteCleanup = null

function rgbToHex(r, g, b) {
  const h = (n) => n.toString(16).padStart(2, '0')
  return `#${h(r)}${h(g)}${h(b)}`
}

function cssColorToHex(cssColor) {
  if (!cssColor) return null
  const s = cssColor.trim()
  if (s.startsWith('#')) return s.length === 7 ? s.toLowerCase() : null
  try {
    const probe = document.createElement('canvas')
    probe.width = probe.height = 1
    const ctx = probe.getContext('2d')
    if (ctx) {
      ctx.fillStyle = s
      ctx.fillRect(0, 0, 1, 1)
      const d = ctx.getImageData(0, 0, 1, 1).data
      return rgbToHex(d[0], d[1], d[2])
    }
  } catch { /* ignore */ }
  return null
}

function isOpaqueColor(c) {
  if (!c) return false
  if (c === 'rgba(0, 0, 0, 0)' || c === 'transparent') return false
  const m = c.match(/rgba?\(([^)]*)\)/)
  if (m && m[1].split(',').length >= 4 && /0(?:\.0+)?$/.test(m[1].split(',')[3].trim())) return false
  return true
}

function pixelFromImage(img, clientX, clientY) {
  try {
    const r = img.getBoundingClientRect()
    if (!r.width || !r.height) return null
    if (clientX < r.left || clientX > r.right || clientY < r.top || clientY > r.bottom) return null
    const w = img.naturalWidth || 0
    const h = img.naturalHeight || 0
    if (!w || !h) return null
    const c = document.createElement('canvas')
    c.width = w
    c.height = h
    const ctx = c.getContext('2d')
    ctx.drawImage(img, 0, 0, w, h)
    const px = Math.max(0, Math.min(w - 1, Math.round(((clientX - r.left) / r.width) * w)))
    const py = Math.max(0, Math.min(h - 1, Math.round(((clientY - r.top) / r.height) * h)))
    const d = ctx.getImageData(px, py, 1, 1).data
    return rgbToHex(d[0], d[1], d[2])
  } catch {
    return null
  }
}

function colorAt(clientX, clientY) {
  const PICKER_CLS = 'sol-page-picker'
  const all = document.elementsFromPoint(clientX, clientY) || []
  const els = all.filter((el) => !el.classList || !el.classList.contains(PICKER_CLS))
  for (const el of els) {
    if (el.tagName === 'IMG') {
      const c = pixelFromImage(el, clientX, clientY)
      if (c) return c
    }
  }
  for (const el of els) {
    const bg = getComputedStyle(el).backgroundColor
    if (isOpaqueColor(bg)) {
      const c = cssColorToHex(bg)
      if (c) return c
    }
  }
  for (const el of els) {
    const c = cssColorToHex(getComputedStyle(el).color)
    if (c) return c
  }
  return '#ffffff'
}

function startPagePipette() {
  const PICKER_CLS = 'sol-page-picker'
  if (pipetteCleanup) pipetteCleanup()

  const overlay = document.createElement('div')
  overlay.className = PICKER_CLS
  overlay.style.cssText =
    'position:fixed;inset:0;z-index:2147483000;cursor:none;background:transparent;'

  const pip = document.createElement('div')
  pip.className = PICKER_CLS + '-pip'
  pip.innerHTML =
    '<svg width="40" height="40" viewBox="0 0 1024 1024" ' +
    'style="filter:drop-shadow(0 0 1.5px rgba(255,255,255,.95)) drop-shadow(0 0 5px rgba(255,255,255,.35));">' +
    '<path d="M988.16 92.16L926.72 30.72c-40.96-40.96-102.4-40.96-143.36 0l-143.36 143.36L573.44 102.4 440.32 240.64l56.32 56.32-389.12 394.24c-25.6 25.6-40.96 61.44-40.96 92.16l-20.48 20.48c-46.08 51.2-46.08 128 0 179.2 20.48 25.6 51.2 40.96 81.92 40.96s66.56-15.36 87.04-35.84l20.48-20.48c35.84 0 66.56-15.36 92.16-40.96l389.12-394.24 56.32 56.32 138.24-138.24-66.56-71.68 143.36-143.36c40.96-40.96 40.96-102.4 0-143.36m-716.8 768c-10.24 10.24-25.6 15.36-35.84 15.36-10.24 0-15.36 0-25.6-5.12L153.6 921.6c-5.12 5.12-15.36 10.24-25.6 10.24s-20.48-5.12-25.6-10.24c-15.36-15.36-15.36-35.84 0-51.2l56.32-51.2c-10.24-20.48-5.12-46.08 10.24-61.44l389.12-394.24 102.4 102.4-389.12 394.24z m0 0" fill="#2c2c2c"/>' +
    '</svg>'
  pip.style.cssText =
    'position:absolute;left:0;top:0;pointer-events:none;transform:translate(-26px,-18px);will-change:left,top;'

  const chip = document.createElement('div')
  chip.style.cssText =
    'position:absolute;left:0;top:0;pointer-events:none;width:22px;height:22px;border-radius:5px;' +
    'border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.4);transform:translate(26px,2px);will-change:left,top;'
  const hexLabel = document.createElement('div')
  hexLabel.style.cssText =
    'position:absolute;left:0;top:0;pointer-events:none;white-space:nowrap;background:rgba(0,0,0,.68);' +
    'color:#fff;font:12px Consolas,monospace;letter-spacing:.02em;padding:2px 8px;border-radius:6px;' +
    'transform:translate(24px,30px);will-change:left,top;'

  const hint = document.createElement('div')
  hint.textContent = '移动针管取色，点击处即取该处颜色 · Esc / 右键取消'
  hint.style.cssText =
    'position:fixed;left:50%;top:14px;transform:translateX(-50%);white-space:nowrap;' +
    'background:rgba(0,0,0,.62);color:#fff;font-size:13px;padding:6px 14px;border-radius:20px;'

  overlay.append(pip, chip, hexLabel, hint)
  document.body.appendChild(overlay)

  let curX = window.innerWidth / 2
  let curY = window.innerHeight / 2
  let currentColor = '#ffffff'

  const paint = () => {
    pip.style.left = `${curX}px`
    pip.style.top = `${curY}px`
    chip.style.left = `${curX}px`
    chip.style.top = `${curY}px`
    chip.style.backgroundColor = currentColor
    hexLabel.style.left = `${curX}px`
    hexLabel.style.top = `${curY}px`
    hexLabel.textContent = currentColor
  }

  const onMove = (e) => {
    curX = e.clientX
    curY = e.clientY
    currentColor = colorAt(curX, curY)
    paint()
  }
  const onDown = (e) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.stopPropagation()
    const color = colorAt(e.clientX, e.clientY)
    cleanup()
    exec('foreColor', color)
  }
  const onKey = (e) => { if (e.key === 'Escape') cleanup() }
  const onCtx = (e) => { e.preventDefault(); cleanup() }
  const cleanup = () => {
    if (!pipetteCleanup) return
    document.removeEventListener('mousemove', onMove)
    overlay.removeEventListener('mousedown', onDown)
    document.removeEventListener('keydown', onKey)
    overlay.removeEventListener('contextmenu', onCtx)
    overlay.remove()
    pipetteCleanup = null
  }
  pipetteCleanup = cleanup

  document.addEventListener('mousemove', onMove)
  overlay.addEventListener('mousedown', onDown)
  document.addEventListener('keydown', onKey)
  overlay.addEventListener('contextmenu', onCtx)
  paint()
}

function pickColor() { startPagePipette() }

// ---------- 生命周期 ----------
onMounted(async () => {
  await loadNote()
  document.addEventListener('keydown', onDocKeydown)
})

onBeforeUnmount(() => {
  if (saveTimer) clearTimeout(saveTimer)
  if (pipetteCleanup) pipetteCleanup()
  revokeAllNoteImages(editorEl.value)
  for (const url of objectUrls.values()) URL.revokeObjectURL(url)
  objectUrls.clear()
  document.removeEventListener('keydown', onDocKeydown)
})

function onDocKeydown(e) {
  if (e.key === 'Escape') {
    if (pipetteCleanup) { pipetteCleanup(); return }
  }
  // 简单 ctrl+s 触发保存
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    scheduleSave()
  }
}

// ---------- 给子组件的 provide ----------
// 子组件（工具栏、内容）需要 editorEl 引用；
// 工具栏还需要 exec / saveSelection 用于按钮；
// 由于 Vue 3 setup 内 provide 是同步的，子组件在 onEditorReady 触发之前不会使用 editorEl，因此注入一个 ref 即可。
provide('editorContext', {
  get editorEl() { return editorEl.value },
  exec,
  saveSelection,
  restoreSelection,
  onToolbarMousedown,
})
</script>

<style scoped>
.ne-ai { margin-top: 16px; padding: 12px; background: var(--xiu-card); border: 1px solid var(--xiu-line); border-radius: 10px; backdrop-filter: blur(10px); }
.ne-ai h4 { margin: 0 0 8px; font-size: 14px; color: var(--xiu-gold); letter-spacing: .08em; }
.ne-ai .el-button { margin-right: 6px; margin-bottom: 6px; }
.drop-active { outline: 2px dashed var(--xiu-primary); outline-offset: -8px; }
.drop-overlay { position: fixed; inset: 0; background: rgba(61, 184, 176, .15); display: flex; align-items: center; justify-content: center; color: var(--xiu-primary-bright); font-size: 20px; z-index: 1000; pointer-events: none; }
</style>

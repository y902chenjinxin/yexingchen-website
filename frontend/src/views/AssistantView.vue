<template>
  <div class="assistant-page">
    <header class="assistant-header">
      <h1>AI 助手</h1>
      <div>
        <el-button @click="showCreate = true">新建对话</el-button>
      </div>
    </header>

    <div class="assistant-body">
      <aside class="assistant-sidebar">
        <h3>对话列表</h3>
        <ul>
          <li
            v-for="c in conversations"
            :key="c.id"
            :class="{ active: c.id === activeId }"
            @click="open(c.id)"
          >
            <span>{{ c.title || '新对话' }}</span>
            <button class="del-btn" @click.stop="del(c.id)">×</button>
          </li>
          <li v-if="!conversations.length" class="empty">还没有对话</li>
        </ul>
      </aside>

      <main class="assistant-main">
        <template v-if="activeId">
          <div class="messages">
            <div v-for="m in messages" :key="m.id" :class="['msg', m.role]">
              <div class="msg-role">{{ roleLabel(m.role) }}</div>
              <pre class="msg-content">{{ m.content }}</pre>
              <details v-if="m.input_scope" class="msg-scope">
                <summary>查看发送范围</summary>
                <pre>{{ m.input_scope }}</pre>
              </details>
              <div v-if="m.provider" class="msg-meta">
                provider: {{ m.provider }} {{ m.is_fake ? '(fake/离线)' : '(真实)' }}
              </div>
            </div>
            <div v-if="!messages.length" class="empty">开始新对话吧</div>
          </div>
          <div class="composer">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="3"
              placeholder="输入要发送给 AI 的内容（不含密钥）"
            />
            <div class="composer-actions">
              <el-button type="primary" :disabled="!draft.trim() || sending" @click="openPreview">
                发送
              </el-button>
            </div>
          </div>
        </template>
        <p v-else class="placeholder">在左侧选择或新建一个对话。</p>
      </main>
    </div>

    <!-- 发送预览确认（preview → 用户确认 → invoke） -->
    <el-dialog v-model="previewDialog" title="发送确认" width="560px" :close-on-click-modal="false">
      <p>将发送以下内容到 AI（已脱敏）：</p>
      <pre class="ai-scope">{{ previewText }}</pre>
      <p v-if="previewMeta" class="ai-meta">
        字符数：{{ previewMeta.char_count || '—' }}{{ previewMeta.has_more ? '（已截断）' : '' }}
      </p>
      <p v-if="invoking" class="ai-status">正在调用 AI…</p>
      <template #footer>
        <el-button @click="cancelPreview" :disabled="invoking">取消</el-button>
        <el-button type="primary" :disabled="invoking" @click="confirmInvoke">确认发送</el-button>
      </template>
    </el-dialog>

    <!-- 调用结果确认（invoke 结果 → 用户确认后 apply） -->
    <el-dialog
      v-model="resultDialog"
      title="AI 调用结果"
      width="640px"
      :close-on-click-modal="false"
    >
      <div v-if="lastInvoke" class="ai-result-meta">
        <span>能力：{{ lastInvoke.ability }}</span>
        <span>provider：{{ lastInvoke.provider }} {{ lastInvoke.is_fake ? '(fake/离线)' : '(真实)' }}</span>
      </div>
      <h4>文本回复</h4>
      <pre class="ai-result">{{ lastInvoke ? lastInvoke.text : '' }}</pre>
      <details v-if="lastInvoke && lastInvoke.data" class="ai-result-data">
        <summary>查看结构化结果（用于 apply）</summary>
        <pre>{{ JSON.stringify(lastInvoke.data, null, 2) }}</pre>
      </details>
      <p class="ai-apply-note">
        {{ applyHint }}
      </p>

      <!-- 目标笔记选择器（对 note 类能力需要选择/新建笔记作为 apply 目标） -->
      <div v-if="lastInvoke && lastInvoke.ability !== 'suggest_task'" class="apply-target">
        <h4>应用到笔记</h4>
        <div class="apply-target-row">
          <NoteSelect
            v-model="applyTargetNoteId"
            :items="applyTargetNotes"
            :loading="notesLoading"
            :has-more="applyTargetNotes.length < applyTargetTotal"
            placeholder="输入关键词搜索笔记，或从下拉中选择"
            empty-text="暂无笔记可选，点右侧「新建草稿」"
            style="flex: 1; min-width: 240px"
            @search="searchApplyTargetNotes"
            @load-more="onApplyTargetPageChange"
          />
          <el-button @click="loadApplyTargetNotes({ reset: true })" :disabled="notesLoading">刷新</el-button>
          <el-button type="primary" plain @click="createApplyTargetNote" :disabled="notesLoading">新建草稿</el-button>
        </div>
        <p class="apply-target-tip">
          {{ applyTargetMetaText }}
        </p>
        <p v-if="applyTargetError" class="ai-apply-error">{{ applyTargetError }}</p>
      </div>

      <template #footer>
        <el-button @click="discardResult">丢弃</el-button>
        <el-button
          v-if="canApply(lastInvoke)"
          type="primary"
          :disabled="applying || !canConfirmApply"
          @click="confirmApply"
        >{{ applyButtonLabel }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreate" title="新建对话" width="420px">
      <el-input v-model="newTitle" placeholder="对话标题（可选）" />
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'
import NoteSelect from '@/components/common/NoteSelect.vue'

const conversations = ref([])
const activeId = ref(null)
const messages = ref([])
const draft = ref('')
const showCreate = ref(false)
const newTitle = ref('')

// AI 流程状态
const previewDialog = ref(false)
const previewText = ref('')
const previewMeta = ref(null)
const sending = ref(false)
const pendingAbility = ref('summarize')

const invoking = ref(false)
const lastInvoke = ref(null)  // { ability, text, data, provider, is_fake, conversation_id, ... }
const resultDialog = ref(false)
const applying = ref(false)

// 目标笔记选择器（apply 到 note 时使用）
// - applyTargetNotes：当前可见的候选笔记（受 page/size + keyword 影响）
// - applyTargetTotal：后端返回的总数，用于判断是否还有下一页
// - applyTargetKeyword：搜索关键词
// - applyTargetPage / applyTargetSize：分页状态
// - loadApplyTargetNotes({reset}) 既支持"刷新"（重置）也支持"加载更多"（追加）
const applyTargetNotes = ref([])
const applyTargetNoteId = ref(null)
const applyTargetTotal = ref(0)
const applyTargetKeyword = ref('')
const applyTargetPage = ref(1)
const applyTargetSize = ref(20)
const notesLoading = ref(false)
const applyTargetError = ref('')
let applyTargetSeq = 0  // 防过期响应

// 哪些 ability 可以应用 + 提示
function canApply(inv) {
  if (!inv) return false
  return ['summarize', 'organize', 'suggest_tags', 'suggest_task'].includes(inv.ability)
}
const applyHint = computed(() => {
  const inv = lastInvoke.value
  if (!inv) return ''
  if (!canApply(inv)) return '该能力暂不支持应用。'
  if (inv.ability === 'suggest_task') return '将创建一条任务草稿，可到 /tasks 确认。'
  if (inv.ability === 'summarize') return '请选择目标笔记，摘要将写入其 summary 字段。'
  if (inv.ability === 'organize') return '请选择目标笔记，结果将覆盖其 title/content/summary。'
  if (inv.ability === 'suggest_tags') return '请选择目标笔记，结果将覆盖其标签。'
  return ''
})

const canConfirmApply = computed(() => {
  const inv = lastInvoke.value
  if (!inv) return false
  if (inv.ability === 'suggest_task') return true
  return !!applyTargetNoteId.value
})

const applyButtonLabel = computed(() => {
  const inv = lastInvoke.value
  if (!inv) return '确认写入'
  if (inv.ability === 'suggest_task') return '确认创建任务'
  return '应用到笔记'
})

/**
 * 加载目标笔记候选列表（支持分页 + 关键词搜索）。
 * @param {Object} opts
 * @param {boolean} [opts.reset=false] - true 表示重置分页到第 1 页并清空候选
 * @param {string} [opts.keyword] - 覆盖当前关键词（可选）
 */
async function loadApplyTargetNotes({ reset = false, keyword = undefined } = {}) {
  if (reset) {
    applyTargetPage.value = 1
    applyTargetNotes.value = []
    applyTargetTotal.value = 0
    if (keyword !== undefined) applyTargetKeyword.value = keyword
  }
  notesLoading.value = true
  applyTargetError.value = ''
  const seq = ++applyTargetSeq
  try {
    const params = {
      page: applyTargetPage.value,
      size: applyTargetSize.value,
    }
    if (applyTargetKeyword.value) params.q = applyTargetKeyword.value
    const res = await workbenchApi.notes.list(params)
    // 过期响应直接丢弃
    if (seq !== applyTargetSeq) return
    const data = res.data || {}
    const list = data.list || []
    applyTargetTotal.value = data.total || 0
    // 累加候选（避免覆盖）
    const seen = new Set(applyTargetNotes.value.map((n) => n.id))
    for (const n of list) {
      if (n && n.id && !seen.has(n.id)) {
        applyTargetNotes.value.push(n)
        seen.add(n.id)
      }
    }
    // 重置模式下自动选中第一条
    if (reset && !applyTargetNoteId.value && applyTargetNotes.value.length) {
      applyTargetNoteId.value = applyTargetNotes.value[0].id
    }
  } catch (e) {
    if (seq !== applyTargetSeq) return
    applyTargetError.value = '加载笔记失败：' + (e?.response?.data?.msg || e.message)
  } finally {
    if (seq === applyTargetSeq) notesLoading.value = false
  }
}

/** 远程搜索：输入框变化时触发 */
function searchApplyTargetNotes(query) {
  loadApplyTargetNotes({ reset: true, keyword: query || '' })
}

/** 滚动到底：触发加载下一页（仅在还有更多时） */
function onApplyTargetPageChange() {
  if (applyTargetNotes.value.length >= applyTargetTotal.value) return
  applyTargetPage.value += 1
  loadApplyTargetNotes()
}

const applyTargetMetaText = computed(() => {
  const loaded = applyTargetNotes.value.length
  const total = applyTargetTotal.value
  const kw = applyTargetKeyword.value
  if (kw) {
    return `已加载 ${loaded} / 共匹配 ${total} 条（关键词：${kw}）`
  }
  return `已加载 ${loaded} / 共 ${total} 条`
})

/** 新建草稿笔记作为应用目标，并自动选上 */
async function createApplyTargetNote() {
  applyTargetError.value = ''
  try {
    const res = await workbenchApi.notes.create({ title: 'AI 应用目标', content: '', status: 'draft' })
    const note = res.data
    if (!note || !note.id) {
      applyTargetError.value = '新建笔记失败：返回为空'
      return
    }
    applyTargetNoteId.value = note.id
    // 加入候选列表（避免重复）
    if (!applyTargetNotes.value.find((n) => n.id === note.id)) {
      applyTargetNotes.value.unshift(note)
    }
    // 新建后总数 +1
    applyTargetTotal.value += 1
    ElMessage.success('已创建草稿笔记 #' + note.id)
  } catch (e) {
    applyTargetError.value = '新建笔记失败：' + (e?.response?.data?.msg || e.message)
  }
}

async function loadConversations() {
  const res = await workbenchApi.ai.conversations()
  conversations.value = res.data.list || []
  if (conversations.value.length && !activeId.value) {
    open(conversations.value[0].id)
  }
}

async function open(id) {
  activeId.value = id
  const res = await workbenchApi.ai.messages(id)
  messages.value = res.data.list || []
}

async function create() {
  if (!newTitle.value.trim()) {
    ElMessage.warning('请输入对话标题')
    return
  }
  const res = await workbenchApi.ai.createConversation({ title: newTitle.value.trim() })
  showCreate.value = false
  newTitle.value = ''
  await loadConversations()
  open(res.data.id)
}

async function del(id) {
  try {
    await ElMessageBox.confirm('删除该对话？原始笔记/资产/任务不会被删除。', '提示', { type: 'warning' })
  } catch { return }
  await workbenchApi.ai.deleteConversation(id)
  if (activeId.value === id) {
    activeId.value = null
    messages.value = []
  }
  loadConversations()
}

// 1. 用户点击"发送" → ai.preview → 显示预览
async function openPreview() {
  const text = draft.value.trim()
  if (!text || !activeId.value) return
  sending.value = true
  pendingAbility.value = 'summarize'
  try {
    const res = await workbenchApi.ai.preview({
      ability: pendingAbility.value,
      content: text,
      conversation_id: activeId.value,
    })
    const d = res.data || {}
    previewText.value = d.preview || text
    previewMeta.value = { char_count: d.char_count, has_more: !!d.has_more }
    previewDialog.value = true
  } catch (e) {
    ElMessage.error('预览失败：' + (e?.response?.data?.msg || e.message))
  } finally {
    sending.value = false
  }
}

// 用户在预览阶段取消：不调用 invoke，仅关闭对话框
function cancelPreview() {
  previewDialog.value = false
  previewText.value = ''
  previewMeta.value = null
}

// 2. 用户确认 → ai.invoke(ability, content, conversation_id)
async function confirmInvoke() {
  const text = draft.value.trim()
  if (!text || !activeId.value) return
  invoking.value = true
  try {
    const res = await workbenchApi.ai.invoke({
      ability: pendingAbility.value,
      content: text,
      conversation_id: activeId.value,
    })
    const d = res.data || {}
    lastInvoke.value = {
      ability: d.ability,
      text: d.text || '',
      data: d.data || {},
      provider: d.provider,
      is_fake: !!d.is_fake,
      conversation_id: d.conversation_id || activeId.value,
    }
    previewDialog.value = false
    resultDialog.value = true
    draft.value = ''
    // note 类能力需要候选笔记列表
    if (lastInvoke.value.ability !== 'suggest_task') {
      applyTargetNoteId.value = null
      applyTargetKeyword.value = ''
      loadApplyTargetNotes({ reset: true })
    }
    // 刷新消息列表（user/assistant 两条已落库）
    await open(activeId.value)
  } catch (e) {
    ElMessage.error('调用失败：' + (e?.response?.data?.msg || e.message))
  } finally {
    invoking.value = false
  }
}

// 3. 用户确认应用结果 → ai.apply（按 ability 选择目标）
async function confirmApply() {
  const inv = lastInvoke.value
  if (!inv) return
  applying.value = true
  try {
    let payload = inv.data || {}
    let targetType, targetId
    if (inv.ability === 'suggest_task') {
      targetType = 'task'
      targetId = null
    } else {
      // note 类（summarize / suggest_tags / organize）必须有 target 笔记
      const noteId = applyTargetNoteId.value
      if (!noteId) {
        ElMessage.warning('请先选择或新建目标笔记')
        applying.value = false
        return
      }
      targetType = 'note'
      targetId = noteId
    }
    const res = await workbenchApi.ai.apply({
      ability: inv.ability,
      target_type: targetType,
      target_id: targetId,
      conversation_id: inv.conversation_id,
      payload,
    })
    const applied = res.data && res.data.applied
    if (applied === 'task') {
      const newTask = (res.data && res.data.task) || {}
      if (newTask.id) {
        ElMessage.success(`任务已创建：${newTask.title || ''}（#${newTask.id}）`)
      } else {
        ElMessage.success('任务已创建，请到 /tasks 确认')
      }
    } else if (applied === 'note') {
      const note = (res.data && res.data.note) || {}
      ElMessage.success(`已应用到笔记 #${note.id || targetId}`)
    } else {
      ElMessage.success('应用完成')
    }
    resultDialog.value = false
    lastInvoke.value = null
    applyTargetNoteId.value = null
  } catch (e) {
    ElMessage.error('应用失败：' + (e?.response?.data?.msg || e.message))
  } finally {
    applying.value = false
  }
}

function discardResult() {
  resultDialog.value = false
  lastInvoke.value = null
  applyTargetNoteId.value = null
}

function roleLabel(r) { return ({ user: '我', assistant: 'AI', system: '系统' })[r] || r }

watch(activeId, () => { messages.value = [] })

onMounted(loadConversations)
</script>

<style scoped>
.assistant-page { max-width: 1100px; margin: 0 auto; padding: 24px 16px 80px; }
.assistant-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.assistant-header h1 { font-size: 22px; margin: 0; }
.assistant-body { display: grid; grid-template-columns: 240px 1fr; gap: 16px; min-height: 60vh; }
.assistant-sidebar { background: var(--paper-white); border-radius: var(--radius-sm); padding: 12px; }
.assistant-sidebar h3 { font-size: 13px; margin: 0 0 8px; color: var(--color-text-muted); }
.assistant-sidebar ul { list-style: none; margin: 0; padding: 0; }
.assistant-sidebar li {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer; font-size: 13px;
}
.assistant-sidebar li:hover { background: var(--paper-cream); }
.assistant-sidebar li.active { background: var(--rattan-yellow); color: var(--paper-white); }
.assistant-sidebar li.empty { color: var(--color-text-muted); cursor: default; }
.del-btn { background: transparent; border: 0; color: inherit; cursor: pointer; font-size: 16px; }
.assistant-main { background: var(--paper-white); border: 1px solid var(--paper-aged); border-radius: var(--radius-sm); display: flex; flex-direction: column; }
.messages { flex: 1; padding: 12px; overflow-y: auto; max-height: 50vh; }
.msg { margin-bottom: 12px; }
.msg.user .msg-content { background: var(--paper-white); }
.msg.assistant .msg-content { background: var(--mist-light); }
.msg-role { font-size: 11px; color: var(--color-text-muted); margin-bottom: 2px; }
.msg-meta { font-size: 11px; color: var(--color-text-muted); margin-top: 4px; }
.msg-content {
  margin: 0; padding: 8px 10px; border-radius: 6px;
  white-space: pre-wrap; word-break: break-word; font-size: 13px;
  font-family: inherit;
}
.msg-scope { margin-top: 4px; font-size: 11px; color: var(--color-text-muted); }
.msg-scope pre { background: var(--paper-aged); padding: 4px; border-radius: 3px; max-height: 120px; overflow: auto; }
.composer { padding: 12px; border-top: 1px solid var(--paper-aged); }
.composer-actions { margin-top: 6px; text-align: right; }
.placeholder { color: var(--color-text-muted); padding: 40px; text-align: center; }
.empty { color: var(--color-text-muted); text-align: center; padding: 12px; }
.ai-scope { background: var(--paper-aged); padding: 8px; border-radius: var(--radius-sm); font-size: 12px; max-height: 200px; overflow: auto; white-space: pre-wrap; word-break: break-word; }
.ai-meta, .ai-status, .ai-apply-note { font-size: 12px; color: var(--color-text-muted); margin: 6px 0 0; }
.ai-result { background: var(--mist-light); padding: 8px; border-radius: var(--radius-sm); font-size: 12px; max-height: 240px; overflow: auto; white-space: pre-wrap; word-break: break-word; }
.ai-result-meta { display: flex; gap: 12px; font-size: 12px; color: var(--color-text-muted); margin-bottom: 8px; }
.ai-result-data { margin-top: 8px; font-size: 11px; color: var(--color-text-muted); }
.ai-result-data pre { background: var(--paper-aged); padding: 4px; border-radius: 3px; max-height: 120px; overflow: auto; }
.apply-target { margin-top: 12px; padding: 10px; background: var(--paper-cream); border: 1px solid var(--paper-aged)2c0; border-radius: var(--radius-sm); }
.apply-target h4 { margin: 0 0 6px; font-size: 13px; }
.apply-target-row { display: flex; gap: 8px; align-items: center; }
.apply-target-row .el-select { flex: 1; min-width: 200px; }
.ai-apply-error { color: var(--color-danger); font-size: 12px; margin: 6px 0 0; }
.apply-target-tip { color: var(--color-text-muted); font-size: 11px; margin: 6px 0 0; }
@media (max-width: 700px) {
  .assistant-body { grid-template-columns: 1fr; }
}
</style>
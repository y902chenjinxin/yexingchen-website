<template>
  <div class="assistant-page">
    <header class="assistant-header">
      <BackButton fallback="/workbench" style="margin-right: 12px;" /><h1>AI 助手</h1>
      <div class="header-actions">
        <el-select
          v-model="currentProviderId"
          placeholder="选择 Provider"
          style="width: 220px"
          @change="onProviderChange"
        >
          <el-option
            v-for="p in providers"
            :key="p.id"
            :value="p.id"
            :label="p.display_name + ' · ' + p.model_name"
          >
            <span style="float:left">{{ p.display_name }}</span>
            <span style="float:right;font-size:12px;color:#999;margin-left:8px">
              {{ p.provider_key }} · {{ p.is_default ? '默认' : '' }}
            </span>
          </el-option>
          <el-option v-if="!providers.length" :value="null" disabled label="（未配置 Provider，AI 使用 fake）" />
        </el-select>
        <el-button @click="openProviders">配置 AI</el-button>
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
              <!-- 结构化结果内联应用（不用弹窗） -->
              <div v-if="inlineApply && inlineApply.msgId === m.id" class="inline-apply">
                <template v-if="inlineApply.applied">
                  <span class="inline-applied">✓ 已应用</span>
                </template>
                <template v-else>
                  <details :open="inlineApplyOpen" class="inline-apply-box">
                    <summary>{{ inlineApplySummary }}</summary>
                    <div v-if="inlineApply.ability === 'suggest_task'" class="inline-apply-body">
                      <p class="inline-apply-tip">将把 AI 建议创建为一条任务草稿。</p>
                      <div class="inline-apply-actions">
                        <el-button size="small" @click="hideInlineApply">放弃</el-button>
                        <el-button size="small" type="primary" :loading="applying" @click="confirmApplyInline">确认创建任务</el-button>
                      </div>
                    </div>
                    <div v-else class="inline-apply-body">
                      <p class="inline-apply-tip">选择要将结果写入的目标笔记：</p>
                      <div class="apply-target-row">
                        <NoteSelect
                          v-model="applyTargetNoteId"
                          :items="applyTargetNotes"
                          :loading="notesLoading"
                          :has-more="applyTargetNotes.length < applyTargetTotal"
                          placeholder="输入关键词搜索笔记…"
                          empty-text="暂无笔记可选，点右侧「新建草稿」"
                          style="flex: 1; min-width: 200px"
                          @search="loadApplyTargetNotes({ reset: true, keyword: $event })"
                          @load-more="loadApplyTargetNotes()"
                        />
                        <el-button size="small" @click="loadApplyTargetNotes({ reset: true })" :disabled="notesLoading">刷新</el-button>
                        <el-button size="small" type="primary" plain @click="createApplyTargetNote" :disabled="notesLoading">新建草稿</el-button>
                      </div>
                      <p v-if="applyTargetError" class="ai-apply-error">{{ applyTargetError }}</p>
                      <div class="inline-apply-actions">
                        <el-button size="small" @click="hideInlineApply">放弃</el-button>
                        <el-button size="small" type="primary" :disabled="!applyTargetNoteId || applying" :loading="applying" @click="confirmApplyInline">{{ applyButtonLabel }}</el-button>
                      </div>
                    </div>
                  </details>
                </template>
              </div>
            </div>
            <div v-if="!messages.length" class="empty">开始新对话吧</div>
          </div>
          <div class="composer">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="3"
              placeholder="输入要发送给 AI 的内容，回车发送（Shift+回车换行）"
              @keydown.enter.exact.prevent="send"
            />
            <div class="composer-actions">
              <el-button type="primary" :disabled="!draft.trim() || sending" @click="send" :loading="sending">
                发送
              </el-button>
            </div>
          </div>
        </template>
        <p v-else class="placeholder">在左侧选择或新建一个对话。</p>
      </main>
    </div>

    <el-dialog v-model="showCreate" title="新建对话" width="420px">
      <el-input v-model="newTitle" placeholder="对话标题（可选）" />
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <!-- AI Provider 配置弹窗 -->
    <el-dialog v-model="showProviders" title="配置 AI Provider" width="640px" :close-on-click-modal="false">
      <p class="modal-tip">
        支持 OpenAI 兼容协议（GPT / DeepSeek / 通义 / Qwen / GLM / 月之暗面 等）。
        Key 按你的授权明文存储，访问 AI 时直接调用。
      </p>

      <div v-if="!providers.length && !showAddProvider" class="empty-providers">
        <p>还没配置 AI Provider。</p>
        <el-button type="primary" @click="openAddProvider">添加第一个 Provider</el-button>
      </div>

      <div v-else class="provider-list">
        <div v-for="p in providers" :key="p.id" class="provider-item">
          <div class="provider-info">
            <div class="provider-name">{{ p.display_name }}</div>
            <div class="provider-meta">
              {{ p.provider_key }} · {{ p.model_name }}
              <span v-if="p.base_url"> · {{ p.base_url }}</span>
              <span v-if="p.is_default" class="badge">默认</span>
              <span v-if="!p.enabled" class="badge-off">已停用</span>
            </div>
            <div class="provider-key">Key: {{ p.api_key_masked }}</div>
          </div>
          <div class="provider-actions">
            <el-button size="small" :loading="testingId === p.id" @click="testProvider(p.id)">测试</el-button>
            <el-button size="small" @click="editProvider(p)">编辑</el-button>
            <el-button v-if="!p.is_default" size="small" @click="setDefault(p.id)">设为默认</el-button>
            <el-button size="small" type="danger" @click="delProvider(p)">删除</el-button>
          </div>
        </div>
        <el-button @click="openAddProvider" style="margin-top: 12px;">
          {{ providers.length ? '+ 添加新 Provider' : '添加 Provider' }}
        </el-button>
      </div>

      <div v-if="showAddProvider" class="add-provider-form">
        <h4>{{ editingProviderId ? '编辑 Provider' : '添加 Provider' }}</h4>
        <el-form :model="newProvider" label-width="100px" label-position="left">
          <el-form-item label="显示名称">
            <el-input v-model="newProvider.display_name" placeholder="我的 GPT-4" />
          </el-form-item>
          <el-form-item label="提供商类型">
            <el-select v-model="newProvider.provider_key">
              <el-option label="OpenAI 兼容" value="openai" />
            </el-select>
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="newProvider.api_key" type="password" show-password placeholder="sk-..." />
          </el-form-item>
          <el-form-item label="Base URL（可选）">
            <el-input v-model="newProvider.base_url" placeholder="https://api.openai.com/v1" />
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="newProvider.model_name" placeholder="gpt-4o-mini" />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="newProvider.is_default">设为默认</el-checkbox>
            <el-checkbox v-model="newProvider.enabled" style="margin-left: 16px;">启用</el-checkbox>
          </el-form-item>
          <div class="form-actions">
            <el-button @click="cancelProviderForm">取消</el-button>
            <el-button @click="saveProvider" type="primary" :loading="savingProvider">
              {{ editingProviderId ? '保存' : '添加' }}
            </el-button>
          </div>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="showProviders = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'
import BackButton from '@/components/BackButton.vue'
import NoteSelect from '@/components/common/NoteSelect.vue'

const conversations = ref([])

// === AI Provider 配置 ===
const providers = ref([])
const currentProviderId = ref(null)
const showProviders = ref(false)
const showAddProvider = ref(false)
const editingProviderId = ref(null)
const testingId = ref(null)
const savingProvider = ref(false)
const newProvider = ref({
  provider_key: 'openai',
  display_name: '',
  api_key: '',
  base_url: '',
  model_name: 'gpt-4o-mini',
  is_default: false,
  enabled: true,
})
const activeId = ref(null)
const messages = ref([])
const draft = ref('')
const showCreate = ref(false)
const newTitle = ref('')

// AI 流程状态
const sending = ref(false)
const pendingAbility = ref('summarize')

const lastInvoke = ref(null)  // { ability, text, data, provider, is_fake, conversation_id, ... }
const applying = ref(false)

// 内联应用（不弹窗，挂在对应消息气泡下）
const inlineApply = ref(null)  // { msgId, ability, applied }
const inlineApplyOpen = ref(true)
const inlineApplySummary = computed(() => {
  if (!inlineApply.value || !lastInvoke.value) return ''
  if (lastInvoke.value.ability === 'suggest_task') return '将 AI 建议创建为任务草稿'
  return '选择目标笔记并写入结果'
})

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

// 应用按钮文案
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


// === AI Provider 配置 ===
async function loadProviders() {
  try {
    const r = await workbenchApi.ai.providersList()
    providers.value = r.data || []
    // 恢复当前选中的 provider（如果还存在），否则选默认或第一个
    if (!providers.value.find(p => p.id === currentProviderId.value)) {
      const def = providers.value.find(p => p.is_default && p.enabled)
      currentProviderId.value = def ? def.id : (providers.value[0]?.id ?? null)
    }
  } catch (e) {
    providers.value = []
    currentProviderId.value = null
  }
}

function openProviders() {
  showProviders.value = true
  loadProviders()
}

function resetProviderForm() {
  newProvider.value = {
    provider_key: 'openai',
    display_name: '',
    api_key: '',
    base_url: '',
    model_name: 'gpt-4o-mini',
    is_default: false,
    enabled: true,
  }
  editingProviderId.value = null
  showAddProvider.value = false
}

function openAddProvider() {
  resetProviderForm()
  showAddProvider.value = true
}

function editProvider(p) {
  editingProviderId.value = p.id
  newProvider.value = {
    provider_key: p.provider_key,
    display_name: p.display_name,
    api_key: '',  // 编辑时不回填 Key（安全）
    base_url: p.base_url || '',
    model_name: p.model_name,
    is_default: p.is_default,
    enabled: p.enabled,
  }
  showAddProvider.value = true
}

function cancelProviderForm() {
  resetProviderForm()
}

async function saveProvider() {
  if (!newProvider.value.display_name || !newProvider.value.api_key) {
    ElMessage.warning('请填写显示名称和 API Key')
    return
  }
  savingProvider.value = true
  try {
    const payload = { ...newProvider.value }
    if (editingProviderId.value) {
      // 编辑：如果 api_key 为空字符串表示未改，不传
      if (!payload.api_key) delete payload.api_key
      await workbenchApi.ai.providerUpdate(editingProviderId.value, payload)
      ElMessage.success('已保存')
    } else {
      await workbenchApi.ai.providerCreate(payload)
      ElMessage.success('已添加')
    }
    resetProviderForm()
    await loadProviders()
  } catch (e) {
    // 错误已由 axios 拦截器处理
  } finally {
    savingProvider.value = false
  }
}

async function testProvider(id) {
  testingId.value = id
  try {
    const r = await workbenchApi.ai.providerTest(id)
    const msg = r.data || r
    if (msg.ok) {
      ElMessage.success(msg.message || '连接成功')
    } else {
      ElMessage.error(msg.message || '连接失败')
    }
  } catch (e) {
    // 拦截器已显示
  } finally {
    testingId.value = null
  }
}

async function setDefault(id) {
  try {
    await workbenchApi.ai.providerUpdate(id, { is_default: true })
    ElMessage.success('已设为默认')
    await loadProviders()
  } catch (e) {}
}

async function delProvider(p) {
  try {
    await ElMessageBox.confirm(`确认删除「${p.display_name}」?`, '删除 Provider', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await workbenchApi.ai.providerDelete(p.id)
    ElMessage.success('已删除')
    if (currentProviderId.value === p.id) currentProviderId.value = null
    await loadProviders()
  } catch (e) {
    // 用户取消或失败
  }
}

function onProviderChange(id) {
  currentProviderId.value = id
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

// 发送：直接调用 invoke（不再弹预览确认），结果在气泡内联呈现
async function send() {
  const text = draft.value.trim()
  if (!text || !activeId.value) return
  sending.value = true
  try {
    const res = await workbenchApi.ai.invoke({
      ability: pendingAbility.value,
      content: text,
      conversation_id: activeId.value,
      provider_id: currentProviderId.value || null,
    })
    const d = res.data || {}
    draft.value = ''
    lastInvoke.value = {
      ability: d.ability,
      text: d.text || '',
      data: d.data || {},
      provider: d.provider,
      is_fake: !!d.is_fake,
      conversation_id: d.conversation_id || activeId.value,
    }
    // 刷新消息列表（user/assistant 两条已落库）
    await open(activeId.value)
    // 定位本次 assistant 回复，激活其内联应用面板
    const asst = [...messages.value].reverse().find((m) => m.role === 'assistant')
    inlineApply.value = {
      msgId: asst ? asst.id : null,
      ability: lastInvoke.value.ability,
      applied: false,
    }
    inlineApplyOpen.value = true
    // note 类能力需要候选笔记列表
    if (lastInvoke.value.ability !== 'suggest_task') {
      applyTargetNoteId.value = null
      applyTargetKeyword.value = ''
      loadApplyTargetNotes({ reset: true })
    }
  } catch (e) {
    ElMessage.error('调用失败：' + (e?.response?.data?.msg || e.message))
  } finally {
    sending.value = false
  }
}

// 关闭内联应用面板
function hideInlineApply() {
  inlineApply.value = null
  applyTargetNoteId.value = null
}

// 在气泡内联确认应用结果 → ai.apply
async function confirmApplyInline() {
  const inv = lastInvoke.value
  if (!inv || !inlineApply.value) return
  applying.value = true
  try {
    let payload = inv.data || {}
    let targetType, targetId
    if (inv.ability === 'suggest_task') {
      targetType = 'task'
      targetId = null
    } else {
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
    inlineApply.value.applied = true
    applyTargetNoteId.value = null
  } catch (e) {
    ElMessage.error('应用失败：' + (e?.response?.data?.msg || e.message))
  } finally {
    applying.value = false
  }
}

function roleLabel(r) { return ({ user: '我', assistant: 'AI', system: '系统' })[r] || r }

watch(activeId, () => { messages.value = [] })

onMounted(() => { loadConversations(); loadProviders(); })
</script>

<style scoped>
.assistant-page { max-width: 1100px; margin: 0 auto; padding: 24px 16px 80px; font-family: var(--font-serif); color: var(--xiu-text); }
.assistant-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.assistant-header h1 { font-size: 26px; margin: 0; letter-spacing: .1em; background: linear-gradient(135deg,#c9a96e,#f0e6c8 48%,#c9a96e); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color: transparent; }
.assistant-body { display: grid; grid-template-columns: 240px 1fr; gap: 16px; min-height: 60vh; }
.assistant-sidebar { background: var(--xiu-card); backdrop-filter: blur(12px); border: 1px solid var(--xiu-line); border-radius: 14px; padding: 12px; }
.assistant-sidebar h3 { font-size: 13px; margin: 0 0 8px; color: var(--xiu-gold); letter-spacing: .1em; }
.assistant-sidebar ul { list-style: none; margin: 0; padding: 0; }
.assistant-sidebar li {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 8px; border-radius: 8px; cursor: pointer; font-size: 13px; color: var(--xiu-text-2);
}
.assistant-sidebar li:hover { background: rgba(201, 169, 110, .12); color: var(--xiu-text); }
.assistant-sidebar li.active { background: rgba(61, 184, 176, .22); color: var(--xiu-primary-bright); }
.assistant-sidebar li.empty { color: var(--xiu-text-3); cursor: default; }
.del-btn { background: transparent; border: 0; color: inherit; cursor: pointer; font-size: 16px; }
.assistant-main { background: var(--xiu-card-strong); border: 1px solid var(--xiu-line); border-radius: 14px; display: flex; flex-direction: column; backdrop-filter: blur(12px); }
.messages { flex: 1; padding: 12px; overflow-y: auto; max-height: 50vh; }
.msg { margin-bottom: 12px; }
.msg.user .msg-content { background: rgba(61, 184, 176, .14); border: 1px solid rgba(61, 184, 176, .2); }
.msg.assistant .msg-content { background: rgba(201, 169, 110, .1); border: 1px solid rgba(201, 169, 110, .18); }
.msg-role { font-size: 11px; color: var(--xiu-gold); margin-bottom: 2px; }
.msg-meta { font-size: 11px; color: var(--xiu-text-3); margin-top: 4px; }
.msg-content {
  margin: 0; padding: 8px 10px; border-radius: 8px;
  white-space: pre-wrap; word-break: break-word; font-size: 13px;
  font-family: inherit; color: var(--xiu-text);
}
.msg-scope { margin-top: 4px; font-size: 11px; color: var(--xiu-text-3); }
.msg-scope pre { background: rgba(0,0,0,.2); padding: 4px; border-radius: 5px; max-height: 120px; overflow: auto; color: var(--xiu-text-2); }
.inline-apply { margin-top: 8px; }
.inline-applied {
  display: inline-block; padding: 4px 10px; font-size: 12px; color: var(--xiu-primary-bright);
  background: rgba(61, 184, 176, .14); border: 1px solid rgba(61, 184, 176, .3); border-radius: 6px;
}
.inline-apply-box { border: 1px solid var(--xiu-line); border-radius: 8px; background: var(--xiu-card); padding: 4px 8px 8px; }
.inline-apply-box summary {
  cursor: pointer; font-size: 12px; color: var(--xiu-gold); padding: 4px 2px; user-select: none;
}
.inline-apply-body { padding: 6px 2px 2px; }
.inline-apply-tip { font-size: 12px; color: var(--xiu-text-2); margin: 0 0 8px; }
.inline-apply-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }
.apply-target-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.composer { padding: 12px; border-top: 1px solid var(--xiu-line); }
.composer-actions { margin-top: 6px; text-align: right; }
.placeholder { color: var(--xiu-text-3); padding: 40px; text-align: center; }
.empty { color: var(--xiu-text-3); text-align: center; padding: 12px; }
.ai-apply-error { color: var(--xiu-danger); font-size: 12px; margin: 6px 0 0; }
@media (max-width: 700px) {
  .assistant-body { grid-template-columns: 1fr; }
}

.header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.modal-tip { color: var(--xiu-text-2); font-size: 12px; margin: 0 0 16px 0; line-height: 1.6; }
.empty-providers { padding: 40px 0; text-align: center; color: var(--xiu-text-3); }
.provider-list { max-height: 400px; overflow-y: auto; }
.provider-item {
  display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;
  padding: 12px; border: 1px solid var(--xiu-line); border-radius: 10px;
  margin-bottom: 8px; gap: 12px; background: var(--xiu-card);
}
.provider-info { flex: 1; min-width: 0; }
.provider-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; color: var(--xiu-text); }
.provider-meta { font-size: 12px; color: var(--xiu-text-2); margin-bottom: 4px; }
.provider-key { font-size: 12px; color: var(--xiu-text-3); font-family: monospace; }
.provider-actions { display: flex; gap: 4px; flex-wrap: wrap; }
.badge { display: inline-block; padding: 2px 6px; background: var(--xiu-primary); color: #fff; border-radius: 3px; font-size: 11px; margin-left: 6px; }
.badge-off { display: inline-block; padding: 2px 6px; background: var(--xiu-text-3); color: #fff; border-radius: 3px; font-size: 11px; margin-left: 6px; }
.add-provider-form { padding: 16px; border-top: 1px dashed var(--xiu-line); margin-top: 12px; }
.add-provider-form h4 { margin: 0 0 12px 0; color: var(--xiu-text); }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
</style>
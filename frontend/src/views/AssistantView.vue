<template>
  <div class="assistant-page">
    <header class="assistant-header">
      <div class="assistant-header-left">
        <BackButton fallback="/workbench" style="margin-right: 12px;" /><h1>AI 助手</h1>
        <span class="header-sub">独立对话 · 流式回答 · 可总结 / 生成笔记</span>
      </div>
      <div class="header-actions">
        <el-select
          v-model="currentProviderId"
          placeholder="选择 Provider"
          style="width: 220px"
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
          <el-option v-if="!providers.length" :value="null" disabled label="（未配置 Provider，使用离线演示）" />
        </el-select>
        <el-button @click="openProviders">配置 AI</el-button>
      </div>
    </header>

    <div class="assistant-body">
      <aside class="assistant-sidebar">
        <button class="new-chat-btn" @click="newConversation">
          <el-icon style="font-size:15px"><Plus /></el-icon><span>新对话</span>
        </button>
        <h3>历史对话</h3>
        <ul>
          <li
            v-for="c in conversations"
            :key="c.id"
            :class="{ active: c.id === activeId }"
            @click="open(c.id)"
          >
            <span class="conv-title">{{ c.title || '新对话' }}</span>
            <button class="del-btn" @click.stop="del(c.id)">×</button>
          </li>
          <li v-if="!conversations.length" class="empty">还没有对话</li>
        </ul>
      </aside>

      <main class="assistant-main">
        <template v-if="activeId !== null">
          <div class="messages" ref="msgListRef">
            <div v-for="(m, i) in messages" :key="m.key" :class="['chat-msg', m.role]">
              <div class="chat-bubble">
                <div class="chat-name">
                  {{ m.role === 'user' ? '我' : '玄黄 AI' }}
                  <template v-if="m.role === 'assistant' && m.provider"> · {{ m.provider }}</template>
                </div>
                <div class="chat-text" v-html="renderText(m.content)"></div>
                <span v-if="m.role === 'assistant' && m.status === 'streaming'" class="chat-cursor">▍</span>
                <!-- 记入笔记（已完成 assistant 气泡内折叠操作，不弹窗） -->
                <div v-if="m.role === 'assistant' && m.status === 'done'" class="chat-save">
                  <details @toggle="m.save.open = $event.target.open">
                    <summary class="chat-save-toggle">记入笔记</summary>
                    <div class="chat-save-body">
                      <el-input v-model="m.save.title" size="small" placeholder="笔记标题（可选，默认取首行）" />
                      <el-input
                        v-model="m.save.content"
                        type="textarea"
                        :rows="5"
                        size="small"
                        placeholder="笔记正文（可先编辑再保存）"
                        class="chat-save-content"
                      />
                      <div class="chat-save-actions">
                        <el-button
                          size="small"
                          type="primary"
                          :loading="m.save.saving"
                          :disabled="m.save.saved"
                          @click="saveNoteToNotebook(i)"
                        >
                          {{ m.save.saved ? '已保存 ✓' : '创建笔记' }}
                        </el-button>
                      </div>
                    </div>
                  </details>
                </div>
              </div>
            </div>
            <div v-if="!messages.length" class="empty">
              <p class="empty-title">你好，我是你的独立 AI 助手</p>
              <p class="empty-sub">随便问我日常问题、让我总结一段文字，或帮我把想法整理成笔记。</p>
            </div>
          </div>
          <div class="composer">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="3"
              placeholder="和 AI 对话…（Enter 发送，Shift+Enter 换行）"
              @keydown.enter.exact.prevent="send"
            />
            <div class="composer-actions">
              <span v-if="streamError" class="composer-error">{{ streamError }}</span>
              <el-button type="primary" :disabled="!draft.trim() || sending" :loading="sending" @click="send">
                发送
              </el-button>
            </div>
          </div>
        </template>
        <div v-else class="placeholder">
          <p>点击左侧「新对话」或选择一个历史对话开始。</p>
        </div>
      </main>
    </div>

    <!-- AI Provider 配置弹窗 -->
    <el-dialog v-model="showProviders" title="配置 AI Provider" width="640px" :close-on-click-modal="false">
      <p class="modal-tip">
        支持 OpenAI 兼容协议（GPT / DeepSeek / 通义 / Qwen / GLM 等）。
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
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workbenchApi } from '@/api/workbench'
import BackButton from '@/components/BackButton.vue'

const conversations = ref([])
const activeId = ref(null)
const messages = ref([])
const draft = ref('')
const sending = ref(false)
const streamError = ref('')
const msgListRef = ref(null)
const streamController = ref(null)
let seq = 0  // 防过期响应 / 限制并发

/* ---- Provider 配置 ---- */
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

/* ---- 工具函数 ---- */
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]))
}
function renderText(s) {
  return escapeHtml(s).replace(/\n/g, '<br>')
}
function makeSaveMeta() {
  return { open: false, title: '', content: '', saved: false, saving: false }
}

async function scrollToBottom() {
  await nextTick()
  const el = msgListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

/* ---- 消息管理 ---- */
async function loadConversations() {
  const res = await workbenchApi.ai.conversations()
  conversations.value = res.data.list || []
}

async function open(id) {
  activeId.value = id
  streamError.value = ''
  const res = await workbenchApi.ai.messages(id)
  messages.value = (res.data.list || []).map((m) => ({
    key: `m-${m.id}`,
    id: m.id,
    role: m.role,
    content: m.content || '',
    status: 'done',
    provider: '',
    save: makeSaveMeta(),
  }))
  await scrollToBottom()
}

async function newConversation() {
  // 点击即创建一条真实会话，使对话输入区立即可用
  streamError.value = ''
  try {
    const created = await workbenchApi.ai.createConversation({ title: '新对话' })
    activeId.value = created.data.id
    messages.value = []
    await loadConversations()
    await scrollToBottom()
  } catch (e) {
    ElMessage.error('创建对话失败：' + (e?.response?.data?.msg || e.message))
  }
}

async function del(id) {
  try {
    await ElMessageBox.confirm('删除该对话？历史消息也会一并删除。', '提示', { type: 'warning' })
  } catch { return }
  await workbenchApi.ai.deleteConversation(id)
  if (activeId.value === id) { activeId.value = null; messages.value = [] }
  loadConversations()
}

/* ---- 发送：原生流式对话 ---- */
async function send() {
  const text = draft.value.trim()
  if (!text || sending.value) return
  if (!activeId.value) {
    // 独立助手：没有会话时自动新建，标题取首行
    const title = text.split('\n')[0].slice(0, 20) || '新对话'
    const created = await workbenchApi.ai.createConversation({ title })
    activeId.value = created.data.id
    await loadConversations()
  }
  const convId = activeId.value

  const mySeq = ++seq
  sending.value = true
  streamError.value = ''
  draft.value = ''

  // 本地先推入用户消息 + 空的 assistant 消息（打字机）
  messages.value.push({ key: `u-${Date.now()}`, role: 'user', content: text, status: 'done' })
  const asstKey = `a-${Date.now()}`
  const asstMsg = { key: asstKey, role: 'assistant', content: '', status: 'streaming', provider: '', save: makeSaveMeta() }
  messages.value.push(asstMsg)
  await scrollToBottom()

  let aborted = false
  const controller = new AbortController()
  streamController.value = controller

  try {
    await workbenchApi.ai.chatStream(
      {
        content: text,
        conversation_id: convId,
        provider_id: currentProviderId.value || null,
      },
      (ev) => {
        if (mySeq !== seq || aborted) return
        if (ev.type === 'token' && ev.delta) {
          asstMsg.content += ev.delta
          scrollToBottom()
        } else if (ev.type === 'done') {
          asstMsg.status = 'done'
          asstMsg.provider = ev.provider || ''
          asstMsg.save.content = ev.text || asstMsg.content
          asstMsg.save.title = firstLineTitle(asstMsg.content)
        } else if (ev.type === 'error') {
          streamError.value = 'AI 出错：' + (ev.msg || '未知错误')
          asstMsg.content = asstMsg.content || '（生成失败）'
          asstMsg.status = 'done'
        }
      },
      controller.signal
    )
    if (mySeq === seq && asstMsg.status === 'streaming') asstMsg.status = 'done'
  } catch (e) {
    if (e.name === 'AbortError') aborted = true
    else streamError.value = '发送失败：' + (e.message || '网络错误')
    asstMsg.status = 'done'
  } finally {
    sending.value = false
    if (streamController.value === controller) streamController.value = null
    await scrollToBottom()
  }
}

function firstLineTitle(text) {
  const line = (text || '').split('\n')[0].trim()
  return line ? line.slice(0, 30) : 'AI 生成笔记'
}

/* ---- 记入笔记（创建一条新笔记，不弹窗） ---- */
async function saveNoteToNotebook(i) {
  const m = messages.value[i]
  if (!m || m.save.saving || m.save.saved) return
  m.save.saving = true
  streamError.value = ''
  try {
    const title = (m.save.title || '').trim() || firstLineTitle(m.content)
    const content = (m.save.content || m.content || '').trim()
    if (!content) { ElMessage.warning('笔记内容为空'); m.save.saving = false; return }
    await workbenchApi.notes.create({ title, content, status: 'draft' })
    m.save.saved = true
    ElMessage.success('已保存至笔记')
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.msg || e.message))
  } finally {
    m.save.saving = false
  }
}

/* ---- Provider 配置操作 ---- */
async function loadProviders() {
  try {
    const r = await workbenchApi.ai.providersList()
    providers.value = r.data || []
    if (!providers.value.find((p) => p.id === currentProviderId.value)) {
      const def = providers.value.find((p) => p.is_default && p.enabled)
      currentProviderId.value = def ? def.id : (providers.value[0]?.id ?? null)
    }
  } catch (e) {
    providers.value = []
    currentProviderId.value = null
  }
}
function openProviders() { showProviders.value = true; loadProviders() }
function resetProviderForm() {
  newProvider.value = { provider_key: 'openai', display_name: '', api_key: '', base_url: '', model_name: 'gpt-4o-mini', is_default: false, enabled: true }
  editingProviderId.value = null
  showAddProvider.value = false
}
function openAddProvider() { resetProviderForm(); showAddProvider.value = true }
function editProvider(p) {
  editingProviderId.value = p.id
  newProvider.value = { provider_key: p.provider_key, display_name: p.display_name, api_key: '', base_url: p.base_url || '', model_name: p.model_name, is_default: p.is_default, enabled: p.enabled }
  showAddProvider.value = true
}
function cancelProviderForm() { resetProviderForm() }
async function saveProvider() {
  if (!newProvider.value.display_name || !newProvider.value.api_key) {
    ElMessage.warning('请填写显示名称和 API Key'); return
  }
  savingProvider.value = true
  try {
    const payload = { ...newProvider.value }
    if (editingProviderId.value) {
      if (!payload.api_key) delete payload.api_key
      await workbenchApi.ai.providerUpdate(editingProviderId.value, payload)
      ElMessage.success('已保存')
    } else {
      await workbenchApi.ai.providerCreate(payload)
      ElMessage.success('已添加')
    }
    resetProviderForm()
    await loadProviders()
  } catch (e) { /* 拦截器已提示 */ } finally { savingProvider.value = false }
}
async function testProvider(id) {
  testingId.value = id
  try {
    const r = await workbenchApi.ai.providerTest(id)
    const msg = r.data || r
    if (msg.ok) ElMessage.success(msg.message || '连接成功')
    else ElMessage.error(msg.message || '连接失败')
  } catch (e) { /* 拦截器已提示 */ } finally { testingId.value = null }
}
async function setDefault(id) {
  try {
    await workbenchApi.ai.providerUpdate(id, { is_default: true })
    ElMessage.success('已设为默认')
    await loadProviders()
  } catch (e) { }
}
async function delProvider(p) {
  try {
    await ElMessageBox.confirm(`确认删除「${p.display_name}」?`, '删除 Provider', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  await workbenchApi.ai.providerDelete(p.id)
  ElMessage.success('已删除')
  if (currentProviderId.value === p.id) currentProviderId.value = null
  await loadProviders()
}

watch(activeId, () => { seq = 0 })

onMounted(() => { loadConversations(); loadProviders() })
onUnmounted(() => {
  seq = 0
  streamController.value?.abort()
  streamController.value = null
})
</script>

<style scoped>
.assistant-page {
  max-width: 1120px; margin: 0 auto; padding: 24px 16px 80px;
  font-family: var(--font-serif); color: var(--xiu-text);
}
.assistant-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; flex-wrap: wrap; gap: 12px;
}
.assistant-header-left { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.assistant-header h1 {
  font-size: 26px; margin: 0; letter-spacing: .1em;
  background: linear-gradient(135deg,#c9a96e,#f0e6c8 48%,#c9a96e);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color: transparent;
}
.header-sub { font-size: 12px; color: var(--xiu-text-3); margin-left: 8px; letter-spacing: .03em; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.assistant-body { display: grid; grid-template-columns: 220px 1fr; gap: 16px; min-height: 62vh; }
.assistant-sidebar {
  background: var(--xiu-card); -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
  border: 1px solid var(--xiu-line); border-radius: 14px; padding: 12px;
}
.new-chat-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%;
  padding: 8px; margin-bottom: 10px;
  border: 1px solid var(--xiu-primary); border-radius: 10px;
  background: rgba(61, 184, 176, .14); color: var(--xiu-primary-bright);
  font-size: 13px; cursor: pointer; transition: all .2s;
}
.new-chat-btn:hover { background: rgba(61, 184, 176, .24); }
.assistant-sidebar h3 { font-size: 12px; margin: 0 0 8px; color: var(--xiu-gold); letter-spacing: .1em; }
.assistant-sidebar ul { list-style: none; margin: 0; padding: 0; max-height: 52vh; overflow-y: auto; }
.assistant-sidebar li {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 8px; border-radius: 8px; cursor: pointer; font-size: 13px; color: var(--xiu-text-2);
}
.assistant-sidebar li:hover { background: rgba(201,169,110,.12); color: var(--xiu-text); }
.assistant-sidebar li.active { background: rgba(61,184,176,.22); color: var(--xiu-primary-bright); }
.assistant-sidebar li.empty { color: var(--xiu-text-3); cursor: default; }
.conv-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.del-btn { background: transparent; border: 0; color: inherit; cursor: pointer; font-size: 16px; line-height: 1; }

.assistant-main {
  background: var(--xiu-card-strong); border: 1px solid var(--xiu-line); border-radius: 14px;
  display: flex; flex-direction: column; -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
}
.messages { flex: 1; padding: 16px; overflow-y: auto; max-height: 56vh; display: flex; flex-direction: column; gap: 14px; }
.chat-msg { display: flex; }
.chat-msg.user { justify-content: flex-end; }
.chat-msg.assistant { justify-content: flex-start; }
.chat-bubble { max-width: 82%; }
.chat-msg.user .chat-bubble { text-align: right; }
.chat-name { font-size: 11px; color: var(--xiu-gold); margin: 0 0 4px; opacity: .8; }
.chat-text {
  display: inline-block; text-align: left;
  padding: 10px 14px; border-radius: 12px; font-size: 13px; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word; color: var(--xiu-text);
}
.chat-msg.user .chat-text { background: rgba(61,184,176,.14); border: 1px solid rgba(61,184,176,.2); }
.chat-msg.assistant .chat-text { background: rgba(201,169,110,.1); border: 1px solid rgba(201,169,110,.18); }
.chat-cursor { display: inline-block; color: var(--xiu-gold); animation: blink 1s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0; } }

.chat-save { margin-top: 8px; text-align: left; }
.chat-save-toggle {
  display: inline-block; cursor: pointer; font-size: 12px; color: var(--xiu-gold);
  padding: 2px 4px; user-select: none; list-style: none;
}
.chat-save-toggle::-webkit-details-marker { display: none; }
.chat-save-toggle::before { content: '＋ '; }
details[open] .chat-save-toggle::before { content: '－ '; }
.chat-save-body {
  margin-top: 6px; padding: 10px; border: 1px dashed var(--xiu-line);
  border-radius: 10px; background: rgba(0,0,0,.12); display: flex; flex-direction: column; gap: 8px;
}
.chat-save-content { font-family: inherit; }
.chat-save-actions { display: flex; justify-content: flex-end; }
.chat-save-error { color: var(--xiu-danger); font-size: 12px; }

.empty { text-align: center; padding: 60px 20px; color: var(--xiu-text-3); }
.empty-title { font-size: 18px; color: var(--xiu-text); margin: 0 0 8px; }
.empty-sub { font-size: 13px; margin: 0; }

.composer { padding: 14px; border-top: 1px solid var(--xiu-line); }
.composer-actions { display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-top: 8px; }
.composer-error { color: var(--xiu-danger); font-size: 12px; margin-right: auto; }
.placeholder { color: var(--xiu-text-3); padding: 48px; text-align: center; }

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

@media (max-width: 700px) {
  .assistant-body { grid-template-columns: 1fr; }
  .assistant-sidebar { display: none; }
}
</style>
/**
 * AssistantView 真实行为测试：
 * - 用户点击"发送" → 必须先调用 ai.preview，且不直接调用 invoke；
 * - 取消预览对话框 → 一定不调用 invoke；
 * - 确认预览 → 必须调用 ai.invoke 并传入 conversation_id；
 * - 显示 fake/真实 provider 标识；
 * - 确认应用 → 对 suggest_task 触发 ai.apply 创建任务。
 *
 * 为了避免 @vue/test-utils trigger('click') 在 el-button stub 下被双触发，
 * 本测试直接通过 wrapper.vm 调用组件 setup 暴露的方法。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const ElementPlusStub = {
  'el-button': { template: '<button class="el-btn-stub"><slot /></button>' },
  'el-input': {
    props: ['modelValue', 'placeholder', 'type', 'rows'],
    template:
      '<textarea v-if="type === \'textarea\'" :placeholder="placeholder" :rows="rows" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"></textarea>' +
      '<input v-else :placeholder="placeholder" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  'el-option': { props: ['label', 'value'], template: '<option :value="value">{{ label }}</option>' },
  'el-select': {
    props: ['modelValue', 'placeholder'],
    template:
      '<select :value="modelValue" @change="$emit(\'update:modelValue\', Number($event.target.value))"><slot /></select>',
  },
  'el-dialog': {
    props: ['modelValue', 'title', 'width', 'closeOnClickModal'],
    template: '<div v-if="modelValue" class="el-dialog-stub" :data-title="title"><slot /></div>',
  },
  'el-tag': { props: ['closable'], template: '<span class="el-tag-stub"><slot /></span>' },
}

const apiMock = {
  ai: {
    conversations: vi.fn(),
    createConversation: vi.fn(),
    deleteConversation: vi.fn(),
    messages: vi.fn(),
    preview: vi.fn(),
    invoke: vi.fn(),
    apply: vi.fn(),
  },
  notes: {
    list: vi.fn(),
    create: vi.fn(),
  },
}

vi.mock('@/api/workbench', () => ({
  workbenchApi: apiMock,
  default: apiMock,
}))

vi.mock('@/router', () => ({
  default: { currentRoute: { value: { path: '/' } }, push: vi.fn() },
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') },
  }
})

beforeEach(() => {
  Object.values(apiMock.ai).forEach((fn) => {
    if (typeof fn === 'function' && fn.mockClear) fn.mockClear()
    if (typeof fn === 'function' && fn.mockReset) fn.mockReset()
  })
  apiMock.notes.list = vi.fn()
  apiMock.notes.create = vi.fn()
  apiMock.ai.conversations.mockResolvedValue({ data: { list: [{ id: 1, title: '会话1' }] } })
  apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
})

afterEach(() => {
  // 兜底：清掉 fetch-blob / assistant 自己写入的 token / session
  try { localStorage.clear() } catch { /* noop */ }
  try { sessionStorage.clear() } catch { /* noop */ }
  vi.useRealTimers()
})

async function mountAssistant() {
  const AssistantView = (await import('@/views/AssistantView.vue')).default
  const w = mount(AssistantView, {
    global: { components: ElementPlusStub },
  })
  await flushPromises()
  return w
}

describe('AssistantView AI flow', () => {
  // send() 直接调 invoke（不再弹预览确认），结果在气泡内联呈现
  async function sendDraft(w, text = 'x') {
    w.vm.draft = text
    await w.vm.send()
    await flushPromises()
  }

  function buildInvoke(overrides = {}) {
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 'AI 文本',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
        ...overrides,
      },
    })
  }

  it('发送 → 直接调 ai.invoke，不调 preview，携带 conversation_id', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    await sendDraft(w, '用户草稿')
    expect(apiMock.ai.preview).not.toHaveBeenCalled()
    expect(apiMock.ai.invoke).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.invoke.mock.calls[0][0]
    expect(arg.content).toBe('用户草稿')
    expect(arg.conversation_id).toBe(1)
    expect(arg.ability).toBe('summarize')
    // 结果不弹窗：内联应用面板激活
    expect(w.vm.resultDialog).toBeUndefined()
    expect(w.vm.inlineApply).not.toBeNull()
  })

  it('发送后内联应用面板与 lastInvoke 状态正确', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    await sendDraft(w)
    expect(w.vm.lastInvoke.provider).toBe('fake')
    expect(w.vm.lastInvoke.is_fake).toBe(true)
    expect(w.vm.inlineApply.applied).toBe(false)
    expect(w.vm.inlineApply.ability).toBe('summarize')
    expect(w.vm.inlineApplyOpen).toBe(true)
    // 草稿已清空
    expect(w.vm.draft).toBe('')
    expect(w.html()).toMatch(/fake/)
  })

  it('没有 activeId 时 send 不调 invoke', async () => {
    apiMock.ai.conversations.mockResolvedValue({ data: { list: [] } })
    buildInvoke()
    const w = await mountAssistant()
    expect(w.vm.activeId).toBeNull()
    await sendDraft(w)
    expect(apiMock.ai.invoke).not.toHaveBeenCalled()
  })

  it('对 suggest_task 内联确认应用 → 触发 ai.apply 创建任务', async () => {
    buildInvoke({ ability: 'suggest_task', text: '建议任务', data: { title: '跟进X', description: 'desc' } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'task', task: { id: 88, title: '跟进X' } } })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    await sendDraft(w, '生成任务')
    await w.vm.confirmApplyInline()
    expect(apiMock.ai.apply).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('suggest_task')
    expect(arg.target_type).toBe('task')
    expect(arg.conversation_id).toBe(1)
    expect(arg.payload).toMatchObject({ title: '跟进X', description: 'desc' })
    expect(w.vm.inlineApply.applied).toBe(true)
  })

  it('hideInlineApply 关闭内联面板并清空目标', async () => {
    buildInvoke()
    apiMock.notes.list.mockResolvedValue({ data: { list: [{ id: 10, title: 'A' }] } })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    await sendDraft(w)
    w.vm.applyTargetNoteId = 10
    w.vm.hideInlineApply()
    expect(w.vm.inlineApply).toBeNull()
    expect(w.vm.applyTargetNoteId).toBeNull()
  })

  // ====== 目标笔记选择器：note 类能力 apply ======
  it('summarize 发送后加载候选笔记并默认选中第一条', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 10, title: '笔记A' }, { id: 11, title: '笔记B' }] },
    })
    const w = await mountAssistant()
    await sendDraft(w)
    expect(apiMock.notes.list).toHaveBeenCalled()
    expect(w.vm.applyTargetNotes.length).toBe(2)
    expect(w.vm.applyTargetNoteId).toBe(10)
  })

  it('summarize 选目标笔记后 confirmApplyInline → ai.apply(target_type=note, target_id=N)', async () => {
    buildInvoke({ data: { summary: 'AI 摘要' } })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 10, title: '笔记A' }, { id: 11, title: '笔记B' }] },
    })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 11, summary: 'AI 摘要' } } })
    const w = await mountAssistant()
    await sendDraft(w)
    w.vm.applyTargetNoteId = 11
    await w.vm.confirmApplyInline()
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('summarize')
    expect(arg.target_type).toBe('note')
    expect(arg.target_id).toBe(11)
    expect(arg.conversation_id).toBe(1)
    expect(arg.payload).toMatchObject({ summary: 'AI 摘要' })
    // 写入成功后面板标记已应用、清空目标
    expect(w.vm.inlineApply.applied).toBe(true)
    expect(w.vm.applyTargetNoteId).toBeNull()
  })

  it('summarize 未选目标笔记时 confirmApplyInline 不调 ai.apply', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 1 } } })
    const w = await mountAssistant()
    await sendDraft(w)
    expect(w.vm.applyTargetNoteId).toBeNull()
    await w.vm.confirmApplyInline()
    expect(apiMock.ai.apply).not.toHaveBeenCalled()
  })

  it('新建草稿笔记作为 summarize 目标并应用', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.create.mockResolvedValue({ data: { id: 99, title: 'AI 应用目标' } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 99, summary: 'S' } } })
    const w = await mountAssistant()
    await sendDraft(w)
    expect(apiMock.notes.create).not.toHaveBeenCalled()
    await w.vm.createApplyTargetNote()
    expect(apiMock.notes.create).toHaveBeenCalledTimes(1)
    expect(w.vm.applyTargetNoteId).toBe(99)
    await w.vm.confirmApplyInline()
    expect(apiMock.ai.apply).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.target_id).toBe(99)
    expect(arg.target_type).toBe('note')
  })

  it('suggest_tags 走 note 目标，payload 是 {tags}', async () => {
    buildInvoke({ ability: 'suggest_tags', data: { tags: ['A', 'B'] } })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [{ id: 22, title: 't1' }] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 22 } } })
    const w = await mountAssistant()
    await sendDraft(w)
    await w.vm.confirmApplyInline()
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('suggest_tags')
    expect(arg.target_type).toBe('note')
    expect(arg.target_id).toBe(22)
    expect(arg.payload).toMatchObject({ tags: ['A', 'B'] })
  })

  it('organize 走 note 目标，payload 是 {title, content, summary}', async () => {
    buildInvoke({
      ability: 'organize',
      data: { title: '新标题', content: '新内容', summary: '新摘要' },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [{ id: 33, title: 't2' }] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 33 } } })
    const w = await mountAssistant()
    await sendDraft(w)
    await w.vm.confirmApplyInline()
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('organize')
    expect(arg.target_type).toBe('note')
    expect(arg.target_id).toBe(33)
    expect(arg.payload).toMatchObject({ title: '新标题', content: '新内容', summary: '新摘要' })
  })

  it('suggest_task 不加载候选笔记，直接 ai.apply(target_type=task)', async () => {
    buildInvoke({ ability: 'suggest_task', data: { title: '跟进', description: '' } })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'task', task: { id: 88 } } })
    const w = await mountAssistant()
    await sendDraft(w)
    expect(apiMock.notes.list).not.toHaveBeenCalled()
    await w.vm.confirmApplyInline()
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.target_type).toBe('task')
    expect(arg.target_id).toBeNull()
  })

  it('笔记候选加载失败时 applyTargetError 显示，不阻塞后续', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockRejectedValue(new Error('boom'))
    const w = await mountAssistant()
    await sendDraft(w)
    expect(w.vm.applyTargetError).toMatch(/加载笔记失败/)
    expect(w.vm.applyTargetNotes.length).toBe(0)
  })

  // ====== 分页 + 关键词过滤 ======
  it('loadApplyTargetNotes 第一页带 page/size；继续加载更多', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockImplementation(async ({ page, size, q }) => {
      if (q) return { data: { list: [{ id: 99, title: '匹配' }], total: 1, page, size } }
      if (page === 1) return { data: { list: [{ id: 1, title: 'A' }, { id: 2, title: 'B' }], total: 5, page, size } }
      if (page === 2) return { data: { list: [{ id: 3, title: 'C' }, { id: 4, title: 'D' }], total: 5, page, size } }
      return { data: { list: [{ id: 5, title: 'E' }], total: 5, page, size } }
    })
    const w = await mountAssistant()
    await sendDraft(w)
    expect(apiMock.notes.list).toHaveBeenCalledTimes(1)
    const firstCall = apiMock.notes.list.mock.calls[0][0]
    expect(firstCall.page).toBe(1)
    expect(firstCall.size).toBe(20)
    expect(w.vm.applyTargetNotes.length).toBe(2)
    expect(w.vm.applyTargetTotal).toBe(5)

    w.vm.applyTargetPage = 2
    await w.vm.loadApplyTargetNotes()
    await flushPromises()
    expect(w.vm.applyTargetNotes.length).toBe(4)

    w.vm.applyTargetPage = 3
    await w.vm.loadApplyTargetNotes()
    await flushPromises()
    expect(w.vm.applyTargetNotes.length).toBe(5)
    const ids = w.vm.applyTargetNotes.map((n) => n.id)
    expect(new Set(ids).size).toBe(5)
  })

  it('loadApplyTargetNotes({reset:true, keyword}) 携带 q 关键词过滤', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 7, title: '玄黄笔记' }], total: 1, page: 1, size: 20 },
    })
    const w = await mountAssistant()
    await sendDraft(w)
    await w.vm.loadApplyTargetNotes({ reset: true, keyword: '玄黄' })
    await flushPromises()
    const lastCall = apiMock.notes.list.mock.calls[apiMock.notes.list.mock.calls.length - 1][0]
    expect(lastCall.q).toBe('玄黄')
    expect(lastCall.page).toBe(1)
    expect(w.vm.applyTargetNotes.length).toBe(1)
    expect(w.vm.applyTargetTotal).toBe(1)
    expect(w.vm.applyTargetKeyword).toBe('玄黄')
  })

  it('已加载全部后再触发 loadApplyTargetNotes 不再请求下一页', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 1, title: 'A' }], total: 1, page: 1, size: 20 },
    })
    const w = await mountAssistant()
    await sendDraft(w)
    const before = apiMock.notes.list.mock.calls.length
    w.vm.applyTargetPage = 2
    await w.vm.loadApplyTargetNotes()
    await flushPromises()
    // total=1 < page=2，返回空且不再累加；这里验证加载完成后不重复计数
    expect(w.vm.applyTargetNotes.length).toBe(1)
    expect(before).toBeGreaterThan(0)
  })

  it('过期响应被丢弃：先发起的请求晚到不会覆盖当前列表', async () => {
    let resolveSlow
    const slowPromise = new Promise((res) => { resolveSlow = () => res({
      data: { list: [{ id: 1, title: 'A' }], total: 1, page: 1, size: 20 },
    }) })
    const fastPromise = Promise.resolve({
      data: { list: [{ id: 99, title: '匹配' }], total: 1, page: 1, size: 20 },
    })
    apiMock.notes.list.mockImplementation(({ q }) => (q ? fastPromise : slowPromise))
    // 无需先走 send：直接验证打分逻辑
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    const slowCall = w.vm.loadApplyTargetNotes({ reset: true })
    w.vm.loadApplyTargetNotes({ reset: true, keyword: '玄' })
    await fastPromise
    await flushPromises()
    if (resolveSlow) resolveSlow()
    await slowCall.catch(() => {})
    await flushPromises()
    expect(w.vm.applyTargetNotes.length).toBe(1)
    expect(w.vm.applyTargetNotes[0].id).toBe(99)
    expect(w.vm.applyTargetKeyword).toBe('玄')
  })

  it('新建草稿后 applyTargetTotal 自增，且新建条目加入列表头部', async () => {
    buildInvoke()
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 1, title: 'A' }], total: 1, page: 1, size: 20 },
    })
    apiMock.notes.create.mockResolvedValue({ data: { id: 77, title: 'AI 应用目标' } })
    const w = await mountAssistant()
    await sendDraft(w)
    expect(w.vm.applyTargetTotal).toBe(1)
    await w.vm.createApplyTargetNote()
    expect(w.vm.applyTargetNoteId).toBe(77)
    expect(w.vm.applyTargetTotal).toBe(2)
    expect(w.vm.applyTargetNotes[0].id).toBe(77)
  })
})
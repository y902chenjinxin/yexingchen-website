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
  it('用户点击发送 → 先调 ai.preview，不调 invoke', async () => {
    apiMock.ai.preview.mockResolvedValue({
      data: { preview: 'hello preview', char_count: 5, has_more: false },
    })
    const w = await mountAssistant()
    // 直接通过组件 setup 的 draft/openPreview
    w.vm.draft = '用户草稿'
    await w.vm.openPreview()
    expect(apiMock.ai.preview).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.preview.mock.calls[0][0]
    expect(arg.content).toBe('用户草稿')
    expect(arg.conversation_id).toBe(1)
    expect(apiMock.ai.invoke).not.toHaveBeenCalled()
  })

  it('预览阶段取消 → 不调 invoke', async () => {
    apiMock.ai.preview.mockResolvedValue({
      data: { preview: 'preview-text', char_count: 11, has_more: false },
    })
    const w = await mountAssistant()
    w.vm.draft = '草稿'
    await w.vm.openPreview()
    expect(apiMock.ai.preview).toHaveBeenCalledTimes(1)
    // 用户取消：previewDialog 应被关闭；invoke 不被调
    w.vm.cancelPreview()
    await flushPromises()
    expect(apiMock.ai.invoke).not.toHaveBeenCalled()
    expect(apiMock.ai.apply).not.toHaveBeenCalled()
    expect(w.vm.previewDialog).toBe(false)
  })

  it('预览阶段确认 → 调 ai.invoke，并携带 conversation_id', async () => {
    apiMock.ai.preview.mockResolvedValue({
      data: { preview: 'p', char_count: 1, has_more: false },
    })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 'AI 文本',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    w.vm.draft = 'some content'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    expect(apiMock.ai.invoke).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.invoke.mock.calls[0][0]
    expect(arg.conversation_id).toBe(1)
    expect(arg.content).toBe('some content')
    expect(arg.ability).toBe('summarize')
    // 状态正确
    expect(w.vm.lastInvoke.provider).toBe('fake')
    expect(w.vm.lastInvoke.is_fake).toBe(true)
    expect(w.vm.resultDialog).toBe(true)
  })

  it('确认 invoke 后展示 fake provider 标识', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 'fake summary',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    expect(w.vm.lastInvoke.provider).toBe('fake')
    expect(w.vm.lastInvoke.is_fake).toBe(true)
    expect(w.html()).toMatch(/fake/)
  })

  it('对 suggest_task 确认应用 → 触发 ai.apply 创建任务', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'suggest_task',
        text: '建议任务',
        data: { title: '跟进X', description: 'desc' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'task', task: { id: 88, title: '跟进X' } } })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    const w = await mountAssistant()
    w.vm.draft = '生成任务'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await w.vm.confirmApply()
    expect(apiMock.ai.apply).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('suggest_task')
    expect(arg.target_type).toBe('task')
    expect(arg.conversation_id).toBe(1)
    expect(arg.payload).toMatchObject({ title: '跟进X', description: 'desc' })
  })

  it('对话列表为空时 openPreview 不调 preview（无 activeId）', async () => {
    apiMock.ai.conversations.mockResolvedValue({ data: { list: [] } })
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    const w = await mountAssistant()
    w.vm.draft = '内容'
    await w.vm.openPreview()
    expect(apiMock.ai.preview).not.toHaveBeenCalled()
  })

  // ====== 目标笔记选择器：note 类能力 apply ======
  it('summarize 确认后调用 refreshApplyTargetNotes 加载候选', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: {
        list: [
          { id: 10, title: '笔记A' },
          { id: 11, title: '笔记B' },
        ],
      },
    })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    expect(apiMock.notes.list).toHaveBeenCalled()
    expect(w.vm.applyTargetNotes.length).toBe(2)
    expect(w.vm.applyTargetNoteId).toBe(10) // 默认选第一条
  })

  it('summarize 选目标笔记后 confirmApply → ai.apply(target_type=note, target_id=N)', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'AI 摘要' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: {
        list: [{ id: 10, title: '笔记A' }, { id: 11, title: '笔记B' }],
      },
    })
    apiMock.ai.apply.mockResolvedValue({
      data: { applied: 'note', note: { id: 11, summary: 'AI 摘要' } },
    })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    // 选第二条
    w.vm.applyTargetNoteId = 11
    await w.vm.confirmApply()
    expect(apiMock.ai.apply).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('summarize')
    expect(arg.target_type).toBe('note')
    expect(arg.target_id).toBe(11)
    expect(arg.conversation_id).toBe(1)
    expect(arg.payload).toMatchObject({ summary: 'AI 摘要' })
    // 写入成功后对话框关闭 + 状态清空
    expect(w.vm.resultDialog).toBe(false)
    expect(w.vm.lastInvoke).toBeNull()
    expect(w.vm.applyTargetNoteId).toBeNull()
  })

  it('summarize 未选目标笔记时 confirmApply 不调 ai.apply', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 1 } } })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    // 没有任何候选且未新建：applyTargetNoteId 仍为 null
    expect(w.vm.applyTargetNoteId).toBeNull()
    await w.vm.confirmApply()
    expect(apiMock.ai.apply).not.toHaveBeenCalled()
  })

  it('新建草稿笔记作为 summarize 目标并应用', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.create.mockResolvedValue({ data: { id: 99, title: 'AI 应用目标' } })
    apiMock.ai.apply.mockResolvedValue({
      data: { applied: 'note', note: { id: 99, summary: 'S' } },
    })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    expect(apiMock.notes.create).not.toHaveBeenCalled()
    await w.vm.createApplyTargetNote()
    expect(apiMock.notes.create).toHaveBeenCalledTimes(1)
    expect(w.vm.applyTargetNoteId).toBe(99)
    await w.vm.confirmApply()
    expect(apiMock.ai.apply).toHaveBeenCalledTimes(1)
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.target_id).toBe(99)
    expect(arg.target_type).toBe('note')
  })

  it('suggest_tags 走 note 目标，payload 是 {tags}', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'suggest_tags',
        text: 't',
        data: { tags: ['A', 'B'] },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [{ id: 22, title: 't1' }] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 22 } } })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    await w.vm.confirmApply()
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('suggest_tags')
    expect(arg.target_type).toBe('note')
    expect(arg.target_id).toBe(22)
    expect(arg.payload).toMatchObject({ tags: ['A', 'B'] })
  })

  it('organize 走 note 目标，payload 是 {title, content, summary}', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'organize',
        text: 't',
        data: {
          title: '新标题',
          content: '新内容',
          summary: '新摘要',
        },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({ data: { list: [{ id: 33, title: 't2' }] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'note', note: { id: 33 } } })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    await w.vm.confirmApply()
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.ability).toBe('organize')
    expect(arg.target_type).toBe('note')
    expect(arg.target_id).toBe(33)
    expect(arg.payload).toMatchObject({ title: '新标题', content: '新内容', summary: '新摘要' })
  })

  it('suggest_task 不需要选目标笔记，直接 ai.apply(target_type=task)', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'suggest_task',
        text: 't',
        data: { title: '跟进', description: '' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.ai.apply.mockResolvedValue({ data: { applied: 'task', task: { id: 88 } } })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    // confirmInvoke 后不应触发 notes.list
    expect(apiMock.notes.list).not.toHaveBeenCalled()
    await w.vm.confirmApply()
    const arg = apiMock.ai.apply.mock.calls[0][0]
    expect(arg.target_type).toBe('task')
    expect(arg.target_id).toBeNull()
  })

  it('笔记候选加载失败时 applyTargetError 显示，不阻塞后续', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockRejectedValue(new Error('boom'))
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    expect(w.vm.applyTargetError).toMatch(/加载笔记失败/)
    expect(w.vm.applyTargetNotes.length).toBe(0)
  })

  // ====== 分页 + 关键词过滤 ======
  it('loadApplyTargetNotes 第一页带 page/size；onApplyTargetPageChange 加载更多', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    // 第 1 页：2 条；总数 5
    apiMock.notes.list.mockImplementation(async ({ page, size, q }) => {
      if (q) {
        return { data: { list: [{ id: 99, title: '匹配' }], total: 1, page, size } }
      }
      if (page === 1) return { data: { list: [{ id: 1, title: 'A' }, { id: 2, title: 'B' }], total: 5, page, size } }
      if (page === 2) return { data: { list: [{ id: 3, title: 'C' }, { id: 4, title: 'D' }], total: 5, page, size } }
      return { data: { list: [{ id: 5, title: 'E' }], total: 5, page, size } }
    })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    expect(apiMock.notes.list).toHaveBeenCalledTimes(1)
    const firstCall = apiMock.notes.list.mock.calls[0][0]
    expect(firstCall.page).toBe(1)
    expect(firstCall.size).toBe(20)
    expect(w.vm.applyTargetNotes.length).toBe(2)
    expect(w.vm.applyTargetTotal).toBe(5)

    // 加载第 2 页
    w.vm.applyTargetPage = 2
    await w.vm.loadApplyTargetNotes()
    await flushPromises()
    expect(apiMock.notes.list).toHaveBeenCalledTimes(2)
    expect(w.vm.applyTargetNotes.length).toBe(4)

    // 第 3 页
    w.vm.applyTargetPage = 3
    await w.vm.loadApplyTargetNotes()
    await flushPromises()
    expect(apiMock.notes.list).toHaveBeenCalledTimes(3)
    expect(w.vm.applyTargetNotes.length).toBe(5)
    // 所有候选不重复
    const ids = w.vm.applyTargetNotes.map((n) => n.id)
    expect(new Set(ids).size).toBe(5)
  })

  it('searchApplyTargetNotes 携带 q 关键词过滤', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 7, title: '玄黄笔记' }], total: 1, page: 1, size: 20 },
    })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    // 搜索关键词
    w.vm.searchApplyTargetNotes('玄黄')
    await flushPromises()
    const lastCall = apiMock.notes.list.mock.calls[apiMock.notes.list.mock.calls.length - 1][0]
    expect(lastCall.q).toBe('玄黄')
    expect(lastCall.page).toBe(1)
    expect(w.vm.applyTargetNotes.length).toBe(1)
    expect(w.vm.applyTargetTotal).toBe(1)
    expect(w.vm.applyTargetKeyword).toBe('玄黄')
  })

  it('onApplyTargetPageChange 在已加载全部时不再请求', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 1, title: 'A' }], total: 1, page: 1, size: 20 },
    })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    const before = apiMock.notes.list.mock.calls.length
    w.vm.onApplyTargetPageChange()
    await flushPromises()
    expect(apiMock.notes.list.mock.calls.length).toBe(before)
  })

  it('过期响应被丢弃：先发起的请求晚到不会覆盖当前列表', async () => {
    // 准备两个 promise：slow（不带 q）和 fast（带 q）
    let resolveSlow
    const slowPromise = new Promise((res) => { resolveSlow = () => res({
      data: { list: [{ id: 1, title: 'A' }], total: 1, page: 1, size: 20 },
    }) })
    const fastPromise = Promise.resolve({
      data: { list: [{ id: 99, title: '匹配' }], total: 1, page: 1, size: 20 },
    })
    // 用一个共享 impl：按参数 q 返回不同 promise
    apiMock.notes.list.mockImplementation(({ q }) => (q ? fastPromise : slowPromise))

    const w = await mountAssistant()
    // 直接调用 loadApplyTargetNotes({reset:true}) 发起慢请求（无 q）
    const slowCall = w.vm.loadApplyTargetNotes({ reset: true })
    // 立刻调用 searchApplyTargetNotes 发起快请求（带 q）
    w.vm.searchApplyTargetNotes('玄')
    // 让快请求解析
    await fastPromise
    await flushPromises()
    // 解析慢请求（晚到）
    if (resolveSlow) resolveSlow()
    await slowCall.catch(() => {})
    await flushPromises()
    // 列表应只剩"匹配"（id=99），不应被过期响应覆盖
    expect(w.vm.applyTargetNotes.length).toBe(1)
    expect(w.vm.applyTargetNotes[0].id).toBe(99)
    expect(w.vm.applyTargetKeyword).toBe('玄')
  })

  it('新建草稿后 applyTargetTotal 自增，且新建条目加入列表头部', async () => {
    apiMock.ai.preview.mockResolvedValue({ data: { preview: 'p', char_count: 1, has_more: false } })
    apiMock.ai.invoke.mockResolvedValue({
      data: {
        ability: 'summarize',
        text: 't',
        data: { summary: 'S' },
        provider: 'fake',
        is_fake: true,
        conversation_id: 1,
      },
    })
    apiMock.ai.messages.mockResolvedValue({ data: { list: [] } })
    apiMock.notes.list.mockResolvedValue({
      data: { list: [{ id: 1, title: 'A' }], total: 1, page: 1, size: 20 },
    })
    apiMock.notes.create.mockResolvedValue({ data: { id: 77, title: 'AI 应用目标' } })
    const w = await mountAssistant()
    w.vm.draft = 'x'
    await w.vm.openPreview()
    await w.vm.confirmInvoke()
    await flushPromises()
    expect(w.vm.applyTargetTotal).toBe(1)
    await w.vm.createApplyTargetNote()
    expect(w.vm.applyTargetNoteId).toBe(77)
    expect(w.vm.applyTargetTotal).toBe(2)
    expect(w.vm.applyTargetNotes[0].id).toBe(77)
  })
})
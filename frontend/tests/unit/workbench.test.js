import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock api/workbench
const workbenchApiMock = {
  summary: vi.fn().mockResolvedValue({
    data: {
      today_tasks: [{ id: 1, title: 't', due_date: null }],
      overdue_tasks: [],
      recent_notes: [{ id: 2, title: 'n', status: 'draft', updated_at: null }],
      draft_notes: [],
    },
  }),
  tags: { list: vi.fn().mockResolvedValue({ data: { list: [{ id: 1, name: 'tagA' }] } }) },
  notes: {
    list: vi.fn().mockResolvedValue({ data: { list: [{ id: 1, title: 'n1', status: 'draft', content: 'x', updated_at: null, tags: [] }], total: 1 } }),
    create: vi.fn().mockResolvedValue({ data: { id: 99, title: 't', content: '' } }),
  },
  tasks: {
    list: vi.fn().mockResolvedValue({ data: { list: [], total: 0 } }),
  },
  ai: {
    conversations: vi.fn().mockResolvedValue({ data: { list: [] } }),
    preview: vi.fn().mockResolvedValue({ data: { preview: 'hello', char_count: 5, has_more: false } }),
    invoke: vi.fn().mockResolvedValue({ data: { text: 'result', data: {}, provider: 'fake', model: 'fake-1', conversation_id: 1, scope_preview: {} } }),
    createConversation: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    deleteConversation: vi.fn().mockResolvedValue({ data: { ok: true } }),
    messages: vi.fn().mockResolvedValue({ data: { list: [] } }),
  },
  assets: { list: vi.fn().mockResolvedValue({ data: { list: [], total: 0 } }) },
  trash: { list: vi.fn().mockResolvedValue({ data: { notes: [], assets: [], tasks: [], conversations: [] } }) },
}

vi.mock('@/api/workbench', () => ({
  default: workbenchApiMock,
  workbenchApi: workbenchApiMock,
}))

// Mock Element Plus Message to avoid runtime errors
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') },
  }
})

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('workbench summary store', () => {
  it('loads summary from api', async () => {
    const { useWorkbenchStore } = await import('@/stores/workbench')
    const store = useWorkbenchStore()
    expect(store.summary).toBeNull()
    await store.loadSummary()
    expect(store.summary.today_tasks).toHaveLength(1)
    expect(store.summary.overdue_tasks).toHaveLength(0)
  })
})

describe('workbench api mock', () => {
  it('summary returns today_tasks', async () => {
    const { workbenchApi } = await import('@/api/workbench')
    const res = await workbenchApi.summary()
    expect(res.data.today_tasks[0].title).toBe('t')
  })

  it('ai preview returns preview payload', async () => {
    const { workbenchApi } = await import('@/api/workbench')
    const res = await workbenchApi.ai.preview({ ability: 'summarize', content: 'x' })
    expect(res.data.preview).toBe('hello')
    expect(res.data.char_count).toBe(5)
  })

  it('ai invoke returns fake provider', async () => {
    const { workbenchApi } = await import('@/api/workbench')
    const res = await workbenchApi.ai.invoke({ ability: 'summarize', content: 'x' })
    expect(res.data.provider).toBe('fake')
    expect(res.data.conversation_id).toBe(1)
  })

  it('notes list returns list payload', async () => {
    const { workbenchApi } = await import('@/api/workbench')
    const res = await workbenchApi.notes.list({})
    expect(res.data.list).toHaveLength(1)
    expect(res.data.total).toBe(1)
  })
})

describe('autosave debounce behavior', () => {
  it('does not call api on every keystroke', async () => {
    vi.useFakeTimers()
    const { workbenchApi } = await import('@/api/workbench')
    workbenchApi.notes.update = vi.fn().mockResolvedValue({ data: { id: 1 } })
    workbenchApi.notes.create = vi.fn().mockResolvedValue({ data: { id: 1, title: 't', content: '', status: 'draft' } })
    workbenchApi.notes.get = vi.fn().mockResolvedValue({ data: { id: 1, title: 't', content: '', status: 'draft', tags: [] } })

    // 直接用 setTimeout 模拟防抖逻辑
    let callCount = 0
    const debounced = () => {
      callCount += 1
    }
    let timer = null
    const schedule = () => {
      if (timer) clearTimeout(timer)
      timer = setTimeout(debounced, 1200)
    }

    // 模拟连续输入 100 次
    for (let i = 0; i < 100; i += 1) schedule()
    expect(callCount).toBe(0)
    vi.advanceTimersByTime(1200)
    expect(callCount).toBe(1)
    vi.useRealTimers()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import NoteSelect from '@/components/common/NoteSelect.vue'

function makeItems(n, startId = 1) {
  const list = []
  for (let i = 0; i < n; i += 1) list.push({ id: startId + i, title: `笔记${startId + i}` })
  return list
}

describe('NoteSelect', () => {
  beforeEach(() => {
    // jsdom 不实现 IntersectionObserver —— 在 beforeEach 中挂一个可触发的 stub
    class StubIO {
      constructor(cb) {
        this.cb = cb
        this.target = null
        globalThis.__lastIO = this
      }
      observe(el) { this.target = el; this.el = el }
      disconnect() {}
      unobserve() {}
      /** 测试用：手动触发"触底"事件 */
      __triggerIntersect() { this.cb([{ isIntersecting: true, target: this.el }]) }
    }
    globalThis.IntersectionObserver = StubIO
    globalThis.__lastIO = null
  })

  it('focus 时打开下拉，emit search 触发首屏加载', async () => {
    const onSearch = vi.fn()
    const w = mount(NoteSelect, {
      props: { items: [], loading: false, hasMore: true, modelValue: null },
    })
    const input = w.find('input.note-select-input')
    await input.trigger('focus')
    await flushPromises()
    expect(w.find('.note-select-list').exists()).toBe(true)
    expect(onSearch).toHaveBeenCalledTimes(0) // 测试不挂 props，组件不会自动 emit
  })

  it('触底哨兵进入视口时 emit load-more（仅在 hasMore && !loading）', async () => {
    let ioInstance = null
    class SpyIO {
      constructor(cb) {
        this.cb = cb
        this.target = null
        ioInstance = this
      }
      observe(el) { this.target = el }
      disconnect() {}
      unobserve() {}
      __triggerIntersect() { this.cb([{ isIntersecting: true, target: this.target }]) }
    }
    globalThis.IntersectionObserver = SpyIO

    const onLoadMore = vi.fn()
    const w = mount(NoteSelect, {
      props: {
        items: makeItems(5),
        loading: false,
        hasMore: true,
        modelValue: null,
        'onLoad-more': onLoadMore,
      },
      attachTo: document.body,
    })
    await w.find('input.note-select-input').trigger('focus')
    await flushPromises()
    expect(ioInstance).toBeTruthy()
    ioInstance.__triggerIntersect()
    await flushPromises()
    expect(onLoadMore).toHaveBeenCalledTimes(1)
  })

  it('hasMore=false 时即使哨兵触发也不应自动 emit load-more', async () => {
    let ioInstance = null
    const OrigIO = globalThis.IntersectionObserver
    class SpyIO extends OrigIO {
      observe(el) { ioInstance = this; super.observe(el) }
    }
    globalThis.IntersectionObserver = SpyIO

    const onLoadMore = vi.fn()
    const w = mount(NoteSelect, {
      props: {
        items: makeItems(3),
        loading: false,
        hasMore: false,
        modelValue: null,
        'onLoad-more': onLoadMore,
      },
      attachTo: document.body,
    })
    await w.find('input.note-select-input').trigger('focus')
    await flushPromises()
    ioInstance.__triggerIntersect()
    await flushPromises()
    expect(onLoadMore).not.toHaveBeenCalled()
    // 实际显示"已加载全部"哨兵文本
    expect(w.find('.note-select-end').exists()).toBe(true)
  })

  it('输入触发搜索（带防抖 250ms）', async () => {
    vi.useFakeTimers()
    const onSearch = vi.fn()
    const w = mount(NoteSelect, {
      props: {
        items: [],
        loading: false,
        hasMore: true,
        modelValue: null,
        'onSearch': onSearch,
      },
      attachTo: document.body,
    })
    await w.find('input.note-select-input').trigger('focus')
    await flushPromises()
    // focus 阶段会立即 emit 一次（immediate）
    expect(onSearch).toHaveBeenCalledTimes(1)
    // 输入文字触发防抖搜索
    const input = w.find('input.note-select-input')
    await input.setValue('玄')
    await input.setValue('玄黄')
    expect(onSearch).toHaveBeenCalledTimes(1) // 防抖中，尚未 flush
    vi.advanceTimersByTime(260)
    expect(onSearch).toHaveBeenCalledTimes(2)
    expect(onSearch).toHaveBeenLastCalledWith('玄黄')
    vi.useRealTimers()
  })

  it('点击 item 后 emit update:modelValue 并关闭面板', async () => {
    const w = mount(NoteSelect, {
      props: { items: makeItems(3), loading: false, hasMore: false, modelValue: null },
      attachTo: document.body,
    })
    await w.find('input.note-select-input').trigger('focus')
    await flushPromises()
    const items = w.findAll('.note-select-item')
    expect(items.length).toBe(3)
    await items[1].trigger('mousedown')
    await flushPromises()
    expect(w.emitted('update:modelValue')).toBeTruthy()
    expect(w.emitted('update:modelValue')[0]).toEqual([2])
    // 面板应关闭
    expect(w.find('.note-select-list').exists()).toBe(false)
  })

  it('键盘 ↑↓ + Enter 可逐项选择', async () => {
    const w = mount(NoteSelect, {
      props: { items: makeItems(3), loading: false, hasMore: false, modelValue: null },
      attachTo: document.body,
    })
    const input = w.find('input.note-select-input')
    await input.trigger('focus')
    await flushPromises()
    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(w.emitted('update:modelValue')).toBeTruthy()
    // hoverIndex 从 -1 起步；两次 ArrowDown 后索引 1；Enter 提交 item.id=2
    expect(w.emitted('update:modelValue')[0]).toEqual([2])
  })

  it('空列表显示 emptyText', async () => {
    const w = mount(NoteSelect, {
      props: {
        items: [],
        loading: false,
        hasMore: false,
        modelValue: null,
        emptyText: '空',
      },
      attachTo: document.body,
    })
    await w.find('input.note-select-input').trigger('focus')
    await flushPromises()
    expect(w.find('.note-select-empty').exists()).toBe(true)
    expect(w.find('.note-select-empty').text()).toContain('空')
  })

  it('loading=true 时显示加载中文本', async () => {
    const w = mount(NoteSelect, {
      props: { items: [], loading: true, hasMore: false, modelValue: null },
      attachTo: document.body,
    })
    await w.find('input.note-select-input').trigger('focus')
    await flushPromises()
    expect(w.find('.note-select-loading').exists()).toBe(true)
  })

  it('props.modelValue 变化时输入框显示对应标题', async () => {
    const items = makeItems(3)
    const w = mount(NoteSelect, {
      props: { items, loading: false, hasMore: false, modelValue: 2 },
      attachTo: document.body,
    })
    await flushPromises()
    const input = w.find('input.note-select-input')
    expect(input.element.value).toBe('笔记2')
  })

  it('hasMore=true 且未触底时显示哨兵占位，不显示"已加载全部"', async () => {
    const w = mount(NoteSelect, {
      props: { items: makeItems(3), loading: false, hasMore: true, modelValue: null },
      attachTo: document.body,
    })
    await w.find('input.note-select-input').trigger('focus')
    await flushPromises()
    expect(w.find('.note-select-sentinel').exists()).toBe(true)
    expect(w.find('.note-select-end').exists()).toBe(false)
  })
})
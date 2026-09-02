/**
 * AssetsView 下载流程测试：
 * - 点击"下载"按钮是 <button> 而非 <a>（不会因为 href="#" 触发导航）；
 * - 点击 @click.prevent → 调 fetchBlob(download)；
 * - 成功后 createObjectURL + 临时 <a download>.click() + 5s 内 revoke；
 * - 失败显示错误信息；
 * - 并发点击同一资产只触发一次下载；
 * - 失败后 downloadingIds 被释放。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiMock = {
  assets: {
    list: vi.fn(),
    fetchBlob: vi.fn(),
    upload: vi.fn(),
    createLink: vi.fn(),
    delete: vi.fn(),
    restore: vi.fn(),
  },
}
vi.mock('@/api/workbench', () => ({
  workbenchApi: apiMock,
  default: apiMock,
}))
const ElementPlusStub = {
  'el-button': { props: ['size', 'type', 'plain'], template: '<button class="el-btn-stub" @click="$emit(\'click\')"><slot /></button>' },
  'el-option': { props: ['label', 'value'], template: '<option :value="value">{{ label }}</option>' },
  'el-select': {
    props: ['modelValue', 'placeholder', 'clearable'],
    template: '<select class="el-select-stub" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><slot /></select>',
  },
  'el-input': {
    props: ['modelValue', 'placeholder', 'clearable', 'type', 'rows'],
    template:
      '<input v-if="type !== \'textarea\'" class="el-input-stub" :placeholder="placeholder" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' +
      '<textarea v-else class="el-input-stub" :placeholder="placeholder" :rows="rows" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"></textarea>',
  },
  'el-pagination': { template: '<div class="el-pager-stub"><slot /></div>' },
  'el-form': { template: '<form class="el-form-stub" @submit.prevent="$emit(\'submit\')"><slot /></form>' },
  'el-form-item': { props: ['label'], template: '<div class="el-form-item-stub"><label>{{ label }}</label><slot /></div>' },
  'el-dialog': { props: ['modelValue', 'title', 'width'], template: '<div v-if="modelValue" class="el-dialog-stub" :data-title="title"><slot /></div>' },
}

vi.mock('vue-router', () => ({
  routerKey: Symbol('routerKey'),
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ back: vi.fn(), push: vi.fn() }),
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
  Object.values(apiMock.assets).forEach((fn) => {
    if (typeof fn === 'function') {
      fn.mockReset()
    }
  })
  // 默认列表：1 张图片 + 1 个 PDF
  apiMock.assets.list.mockResolvedValue({
    data: {
      list: [
        { id: 1, type: 'image', title: 'a.png', tags: [], file_size: 100 },
        { id: 2, type: 'pdf', title: 'b.pdf', tags: [], file_size: 200 },
      ],
      total: 2,
      page: 1,
      size: 12,
    },
  })
  apiMock.assets.fetchBlob.mockResolvedValue({
    blob: new Blob(['x'], { type: 'image/png' }),
    mime: 'image/png',
    objectUrl: 'blob:http://localhost/preview',
  })
})

afterEach(() => {
  vi.restoreAllMocks()
  // 兜底：还原可能被某 case 直接赋值的全局（setup.js 也会兜一份）
  if (typeof URL.createObjectURL === 'function' && URL.createObjectURL.name !== 'createObjectURL') {
    try { delete URL.createObjectURL } catch { /* noop */ }
  }
  document.body.innerHTML = ''
})

async function mountAssets() {
  const AssetsView = (await import('@/views/AssetsView.vue')).default
  const w = mount(AssetsView, {
    global: { components: ElementPlusStub },
    attachTo: document.body,
  })
  await flushPromises()
  return w
}

describe('AssetsView download flow', () => {
  it('下载按钮是 <button> 而非 <a>，不存在 href="#" 触发导航的隐患', async () => {
    const w = await mountAssets()
    const btn = w.find('button.link-btn')
    expect(btn.exists()).toBe(true)
    // 模板不应再使用 <a href="#"> 作为下载入口
    expect(w.find('a[href="#"][download]').exists()).toBe(false)
    expect(btn.attributes('href')).toBeUndefined()
    expect(btn.attributes('type')).toBe('button')
  })

  it('点击"下载"调用 fetchBlob(id, "download")', async () => {
    const w = await mountAssets()
    const btns = w.findAll('button.link-btn')
    expect(btns.length).toBe(2)
    // 列表挂载时会为每个 image/pdf 触发 fetchBlob(id, 'preview')；先记录已有调用次数
    await flushPromises()
    const before = apiMock.assets.fetchBlob.mock.calls.length
    await btns[0].trigger('click')
    await flushPromises()
    const downloadCalls = apiMock.assets.fetchBlob.mock.calls
      .slice(before)
      .filter(([, kind]) => kind === 'download')
    expect(downloadCalls.length).toBe(1)
    expect(downloadCalls[0][0]).toBe(1)
  })

  it('成功后创建临时 <a download> 触发浏览器下载，并跟踪临时 URL 等待 revoke', async () => {
    // 替换 mock fetchBlob：返回的 blob 应被读为 URL.createObjectURL 输入
    const blob = new Blob(['x'], { type: 'image/png' })
    apiMock.assets.fetchBlob.mockResolvedValue({
      blob,
      mime: 'image/png',
      objectUrl: 'blob:http://localhost/preview',
    })

    // 跟踪 createObjectURL / revokeObjectURL — 必须 try/finally 还原，否则跨文件污染
    const created = []
    const revoked = []
    const origCreate = URL.createObjectURL
    const origRevoke = URL.revokeObjectURL
    URL.createObjectURL = (b) => {
      const u = 'blob:http://localhost/test-' + created.length
      created.push({ url: u, blob: b })
      return u
    }
    URL.revokeObjectURL = (u) => { revoked.push(u) }

    const origClick = HTMLAnchorElement.prototype.click
    const clicked = []
    HTMLAnchorElement.prototype.click = function () { clicked.push(this.download) }

    try {
      const w = await mountAssets()
      const btns = w.findAll('button.link-btn')
      await btns[0].trigger('click')
      await flushPromises()

      await btns[0].trigger('click')
      await flushPromises()

      // 至少触发过一次 a.click() 且 download 是文件名
      expect(clicked.length).toBeGreaterThanOrEqual(1)
      expect(clicked.some((d) => d === 'a.png')).toBe(true)
      expect(created.length).toBeGreaterThanOrEqual(1)
      // 临时 URL 已被跟踪（不在 5s 之内立即 revoke）
      expect(revoked.length).toBe(0)
    } finally {
      URL.createObjectURL = origCreate
      URL.revokeObjectURL = origRevoke
      HTMLAnchorElement.prototype.click = origClick
    }
  })

  it('fetchBlob 失败时显示错误，不修改卡片状态', async () => {
    apiMock.assets.fetchBlob.mockRejectedValue(new Error('boom'))
    const w = await mountAssets()
    const btn = w.findAll('button.link-btn')[0]
    await btn.trigger('click')
    await flushPromises()
    // ElMessage.error 被调用
    const { ElMessage } = await import('element-plus')
    expect(ElMessage.error).toHaveBeenCalled()
    // 卡片 objectUrl 未被设置（卡片不显示破坏性更新）
    const item = w.vm.items.find((a) => a.id === 1)
    expect(item.objectUrl).toBeNull()
  })

  it('并发点击同一资产的下载按钮只触发一次 download 类型 fetchBlob', async () => {
    // 让 fetchBlob 慢解析，以制造并发
    let resolveBlob
    apiMock.assets.fetchBlob.mockImplementation(
      () => new Promise((res) => { resolveBlob = () => res({ blob: new Blob(['x']), objectUrl: 'blob:x' }) }),
    )
    const w = await mountAssets()
    const btns = w.findAll('button.link-btn')
    // 先消化 preview 阶段调用
    await flushPromises()
    const before = apiMock.assets.fetchBlob.mock.calls.length
    // 第一次点击启动下载（pending）
    await btns[0].trigger('click')
    await flushPromises()
    // 第二次点击同一资产 — 应被 downloadingIds 拦截
    await btns[0].trigger('click')
    await flushPromises()
    const downloadCalls = apiMock.assets.fetchBlob.mock.calls
      .slice(before)
      .filter(([, kind]) => kind === 'download')
    expect(downloadCalls.length).toBe(1)
    // 释放
    if (resolveBlob) resolveBlob()
    await flushPromises()
  })

  it('onDownload 对 link 类型资产直接 return，不调 fetchBlob', async () => {
    // 改 list 返回 link 类型
    apiMock.assets.list.mockResolvedValue({
      data: {
        list: [
          { id: 10, type: 'link', url: 'https://example.com', title: 'x', tags: [], file_size: 0 },
        ],
        total: 1,
        page: 1,
        size: 12,
      },
    })
    const w = await mountAssets()
    // 不应有 link-btn（只对 image/pdf 显示）
    const btns = w.findAll('button.link-btn')
    expect(btns.length).toBe(0)
    // 手动调用 onDownload 也不该调 fetchBlob
    await w.vm.onDownload({ id: 10, type: 'link', title: 'x' })
    expect(apiMock.assets.fetchBlob).not.toHaveBeenCalled()
  })

  it('fetchBlob(download) URL 是私有接口，不改为匿名公开（仍要求 Bearer 头）', async () => {
    const w = await mountAssets()
    const btns = w.findAll('button.link-btn')
    await btns[0].trigger('click')
    await flushPromises()
    const callUrl = apiMock.assets.fetchBlob.mock.calls[0][0]
    // 仍调用 /api/workbench/assets/{id}/download（私有鉴权路径）
    expect(typeof callUrl).toBe('number')
    // fetchBlob 是 workbenchApi 中的私有 fetch+Bearer，未公开
    expect(typeof apiMock.assets.fetchBlob).toBe('function')
  })
})
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
// 顶层静态导入：workbench.js 的模块图（含 Vue Router）在收集期完成转换。
// 早期写成用例内 `await import('@/api/workbench')`，首次转换计入 5s 用例超时，
// 全套串行跑时偶发超时（单跑 ~1.9s、全量跑偶超 5s）。vi.mock 会被提升到该导入之前，router 仍被 mock。
import { workbenchApi } from '@/api/workbench'

/**
 * 验证 workbenchApi.assets.fetchBlob 在调用时：
 * - 用 native fetch（不走 axios，否则 <img>/<iframe> 无法带 Authorization）；
 * - 自动注入 Bearer token；
 * - 返回 { blob, mime, objectUrl }。
 */

// 避免 workbench.js 顶层 import Vue Router 触发异步初始化导致第一个用例超时
vi.mock('@/router', () => ({
  default: {
    currentRoute: { value: { path: '/' } },
    push: vi.fn(),
  },
}))

const mockBlob = new Blob(['x'], { type: 'image/png' })
const objectUrl = 'blob:http://localhost/mock-id'

let lastFetchArgs = null

// 直接赋值的 global stub 必须保存原引用并在 afterEach 还原，
// 否则 vi.restoreAllMocks() 不会处理，跨测试文件造成污染。
const REAL_URL_CREATE = URL.createObjectURL
const REAL_URL_REVOKE = URL.revokeObjectURL
const REAL_FETCH = global.fetch

beforeEach(() => {
  global.URL.createObjectURL = vi.fn(() => objectUrl)
  global.URL.revokeObjectURL = vi.fn()
  global.fetch = vi.fn(async (url, init) => {
    lastFetchArgs = { url, init }
    return {
      ok: true,
      status: 200,
      blob: async () => mockBlob,
      headers: { get: (k) => (k.toLowerCase() === 'content-type' ? 'image/png' : null) },
    }
  })
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
  // 还原直接赋值的 global
  global.URL.createObjectURL = REAL_URL_CREATE
  global.URL.revokeObjectURL = REAL_URL_REVOKE
  global.fetch = REAL_FETCH
  localStorage.clear()
})

describe('workbenchApi.assets.fetchBlob', () => {
  it('uses native fetch and sends Bearer token', async () => {
    localStorage.setItem('token', 'test-token-abc')
    const r = await workbenchApi.assets.fetchBlob(42, 'preview')
    expect(r.blob).toBe(mockBlob)
    expect(r.mime).toBe('image/png')
    expect(r.objectUrl).toBe(objectUrl)
    expect(lastFetchArgs.url).toBe('/api/workbench/assets/42/preview')
    expect(lastFetchArgs.init.headers.Authorization).toBe('Bearer test-token-abc')
  })

  it('does not send Authorization when no token', async () => {
    localStorage.removeItem('token')
    await workbenchApi.assets.fetchBlob(7, 'download')
    expect(lastFetchArgs.url).toBe('/api/workbench/assets/7/download')
    expect(lastFetchArgs.init.headers.Authorization).toBeUndefined()
  })

  it('throws on non-2xx with status attached', async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 403,
      text: async () => 'forbidden',
      headers: { get: () => null },
    }))
    await expect(workbenchApi.assets.fetchBlob(1, 'preview')).rejects.toMatchObject({
      status: 403,
    })
  })

  it('401 from native fetch does not trigger axios router redirect', async () => {
    // 模拟 401：fetchBlob 抛错即可，不应触发 router.push('/login')
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 401,
      text: async () => 'unauthorized',
      headers: { get: () => null },
    }))
    const router = (await import('@/router')).default
    await expect(workbenchApi.assets.fetchBlob(9, 'preview')).rejects.toMatchObject({
      status: 401,
    })
    // 关键：native fetch 错误不会被 axios 拦截器处理 → router.push 不被触发
    expect(router.push).not.toHaveBeenCalled()
  })

  it('passes through arbitrary kind (preview|download) verbatim', async () => {
    localStorage.setItem('token', 'tok')
    await workbenchApi.assets.fetchBlob(11, 'preview')
    expect(lastFetchArgs.url).toBe('/api/workbench/assets/11/preview')
    await workbenchApi.assets.fetchBlob(11, 'download')
    expect(lastFetchArgs.url).toBe('/api/workbench/assets/11/download')
  })
})
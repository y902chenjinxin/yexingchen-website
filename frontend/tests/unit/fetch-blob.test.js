import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

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
    const { workbenchApi } = await import('@/api/workbench')
    const r = await workbenchApi.assets.fetchBlob(42, 'preview')
    expect(r.blob).toBe(mockBlob)
    expect(r.mime).toBe('image/png')
    expect(r.objectUrl).toBe(objectUrl)
    expect(lastFetchArgs.url).toBe('/api/workbench/assets/42/preview')
    expect(lastFetchArgs.init.headers.Authorization).toBe('Bearer test-token-abc')
  })

  it('does not send Authorization when no token', async () => {
    localStorage.removeItem('token')
    const { workbenchApi } = await import('@/api/workbench')
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
    const { workbenchApi } = await import('@/api/workbench')
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
    const { workbenchApi } = await import('@/api/workbench')
    await expect(workbenchApi.assets.fetchBlob(9, 'preview')).rejects.toMatchObject({
      status: 401,
    })
    // 关键：native fetch 错误不会被 axios 拦截器处理 → router.push 不被触发
    expect(router.push).not.toHaveBeenCalled()
  })

  it('passes through arbitrary kind (preview|download) verbatim', async () => {
    localStorage.setItem('token', 'tok')
    const { workbenchApi } = await import('@/api/workbench')
    await workbenchApi.assets.fetchBlob(11, 'preview')
    expect(lastFetchArgs.url).toBe('/api/workbench/assets/11/preview')
    await workbenchApi.assets.fetchBlob(11, 'download')
    expect(lastFetchArgs.url).toBe('/api/workbench/assets/11/download')
  })
})
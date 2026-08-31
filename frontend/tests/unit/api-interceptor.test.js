/**
 * axios 响应拦截器测试
 * 验证已取消的请求（ERR_CANCELED）不弹 ElMessage 错误
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mocks = vi.hoisted(() => {
  return {
    elMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
    router: { push: vi.fn(), currentRoute: { value: { path: '/login' } } }
  }
})

vi.mock('element-plus', () => ({ ElMessage: mocks.elMessage }))
vi.mock('@/router', () => ({ default: mocks.router }))

import api from '@/api/index.js'

describe('axios response interceptor - cancelled requests', () => {
  let rejectedHandler

  beforeEach(() => {
    mocks.elMessage.error.mockClear()
    mocks.router.push.mockClear()
    localStorage.clear()
    rejectedHandler = api.interceptors.response.handlers[0].rejected
  })

  async function runHandler(err) {
    try {
      await rejectedHandler(err)
    } catch {
      // swallow rejection to inspect mock calls
    }
  }

  it('已取消请求（ERR_CANCELED）不应弹错误提示', async () => {
    await runHandler({ code: 'ERR_CANCELED', message: 'canceled' })
    expect(mocks.elMessage.error).not.toHaveBeenCalled()
  })

  it('已取消请求（CanceledError name）不应弹错误提示', async () => {
    await runHandler({ name: 'CanceledError', message: 'canceled' })
    expect(mocks.elMessage.error).not.toHaveBeenCalled()
  })

  it('网络错误（ERR_NETWORK）应弹错误提示', async () => {
    await runHandler({ code: 'ERR_NETWORK', message: 'Network Error' })
    expect(mocks.elMessage.error).toHaveBeenCalledWith('网络错误，请检查连接')
  })

  it('401 应清除 token 并跳 /login（当前在 /home）', async () => {
    mocks.router.currentRoute.value.path = '/home'
    localStorage.setItem('token', 'fake')
    await runHandler({ response: { status: 401, data: { detail: 'unauthorized' } } })
    expect(localStorage.getItem('token')).toBeNull()
    expect(mocks.router.push).toHaveBeenCalledWith('/login')
    mocks.router.currentRoute.value.path = '/login'  // reset
  })

  it('401 当前已在 /login，不应重复跳转', async () => {
    mocks.router.currentRoute.value.path = '/login'
    await runHandler({ response: { status: 401, data: { detail: 'unauthorized' } } })
    expect(mocks.router.push).not.toHaveBeenCalled()
  })
})

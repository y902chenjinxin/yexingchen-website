/**
 * 路由守卫测试
 * 验证 routeGuard 函数的正确性
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

const mockAuth = {
  isLoggedIn: false,
  isSuperAdmin: false,
  token: '',
  user: null
}

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => mockAuth
}))

import { routeGuard } from '@/router/guards'

describe('routeGuard', () => {
  beforeEach(() => {
    mockAuth.isLoggedIn = false
    mockAuth.isSuperAdmin = false
  })

  function makeTo(path, meta = {}) {
    return { path, meta, fullPath: path, params: {}, query: {} }
  }

  it('未登录访问 /workbench 应跳 /login', async () => {
    mockAuth.isLoggedIn = false
    const next = vi.fn()
    await routeGuard(makeTo('/workbench', { requiresAuth: true }), makeTo('/'), next)
    expect(next).toHaveBeenCalledWith('/login')
  })

  it('已登录访问 /login 应跳 /home（修复死代码 bug）', async () => {
    mockAuth.isLoggedIn = true
    const next = vi.fn()
    await routeGuard(makeTo('/login', { requiresAuth: false }), makeTo('/'), next)
    expect(next).toHaveBeenCalledWith('/home')
  })

  it('未登录访问 /login 应放行', async () => {
    mockAuth.isLoggedIn = false
    const next = vi.fn()
    await routeGuard(makeTo('/login', { requiresAuth: false }), makeTo('/'), next)
    expect(next).toHaveBeenCalledWith()
  })

  it('已登录普通用户访问 /admin 应跳 /home', async () => {
    mockAuth.isLoggedIn = true
    mockAuth.isSuperAdmin = false
    const next = vi.fn()
    await routeGuard(makeTo('/admin', { requiresAuth: true, role: 'super_admin' }), makeTo('/'), next)
    expect(next).toHaveBeenCalledWith('/home')
  })

  it('已登录 super_admin 访问 /admin 应放行', async () => {
    mockAuth.isLoggedIn = true
    mockAuth.isSuperAdmin = true
    const next = vi.fn()
    await routeGuard(makeTo('/admin', { requiresAuth: true, role: 'super_admin' }), makeTo('/'), next)
    expect(next).toHaveBeenCalledWith()
  })

  it('已登录访问 /workbench 应放行', async () => {
    mockAuth.isLoggedIn = true
    const next = vi.fn()
    await routeGuard(makeTo('/workbench', { requiresAuth: true }), makeTo('/'), next)
    expect(next).toHaveBeenCalledWith()
  })
})

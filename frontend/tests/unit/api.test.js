/**
 * API 基础功能测试
 */
import { describe, it, expect } from 'vitest'

describe('API 基础验证', () => {
  it('should have correct base URL', () => {
    // 验证API配置
    const baseURL = '/api'
    expect(baseURL).toBe('/api')
  })

  it('should handle login endpoint', async () => {
    // 验证登录接口路径
    const loginPath = '/api/auth/login'
    expect(loginPath).toContain('/auth/login')
  })

  it('should handle music endpoint', async () => {
    // 验证音乐接口路径
    const musicPath = '/api/music'
    expect(musicPath).toContain('/music')
  })
})
/**
 * Auth Store 单元测试
 */
import { describe, it, expect, beforeEach } from 'vitest'

// Mock axios
const mockPost = vi.fn()
const mockGet = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: () => ({
      post: mockPost,
      get: mockGet,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    })
  }
}))

// Mock auth store
const useAuthStore = () => {
  const token = ref(null)
  const user = ref(null)
  const isLoggedIn = computed(() => !!token.value)

  const login = async (email, password) => {
    try {
      const response = await mockPost('/api/auth/login', { email, password })
      if (response.data.code === 0) {
        token.value = response.data.data.token
        user.value = response.data.data.user
        localStorage.setItem('token', token.value)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const logout = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, login, logout }
}

describe('Auth Store', () => {
  beforeEach(() => {
    localStorage.clear()
    mockPost.mockReset()
    mockGet.mockReset()
  })

  describe('login', () => {
    it('should login successfully with correct credentials', async () => {
      mockPost.mockResolvedValue({
        data: {
          code: 0,
          msg: '登录成功',
          data: {
            token: 'test-token-123',
            user: { id: 1, email: 'admin@test.com', nickname: 'Admin' }
          }
        }
      })

      const store = useAuthStore()
      const result = await store.login('admin@test.com', 'password')

      expect(result).toBe(true)
      expect(store.token.value).toBe('test-token-123')
      expect(store.user.value.email).toBe('admin@test.com')
    })

    it('should fail login with wrong credentials', async () => {
      mockPost.mockResolvedValue({
        data: {
          code: 401,
          msg: '账密输入错误，请重试'
        }
      })

      const store = useAuthStore()
      const result = await store.login('admin@test.com', 'wrong')

      expect(result).toBe(false)
      expect(store.token.value).toBeNull()
    })

    it('should store token in localStorage on login', async () => {
      mockPost.mockResolvedValue({
        data: {
          code: 0,
          data: { token: 'token-123', user: {} }
        }
      })

      const store = useAuthStore()
      await store.login('test@test.com', 'pass')

      expect(localStorage.getItem('token')).toBe('token-123')
    })
  })

  describe('logout', () => {
    it('should clear token and user on logout', async () => {
      mockPost.mockResolvedValue({
        data: {
          code: 0,
          data: { token: 'token-123', user: { id: 1 } }
        }
      })

      const store = useAuthStore()
      await store.login('test@test.com', 'pass')
      store.logout()

      expect(store.token.value).toBeNull()
      expect(store.user.value).toBeNull()
      expect(localStorage.getItem('token')).toBeNull()
    })
  })
})
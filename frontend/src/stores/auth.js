import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getMe, logout as logoutApi, updateMe as updateMeApi, changePassword as changePasswordApi, extendToken as extendTokenApi } from '@/api/auth'
import { isTokenValid, getTokenExpiresIn } from '@/utils/token'

// 剩余有效期不足该秒数（24h）时触发滑动续期
const EXTEND_THRESHOLD = 24 * 60 * 60

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value && isTokenValid(token.value))
  const isSuperAdmin = computed(() => user.value?.is_super_admin === 1)

  async function loginAction(email, password) {
    const res = await loginApi(email, password)
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('token', token.value)
    return res
  }

  async function fetchUser() {
    if (!token.value || !isTokenValid(token.value)) {
      token.value = ''
      user.value = null
      localStorage.removeItem('token')
      return
    }
    try {
      const res = await getMe()
      user.value = res.data
    } catch {
      token.value = ''
      user.value = null
      localStorage.removeItem('token')
    }
  }

  async function updateMe(data) {
    return await updateMeApi(data)
  }

  async function changePassword(oldPassword, newPassword) {
    return await changePasswordApi(oldPassword, newPassword)
  }

  function logoutAction() {
    try {
      logoutApi()
    } catch {
      // 忽略登出API错误
    }
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  // 滑动续期：距过期不足阈值时调用 /auth/extend 换取新 token，保持登录不掉线
  function scheduleExtend() {
    const t = token.value
    if (!t) return
    const left = getTokenExpiresIn(t)
    if (left <= 0) return
    // 剩余有效期不足下方秒数才续期，避免频繁请求
    if (left > EXTEND_THRESHOLD) return
    extendTokenApi()
      .then((res) => {
        if (res?.data?.token) {
          token.value = res.data.token
          localStorage.setItem('token', res.data.token)
        }
      })
      .catch(() => {
        // 续期失败（网络/服务异常）：保留旧 token，下次定时再试
      })
  }

  return { token, user, isLoggedIn, isSuperAdmin, loginAction, fetchUser, logoutAction, updateMe, changePassword, scheduleExtend }
})
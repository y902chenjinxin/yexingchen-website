import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getMe, logout as logoutApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const isSuperAdmin = computed(() => user.value?.is_super_admin === 1)

  async function loginAction(email, password) {
    const res = await loginApi(email, password)
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('token', token.value)
    return res
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await getMe()
      user.value = res.data
    } catch {
      // token无效，只清除本地状态，不调用logoutAPI（避免401错误）
      token.value = ''
      user.value = null
      localStorage.removeItem('token')
    }
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

  return { token, user, isLoggedIn, isSuperAdmin, loginAction, fetchUser, logoutAction }
})
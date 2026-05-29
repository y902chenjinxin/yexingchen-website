import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getMe, logout as logoutApi, updateMe as updateMeApi } from '@/api/auth'

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
      token.value = ''
      user.value = null
      localStorage.removeItem('token')
    }
  }

  async function updateMe(data) {
    return await updateMeApi(data)
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

  return { token, user, isLoggedIn, isSuperAdmin, loginAction, fetchUser, logoutAction, updateMe }
})
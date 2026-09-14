/**
 * 统一 axios 工厂：消除各 api/*.js 重复的拦截器代码。
 *
 * 用法：const api = createApi({ baseURL: '/api', ... })
 * - 401：清 token + 跳 /login
 * - 403/404：弹 ElMessage
 * - 其他：弹后端 detail.msg / 通用"网络错误"
 * - 各 api 文件可在自己 response 拦截器里追加专属逻辑
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

export function createApi({ baseURL = '/api', timeout = 30000, ...rest } = {}) {
  const api = axios.create({
    baseURL,
    timeout,
    headers: { 'Content-Type': 'application/json' },
    ...rest,
  })

  // 请求：自动注入 Bearer token
  api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  // 响应：401 跳登录；其他 status 弹 ElMessage
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response) {
        const status = error.response.status
        const detail = error.response.data?.detail || error.response.data?.msg || '请求失败'
        const message = typeof detail === 'string' ? detail : detail?.msg || '请求失败'
        if (status === 401) {
          localStorage.removeItem('token')
          if (router.currentRoute.value.path !== '/login') {
            router.push('/login')
          }
        } else if (status === 403) {
          ElMessage.error('权限不足')
        } else if (status === 404) {
          ElMessage.error('资源不存在')
        } else {
          ElMessage.error(message)
        }
      } else if (error.code !== 'ERR_CANCELED' && error.name !== 'CanceledError') {
        ElMessage.error('网络错误，请检查连接')
      }
      return Promise.reject(error)
    },
  )

  return api
}

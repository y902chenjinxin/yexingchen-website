import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  // 注意：不要在此设置全局 Content-Type: application/json。
  // axios v1 在请求已带 application/json 头时，会把 FormData 用 formDataToJSON
  // 转成 JSON（file 字段变空对象），导致所有上传接口丢失文件 → 后端 422「file Field required」。
  // 交 axios 自动判断：JSON 对象自动 application/json，FormData 自动 multipart/boundary。
})

// 请求拦截器：注入token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误
api.interceptors.response.use(
  (response) => {
    if (response.data.code !== 0 && response.data.code !== 200) {
      ElMessage.error(response.data.msg || '请求失败')
      return Promise.reject(response.data)
    }
    return response.data
  },
  (error) => {
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || '请求失败'
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
    } else {
      // 请求被主动取消（页面跳转、组件卸载、AbortController）不算错误，不弹提示
      if (error.code !== 'ERR_CANCELED' && error.name !== 'CanceledError') {
        ElMessage.error('网络错误，请检查连接')
      }
    }
    return Promise.reject(error)
  }
)

export default api
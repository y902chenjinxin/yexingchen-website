/**
 * 资讯推送 API
 * 独立 axios 实例，读 res.data.*。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/feeds',
  timeout: 90000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || error.response.data?.msg || '请求失败'
      const message = typeof detail === 'string' ? detail : detail?.msg || '请求失败'
      if (status === 401) {
        localStorage.removeItem('token')
        if (router.currentRoute.value.path !== '/login') router.push('/login')
      } else if (status === 403) {
        ElMessage.error('权限不足')
      } else if (status === 404) {
        ElMessage.error('资源不存在')
      } else {
        ElMessage.error(message)
      }
    } else {
      ElMessage.error('网络错误，请检查连接')
    }
    return Promise.reject(error)
  }
)

export const feedsApi = {
  dashboard: () => api.get('/dashboard'),
  sources: () => api.get('/sources'),
  addSource: (data) => api.post('/sources', data),
  updateSource: (id, data) => api.put(`/sources/${id}`, data),
  deleteSource: (id) => api.delete(`/sources/${id}`),
  fetchSource: (id) => api.post(`/sources/${id}/fetch`),
  fetchAll: () => api.post('/fetch-all'),
  list: (params) => api.get('/articles', { params }),
  get: (id) => api.get(`/articles/${id}`),
  delArticle: (id) => api.delete(`/articles/${id}`),
  summary: (id) => api.post(`/articles/${id}/summary`),
  translate: (id) => api.post(`/articles/${id}/translate`),
  toggleBookmark: (id) => api.post(`/articles/${id}/toggle-bookmark`),
  toNote: (id, data) => api.post(`/articles/${id}/to-note`, data),
}

export default feedsApi
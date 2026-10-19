/**
 * 爬虫工具 API（通用抓取 + 小说下载/精校），独立 axios 实例，不自动解包 data。
 * 小说导出走 blob（文件下载），长抓取放宽超时到 120s（后端逐章限速）。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('token')
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    } else if (err.response?.status === 429) {
      ElMessage.error('操作太频繁，稍后再试')
    }
    return Promise.reject(err)
  },
)

export const crawlerApi = {
  fetch: (payload) => api.post('/crawler/fetch', payload),
  novelOutline: (url) => api.post('/crawler/novel/outline', { url }),
  novelChapters: (payload) => api.post('/crawler/novel/chapters', payload, { timeout: 120000 }),
  novelExport: (payload) => api.post('/crawler/novel/export', payload, { responseType: 'blob', timeout: 60000 }),
}

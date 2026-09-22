/**
 * 股票查看 API
 * 独立 axios 实例，读 res.data.*。行情刷新走服务端东财接口 + 缓存。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/stocks',
  timeout: 20000,
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
        // 行情类接口 404（上游东财抖动）改为静默：调用方会自己用旧缓存或占位
        // 仅 console.warn 方便排查
        if (typeof console !== 'undefined') console.warn('[stocks]', message)
      } else if (status >= 500) {
        // 上游故障 → 静默
        if (typeof console !== 'undefined') console.warn('[stocks 5xx]', message)
      } else {
        ElMessage.error(message)
      }
    } else {
      // 网络层错误（DNS/CORS/断连）→ 静默，不打扰用户
      if (typeof console !== 'undefined') console.warn('[stocks network]', error.message || error)
    }
    return Promise.reject(error)
  }
)

export const stocksApi = {
  watchlist: () => api.get('/watchlist'),
  add: (data) => api.post('/watchlist', data),
  update: (id, data) => api.put(`/watchlist/${id}`, data),
  remove: (id) => api.delete(`/watchlist/${id}`),
  search: (q, count) => api.get('/search', { params: { q, count } }),
  quote: (market, code) => api.get(`/quote/${market}/${encodeURIComponent(code)}`),
  kline: (market, code, lmt) => api.get(`/kline/${market}/${encodeURIComponent(code)}`, { params: { lmt } }),
  summary: () => api.get('/summary'),
  dashboard: () => api.get('/dashboard'),
  snapshots: (days) => api.get('/snapshots', { params: { days } }),
  recordSnapshot: () => api.post('/snapshots/today'),
  analysis: (market, code, days) => api.get(`/analysis/${market}/${code}`, { params: { days } }),
  generateAnalysis: (market, code) => api.post(`/analysis/${market}/${code}`),
  // 目标价预警
  alerts: (params) => api.get('/alerts', { params }),
  markAlertRead: (id) => api.post(`/alerts/${id}/read`),
  markAllAlertsRead: () => api.post('/alerts/read-all'),
}

export default stocksApi
/**
 * 个人记账 API
 * 独立 axios 实例（与 workbench.js 同构），不自动解包 data，调用方读 res.data.*。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
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

export const financeApi = {
  categories: () => api.get('/finance/categories'),
  summary: (month) => api.get('/finance/summary', { params: { month } }),
  list: (params) => api.get('/finance/transactions', { params }),
  create: (data) => api.post('/finance/transactions', data),
  update: (id, data) => api.put(`/finance/transactions/${id}`, data),
  remove: (id) => api.delete(`/finance/transactions/${id}`),
  importCsv: (csvText) => api.post('/finance/import', { csv: csvText }),
  analyzeImport: (csvText) => api.post('/finance/import/analyze', { csv: csvText }),
  confirmImport: (rows) => api.post('/finance/import/confirm', { rows }),
}

// CSV 导出走 blob（不经 axios 拦截器，避免响应处理差异）
export function exportFinanceCsv(params = {}) {
  const token = localStorage.getItem('token')
  const query = new URLSearchParams()
  if (params.start) query.set('start', params.start)
  if (params.end) query.set('end', params.end)
  return fetch(`/api/finance/export?${query.toString()}`, { headers: { authorization: `Bearer ${token}` } })
    .then(async (resp) => {
      if (!resp.ok) throw new Error('导出失败')
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const cd = resp.headers.get('content-disposition') || ''
      const m = /filename="?([^";]+)"?/.exec(cd)
      a.href = url
      a.download = m ? m[1] : `账本导出_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    })
}

export default financeApi
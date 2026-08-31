/**
 * 工作台独立 axios 实例
 *
 * 与旧 api/index.js 共用 baseURL 与 token 注入；
 * 统一工作台 API 契约：后端所有接口返回 {code, msg, data} 包装。
 * 拦截器**不**自动解包 data 字段，调用方读 res.data.*。
 *
 * 为避免混淆，工作台所有调用统一走本实例（api.workbench.*）。
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
  if (token) {
    config.headers.authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  // 直接返回 response.data，保持 {code, msg, data} 包装。
  // 调用方统一通过 res.data.* 读取业务字段。
  (response) => response.data,
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
    } else {
      ElMessage.error('网络错误，请检查连接')
    }
    return Promise.reject(error)
  }
)

export const workbenchApi = {
  // 工作台首页聚合
  summary: () => api.get('/workbench/summary'),

  // 笔记
  notes: {
    list: (params) => api.get('/workbench/notes', { params }),
    create: (data) => api.post('/workbench/notes', data),
    get: (id) => api.get(`/workbench/notes/${id}`),
    update: (id, data) => api.put(`/workbench/notes/${id}`, data),
    setStatus: (id, status) => api.post(`/workbench/notes/${id}/status`, { status }),
    delete: (id) => api.delete(`/workbench/notes/${id}`),
    restore: (id) => api.post(`/workbench/notes/${id}/restore`),
    setTags: (id, tag_names) => api.post(`/workbench/notes/${id}/tags`, { tag_names }),
    attachAsset: (noteId, assetId) => api.post(`/workbench/notes/${noteId}/assets/${assetId}`),
    detachAsset: (noteId, assetId) =>
      api.delete(`/workbench/notes/${noteId}/assets/${assetId}`),
    listAssets: (noteId) => api.get(`/workbench/notes/${noteId}/assets`),
  },

  // 资产
  assets: {
    list: (params) => api.get('/workbench/assets', { params }),
    createLink: (data) => api.post('/workbench/assets/link', data),
    upload: (formData, config = {}) =>
      api.post('/workbench/assets/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        ...config,
      }),
    delete: (id) => api.delete(`/workbench/assets/${id}`),
    restore: (id) => api.post(`/workbench/assets/${id}/restore`),
    // 私有资源：以 fetch + Bearer 取回 blob，再生成本地 object URL。
    fetchBlob: async (id, kind = 'preview') => {
      const token = localStorage.getItem('token') || ''
      const url = `/api/workbench/assets/${id}/${kind}`
      const resp = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) {
        const txt = await resp.text().catch(() => '')
        const err = new Error(`fetch failed ${resp.status}: ${txt}`)
        err.status = resp.status
        throw err
      }
      const blob = await resp.blob()
      const mime = resp.headers.get('content-type') || 'application/octet-stream'
      return { blob, mime, objectUrl: URL.createObjectURL(blob) }
    },
  },

  // 任务
  tasks: {
    list: (params) => api.get('/workbench/tasks', { params }),
    create: (data) => api.post('/workbench/tasks', data),
    update: (id, data) => api.put(`/workbench/tasks/${id}`, data),
    link: (id, payload) => api.post(`/workbench/tasks/${id}/link`, payload),
    delete: (id) => api.delete(`/workbench/tasks/${id}`),
    restore: (id) => api.post(`/workbench/tasks/${id}/restore`),
  },

  tags: {
    list: () => api.get('/workbench/tags'),
  },

  trash: {
    list: () => api.get('/workbench/trash'),
    cleanup: () => api.post('/workbench/trash/cleanup'),
  },

  search: (q, params) => api.get('/workbench/search', { params: { q, ...params } }),

  // AI
  ai: {
    preview: (data) => api.post('/workbench/ai/preview', data),
    // invoke 强制要求 conversation_id
    invoke: (data) => api.post('/workbench/ai/invoke', data),
    // AI 结果应用：summary / organize / suggest_tags / suggest_task
    apply: (data) => api.post('/workbench/ai/apply', data),
    conversations: (params) => api.get('/workbench/ai/conversations', { params }),
    createConversation: (data) => api.post('/workbench/ai/conversations', data),
    renameConversation: (id, data) => api.put(`/workbench/ai/conversations/${id}`, data),
    deleteConversation: (id) => api.delete(`/workbench/ai/conversations/${id}`),
    messages: (id) => api.get(`/workbench/ai/conversations/${id}/messages`),
    // 关联笔记/资产/任务到对话
    link: (convId, payload) => api.post(`/workbench/ai/conversations/${convId}/links`, payload),
    unlink: (convId, linkId) => api.delete(`/workbench/ai/conversations/${convId}/links/${linkId}`),
    listLinks: (convId) => api.get(`/workbench/ai/conversations/${convId}/links`),
  },
}

export default workbenchApi

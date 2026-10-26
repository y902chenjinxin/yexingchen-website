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

  // 习惯打卡：返回 {code,msg,data:{habits:[...]}}，每条含 id/name/icon/color/weekly_goal/checked_today/streak/week_count/total_count/heat
  habits: {
    list: () => api.get('/habits'),
    create: (data) => api.post('/habits', data),
    // 后端早有 PATCH / DELETE（重命名 / 改目标 / 归档），之前 api 层没包，页面没法用
    update: (id, data) => api.patch(`/habits/${id}`, data),
    remove: (id) => api.delete(`/habits/${id}`),
    toggle: (id, data) => api.post(`/habits/${id}/toggle`, data),
    // v2.46.245 每日进度：「今天喝 3 杯水，喝一杯记一下」——delta 默认 +1
    step: (id, delta = 1) => api.post(`/habits/${id}/step`, { delta }),
    // v2.46.143：断链自罚结算（幂等，进「今天」页调用一次）+ 本周复盘
    settle: () => api.post('/habits/settle'),
    weekly: () => api.get('/habits/weekly'),
    // v2.46.144（P2）：六账户雷达 / 家人概览 / 周复盘快照
    radar: () => api.get('/habits/radar'),
    household: () => api.get('/habits/household'),
    reviews: (limit = 12) => api.get('/habits/reviews', { params: { limit } }),
    makeReview: () => api.post('/habits/reviews'),
  },

  // 服务器资源监测（PC 工作台，仅超管）：内存 / 磁盘 / 模块存储占用 / 进程内存
  serverMonitor: () => api.get('/workbench/server-monitor'),

  // 天气（后端代理高德，key 不出服务器）：{city} 或 {lat,lon}
  weather: (params) => api.get('/workbench/dashboard/weather', { params }),

  // 每日一言（hitokoto 代理）：{refresh?:boolean}，返回 {hitokoto, from, from_who, type, uuid, date, fallback?}
  dailyQuote: (params = {}) => api.get('/workbench/dashboard/daily-quote', { params }),

  // 历史上的今天：{refresh?:boolean}，返回 {date, month, day, items:[{year,month,day,title,desc}]}
  todayInHistory: (params = {}) => api.get('/workbench/dashboard/today-in-history', { params }),

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

  // ====== v2.39 AI 高级玩法 ======
  aiAdv: {
    // 通用入口：ability = rewrite | explain | extract_entities | memory_distill | agent_plan
    invoke: (data) => api.post('/workbench/ai/advanced', data),
    // 语义召回（GET）
    semanticSearch: (q, topK = 8) => api.get('/workbench/ai/semantic_search', { params: { q, top_k: topK } }),
    // 建立/重建嵌入
    indexNote: (data) => api.post('/workbench/ai/index', data),
    // Agent 自动任务
    agentStart: (data) => api.post('/workbench/ai/agent/start', data),
    agentRun: (data) => api.post('/workbench/ai/agent/run', data),
    agentGet: (id) => api.get(`/workbench/ai/agent/${id}`),
    // 长期记忆
    memoryList: () => api.get('/workbench/ai/memory'),
    memoryAdd: (data) => api.post('/workbench/ai/memory/add', data),
    memoryForget: (data) => api.post('/workbench/ai/memory/forget', data),
    // 用量
    usage: () => api.get('/workbench/ai/usage'),
    // OCR
    ocr: (data) => api.post('/workbench/ai/ocr', data),
  },

  // AI
  ai: {
    // === Provider 配置（用户级，明文存储 Key） ===
    providersList: () => api.get('/workbench/ai/providers'),
    providerCreate: (data) => api.post('/workbench/ai/providers', data),
    providerUpdate: (id, data) => api.put('/workbench/ai/providers/' + id, data),
    providerDelete: (id) => api.delete('/workbench/ai/providers/' + id),
    providerTest: (id) => api.post('/workbench/ai/providers/' + id + '/test'),
    // === 对话/调用 ===
        preview: (data) => api.post('/workbench/ai/preview', data),
    // invoke 强制要求 conversation_id；data.provider_id 可选指定 provider
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
    // 独立原生对话：SSE 流式（需要原始 fetch，不用 axios 拦截器）
    chatStream: async (body, onEvent, signal) => {
      const token = localStorage.getItem('token') || ''
      const resp = await fetch('/api/workbench/ai/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal,
      })
      if (!resp.ok || !resp.body) {
        const txt = await resp.text().catch(() => '')
        throw new Error(`对话流请求失败（HTTP ${resp.status}）：${txt.slice(0, 200)}`)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, idx).trim()
          buffer = buffer.slice(idx + 2)
          if (!raw.startsWith('data:')) continue
          const payload = raw.replace(/^data:\s*/, '').trim()
          if (!payload) continue
          let obj
          try { obj = JSON.parse(payload) } catch { continue }
          onEvent(obj)
        }
      }
    },
  },
}

// 每日英语（v2.46.245 / 词库扩到 962 词见 v2.46.247）：内置词库按日期轮换，不调外部模型
workbenchApi.study = {
  today: (offset = 0) => api.get('/study/today', { params: { offset } }),
  list: (limit = 30) => api.get('/study/list', { params: { limit } }),
}

// 每日知识（v2.46.248）：跨学科知识点 + 原创寓言，220 条按日期轮换
workbenchApi.knowledge = {
  today: (offset = 0) => api.get('/knowledge/today', { params: { offset } }),
  list: (limit = 30) => api.get('/knowledge/list', { params: { limit } }),
}

export default workbenchApi

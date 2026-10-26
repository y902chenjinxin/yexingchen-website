import api from './index'

export const getVideoList = (params) => api.get('/videos', { params })
export const uploadVideo = (formData) => api.post('/videos', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateVideo = (id, data) => api.put(`/videos/${id}`, data)
export const deleteVideo = (id) => api.delete(`/videos/${id}`)

// 上传人列表（只包含确实有视频的账号），供列表页的「上传人」筛选下拉使用
export const getVideoUploaders = () => api.get('/videos/uploaders')

// 批量导入：files + items 一一对应；items 中可选 cover
export const batchUploadVideo = ({ files, items, covers }) => {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  items.forEach((it) => {
    formData.append('titles', it.title || '')
    formData.append('cos_urls', it.cos_url || '')
    formData.append('categories', it.category || '')
    formData.append('tags', it.tags || '')
  })
  if (covers && covers.length) {
    covers.forEach((c) => { if (c) formData.append('covers', c) })
  }
  return api.post('/videos/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 15 * 60 * 1000, // 视频批量给 15 分钟
  })
}

export const downloadVideoTemplate = async () => {
  const res = await api.get('/videos/template', { responseType: 'blob' })
  const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'video_import_template.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** 拖拽排序（v2.46.188）：按传入的 id 顺序保存 */
// v2.46.236：路径原来写成单数 /video/reorder，但后端 router 的 prefix 是 /api/videos
// —— 拖拽排序一直在 404（静默失败，列表顺序看着"保存了"其实没存）。已对齐成复数。
export const reorderVideo = (ids) => api.put('/videos/reorder', { ids })


/* ---------- 自动字幕（v2.46.236） ---------- */
export const getSubtitleStatus = () => api.get('/videos/subtitle/status')
export const createSubtitle = (id) => api.post(`/videos/${id}/subtitle`, null, { timeout: 30 * 1000 })
export const getSubtitleTask = (id, taskId) => api.get(`/videos/${id}/subtitle/${taskId}`)
export const deleteSubtitle = (id) => api.delete(`/videos/${id}/subtitle`)
/** 下载 srt：走 blob，避免浏览器直接打开纯文本 */
export async function downloadSubtitle(id, filename) {
  const res = await api.get(`/videos/${id}/subtitle.srt`, { responseType: 'blob' })
  const blob = new Blob([res.data], { type: 'application/x-subrip' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `video-${id}.srt`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

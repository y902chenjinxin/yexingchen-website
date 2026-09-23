import api from './index'

export const getVideoList = (params) => api.get('/videos', { params })
export const uploadVideo = (formData) => api.post('/videos', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateVideo = (id, data) => api.put(`/videos/${id}`, data)
export const deleteVideo = (id) => api.delete(`/videos/${id}`)

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
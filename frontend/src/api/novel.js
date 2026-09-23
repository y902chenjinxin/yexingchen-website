import api from './index'

export const getNovelList = (params) => api.get('/novels', { params })
export const uploadNovel = (formData) => api.post('/novels', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateNovel = (id, data) => api.put(`/novels/${id}`, data)
export const deleteNovel = (id) => api.delete(`/novels/${id}`)

// 批量导入：files + items 一一对应；items 中可选 cover（同下标对应同文件）
export const batchUploadNovel = ({ files, items, covers }) => {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  items.forEach((it) => {
    formData.append('titles', it.title || '')
    formData.append('authors', it.author || '')
    formData.append('categories', it.category || '')
    formData.append('tags', it.tags || '')
  })
  if (covers && covers.length) {
    // covers[i] 可能为 undefined/File；append 时直接传 File 或忽略
    covers.forEach((c) => {
      if (c) formData.append('covers', c)
    })
  }
  return api.post('/novels/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 10 * 60 * 1000, // 小说批量给 10 分钟
  })
}

export const downloadNovelTemplate = async () => {
  const res = await api.get('/novels/template', { responseType: 'blob' })
  const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'novel_import_template.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
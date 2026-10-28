import api from './index'

export const getMusicList = (params) => api.get('/music', { params })
export const uploadMusic = (formData) => api.post('/music', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateMusic = (id, data) => api.put(`/music/${id}`, data)
export const deleteMusic = (id) => api.delete(`/music/${id}`)

// 上传人列表（只包含确实有曲目的账号），供列表页的「上传人」筛选下拉使用
export const getMusicUploaders = () => api.get('/music/uploaders')

// 批量导入：传入 { files: File[], items: [{ title, artist, category, tags }] }，items 与 files 一一对应
export const batchUploadMusic = ({ files, items }) => {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  items.forEach((it) => {
    formData.append('titles', it.title || '')
    formData.append('artists', it.artist || '')
    formData.append('categories', it.category || '')
    formData.append('tags', it.tags || '')
    // v2.46.231：时长由前端读本地文件得到，后端只存不解析
    formData.append('durations', String(it.duration || 0))
  })
  return api.post('/music/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    // 批量上传耗时长，给 5 分钟超时；网络异常时不会卡死
    timeout: 5 * 60 * 1000,
  })
}

// 下载导入模板（CSV，UTF-8 BOM，Excel 可直接打开）—— 用 axios blob 流触发浏览器下载
export const downloadMusicTemplate = async () => {
  const res = await api.get('/music/template', { responseType: 'blob' })
  const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'music_import_template.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** 拖拽排序（v2.46.188）：按传入的 id 顺序保存 */
export const reorderMusic = (ids) => api.put('/music/reorder', { ids })

/* ---------- 上次听到哪（v2.46.259） ----------
 * 按账号存在后端（不是 localStorage）：换设备/清缓存都能续上，
 * 家里多人共用一台设备时各记各的。 */
export const getMusicPlayback = () => api.get('/music/playback')
export const saveMusicPlayback = (trackId, position) =>
  api.put('/music/playback', { track_id: Number(trackId), position: Math.max(0, Math.round(position || 0)) })

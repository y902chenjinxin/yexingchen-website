// 倒计时 API（Days Matter 风格纪念日/倒数日）
// 复用 cover.js 的 baseURL/authHeader 模式

import api from './index'

const BASE = '/api/countdowns'

export const listCountdowns = ({ includeArchived = false } = {}) =>
  api.get(`${BASE}?include_archived=${includeArchived ? 'true' : 'false'}`)

export const listHomeCountdowns = () => api.get(`${BASE}/home`)

export const getCountdown = (id) => api.get(`${BASE}/${id}`)

export const createCountdown = (payload) => api.post(BASE, payload)

export const updateCountdown = (id, payload) => api.put(`${BASE}/${id}`, payload)

export const deleteCountdown = (id) => api.delete(`${BASE}/${id}`)

// 上传图片（背景图）。返回 { url, size }
export const uploadImage = (file, subDir = 'countdown') => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('sub_dir', subDir)
  return api.post('/uploads/image', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

import api from './index'

export const getNovelList = (params) => api.get('/novels', { params })
export const uploadNovel = (formData) => api.post('/novels', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateNovel = (id, data) => api.put(`/novels/${id}`, data)
export const deleteNovel = (id) => api.delete(`/novels/${id}`)
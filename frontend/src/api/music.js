import api from './index'

export const getMusicList = (params) => api.get('/music', { params })
export const uploadMusic = (formData) => api.post('/music', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateMusic = (id, data) => api.put(`/music/${id}`, data)
export const deleteMusic = (id) => api.delete(`/music/${id}`)
import api from './index'

export const getVideoList = (params) => api.get('/videos', { params })
export const uploadVideo = (formData) => api.post('/videos', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const updateVideo = (id, data) => api.put(`/videos/${id}`, data)
export const deleteVideo = (id) => api.delete(`/videos/${id}`)
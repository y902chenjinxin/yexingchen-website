import api from './index'

export const getBgMusic = () => api.get('/settings/bg_music')
export const updateBgMusic = (formData) => api.put('/settings/bg_music', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
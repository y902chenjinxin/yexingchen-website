import api from './index'

export const getBgMusic = () => api.get('/settings/bg_music')
export const updateBgMusic = (formData) => api.put('/settings/bg_music', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const getBgmChoice = () => api.get('/settings/bgm_choice')
export const updateBgmChoice = (data) => api.put('/settings/bgm_choice', data)
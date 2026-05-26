import api from './index'

export const searchAll = (params) => api.get('/search', { params })
import api from './index'

export const getLogs = (params) => api.get('/logs', { params })
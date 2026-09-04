import api from './index'

export const getToolList = (params) => api.get('/tools', { params })
export const createTool = (data) => api.post('/tools', data)
export const updateTool = (id, data) => api.put(`/tools/${id}`, data)
export const deleteTool = (id) => api.delete(`/tools/${id}`)
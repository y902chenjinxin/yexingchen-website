import api from './index'

export const getUserList = (params) => api.get('/admin/users', { params })
export const approveUser = (id) => api.post(`/admin/users/${id}/approve`)
export const rejectUser = (id) => api.post(`/admin/users/${id}/reject`)
export const updateUser = (id, data) => api.put(`/admin/users/${id}`, data)
export const deleteUser = (id) => api.delete(`/admin/users/${id}`)
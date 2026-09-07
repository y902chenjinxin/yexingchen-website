import api from './index'

export const getUserList = (params) => api.get('/admin/users', { params })
export const addUser = (data) => api.post('/admin/users', data)
export const approveUser = (id) => api.post(`/admin/users/${id}/approve`)
export const rejectUser = (id) => api.post(`/admin/users/${id}/reject`)
export const updateUser = (id, data) => api.put(`/admin/users/${id}`, data)
export const updateUserRole = (id, data) => api.put(`/admin/users/${id}/role`, data)
export const deleteUser = (id) => api.delete(`/admin/users/${id}`)

export const getRoleList = () => api.get('/admin/roles')
export const addRole = (data) => api.post('/admin/roles', data)
export const updateRole = (id, data) => api.put(`/admin/roles/${id}`, data)
export const deleteRole = (id) => api.delete(`/admin/roles/${id}`)

export const getMenuList = () => api.get('/admin/menus')
export const getPublicMenus = () => api.get('/admin/menus/public')
export const addMenu = (data) => api.post('/admin/menus', data)
export const updateMenu = (id, data) => api.put(`/admin/menus/${id}`, data)
export const deleteMenu = (id) => api.delete(`/admin/menus/${id}`)

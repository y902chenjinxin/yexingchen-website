import api from './index'

// ============================== 家庭成员 ==============================
export const listMembers = () => api.get('/life/members')
export const createMember = (formData) => api.post('/life/members', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
})
export const updateMember = (id, formData) => api.patch(`/life/members/${id}`, formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
})
export const deleteMember = (id) => api.delete(`/life/members/${id}`)

// ============================== 体重 ==============================
export const listWeight = (params) => api.get('/life/weight', { params })
export const createWeight = (formData) => api.post('/life/weight', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
})
export const deleteWeight = (id) => api.delete(`/life/weight/${id}`)

// ============================== 三餐 ==============================
export const listMeals = (params) => api.get('/life/meals', { params })
export const createMeal = (formData) => api.post('/life/meals', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 5 * 60 * 1000, // 图片上传给 5 分钟
})
export const deleteMeal = (id) => api.delete(`/life/meals/${id}`)

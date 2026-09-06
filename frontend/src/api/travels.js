/**
 * 旅游足迹 API
 * 独立 axios 实例，读 res.data.*；上传走 FormData。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/travels',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use(
  (r) => {
    if (r.data && r.data.code !== 0 && r.data.code !== 200) {
      ElMessage.error(r.data.msg || '请求失败')
      return Promise.reject(r.data)
    }
    return r.data
  },
  (e) => {
    const detail = e.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (detail?.msg || '请求失败')
    if (e.response?.status === 401) {
      localStorage.removeItem('token')
      if (router.currentRoute.value.path !== '/login') router.push('/login')
    } else if (e.response?.status !== 404) {
      ElMessage.error(msg)
    }
    return Promise.reject(e)
  }
)

export const listTravels = (params = {}) => api.get('', { params })
export const getStats = () => api.get('/stats')
export const getTravel = (id) => api.get(`/${id}`)
export const createTravel = (payload) => api.post('', payload)
export const updateTravel = (id, payload) => api.put(`/${id}`, payload)
export const removeTravel = (id) => api.delete(`/${id}`)
export const uploadMedia = (type, file) => {
  const fd = new FormData()
  fd.append('file', file)
  return axios.post('/api/travels/upload', fd, {
    params: { type },
    headers: {
      'Content-Type': 'multipart/form-data',
      authorization: `Bearer ${localStorage.getItem('token') || ''}`
    }
  }).then((r) => r.data)
}
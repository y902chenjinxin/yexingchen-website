import api from './index'

export const login = (email, password) => api.post('/auth/login', { email, password })
export const register = (email) => api.post('/auth/register', { email })
export const verifyCode = (email, code, password) => api.post('/auth/verify', { email, code, password })
export const logout = () => api.post('/auth/logout')
export const getMe = () => api.get('/auth/me')
export const updateMe = (data) => api.put('/auth/me', data)
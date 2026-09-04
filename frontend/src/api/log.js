import api from './index'

export const getLogs = (params) => api.get('/logs', { params })

// 批量删除操作日志
export const deleteLogs = (ids) => api.delete('/logs', { data: { ids } })

// 清空操作日志（可指定时间范围）
export const clearLogs = (payload = {}) => api.delete('/logs/clear', { data: payload })
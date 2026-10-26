import api from './index'

/**
 * 关系维护（v2.46.250）
 *
 * 与「家人通讯录」用同一张表，但后端按 user_id 隔离 —— 这里看到的人只有你自己能看到。
 */
const relationsApi = {
  list: (params = {}) => api.get('/relations', { params }),
  dashboard: () => api.get('/relations/dashboard'),
  detail: (id) => api.get(`/relations/${id}`),
  create: (payload) => api.post('/relations', payload),
  update: (id, payload) => api.patch(`/relations/${id}`, payload),
  remove: (id) => api.delete(`/relations/${id}`),

  addLog: (id, payload) => api.post(`/relations/${id}/logs`, payload),
  removeLog: (lid) => api.delete(`/relations/logs/${lid}`),

  icebreak: (id) => api.post(`/relations/${id}/icebreak`),
}

export default relationsApi

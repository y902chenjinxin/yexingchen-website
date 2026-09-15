/**
 * 家庭助理 API：家人通讯录 + 订阅账单。
 * 两者都由后端 /api/contacts 与 /api/subscriptions 提供；
 * 待办（含生日/续费自动提醒）沿用既有 workbenchApi.tasks。
 */
import { createApi } from '@/utils/http'
import { ElMessage } from 'element-plus'

const api = createApi({ baseURL: '/api', timeout: 20000 })

// 把后端统一信封 {code,msg,data} 透出，调用方即可用 res.data.list 取数据
api.interceptors.response.use(
  (r) => {
    if (r.data && r.data.code !== 0 && r.data.code !== 200) {
      ElMessage.error(r.data.msg || '请求失败')
      return Promise.reject(r.data)
    }
    return r.data
  },
  (e) => Promise.reject(e),
)

/* ---------------- 通讯录 ---------------- */
export const contactsApi = {
  list: (params = {}) => api.get('/contacts', { params }),
  upcoming: (days = 30) => api.get('/contacts/upcoming', { params: { days } }),
  detail: (id) => api.get(`/contacts/${id}`),
  create: (payload) => api.post('/contacts', payload),
  update: (id, payload) => api.put(`/contacts/${id}`, payload),
  remove: (id) => api.delete(`/contacts/${id}`),
  restore: (id) => api.post(`/contacts/${id}/restore`),
}

/* ---------------- 订阅 ---------------- */
export const subscriptionsApi = {
  list: (params = {}) => api.get('/subscriptions', { params }),
  stats: () => api.get('/subscriptions/stats'),
  upcoming: (days = 30) => api.get('/subscriptions/upcoming', { params: { days } }),
  detail: (id) => api.get(`/subscriptions/${id}`),
  create: (payload) => api.post('/subscriptions', payload),
  update: (id, payload) => api.put(`/subscriptions/${id}`, payload),
  remove: (id) => api.delete(`/subscriptions/${id}`),
  restore: (id) => api.post(`/subscriptions/${id}/restore`),
  /** 标记已缴费：到期日顺延到下一个账单周期 */
  pay: (id) => api.post(`/subscriptions/${id}/pay`),
}

/* ---------------- 公共常量（与后端 CYCLE_LABEL 保持一致） ---------------- */
export const CYCLE_OPTIONS = [
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' },
  { value: 'quarterly', label: '每季' },
  { value: 'yearly', label: '每年' },
  { value: 'once', label: '一次性' },
]

export const RELATION_OPTIONS = [
  '父亲', '母亲', '爷爷', '奶奶', '外公', '外婆',
  '伯父', '伯母', '叔叔', '婶婶', '姑姑', '姑父',
  '舅舅', '舅妈', '姨妈', '姨父', '哥哥', '姐姐',
  '弟弟', '妹妹', '其他亲戚', '朋友',
]

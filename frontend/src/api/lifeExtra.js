/**
 * 生活岛三件套 API（v2.40.21）：遗失物件 / 穿搭推荐 / 密码保险箱。
 *
 * 三者同属生活模块、同一批上线，故收在一个文件里；
 * 后端分别挂在 /api/lost、/api/wardrobe、/api/vault。
 */
import api from './index'

/* ---------------- 遗失物件 ---------------- */
export const lostApi = {
  list: (params) => api.get('/lost', { params }),
  stats: (params) => api.get('/lost/stats', { params }),
  uploaders: () => api.get('/lost/uploaders'),
  create: (data) => api.post('/lost', data),
  update: (id, data) => api.put(`/lost/${id}`, data),
  remove: (id) => api.delete(`/lost/${id}`),
}

/* ---------------- 穿搭推荐 ---------------- */
export const wardrobeApi = {
  // 单品
  items: (params) => api.get('/wardrobe/items', { params }),
  createItem: (data) => api.post('/wardrobe/items', data),
  updateItem: (id, data) => api.put(`/wardrobe/items/${id}`, data),
  wear: (id) => api.post(`/wardrobe/items/${id}/wear`),
  removeItem: (id) => api.delete(`/wardrobe/items/${id}`),
  // 人（家庭成员 + 穿搭附加信息）
  persons: () => api.get('/wardrobe/persons'),
  savePerson: (memberId, data) => api.put(`/wardrobe/persons/${memberId}`, data),
  // 搭配
  outfits: (params) => api.get('/wardrobe/outfits', { params }),
  createOutfit: (data) => api.post('/wardrobe/outfits', data),
  removeOutfit: (id) => api.delete(`/wardrobe/outfits/${id}`),
  // 今日推荐（按人 + 当天天气）
  suggest: (params) => api.get('/wardrobe/suggest', { params }),
  stats: () => api.get('/wardrobe/stats'),
}

/* ---------------- 密码保险箱 ---------------- */
export const vaultApi = {
  list: (params) => api.get('/vault', { params }),
  uploaders: () => api.get('/vault/uploaders'),
  generate: (params) => api.get('/vault/generate', { params }),
  create: (data) => api.post('/vault', data),
  update: (id, data) => api.put(`/vault/${id}`, data),
  remove: (id) => api.delete(`/vault/${id}`),
}

/* ---------------- 图片上传（复用工具岛的通用端点）----------------
 * sub_dir 只允许 [a-z0-9_-]，后端还会校验扩展名与大小。
 */
export function uploadLifeImage(file, subDir) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('sub_dir', subDir)
  return api.post('/uploads/image', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}

/** 家人选项（上传人 / 穿搭人选人共用来源：/api/life/members） */
export const familyMembers = () => api.get('/life/members')

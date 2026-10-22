import api from './index'

/** 服务器上的 ROM 列表（内置 + 本账号上传），v2.46.192 */
export const listRoms = () => api.get('/emulator/roms')

/** 上传自己的 ROM 到本账号目录（64MB 上限） */
export const uploadRom = (formData) =>
  api.post('/emulator/roms', formData, { headers: { 'Content-Type': 'multipart/form-data' } })

/** 删除已上传的 ROM（内置的删不掉） */
export const deleteRom = (filename) => api.delete(`/emulator/roms/${encodeURIComponent(filename)}`)

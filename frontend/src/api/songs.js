import api from './index'

/* 曲谱（钢琴演奏器 v2.46.334） */

/** 列表：只回元信息（id/标题/bpm/音符数/时长） */
export const getSongs = () => api.get('/songs')

/** 详情：带完整 notes */
export const getSong = (id) => api.get(`/songs/${id}`)

/** 上传一份曲谱 */
export const createSong = (payload) => api.post('/songs', payload, { timeout: 60000 })

export const deleteSong = (id) => api.delete(`/songs/${id}`)

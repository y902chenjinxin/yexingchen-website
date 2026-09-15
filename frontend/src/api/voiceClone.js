import api from './index'

/**
 * 音色克隆（MiniMax）。/speak 返回二进制音频，走独立 axios 实例拿 blob。
 */
export const getVoiceStatus = () => api.get('/tools/voice/status')
export const cloneVoice = (formData, onProgress) => api.post('/tools/voice/clone', formData, {
  timeout: 300000,  // 复刻是重操作（上传+ASR+克隆），30s 默认超时不够
  onUploadProgress: onProgress,
})
export const deleteVoice = (id) => api.delete(`/tools/voice/voices/${id}`)

import axios from 'axios'

export const speakVoice = async (payload) => {
  const token = localStorage.getItem('token')
  const resp = await axios.post('/api/tools/voice/speak', payload, {
    responseType: 'blob',
    timeout: 300000,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  return resp.data  // Blob(audio/mpeg)
}

export const voiceErrorMsg = (e) => {
  const d = e?.response?.data?.detail
  if (typeof d === 'string') return d
  return d?.msg || e?.detail?.msg || e?.msg || '操作失败，请稍后重试'
}

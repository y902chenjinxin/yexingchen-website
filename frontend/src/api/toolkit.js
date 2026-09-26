import api from './index'

/**
 * 工具岛 v2.40.14：OCR / 语音转文字。
 * 二维码、密码生成器为纯前端实现，不走 API。
 * OCR/ASR 是本地 CPU 推理：OCR 秒级；ASR 时长≈音频时长/17 + 上传，放宽超时。
 */

export const ocrImage = (fd) => api.post('/ocr', fd, { timeout: 120000 })

export const asrStatus = () => api.get('/asr/status')

export const asrTranscribe = (fd) => api.post('/asr', fd, { timeout: 300000 })

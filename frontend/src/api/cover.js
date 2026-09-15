import api from './index'

/**
 * AI 封面生成（服务端 Pillow 模板渲染）。
 * 走全局拦截器；渲染是秒级 CPU 操作，默认 30s 超时绰绰有余。
 */
export const getCoverPresets = () => api.get('/tools/cover/presets')

export const renderCover = (payload) => api.post('/tools/cover/render', payload)

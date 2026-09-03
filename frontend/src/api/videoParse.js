import axios from 'axios'

// 视频去水印解析。不走 api/index 的全局拦截器，错误由组件内联展示（符合无弹窗偏好）。
export const parseVideoUrl = async (url) => {
  const token = localStorage.getItem('token')
  const { data } = await axios.post('/api/video_parse', { url }, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  return data
}

export const parseErrorMsg = (e) => {
  const d = e?.response?.data?.detail
  if (typeof d === 'string') return d
  return d?.msg || '解析失败，请稍后重试'
}
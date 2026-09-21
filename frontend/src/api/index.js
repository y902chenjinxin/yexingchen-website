import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  // 注意：不要在此设置全局 Content-Type: application/json。
  // axios v1 在请求已带 application/json 头时，会把 FormData 用 formDataToJSON
  // 转成 JSON（file 字段变空对象），导致所有上传接口丢失文件 → 后端 422「file Field required」。
  // 交 axios 自动判断：JSON 对象自动 application/json，FormData 自动 multipart/boundary。
})

// 请求拦截器：注入token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误
//
// 设计原则（v2.38.3）：通用拦截器**不再默认弹任何错误吐司**。
// 业务方在各自的 catch 中按需提示（部分场景如 AI 简报、桌面搜索希望静默失败；
// 一些必填校验希望保留 422 给业务弹窗，不被拦截器抢去）。
// 仅 401（token 失效）这一**系统级**动作需要拦截器处理：清 token + 跳登录。
api.interceptors.response.use(
  (response) => {
    if (response.data.code !== 0 && response.data.code !== 200) {
      return Promise.reject(response.data)
    }
    return response.data
  },
  (error) => {
    if (error.response) {
      const status = error.response.status
      if (status === 401) {
        localStorage.removeItem('token')
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
      }
      // 其它状态码（400/403/404/422/5xx）一律交业务方 catch 处理
    }
    // 网络层错误/取消：不弹（页面切换、组件卸载等也会产生这类错）
    return Promise.reject(error)
  }
)

export default api
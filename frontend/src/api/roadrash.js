/** 暴力摩托 · 在线一起玩（房号 + 轮询，v2.46.150）。
 *  与 game_rooms 的差别：竞速不是回合制，状态是「每人一份里程快照」，
 *  比赛中 450ms 上报一次（sync），大厅 800ms 拉一次（state）。
 */
import api from './index'

export const roadrashApi = {
  create: (data) => api.post('/games/roadrash/rooms', data),
  join: (code) => api.post(`/games/roadrash/rooms/${code}/join`),
  state: (code) => api.get(`/games/roadrash/rooms/${code}`),
  start: (code) => api.post(`/games/roadrash/rooms/${code}/start`),
  sync: (code, data) => api.post(`/games/roadrash/rooms/${code}/sync`, data),
  reset: (code) => api.post(`/games/roadrash/rooms/${code}/reset`),
  leave: (code) => api.post(`/games/roadrash/rooms/${code}/leave`),
}

/** 页面关闭 / 组件卸载时通知服务端离房。
 *  普通 fetch 在 pagehide 阶段会被中断，keepalive:true 才能发出去。 */
export function beaconRoadrashLeave(code) {
  if (!code) return
  try {
    const token = localStorage.getItem('token')
    const base = api.defaults?.baseURL || '/api'
    fetch(`${base}/games/roadrash/rooms/${code}/leave`, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: '{}',
    }).catch(() => {})
  } catch { /* 忽略 */ }
}

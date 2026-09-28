/** 在线对战房间 API（生活岛·棋类游戏，v2.40.25）。
 * 轮询同步：客户端每 ~1.5s 拉 GET /rooms/{id}?after_seq=N 增量事件。
 */
import api from './index'

export const gameRoomsApi = {
  create: (data) => api.post('/games/rooms', data),
  mine: () => api.get('/games/rooms/mine'),
  invites: () => api.get('/games/invites'),
  accept: (id) => api.post(`/games/rooms/${id}/accept`),
  decline: (id) => api.post(`/games/rooms/${id}/decline`),
  resign: (id) => api.post(`/games/rooms/${id}/resign`),
  state: (id, afterSeq = 0) => api.get(`/games/rooms/${id}`, { params: { after_seq: afterSeq } }),
  move: (id, action) => api.post(`/games/rooms/${id}/move`, { action }),
  undo: (id) => api.post(`/games/rooms/${id}/undo`),
  leave: (id) => api.post(`/games/rooms/${id}/leave`),
  finish: (id, winnerId) => api.post(`/games/rooms/${id}/finish`, { action: { winner_id: winnerId } }),
}

/** 页面卸载/切走时通知服务端「我离开了对局」。
 *  普通 fetch 在 pagehide 阶段会被浏览器中断，`keepalive:true` 才能发得出去；
 *  它同时支持 Authorization 头（sendBeacon 不能自定义头，所以没用它）。 */
export function beaconLeave(roomId) {
  if (!roomId) return
  try {
    const token = localStorage.getItem('token')
    const base = api.defaults?.baseURL || '/api'
    fetch(`${base}/games/rooms/${roomId}/leave`, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: '{}',
    }).catch(() => {})
  } catch { /* 忽略 */ }
}

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
  finish: (id, winnerId) => api.post(`/games/rooms/${id}/finish`, { action: { winner_id: winnerId } }),
}

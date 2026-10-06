/** 牌类在线对局 API（v2.44）—— 掼蛋 / 麻将 / 大富翁 的多席服务端权威房间。
 *
 * 与 `gameRooms.js`（双人棋类，客户端权威）不同：牌类的手牌由服务端保管，
 * 前端只拿 `view` 投影（自己的手牌 + 公开信息），所有动作走 `/act`。
 * 轮询同步沿用 1.6s 骨架，不引入 WebSocket。
 */
import api from './index'

export const gameTablesApi = {
  /** 建房：game_key / 邀请人 / 席位数 / 底注 */
  create: (data) => api.post('/game/rooms', data),
  /** 待我接受的牌桌邀请 */
  invites: () => api.get('/game/rooms/invites'),
  /** 我参与的牌桌（等待 / 进行 / 刚结束） */
  mine: () => api.get('/game/rooms/mine'),
  join: (id) => api.post(`/game/rooms/${id}/join`),
  decline: (id) => api.post(`/game/rooms/${id}/decline`),
  /** 房主换位 / 踢人（开局后锁定） */
  seat: (id, data) => api.post(`/game/rooms/${id}/seat`, data),
  /** 房主开局（空席 AI 补位 + 预扣底注） */
  start: (id) => api.post(`/game/rooms/${id}/start`),
  /** 投影态：自己的手牌 + 公开信息 */
  state: (id) => api.get(`/game/rooms/${id}`),
  /** 动作：出牌 / 摸打 / 碰杠胡 / 还贡 / 买地 / 拍卖 / 交易 / 抵押 */
  act: (id, action) => api.post(`/game/rooms/${id}/act`, { action }),
  rematch: (id) => api.post(`/game/rooms/${id}/rematch`),
  /** 退出：显式退出＝认输（对局中会就地结算整局）；soft=true 为「页面切走」兜底，仅转托管 */
  leave: (id, soft = false) => api.post(`/game/rooms/${id}/leave${soft ? '?soft=1' : ''}`),
  /** 解散牌桌：任何在座家人都可；不判输赢，已开局则退还底注 */
  dissolve: (id) => api.post(`/game/rooms/${id}/dissolve`),
  heartbeat: (id) => api.post(`/game/rooms/${id}/heartbeat`),
}

/** 页面卸载 / 切走时通知服务端「我离开了牌桌」。
 *  soft=1 → 只转托管 / 刷心跳，**不结束牌局**（一次刷新不该废掉整桌）。
 *  keepalive 才能在 pagehide 阶段发出；sendBeacon 不能自定义 Authorization 头，故用 fetch。 */
export function beaconTableLeave(roomId) {
  if (!roomId) return
  try {
    const token = localStorage.getItem('token')
    const base = api.defaults?.baseURL || '/api'
    fetch(`${base}/game/rooms/${roomId}/leave?soft=1`, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: '{}',
    }).catch(() => {})
  } catch { /* 忽略 */ }
}

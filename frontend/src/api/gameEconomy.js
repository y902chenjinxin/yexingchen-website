/** 棋牌三件套 · 积分 / 欢乐豆经济系统 API（v2.43）。 */
import api from './index'

export const gameEconomyApi = {
  wallet: () => api.get('/game/wallet'),
  signin: () => api.post('/game/signin'),
  behavior: (action) => api.post('/game/behavior', { action }),
  exchange: (points) => api.post('/game/exchange', { points }),
  gift: (toUserId, beans) => api.post('/game/gift', { to_user_id: toUserId, beans }),
  relief: () => api.post('/game/relief'),
  settle: (payload) => api.post('/game/settle', payload),
  ledger: (kind = 'bean', limit = 30) => api.get('/game/ledger', { params: { kind, limit } }),
  stats: () => api.get('/game/stats'),
  leaderboard: () => api.get('/game/leaderboard'),
  maps: () => api.get('/game/maps'),
  createMap: (data) => api.post('/game/maps', data),
  updateMap: (id, data) => api.put(`/game/maps/${id}`, data),
  deleteMap: (id) => api.delete(`/game/maps/${id}`),
}

/** 对局结算：静默上报，失败不打断游戏体验。 */
export async function reportSettle(gameKey, result, beanDelta, stake) {
  try {
    const res = await gameEconomyApi.settle({
      game_key: gameKey, result, bean_delta: beanDelta, stake,
    })
    return res?.data || null
  } catch {
    return null
  }
}

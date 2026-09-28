/** 本地对局存档（棋类游戏）。
 *
 * 只存本机（localStorage），不落库：家庭场景下"继续上局"是**这台设备**的临时便利，
 * 跨设备续局要服务端房间（在线模式已有）。
 *
 * 约定：key = xuanhuang_game_save_<game>
 *   { mode, summary, ts, ...游戏自定义状态 }
 * summary 是给「继续上一局 · xxx」按钮显示的一句话摘要。
 */
const PREFIX = 'xuanhuang_game_save_'

export function saveGame(game, data) {
  try {
    localStorage.setItem(PREFIX + game, JSON.stringify({ ...data, ts: Date.now() }))
  } catch { /* 隐私模式/配额满：静默失败，不影响游戏 */ }
}

export function loadGame(game) {
  try {
    const raw = localStorage.getItem(PREFIX + game)
    if (!raw) return null
    const d = JSON.parse(raw)
    return d && typeof d === 'object' ? d : null
  } catch { return null }
}

export function clearGame(game) {
  try { localStorage.removeItem(PREFIX + game) } catch { /* 忽略 */ }
}

/** 相对时间：刚刚 / N 分钟前 / N 小时前 / N 天前 */
export function saveAge(ts) {
  if (!ts) return ''
  const s = Math.max(0, (Date.now() - ts) / 1000)
  if (s < 60) return '刚刚'
  if (s < 3600) return `${Math.floor(s / 60)} 分钟前`
  if (s < 86400) return `${Math.floor(s / 3600)} 小时前`
  return `${Math.floor(s / 86400)} 天前`
}

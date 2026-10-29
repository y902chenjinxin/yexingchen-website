/* AI 计算 Worker（v2.46.278）
 *
 * 为什么单独开一个线程：五子棋困难档是 depth 4 的 alpha-beta，象棋困难档是 5 层
 * 迭代加深 + 置换表，实测 1.2~2 秒。跑在主线程就是「点完卡住、动画掉帧、按钮没响应」——
 * 夜星原话「忍不了」。
 *
 * 两种棋共用一个 worker（消息里带 kind），省一个线程也省一次模型初始化。
 * 传进来的棋盘必须是**普通数组**（structured clone 不认 Vue 的 reactive proxy）。
 */
import { bestMove } from '../utils/games/gomokuAI'
import { aiPick, legalMoves } from '../utils/xiangqiRules'

self.onmessage = (e) => {
  const { id, kind, payload } = e.data || {}
  if (!id) return
  try {
    let result = null
    if (kind === 'gomoku') {
      result = bestMove(payload.board, payload.depth)
    } else if (kind === 'xiangqi') {
      result = aiPick(payload.board, payload.side, payload.depth)
    } else if (kind === 'xiangqi-moves') {
      // 判将死用：无合法着法 = 该方负
      result = legalMoves(payload.board, payload.side).length
    } else {
      throw new Error(`unknown kind: ${kind}`)
    }
    self.postMessage({ id, ok: true, result })
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message ? err.message : err) })
  }
}

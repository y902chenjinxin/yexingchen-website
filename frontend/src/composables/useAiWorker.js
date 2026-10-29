/* AI Worker 客户端（v2.46.278）
 *
 * 用法：
 *   const idx = await runAI('gomoku', { board: [...board.value], depth: 4 })
 *   const mv  = await runAI('xiangqi', { board: [...board.value], side: 'b', depth: 5 })
 *
 * 三条设计要求（都是踩过的）：
 * 1. **单例**：worker 只建一次。每次对局新建一个会重复加载 xiangqiRules / gomokuAI，
 *    首步额外多 100~200ms，反而更慢。
 * 2. **失败降级**：Worker 不可用（老 WebView / 被 CSP 拦）时回落到主线程同步算。
 *    宁可卡一下也不能点不动 —— 功能优先于流畅。
 * 3. **可作废**：重开/悔棋时旧的搜索结果必须丢掉。用 epoch 递增做标记，
 *    回来时对不上就返回 null，绝不能让上一局的走法落到新棋盘上。
 */
let worker = null
let workerBroken = false
let seq = 0
let epoch = 0
const pending = new Map()

function ensureWorker() {
  if (worker || workerBroken) return worker
  try {
    worker = new Worker(new URL('../workers/ai.worker.js', import.meta.url), { type: 'module' })
    worker.onmessage = (e) => {
      const { id, ok, result, error } = e.data || {}
      const p = pending.get(id)
      if (!p) return
      pending.delete(id)
      if (ok) p.resolve(result)
      else p.reject(new Error(error || 'ai failed'))
    }
    worker.onerror = () => {
      /* Worker 自身崩了：把等待中的全部 reject，让调用方走降级路径 */
      workerBroken = true
      for (const [, p] of pending) p.reject(new Error('worker crashed'))
      pending.clear()
      try { worker.terminate() } catch { /* 忽略 */ }
      worker = null
    }
  } catch {
    workerBroken = true
    worker = null
  }
  return worker
}

/** 让当前在算的结果作废（重开 / 悔棋 / 卸载时调用） */
export function invalidateAI() {
  epoch += 1
  for (const p of pending.values()) p.resolve(null)
  pending.clear()
}

/**
 * @returns {Promise<any|null>} 结果；被 invalidate 作废或算失败时返回 null
 */
export function runAI(kind, payload) {
  const myEpoch = epoch
  const w = ensureWorker()
  if (!w) return Promise.resolve(fallback(kind, payload)).then(r => (myEpoch === epoch ? r : null))

  return new Promise((resolve, reject) => {
    const id = ++seq
    pending.set(id, {
      resolve: r => resolve(myEpoch === epoch ? r : null),
      reject,
    })
    const timer = setTimeout(() => {
      if (!pending.has(id)) return
      pending.delete(id)
      /* 超时就降级到主线程算一次：宁可卡一下也不给「点了没反应」 */
      resolve(fallback(kind, payload))
    }, 9000)
    const done = pending.get(id)
    const origResolve = done.resolve
    done.resolve = (r) => { clearTimeout(timer); origResolve(r) }
    try {
      w.postMessage({ id, kind, payload })
    } catch (err) {
      clearTimeout(timer)
      pending.delete(id)
      reject(err)
    }
  })
}

/* 降级路径：主线程同步算（老 WebView）。这里刻意用动态 import，
   让「Worker 能用的设备」不为此多背一份解析成本。 */
async function fallback(kind, payload) {
  try {
    if (kind === 'gomoku') {
      const { bestMove } = await import('../utils/games/gomokuAI')
      return bestMove(payload.board, payload.depth)
    }
    if (kind === 'xiangqi') {
      const { aiPick } = await import('../utils/xiangqiRules')
      return aiPick(payload.board, payload.side, payload.depth)
    }
    if (kind === 'xiangqi-moves') {
      const { legalMoves } = await import('../utils/xiangqiRules')
      return legalMoves(payload.board, payload.side).length
    }
  } catch { /* 忽略 */ }
  return null
}

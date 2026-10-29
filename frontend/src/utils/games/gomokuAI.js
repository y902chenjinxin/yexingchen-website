/** 五子棋 AI（v2.46.277，3D 棋盘用）
 *
 * 与 components/games/GomokuBoard.vue 的算法**同源**（alpha-beta + 全盘求和评估），
 * 但这里是**固定 15×15 标准盘**：2D 版是 27×27 内部坐标 + 可变开放区（margin 那套
 * 动态扩棋盘），两者坐标系不同，硬合并反而容易出错，所以各留一份。
 *
 * ⚠️ 以后要补置换表 / 迭代加深（ISSUES V2424-002 的方向），**先改这里再同步 2D**：
 *    两边算法一旦漂移，同一个局面会出现「3D 版走法比平面版强/弱」的怪现象。
 *
 * 棋盘是一维数组：下标 = y * SIZE + x，0 = 空，1 = 黑，2 = 白。
 */

export const SIZE = 15
export const EMPTY = 0
export const BLACK = 1
export const WHITE = 2

const DIRS = [[1, 0], [0, 1], [1, 1], [1, -1]]

/** 从 idx 落下 p 后是否成五；返回连珠下标数组（含自身）或 null */
export function checkWinFrom(bd, idx, p) {
  const x = idx % SIZE
  const y = (idx / SIZE) | 0
  for (const [dx, dy] of DIRS) {
    const line = [idx]
    for (const sign of [1, -1]) {
      let nx = x + dx * sign
      let ny = y + dy * sign
      while (nx >= 0 && nx < SIZE && ny >= 0 && ny < SIZE && bd[ny * SIZE + nx] === p) {
        line.push(ny * SIZE + nx)
        nx += dx * sign
        ny += dy * sign
      }
    }
    if (line.length >= 5) return line
  }
  return null
}

/** 单方向的连子分（count 连、open 个开放端） */
function lineScore(count, open) {
  if (count >= 5) return 1000000
  if (count === 4) return open === 2 ? 50000 : (open === 1 ? 8000 : 0)
  if (count === 3) return open === 2 ? 5000 : (open === 1 ? 500 : 0)
  if (count === 2) return open === 2 ? 300 : (open === 1 ? 50 : 0)
  return open === 2 ? 10 : 0
}

/** 某空点对 p 的四个方向合计价值 */
export function pointScore(bd, idx, p) {
  const x = idx % SIZE
  const y = (idx / SIZE) | 0
  let total = 0
  for (const [dx, dy] of DIRS) {
    let count = 1
    let open = 0
    for (const sign of [1, -1]) {
      let nx = x + dx * sign
      let ny = y + dy * sign
      while (nx >= 0 && nx < SIZE && ny >= 0 && ny < SIZE && bd[ny * SIZE + nx] === p) {
        count++
        nx += dx * sign
        ny += dy * sign
      }
      if (nx >= 0 && nx < SIZE && ny >= 0 && ny < SIZE && bd[ny * SIZE + nx] === EMPTY) open++
    }
    total += lineScore(count, open)
  }
  return total
}

/** 候选点：已有棋子周围 2 格内的空点（全盘搜索太慢，也没有意义） */
export function candidates(bd) {
  const out = []
  if (!bd.some(v => v)) return [((SIZE - 1) / 2) * SIZE + (SIZE - 1) / 2]
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const idx = y * SIZE + x
      if (bd[idx]) continue
      let near = false
      for (let dy = -2; dy <= 2 && !near; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
          const nx = x + dx
          const ny = y + dy
          if (nx >= 0 && nx < SIZE && ny >= 0 && ny < SIZE && bd[ny * SIZE + nx]) { near = true; break }
        }
      }
      if (near) out.push(idx)
    }
  }
  return out
}

/** 全盘评估：双向求和（只取单点最大值会看不到「双活三」这类叠加威胁） */
export function evaluateBoard(bd) {
  let me = 0
  let op = 0
  for (const idx of candidates(bd)) {
    me += pointScore(bd, idx, WHITE)
    op += pointScore(bd, idx, BLACK)
  }
  return me - op * 1.1
}

function search(bd, depth, alpha, beta, maximizing) {
  if (depth === 0) return evaluateBoard(bd)
  const p = maximizing ? WHITE : BLACK
  const cands = candidates(bd)
    .map(idx => ({ idx, s: pointScore(bd, idx, p) + pointScore(bd, idx, 3 - p) }))
    .sort((a, b) => b.s - a.s)
    .slice(0, 10)
  if (!cands.length) return 0
  let best = maximizing ? -Infinity : Infinity
  for (const { idx } of cands) {
    bd[idx] = p
    let val
    if (checkWinFrom(bd, idx, p)) val = maximizing ? 900000 + depth : -900000 - depth
    else val = search(bd, depth - 1, alpha, beta, !maximizing)
    bd[idx] = EMPTY
    if (maximizing) { best = Math.max(best, val); alpha = Math.max(alpha, val) }
    else { best = Math.min(best, val); beta = Math.min(beta, val) }
    if (beta <= alpha) break
  }
  return best
}

/**
 * 白方（AI，2）该走哪。
 * @param {number[]} bd  当前局面（不会被修改，内部复制）
 * @param {number} depth 搜索层数（困难档 4，普通 2）
 * @returns {number} 落子下标；无处可走返回 -1
 */
export function bestMove(bd, depth = 4) {
  const b = [...bd]
  if (!b.some(v => v)) return ((SIZE - 1) / 2) * SIZE + ((SIZE - 1) / 2)
  const cands = candidates(b)
    .map(idx => ({ idx, s: pointScore(b, idx, WHITE) * 2 + pointScore(b, idx, BLACK) }))
    .sort((a, b2) => b2.s - a.s)
    .slice(0, 10)
  if (!cands.length) return -1

  // ① 自己能一步成五 → 直接下
  for (const c of cands) {
    b[c.idx] = WHITE
    const win = checkWinFrom(b, c.idx, WHITE)
    b[c.idx] = EMPTY
    if (win) return c.idx
  }
  // ② 对手能一步成五 → 堵
  for (const c of cands) {
    b[c.idx] = BLACK
    const win = checkWinFrom(b, c.idx, BLACK)
    b[c.idx] = EMPTY
    if (win) return c.idx
  }
  // ③ 正常搜索
  let bestVal = -Infinity
  let pick = cands[0].idx
  for (const c of cands) {
    b[c.idx] = WHITE
    const val = search(b, depth - 1, -Infinity, Infinity, false)
    b[c.idx] = EMPTY
    if (val > bestVal) { bestVal = val; pick = c.idx }
  }
  return pick
}

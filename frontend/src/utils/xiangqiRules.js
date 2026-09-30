/** 中国象棋规则引擎（明棋 / 翻棋共用，无外部依赖）。
 *
 * 棋盘用长度 90 的字符串数组表示：'' 为空，'rK' / 'bP' 为红 / 黑棋子。
 * 坐标：x = 0..8（列，左→右），y = 0..9（行，上→下；黑方在上、红方在下）。
 *
 * 走法覆盖完整象棋规则：马蹩腿 / 象塞眼不过河 / 士象九宫 / 炮隔子吃 /
 * 兵过河横走 / 将帅照面（飞将）。
 */

export const COLS = 9
export const ROWS = 10
export const RED = 'r'
export const BLACK = 'b'

export const GLYPH = {
  r: { K: '帅', A: '仕', B: '相', N: '马', R: '车', C: '炮', P: '兵' },
  b: { K: '将', A: '士', B: '象', N: '马', R: '车', C: '砲', P: '卒' },
}

export const VAL = { K: 10000, R: 900, N: 400, C: 450, A: 200, B: 200, P: 100 }

export const idx = (x, y) => y * COLS + x
export const xOf = i => i % COLS
export const yOf = i => (i / COLS) | 0
export const other = s => (s === RED ? BLACK : RED)

export const inPalace = (x, y, s) => x >= 3 && x <= 5 && (s === BLACK ? y <= 2 : y >= 7)
export const onOwnSide = (y, s) => (s === BLACK ? y <= 4 : y >= 5)

const N_DELTA = [
  [1, 2, 0, 1], [-1, 2, 0, 1], [1, -2, 0, -1], [-1, -2, 0, -1],
  [2, 1, 1, 0], [2, -1, 1, 0], [-2, 1, -1, 0], [-2, -1, -1, 0],
]
const ORTHO = [[1, 0], [-1, 0], [0, 1], [0, -1]]

/** 标准开局：红方在下（y=9），黑方在上（y=0） */
export function initialBoard() {
  const b = new Array(COLS * ROWS).fill('')
  const back = ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R']
  for (let x = 0; x < COLS; x++) { b[idx(x, 0)] = 'b' + back[x]; b[idx(x, 9)] = 'r' + back[x] }
  b[idx(1, 2)] = 'bC'; b[idx(7, 2)] = 'bC'; b[idx(1, 7)] = 'rC'; b[idx(7, 7)] = 'rC'
  for (const x of [0, 2, 4, 6, 8]) { b[idx(x, 3)] = 'bP'; b[idx(x, 6)] = 'rP' }
  return b
}

/** 单子的伪合法目标（含吃子，不含「走完自己被将」的过滤）。
 *
 * opts.relaxed = true 供**翻棋（暗棋）**使用：棋盘上没有「阵营半场」这个概念了，
 * 所以放开三处限制 —— 士/象/将不再受九宫与河界约束（否则被发到界外就永远动不了）、
 * 兵/卒按「单格位移」上下左右各一格（可横走、可后退），并且不启用「飞将」照面吃
 * （暗子身份未知，照面规则会造成莫名其妙的胜负）。
 * 走法形态本身完全保留：士斜一格、象走田且塞象眼、将走一格、车直行、马蹩腿、炮隔子吃。
 */
export function pieceTargets(b, from, opts = {}) {
  const relaxed = !!opts.relaxed
  const p = b[from]
  if (!p) return []
  const s = p[0], t = p[1]
  const x = xOf(from), y = yOf(from)
  const out = []
  const push = (nx, ny) => {
    if (nx < 0 || nx >= COLS || ny < 0 || ny >= ROWS) return false
    const q = b[idx(nx, ny)]
    if (!q) { out.push(idx(nx, ny)); return true }
    if (q[0] !== s) out.push(idx(nx, ny))
    return false
  }
  if (t === 'K') {
    for (const [dx, dy] of ORTHO) {
      const nx = x + dx, ny = y + dy
      if (relaxed || inPalace(nx, ny, s)) push(nx, ny)
    }
    // 飞将：同列无遮挡 → 可「照面」吃对方将帅（同时也是被将的判定）
    if (!relaxed) {
      for (const dy of [1, -1]) {
        let ny = y + dy
        while (ny >= 0 && ny < ROWS) {
          const q = b[idx(x, ny)]
          if (q) { if (q === other(s) + 'K') out.push(idx(x, ny)); break }
          ny += dy
        }
      }
    }
  } else if (t === 'A') {
    for (const [dx, dy] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const nx = x + dx, ny = y + dy
      if (relaxed || inPalace(nx, ny, s)) push(nx, ny)
    }
  } else if (t === 'B') {
    for (const [dx, dy] of [[2, 2], [2, -2], [-2, 2], [-2, -2]]) {
      const nx = x + dx, ny = y + dy
      if (nx < 0 || nx >= COLS || ny < 0 || ny >= ROWS) continue
      if (!relaxed && !onOwnSide(ny, s)) continue     // 象不过河（翻棋放开）
      if (b[idx(x + dx / 2, y + dy / 2)]) continue    // 塞象眼
      push(nx, ny)
    }
  } else if (t === 'N') {
    for (const [dx, dy, lx, ly] of N_DELTA) {
      const nx = x + dx, ny = y + dy
      if (nx < 0 || nx >= COLS || ny < 0 || ny >= ROWS) continue
      if (b[idx(x + lx, y + ly)]) continue            // 蹩马腿
      push(nx, ny)
    }
  } else if (t === 'R') {
    for (const [dx, dy] of ORTHO) {
      let nx = x + dx, ny = y + dy
      while (nx >= 0 && nx < COLS && ny >= 0 && ny < ROWS) {
        const q = b[idx(nx, ny)]
        if (!q) out.push(idx(nx, ny))
        else { if (q[0] !== s) out.push(idx(nx, ny)); break }
        nx += dx; ny += dy
      }
    }
  } else if (t === 'C') {
    for (const [dx, dy] of ORTHO) {
      let nx = x + dx, ny = y + dy, screen = false
      while (nx >= 0 && nx < COLS && ny >= 0 && ny < ROWS) {
        const q = b[idx(nx, ny)]
        if (!screen) {
          if (!q) out.push(idx(nx, ny))
          else screen = true
        } else if (q) {
          if (q[0] !== s) out.push(idx(nx, ny))       // 隔一子吃
          break
        }
        nx += dx; ny += dy
      }
    }
  } else if (t === 'P') {
    if (relaxed) {
      // 暗棋：河界已整体放开（士/象/将都能越河），「只能前进」失去参照 ——
      // 兵/卒按夜星口径归入「单格位移」，上下左右各一格（可横走、可后退，与将帅同款）。
      for (const [dx, dy] of ORTHO) push(x + dx, y + dy)
    } else {
      const fwd = s === BLACK ? 1 : -1
      push(x, y + fwd)
      if (!onOwnSide(y, s)) { push(x + 1, y); push(x - 1, y) }   // 明棋：过河才可横走，永不后退
    }
  }
  return out
}

/* ---------- 暗棋（翻棋）发牌 ---------- */

/** 标准开局占位：明棋 initialBoard() 上所有非空位，正好 32 个点。
 *  暗棋的「位置」就用它 —— 只洗棋子，不洗位置（V2442-007）。 */
export const STANDARD_SPOTS = initialBoard().reduce((acc, p, i) => {
  if (p) acc.push(i)
  return acc
}, [])

/** 32 枚棋子（红黑各 16：车2 马2 相2 士2 将1 炮2 兵5）。 */
export function flipDeck() {
  const d = []
  for (const c of [RED, BLACK]) {
    d.push(c + 'K', c + 'A', c + 'A', c + 'B', c + 'B', c + 'R', c + 'R', c + 'N', c + 'N', c + 'C', c + 'C')
    for (let k = 0; k < 5; k++) d.push(c + 'P')
  }
  return d
}

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
function shuffleIn(arr, rnd) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1))
    const t = arr[i]; arr[i] = arr[j]; arr[j] = t
  }
  return arr
}

/** 暗棋发牌：32 枚棋子洗牌后铺到 STANDARD_SPOTS 这 32 个标准开局点上，全部背面朝上。
 *  seed 为真值时结果可复现（在线对局用房间号播种，两端一致）；seed 为 0/空则用时间随机。
 *  返回长度 90 的数组，元素为 { c, t, up:false } 或 null。 */
export function flipDeal(seed) {
  const rnd = mulberry32(seed || ((Date.now() ^ 0x5f3a) & 0x7fffffff))
  const pieces = shuffleIn(flipDeck(), rnd)
  const spots = shuffleIn(STANDARD_SPOTS.slice(), rnd)
  const cells = new Array(COLS * ROWS).fill(null)
  for (let k = 0; k < pieces.length; k++) {
    cells[spots[k]] = { c: pieces[k][0], t: pieces[k][1], up: false }
  }
  return cells
}

export function findGeneral(b, s) {
  const g = s + 'K'
  for (let i = 0; i < b.length; i++) if (b[i] === g) return i
  return -1
}

/** sq 是否被 by 方攻击（含飞将） */
export function isAttacked(b, sq, by) {
  for (let i = 0; i < b.length; i++) {
    const p = b[i]
    if (!p || p[0] !== by) continue
    if (pieceTargets(b, i).includes(sq)) return true
  }
  return false
}

export function applyMove(b, from, to) {
  const nb = b.slice()
  nb[to] = nb[from]
  nb[from] = ''
  return nb
}

export function inCheck(b, s) {
  const g = findGeneral(b, s)
  return g < 0 ? true : isAttacked(b, g, other(s))
}

/** 全部合法走法（已过滤自将 / 照面） */
export function legalMoves(b, s) {
  const out = []
  for (let i = 0; i < b.length; i++) {
    const p = b[i]
    if (!p || p[0] !== s) continue
    for (const to of pieceTargets(b, i)) {
      const nb = applyMove(b, i, to)
      if (!inCheck(nb, s)) out.push({ from: i, to, cap: b[to] || '' })
    }
  }
  return out
}

/** 搜索用：不做自将过滤（被吃将帅由评估函数给极大负分惩罚），换取速度 */
export function pseudoMoves(b, s) {
  const out = []
  for (let i = 0; i < b.length; i++) {
    const p = b[i]
    if (!p || p[0] !== s) continue
    for (const to of pieceTargets(b, i)) out.push({ from: i, to, cap: b[to] || '' })
  }
  return out
}

export function evaluate(b, s) {
  let sc = 0
  for (let i = 0; i < b.length; i++) {
    const p = b[i]
    if (!p) continue
    const t = p[1]
    let v = VAL[t]
    if (t === 'P') {
      const y = yOf(i)
      if (!onOwnSide(y, p[0])) v += 100          // 过河兵增值
    }
    sc += (p[0] === s ? v : -v)
  }
  return sc
}

export function search(b, s, depth, alpha, beta) {
  if (findGeneral(b, s) < 0) return -99999
  if (findGeneral(b, other(s)) < 0) return 99999
  if (depth === 0) return evaluate(b, s)
  const moves = pseudoMoves(b, s)
  if (!moves.length) return -90000 + (10 - depth)
  moves.sort((a, c) => (c.cap ? VAL[c.cap[1]] || 0 : 0) - (a.cap ? VAL[a.cap[1]] || 0 : 0))
  let best = -Infinity
  for (const m of moves) {
    const nb = applyMove(b, m.from, m.to)
    const sc = -search(nb, other(s), depth - 1, -beta, -alpha)
    if (sc > best) best = sc
    if (best > alpha) alpha = best
    if (alpha >= beta) break
  }
  return best
}

export function aiPick(b, s, depth) {
  const moves = legalMoves(b, s)
  if (!moves.length) return null
  moves.sort((a, c) => (c.cap ? VAL[c.cap[1]] || 0 : 0) - (a.cap ? VAL[a.cap[1]] || 0 : 0))
  let best = -Infinity, pool = []
  for (const m of moves) {
    const nb = applyMove(b, m.from, m.to)
    const sc = -search(nb, other(s), depth - 1, -Infinity, Infinity)
    if (sc > best + 1) { best = sc; pool = [m] }
    else if (Math.abs(sc - best) <= 1) pool.push(m)
  }
  return pool[(Math.random() * pool.length) | 0] || moves[0]
}
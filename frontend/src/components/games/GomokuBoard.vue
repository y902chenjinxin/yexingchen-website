<template>
  <div class="gk-wrap">
    <div class="gk-toolbar">
      <div class="gk-modes">
        <button v-for="m in modes" :key="m.key" class="gk-mode" :class="{ on: mode === m.key }" @click="setMode(m.key)">{{ m.label }}</button>
      </div>
      <div class="gk-status">
        <span v-if="!over" :class="{ turn: turn === HUMAN }">{{ turn === HUMAN ? '轮到你（黑）' : (mode === 'pvp' ? '轮到白方' : 'AI 思考中…') }}</span>
        <span v-else class="gk-result">{{ resultText }}</span>
        <button class="gk-btn" @click="restart">重开</button>
        <button class="gk-btn" :disabled="!canUndo" @click="undo">悔棋</button>
      </div>
    </div>

    <div class="gk-board" :style="{ '--n': N }">
      <!-- 星位与线由背景网格绘制；棋子用 DOM，点击即落子 -->
      <button
        v-for="idx in N * N"
        :key="idx"
        class="gk-cell"
        :class="{ last: lastIdx === idx - 1 }"
        :aria-label="`第${Math.ceil(idx / N)}行第${((idx - 1) % N) + 1}列`"
        @click="play(idx - 1)"
      >
        <i v-if="board[idx - 1]" class="gk-stone" :class="board[idx - 1] === HUMAN ? 'black' : 'white'"></i>
      </button>
    </div>
    <p class="gk-hint">黑方先行 · 五子连珠获胜 · 困难模式 AI 搜索更深，落子会稍慢</p>
  </div>
</template>

<script setup>
/** 五子棋（自写，无外部依赖）。
 * AI = 极小化极大 + Alpha-Beta 剪枝，候选点限制在已有棋子半径 2 内，评估用公开的棋型打分表
 * （连五/活四/冲四/活三…，与 lihongxun945/gobang README 教程同一套公开算法，代码为自研实现）。
 * 模式：pvp 双人 / easy 陪练（1 层贪心）/ hard（3 层搜索）。
 */
import { ref, computed, onBeforeUnmount } from 'vue'

const N = 15
const HUMAN = 1, AI = 2
const modes = [
  { key: 'pvp', label: '双人' },
  { key: 'easy', label: '单机 · 简单' },
  { key: 'hard', label: '单机 · 困难' },
]
const mode = ref('easy')
const board = ref(Array(N * N).fill(0))
const turn = ref(HUMAN)
const over = ref(false)
const winner = ref(0)
const winLine = ref([])
const lastIdx = ref(-1)
const history = ref([])
const thinking = ref(false)
let timer = null

const canUndo = computed(() => history.value.length > 0 && !thinking.value)
const resultText = computed(() => {
  if (winner.value === HUMAN) return mode.value === 'pvp' ? '🎉 黑方胜' : '🎉 你赢了'
  if (winner.value === AI) return mode.value === 'pvp' ? '🎉 白方胜' : 'AI 赢了，再来'
  return '🤝 平局'
})

function setMode(k) {
  mode.value = k
  restart()
}
function restart() {
  clearTimeout(timer)
  board.value = Array(N * N).fill(0)
  turn.value = HUMAN
  over.value = false
  winner.value = 0
  winLine.value = []
  lastIdx.value = -1
  history.value = []
  thinking.value = false
}

/** 从最后一手出发四方向数连子（O(1)，只查 5 颗） */
function checkWinFrom(bd, idx, p) {
  const x = idx % N, y = Math.floor(idx / N)
  for (const [dx, dy] of [[1, 0], [0, 1], [1, 1], [1, -1]]) {
    const line = [idx]
    for (const sign of [1, -1]) {
      let nx = x + dx * sign, ny = y + dy * sign
      while (nx >= 0 && nx < N && ny >= 0 && ny < N && bd[ny * N + nx] === p) {
        line.push(ny * N + nx)
        nx += dx * sign; ny += dy * sign
      }
    }
    if (line.length >= 5) return line
  }
  return null
}

/* ---------- 评估：某点落 p 后，四方向的 (连子数, 开口数) 打分 ---------- */
function lineScore(count, open) {
  if (count >= 5) return 1000000
  if (count === 4) return open === 2 ? 50000 : (open === 1 ? 8000 : 0)
  if (count === 3) return open === 2 ? 5000 : (open === 1 ? 500 : 0)
  if (count === 2) return open === 2 ? 300 : (open === 1 ? 50 : 0)
  return open === 2 ? 10 : 0
}
function pointScore(bd, idx, p) {
  const x = idx % N, y = Math.floor(idx / N)
  let total = 0
  for (const [dx, dy] of [[1, 0], [0, 1], [1, 1], [1, -1]]) {
    let count = 1, open = 0
    for (const sign of [1, -1]) {
      let nx = x + dx * sign, ny = y + dy * sign
      while (nx >= 0 && nx < N && ny >= 0 && ny < N && bd[ny * N + nx] === p) {
        count++; nx += dx * sign; ny += dy * sign
      }
      if (nx >= 0 && nx < N && ny >= 0 && ny < N && bd[ny * N + nx] === 0) open++
    }
    total += lineScore(count, open)
  }
  return total
}

/** 候选点：有棋子的半径 2 内的空位（首手走天元） */
function candidates(bd) {
  const out = []
  if (!bd.some(v => v)) return [Math.floor(N * N / 2)]
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const idx = y * N + x
    if (bd[idx]) continue
    let near = false
    for (let dy = -2; dy <= 2 && !near; dy++) for (let dx = -2; dx <= 2; dx++) {
      const nx = x + dx, ny = y + dy
      if (nx >= 0 && nx < N && ny >= 0 && ny < N && bd[ny * N + nx]) { near = true; break }
    }
    if (near) out.push(idx)
  }
  return out
}

/** 极小化极大（AI 最大化）。depth：easy=1 贪心，hard=3 */
function search(bd, depth, alpha, beta, maximizing) {
  // 终局：上一层已把「能赢的点」处理掉，这里以评估值收口
  if (depth === 0) return evaluateBoard(bd)
  const p = maximizing ? AI : HUMAN
  const cands = candidates(bd)
    .map(idx => ({ idx, s: pointScore(bd, idx, p) + pointScore(bd, idx, 3 - p) }))
    .sort((a, b) => b.s - a.s)
    .slice(0, 10)                          // 剪枝：只搜启发式前 10 个候选
  if (!cands.length) return 0
  let best = maximizing ? -Infinity : Infinity
  for (const { idx } of cands) {
    bd[idx] = p
    let val
    if (checkWinFrom(bd, idx, p)) val = maximizing ? 900000 + depth : -900000 - depth
    else val = search(bd, depth - 1, alpha, beta, !maximizing)
    bd[idx] = 0
    if (maximizing) { best = Math.max(best, val); alpha = Math.max(alpha, val) }
    else { best = Math.min(best, val); beta = Math.min(beta, val) }
    if (beta <= alpha) break
  }
  return best
}
function evaluateBoard(bd) {
  // 全盘粗评估：双方候选点最高威胁差（够用即可，搜索已承担主要智力）
  let ai = 0, hu = 0
  for (const idx of candidates(bd)) {
    ai = Math.max(ai, pointScore(bd, idx, AI))
    hu = Math.max(hu, pointScore(bd, idx, HUMAN))
  }
  return ai - hu * 1.1
}

function play(idx) {
  if (over.value || thinking.value || board.value[idx]) return
  if (mode.value !== 'pvp' && turn.value !== HUMAN) return
  place(idx)
  if (over.value) return
  if (mode.value !== 'pvp' && turn.value === AI) aiMove()
  else turn.value = 3 - turn.value
}

function place(idx) {
  history.value.push(idx)
  board.value[idx] = turn.value
  lastIdx.value = idx
  const line = checkWinFrom(board.value, idx, turn.value)
  if (line) { winLine.value = line; winner.value = turn.value; over.value = true }
  else if (board.value.every(v => v)) { over.value = true }
}

function aiMove() {
  thinking.value = true
  timer = setTimeout(() => {
    const bd = [...board.value]
    const depth = mode.value === 'hard' ? 3 : 1
    const cands = candidates(bd)
      .map(idx => ({ idx, s: pointScore(bd, idx, AI) * 2 + pointScore(bd, idx, HUMAN) }))
      .sort((a, b) => b.s - a.s)
      .slice(0, depth === 1 ? 1 : 10)
    // 先看有没有「自己能立刻赢」或「对方能立刻赢」的点（必杀/必防）
    let pick = cands.find(c => { bd[c.idx] = AI; const w = checkWinFrom(bd, c.idx, AI); bd[c.idx] = 0; return w })
    if (!pick) pick = cands.find(c => { bd[c.idx] = HUMAN; const w = checkWinFrom(bd, c.idx, HUMAN); bd[c.idx] = 0; return w })
    if (!pick) {
      let bestVal = -Infinity
      for (const c of cands) {
        bd[c.idx] = AI
        const val = search(bd, depth - 1, -Infinity, Infinity, false)
        bd[c.idx] = 0
        if (val > bestVal) { bestVal = val; pick = c }
      }
    }
    thinking.value = false
    if (pick) { turn.value = AI; place(pick.idx); turn.value = HUMAN }
  }, 120)
}

function undo() {
  if (!history.value.length || thinking.value) return
  clearTimeout(timer)
  // 双人撤 1 步；人机把 AI 那步也一起撤（撤回到自己上一手之前）
  const steps = mode.value === 'pvp' ? 1 : (history.value.length >= 2 ? 2 : 1)
  for (let i = 0; i < steps && history.value.length; i++) {
    const idx = history.value.pop()
    board.value[idx] = 0
  }
  over.value = false; winner.value = 0; winLine.value = []
  lastIdx.value = history.value[history.value.length - 1] ?? -1
  turn.value = HUMAN
}

onBeforeUnmount(() => clearTimeout(timer))
</script>

<style scoped>
.gk-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.gk-toolbar { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; justify-content: center; width: 100%; }
.gk-modes { display: flex; gap: 6px; }
.gk-mode { padding: 6px 14px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 12.5px; font-family: inherit; }
.gk-mode.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gk-status { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--dp-text2, #45505b); }
.gk-result { font-weight: 700; color: var(--yq-gold, #c7a96b); }
.gk-btn { padding: 4px 13px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }
.gk-btn:disabled { opacity: .5; cursor: default; }

.gk-board {
  display: grid; grid-template-columns: repeat(15, var(--cell, 26px)); grid-auto-rows: var(--cell, 26px);
  background: linear-gradient(135deg, #e8d9b8, #dcc79a); padding: 8px; border-radius: 12px;
  touch-action: manipulation; user-select: none; box-shadow: inset 0 0 0 1px rgba(0,0,0,.15);
}
.gk-cell { border: none; padding: 0; background: transparent; cursor: pointer; position: relative;
  box-shadow: inset -1px 0 0 rgba(0,0,0,.25), inset 0 -1px 0 rgba(0,0,0,.25); }
.gk-cell:last-child { box-shadow: none; }
.gk-stone { position: absolute; inset: 2px; border-radius: 50%; display: block; }
.gk-stone.black { background: radial-gradient(circle at 34% 30%, #555, #111); }
.gk-stone.white { background: radial-gradient(circle at 34% 30%, #fff, #cfcabb); }
.gk-cell.last::after { content: ''; position: absolute; top: 50%; left: 50%; width: 5px; height: 5px;
  margin: -2.5px; border-radius: 50%; background: #e5484d; z-index: 2; }
.gk-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }

@media (max-width: 480px) {
  .gk-board { --cell: 21px; padding: 6px; }
}
</style>

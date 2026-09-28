<template>
  <div class="ot-wrap">
    <div class="ot-toolbar">
      <div v-if="!bare" class="ot-modes">
        <button v-for="m in modes" :key="m.key" class="ot-mode" :class="{ on: mode === m.key }" @click="setMode(m.key)">{{ m.label }}</button>
      </div>
      <div class="ot-status">
        <span class="ot-count black">⬤ {{ counts.black }}</span>
        <span class="ot-count white">⬤ {{ counts.white }}</span>
        <button class="ot-btn" @click="restart">重开</button>
        <button class="ot-btn" @click="showHints = !showHints">{{ showHints ? '隐藏提示' : '显示可下点' }}</button>
      </div>
    </div>

    <div class="ot-board">
      <button
        v-for="idx in 64"
        :key="idx"
        class="ot-cell"
        :class="{ hint: showHints && !board[idx - 1] && legal(idx - 1).length, last: lastIdx === idx - 1 }"
        @click="play(idx - 1)"
      >
        <i v-if="board[idx - 1]" class="ot-disc" :class="[board[idx - 1] === BLACK ? 'black' : 'white', { flip: flipSet.has(idx - 1) }]"></i>
      </button>
      <div v-if="over" class="ot-over">
        <div class="ot-over-title">
          {{ counts.black === counts.white ? '🤝 平局' : ((counts.black > counts.white) === humanIsBlack ? '🎉 你赢了' : (mode === 'pvp' ? '🎉 黑方胜' : 'AI 赢了')) }}
        </div>
        <button class="ot-btn" @click="restart">再来</button>
      </div>
    </div>
    <p class="ot-hint">
      {{ turnText }}
      · 黑方先行 · 夹住对方棋子即可翻转 · 棋盘满或双方无子可下时多者胜
    </p>
  </div>
</template>

<script setup>
/** 黑白棋（自写，无外部依赖）。
 * 规则：落子必须至少翻转一枚对方棋子；无合法步则跳过（面板会提示）；
 *       双方都无法落子或棋盘满则终局，子多者胜。
 * AI：简单 = 位置权重贪心（角最高、角旁负分）；困难 = 3 层极小化极大 + Alpha-Beta。
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'

const N = 8
const BLACK = 1, WHITE = 2
const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]
const modes = [
  { key: 'pvp', label: '双人' },
  { key: 'easy', label: '单机 · 简单' },
  { key: 'hard', label: '单机 · 困难' },
]
const props = defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
})
const mode = ref(props.initialMode || 'easy')
const humanIsBlack = true

const board = ref(Array(64).fill(0))
const turn = ref(BLACK)
const over = ref(false)
const lastIdx = ref(-1)
const flipSet = ref(new Set())
const showHints = ref(false)
const skipNote = ref('')
const thinking = ref(false)
let timer = null


const counts = computed(() => {
  let black = 0, white = 0
  board.value.forEach(v => { if (v === BLACK) black++; else if (v === WHITE) white++ })
  return { black, white }
})
const turnText = computed(() => {
  if (over.value) return '对局结束'
  const side = turn.value === BLACK ? '黑方' : '白方'
  if (mode.value === 'pvp') return `轮到${side}`
  return turn.value === (humanIsBlack ? BLACK : WHITE) ? `轮到你（${side}）` : 'AI 思考中…'
})

/* ---------- 本地存档：返回列表后可「继续上一局」 ---------- */
const SAVE_KEY = 'othello'
let saveTimer = null
const modeLabel = computed(() => (modes.find(m => m.key === mode.value) || {}).label || '本局')
function saveLocal() {
  // 开局只有 4 颗子时没必要存（等于没下）
  if (over.value || counts.value.black + counts.value.white <= 4) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveGame(SAVE_KEY, {
      mode: mode.value,
      summary: `${modeLabel.value} · 黑白 ${counts.value.black}:${counts.value.white}`,
      board: board.value, turn: turn.value, over: over.value, lastIdx: lastIdx.value,
    })
  }, 400)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !Array.isArray(s.board) || s.board.length !== 64) return false
  if (s.mode) mode.value = s.mode
  board.value = s.board
  turn.value = s.turn || BLACK
  over.value = !!s.over
  lastIdx.value = s.lastIdx ?? -1
  return true
}
watch([board, over], saveLocal, { deep: true })
onMounted(() => { if (props.resume) restoreLocal() })

function resetBoard() {
  clearTimeout(timer)
  board.value = Array(64).fill(0)
  board.value[27] = WHITE; board.value[28] = BLACK
  board.value[35] = BLACK; board.value[36] = WHITE
  turn.value = BLACK
  over.value = false
  lastIdx.value = -1
  flipSet.value = new Set()
  skipNote.value = ''
  thinking.value = false
}
/** 用户主动重开 / 切模式：作废存档。setup 期间的初始化走 resetBoard()，不能清档 */
function restart() {
  clearTimeout(saveTimer)
  clearGame(SAVE_KEY)
  resetBoard()
}

function xy(idx) { return [idx % N, Math.floor(idx / N)] }
function legalFor(bd, p) {
  const out = {}
  for (let idx = 0; idx < 64; idx++) {
    if (bd[idx]) continue
    const flips = flipsFor(bd, idx, p)
    if (flips.length) out[idx] = flips
  }
  return out
}
function flipsFor(bd, idx, p) {
  const [x, y] = xy(idx)
  const flips = []
  for (const [dx, dy] of DIRS) {
    const line = []
    let nx = x + dx, ny = y + dy
    while (nx >= 0 && nx < N && ny >= 0 && ny < N && bd[ny * N + nx] === 3 - p) {
      line.push(ny * N + nx); nx += dx; ny += dy
    }
    if (line.length && nx >= 0 && nx < N && ny >= 0 && ny < N && bd[ny * N + nx] === p) flips.push(...line)
  }
  return flips
}
function legal(idx) { return legalFor(board.value, turn.value)[idx] || [] }

/** 位置权重：角 100、角旁 -20、边 10，其余 1（经典启发式，公开知识） */
const WEIGHTS = [
  100, -20, 10, 5, 5, 10, -20, 100,
  -20, -50, -2, -2, -2, -2, -50, -20,
  10, -2, 3, 1, 1, 3, -2, 10,
  5, -2, 1, 1, 1, 1, -2, 5,
  5, -2, 1, 1, 1, 1, -2, 5,
  10, -2, 3, 1, 1, 3, -2, 10,
  -20, -50, -2, -2, -2, -2, -50, -20,
  100, -20, 10, 5, 5, 10, -20, 100,
]

function play(idx) {
  if (over.value || thinking.value) return
  if (mode.value !== 'pvp' && turn.value !== (humanIsBlack ? BLACK : WHITE)) return
  const flips = legal(idx)
  if (!flips.length) return
  applyMove(idx)
  if (!over.value && mode.value !== 'pvp') aiTurn()
}

function applyMove(idx) {
  const p = turn.value
  const flips = legalFor(board.value, idx, p)
  board.value[idx] = p
  flips.forEach(i => { board.value[i] = p })
  flipSet.value = new Set(flips)
  lastIdx.value = idx
  advanceTurn()
}

function advanceTurn() {
  const next = 3 - turn.value
  if (legalFor(board.value, next) && Object.keys(legalFor(board.value, next)).length) {
    turn.value = next
  } else if (Object.keys(legalFor(board.value, turn.value)).length) {
    skipNote.value = `${next === BLACK ? '黑方' : '白方'}无子可下，跳过`
    // 同一方继续
  } else {
    over.value = true
  }
}

function aiTurn() {
  thinking.value = true
  timer = setTimeout(() => {
    const p = turn.value
    const legalMap = legalFor(board.value, p)
    const entries = Object.entries(legalMap).map(([idx, flips]) => ({ idx: Number(idx), flips }))
    let pick
    if (mode.value === 'easy' || entries.length === 1) {
      // 贪心：翻最多 + 位置权重
      pick = entries.sort((a, b) =>
        (b.flips.length + WEIGHTS[b.idx] / 10) - (a.flips.length + WEIGHTS[a.idx] / 10))[0]
    } else {
      // 3 层搜索
      let best = -Infinity
      const sorted = entries.sort((a, b) =>
        (WEIGHTS[b.idx] + b.flips.length) - (WEIGHTS[a.idx] + a.flips.length)).slice(0, 8)
      for (const e of sorted) {
        const bd = [...board.value]
        bd[e.idx] = p; e.flips.forEach(i => { bd[i] = p })
        const val = search(bd, 3 - 1, -Infinity, Infinity, 3 - p, p)
        if (val > best) { best = val; pick = e }
      }
      pick = pick || entries[0]
    }
    thinking.value = false
    if (pick) {
      applyMove(Number(pick.idx))
      // AI 落子后对方无合法步被跳过时，AI 继续走（否则会卡死在「轮到 AI」）
      if (!over.value && mode.value !== 'pvp' && turn.value !== (humanIsBlack ? BLACK : WHITE)) aiTurn()
    }
  }, 120)
}

function search(bd, depth, alpha, beta, turnP, aiP) {
  const legalMap = legalFor(bd, turnP)
  const keys = Object.keys(legalMap)
  if (depth === 0 || !keys.length) {
    let ai = 0, hu = 0
    bd.forEach((v, i) => { if (v === aiP) ai += WEIGHTS[i]; else if (v) hu += WEIGHTS[i] })
    return ai - hu
  }
  const maximizing = turnP === aiP
  let best = maximizing ? -Infinity : Infinity
  for (const k of keys) {
    const bd2 = [...bd]
    bd2[k] = turnP; legalMap[k].forEach(i => { bd2[i] = turnP })
    const val = search(bd2, depth - 1, alpha, beta, 3 - turnP, aiP)
    if (maximizing) { best = Math.max(best, val); alpha = Math.max(alpha, val) }
    else { best = Math.min(best, val); beta = Math.min(beta, val) }
    if (beta <= alpha) break
  }
  return best
}

function setMode(k) { mode.value = k; restart() }
onBeforeUnmount(() => { clearTimeout(timer); clearTimeout(saveTimer) })
resetBoard()   // 初始摆子；「继续上一局」由 onMounted 覆盖，不能在这里清档
</script>

<style scoped>
.ot-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.ot-toolbar { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; justify-content: center; width: 100%; }
.ot-modes { display: flex; gap: 6px; }
.ot-mode { padding: 6px 14px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 12.5px; font-family: inherit; }
.ot-mode.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.ot-status { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--dp-text2, #45505b); }
.ot-count { font-weight: 700; font-variant-numeric: tabular-nums; }
.ot-btn { padding: 4px 13px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }

.ot-board {
  position: relative; display: grid; grid-template-columns: repeat(8, var(--cell, 40px)); grid-auto-rows: var(--cell, 40px);
  gap: 2px; padding: 8px; border-radius: 12px; background: #2e6b4f; touch-action: manipulation; user-select: none;
}
.ot-cell { border: none; padding: 0; border-radius: 4px; background: #3c8563; cursor: pointer; position: relative; }
.ot-cell:hover { background: #47996f; }
.ot-cell.hint { box-shadow: inset 0 0 0 2px rgba(199,169,107,.8); }
.ot-disc { position: absolute; inset: 3px; border-radius: 50%; display: block; transition: transform .25s; }
.ot-disc.black { background: radial-gradient(circle at 34% 30%, #555, #111); }
.ot-disc.white { background: radial-gradient(circle at 34% 30%, #fff, #cfcabb); }
.ot-disc.flip { animation: otflip .35s; }
@keyframes otflip { 50% { transform: scaleX(.1) } }
.ot-cell.last::after { content: ''; position: absolute; top: 50%; left: 50%; width: 6px; height: 6px;
  margin: -3px; border-radius: 50%; background: #e5484d; z-index: 2; }
.ot-over {
  position: absolute; inset: 0; border-radius: 12px; background: rgba(0,0,0,.55);
  display: flex; flex-direction: column; gap: 12px; align-items: center; justify-content: center;
}
.ot-over-title { color: #fff; font-size: 19px; font-weight: 800; }
.ot-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center; max-width: 480px; }

@media (max-width: 480px) {
  .ot-board { --cell: 34px; }
}
</style>

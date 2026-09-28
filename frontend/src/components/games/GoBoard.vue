<template>
  <div class="go-wrap" :class="{ 'is-big': big }" :style="{ '--board-w': boardW + 'px' }">
    <!-- ===== 辅栏：玩家条 + 操作（普通模式随主列纵向排；放大模式移到棋盘右侧） ===== -->
    <div class="go-side">
    <div class="go-shell">
      <div class="go-players">
        <div class="go-player" :class="{ active: !over && turn === BLACK }">
          <span class="go-stone-sm black"></span>
          <div class="go-player-txt">
            <b>{{ mode === 'pvp' ? '黑方' : '你' }}</b>
            <i>{{ over ? '—' : (turn === BLACK ? (mode === 'pvp' ? '行棋中' : '你的回合') : '黑') }}</i>
          </div>
          <span class="go-score">{{ over ? score.black + " 目" : "提 " + captured.black }}</span>
        </div>
        <span class="go-vs">⚔</span>
        <div class="go-player" :class="{ active: !over && turn === WHITE }">
          <span class="go-stone-sm white"></span>
          <div class="go-player-txt">
            <b>{{ mode === 'pvp' ? '白方' : 'AI' }}</b>
            <i>{{ over ? '—' : (turn === WHITE ? (mode === 'pvp' ? '行棋中' : '思考中…') : '白') }}</i>
          </div>
          <span class="go-score">{{ over ? score.white + " 目" : "提 " + captured.white }}</span>
        </div>
      </div>

      <div class="go-status">
        <span class="go-info">
          {{ size }}×{{ size }} · 提子 黑 {{ captured.black }} / 白 {{ captured.white }}
          <span v-if="koPoint >= 0" class="go-ko">劫</span>
        </span>
        <button class="go-btn" :disabled="over || thinking" @click="pass">{{ passLabel }}</button>
        <button class="go-btn" @click="restart">重开</button>
        <button class="go-btn" :disabled="!canUndo" @click="undo">悔棋</button>
      </div>

      <div v-if="resultText" class="go-result">{{ resultText }}</div>
    </div>
    </div><!-- /.go-side -->

    <!-- ===== 主区：棋盘（放大模式下独占左侧主位） ===== -->
    <div ref="mainEl" class="go-main">
    <div class="go-boardwrap">
      <div
        class="go-board"
        :style="{ gridTemplateColumns: `repeat(${size}, ${cellPx}px)`, gridAutoRows: cellPx + 'px' }"
        :class="{ locked: thinking || over }"
      >
        <button
          v-for="i in size * size"
          :key="i"
          class="go-cell"
          :class="{ edge: isEdge(i - 1), star: stars.has(i - 1), last: lastIdx === i - 1 }"
          :aria-label="`${Math.floor((i - 1) / size) + 1}行${((i - 1) % size) + 1}列`"
          @click="play(i - 1)"
        >
          <i v-if="board[i - 1]" class="go-stone" :class="board[i - 1] === BLACK ? 'black' : 'white'"></i>
          <i v-else-if="koPoint === i - 1" class="go-ko-mark"></i>
        </button>
      </div>
    </div>
    </div><!-- /.go-main -->

    <p class="go-hint">
      落子于交叉点 · 无气之子被提 · 不能自杀 · 禁立即回提（劫）·
      <span v-if="mode === 'pvp'">双方连续「停一手」即终局，自动数子（中国规则，黑贴 {{ komi }} 目）</span>
      <span v-else>连续停一手即终局，自动数子（中国规则，黑贴 {{ komi }} 目）</span>
    </p>
  </div>
</template>

<script setup>
/** 围棋（自写，中国规则数子法，v2.40.33）。
 *
 * 规则实现：
 *  - 气 / 提子：落子后对四邻的对方棋块做连通块搜索，无气（libs=0）整块提掉
 *  - 禁自杀：提子结算后自己的棋块若仍无气 → 非法
 *  - 打劫：提掉对方**恰好一子**时记下该点，下一手不能立即回提（最经典的简单劫规则）
 *  - 终局：双方连续「停一手」→ 数子（中国规则：子 + 围空；黑贴 7.5 目）
 *
 * AI：**入门级**（提子 > 救自己 > 打吃 > 靠子延伸 + 随机扰动）。
 *     真正的棋力需要 MCTS + 算力，本站服务器纯 CPU、无 GPU，做不到「能下过你」，页面已如实标注。
 * 在线对战未接（服务端当前只认五子棋/黑白棋的 15×15 坐标）。
 */
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'

const props = defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
  boardSize: { type: Number, default: 19 },
  big: { type: Boolean, default: false },   // 页面「放大」：棋盘占左侧主位，其余内容移到右侧辅栏
})

const EMPTY = 0, BLACK = 1, WHITE = 2
const SAVE_KEY = 'go'

const size = ref([9, 13, 19].includes(Number(props.boardSize)) ? Number(props.boardSize) : 19)
const mode = ref(['pvp', 'easy', 'hard'].includes(props.initialMode) ? props.initialMode : 'easy')
const board = ref(Array(size.value * size.value).fill(EMPTY))
const turn = ref(BLACK)
const over = ref(false)
const passes = ref(0)
const koPoint = ref(-1)
const lastIdx = ref(-1)
const captured = reactive({ black: 0, white: 0 })   // 各方**提掉对方**的子数
const winner = ref(0)                                // 0=未定 1=黑胜 2=白胜 3=和
const scoreLine = ref('')
const thinking = ref(false)
const history = ref([])                              // [{ idx, color, koPoint, capturedBefore }]
const komi = 7.5
let aiTimer = null
let saveTimer = null

const modeLabel = computed(() => ({ pvp: '双人', easy: '单机 · 入门', hard: '单机 · 稍强' }[mode.value] || ''))
const aiColor = WHITE
/** 数子（中国规则）：子 + 只邻接单色的空区 */
const score = computed(() => {
  const n = size.value
  const bd = board.value
  let b = 0, w = 0
  for (let i = 0; i < n * n; i++) { if (bd[i] === BLACK) b++; else if (bd[i] === WHITE) w++ }
  const seen = new Uint8Array(n * n)
  for (let i = 0; i < n * n; i++) {
    if (bd[i] !== EMPTY || seen[i]) continue
    const stack = [i], region = []
    seen[i] = 1
    let touchB = false, touchW = false
    while (stack.length) {
      const cur = stack.pop(); region.push(cur)
      for (const nb of neighbors(cur)) {
        if (bd[nb] === EMPTY) { if (!seen[nb]) { seen[nb] = 1; stack.push(nb) } }
        else if (bd[nb] === BLACK) touchB = true
        else touchW = true
      }
    }
    if (touchB && !touchW) b += region.length
    else if (touchW && !touchB) w += region.length
  }
  return { black: b, white: w + komi }
})
const resultText = computed(() => {
  if (!over.value) return ''
  if (winner.value === 3) return `🤝 和棋 · ${scoreLine.value}`
  return `${winner.value === BLACK ? '⚫ 黑胜' : '⚪ 白胜'} · ${scoreLine.value}`
})
const canUndo = computed(() => history.value.length > 0 && !thinking.value)
const passLabel = computed(() => (passes.value ? '停手即终局' : '停一手'))

/* ---------- 棋盘几何 ----------
 * 棋盘总宽 = size * 格宽 + 24（两侧各 12px 木框）。量 .go-main（width:100%），
 * 不能量 .go-boardwrap —— 它是 inline-block，宽度由棋盘自己决定，量了会自我循环。
 * 普通模式：宽度上限 560，玩家条与棋盘**同宽**（--board-w），避免「壳比盘宽」的错位。
 * 放大模式：棋盘独占左栏，上限放大，且再受可用高度约束（不能竖着溢出）。 */
const mainEl = ref(null)
const cellPx = ref(28)
const MAX_BOARD_W = 560        // 普通模式棋盘宽度上限
const BIG_MAX_BOARD_W = 880    // 放大模式棋盘宽度上限
let resizeHandler = null
function measureCell() {
  const el = mainEl.value
  const availW = el?.clientWidth || 0
  if (!availW) { cellPx.value = size.value > 13 ? 20 : 28; return }
  const capW = props.big ? BIG_MAX_BOARD_W : MAX_BOARD_W
  let cell = Math.floor((Math.min(availW, capW) - 24) / size.value)
  if (props.big) {
    const availH = el?.clientHeight || 0
    if (availH > 160) cell = Math.min(cell, Math.floor((availH - 24) / size.value))
  }
  // 上限：普通模式 46（避免 9 路盘把棋子画成巨球），放大模式 64
  cellPx.value = Math.max(12, Math.min(props.big ? 64 : 46, cell))
}
/** 棋盘实际总宽（与 .go-board 盒模型一致），普通模式下供玩家条对齐 */
const boardW = computed(() => size.value * cellPx.value + 24)
// 放大/退出放大：布局从单列切成两栏，容器宽高都变了 → 重新量格宽
watch(() => props.big, () => nextTick(measureCell))
function coord(idx) { return [idx % size.value, Math.floor(idx / size.value)] }
function neighbors(idx) {
  const n = size.value, [x, y] = coord(idx), out = []
  if (x > 0) out.push(idx - 1)
  if (x < n - 1) out.push(idx + 1)
  if (y > 0) out.push(idx - n)
  if (y < n - 1) out.push(idx + n)
  return out
}
function isEdge(idx) { const n = size.value, [x, y] = coord(idx); return x === 0 || y === 0 || x === n - 1 || y === n - 1 }
/** 星位（小目点）：按边长给常用的几个位置 */
const stars = computed(() => {
  const n = size.value, s = new Set()
  const lo = n >= 13 ? 3 : 2
  const mid = (n - 1) / 2
  const pts = [[lo, lo], [lo, n - 1 - lo], [n - 1 - lo, lo], [n - 1 - lo, n - 1 - lo]]
  if (n % 2 === 1) pts.push([mid, mid], [lo, mid], [mid, lo], [mid, n - 1 - lo], [n - 1 - lo, mid])
  pts.forEach(([x, y]) => s.add(y * n + x))
  return s
})

/* ---------- 围棋核心：块 / 气 / 提子 ---------- */
function groupAt(bd, idx) {
  const color = bd[idx]
  const stack = [idx], seen = new Set([idx]), stones = [], libs = new Set()
  while (stack.length) {
    const cur = stack.pop(); stones.push(cur)
    for (const nb of neighbors(cur)) {
      if (bd[nb] === EMPTY) libs.add(nb)
      else if (bd[nb] === color && !seen.has(nb)) { seen.add(nb); stack.push(nb) }
    }
  }
  return { stones, libs: libs.size }
}
/** 试下一手：返回 {board, captured[]} 或 null（非法） */
function tryPlay(bd, idx, color, ko) {
  const n = size.value
  if (idx < 0 || idx >= n * n || bd[idx] !== EMPTY) return null
  const nb = bd.slice()
  nb[idx] = color
  const opp = 3 - color
  const captured = []
  for (const near of neighbors(idx)) {
    if (nb[near] === opp) {
      const g = groupAt(nb, near)
      if (g.libs === 0) { g.stones.forEach(s => { nb[s] = EMPTY }); captured.push(...g.stones) }
    }
  }
  const own = groupAt(nb, idx)
  if (own.libs === 0) return null                       // 禁自杀
  if (ko >= 0 && idx === ko) return null                 // 简单劫：ko 点下一手不能立即回提
  return { board: nb, captured }
}

/* ---------- 落子 ---------- */
function applyMove(idx, color) {
  const res = tryPlay(board.value, idx, color, koPoint.value)
  if (!res) return false
  history.value.push({
    snapshot: board.value.slice(), koPoint: koPoint.value, turn: turn.value,
    lastIdx: lastIdx.value, capBlack: captured.black, capWhite: captured.white,
  })
  board.value = res.board
  koPoint.value = res.captured.length === 1 ? res.captured[0] : -1
  if (color === BLACK) captured.black += res.captured.length
  else captured.white += res.captured.length
  lastIdx.value = idx
  passes.value = 0
  return true
}
function play(idx) {
  if (over.value || thinking.value || board.value[idx] !== EMPTY) return
  if (mode.value !== 'pvp' && turn.value === aiColor) return
  const res = tryPlay(board.value, idx, turn.value, koPoint.value)
  if (!res) { ElMessage.warning('这里不能下（自杀或打劫回提）'); return }
  const mover = turn.value
  applyMove(idx, mover)
  turn.value = 3 - mover
  if (mode.value !== 'pvp' && turn.value === aiColor) scheduleAi()
}
function pass() {
  if (over.value || thinking.value) return
  // 记一手「停手」（不落子，只推进轮次）
  history.value.push({ snapshot: board.value.slice(), koPoint: koPoint.value, turn: turn.value, lastIdx: lastIdx.value, capBlack: captured.black, capWhite: captured.white })
  passes.value++
  koPoint.value = -1
  lastIdx.value = -1
  turn.value = 3 - turn.value
  if (passes.value >= 2) { finishByScore(); return }
  if (mode.value !== 'pvp' && turn.value === aiColor) scheduleAi()
}
function finishByScore() {
  over.value = true
  const s = score.value
  winner.value = s.black > s.white ? BLACK : (s.white > s.black ? WHITE : 3)
  scoreLine.value = `黑 ${s.black} 目 · 白 ${s.white} 目（含贴目 ${komi}）`
  clearGame(SAVE_KEY)
}
function restart() {
  clearTimeout(aiTimer)
  clearGame(SAVE_KEY)
  board.value = Array(size.value * size.value).fill(EMPTY)
  turn.value = BLACK
  over.value = false
  passes.value = 0
  koPoint.value = -1
  lastIdx.value = -1
  captured.black = 0; captured.white = 0
  winner.value = 0
  scoreLine.value = ''
  thinking.value = false
  history.value = []
  nextTick(measureCell)
}
function undo() {
  if (!canUndo.value) return
  clearTimeout(aiTimer)
  thinking.value = false
  const steps = mode.value === 'pvp' ? 1 : Math.min(2, history.value.length)
  for (let i = 0; i < steps; i++) {
    const h = history.value.pop()
    if (!h) break
    board.value = h.snapshot
    koPoint.value = h.koPoint
    turn.value = h.turn
    lastIdx.value = h.lastIdx
    captured.black = h.capBlack
    captured.white = h.capWhite
    over.value = false
    winner.value = 0
    scoreLine.value = ''
  }
}

/* ---------- AI（入门级） ---------- */
function candidatesForAi(bd) {
  const n = size.value, out = []
  let any = false
  for (let i = 0; i < n * n; i++) if (bd[i]) { any = true; break }
  if (!any) return [[Math.floor(n / 2) * n + Math.floor(n / 2)]]
  for (let i = 0; i < n * n; i++) {
    if (bd[i] !== EMPTY) continue
    let near = false
    for (const nb of neighbors(i)) if (bd[nb]) { near = true; break }
    if (!near) continue
    // 再放宽一圈
    for (const nb of neighbors(i)) for (const nb2 of neighbors(nb)) if (bd[nb2]) { near = true; break }
    out.push(i)
  }
  return out
}
function evalMove(bd, idx, color, ko) {
  const res = tryPlay(bd, idx, color, ko)
  if (!res) return -Infinity
  let s = res.captured.length * 120                       // 能提子最好
  const own = groupAt(res.board, idx)
  s += Math.min(own.libs, 6) * 14                          // 自己的气
  const opp = 3 - color
  let oppPressure = 0
  for (const nb of neighbors(idx)) {
    if (res.board[nb] === opp) {
      const g = groupAt(res.board, nb)
      if (g.libs === 1) oppPressure += 90                  // 打吃
      else if (g.libs === 2) oppPressure += 30
    }
  }
  s += oppPressure
  const n = size.value, [x, y] = coord(idx)
  const edgeDist = Math.min(x, y, n - 1 - x, n - 1 - y)
  s -= Math.max(0, 3 - edgeDist) * 6                       // 别老贴着边
  s += Math.random() * 12
  return s
}
function bestMove(bd, color, ko, depth) {
  const cands = candidatesForAi(bd)
  let best = null, bestVal = -Infinity
  for (const idx of cands) {
    if (bd[idx] !== EMPTY) continue
    const res = tryPlay(bd, idx, color, ko)
    if (!res) continue
    let val = evalMove(bd, idx, color, ko)
    if (depth > 1) {
      // 稍强档：扣掉对手最佳回应的收益（一层）
      let worst = 0
      const oppCands = candidatesForAi(res.board)
      for (const oi of oppCands) {
        if (res.board[oi] !== EMPTY) continue
        const ov = evalMove(res.board, oi, 3 - color, -1)
        if (ov > worst) worst = ov
      }
      val -= worst * 0.8
    }
    if (val > bestVal) { bestVal = val; best = idx }
  }
  return best
}
function scheduleAi() {
  thinking.value = true
  aiTimer = setTimeout(() => {
    const depth = mode.value === 'hard' ? 2 : 1
    const idx = bestMove(board.value, aiColor, koPoint.value, depth)
    thinking.value = false
    if (idx == null) { pass(); return }
    applyMove(idx, aiColor)
    turn.value = BLACK
  }, 220)
}

/* ---------- 存档 ---------- */
function saveLocal() {
  if (over.value || !history.value.length) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveGame(SAVE_KEY, {
      mode: mode.value,
      summary: `${modeLabel.value} · ${size.value} 路 · 已下 ${history.value.length} 手`,
      size: size.value,
      board: board.value,
      turn: turn.value,
      koPoint: koPoint.value,
      lastIdx: lastIdx.value,
      passes: passes.value,
      capBlack: captured.black,
      capWhite: captured.white,
    })
  }, 500)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !Array.isArray(s.board) || !s.size) return false
  size.value = s.size
  if (s.mode) mode.value = s.mode
  board.value = s.board
  turn.value = s.turn || BLACK
  koPoint.value = typeof s.koPoint === 'number' ? s.koPoint : -1
  lastIdx.value = typeof s.lastIdx === 'number' ? s.lastIdx : -1
  passes.value = s.passes || 0
  captured.black = s.capBlack || 0
  captured.white = s.capWhite || 0
  history.value = []          // 续局不保留悔棋栈（存档体积考虑）
  over.value = false
  ElMessage.success('已继续上一局（续局后不能悔棋）')
  nextTick(measureCell)
  return true
}
watch([board, over], saveLocal, { deep: true })

onMounted(() => {
  resizeHandler = () => measureCell()
  window.addEventListener('resize', resizeHandler, { passive: true })
  nextTick(measureCell)
  if (props.resume && restoreLocal()) return
  if (mode.value !== 'pvp' && turn.value === aiColor) scheduleAi()
})
onBeforeUnmount(() => {
  clearTimeout(aiTimer); clearTimeout(saveTimer)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})
</script>

<style scoped>
.go-wrap { display: flex; flex-direction: column; align-items: center; gap: 14px; width: 100%; }

/* 辅栏容器：普通模式 display:contents → 子项直接参与 .go-wrap 的纵向排列 */
.go-side { display: contents; }
/* 主区（棋盘所在列）：普通模式占满宽度并居中棋盘 */
.go-main { width: 100%; display: flex; justify-content: center; }

/* ===== 放大模式：左主棋盘 + 右辅栏，主次分明 ===== */
.go-wrap.is-big {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px 22px;
  width: 100%; height: 100%; min-height: 0;
}
.go-wrap.is-big .go-side {
  display: flex; flex-direction: column; gap: 12px;
  grid-column: 2; grid-row: 1; width: 100%; max-height: 100%;
  overflow-y: auto; align-self: start;
}
.go-wrap.is-big .go-shell { width: 100%; max-width: 100%; }
.go-wrap.is-big .go-players { gap: 10px; }
.go-wrap.is-big .go-player { max-width: none; }
.go-wrap.is-big .go-main {
  grid-column: 1; grid-row: 1; width: 100%; height: 100%; min-height: 0;
  align-items: center;
}
.go-wrap.is-big .go-hint { grid-column: 1; grid-row: 2; justify-self: center; }

/* 玩家条宽度 = 棋盘宽（--board-w，由 boardW 计算），与棋局左右边缘严格对齐 */
.go-shell {
  width: var(--board-w, 100%); max-width: 100%; border-radius: 18px; padding: 14px 16px;
  background: linear-gradient(160deg, rgba(255,255,255,.75), rgba(255,255,255,.45));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  box-shadow: 0 8px 28px rgba(20,30,40,.08), inset 0 1px 0 rgba(255,255,255,.6);
  display: flex; flex-direction: column; gap: 10px;
}
.go-players { display: flex; align-items: center; justify-content: center; gap: 16px; }
.go-player {
  flex: 1; display: flex; align-items: center; gap: 9px; padding: 8px 12px; border-radius: 13px;
  border: 1px solid transparent; transition: all .25s; max-width: 220px;
}
.go-player.active { border-color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.1); box-shadow: 0 0 0 3px rgba(199,169,107,.15); }
.go-player-txt { min-width: 0; }
.go-player-txt b { display: block; font-size: 13.5px; color: var(--dp-text, #18202a); }
.go-player-txt i { font-style: normal; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.go-score { margin-left: auto; font-size: 12.5px; font-weight: 700; color: var(--yq-gold, #c7a96b); }
.go-score em { font-style: normal; font-weight: 400; font-size: 10.5px; opacity: .8; }
.go-stone-sm { width: 20px; height: 20px; border-radius: 50%; flex: none; box-shadow: 0 2px 5px rgba(0,0,0,.25); }
.go-stone-sm.black { background: radial-gradient(circle at 34% 30%, #555, #111); }
.go-stone-sm.white { background: radial-gradient(circle at 34% 30%, #fff, #cfcabb); }
.go-vs { font-size: 16px; color: var(--dp-text3, #8a8f98); }
.go-status { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center; font-size: 12px; }
.go-info { color: var(--dp-text3, #8a8f98); }
.go-ko { color: #d9534f; font-weight: 700; margin-left: 4px; }
.go-btn {
  padding: 5px 13px; border-radius: 9px; font-size: 12px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b);
}
.go-btn:disabled { opacity: .45; cursor: default; }
.go-result { text-align: center; font-size: 13.5px; font-weight: 700; color: var(--yq-gold, #c7a96b); }

/* 棋盘：木色底 + 交叉点网格；棋子落在**交叉点**上 */
.go-boardwrap { display: inline-block; }
.go-board {
  display: grid; padding: 12px; border-radius: 12px;
  background: linear-gradient(135deg, #e6cd9f, #d9bb84);
  box-shadow: inset 0 0 0 1px rgba(90,74,52,.35), 0 10px 30px rgba(20,30,40,.14);
  touch-action: manipulation; user-select: none; transition: filter .2s;
}
.go-board.locked { filter: saturate(.85) brightness(.97); pointer-events: none; }
.go-cell {
  position: relative; border: none; padding: 0; background: transparent; cursor: pointer;
}
/* 交叉点：横竖线各一条（第一列/行补半截，视觉上是完整棋盘格线） */
.go-cell::before {
  content: ''; position: absolute; left: 0; right: 0; top: 50%; height: 1px;
  background: rgba(90, 74, 52, .75);
}
.go-cell::after {
  content: ''; position: absolute; top: 0; bottom: 0; left: 50%; width: 1px;
  background: rgba(90, 74, 52, .75);
}
.go-cell.star { background: radial-gradient(circle, rgba(90, 74, 52, .9) 0 2.4px, transparent 2.6px); }
.go-stone { position: absolute; inset: 6%; border-radius: 50%; display: block; z-index: 2; }
.go-stone.black { background: radial-gradient(circle at 34% 30%, #5a5a5a, #0b0b0b); box-shadow: 0 2px 4px rgba(0,0,0,.35); }
.go-stone.white { background: radial-gradient(circle at 34% 30%, #fff, #cbc6b7); box-shadow: 0 2px 4px rgba(0,0,0,.25); }
.go-cell.last::after { z-index: 3; }
.go-cell.last > .go-stone { box-shadow: 0 0 0 2px rgba(199,169,107,.95); }
.go-ko-mark {
  position: absolute; inset: 34%; border-radius: 50%; background: rgba(217,83,79,.85); z-index: 1;
}
.go-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center; line-height: 1.8; max-width: 520px; }

@media (max-width: 480px) {
  .go-shell { padding: 10px 12px; }
  .go-players { gap: 8px; }
  .go-player { padding: 6px 9px; }
}

/* 窄屏：放大模式退回单列（棋盘在上、辅栏在下），避免两栏把棋盘挤成一条 */
@media (max-width: 900px) {
  .go-wrap.is-big { grid-template-columns: 1fr; grid-template-rows: auto auto auto; height: auto; }
  .go-wrap.is-big .go-side { grid-column: 1; grid-row: 1; max-height: none; overflow: visible; }
  .go-wrap.is-big .go-main { grid-column: 1; grid-row: 2; height: auto; }
  .go-wrap.is-big .go-hint { grid-column: 1; grid-row: 3; }
}

/* ===== 夜间主题：深木纹棋盘 + 深色玻璃壳（与五子棋一致，避免白壳压在纯黑底上发灰看不清） ===== */
:root[data-theme="night"] .go-shell {
  background: linear-gradient(160deg, rgba(38,44,58,.94), rgba(22,26,36,.92));
  border-color: rgba(199,169,107,.3);
  box-shadow: 0 8px 28px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.07);
}
:root[data-theme="night"] .go-player-txt b { color: #f2eee4; }
:root[data-theme="night"] .go-player-txt i { color: #b9b3cc; }
:root[data-theme="night"] .go-player.active { background: rgba(199,169,107,.18); }
:root[data-theme="night"] .go-vs,
:root[data-theme="night"] .go-info { color: #b9b3cc; }
:root[data-theme="night"] .go-hint { color: #a9a3bd; }
:root[data-theme="night"] .go-btn {
  background: rgba(255,255,255,.09); border-color: rgba(255,255,255,.2); color: #ece7dc;
}
:root[data-theme="night"] .go-btn:hover:not(:disabled) { border-color: rgba(252,211,77,.6); color: #fde68a; }
:root[data-theme="night"] .go-board {
  background: linear-gradient(135deg, #6d5836, #4f3f26);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.12), 0 10px 30px rgba(0,0,0,.55);
}
:root[data-theme="night"] .go-cell::before,
:root[data-theme="night"] .go-cell::after { background: rgba(255, 236, 190, .5); }
:root[data-theme="night"] .go-cell.star {
  background: radial-gradient(circle, rgba(255,236,190,.85) 0 2.4px, transparent 2.6px);
}
:root[data-theme="night"] .go-stone.black { box-shadow: 0 0 0 1px rgba(255,255,255,.22); }
:root[data-theme="night"] .go-stone.white { box-shadow: 0 0 0 1px rgba(0,0,0,.35); }
</style>

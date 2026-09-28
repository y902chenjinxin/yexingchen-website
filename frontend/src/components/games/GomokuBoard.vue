<template>
  <div class="gk-wrap">
    <div class="gk-toolbar">
      <div class="gk-modes">
        <button v-for="m in modes" :key="m.key" class="gk-mode" :class="{ on: mode === m.key }" @click="setMode(m.key)">{{ m.label }}</button>
      </div>
      <div class="gk-status">
        <template v-if="mode === 'online'">
          <span v-if="!gRoom.room.value">{{ '邀请一位家人开一局' }}</span>
          <span v-else-if="gRoom.status.value === 'waiting'">等待 {{ gRoom.opponentName.value }} 接受…</span>
          <span v-else-if="gRoom.status.value === 'playing'">
            {{ gRoom.myTurn.value ? '轮到你（' + (myColor === HUMAN ? '黑' : '白') + '）' : '等对方落子…' }}
          </span>
          <span v-else class="gk-result">{{ onlineResultText }}</span>
        </template>
        <template v-else>
          <span v-if="!over" :class="{ turn: turn === HUMAN }">{{ turn === HUMAN ? '轮到你（黑）' : (mode === 'pvp' ? '轮到白方' : 'AI 思考中…') }}</span>
          <span v-else class="gk-result">{{ resultText }}</span>
        </template>
        <button class="gk-btn" @click="restart">重开</button>
        <button v-if="mode !== 'online'" class="gk-btn" :disabled="!canUndo" @click="undo">悔棋</button>
      </div>
    </div>

    <!-- 在线：邀请面板 / 房间操作 -->
    <div v-if="mode === 'online'" class="gk-online glass">
      <template v-if="!gRoom.room.value">
        <span>对手：</span>
        <select v-model="inviteeId" class="gk-select">
          <option v-for="f in families" :key="f.user_id" :value="f.user_id">{{ f.avatar }} {{ f.name }}</option>
        </select>
        <button class="gk-btn primary" :disabled="!inviteeId || gRoom.joining.value" @click="invite">
          {{ gRoom.joining.value ? '创建中…' : '发出邀请' }}
        </button>
        <span class="gk-hint">对方在线会立刻弹窗，收到邀请后接受即可开局</span>
      </template>
      <template v-else>
        <span>对局编号 #{{ gRoom.room.value.id }} · 对手：{{ gRoom.opponentName.value }}</span>
        <button v-if="gRoom.status.value === 'waiting'" class="gk-btn" @click="cancelInvite">取消邀请</button>
        <button v-if="gRoom.status.value === 'waiting'" class="gk-btn" @click="refreshRoom">刷新</button>
        <button v-if="gRoom.status.value === 'playing'" class="gk-btn" @click="resignOnline">认输</button>
        <button v-if="gRoom.status.value === 'finished'" class="gk-btn primary" @click="reinviteSame">再来一局</button>
      </template>
    </div>

    <div class="gk-board" :style="{ '--n': N }">
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
    <p class="gk-hint">黑方先行 · 五子连珠获胜 · 在线模式对方落子后棋盘自动更新（约 2 秒内）</p>
  </div>
</template>

<script setup>
/** 五子棋（自写，无外部依赖）。
 * 本地：双人 / 简单(贪心) / 困难(3 层极小化极大 + Alpha-Beta + 棋型打分表，公开算法自研实现)。
 * 在线（v2.40.25）：useGameRoom 房间会话 —— 邀请家人 → 接受 → 轮询同步落子；
 * 服务端权威 = 轮次 / 占位 / 五连胜负，棋盘状态由事件重放。
 */
import { ref, computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useGameRoom } from '@/composables/useGameRoom'
import { familyMembers } from '@/api/lifeExtra'

const N = 15
const HUMAN = 1, AI = 2
const modes = [
  { key: 'pvp', label: '双人（同屏）' },
  { key: 'easy', label: '单机 · 简单' },
  { key: 'hard', label: '单机 · 困难' },
  { key: 'online', label: '在线 · 邀请对战' },
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

/* ---------- 在线对战 ---------- */
const families = ref([])
const inviteeId = ref(null)
const onlineWinner = ref('')   // 'me' | 'opp' | 'draw'
const myColor = ref(HUMAN)     // 在线座位：房主执黑

function onRemoteMove(action) {
  const idx = action?.idx
  if (typeof idx !== 'number' || board.value[idx]) return
  const color = 3 - turn.value        // 轮到谁，落的就是谁的颜色
  board.value[idx] = color
  lastIdx.value = idx
  history.value.push(idx)
  const line = checkWinFrom(board.value, idx, color)
  if (line) { winLine.value = line; winner.value = color; over.value = true }
  turn.value = color === HUMAN ? AI : HUMAN
}
function onRoomStatus(s) {
  if (s.status === 'finished') {
    over.value = true
    const uid = Number(gRoom.myUserId.value)
    onlineWinner.value = !s.winner_id ? 'draw' : (s.winner_id === uid ? 'me' : 'opp')
  }
}
const gRoom = useGameRoom('gomoku', { onRemoteMove, onStatus: onRoomStatus })

const onlineResultText = computed(() =>
  onlineWinner.value === 'me' ? '🎉 你赢了' : onlineWinner.value === 'opp' ? '对方赢了' : '🤝 平局')

async function loadFamilies() {
  try {
    const res = await familyMembers()
    families.value = (res?.data?.list || []).filter(m => m.user_id && m.user_id !== Number(gRoom.myUserId.value))
  } catch { families.value = [] }
}
async function invite() {
  if (!inviteeId.value) { ElMessage.warning('先选一位家人'); return }
  try {
    await gRoom.createInvite(inviteeId.value)
    ElMessage.success('邀请已发出，等对方接受')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '邀请失败')
  }
}
async function cancelInvite() {
  await gRoom.cancel()
  ElMessage.success('已取消')
}
async function reinviteSame() {
  gRoom.reset()
  clearLocal()
  if (inviteeId.value) await gRoom.createInvite(inviteeId.value)
}
function resignOnline() { gRoom.resign(); over.value = true; onlineWinner.value = 'opp' }
async function refreshRoom() { if (gRoom.room.value?.id) await gRoom.join(gRoom.room.value.id, { autoAccept: false }) }
/** 其他会话/全局弹窗接受后跳转进来：由父组件传 joinRoomId */
const props = defineProps({ joinRoomId: { type: Number, default: 0 } })
watch(() => props.joinRoomId, (id) => {
  if (!id) return
  mode.value = 'online'
  clearLocal()
  gRoom.join(Number(id), { autoAccept: true }).then(() => {
    myColor.value = gRoom.mySeat.value === 'black' ? HUMAN : AI
    ElMessage.success('已进入对局')
  })
})

const onlinePlaying = computed(() => mode.value === 'online' && gRoom.status.value === 'playing')
const onlineMyTurn = computed(() => onlinePlaying.value && gRoom.myTurn.value)

/* ---------- 本地对局逻辑（双人 / AI） ---------- */
const canUndo = computed(() => history.value.length > 0 && !thinking.value && mode.value !== 'online')
const resultText = computed(() => {
  if (winner.value === HUMAN) return mode.value === 'pvp' ? '🎉 黑方胜' : '🎉 你赢了'
  if (winner.value === AI) return mode.value === 'pvp' ? '🎉 白方胜' : 'AI 赢了，再来'
  return '🤝 平局'
})

function clearLocal() {
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
function setMode(k) {
  mode.value = k
  clearLocal()
  gRoom.reset()
  if (k === 'online') { myColor.value = HUMAN; loadFamilies() }
}
function restart() {
  if (mode.value === 'online') { gRoom.reset(); clearLocal(); loadFamilies(); return }
  clearLocal()
  if (mode.value !== 'pvp') return
}

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
function search(bd, depth, alpha, beta, maximizing) {
  if (depth === 0) return evaluateBoard(bd)
  const p = maximizing ? AI : HUMAN
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
    bd[idx] = 0
    if (maximizing) { best = Math.max(best, val); alpha = Math.max(alpha, val) }
    else { best = Math.min(best, val); beta = Math.min(beta, val) }
    if (beta <= alpha) break
  }
  return best
}
function evaluateBoard(bd) {
  let ai = 0, hu = 0
  for (const idx of candidates(bd)) {
    ai = Math.max(ai, pointScore(bd, idx, AI))
    hu = Math.max(hu, pointScore(bd, idx, HUMAN))
  }
  return ai - hu * 1.1
}

function place(idx) {
  history.value.push(idx)
  board.value[idx] = turn.value
  lastIdx.value = idx
  const line = checkWinFrom(board.value, idx, turn.value)
  if (line) { winLine.value = line; winner.value = turn.value; over.value = true }
  else if (board.value.every(v => v)) { over.value = true }
}

function play(idx) {
  if (over.value || thinking.value || board.value[idx]) return
  // ---------- 在线 ----------
  if (mode.value === 'online') {
    if (!onlineMyTurn.value) return
    const color = myColor.value
    board.value[idx] = color
    lastIdx.value = idx
    history.value.push(idx)
    turn.value = color === HUMAN ? AI : HUMAN
    const line = checkWinFrom(board.value, idx, color)
    if (line) { winLine.value = line; over.value = true }
    gRoom.send({ idx }).catch(() => {
      ElMessage.warning('落子同步失败，正在恢复局面…')
      gRoom.join(gRoom.room.value.id).then(() => {
        clearLocal()
        for (const m of gRoom.moves.value) onRemoteMove(m.action, m.user_id)
      })
    })
    return
  }
  // ---------- 本地 ----------
  if (mode.value !== 'pvp' && turn.value !== HUMAN) return
  place(idx)
  if (over.value) return
  if (mode.value !== 'pvp') {
    turn.value = AI
    aiMove()
  } else {
    turn.value = 3 - turn.value
  }
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
  if (!history.value.length || thinking.value || mode.value === 'online') return
  clearTimeout(timer)
  const steps = mode.value === 'pvp' ? 1 : (history.value.length >= 2 ? 2 : 1)
  for (let i = 0; i < steps && history.value.length; i++) {
    const idx = history.value.pop()
    board.value[idx] = 0
  }
  over.value = false; winner.value = 0; winLine.value = []
  lastIdx.value = history.value[history.value.length - 1] ?? -1
  turn.value = HUMAN
}

onMounted(async () => {
  if (mode.value === 'online') loadFamilies()
})
onBeforeUnmount(() => { clearTimeout(timer); gRoom.stopPoll() })
</script>

<style scoped>
.gk-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.gk-toolbar { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; justify-content: center; width: 100%; }
.gk-modes { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.gk-mode { padding: 6px 14px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 12.5px; font-family: inherit; }
.gk-mode.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gk-status { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--dp-text2, #45505b); }
.gk-result { font-weight: 700; color: var(--yq-gold, #c7a96b); }
.gk-btn { padding: 4px 13px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }
.gk-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; }
.gk-btn:disabled { opacity: .5; cursor: default; }
.gk-online { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center;
  padding: 10px 16px; border-radius: 12px; font-size: 13px; color: var(--dp-text2, #45505b); width: 100%; }
.gk-select { border: 1px solid var(--dp-line, rgba(0,0,0,.14)); border-radius: 8px; padding: 6px 9px;
  font-size: 13px; background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-family: inherit; }

.gk-board {
  display: grid; grid-template-columns: repeat(15, var(--cell, 26px)); grid-auto-rows: var(--cell, 26px);
  background: linear-gradient(135deg, #e8d9b8, #dcc79a); padding: 8px; border-radius: 12px;
  touch-action: manipulation; user-select: none; box-shadow: inset 0 0 0 1px rgba(0,0,0,.15);
}
.gk-cell { border: none; padding: 0; background: transparent; cursor: pointer; position: relative;
  box-shadow: inset -1px 0 0 rgba(0,0,0,.25), inset 0 -1px 0 rgba(0,0,0,.25); }
.gk-stone { position: absolute; inset: 2px; border-radius: 50%; display: block; }
.gk-stone.black { background: radial-gradient(circle at 34% 30%, #555, #111); }
.gk-stone.white { background: radial-gradient(circle at 34% 30%, #fff, #cfcabb); }
.gk-cell.last::after { content: ''; position: absolute; top: 50%; left: 50%; width: 5px; height: 5px;
  margin: -2.5px; border-radius: 50%; background: #e5484d; z-index: 2; }
.gk-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center; }

@media (max-width: 480px) {
  .gk-board { --cell: 21px; padding: 6px; }
}
</style>

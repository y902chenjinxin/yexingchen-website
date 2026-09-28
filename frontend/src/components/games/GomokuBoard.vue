<template>
  <div class="gk-wrap">
    <!-- ===== 玩家条：头像对峙 + 回合指示（质感壳） ===== -->
    <div class="gk-shell">
      <div class="gk-players">
        <div class="gk-player" :class="{ active: activeColor === HUMAN }">
          <span class="gk-stone-sm black"></span>
          <div class="gk-player-txt">
            <b>{{ blackName }}</b>
            <i>{{ activeColor === HUMAN && !over ? (modeLabel === '在线' ? '行棋中' : '你的回合') : '黑' }}</i>
          </div>
        </div>
        <span class="gk-vs">⚔</span>
        <div class="gk-player" :class="{ active: activeColor === AI }">
          <span class="gk-stone-sm white"></span>
          <div class="gk-player-txt">
            <b>{{ whiteName }}</b>
            <i>{{ activeColor === AI && !over ? (modeLabel === '在线' ? '等待落子' : '思考中…') : '白' }}</i>
          </div>
        </div>
      </div>

      <!-- 模式（页面已选则隐藏；房间激活时锁定） -->
      <div v-if="!bare" class="gk-modes" :class="{ locked: roomLocked }">
        <button
          v-for="m in modes"
          :key="m.key"
          class="gk-mode"
          :class="{ on: mode === m.key }"
          :disabled="roomLocked && mode !== m.key"
          :title="roomLocked && mode !== m.key ? '对局进行中，退出后才能切换' : ''"
          @click="setMode(m.key)"
        >{{ m.label }}</button>
      </div>

      <!-- 本地对局操作：重开 / 悔棋 -->
      <div v-if="mode !== 'online'" class="gk-status">
        <span v-if="over" class="gk-result">{{ resultText }}</span>
        <button class="gk-btn" @click="restart">重开</button>
        <button class="gk-btn" :disabled="!canUndo" @click="undo">悔棋</button>
      </div>

      <!-- 房间状态横幅（waiting / playing 结果提示） -->
      <div v-if="mode === 'online' && gRoom.room.value" class="gk-banner" :class="'st-' + gRoom.status.value">
        <template v-if="gRoom.status.value === 'waiting'">
          <span class="gk-pulse"></span> 邀请已发给 {{ gRoom.opponentName.value }}，等待接受…
          <span class="gk-firstnote">{{ gRoom.room.value.black_name }} 执黑先行</span>
          <button class="gk-btn" @click="cancelInvite">取消邀请</button>
          <button class="gk-btn" @click="refreshRoom">刷新</button>
        </template>
        <template v-else-if="gRoom.status.value === 'playing'">
          <span>{{ gRoom.myTurn.value ? '轮到你落子' : '等对方落子…' }}</span>
          <button class="gk-btn" @click="askExit">退出对局（认输）</button>
        </template>
        <template v-else-if="gRoom.status.value === 'finished'">
          <span class="gk-result">{{ onlineResultText }}</span>
          <button class="gk-btn primary" @click="reinviteSame">再来一局</button>
          <button class="gk-btn" @click="exitOnline">退出</button>
        </template>
      </div>
    </div>

    <!-- 在线：邀请面板（尚未建房时） -->
    <div v-if="mode === 'online' && !gRoom.room.value" class="gk-online">
      <div class="gk-online-title">🎯 在线邀请对战</div>
      <p class="gk-online-desc">选一位家人发出邀请，对方接受后进入对局；落子自动同步，约 2 秒内可见。</p>
      <div class="gk-online-row">
        <select v-model="inviteeId" class="gk-select">
          <option v-for="f in families" :key="f.user_id" :value="f.user_id">{{ f.avatar }} {{ f.display_name }}</option>
        </select>
      </div>
      <div class="gk-first-row">
        <span class="gk-first-label">先手：</span>
        <button class="gk-mode" :class="{ on: firstPick === 'me' }" @click="firstPick = 'me'">我执黑</button>
        <button class="gk-mode" :class="{ on: firstPick === 'other' }" @click="firstPick = 'other'">对方执黑</button>
      </div>
      <div class="gk-online-row">
        <button class="gk-btn primary" :disabled="!inviteeId || gRoom.joining.value" @click="invite">
          {{ gRoom.joining.value ? '创建中…' : '发出邀请' }}
        </button>
      </div>
      <p v-if="!families.length" class="gk-online-desc">家庭里还没有其他账号可以邀请。</p>
    </div>

    <div ref="wrapEl" class="gk-boardwrap">
      <div
        class="gk-board"
        :class="{ locked: boardLocked, 'has-winner': winLine.length }"
        :style="{ gridTemplateColumns: `repeat(${N}, ${cellPx}px)`, gridAutoRows: cellPx + 'px' }"
      >
        <button
          v-for="idx in N * N"
          :key="idx"
          class="gk-cell"
          :class="{ last: lastIdx === domToInner(idx - 1), win: winDomSet.has(idx - 1) }"
          :aria-label="`第${Math.ceil(idx / N)}行第${((idx - 1) % N) + 1}列`"
          @click="play(idx - 1)"
        >
          <i v-if="board[domToInner(idx - 1)]" class="gk-stone" :class="board[domToInner(idx - 1)] === HUMAN ? 'black' : 'white'"></i>
        </button>
      </div>
      <!-- 锁定时给出可见原因（此前是静默 pointer-events:none，点了毫无反馈） -->
      <div v-if="lockHint" class="gk-lockmask"><span>{{ lockHint }}</span></div>
    </div>
    <p class="gk-hint">
      <template v-if="mode === 'online'">在线模式 · 对方落子约 2 秒内自动出现</template>
      <template v-else>
        黑方先行 · 五子连珠获胜 · 困难模式 AI 搜索更深
        <span v-if="expands" class="gk-expandnote">· 棋盘已向外扩展 {{ expands }}/3 次（现 {{ N }}×{{ N }}）</span>
      </template>
    </p>
  </div>
</template>

<script setup>
/** 五子棋（自写，无外部依赖）。
 * 本地：双人 / 简单(贪心) / 困难(3 层极小化极大 + Alpha-Beta + 棋型打分表，公开算法自研实现)。
 * 在线（v2.40.25→v2.40.26 重构）：useGameRoom 房间会话；
 *   - 房间激活（waiting/playing）时**锁定模式与页面**（父组件收 room-lock 事件禁用游戏 tab），
 *     只有「退出对局」能解锁 —— 修复「第二个人还能自己直接操作/随意切换」的问题
 *   - 邀请下拉修复：显示家人名字（此前误读字段名只显示了头像 emoji）
 *   - 恢复：进页面自动接回自己进行中的房间（刷新/换设备都不丢）
 */
import { ref, computed, nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGameRoom } from '@/composables/useGameRoom'
import { familyMembers } from '@/api/lifeExtra'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'

const emit = defineEmits(['room-lock', 'room-unlock'])
const props = defineProps({
  initialMode: { type: String, default: '' },   // 模式由页面「第一步」选定（v2.40.29）
  resume: { type: Boolean, default: false },    // 从本地存档续局
  bare: { type: Boolean, default: false },      // 隐藏内置模式段（模式已在页面上选过）
  joinRoomId: { type: Number, default: 0 },     // 受邀跳转进来：直接进指定房间
})

/* ---------- 棋盘尺寸：内部满盘固定，外部开放区可扩（v2.40.30） ----------
 * 内部一律用 FULL×FULL 的坐标存棋子（27×27），**永不重映射**；
 * 开放区是它中心的方块，起始 15×15，棋子落到距离边缘 1 线以内就向外扩 2 圈，
 * 最多 3 次：15 → 19 → 23 → 27。
 * 这样扩展只是「放大窗口」，已落的子、AI 搜索、胜负判定都不受影响。
 * 在线对局不扩展（服务端棋盘固定 15×15，srv2in/in2srv 做坐标翻译）。 */
const FULL = 27
const BASE_MARGIN = 6                       // (27 - 6*2) = 15 起始边长
const SRV_N = 15                            // 服务端棋盘边长
const margin = ref(BASE_MARGIN)             // 开放区外留的边距：6 → 4 → 2 → 0
const N = computed(() => FULL - margin.value * 2)          // 对外边长 15/19/23/27
const expands = computed(() => (BASE_MARGIN - margin.value) / 2)   // 已扩展次数 0..3

const HUMAN = 1, AI = 2
const modes = [
  { key: 'pvp', label: '双人（同屏）' },
  { key: 'easy', label: '单机 · 简单' },
  { key: 'hard', label: '单机 · 困难' },
  { key: 'online', label: '在线 · 邀请对战' },
]
const mode = ref(props.initialMode || 'easy')
const board = ref(Array(FULL * FULL).fill(0))
const turn = ref(HUMAN)
const over = ref(false)
const winner = ref(0)
const winLine = ref([])
const lastIdx = ref(-1)
const history = ref([])
const thinking = ref(false)
let timer = null

/* ---------- 坐标换算 ---------- */
/** DOM 格序号（0..N*N-1）→ 内部索引 */
function domToInner(d) {
  const n = N.value, m = margin.value
  const x = d % n, y = (d / n) | 0
  return (y + m) * FULL + (x + m)
}
/** 内部索引 → DOM 格序号（不在开放区返回 -1） */
function innerToDom(i) {
  const n = N.value, m = margin.value
  const x = i % FULL, y = (i / FULL) | 0
  const dx = x - m, dy = y - m
  if (dx < 0 || dy < 0 || dx >= n || dy >= n) return -1
  return dy * n + dx
}
/** 服务端 15×15 索引 ↔ 内部索引（在线对局用；服务端棋盘永远是起始那 15×15） */
function srvToInner(s) {
  const x = s % SRV_N, y = (s / SRV_N) | 0
  return (y + BASE_MARGIN) * FULL + (x + BASE_MARGIN)
}
function innerToSrv(i) {
  const x = (i % FULL) - BASE_MARGIN, y = ((i / FULL) | 0) - BASE_MARGIN
  if (x < 0 || y < 0 || x >= SRV_N || y >= SRV_N) return -1
  return y * SRV_N + x
}
/** 胜利连子对应的 DOM 格（高亮用），一次算好 */
const winDomSet = computed(() => new Set(winLine.value.map(innerToDom).filter(i => i >= 0)))

/* ---------- 棋盘自适应：格宽 = min(26, (容器宽 - 内边距) / 边长) ---------- */
const wrapEl = ref(null)
const cellPx = ref(26)
let resizeHandler = null
function measureCell() {
  const w = wrapEl.value?.clientWidth || 0
  if (!w) { cellPx.value = N.value > 19 ? 20 : 26; return }
  cellPx.value = Math.max(13, Math.min(26, Math.floor((w - 20) / N.value)))
}

/* ---------- 在线对战 ---------- */
const families = ref([])
const inviteeId = ref(null)
const firstPick = ref('me')     // 先手：'me'=我执黑 / 'other'=对方执黑（v2.40.27）
const onlineWinner = ref('')
const lastInviteeName = ref('')

function onRemoteMove(action, userId) {
  const srv = action?.idx
  if (typeof srv !== 'number' || srv < 0 || srv >= SRV_N * SRV_N) return
  const idx = srvToInner(srv)          // 服务端坐标 → 内部坐标（在线不扩展，偏移固定）
  if (board.value[idx]) return
  // 颜色按**座位**（绝对色）：执黑方 = 1、执白方 = 2。
  // 不能用「3 - 上一手」反推 —— join 重放时 turn 初值是 HUMAN，黑方第一手会被画成白子。
  const blackId = gRoom.room.value?.black_user_id
  const color = (userId != null && blackId != null && userId === blackId) ? HUMAN : AI
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

const roomActive = computed(() =>
  mode.value === 'online' && !!gRoom.room.value && ['waiting', 'playing'].includes(gRoom.status.value))
const roomLocked = computed(() => roomActive.value)
const onlinePlaying = computed(() => mode.value === 'online' && gRoom.status.value === 'playing')
const onlineMyTurn = computed(() => onlinePlaying.value && gRoom.myTurn.value)
const boardLocked = computed(() => mode.value === 'online' && !onlineMyTurn.value)
/** 棋盘为什么点不动 —— 必须显式告诉用户，静默锁死会让人以为「坏了」 */
const lockHint = computed(() => {
  if (mode.value !== 'online') return ''
  if (!gRoom.room.value) return '先选一位家人发出邀请，再开始对局'
  const st = gRoom.status.value
  const who = gRoom.opponentName.value || '对方'
  if (st === 'waiting') return `等「${who}」接受邀请…`
  if (st === 'playing') return gRoom.myTurn.value ? '' : `等「${who}」落子…`
  if (st === 'finished') return '本局已结束'
  return ''
})
const myColor = computed(() => (gRoom.mySeat.value === 'white' ? AI : HUMAN))
const blackName = computed(() => {
  if (mode.value === 'online' && gRoom.room.value) return gRoom.mySeat.value === 'black' ? '你' : (gRoom.opponentName.value || '对方')
  return mode.value === 'pvp' ? '黑方' : '你'
})
const whiteName = computed(() => {
  if (mode.value === 'online' && gRoom.room.value) return gRoom.mySeat.value === 'white' ? '你' : (gRoom.opponentName.value || '对方')
  return mode.value === 'pvp' ? '白方' : 'AI'
})
const activeColor = computed(() => (over.value ? 0 : turn.value))
const modeLabel = computed(() => (mode.value === 'online' ? '在线' : '本地'))
const onlineResultText = computed(() =>
  onlineWinner.value === 'me' ? '🎉 你赢了' : onlineWinner.value === 'opp' ? '对方赢了' : '🤝 平局')

watch(roomActive, (v) => { emit(v ? 'room-lock' : 'room-unlock') })

async function loadFamilies() {
  try {
    const res = await familyMembers()
    families.value = (res?.data?.list || []).filter(m => m.user_id && m.user_id !== Number(gRoom.myUserId.value))
  } catch { families.value = [] }
}
async function invite() {
  if (!inviteeId.value) { ElMessage.warning('先选一位家人'); return }
  const f = families.value.find(x => x.user_id === inviteeId.value)
  lastInviteeName.value = f?.display_name || ''
  try {
    await gRoom.createInvite(inviteeId.value, firstPick.value)
    ElMessage.success(`邀请已发出（${firstPick.value === 'me' ? '你' : lastInviteeName.value || '对方'}执黑先行），等对方接受`)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '邀请失败')
  }
}
async function cancelInvite() {
  await gRoom.cancel()
  clearLocal()
  ElMessage.success('已取消')
}
async function refreshRoom() { if (gRoom.room.value?.id) await gRoom.join(gRoom.room.value.id, { autoAccept: false }) }
/** 再来一局：邀请同一人，并**交换先后手**（上一局谁执黑，这局换人） */
async function reinviteSame() {
  const uid = inviteeId.value
  firstPick.value = firstPick.value === 'me' ? 'other' : 'me'
  gRoom.reset(); clearLocal()
  if (uid) { inviteeId.value = uid }
  if (uid) {
    try {
      await gRoom.createInvite(uid, firstPick.value)
      ElMessage.success(`新对局已发出（${firstPick.value === 'me' ? '你' : '对方'}执黑先行）`)
    } catch (e) {
      ElMessage.warning(e?.response?.data?.detail || '邀请失败')
    }
  }
}
function askExit() {
  ElMessageBox.confirm('退出将按认输处理，对方获胜。确定退出？', '退出对局', {
    confirmButtonText: '认输退出', cancelButtonText: '继续下', type: 'warning',
  }).then(async () => {
    await gRoom.resign()
    over.value = true
    onlineWinner.value = 'opp'
    gRoom.reset()
    emit('room-unlock')
    ElMessage.success('已退出对局')
  }).catch(() => {})
}
function exitOnline() { gRoom.reset(); clearLocal() }

/** 进页面自动接回进行中的房间（刷新/换设备/直接打开页面都不丢） */
async function resumeMine() {
  try {
    const res = await (await import('@/api/gameRooms')).gameRoomsApi.mine()
    const active = (res?.data?.list || []).find(x =>
      x.game === 'gomoku' && ['waiting', 'playing'].includes(x.status))
    if (!active) return
    mode.value = 'online'
    await gRoom.join(active.id, { autoAccept: active.status === 'playing' })
    ElMessage.success(`已接回与「${gRoom.opponentName.value}」的对局`)
  } catch { /* 无进行中房间，忽略 */ }
}

const resultText = computed(() => {
  if (winner.value === HUMAN) return mode.value === 'pvp' ? '🎉 黑方胜' : '🎉 你赢了'
  if (winner.value === AI) return mode.value === 'pvp' ? '🎉 白方胜' : 'AI 赢了，再来'
  return '🤝 平局'
})

function clearLocal() {
  clearTimeout(timer)
  board.value = Array(FULL * FULL).fill(0)
  margin.value = BASE_MARGIN
  nextTick(measureCell)
  turn.value = HUMAN
  over.value = false
  winner.value = 0
  winLine.value = []
  lastIdx.value = -1
  history.value = []
  thinking.value = false
  onlineWinner.value = ''
}
/* ---------- 本地存档：退出/返回首页后可从「第一步」续上（在线局不存） ---------- */
const SAVE_KEY = 'gomoku'
let saveTimer = null
function saveLocal() {
  if (mode.value === 'online' || over.value || !history.value.length) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveGame(SAVE_KEY, {
      mode: mode.value,
      summary: `${modeLabel.value} · 已下 ${history.value.length} 手`,
      board: board.value,
      margin: margin.value,
      history: history.value,
      turn: turn.value,
      lastIdx: lastIdx.value,
      winLine: winLine.value,
      winner: winner.value,
      over: over.value,
    })
  }, 400)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !Array.isArray(s.board) || s.board.length !== FULL * FULL || s.mode === 'online') return false
  clearTimeout(timer)
  if (s.mode) mode.value = s.mode
  board.value = s.board
  margin.value = typeof s.margin === 'number' ? s.margin : BASE_MARGIN
  nextTick(measureCell)
  history.value = s.history || []
  turn.value = s.turn || HUMAN
  lastIdx.value = s.lastIdx ?? -1
  winLine.value = s.winLine || []
  winner.value = s.winner || 0
  over.value = !!s.over
  return true
}
watch([board, over], saveLocal, { deep: true })

function setMode(k) {
  if (roomLocked.value && k !== mode.value) {
    ElMessage.warning('对局进行中 —— 先点「退出对局」再切换模式')
    return
  }
  mode.value = k
  clearLocal()
  gRoom.reset()
  if (k === 'online') loadFamilies()
}
function restart() {
  if (mode.value === 'online') { ElMessage.info('在线模式请用「再来一局」或「退出对局」'); return }
  clearTimeout(saveTimer)
  clearGame(SAVE_KEY)
  clearLocal()
}

function checkWinFrom(bd, idx, p) {
  const x = idx % FULL, y = Math.floor(idx / FULL)
  for (const [dx, dy] of [[1, 0], [0, 1], [1, 1], [1, -1]]) {
    const line = [idx]
    for (const sign of [1, -1]) {
      let nx = x + dx * sign, ny = y + dy * sign
      while (nx >= 0 && nx < FULL && ny >= 0 && ny < FULL && bd[ny * FULL + nx] === p) {
        line.push(ny * FULL + nx)
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
  const x = idx % FULL, y = Math.floor(idx / FULL)
  let total = 0
  for (const [dx, dy] of [[1, 0], [0, 1], [1, 1], [1, -1]]) {
    let count = 1, open = 0
    for (const sign of [1, -1]) {
      let nx = x + dx * sign, ny = y + dy * sign
      while (nx >= 0 && nx < FULL && ny >= 0 && ny < FULL && bd[ny * FULL + nx] === p) {
        count++; nx += dx * sign; ny += dy * sign
      }
      if (nx >= 0 && nx < FULL && ny >= 0 && ny < FULL && bd[ny * FULL + nx] === 0) open++
    }
    total += lineScore(count, open)
  }
  return total
}
function candidates(bd) {
  const out = []
  const m = margin.value                 // 只在开放区内找点（外面还没开放）
  const lo = m, hi = FULL - m
  if (!bd.some(v => v)) return [Math.floor(FULL / 2) * FULL + Math.floor(FULL / 2)]
  for (let y = lo; y < hi; y++) for (let x = lo; x < hi; x++) {
    const idx = y * FULL + x
    if (bd[idx]) continue
    let near = false
    for (let dy = -2; dy <= 2 && !near; dy++) for (let dx = -2; dx <= 2; dx++) {
      const nx = x + dx, ny = y + dy
      if (nx >= 0 && nx < FULL && ny >= 0 && ny < FULL && bd[ny * FULL + nx]) { near = true; break }
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
  else if (openAreaFull()) { over.value = true }
}
/** 开放区是否已下满（判定平局，只看当前开放区） */
function openAreaFull() {
  const m = margin.value
  for (let y = m; y < FULL - m; y++) {
    for (let x = m; x < FULL - m; x++) if (!board.value[y * FULL + x]) return false
  }
  return true
}
/** 落子后看它离开放区边缘还有几线，≤1 就向外扩 2 圈（最多 3 次；在线模式不扩） */
function maybeExpand(innerIdx) {
  if (mode.value === 'online' || margin.value <= 0) return
  if (history.value.length < 12) return      // 开局贴边不算「吃紧」，至少下过 12 手再考虑
  const x = innerIdx % FULL, y = (innerIdx / FULL) | 0
  const m = margin.value
  const d = Math.min(x - m, FULL - 1 - m - x, y - m, FULL - 1 - m - y)
  if (d > 1) return
  margin.value -= 2
  nextTick(() => { measureCell(); ElMessage.success(`棋局吃紧，棋盘向外扩展 —— 现在 ${N.value}×${N.value}（第 ${expands.value}/3 次）`) })
}

/** 模板传进来的是 DOM 格序号；内部一律用 27×27 坐标 */
function play(domIdx) {
  const idx = domToInner(domIdx)
  if (over.value || thinking.value || board.value[idx]) return
  if (mode.value === 'online') {
    if (!onlineMyTurn.value) { ElMessage.warning('还没轮到你'); return }
    const color = myColor.value
    board.value[idx] = color
    lastIdx.value = idx
    history.value.push(idx)
    turn.value = color === HUMAN ? AI : HUMAN
    const line = checkWinFrom(board.value, idx, color)
    if (line) { winLine.value = line; over.value = true }
    gRoom.send({ idx: innerToSrv(idx) }).catch(() => {
      ElMessage.warning('落子同步失败，正在恢复局面…')
      gRoom.join(gRoom.room.value.id).then(() => {
        clearLocal()
        for (const m of gRoom.moves.value) onRemoteMove(m.action, m.user_id)
      })
    })
    return
  }
  if (mode.value !== 'pvp' && turn.value !== HUMAN) return
  place(idx)
  if (over.value) return
  maybeExpand(idx)
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
    if (pick) { turn.value = AI; place(pick.idx); turn.value = HUMAN; maybeExpand(pick.idx) }
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
  // 格宽随容器与当前边长自适应（项目惯例：nextTick 后量容器）
  resizeHandler = () => measureCell()
  window.addEventListener('resize', resizeHandler, { passive: true })
  nextTick(measureCell)
  await loadFamilies()
  // 受邀跳转进来（/tool/games?room=&game=）：直接进那个房间
  if (props.joinRoomId) {
    mode.value = 'online'
    try {
      await gRoom.join(props.joinRoomId)
      ElMessage.success(`已进入与「${gRoom.opponentName.value}」的对局`)
      return
    } catch { /* 房间不可用 → 落到常规流程 */ }
  }
  if (props.resume && restoreLocal()) return
  // 只有在线模式才自动接回进行中的房间，避免玩本地局时被拉走
  if (mode.value === 'online') await resumeMine()
})
onBeforeUnmount(() => {
  clearTimeout(timer); clearTimeout(saveTimer); gRoom.stopPoll()
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})
</script>

<style scoped>
.gk-wrap { display: flex; flex-direction: column; align-items: center; gap: 14px; width: 100%; }

/* ===== 质感壳：玻璃卡 + 柔和渐变 ===== */
.gk-shell {
  width: 100%; max-width: 560px; border-radius: 18px; padding: 16px 18px;
  background: linear-gradient(160deg, rgba(255,255,255,.75), rgba(255,255,255,.45));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  box-shadow: 0 8px 28px rgba(20,30,40,.08), inset 0 1px 0 rgba(255,255,255,.6);
  display: flex; flex-direction: column; gap: 12px;
}
.gk-players { display: flex; align-items: center; justify-content: center; gap: 18px; }
.gk-player {
  flex: 1; display: flex; align-items: center; gap: 10px; padding: 9px 13px; border-radius: 13px;
  border: 1px solid transparent; transition: all .25s; max-width: 200px;
}
.gk-player.active {
  border-color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.1);
  box-shadow: 0 0 0 3px rgba(199,169,107,.15);
}
.gk-player-txt { min-width: 0; }
.gk-player-txt b { display: block; font-size: 13.5px; color: var(--dp-text, #18202a); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gk-player-txt i { font-style: normal; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.gk-stone-sm { width: 22px; height: 22px; border-radius: 50%; flex: none; box-shadow: 0 2px 5px rgba(0,0,0,.25); }
.gk-stone-sm.black { background: radial-gradient(circle at 34% 30%, #555, #111); }
.gk-stone-sm.white { background: radial-gradient(circle at 34% 30%, #fff, #cfcabb); }
.gk-vs { font-size: 17px; color: var(--dp-text3, #8a8f98); flex: none; }

.gk-modes { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.gk-mode { padding: 6px 14px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 12.5px; font-family: inherit; transition: all .2s; }
.gk-mode.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gk-mode:disabled { opacity: .38; cursor: not-allowed; }

.gk-banner { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center;
  padding: 9px 14px; border-radius: 12px; font-size: 12.5px; }
.gk-banner.st-waiting { background: rgba(199,169,107,.12); color: var(--dp-text2, #45505b); }
.gk-banner.st-playing { background: rgba(127,168,163,.12); color: var(--dp-text2, #45505b); }
.gk-banner.st-finished { background: rgba(199,169,107,.18); color: var(--dp-text, #18202a); }
.gk-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--yq-gold, #c7a96b);
  animation: gkpulse 1.2s infinite; }
@keyframes gkpulse { 50% { opacity: .3 } }
.gk-result { font-weight: 700; color: var(--yq-gold, #c7a96b); }

.gk-status { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--dp-text2, #45505b); }
.gk-btn { padding: 5px 14px; border-radius: 9px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }
.gk-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gk-btn:disabled { opacity: .5; cursor: default; }

/* 邀请面板 */
.gk-online {
  width: 100%; max-width: 560px; border-radius: 18px; padding: 18px;
  background: linear-gradient(160deg, rgba(255,255,255,.75), rgba(255,255,255,.45));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1)); box-shadow: 0 8px 28px rgba(20,30,40,.08);
}
.gk-online-title { font-size: 15px; font-weight: 700; color: var(--dp-text, #18202a); }
.gk-online-desc { margin: 6px 0 10px; font-size: 12px; color: var(--dp-text3, #8a8f98); line-height: 1.7; }
.gk-online-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
/* 先手选择（v2.40.27） */
.gk-first-row { display: flex; align-items: center; gap: 6px; margin: 8px 0; flex-wrap: wrap; }
.gk-first-label { font-size: 12.5px; color: var(--dp-text3, #8a8f98); }
.gk-firstnote { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.gk-select { flex: 1; min-width: 160px; border: 1px solid var(--dp-line, rgba(0,0,0,.14)); border-radius: 10px;
  padding: 9px 11px; font-size: 13.5px; background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-family: inherit; }

/* 棋盘：锁定时压暗禁点 */
.gk-boardwrap { position: relative; display: inline-block; }
.gk-lockmask {
  position: absolute; inset: 0; border-radius: 14px; display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.5); pointer-events: none; padding: 12px; text-align: center;
}
.gk-lockmask span {
  font-size: 12.5px; font-weight: 600; color: var(--dp-text2, #45505b);
  background: rgba(255,255,255,.94); padding: 8px 16px; border-radius: 999px;
  box-shadow: 0 4px 14px rgba(20,30,40,.14);
}
.gk-board {
  display: grid; grid-template-columns: repeat(15, var(--cell, 26px)); grid-auto-rows: var(--cell, 26px);
  background: linear-gradient(135deg, #e8d9b8, #dcc79a); padding: 8px; border-radius: 14px;
  touch-action: manipulation; user-select: none; box-shadow: inset 0 0 0 1px rgba(0,0,0,.15), 0 10px 30px rgba(20,30,40,.12);
  transition: filter .2s;
}
.gk-board.locked { filter: saturate(.75) brightness(.94); pointer-events: none; }
.gk-cell { border: none; padding: 0; background: transparent; cursor: pointer; position: relative;
  box-shadow: inset -1px 0 0 rgba(0,0,0,.25), inset 0 -1px 0 rgba(0,0,0,.25); }
.gk-stone { position: absolute; inset: 2px; border-radius: 50%; display: block; }
.gk-stone.black { background: radial-gradient(circle at 34% 30%, #555, #111); }
.gk-stone.white { background: radial-gradient(circle at 34% 30%, #fff, #cfcabb); }
.gk-cell.last::after { content: ''; position: absolute; top: 50%; left: 50%; width: 5px; height: 5px;
  margin: -2.5px; border-radius: 50%; background: #e5484d; z-index: 2; }
.gk-cell.win::before { content: ''; position: absolute; inset: 1px; border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(229,72,77,.85); z-index: 1; }
.gk-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center; }

@media (max-width: 480px) {
  .gk-board { --cell: 21px; padding: 6px; }
  .gk-shell { padding: 12px; }
  .gk-players { gap: 8px; }
}
</style>

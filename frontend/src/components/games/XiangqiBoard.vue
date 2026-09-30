<template>
  <div class="xq-wrap" :class="{ 'is-big': big }" :style="{ '--board-w': boardW + 'px', '--tilt': (big ? TILT_DEG : 0) + 'deg' }">
    <!-- ===== 辅栏：玩家条 + 状态 + 操作 + 邀请（放大时移到棋盘右侧） ===== -->
    <div class="xq-side">
      <div class="xq-shell">
        <div class="xq-players">
          <div class="xq-player" :class="{ active: !over && turn === 'b' }">
            <span class="xq-dot black"></span>
            <div class="xq-player-txt">
              <b>{{ blackName }}</b>
              <i>{{ blackSub }}</i>
            </div>
          </div>
          <span class="xq-vs">⚔</span>
          <div class="xq-player" :class="{ active: !over && turn === 'r' }">
            <span class="xq-dot red"></span>
            <div class="xq-player-txt">
              <b>{{ redName }}</b>
              <i>{{ redSub }}</i>
            </div>
          </div>
        </div>

        <!-- 模式（页面已选则隐藏；房间激活时锁定） -->
        <div v-if="!bare" class="xq-modes" :class="{ locked: roomLocked }">
          <button
            v-for="m in MODES"
            :key="m.key"
            class="xq-mode"
            :class="{ on: mode === m.key }"
            :disabled="roomLocked && mode !== m.key"
            @click="setMode(m.key)"
          >{{ m.label }}</button>
        </div>

        <!-- 本地对局操作 -->
        <div v-if="mode !== 'online'" class="xq-status">
          <span v-if="over" class="xq-result">{{ resultText }}</span>
          <span v-else-if="checkSide" class="xq-check">将军！</span>
          <button class="xq-btn" @click="restart">重开</button>
          <button class="xq-btn" :disabled="!canUndoLocal" @click="undoLocal">悔棋</button>
          <span class="xq-quota">{{ history.length }} 手</span>
        </div>

        <!-- 在线横幅 -->
        <div v-if="mode === 'online' && gRoom.room.value" class="xq-banner" :class="'st-' + gRoom.status.value">
          <template v-if="gRoom.status.value === 'waiting'">
            <span class="xq-pulse"></span> 邀请已发给 {{ gRoom.opponentName.value }}，等待接受…
            <span class="xq-firstnote">{{ gRoom.room.value.black_name }} 执红先行</span>
            <button class="xq-btn" @click="cancelInvite">取消邀请</button>
            <button class="xq-btn" @click="refreshRoom">刷新</button>
          </template>
          <template v-else-if="gRoom.status.value === 'playing'">
            <span>{{ gRoom.myTurn.value ? '轮到你走' : '等对方走棋…' }}</span>
            <button class="xq-btn" @click="askExit">退出对局（认输）</button>
          </template>
          <template v-else-if="gRoom.status.value === 'finished'">
            <span class="xq-result">{{ onlineResultText }}</span>
            <button class="xq-btn primary" @click="reinviteSame">再来一局</button>
            <button class="xq-btn" @click="exitOnline">退出</button>
          </template>
        </div>
      </div>

      <!-- 在线邀请面板 -->
      <div v-if="mode === 'online' && !gRoom.room.value" class="xq-online">
        <div class="xq-online-title">🎯 在线邀请对战</div>
        <p class="xq-online-desc">选一位家人发出邀请，对方接受后进入对局；走子自动同步，约 2 秒内可见。</p>
        <div class="xq-online-row">
          <MemberPicker v-model="inviteeId" :members="families" placeholder="选择一位家人…" />
        </div>
        <div class="xq-online-row">
          <span class="xq-first-label">先手：</span>
          <button class="xq-mode" :class="{ on: firstPick === 'me' }" @click="firstPick = 'me'">我执红</button>
          <button class="xq-mode" :class="{ on: firstPick === 'other' }" @click="firstPick = 'other'">对方执红</button>
        </div>
        <div class="xq-online-row">
          <button class="xq-btn primary" :disabled="!inviteeId || gRoom.joining.value" @click="invite">
            {{ gRoom.joining.value ? '创建中…' : '发出邀请' }}
          </button>
        </div>
        <p v-if="!families.length" class="xq-online-desc">家庭里还没有其他账号可以邀请。</p>
      </div>

      <p v-if="lockHint" class="xq-locknote"><span class="xq-dot-sm"></span>{{ lockHint }}</p>
    </div>

    <!-- ===== 主区：棋盘 ===== -->
    <div ref="mainEl" class="xq-main">
      <div class="xq-boardwrap">
        <div class="xq-board" :style="{ width: boardW + 'px', height: boardH + 'px' }">
          <!-- eslint-disable-next-line vue/no-v-html -- 本地常量 SVG，无外部输入 -->
          <svg class="xq-svg" :viewBox="`0 0 ${boardW} ${boardH}`" aria-hidden="true" v-html="svgMarkup"></svg>
          <button
            v-for="(p, i) in board"
            :key="i"
            class="xq-cell"
            :class="{
              'has-piece': !!p,
              sel: selIdx === i,
              target: targets.includes(i),
              last: lastIdx === i,
              check: checkIdx === i,
            }"
            :style="cellStyle(i)"
            :aria-label="ariaOf(i, p)"
            @click="tap(i)"
          >
            <span v-if="p" class="xq-piece" :class="p[0] === 'r' ? 'red' : 'black'">{{ glyph(p) }}</span>
          </button>
        </div>
      </div>
    </div>

    <p class="xq-hint">
      <template v-if="mode === 'online'">在线模式 · 对方走子约 2 秒内自动出现</template>
      <template v-else>红方先行 · 帅（将）不可照面 · 无子可动即负（困毙）</template>
    </p>
  </div>
</template>

<script setup>
/** 中国象棋 · 明棋（自写，无外部依赖）。
 *
 * 规则：完整象棋走法（马蹩腿 / 象塞眼不过河 / 士象九宫 / 炮隔子吃 / 兵过河横走 /
 * 将帅不可照面 / 将军与困毙判负）。
 * 对手：双人同屏 / 单机（简单·1 层贪心，困难·3 层 Alpha-Beta）/ 在线邀请（轮询同步，客户端权威）。
 * 在线：useGameRoom('xiangqi')，服务端只记事件流；棋盘与轮次由客户端重放。
 */
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGameRoom } from '@/composables/useGameRoom'
import MemberPicker from '@/components/games/MemberPicker.vue'
import { familyMembers } from '@/api/lifeExtra'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'
import {
  COLS, ROWS, RED, BLACK, GLYPH,
  xOf, yOf, other,
  initialBoard, pieceTargets, findGeneral, applyMove, inCheck, legalMoves, aiPick,
} from '@/utils/xiangqiRules'

const emit = defineEmits(['room-lock', 'room-unlock', 'exit'])
const props = defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
  joinRoomId: { type: Number, default: 0 },
  boardSize: { type: Number, default: 0 },
  big: { type: Boolean, default: false },
  gameKey: { type: String, default: 'xiangqi' },
})

const GAME_KEY = computed(() => props.gameKey || 'xiangqi')

const MODES = [
  { key: 'pvp', label: '双人（同屏）' },
  { key: 'easy', label: '单机 · 简单' },
  { key: 'hard', label: '单机 · 困难' },
  { key: 'online', label: '在线 · 邀请对战' },
]

const PAD = 24

/* ---------- 走法生成：引擎统一见 @/utils/xiangqiRules ---------- */

/* ---------- 状态 ---------- */
const mode = ref(props.initialMode || 'easy')
const board = ref(initialBoard())
const turn = ref(RED)
const over = ref(false)
const winner = ref('')
const selIdx = ref(-1)
const lastIdx = ref(-1)
const history = ref([])        // { from, to, cap, turn }
const thinking = ref(false)
const checkSide = ref('')
let timer = null

const cellPx = ref(44)
const mainEl = ref(null)
const boardW = computed(() => (COLS - 1) * cellPx.value + PAD * 2)
const boardH = computed(() => (ROWS - 1) * cellPx.value + PAD * 2)

// 放大时棋盘绕底边后仰 TILT_DEG 度（与 <style> 里的 .xq-board 变换一致）。
// 视觉高度 = 实际高度 × cos，所以可用高度按 cos 折算，倾斜后盘面仍能填满主区。
const TILT_DEG = 26
const TILT_COS = Math.cos((TILT_DEG * Math.PI) / 180)

function measureCell() {
  const el = mainEl.value
  const availW = el?.clientWidth || 0
  const availH = el?.clientHeight || 0
  const capW = props.big ? 700 : 540
  let cell = Math.floor((Math.min(availW || capW, capW) - PAD * 2) / (COLS - 1))
  if (availH > 240) {
    const usableH = props.big ? availH / TILT_COS : availH
    cell = Math.min(cell, Math.floor((usableH - PAD * 2 - 24) / (ROWS - 1)))
  }
  cellPx.value = Math.max(26, Math.min(props.big ? 70 : 50, cell))
}
function cellStyle(i) {
  const c = cellPx.value
  const r = Math.round(c * 0.44)
  return {
    left: PAD + xOf(i) * c - r + 'px',
    top: PAD + yOf(i) * c - r + 'px',
    width: r * 2 + 'px',
    height: r * 2 + 'px',
    fontSize: Math.round(r * 0.98) + 'px',
  }
}

const svgMarkup = computed(() => {
  const c = cellPx.value
  const X = i => PAD + i * c, Y = j => PAD + j * c
  const L = []
  const ln = (x1, y1, x2, y2, w = 1) =>
    L.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke-width="${w}"/>`)
  // 横线 10 条
  for (let j = 0; j < ROWS; j++) ln(X(0), Y(j), X(8), Y(j))
  // 竖线：两边到底，中间被楚河汉界断开
  ln(X(0), Y(0), X(0), Y(9)); ln(X(8), Y(0), X(8), Y(9))
  for (let i = 1; i <= 7; i++) { ln(X(i), Y(0), X(i), Y(4)); ln(X(i), Y(5), X(i), Y(9)) }
  // 九宫斜线
  ln(X(3), Y(0), X(5), Y(2)); ln(X(5), Y(0), X(3), Y(2))
  ln(X(3), Y(7), X(5), Y(9)); ln(X(5), Y(7), X(3), Y(9))
  // 外框加粗
  L.push(`<rect x="${X(0)}" y="${Y(0)}" width="${X(8) - X(0)}" height="${Y(9) - Y(0)}" fill="none" stroke-width="2"/>`)
  const fs = Math.max(13, Math.round(c * 0.5))
  const my = (Y(4) + Y(5)) / 2 + fs / 3
  L.push(`<text x="${X(2)}" y="${my}" text-anchor="middle" font-size="${fs}" class="xq-river">楚 河</text>`)
  L.push(`<text x="${X(6)}" y="${my}" text-anchor="middle" font-size="${fs}" class="xq-river">漢 界</text>`)
  return `<g>${L.join('')}</g>`
})

const checkIdx = computed(() => {
  if (!checkSide.value) return -1
  return findGeneral(board.value, checkSide.value)
})
const targets = computed(() => {
  if (selIdx.value < 0 || over.value) return []
  return pieceTargets(board.value, selIdx.value).filter(to => !inCheck(applyMove(board.value, selIdx.value, to), turn.value))
})
function glyph(p) { return GLYPH[p[0]][p[1]] }
function ariaOf(i, p) {
  const s = `第${yOf(i) + 1}行第${xOf(i) + 1}列`
  return p ? `${s} ${p[0] === 'r' ? '红' : '黑'}${glyph(p)}` : `${s} 空`
}

/* ---------- 交互 ---------- */
const localSide = ref(RED)          // 单机模式我方颜色
const aiSide = computed(() => other(localSide.value))
const boardLocked = computed(() => {
  if (over.value) return true
  if (mode.value === 'online') return !onlineMyTurn.value
  if (mode.value === 'pvp') return false
  return turn.value === aiSide.value || thinking.value
})

function tap(i) {
  if (boardLocked.value) return
  if (mode.value === 'online' && !onlineMyTurn.value) return
  const p = board.value[i]
  if (selIdx.value >= 0) {
    if (i === selIdx.value) { selIdx.value = -1; return }
    if (targets.value.includes(i)) { doMove(selIdx.value, i); return }
  }
  if (p && p[0] === turn.value) selIdx.value = i
  else selIdx.value = -1
}

function doMove(from, to) {
  const cap = board.value[to]
  history.value.push({ from, to, cap })
  board.value = applyMove(board.value, from, to)
  selIdx.value = -1
  lastIdx.value = to
  turn.value = other(turn.value)
  checkSide.value = inCheck(board.value, turn.value) ? turn.value : ''
  if (mode.value === 'online') {
    gRoom.send({ from, to }).catch(() => { /* 下轮轮询以服务端事件流为准 */ })
    settleOnline()
  } else {
    settle()
  }
}

function settle() {
  const s = turn.value
  const moves = legalMoves(board.value, s)
  if (!moves.length) {
    // 无子可动（将死或困毙）→ 该方负
    over.value = true
    winner.value = other(s)
    checkSide.value = ''
    return
  }
  if (mode.value !== 'pvp' && mode.value !== 'online' && s === aiSide.value) maybeScheduleAI()
}

function scheduleAI() {
  thinking.value = true
  clearTimeout(timer)
  timer = setTimeout(() => {
    const depth = mode.value === 'hard' ? 3 : 1
    const m = aiPick(board.value, aiSide.value, depth)
    thinking.value = false
    if (!m) return
    const cap = board.value[m.to]
    history.value.push({ from: m.from, to: m.to, cap })
    board.value = applyMove(board.value, m.from, m.to)
    lastIdx.value = m.to
    turn.value = other(turn.value)
    checkSide.value = inCheck(board.value, turn.value) ? turn.value : ''
    settle()
  }, 260)
}

/** AI 落子的唯一入口：只在「本地单机 + 确实轮到 AI」时才走。
 *  修 V2442-006：onMounted / restart 原先无条件 scheduleAI()，
 *  红方（玩家）先行而 AI 执黑，导致「我还没操作，两个炮就压过来了」。 */
function maybeScheduleAI() {
  if (mode.value === 'pvp' || mode.value === 'online') return
  if (thinking.value || over.value) return
  if (turn.value !== aiSide.value) return
  scheduleAI()
}

/* ---------- 悔棋（仅本地） ---------- */
const canUndoLocal = computed(() => mode.value !== 'online' && !thinking.value && history.value.length > 0 && !over.value)
function undoLocal() {
  if (!canUndoLocal.value) return
  const steps = mode.value === 'pvp' ? 1 : (history.value.length >= 2 && turn.value === localSide.value ? 2 : 1)
  for (let k = 0; k < steps; k++) {
    const h = history.value.pop()
    if (!h) break
    const b = board.value.slice()
    b[h.from] = b[h.to]
    b[h.to] = h.cap || ''
    board.value = b
    turn.value = other(turn.value)
    lastIdx.value = h.from
  }
  over.value = false
  winner.value = ''
  selIdx.value = -1
  checkSide.value = inCheck(board.value, turn.value) ? turn.value : ''
}

/* ---------- 在线对战 ---------- */
const families = ref([])
const inviteeId = ref(null)
const firstPick = ref('me')
const onlineWinner = ref('')
const lastInviteeName = ref('')
let exited = false

function seatSide(userId) {
  const blackId = gRoom.room.value?.black_user_id
  // 象棋执红先行：black_user_id 字段承载「先行方」
  return (userId != null && blackId != null && userId === blackId) ? RED : BLACK
}

function applyRemote(from, to) {
  const b = board.value.slice()
  const cap = b[to]
  history.value.push({ from, to, cap })
  b[to] = b[from]
  b[from] = ''
  board.value = b
  lastIdx.value = to
  turn.value = other(turn.value)
  checkSide.value = inCheck(board.value, turn.value) ? turn.value : ''
}

function onRemoteMove(action) {
  if (action?.from == null || action?.to == null) return
  applyRemote(action.from, action.to)
  settleOnline()
}
function settleOnline() {
  const moves = legalMoves(board.value, turn.value)
  if (!moves.length) {
    over.value = true
    winner.value = other(turn.value)
    onlineWinner.value = winner.value === mySide.value ? 'me' : 'opp'
    checkSide.value = ''
    const uid = Number(gRoom.myUserId.value)
    const oppId = gRoom.room.value?.owner_id === uid ? gRoom.room.value?.invitee_id : gRoom.room.value?.owner_id
    gRoom.finish(winner.value === mySide.value ? uid : Number(oppId)).catch(() => { /* 对方可能已上报终局 */ })
  }
}
function onRoomStatus(s) {
  if (s.status === 'finished') {
    over.value = true
    const uid = Number(gRoom.myUserId.value)
    onlineWinner.value = !s.winner_id ? 'draw' : (s.winner_id === uid ? 'me' : 'opp')
    const reason = s.end_reason || gRoom.room.value?.end_reason || ''
    if (s.winner_id === uid && (reason === 'leave' || reason === 'timeout')) autoExit(reason)
  }
}
function autoExit(reason) {
  if (exited) return
  exited = true
  ElMessage.info(reason === 'timeout' ? '对方已掉线，对局自动结束' : '对方已离开，对局结束')
  gRoom.reset()
  emit('room-unlock')
  emit('exit')
}
const gRoom = useGameRoom(GAME_KEY.value, { onRemoteMove, onStatus: onRoomStatus })

const mySide = computed(() => (mode.value === 'online' ? seatSide(Number(gRoom.myUserId.value)) : localSide.value))
const roomActive = computed(() =>
  mode.value === 'online' && !!gRoom.room.value && ['waiting', 'playing'].includes(gRoom.status.value))
const roomLocked = computed(() => roomActive.value)
const onlinePlaying = computed(() => mode.value === 'online' && gRoom.status.value === 'playing')
const onlineMyTurn = computed(() => onlinePlaying.value && gRoom.myTurn.value)
const lockHint = computed(() => {
  if (mode.value !== 'online') return ''
  if (!gRoom.room.value) return '先选一位家人发出邀请，再开始对局'
  const st = gRoom.status.value
  const who = gRoom.opponentName.value || '对方'
  if (st === 'waiting') return `等「${who}」接受邀请…`
  if (st === 'playing') return gRoom.myTurn.value ? '' : `等「${who}」走棋…`
  if (st === 'finished') return '本局已结束'
  return ''
})

const blackName = computed(() => {
  if (mode.value === 'online' && gRoom.room.value) return mySide.value === BLACK ? '你（黑）' : (gRoom.opponentName.value || '对方')
  return mode.value === 'pvp' ? '黑方' : (aiSide.value === BLACK ? 'AI' : '黑方')
})
const redName = computed(() => {
  if (mode.value === 'online' && gRoom.room.value) return mySide.value === RED ? '你（红）' : (gRoom.opponentName.value || '对方')
  return mode.value === 'pvp' ? '红方' : (aiSide.value === RED ? 'AI' : '红方')
})
const blackSub = computed(() => (over.value ? '' : (turn.value === BLACK ? '行棋中' : '待走')))
const redSub = computed(() => (over.value ? '' : (turn.value === RED ? '行棋中' : '待走')))
const resultText = computed(() => {
  if (winner.value === RED) return mode.value === 'pvp' ? '🎉 红方胜' : (mySide.value === RED ? '🎉 你赢了' : 'AI 赢了，再来')
  if (winner.value === BLACK) return mode.value === 'pvp' ? '🎉 黑方胜' : (mySide.value === BLACK ? '🎉 你赢了' : 'AI 赢了，再来')
  return ''
})
const onlineResultText = computed(() =>
  onlineWinner.value === 'me' ? '🎉 你赢了' : onlineWinner.value === 'opp' ? '对方赢了' : '🤝 平局')

watch(roomActive, (v) => { emit(v ? 'room-lock' : 'room-unlock') })
watch(() => props.big, () => nextTick(measureCell))

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
    ElMessage.success(`邀请已发出（${firstPick.value === 'me' ? '你' : lastInviteeName.value || '对方'}执红先行），等对方接受`)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || e?.msg || '邀请失败')
  }
}
async function cancelInvite() { await gRoom.cancel(); clearLocal(); ElMessage.success('已取消') }
async function refreshRoom() { if (gRoom.room.value?.id) await gRoom.join(gRoom.room.value.id, { autoAccept: false }) }
async function reinviteSame() {
  const uid = inviteeId.value
  firstPick.value = firstPick.value === 'me' ? 'other' : 'me'
  gRoom.reset(); clearLocal()
  if (uid) {
    inviteeId.value = uid
    try {
      await gRoom.createInvite(uid, firstPick.value)
      ElMessage.success(`新对局已发出（${firstPick.value === 'me' ? '你' : '对方'}执红先行）`)
    } catch (e) { ElMessage.warning(e?.response?.data?.detail || e?.msg || '邀请失败') }
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

async function resumeMine() {
  try {
    const res = await (await import('@/api/gameRooms')).gameRoomsApi.mine()
    const active = (res?.data?.list || []).find(x => x.game === GAME_KEY.value && ['waiting', 'playing'].includes(x.status))
    if (!active) return
    mode.value = 'online'
    await gRoom.join(active.id, { autoAccept: active.status === 'playing' })
    ElMessage.success(`已接回与「${gRoom.opponentName.value}」的对局`)
  } catch { /* 忽略 */ }
}

/* ---------- 本地存档 ---------- */
const SAVE_KEY = GAME_KEY.value
let saveTimer = null
function saveLocal() {
  if (mode.value === 'online' || over.value || !history.value.length) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveGame(SAVE_KEY, {
      mode: mode.value,
      summary: `${mode.value === 'pvp' ? '双人同屏' : '单机'} · 已走 ${history.value.length} 手`,
      board: board.value,
      turn: turn.value,
      history: history.value,
      lastIdx: lastIdx.value,
      localSide: localSide.value,
    })
  }, 400)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !Array.isArray(s.board) || s.board.length !== COLS * ROWS || s.mode === 'online') return false
  if (s.mode) mode.value = s.mode
  board.value = s.board
  turn.value = s.turn || RED
  history.value = s.history || []
  lastIdx.value = s.lastIdx ?? -1
  localSide.value = s.localSide || RED
  over.value = false
  winner.value = ''
  checkSide.value = inCheck(board.value, turn.value) ? turn.value : ''
  return true
}
watch([board, over], saveLocal, { deep: true })

function clearLocal() {
  clearTimeout(timer)
  board.value = initialBoard()
  turn.value = RED
  over.value = false
  winner.value = ''
  selIdx.value = -1
  lastIdx.value = -1
  history.value = []
  thinking.value = false
  checkSide.value = ''
  onlineWinner.value = ''
}

function setMode(k) {
  if (roomLocked.value && k !== mode.value) { ElMessage.warning('对局进行中 —— 先点「退出对局」再切换模式'); return }
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
  maybeScheduleAI()
}

function onResize() { measureCell() }

onMounted(async () => {
  const restored = props.resume ? restoreLocal() : false
  await nextTick()
  measureCell()
  window.addEventListener('resize', onResize)
  // 家人列表必须无条件拉取：模式可能由页面「第一步」直接定为 online（或从存档恢复），
  // 只在 setMode('online') 里拉会让直接进入在线模式的邀请面板显示「没有其他账号」
  await loadFamilies()
  if (props.joinRoomId) {
    mode.value = 'online'
    try { await gRoom.join(props.joinRoomId, { autoAccept: true }) } catch { /* 忽略 */ }
    emit('room-lock')
  } else if (mode.value === 'online') {
    await resumeMine()
  } else if (!restored) {
    maybeScheduleAI()
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  clearTimeout(timer); clearTimeout(saveTimer)
  if (roomActive.value) gRoom.leaveOnUnload()
})
</script>

<style scoped>
.xq-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.xq-side { width: var(--board-w, 100%); max-width: 100%; display: flex; flex-direction: column; gap: 10px; }
.xq-main { width: 100%; display: flex; justify-content: center; }
/* 透视容器：放大后棋盘绕**底边**后仰平躺（近边贴屏、远端后收），像摆在桌面上对弈。
   perspective 收小 → 透视更强、立体感更足；origin 略上移，让近端盘面更"探"向观者。 */
.xq-boardwrap {
  display: flex; justify-content: center;
  perspective: 1180px; perspective-origin: 50% 26%;
}

/* ===== 玩家条（质感壳） ===== */
.xq-shell {
  border-radius: 18px; padding: 12px 14px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  background: var(--color-bg-glass, rgba(255,255,255,.6));
  backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  box-shadow: var(--shadow-glass, 0 8px 24px rgba(20,30,40,.08));
  display: flex; flex-direction: column; gap: 10px;
}
.xq-players { display: flex; align-items: center; justify-content: center; gap: 14px; }
.xq-player { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 12px; transition: all .2s; }
.xq-player.active { background: var(--yq-gold-faint, rgba(199,169,107,.16)); box-shadow: inset 0 0 0 1px var(--yq-gold, #c7a96b); }
.xq-dot { width: 14px; height: 14px; border-radius: 50%; flex: none; }
.xq-dot.red { background: radial-gradient(circle at 34% 30%, #f6b3a5, #c0392b 70%); }
.xq-dot.black { background: radial-gradient(circle at 34% 30%, #7b8494, #1f2630 70%); }
.xq-player-txt { display: flex; flex-direction: column; line-height: 1.25; }
.xq-player-txt b { font-size: 13px; color: var(--dp-text, #18202a); }
.xq-player-txt i { font-style: normal; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.xq-vs { color: var(--yq-gold, #c7a96b); font-size: 13px; }

.xq-modes { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.xq-mode {
  padding: 6px 12px; border-radius: 999px; font-size: 12px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: transparent;
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.xq-mode:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.xq-mode.on {
  background: var(--yq-gold-faint, rgba(199,169,107,.16));
  border-color: var(--yq-gold, #c7a96b);
  color: var(--yq-gold-deep, var(--yq-gold, #c7a96b));
  box-shadow: 0 6px 18px var(--yq-gold-glow, rgba(199,169,107,.16));
}
.xq-mode:disabled { opacity: .4; cursor: not-allowed; }

.xq-status { display: flex; align-items: center; gap: 8px; justify-content: center; flex-wrap: wrap; }
.xq-btn {
  padding: 6px 13px; border-radius: 999px; font-size: 12.5px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.xq-btn:hover:not(:disabled) { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.xq-btn:disabled { opacity: .4; cursor: not-allowed; }
.xq-btn.primary { background: var(--yq-gold, #c7a96b); color: #fff; border-color: transparent; }
.xq-quota { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.xq-result { font-size: 13px; font-weight: 600; color: var(--yq-gold-deep, var(--yq-gold, #c7a96b)); }
.xq-check { font-size: 12.5px; color: #c0392b; font-weight: 600; }

.xq-banner {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center;
  font-size: 12.5px; color: var(--dp-text2, #45505b);
}
.xq-firstnote { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.xq-pulse {
  width: 8px; height: 8px; border-radius: 50%; background: var(--yq-gold, #c7a96b);
  animation: xqPulse 1.4s ease-in-out infinite;
}
@keyframes xqPulse { 0%, 100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1.15); } }

.xq-online {
  border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 10px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  background: var(--color-bg-glass, rgba(255,255,255,.5));
}
.xq-online-title { font-size: 13.5px; font-weight: 600; color: var(--dp-text, #18202a); }
.xq-online-desc { font-size: 12px; line-height: 1.7; margin: 0; color: var(--dp-text2, #8a8f98); }
.xq-online-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.xq-first-label { font-size: 12px; color: var(--dp-text2, #8a8f98); }
.xq-locknote {
  margin: 0; font-size: 12px; color: var(--dp-text2, #8a8f98);
  display: flex; align-items: center; gap: 6px; justify-content: center;
}
.xq-dot-sm { width: 6px; height: 6px; border-radius: 50%; background: var(--yq-gold, #c7a96b); }

/* ===== 棋盘：青玉 / 墨玉盘面 + 立体盘厚（与冷调玻璃棋子同调，不再是暖褐配冷玻璃） ===== */
.xq-board {
  position: relative; border-radius: 16px;
  background:
    radial-gradient(135% 100% at 50% -12%, rgba(255,255,255,.72), rgba(255,255,255,0) 58%),
    repeating-linear-gradient(92deg, rgba(58,96,88,.05) 0 1px, rgba(0,0,0,0) 1px 6px),
    linear-gradient(158deg, #e9f1ea 0%, #d2e1d7 46%, #b6ccc0 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.7),
    inset 0 0 0 1px rgba(96,124,108,.35),
    inset 0 -10px 22px -12px rgba(20,44,38,.4),
    /* 盘厚：四层硬投影堆出「玉牌」侧壁，倾斜后像一块有厚度的桌面 */
    0 8px 0 -1px #a6bbae,
    0 15px 0 -2px #82988c,
    0 22px 0 -3px #63776d,
    0 29px 0 -6px #46574f,
    0 46px 56px -22px rgba(20, 34, 30, .6);
  /* --tilt 由组件按「是否放大」下发；绕底边旋转 → 视觉宽度不超出原盒，不会横向溢出 */
  transform-origin: 50% 100%;
  transform: rotateX(var(--tilt, 0deg));
  transition: transform .3s cubic-bezier(.4, .1, .2, 1);
  will-change: transform;
}
.xq-wrap.is-big .xq-board {
  /* 平躺后的盘面更靠近观者，落影加大加柔，营造「桌面承托」感 */
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.7),
    inset 0 0 0 1px rgba(96,124,108,.35),
    inset 0 -12px 26px -12px rgba(20,44,38,.42),
    0 10px 0 -1px #a6bbae,
    0 19px 0 -2px #82988c,
    0 28px 0 -4px #63776d,
    0 37px 0 -8px #3f4f48,
    0 66px 74px -28px rgba(18, 30, 27, .66);
}
html[data-theme="night"] .xq-board {
  background:
    radial-gradient(135% 100% at 50% -12%, rgba(127,168,163,.2), rgba(0,0,0,0) 62%),
    repeating-linear-gradient(92deg, rgba(255,255,255,.025) 0 1px, rgba(0,0,0,0) 1px 6px),
    linear-gradient(158deg, #223130 0%, #17211f 48%, #0c1211 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.12),
    inset 0 0 0 1px rgba(199,169,107,.34),
    inset 0 -12px 26px -12px rgba(0,0,0,.7),
    0 8px 0 -1px #16211f,
    0 15px 0 -2px #101917,
    0 22px 0 -3px #0a1210,
    0 29px 0 -6px #060c0b,
    0 46px 58px -22px rgba(0,0,0,.88);
}
html[data-theme="night"] .xq-wrap.is-big .xq-board {
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.12),
    inset 0 0 0 1px rgba(199,169,107,.34),
    inset 0 -14px 30px -12px rgba(0,0,0,.72),
    0 10px 0 -1px #16211f,
    0 19px 0 -2px #101917,
    0 28px 0 -4px #0a1210,
    0 37px 0 -8px #040908,
    0 66px 76px -28px rgba(0,0,0,.92);
}
.xq-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.xq-svg :deep(line), .xq-svg :deep(rect) { stroke: rgba(146, 114, 52, .62); }
html[data-theme="night"] .xq-svg :deep(line),
html[data-theme="night"] .xq-svg :deep(rect) { stroke: rgba(199, 169, 107, .6); }
.xq-svg :deep(text.xq-river) {
  fill: rgba(138, 106, 46, .7); font-weight: 600; letter-spacing: .18em;
  font-family: "Songti SC", "STSong", "SimSun", serif;
}
html[data-theme="night"] .xq-svg :deep(text.xq-river) { fill: rgba(199, 169, 107, .66); }

.xq-cell {
  position: absolute; border-radius: 50%; padding: 0; cursor: pointer;
  background: transparent; border: none; display: grid; place-items: center;
  transition: box-shadow .16s, transform .16s;
}
.xq-cell.target::after {
  content: ''; width: 26%; height: 26%; border-radius: 50%;
  background: var(--yq-gold, #c7a96b); opacity: .75;
}
.xq-cell.target.has-piece::after { display: none; }
.xq-cell.target.has-piece { box-shadow: 0 0 0 3px rgba(199, 169, 107, .85); }
.xq-cell.sel { box-shadow: 0 0 0 3px var(--yq-gold, #c7a96b), 0 0 14px rgba(199,169,107,.55); }
.xq-cell.last { box-shadow: 0 0 0 2px rgba(80, 140, 200, .75); }
.xq-cell.check { animation: xqCheck 1.1s ease-in-out infinite; }
@keyframes xqCheck {
  0%, 100% { box-shadow: 0 0 0 3px rgba(200, 60, 50, .75); }
  50% { box-shadow: 0 0 0 6px rgba(200, 60, 50, .3); }
}
.xq-piece {
  position: relative;
  width: 100%; height: 100%; border-radius: 50%; display: grid; place-items: center;
  font-family: "Songti SC", "STSong", "SimSun", serif; font-weight: 700; line-height: 1;
  user-select: none;
  /* 透明水晶质感：半透明玻璃体 + 内部高光 + 折射边 + 玉环嵌口（加浓底色，昼夜都更清晰） */
  background:
    radial-gradient(circle at 32% 26%, rgba(255,255,255,.92) 0 12%, transparent 30%),
    radial-gradient(circle at 68% 78%, rgba(255,255,255,.28) 0 12%, transparent 34%),
    radial-gradient(circle at 50% 46%, rgba(255,255,255,.18) 0 58%, transparent 72%),
    linear-gradient(150deg, rgba(176,208,224,.6), rgba(236,228,210,.42) 46%, rgba(150,178,204,.56));
  box-shadow:
    inset 0 0 0 1.6px rgba(255,255,255,.62),
    inset 2px 3px 7px rgba(255,255,255,.58),
    inset -3px -4px 10px rgba(96,122,156,.44),
    0 4px 10px rgba(30, 48, 74, .34);
}
.xq-piece::before {
  content: ''; position: absolute; inset: 0; border-radius: 50%;
  /* 玉环嵌口：外环玻璃描边 + 内侧一圈暗口，让文字像嵌在水晶里 */
  box-shadow:
    inset 0 0 0 2px rgba(255,255,255,.45),
    inset 0 0 0 3.6px rgba(64,96,138,.3),
    inset 0 0 10px rgba(255,255,255,.18);
}
.xq-piece::after {
  content: ''; position: absolute; inset: 22%; border-radius: 50%;
  /* 内部冰透：内环高光折射，托起中央汉字 */
  box-shadow: inset 0 0 8px rgba(255,255,255,.34), inset 0 0 0 1px rgba(255,255,255,.2);
}
.xq-piece.red {
  color: #9e1a14;
  text-shadow: 0 1px 2px rgba(120, 20, 12, .38), 0 0 7px rgba(255, 170, 158, .5);
}
.xq-piece.black {
  color: #0a0f16;
  text-shadow: 0 1px 2px rgba(6, 10, 16, .42), 0 0 7px rgba(210, 224, 250, .45);
}
html[data-theme="night"] .xq-piece {
  background:
    radial-gradient(circle at 32% 26%, rgba(255,255,255,.42) 0 12%, transparent 30%),
    radial-gradient(circle at 68% 78%, rgba(255,255,255,.14) 0 12%, transparent 34%),
    radial-gradient(circle at 50% 46%, rgba(255,255,255,.09) 0 58%, transparent 72%),
    linear-gradient(150deg, rgba(140,178,208,.4), rgba(255,255,255,.12) 46%, rgba(108,146,186,.38));
  box-shadow:
    inset 0 0 0 1.6px rgba(255,255,255,.34),
    inset 2px 3px 7px rgba(255,255,255,.2),
    inset -3px -4px 10px rgba(74, 106, 148, .46),
    0 4px 10px rgba(0,0,0,.6);
}
html[data-theme="night"] .xq-piece::before {
  box-shadow:
    inset 0 0 0 2px rgba(255,255,255,.24),
    inset 0 0 0 3.6px rgba(130, 172, 216, .3),
    inset 0 0 10px rgba(255,255,255,.1);
}
html[data-theme="night"] .xq-piece.red { color: #ffb0a6; text-shadow: 0 1px 3px rgba(90, 14, 8, .62), 0 0 9px rgba(255,130,118,.42); }
html[data-theme="night"] .xq-piece.black { color: #f2f6fc; text-shadow: 0 1px 3px rgba(0,0,0,.7), 0 0 9px rgba(200,220,255,.4); }

.xq-hint {
  margin: 0; font-size: 12px; line-height: 1.7; text-align: center;
  color: var(--dp-text3, #8a8f98);
}

/* ===== 放大：左主棋盘 + 右辅栏（定高两栏，头部与棋局分层） ===== */
.xq-wrap.is-big {
  display: grid; grid-template-columns: minmax(0, 1fr) 330px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px 22px; width: 100%; height: 100%; min-height: 0;
}
.xq-wrap.is-big .xq-side {
  grid-column: 2; grid-row: 1 / span 2; width: 100%; max-height: 100%;
  overflow-y: auto; align-self: start;
}
.xq-wrap.is-big .xq-main {
  grid-column: 1; grid-row: 1; width: 100%; height: 100%; min-height: 0; align-items: center;
}
.xq-wrap.is-big .xq-hint { grid-column: 1; grid-row: 2; }
@media (max-width: 900px) {
  .xq-wrap.is-big { display: flex; flex-direction: column; }
  .xq-wrap.is-big .xq-side, .xq-wrap.is-big .xq-main { grid-column: auto; grid-row: auto; max-height: none; }
}
</style>
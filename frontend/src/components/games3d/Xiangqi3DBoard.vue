<template>
  <div class="g3d-board">
    <!-- 顶栏承担全部操作（棋盘倾斜后上下都没有安全区放浮动条） -->
    <header v-if="showTopbar" class="g3d-topbar">
      <div class="g3d-title">
        <span class="g3d-logo">3D</span>
        <div class="g3d-tx">
          <b>3D 象棋</b>
          <i v-if="online">{{ onlineHint }}</i>
          <i v-else>电脑 {{ alive.black }} 子 · {{ statusText }}</i>
        </div>
      </div>
      <div class="g3d-ops">
        <template v-if="!online">
          <button class="g3d-op ghost" title="点击切换难度" @click="cycleDiff">{{ diffLabel }}</button>
          <button class="g3d-op ghost" :disabled="!canUndo" @click="undo">悔棋</button>
          <button class="g3d-op" @click="restart">重开</button>
        </template>
        <template v-else>
          <button v-if="!room" class="g3d-op primary" @click="panelOpen = true">邀人对局</button>
          <button v-else-if="canUndoOnline" class="g3d-op ghost" @click="undoOnline">悔棋（余 {{ gRoom.undoLeft.value }}）</button>
          <button v-if="room" class="g3d-op ghost" @click="leaveRoom">退出对局</button>
        </template>
        <button class="g3d-op ghost" @click="$emit('exit')">返回</button>
      </div>
    </header>

    <div class="g3d-stage">
      <div class="g3d-world" :style="{ transform: world.tf, top: world.top }">
        <!-- 棋盘：木底 + 厚 20；线（含九宫斜线、河界断线）用 SVG 精确画在顶面 -->
        <div class="xq3-slab" :class="{ 'is-shake': shake }" :style="boxVars(BOARD_W, BOARD_H, 26)">
          <div class="xq3-face xq3-top">
            <svg class="xq3-grid" :viewBox="`0 0 ${BOARD_W} ${BOARD_H}`" aria-hidden="true">
              <!-- 横线 10 条 -->
              <line v-for="r in ROWS" :key="'r' + r"
                :x1="PAD" :y1="PAD + (r - 1) * CELL_Y"
                :x2="BOARD_W - PAD" :y2="PAD + (r - 1) * CELL_Y" />
              <!-- 竖线 9 条：边线贯通，中间 7 条在河界处断开 -->
              <template v-for="c in COLS" :key="'c' + c">
                <line v-if="c === 1 || c === COLS"
                  :x1="PAD + (c - 1) * CELL_X" :y1="PAD"
                  :x2="PAD + (c - 1) * CELL_X" :y2="BOARD_H - PAD" />
                <template v-else>
                  <line :x1="PAD + (c - 1) * CELL_X" :y1="PAD"
                    :x2="PAD + (c - 1) * CELL_X" :y2="PAD + 4 * CELL_Y" />
                  <line :x1="PAD + (c - 1) * CELL_X" :y1="PAD + 5 * CELL_Y"
                    :x2="PAD + (c - 1) * CELL_X" :y2="BOARD_H - PAD" />
                </template>
              </template>
              <!-- 九宫斜线 -->
              <line :x1="PAD + 3 * CELL_X" :y1="PAD" :x2="PAD + 5 * CELL_X" :y2="PAD + 2 * CELL_Y" />
              <line :x1="PAD + 5 * CELL_X" :y1="PAD" :x2="PAD + 3 * CELL_X" :y2="PAD + 2 * CELL_Y" />
              <line :x1="PAD + 3 * CELL_X" :y1="PAD + 7 * CELL_Y" :x2="PAD + 5 * CELL_X" :y2="PAD + 9 * CELL_Y" />
              <line :x1="PAD + 5 * CELL_X" :y1="PAD + 7 * CELL_Y" :x2="PAD + 3 * CELL_X" :y2="PAD + 9 * CELL_Y" />
              <!-- 河界 -->
              <text class="xq3-river" :x="PAD + 2 * CELL_X" :y="PAD + 4.62 * CELL_Y">楚 河</text>
              <text class="xq3-river" :x="PAD + 6.1 * CELL_X" :y="PAD + 4.62 * CELL_Y">漢 界</text>
            </svg>
          </div>
          <div class="xq3-face xq3-front"></div>
          <div class="xq3-face xq3-left"></div>
          <div class="xq3-face xq3-right"></div>
        </div>

        <!-- 可落点（空位）：透明命中层 + 视觉点。敌方位置由棋子自己接点击 -->
        <div
          v-for="i in emptyTargets"
          :key="'tg' + i"
          class="xq3-hit"
          :style="dotStyle(i)"
          @click="tap(i)"
        ><i class="xq3-dot"></i></div>

        <!-- 棋子：圆柱（顶面 + 底面），选中抬高 -->
        <div
          v-for="p in pieces"
          :key="'p' + p.i"
          class="xq3-piece"
          :class="[p.side === RED ? 'red' : 'black', { 'is-sel': p.i === sel, 'is-last': p.i === lastIdx }]"
          :style="pieceStyle(p.i)"
          @click="tap(p.i)"
        >
          <i class="xq3-pc-side"></i>
          <i class="xq3-pc-top"><b>{{ glyph(p) }}</b></i>
        </div>

        <!-- 🔴 不放 3D 座位铭牌：SEAT_SLOT 按 660 牌桌标定，棋盘只有 554×516，
             铭牌会飘到棋盘上方（竖屏探针实测）。两人局的信息顶栏一行够用。 -->
      </div>
    </div>

    <!-- 我：左下 HUD -->
    <div class="gt3-seat gt3-self" :class="{ 'is-turn': !over && turn === RED }">
      <div class="gt3-ava me"><AppIcon icon="🙂" /></div>
      <div class="gt3-meta">
        <b>你</b>
        <i :class="{ turn: !over && turn === RED }">{{ over ? '已结束' : '红方' }}</i>
      </div>
      <div class="gt3-score is-you">
        <span class="snum">{{ alive.red }}</span><span class="slbl">子</span>
      </div>
    </div>

    <!-- 在线邀请面板（未建房时） -->
    <div v-if="online && panelOpen && !room" class="g3d-invite">
      <div class="g3d-invite-card">
        <h3>在线邀请对战</h3>
        <p>选一位家人发出邀请，对方接受后进入对局。走子自动同步，约 2 秒可见。</p>
        <MemberPicker v-model="inviteeId" :members="families" placeholder="选择一位家人…" />
        <div class="g3d-invite-row">
          <span>先手</span>
          <button class="g3d-op ghost" :class="{ on: firstPick === 'me' }" @click="firstPick = 'me'">我执红</button>
          <button class="g3d-op ghost" :class="{ on: firstPick === 'other' }" @click="firstPick = 'other'">对方执红</button>
        </div>
        <div class="g3d-invite-acts">
          <button class="g3d-btn ghost" @click="panelOpen = false">取消</button>
          <button class="g3d-btn primary" :disabled="!inviteeId || joining" @click="invite">
            {{ joining ? '创建中…' : '发出邀请' }}
          </button>
        </div>
        <p v-if="!families.length" class="g3d-invite-tip">家庭里还没有其他账号可以邀请。</p>
      </div>
    </div>

    <div v-if="toast" class="g3d-toast">{{ toast }}</div>

    <div v-if="showResult" class="g3d-over is-chess">
      <div class="ov-card">
        <h2>{{ winner === RED ? '你赢了' : '电脑赢了' }}</h2>
        <p>{{ winner === RED ? '将死' : '被将死' }} · 共 {{ history.length }} 手</p>
        <div class="ov-acts">
          <button class="g3d-btn ghost" @click="restart">再来一局</button>
          <button class="g3d-btn primary" @click="$emit('exit')">返回大厅</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 3D 象棋（v2.46.277）
 *
 * 规则与 AI 全部复用 utils/xiangqiRules.js（和 2D 版同一份，纯函数、无 Vue 依赖），
 * 这里只负责「把棋盘画成透视的」：
 *   · 棋盘是有厚度的板，线用 SVG 精确画在顶面（九宫斜线、河界断线都不用 CSS 拼）
 *   · 棋子是圆柱：顶面平躺（rotateX(-90deg)）、底面下沉 7px 做厚度
 *   · 视角 50°：再陡远端字就压扁，再平就没有纵深
 *
 * 走子/判负照抄 2D：pieceTargets 出可走点、legalMoves 为空即被将死。
 * 不引「走后自己被将」的额外过滤，否则 3D 能走的棋 2D 走不了，两边规则就分了家。
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { boxVars, boardWorld } from './use3dTable'
import { sfx } from '@/utils/games/sfx'
import { runAI, invalidateAI } from '@/composables/useAiWorker'
import { useGameRoom } from '@/composables/useGameRoom'
import { familyMembers } from '@/api/lifeExtra'
import { gameRoomsApi } from '@/api/gameRooms'
import MemberPicker from '@/components/games/MemberPicker.vue'
import { ElMessage } from 'element-plus'
import {
  COLS, ROWS, RED, BLACK, GLYPH,
  xOf, yOf, initialBoard, pieceTargets, applyMove, inCheck, legalMoves, other,
} from '@/utils/xiangqiRules'
import AppIcon from '@/components/common/AppIcon.vue'
import '@/assets/styles/games3d.css'

const props = defineProps({
  showTopbar: { type: Boolean, default: true },
  online: { type: Boolean, default: false },
  joinRoomId: { type: Number, default: 0 },
})
defineEmits(['exit'])
const online = computed(() => props.online)

/* ---------- 几何 ---------- */
const CELL_X = 56
const CELL_Y = 54
const PAD = 34
const BOARD_W = (COLS - 1) * CELL_X + PAD * 2   // 516
const BOARD_H = (ROWS - 1) * CELL_Y + PAD * 2   // 554
const PIECE_Z = 20        // 棋子抬到板面上方（板厚 26 → 顶面 z = 13）
const SEL_LIFT = 15       // 选中再抬 15px

/* 投影高 ≈ 554 × cos50° ≈ 356px。横屏 .78 → 278，底边落在 338（HUD 从 348 起）。
   原来用牌桌原点 52% + .84 时底边到 368，左下角整块被 HUD 压住（探针实测）。 */
const world = ref(boardWorld(50, BOARD_W, 0.78))
function onResize() { world.value = boardWorld(50, BOARD_W, 0.78) }

const cx = i => xOf(i) * CELL_X - BOARD_W / 2 + PAD
const cy = i => yOf(i) * CELL_Y - BOARD_H / 2 + PAD

/* z 必须 > 板厚/2 = 13：低于顶面的落点会被木板整个遮住（探针第一版就是这么隐身的） */
const dotStyle = i => ({ transform: `translate(-50%,-50%) translate3d(${cx(i)}px,${cy(i)}px,15px)` })
function pieceStyle(i) {
  const x = cx(i)
  const y = cy(i)
  const z = PIECE_Z + (i === sel.value ? SEL_LIFT : 0)
  return {
    '--bx': `${x}px`,
    '--by': `${y}px`,
    '--bz': `${z}px`,
    transform: `translate(-50%,-50%) translate3d(${x}px,${y}px,${z}px) rotateX(-90deg)`,
  }
}

/* ---------- 状态 ---------- */
const board = ref(initialBoard())
const turn = ref(RED)          // 红先，玩家执红（在下）
const sel = ref(-1)
const lastIdx = ref(-1)
const over = ref(false)       // 锁盘
const showResult = ref(false) // 结算浮层（晚 0.9s）
const winner = ref('')
const thinking = ref(false)
const toast = ref('')
const shake = ref(false)
const diff = ref('normal')
const history = ref([])        // [{ from, to, cap }]

let aiTimer = null
let toastTimer = null
let shakeTimer = null
let resultTimer = null

const DIFFS = [
  { key: 'easy', label: '简单', depth: 2 },
  { key: 'normal', label: '普通', depth: 3 },
  { key: 'hard', label: '困难', depth: 5 },
]
const depth = () => DIFFS.find(d => d.key === diff.value)?.depth ?? 3
const diffLabel = computed(() => DIFFS.find(d => d.key === diff.value)?.label || '普通')

const pieces = computed(() => {
  const out = []
  for (let i = 0; i < board.value.length; i++) {
    const p = board.value[i]
    if (p) out.push({ i, side: p[0], t: p[1] })
  }
  return out
})
const alive = computed(() => {
  let red = 0
  let black = 0
  for (const p of pieces.value) (p.side === RED ? red++ : black++)
  return { red, black }
})

const targets = computed(() => (sel.value >= 0 ? pieceTargets(board.value, sel.value) : []))
/* 空位才需要额外命中层：敌方棋子所在的「可吃目标」由棋子自己接点击 */
const emptyTargets = computed(() => targets.value.filter(i => !board.value[i]))

const canUndo = computed(() => !thinking.value && !over.value && history.value.length > 0)

const statusText = computed(() => {
  if (over.value) return winner.value === RED ? '将死 · 你赢' : '被将死'
  if (thinking.value) return '电脑思考中…'
  if (inCheck(board.value, turn.value)) return turn.value === RED ? '将军！快应' : '你将军了'
  return turn.value === RED ? '轮到你走' : '轮到电脑'
})

function glyph(p) { return GLYPH[p.side]?.[p.t] || '' }

function say(t) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1400)
}

/* ================= 在线对局（v2.46.278） =================
 * 服务端 game_rooms 只存 {from,to} 事件、不重放校验（象棋规则比五子棋复杂得多），
 * 胜负由客户端上报 —— 家人之间的荣誉制，与 2D 版同一口径。
 * 座位约定：服务端 black_user_id = 黑方（棋盘上方），另一人红方（下方）。
 */
const families = ref([])
const inviteeId = ref(null)
const firstPick = ref('me')
const panelOpen = ref(false)
const joining = ref(false)
let replaying = false

const room = computed(() => gRoom.room.value)
/* 🔴 单机必须固定执红：gRoom.mySeat 在没有房间时默认返回 'black'，
   照搬过来会让单机变成「我执黑」→ 红方棋子一个都点不动（探针实测）。 */
const mySide = computed(() => ((online.value && gRoom.mySeat.value === 'black') ? BLACK : RED))
const onlineMyTurn = computed(() => gRoom.status.value === 'playing' && gRoom.myTurn.value)
const canUndoOnline = computed(() => gRoom.status.value === 'playing' && !over.value && gRoom.undoPlies.value > 0)

const onlineHint = computed(() => {
  if (!room.value) return '还没开局 · 点右上「邀人对局」'
  const st = gRoom.status.value
  const who = gRoom.opponentName.value || '对方'
  if (st === 'waiting') return `等「${who}」接受邀请…`
  if (st === 'playing') {
    return gRoom.myTurn.value
      ? `轮到你（${mySide.value === RED ? '红' : '黑'}）`
      : `等「${who}」走子…`
  }
  return '对局已结束'
})

function sideOf(userId) {
  const blackId = room.value?.black_user_id
  if (blackId == null || userId == null) return RED
  return Number(userId) === Number(blackId) ? BLACK : RED
}

/** 撤销一手：to 上的子挪回 from，被吃的子放回 to */
function undoOne(b, h) {
  const nb = b.slice()
  nb[h.from] = nb[h.to]
  nb[h.to] = h.cap || ''
  return nb
}

function onRemoteMove(action, userId) {
  if (!action) return
  if (action.undo) {
    const plies = action.undo === 2 ? 2 : 1
    for (let k = 0; k < plies; k++) {
      const h = history.value.pop()
      if (h) board.value = undoOne(board.value, h)
    }
    over.value = false
    showResult.value = false
    winner.value = ''
    sel.value = -1
    lastIdx.value = history.value.length ? history.value[history.value.length - 1].to : -1
    turn.value = sideOf(userId)
    return
  }
  const { from, to } = action
  if (typeof from !== 'number' || typeof to !== 'number') return
  if (!board.value[from]) return
  const cap = board.value[to]
  history.value.push({ from, to, cap })
  board.value = applyMove(board.value, from, to)
  lastIdx.value = to
  turn.value = board.value[to][0] === RED ? BLACK : RED
  if (inCheck(board.value, turn.value)) sfx.check()
}

function onRoomStatus(st) {
  if (st?.status !== 'finished') return
  over.value = true
  thinking.value = false
  void st
  showResult.value = true
}

const gRoom = useGameRoom('xiangqi', { onRemoteMove, onStatus: onRoomStatus })

async function loadFamilies() {
  try {
    const res = await familyMembers()
    families.value = (res?.data?.list || []).filter(m => m.user_id && Number(m.user_id) !== Number(gRoom.myUserId.value))
  } catch { families.value = [] }
}

async function invite() {
  if (!inviteeId.value) { ElMessage.warning('先选一位家人'); return }
  joining.value = true
  try {
    await gRoom.createInvite(inviteeId.value, firstPick.value)
    panelOpen.value = false
    ElMessage.success('邀请已发出，等对方接受')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || e?.msg || '邀请失败')
  } finally {
    joining.value = false
  }
}

function leaveRoom() {
  gRoom.resign().catch(() => {})
  gRoom.reset()
  restart()
}

async function undoOnline() {
  try { await gRoom.undo() } catch { /* 服务端会拒绝，下一轮轮询自然对齐 */ }
}

/* ---------- 交互 ---------- */
function tap(i) {
  if (over.value || thinking.value) return
  if (online.value && !onlineMyTurn.value) { say('还没轮到你'); return }
  if (turn.value !== mySide.value) return
  if (sel.value >= 0) {
    if (i === sel.value) { sel.value = -1; return }
    if (targets.value.includes(i)) { doMove(sel.value, i); return }
  }
  const p = board.value[i]
  sel.value = p && p[0] === turn.value ? i : -1
  if (sel.value >= 0) sfx.pick()
}

function doMove(from, to) {
  const cap = board.value[to]
  history.value.push({ from, to, cap })
  board.value = applyMove(board.value, from, to)
  sel.value = -1
  lastIdx.value = to
  if (!replaying) cap ? sfx.capture() : sfx.wood()
  turn.value = other(turn.value)
  if (inCheck(board.value, turn.value)) sfx.check()
  if (online.value) {
    /* 在线：上报这一手，然后只判「对方还有没有合法着法」，不跑本地 AI */
    if (!replaying && board.value[to][0] === mySide.value) gRoom.send({ from, to }).catch(() => {})
    settleOnline()
    return
  }
  settle()
}

/** 在线判负：对方无合法着法 = 将死，由我方上报胜负 */
function settleOnline() {
  const opponent = turn.value
  if (legalMoves(board.value, opponent).length) return
  over.value = true
  winner.value = other(opponent)
  sfx.mate()
  shake.value = true
  clearTimeout(shakeTimer)
  shakeTimer = setTimeout(() => { shake.value = false }, 700)
  clearTimeout(resultTimer)
  resultTimer = setTimeout(() => { showResult.value = true }, 900)
  const uid = Number(gRoom.myUserId.value)
  if (uid && winner.value === mySide.value) gRoom.finish(uid).catch(() => {})
}

function settle() {
  const s = turn.value
  if (!legalMoves(board.value, s).length) {
    over.value = true
    winner.value = other(s)
    thinking.value = false
    sfx.mate()
    shake.value = true
    clearTimeout(shakeTimer)
    shakeTimer = setTimeout(() => { shake.value = false }, 700)
    clearTimeout(resultTimer)
    resultTimer = setTimeout(() => { showResult.value = true }, 900)
    return
  }
  if (s === BLACK) scheduleAI()
}

function scheduleAI() {
  clearTimeout(aiTimer)
  thinking.value = true
  /* 让这一手先画出来再搜索：aiPick 是同步的，困难档 5 层约 1.2 秒 */
  aiTimer = setTimeout(async () => {
    /* v2.46.278：5 层迭代加深搬进 Worker。原来主线程跑约 1.2 秒，
       这段时间整个页面是僵的（连悔棋按钮都点不动）。 */
    const m = await runAI('xiangqi', { board: [...board.value], side: BLACK, depth: depth() })
    thinking.value = false
    if (m === null) return          // 被作废（重开/悔棋）
    if (!m) { settle(); return }
    const cap = board.value[m.to]
    history.value.push({ from: m.from, to: m.to, cap })
    board.value = applyMove(board.value, m.from, m.to)
    lastIdx.value = m.to
    cap ? sfx.capture() : sfx.wood()
    turn.value = RED
    settle()
  }, 140)
}

/* ---------- 操作 ---------- */
function cycleDiff() {
  const k = DIFFS.findIndex(d => d.key === diff.value)
  diff.value = DIFFS[(k + 1) % DIFFS.length].key
  say(`难度：${diffLabel.value}`)
}

function undo() {
  if (!canUndo.value) return
  clearTimeout(aiTimer)
  invalidateAI()
  thinking.value = false
  /* 撤到「轮到红方」。canUndo 已排除「AI 思考中」，所以此刻一定刚走完黑棋 →
     连续撤两手（黑 + 红）。只剩一手时退化成撤一手。 */
  const n = Math.min(2, history.value.length)
  for (let k = 0; k < n; k++) {
    const h = history.value.pop()
    if (!h) break
    board.value = applyMoveRev(board.value, h)
  }
  over.value = false
  showResult.value = false
  winner.value = ''
  sel.value = -1
  turn.value = RED
  lastIdx.value = history.value.length ? history.value[history.value.length - 1].to : -1
  sfx.pick()
}

/** 撤销一手：把 to 上的子挪回 from，并把被吃的子放回 to */
function applyMoveRev(b, h) {
  const nb = b.slice()
  nb[h.from] = nb[h.to]
  nb[h.to] = h.cap || ''
  return nb
}

function restart() {
  clearTimeout(aiTimer)
  clearTimeout(resultTimer)
  invalidateAI()
  thinking.value = false
  board.value = initialBoard()
  history.value = []
  turn.value = RED
  sel.value = -1
  lastIdx.value = -1
  over.value = false
  showResult.value = false
  winner.value = ''
  toast.value = ''
}

onMounted(async () => {
  sfx.preload()
  window.addEventListener('resize', onResize)
  window.addEventListener('orientationchange', onResize)
  if (!online.value) return
  await loadFamilies()
  if (props.joinRoomId) {
    replaying = true
    try { await gRoom.join(props.joinRoomId, { autoAccept: true }) } catch { /* 房间可能已结束 */ }
    replaying = false
    return
  }
  try {
    const res = await gameRoomsApi.mine()
    const active = (res?.data?.list || []).find(x => x.game === 'xiangqi' && ['waiting', 'playing'].includes(x.status))
    if (active) {
      replaying = true
      await gRoom.join(active.id, { autoAccept: active.status === 'playing' })
      replaying = false
      ElMessage.success(`已接回与「${gRoom.opponentName.value}」的对局`)
      return
    }
  } catch { /* 无进行中对局 */ }
  panelOpen.value = true
})
onBeforeUnmount(() => {
  invalidateAI()
  window.removeEventListener('resize', onResize)
  window.removeEventListener('orientationchange', onResize)
  clearTimeout(aiTimer)
  clearTimeout(toastTimer)
  clearTimeout(shakeTimer)
  clearTimeout(resultTimer)
})

defineExpose({ board, history, doMove, restart, setDiff: (k) => { diff.value = k }, getDiff: () => diff.value })
</script>

<template>
  <div class="gk-wrap" :class="{ 'is-big': big }" :style="{ '--board-w': boardW + 'px', '--tilt': (big ? TILT_DEG : 0) + 'deg' }">
    <!-- ===== 辅栏：玩家条 + 模式 + 操作 + 邀请（普通模式随主列纵向排；放大模式移到棋盘右侧） ===== -->
    <div class="gk-side">
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

      <!-- 本地对局操作：重开 / 悔棋（含配额） -->
      <div v-if="mode !== 'online'" class="gk-status">
        <span v-if="over" class="gk-result">{{ resultText }}</span>
        <button class="gk-btn" @click="restart">重开</button>
        <button class="gk-btn" :disabled="!canUndoLocal" @click="undoLocal">悔棋</button>
        <span class="gk-quota">{{ localQuotaText }}</span>
      </div>

      <!-- 房间状态横幅（waiting / playing / finished） -->
      <div v-if="mode === 'online' && gRoom.room.value" class="gk-banner" :class="'st-' + gRoom.status.value">
        <template v-if="gRoom.status.value === 'waiting'">
          <span class="gk-pulse"></span> 邀请已发给 {{ gRoom.opponentName.value }}，等待接受…
          <span class="gk-firstnote">{{ gRoom.room.value.black_name }} 执黑先行</span>
          <button class="gk-btn" @click="cancelInvite">取消邀请</button>
          <button class="gk-btn" @click="refreshRoom">刷新</button>
        </template>
        <template v-else-if="gRoom.status.value === 'playing'">
          <span>{{ gRoom.myTurn.value ? '轮到你落子' : '等对方落子…' }}</span>
          <button class="gk-btn" :disabled="!canUndoOnline" @click="undoOnline">
            悔棋{{ gRoom.undoPlies.value === 2 ? '（连对方应招共撤 2 手）' : '' }}（你 {{ gRoom.undoLeft.value }} · 对方 {{ gRoom.undoOppLeft.value }}）
          </button>
          <button class="gk-btn" @click="askExit">退出对局（认输）</button>
        </template>
        <template v-else-if="gRoom.status.value === 'finished'">
          <span class="gk-result">{{ onlineResultText }}</span>
          <button v-if="canUndoOnline" class="gk-btn" @click="undoOnline">悔棋翻盘{{ gRoom.undoPlies.value === 2 ? ' · 撤 2 手' : '' }}（余 {{ gRoom.undoLeft.value }}）</button>
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
        <MemberPicker v-model="inviteeId" :members="families" placeholder="选择一位家人…" />
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

    <!-- 锁定原因：放在棋盘**外面**，不遮挡棋局（此前是覆盖在棋盘上的遮罩气泡） -->
    <p v-if="lockHint" class="gk-locknote"><span class="gk-dot"></span>{{ lockHint }}</p>
    </div><!-- /.gk-side -->

    <!-- ===== 主区：棋盘（放大模式下独占左侧主位） ===== -->
    <div ref="mainEl" class="gk-main">
    <div class="gk-boardwrap">
      <div
        class="gk-board"
        :class="{ locked: boardLocked, 'has-winner': winLine.length }"
        :style="{ '--cell': cellPx + 'px', '--n': N, gridTemplateColumns: `repeat(${N}, ${cellPx}px)`, gridAutoRows: cellPx + 'px' }"
      >
        <!-- 网格线画在**格子中心** → 棋子圆心正好落在交叉点上 -->
        <div class="gk-grid" aria-hidden="true"></div>
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
    </div>
    </div><!-- /.gk-main -->
    <p class="gk-hint">
      <template v-if="mode === 'online'">在线模式 · 对方落子约 2 秒内自动出现 · 每方每局 3 次悔棋</template>
      <template v-else>
        黑方先行 · 五子连珠获胜 · 困难模式 AI 搜索更深
        <span class="gk-expandnote">· 棋盘 {{ N }}×{{ N }} · 每方每局 3 次悔棋</span>
      </template>
    </p>
  </div>
</template>

<script setup>
/** 五子棋（自写，无外部依赖）。
 * 本地：双人 / 简单(贪心) / 困难(3 层极小化极大 + Alpha-Beta + 棋型打分表，公开算法自研实现)。
 * 在线：useGameRoom 房间会话（轮询同步）。
 *
 * v2.40.34 修复（夜星反馈）：
 *  1. **棋子落在交叉点上**：格子按钮不再画边框，另加 .gk-grid 覆盖层把线画在格心；
 *     棋盘内边距 = 半个格宽，边线上的棋子不被裁。
 *  2. **提示语不盖棋盘**：删掉 .gk-lockmask 遮罩，锁定原因移到棋盘上方独立一行。
 *  3. **悔棋配额**：本地每方每局 3 次（按钮显示余量）；在线走服务端 /undo（同为 3 次）。
 *  4. **夜间主题提亮**：深木纹棋盘 + 深色玻璃壳，文字对比度拉到 AA。
 *  5. **对手退出自动结束**：服务端 end_reason=leave/timeout 且我方获胜 → 提示并自动退出。
 *
 * v2.40.35 排版（夜星反馈）：
 *  1. 玩家条/邀请面板宽度改由 `--board-w` 驱动，与棋盘**严格同宽**，修掉「壳 560、盘 432」的边缘错位。
 *  2. 放大模式改「左主棋盘 + 右辅栏」两栏（棋盘独占左侧主位，玩家条/模式/操作移右侧），主次分明。
 *  3. 放大模式棋盘同时受可用宽高约束，一屏放下不溢出；窄屏（≤900px）自动退回单列。
 */
import { ref, computed, nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGameRoom } from '@/composables/useGameRoom'
import MemberPicker from '@/components/games/MemberPicker.vue'
import { familyMembers } from '@/api/lifeExtra'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'

const emit = defineEmits(['room-lock', 'room-unlock', 'exit'])
const props = defineProps({
  initialMode: { type: String, default: '' },   // 模式由页面「第一步」选定（v2.40.29）
  resume: { type: Boolean, default: false },    // 从本地存档续局
  bare: { type: Boolean, default: false },      // 隐藏内置模式段（模式已在页面上选过）
  joinRoomId: { type: Number, default: 0 },     // 受邀跳转进来：直接进指定房间
  boardSize: { type: Number, default: 15 },     // 开局选定的棋盘边长（15/19/23）
  big: { type: Boolean, default: false },       // 页面「放大」：棋盘占左侧主位，其余内容移到右侧辅栏
})

/* ---------- 棋盘尺寸：内部满盘固定，外部开放区可扩（v2.40.30） ----------
 * 内部一律用 FULL×FULL 的坐标存棋子（27×27），**永不重映射**；
 * 开放区（真正在下的棋盘）是它中心的方块，**开局由玩家选定**：15×15 / 19×19 / 23×23，
 * 对局中固定不变 —— 中途改变棋盘会影响五子连珠的规则，不能自动扩。
 * 在线对局不扩展（服务端棋盘固定 15×15，srv2in/in2srv 做坐标翻译）。 */
const FULL = 27
const BASE_MARGIN = 6                       // (27 - 6*2) = 15 起始边长
const SRV_N = 15                            // 服务端棋盘边长
const UNDO_QUOTA = 3                        // 每方每局悔棋上限
/** 开局尺寸 → 外边距（27-15=12→6，27-19=8→4，27-23=4→2；对局中**不再变化**） */
const defaultMargin = computed(() => {
  const size = Number(props.boardSize) || 15
  return Math.max(0, Math.min(BASE_MARGIN, Math.round((FULL - size) / 2)))
})
const margin = ref(defaultMargin.value)     // 开放区外留的边距（开局定死）
const N = computed(() => FULL - margin.value * 2)          // 对外边长 15/19/23/27

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
/** 本地模式悔棋余量（按颜色记，双方各 3 次） */
const undoLeft = ref({ black: UNDO_QUOTA, white: UNDO_QUOTA })
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

/* ---------- 棋盘自适应 ----------
 * 棋盘总宽 = (N + 1) * 格宽 + 16（两侧各 8px 木框 + 半个格宽的内缩），
 * 所以 格宽 = (容器宽 - 16) / (N + 1)。量的是 .gk-main（width:100%），
 * 不能量 .gk-boardwrap —— 它是 inline-block，宽度由棋盘自己决定，量了会自我循环。
 * 普通模式：宽度上限 560，玩家条/邀请面板与棋盘**同宽**（--board-w），避免「壳比盘宽」的错位。
 * 放大模式：棋盘独占左栏，宽度上限放大，且再受可用高度约束（不能竖着溢出）。 */
const mainEl = ref(null)
const cellPx = ref(26)
const MAX_BOARD_W = 560        // 普通模式棋盘宽度上限
const BIG_MAX_BOARD_W = 880    // 放大模式棋盘宽度上限
// 放大时棋盘绕底边后仰 TILT_DEG 度（与 <style> 的 .gk-board 一致）；视觉高度 = 实际 × cos
const TILT_DEG = 20
const TILT_COS = Math.cos((TILT_DEG * Math.PI) / 180)
let resizeHandler = null
function measureCell() {
  const el = mainEl.value
  const availW = el?.clientWidth || 0
  if (!availW) { cellPx.value = N.value > 19 ? 18 : 24; return }
  const capW = props.big ? BIG_MAX_BOARD_W : MAX_BOARD_W
  let cell = Math.floor((Math.min(availW, capW) - 16) / (N.value + 1))
  if (props.big) {
    const availH = el?.clientHeight || 0
    // 盘面平躺后只占 cos 倍高度，按折算后的可用高度放宽格宽，让棋盘铺满主区
    if (availH > 160) cell = Math.min(cell, Math.floor((availH / TILT_COS - 16) / (N.value + 1)))
  }
  cellPx.value = Math.max(11, cell)
}
/** 棋盘实际总宽（与 .gk-board 的盒模型一致）；普通模式下供玩家条/邀请面板对齐 */
const boardW = computed(() => (N.value + 1) * cellPx.value + 16)

/* ---------- 在线对战 ---------- */
const families = ref([])
const inviteeId = ref(null)
const firstPick = ref('me')     // 先手：'me'=我执黑 / 'other'=对方执黑（v2.40.27）
const onlineWinner = ref('')
const lastInviteeName = ref('')
let exited = false               // 已自动退出，避免重复触发

function onRemoteMove(action, userId) {
  // 悔棋事件：弹出栈顶 N 手 —— N=1 只撤自己刚下的那手，N=2 连同对方应招一起撤。
  // 必须按 N 弹，只弹 1 手会让对方（只能靠轮询重放）的棋盘与自己错位。
  if (action?.undo) {
    const plies = action.undo === 2 ? 2 : 1
    for (let i = 0; i < plies; i++) {
      const idx = history.value.pop()
      if (typeof idx === 'number') board.value[idx] = 0
    }
    lastIdx.value = history.value[history.value.length - 1] ?? -1
    winLine.value = []; winner.value = 0; over.value = false
    // 悔棋方重新行棋：按**座位**定色（与落子同一口径），两端重放结果才一致
    const blackId = gRoom.room.value?.black_user_id
    turn.value = (userId != null && blackId != null && userId === blackId) ? HUMAN : AI
    return
  }
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
    const reason = s.end_reason || gRoom.room.value?.end_reason || ''
    // 对手离开/掉线 → 我方**一起退出**，不傻等（夜星反馈 #5）
    if (s.winner_id === uid && (reason === 'leave' || reason === 'timeout')) {
      autoExit(reason)
    }
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
const gRoom = useGameRoom('gomoku', { onRemoteMove, onStatus: onRoomStatus })

const roomActive = computed(() =>
  mode.value === 'online' && !!gRoom.room.value && ['waiting', 'playing'].includes(gRoom.status.value))
const roomLocked = computed(() => roomActive.value)
const onlinePlaying = computed(() => mode.value === 'online' && gRoom.status.value === 'playing')
const onlineMyTurn = computed(() => onlinePlaying.value && gRoom.myTurn.value)
const boardLocked = computed(() => mode.value === 'online' && !onlineMyTurn.value)
/** 棋盘为什么点不动 —— 必须显式告诉用户（显示在棋盘**外面**，不遮棋局） */
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

/* ---------- 悔棋 ---------- */
/** 最后一手是谁下的（本地模式扣谁的配额） */
const lastMoverColor = computed(() => {
  const i = history.value[history.value.length - 1]
  return typeof i === 'number' ? board.value[i] : 0
})
const localQuotaLeft = computed(() =>
  mode.value === 'pvp' ? (lastMoverColor.value === AI ? undoLeft.value.white : undoLeft.value.black)
    : undoLeft.value.black)
const canUndoLocal = computed(() =>
  mode.value !== 'online' && !thinking.value && history.value.length > 0 && localQuotaLeft.value > 0)
const localQuotaText = computed(() => {
  const q = undoLeft.value
  return mode.value === 'pvp' ? `悔棋余量 黑 ${q.black} · 白 ${q.white}` : `悔棋余量 ${q.black} 次`
})
/** 在线：服务端下发的 can_undo 才是权威（最后一手是我下的 → 撤 1 手；对方已应招 → 连应招一起撤 2 手） */
const canUndoOnline = computed(() => mode.value === 'online' && !!gRoom.room.value?.can_undo)

watch(roomActive, (v) => { emit(v ? 'room-lock' : 'room-unlock') })
// 放大/退出放大：布局从单列切成两栏，容器宽高都变了 → 重新量格宽
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
    ElMessage.success(`邀请已发出（${firstPick.value === 'me' ? '你' : lastInviteeName.value || '对方'}执黑先行），等对方接受`)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || e?.msg || '邀请失败')
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
      ElMessage.warning(e?.response?.data?.detail || e?.msg || '邀请失败')
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
  margin.value = mode.value === 'online' ? BASE_MARGIN : defaultMargin.value
  nextTick(measureCell)
  turn.value = HUMAN
  over.value = false
  winner.value = 0
  winLine.value = []
  lastIdx.value = -1
  history.value = []
  thinking.value = false
  onlineWinner.value = ''
  undoLeft.value = { black: UNDO_QUOTA, white: UNDO_QUOTA }
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
      undoLeft: undoLeft.value,
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
  undoLeft.value = s.undoLeft && typeof s.undoLeft.black === 'number'
    ? { black: s.undoLeft.black, white: s.undoLeft.white ?? UNDO_QUOTA }
    : { black: UNDO_QUOTA, white: UNDO_QUOTA }
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

/** 本地悔棋：双人撤 1 手（扣该手落子方的配额），单机撤 2 手（扣自己的配额） */
function undoLocal() {
  if (mode.value === 'online') { undoOnline(); return }
  if (thinking.value || !history.value.length) return
  if (localQuotaLeft.value <= 0) { ElMessage.warning(`本局悔棋次数已用完（每方 ${UNDO_QUOTA} 次）`); return }
  clearTimeout(timer)
  if (mode.value === 'pvp') {
    const idx = history.value.pop()
    const color = board.value[idx]
    board.value[idx] = 0
    if (color === AI) undoLeft.value.white = Math.max(0, undoLeft.value.white - 1)
    else undoLeft.value.black = Math.max(0, undoLeft.value.black - 1)
    turn.value = color || HUMAN          // 撤掉谁的手，就还谁走
  } else {
    const steps = history.value.length >= 2 ? 2 : 1
    for (let i = 0; i < steps && history.value.length; i++) {
      const idx = history.value.pop()
      board.value[idx] = 0
    }
    undoLeft.value.black = Math.max(0, undoLeft.value.black - 1)
    turn.value = HUMAN
  }
  over.value = false; winner.value = 0; winLine.value = []
  lastIdx.value = history.value[history.value.length - 1] ?? -1
}

/** 在线悔棋：服务端校验（撤 1~2 手 + 配额），回吐全量事件后本地重建 */
async function undoOnline() {
  if (!canUndoOnline.value) return
  try {
    const d = await gRoom.undo()
    rebuildFromMoves(d.moves || [])
    if (gRoom.status.value === 'finished') {
      over.value = true
      onlineWinner.value = !d.winner_id ? 'draw' : (d.winner_id === Number(gRoom.myUserId.value) ? 'me' : 'opp')
    }
  } catch (e) {
    ElMessage.warning(e?.response?.data?.msg || e?.msg || '悔棋失败')
  }
}
/** 用事件流重建棋盘（悔棋 / 落子失败恢复都用它） */
function rebuildFromMoves(list) {
  board.value = Array(FULL * FULL).fill(0)
  history.value = []
  lastIdx.value = -1
  winLine.value = []
  winner.value = 0
  over.value = false
  for (const m of list) onRemoteMove(m.action, m.user_id)
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
  clearTimeout(timer); clearTimeout(saveTimer)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  // 离开页面 = 离开对局：对方立刻看到终局（不用等 90s 心跳超时）
  gRoom.leaveOnUnload()
  gRoom.stopPoll()
})
</script>

<style scoped>
.gk-wrap { display: flex; flex-direction: column; align-items: center; gap: 14px; width: 100%; }

/* 辅栏容器：普通模式 display:contents → 子项直接参与 .gk-wrap 的纵向排列（布局与改动前一致） */
.gk-side { display: contents; }
/* 主区（棋盘所在列）：普通模式占满宽度并居中棋盘 */
.gk-main { width: 100%; display: flex; justify-content: center; }

/* ===== 放大模式：左主棋盘 + 右辅栏，主次分明 ===== */
.gk-wrap.is-big {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px 22px;
  width: 100%; height: 100%; min-height: 0;
}
.gk-wrap.is-big .gk-side {
  display: flex; flex-direction: column; gap: 12px;
  grid-column: 2; grid-row: 1; width: 100%; max-height: 100%;
  overflow-y: auto; align-self: start;
}
.gk-wrap.is-big .gk-shell,
.gk-wrap.is-big .gk-online { width: 100%; max-width: 100%; }
.gk-wrap.is-big .gk-locknote { align-self: flex-start; }
.gk-wrap.is-big .gk-players { gap: 10px; }
.gk-wrap.is-big .gk-player { max-width: none; }
.gk-wrap.is-big .gk-main {
  grid-column: 1; grid-row: 1; width: 100%; height: 100%; min-height: 0;
  align-items: center;
}
.gk-wrap.is-big .gk-hint { grid-column: 1; grid-row: 2; }

/* ===== 质感壳：玻璃卡 + 柔和渐变 =====
   宽度 = 棋盘宽（--board-w，由 boardW 计算），与棋局左右边缘严格对齐 */
.gk-shell {
  width: var(--board-w, 100%); max-width: 100%; border-radius: 18px; padding: 16px 18px;
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
.gk-stone-sm { width: 22px; height: 22px; border-radius: 50%; flex: none; }
.gk-stone-sm.black {
  background:
    radial-gradient(circle at 33% 26%, rgba(255,255,255,.85) 0 8%, transparent 42%),
    radial-gradient(circle at 50% 48%, #46505f 0%, #222a36 52%, #0a0e14 100%);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.28), inset -2px -2px 5px rgba(150,185,225,.2), 0 2px 5px rgba(20,30,45,.4);
}
.gk-stone-sm.white {
  background:
    radial-gradient(circle at 33% 26%, rgba(255,255,255,1) 0 12%, transparent 48%),
    linear-gradient(150deg, rgba(255,255,255,.96), rgba(228,234,244,.78) 52%, rgba(198,208,224,.8));
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.9), inset -2px -2px 5px rgba(140,168,205,.3), 0 2px 5px rgba(20,30,45,.28);
}
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

.gk-status { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--dp-text2, #45505b); flex-wrap: wrap; justify-content: center; }
.gk-quota { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.gk-btn { padding: 5px 14px; border-radius: 9px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }
.gk-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gk-btn:disabled { opacity: .5; cursor: default; }

/* 邀请面板：与玩家条/棋盘同宽 */
.gk-online {
  width: var(--board-w, 100%); max-width: 100%; border-radius: 18px; padding: 18px;
  background: linear-gradient(160deg, rgba(255,255,255,.75), rgba(255,255,255,.45));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1)); box-shadow: 0 8px 28px rgba(20,30,40,.08);
}
.gk-online-title { font-size: 15px; font-weight: 700; color: var(--dp-text, #18202a); }
.gk-online-desc { margin: 6px 0 10px; font-size: 12px; color: var(--dp-text3, #8a8f98); line-height: 1.7; }
.gk-online-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.gk-first-row { display: flex; align-items: center; gap: 6px; margin: 8px 0; flex-wrap: wrap; }
.gk-first-label { font-size: 12.5px; color: var(--dp-text3, #8a8f98); }
.gk-firstnote { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }


/* 锁定提示：棋盘外的独立一行（不遮挡棋局） */
.gk-locknote {
  display: inline-flex; align-items: center; gap: 8px; margin: 0;
  font-size: 12.5px; font-weight: 600; color: var(--dp-text2, #45505b);
  background: rgba(199,169,107,.14); padding: 7px 16px; border-radius: 999px;
}
.gk-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--yq-gold, #c7a96b); animation: gkpulse 1.2s infinite; }

/* ===== 棋盘：网格线画在格心 → 棋子落在交叉点上 ===== */
.gk-boardwrap {
  position: relative; display: inline-block;
  /* 透视容器：放大后棋盘绕底边后仰平躺，像摆在桌面上 */
  perspective: 2400px; perspective-origin: 50% 34%;
}
.gk-board {
  position: relative;
  display: grid;
  /* 内边距 = 半个格宽 + 8px 木框；总宽 = (N+1)*格宽 + 16px（measureCell 按此反算） */
  padding: calc(var(--cell, 26px) / 2 + 8px);
  background: linear-gradient(135deg, #e8d9b8, #dcc79a);
  border-radius: 14px;
  touch-action: manipulation; user-select: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.15), 0 10px 30px rgba(20,30,40,.12);
  transform-origin: 50% 100%;
  transform: rotateX(var(--tilt, 0deg));
  transition: transform .3s cubic-bezier(.4, .1, .2, 1), filter .2s;
  will-change: transform;
  --gk-line: rgba(40, 30, 10, .5);
}
.gk-wrap.is-big .gk-board {
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.15), 0 30px 46px -22px rgba(45, 32, 14, .55);
}
.gk-board.locked { filter: saturate(.75) brightness(.94); pointer-events: none; }
/* 网格线覆盖层：从第一个交叉点画到最后一个，间距 = 格宽 */
.gk-grid {
  position: absolute;
  left: calc(var(--cell, 26px) + 8px);
  top: calc(var(--cell, 26px) + 8px);
  width: calc(var(--cell, 26px) * (var(--n, 15) - 1) + 1px);
  height: calc(var(--cell, 26px) * (var(--n, 15) - 1) + 1px);
  background-image:
    repeating-linear-gradient(to right, var(--gk-line) 0 1px, transparent 1px var(--cell, 26px)),
    repeating-linear-gradient(to bottom, var(--gk-line) 0 1px, transparent 1px var(--cell, 26px));
  pointer-events: none;
}
.gk-cell { border: none; padding: 0; background: transparent; cursor: pointer; position: relative; }
/* 悬停提示：空格子上浮现淡影 */
.gk-cell:hover::after { content: ''; position: absolute; inset: 30%; border-radius: 50%; background: rgba(30,20,0,.16); }
.gk-cell.last:hover::after, .gk-cell.win:hover::after { content: none; }
.gk-stone { position: absolute; inset: 7%; border-radius: 50%; display: block; }
/* 水晶棋子：一点高光 + 内部折射 + 边缘反光（黑白仍一眼可辨） */
.gk-stone.black {
  background:
    radial-gradient(circle at 33% 26%, rgba(255,255,255,.9) 0 7%, rgba(255,255,255,.26) 20%, transparent 44%),
    radial-gradient(circle at 68% 80%, rgba(170,200,235,.3) 0 8%, transparent 34%),
    radial-gradient(circle at 50% 48%, #46505f 0%, #222a36 52%, #0a0e14 100%);
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.3),
    inset 2px 3px 7px rgba(255,255,255,.16),
    inset -3px -4px 9px rgba(150,185,225,.22),
    0 3px 7px rgba(20, 30, 45, .45);
}
.gk-stone.white {
  background:
    radial-gradient(circle at 33% 26%, rgba(255,255,255,1) 0 10%, rgba(255,255,255,.6) 26%, transparent 50%),
    radial-gradient(circle at 68% 80%, rgba(255,255,255,.5) 0 8%, transparent 32%),
    linear-gradient(150deg, rgba(255,255,255,.96), rgba(228,234,244,.78) 52%, rgba(198,208,224,.8));
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.9),
    inset -3px -4px 9px rgba(140,168,205,.3),
    0 3px 7px rgba(20, 30, 45, .3);
}
/* 最后一手：子上一枚红点 */
.gk-cell.last .gk-stone::after {
  content: ''; position: absolute; left: 50%; top: 50%; width: 22%; height: 22%;
  margin: -11% 0 0 -11%; border-radius: 50%; background: #e5484d;
}
/* 五连高亮：用 outline 画红环（不覆盖棋子自身的水晶投影） */
.gk-cell.win .gk-stone {
  outline: 2px solid rgba(229,72,77,.9); outline-offset: -2px;
  filter: drop-shadow(0 0 6px rgba(229,72,77,.6));
}
.gk-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center; }

@media (max-width: 480px) {
  /* 格宽由 measureCell 按容器反算（.gk-board 的 --cell 是内联样式，这里覆盖不到），
     故小屏只收壳的留白，不再重复声明 --cell */
  .gk-shell { padding: 12px; }
  .gk-players { gap: 8px; }
}

/* 窄屏：放大模式退回单列（棋盘在上、辅栏在下），避免两栏把棋盘挤成一条 */
@media (max-width: 900px) {
  .gk-wrap.is-big { grid-template-columns: 1fr; grid-template-rows: auto auto auto; height: auto; }
  .gk-wrap.is-big .gk-side { grid-column: 1; grid-row: 1; max-height: none; overflow: visible; }
  .gk-wrap.is-big .gk-main { grid-column: 1; grid-row: 2; height: auto; }
  .gk-wrap.is-big .gk-hint { grid-column: 1; grid-row: 3; }
}

/* ===== 夜间主题：深木纹棋盘 + 深色玻璃壳（此前白壳压在纯黑底上，发灰看不清） ===== */
:root[data-theme="night"] .gk-shell,
:root[data-theme="night"] .gk-online {
  background: linear-gradient(160deg, rgba(38,44,58,.94), rgba(22,26,36,.92));
  border-color: rgba(199,169,107,.3);
  box-shadow: 0 8px 28px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.07);
}
:root[data-theme="night"] .gk-player-txt b { color: #f2eee4; }
:root[data-theme="night"] .gk-player-txt i { color: #b9b3cc; }
:root[data-theme="night"] .gk-player.active { background: rgba(199,169,107,.18); }
:root[data-theme="night"] .gk-online-title { color: #f2eee4; }
:root[data-theme="night"] .gk-online-desc,
:root[data-theme="night"] .gk-first-label,
:root[data-theme="night"] .gk-firstnote,
:root[data-theme="night"] .gk-quota { color: #b9b3cc; }
:root[data-theme="night"] .gk-hint { color: #a9a3bd; }
:root[data-theme="night"] .gk-status { color: #ded9ee; }
:root[data-theme="night"] .gk-btn {
  background: rgba(255,255,255,.09); border-color: rgba(255,255,255,.2); color: #ece7dc;
}
:root[data-theme="night"] .gk-btn:hover:not(:disabled) { border-color: rgba(252,211,77,.6); color: #fde68a; }
:root[data-theme="night"] .gk-btn.primary { background: #c7a96b; border-color: #c7a96b; color: #1a1509; }
:root[data-theme="night"] .gk-mode { color: #ded9ee; border-color: rgba(255,255,255,.2); }
:root[data-theme="night"] .gk-banner.st-waiting { background: rgba(199,169,107,.2); color: #ded9ee; }
:root[data-theme="night"] .gk-banner.st-playing { background: rgba(127,168,163,.22); color: #ded9ee; }
:root[data-theme="night"] .gk-banner.st-finished { background: rgba(199,169,107,.26); color: #f6f2e8; }
:root[data-theme="night"] .gk-locknote { background: rgba(199,169,107,.22); color: #ded9ee; }
:root[data-theme="night"] .gk-board {
  background: linear-gradient(135deg, #6d5836, #4f3f26);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.12), 0 10px 30px rgba(0,0,0,.55);
  --gk-line: rgba(255, 236, 190, .5);
}
:root[data-theme="night"] .gk-wrap.is-big .gk-board {
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.12), 0 30px 48px -22px rgba(0,0,0,.8);
}
:root[data-theme="night"] .gk-stone.black {
  background:
    radial-gradient(circle at 33% 26%, rgba(255,255,255,.8) 0 7%, rgba(255,255,255,.22) 20%, transparent 44%),
    radial-gradient(circle at 68% 80%, rgba(170,200,235,.24) 0 8%, transparent 34%),
    radial-gradient(circle at 50% 48%, #3c4552 0%, #1b222c 52%, #05070a 100%);
  box-shadow:
    inset 0 0 0 1px rgba(178,204,238,.42),
    inset 2px 3px 7px rgba(255,255,255,.18),
    inset -3px -4px 9px rgba(150,185,225,.28),
    0 3px 8px rgba(0,0,0,.7);
}
:root[data-theme="night"] .gk-stone.white {
  background:
    radial-gradient(circle at 33% 26%, rgba(255,255,255,.98) 0 10%, rgba(255,255,255,.55) 26%, transparent 50%),
    radial-gradient(circle at 68% 80%, rgba(255,255,255,.42) 0 8%, transparent 32%),
    linear-gradient(150deg, rgba(250,252,255,.94), rgba(220,228,240,.78) 52%, rgba(186,198,216,.8));
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.85),
    inset -3px -4px 9px rgba(120,150,190,.35),
    0 3px 8px rgba(0,0,0,.6);
}
:root[data-theme="night"] .gk-stone-sm.black {
  background: radial-gradient(circle at 33% 26%, rgba(255,255,255,.75) 0 8%, transparent 42%),
    radial-gradient(circle at 50% 48%, #3c4552 0%, #1b222c 52%, #05070a 100%);
  box-shadow: inset 0 0 0 1px rgba(178,204,238,.4), 0 2px 5px rgba(0,0,0,.6);
}
:root[data-theme="night"] .gk-stone-sm.white {
  background: radial-gradient(circle at 33% 26%, rgba(255,255,255,1) 0 12%, transparent 48%),
    linear-gradient(150deg, rgba(250,252,255,.94), rgba(220,228,240,.78) 52%, rgba(186,198,216,.8));
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.85), 0 2px 5px rgba(0,0,0,.5);
}
</style>
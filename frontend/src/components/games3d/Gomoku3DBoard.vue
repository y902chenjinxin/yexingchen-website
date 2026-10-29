<template>
  <div class="g3d-board">
    <!-- 顶栏：所有操作塞这里，舞台内不放任何浮动条 ——
         3D 透视下棋盘远端会向上延伸，任何 absolute 浮动条都会压盘（v2.46.263 的教训）。 -->
    <header v-if="showTopbar" class="g3d-topbar">
      <div class="g3d-title">
        <span class="g3d-logo">3D</span>
        <div class="g3d-tx">
          <b>3D 五子棋</b>
          <i v-if="online">{{ onlineHint }}</i>
          <i v-else>电脑 {{ count.white }} 子 · {{ over ? '已结束' : (thinking ? '思考中…' : (turn === BLACK ? '轮到你走' : '轮到电脑')) }}</i>
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
          <button v-else-if="canUndoOnline" class="g3d-op ghost" @click="undoOnline">悔棋（余 {{ room.undo_left ?? gRoom.undoLeft.value }}）</button>
          <button v-if="room" class="g3d-op ghost" @click="leaveRoom">退出对局</button>
        </template>
        <button class="g3d-op ghost" @click="$emit('exit')">返回</button>
      </div>
    </header>

    <!-- 3D 舞台 -->
    <div class="g3d-stage">
      <div class="g3d-world" :style="{ transform: world.tf, top: world.top }">
        <!-- 棋盘：木底 + 厚 18。只做看得见的四个面 —— 底面与背面在 54° 视角下永远不出现，做了是白渲染 -->
        <div class="gk3-slab" :class="{ 'is-shake': shake }" :style="boxVars(BOARD, BOARD, 24)">
          <div class="gk3-face gk3-top">
            <svg class="gk3-grid" :viewBox="`0 0 ${BOARD} ${BOARD}`" aria-hidden="true">
              <line v-for="n in SIZE" :key="'h' + n"
                :x1="PAD" :y1="PAD + (n - 1) * CELL" :x2="BOARD - PAD" :y2="PAD + (n - 1) * CELL" />
              <line v-for="n in SIZE" :key="'v' + n"
                :x1="PAD + (n - 1) * CELL" :y1="PAD" :x2="PAD + (n - 1) * CELL" :y2="BOARD - PAD" />
              <circle v-for="(s, i) in STARS" :key="'s' + i" class="gk3-star"
                :cx="PAD + s[0] * CELL" :cy="PAD + s[1] * CELL" r="3.4" />
            </svg>
          </div>
          <div class="gk3-face gk3-front"></div>
          <div class="gk3-face gk3-left"></div>
          <div class="gk3-face gk3-right"></div>
        </div>

        <!-- 落点：每个空交叉点一个透明命中层。
             🔴 一律用 DOM 元素接点击，不用 clientX/clientY 反算格子 ——
                透视下屏幕坐标与棋盘坐标不是线性关系，反算必错（v2.46.2-001 那条）。 -->
        <div
          v-for="i in empties"
          :key="'hit' + i"
          class="gk3-hit"
          :style="hitStyle(i)"
          @click="play(i)"
        />

        <!-- 棋子 -->
        <div
          v-for="s in stones"
          :key="'st' + s.idx"
          class="gk3-stone"
          :class="[
            s.color === BLACK ? 'black' : 'white',
            { 'is-win': winSet.has(s.idx), 'is-last': s.idx === lastIdx && !over },
          ]"
          :style="stoneStyle(s.idx)"
        >
          <i class="gk3-stone-side"></i>
          <i class="gk3-stone-top"></i>
        </div>

        <!-- 🔴 不放 3D 座位铭牌（v2.46.277）：SEAT_SLOT 是按 660 见方的牌桌标定的，
             棋盘只有 512，铭牌会飘到棋盘上方很远（竖屏探针实测）。
             两人对局的信息量顶栏一行就够了，不再往舞台里塞东西。 -->
      </div>
    </div>

    <!-- 我：左下角 HUD（屏幕坐标系，不参与 3D 变换） -->
    <div class="gt3-seat gt3-self" :class="{ 'is-turn': !over && turn === BLACK }">
      <div class="gt3-ava me"><AppIcon icon="🙂" /></div>
      <div class="gt3-meta">
        <b>你</b>
        <i :class="{ turn: !over && turn === BLACK }">{{ over ? '已结束' : '黑方' }}</i>
      </div>
      <div class="gt3-score is-you">
        <span class="snum">{{ count.black }}</span><span class="slbl">子</span>
      </div>
    </div>

    <!-- 在线邀请面板：只在「在线模式且还没房间」时出现，盖在棋盘上方居中 -->
    <div v-if="online && panelOpen && !room" class="g3d-invite">
      <div class="g3d-invite-card">
        <h3>在线邀请对战</h3>
        <p>选一位家人发出邀请，对方接受后进入对局。落子自动同步，约 2 秒可见。</p>
        <MemberPicker v-model="inviteeId" :members="families" placeholder="选择一位家人…" />
        <div class="g3d-invite-row">
          <span>先手</span>
          <button class="g3d-op ghost" :class="{ on: firstPick === 'me' }" @click="firstPick = 'me'">我执黑</button>
          <button class="g3d-op ghost" :class="{ on: firstPick === 'other' }" @click="firstPick = 'other'">对方执黑</button>
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

    <!-- 结算：延迟 0.9s 才弹，先让五连的金色呼吸高亮被看见（v2.46.277） -->
    <div v-if="showResult" class="g3d-over is-chess">
      <div class="ov-card">
        <h2>{{ winner === BLACK ? '你赢了' : (winner === WHITE ? '电脑赢了' : '平局') }}</h2>
        <p>共 {{ history.length }} 手<template v-if="winner"> · {{ winner === BLACK ? '黑' : '白' }}方五连</template></p>
        <div class="ov-acts">
          <button class="g3d-btn ghost" @click="restart">再来一局</button>
          <button class="g3d-btn primary" @click="$emit('exit')">返回大厅</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 3D 五子棋（v2.46.277）
 *
 * 规则 / AI 在 utils/games/gomokuAI.js（固定 15×15），渲染沿用 3D 牌桌的 CSS 语言：
 * .g3d-stage 给透视，.g3d-world 整体绕 X 轴倾斜，棋盘是有厚度的板，
 * 棋子是**平躺在盘面上的圆片**（rotateX(-90deg)），透视下自然呈椭圆、带侧厚。
 *
 * 与 2D 版的差别：固定 15 路、不做「动态扩棋盘」。这是标准五子棋，
 * 也让 3D 的坐标换算保持常量（扩棋盘会导致每次落子重排整盘 DOM）。
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
import { BLACK, WHITE, EMPTY, SIZE, checkWinFrom } from '@/utils/games/gomokuAI'
import AppIcon from '@/components/common/AppIcon.vue'
/* 样式由组件自己引：别的入口（棋类大厅直达）不经过 Games3DView，
   否则在线/直达场景会渲染成一堆无样式方块（v2.46.263 踩过） */
import '@/assets/styles/games3d.css'

const props = defineProps({
  showTopbar: { type: Boolean, default: true },
  /** 在线对局（走 game_rooms 事件流，对手是真人） */
  online: { type: Boolean, default: false },
  /** 从「我的棋局」点进来时带房间号，挂载即加入 */
  joinRoomId: { type: Number, default: 0 },
})
defineEmits(['exit'])
const online = computed(() => props.online)

/* ---------- 几何 ---------- */
const CELL = 32                              // 格距
const PAD = 32                               // 边线到板边
const BOARD = (SIZE - 1) * CELL + PAD * 2    // 512
const STONE_Z = 16                           // 圆片抬到板面上方（板厚 24 → 顶面 z = 12）

/* 54° 是权衡值：再倾斜远端格距就压到看不清，再平就没立体感。
   投影高度 ≈ 512 × cos54° ≈ 301px；缩放与原点由 boardWorld 按横/竖屏给
   （横屏 .90 让底边落在 341px，避开 left-bottom HUD 的 348px）。 */
const world = ref(boardWorld(54, BOARD, 0.9))
function onResize() { world.value = boardWorld(54, BOARD, 0.9) }

/* 15 路标准星位 */
const STARS = [[3, 3], [11, 3], [7, 7], [3, 11], [11, 11]]

const px = i => (i % SIZE) * CELL - BOARD / 2 + PAD
const py = i => (((i / SIZE) | 0) * CELL) - BOARD / 2 + PAD

/* z 必须 > 板厚/2 = 12：否则命中层躺在木板内部，会被 .gk3-top 挡在下面，
   点不到（探针实测点击无效），落点也看不见。 */
const hitStyle = i => ({ transform: `translate(-50%,-50%) translate3d(${px(i)}px,${py(i)}px,14px)` })
function stoneStyle(i) {
  const x = px(i)
  const y = py(i)
  return {
    '--bx': `${x}px`,
    '--by': `${y}px`,
    transform: `translate(-50%,-50%) translate3d(${x}px,${y}px,${STONE_Z}px) rotateX(-90deg)`,
  }
}

/* ---------- 状态 ---------- */
const board = ref(new Array(SIZE * SIZE).fill(EMPTY))
const history = ref([])        // 落子先后（下标），撤销只认它
const turn = ref(BLACK)
const lastIdx = ref(-1)
const winLine = ref([])
const winner = ref(0)
const over = ref(false)       // 锁盘（禁止再落子）
const showResult = ref(false) // 结算浮层（比锁盘晚 0.9s）
const thinking = ref(false)
const toast = ref('')
const shake = ref(false)
const diff = ref('normal')

let aiTimer = null
let toastTimer = null
let shakeTimer = null
let resultTimer = null

const DIFFS = [
  { key: 'easy', label: '简单', depth: 1 },
  { key: 'normal', label: '普通', depth: 2 },
  { key: 'hard', label: '困难', depth: 4 },
]
const depth = () => DIFFS.find(d => d.key === diff.value)?.depth ?? 2
const diffLabel = computed(() => DIFFS.find(d => d.key === diff.value)?.label || '普通')

const stones = computed(() => {
  const out = []
  for (let i = 0; i < board.value.length; i++) {
    if (board.value[i]) out.push({ idx: i, color: board.value[i] })
  }
  return out
})
const empties = computed(() => {
  const out = []
  for (let i = 0; i < board.value.length; i++) if (!board.value[i]) out.push(i)
  return out
})
const winSet = computed(() => new Set(winLine.value))
const count = computed(() => ({
  black: board.value.filter(v => v === BLACK).length,
  white: board.value.filter(v => v === WHITE).length,
}))
const canUndo = computed(() => !thinking.value && !over.value && history.value.length > 0)

function say(t) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1400)
}

/* ---------- 落子 ---------- */
function play(i) {
  if (over.value || thinking.value) return
  if (board.value[i]) return
  if (online.value) {
    if (!onlineMyTurn.value) { say('还没轮到你'); return }
    drop(i, myColorCode.value, false)
    return
  }
  if (turn.value !== BLACK) { say('等电脑落子'); return }
  drop(i, BLACK)
}

function drop(i, color) {
  board.value[i] = color
  history.value.push(i)
  lastIdx.value = i
  if (!replaying) sfx.stone()

  const line = checkWinFrom(board.value, i, color)
  if (line) {
    winLine.value = line
    winner.value = color
    over.value = true
    thinking.value = false
    if (!replaying) sfx.win()
    /* 在线：由我方判定胜负后上报服务端（五子棋服务端也会重放校验，双保险） */
    if (online.value && !replaying && color === myColorCode.value) {
      const uid = Number(gRoom.myUserId.value)
      if (uid) gRoom.finish(uid).catch(() => {})
    }
    shake.value = true
    clearTimeout(shakeTimer)
    shakeTimer = setTimeout(() => { shake.value = false }, 620)
    clearTimeout(resultTimer)
    /* 先给五连的高亮一点时间，再弹浮层 —— 否则玩家根本看不到自己赢在哪 */
    resultTimer = setTimeout(() => { showResult.value = true }, 900)
    return
  }
  if (!board.value.includes(EMPTY)) {
    over.value = true
    clearTimeout(resultTimer)
    resultTimer = setTimeout(() => { showResult.value = true }, 600)
    return
  }

  turn.value = color === BLACK ? WHITE : BLACK
  /* 在线：落子要上报，但不跑本地 AI（对手是真人） */
  if (online.value) {
    if (!replaying && color === myColorCode.value) gRoom.send({ idx: i }).catch(() => {})
    return
  }
  if (turn.value === WHITE) scheduleAI()
}

function scheduleAI() {
  clearTimeout(aiTimer)
  thinking.value = true
  /* v2.46.278：搜索搬进 Web Worker。原来在主线程跑 depth 4，
     点完到落子之间整页卡 0.5~1.5 秒（夜星：「忍不了」）。
     先等 140ms 让这一手先画出来，再派给 worker。
     棋盘必须拷贝成普通数组 —— postMessage 不认 reactive proxy。 */
  aiTimer = setTimeout(async () => {
    const i = await runAI('gomoku', { board: [...board.value], depth: depth() })
    thinking.value = false
    /* i === null 表示这次计算被作废（重开/悔棋），或者算失败 —— 都不能落子 */
    if (i == null || i < 0 || board.value[i]) return
    drop(i, WHITE)
  }, 140)
}

/* ================= 在线对局（v2.46.278） =================
 * 服务端是 game_rooms 的事件流：进房时 join() 会把**全部历史**重放一遍
 * （自己和对手的都在里面），所以这里不能按「现在轮到我」过滤，
 * 必须按 userId 归色重放，否则恢复回来的棋盘会缺子。
 * 坐标：服务端就是 15×15 扁平下标，与 3D 棋盘完全一致，不需要任何映射。
 */
const families = ref([])
const inviteeId = ref(null)
const firstPick = ref('me')
const panelOpen = ref(false)
const joining = ref(false)
let replaying = false     // 重放期间静音 + 不上报

const room = computed(() => gRoom.room.value)
const myColorCode = computed(() => (gRoom.mySeat.value === 'white' ? WHITE : BLACK))
const onlineMyTurn = computed(() => gRoom.status.value === 'playing' && gRoom.myTurn.value)
const canUndoOnline = computed(() => gRoom.status.value === 'playing' && !over.value && gRoom.undoPlies.value > 0)

const onlineHint = computed(() => {
  if (!room.value) return '还没开局 · 点右上「邀人对局」'
  const st = gRoom.status.value
  const who = gRoom.opponentName.value || '对方'
  if (st === 'waiting') return `等「${who}」接受邀请…`
  if (st === 'playing') {
    return gRoom.myTurn.value
      ? `轮到你（${myColorCode.value === BLACK ? '黑' : '白'}）`
      : `等「${who}」落子…`
  }
  return '对局已结束'
})

/** 按服务端座位表把 userId 换算成颜色（重放与实时都走这里） */
function seatColorOf(userId) {
  const blackId = room.value?.black_user_id
  if (blackId == null || userId == null) return BLACK
  return Number(userId) === Number(blackId) ? BLACK : WHITE
}

function onRemoteMove(action, userId) {
  if (!action) return
  if (action.undo) {
    const plies = action.undo === 2 ? 2 : 1
    for (let k = 0; k < plies; k++) {
      const i = history.value.pop()
      if (typeof i === 'number') board.value[i] = EMPTY
    }
    over.value = false
    showResult.value = false
    winner.value = 0
    winLine.value = []
    lastIdx.value = history.value.length ? history.value[history.value.length - 1] : -1
    turn.value = seatColorOf(userId)
    return
  }
  const i = action.idx
  if (typeof i !== 'number' || i < 0 || i >= SIZE * SIZE) return
  if (board.value[i]) return
  drop(i, seatColorOf(userId))
}

function onRoomStatus(st) {
  if (st?.status !== 'finished') return
  over.value = true
  thinking.value = false
  const uid = Number(gRoom.myUserId.value)
  if (!st.winner_id) { winner.value = 0; return }
  winner.value = Number(st.winner_id) === uid ? myColorCode.value : (myColorCode.value === BLACK ? WHITE : BLACK)
  const reason = gRoom.endReason.value || room.value?.end_reason || ''
  if (Number(st.winner_id) === uid && (reason === 'leave' || reason === 'timeout')) {
    ElMessage.info(reason === 'timeout' ? '对方已掉线，对局结束' : '对方已离开，对局结束')
  }
  showResult.value = true
}

const gRoom = useGameRoom('gomoku', { onRemoteMove, onStatus: onRoomStatus })

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
  try { await gRoom.undo() } catch { /* 服务端会拒绝并给原因，下一轮轮询自然对齐 */ }
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
  /* 单机每轮是 黑→白，所以撤到「轮到黑」为止：
     最后一手是白就撤两手，否则撤一手。 */
  const lastColor = board.value[history.value[history.value.length - 1]]
  const steps = lastColor === WHITE ? 2 : 1
  for (let k = 0; k < steps; k++) {
    const i = history.value.pop()
    if (i === undefined) break
    board.value[i] = EMPTY
  }
  over.value = false
  showResult.value = false
  winner.value = 0
  winLine.value = []
  turn.value = BLACK
  lastIdx.value = history.value.length ? history.value[history.value.length - 1] : -1
  sfx.pick()
}

function restart() {
  clearTimeout(aiTimer)
  clearTimeout(resultTimer)
  invalidateAI()
  thinking.value = false
  board.value = new Array(SIZE * SIZE).fill(EMPTY)
  history.value = []
  turn.value = BLACK
  lastIdx.value = -1
  winLine.value = []
  winner.value = 0
  over.value = false
  showResult.value = false
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
  /* 没有指定房间：接回进行中的那局（刷新/换设备不丢） */
  try {
    const res = await gameRoomsApi.mine()
    const active = (res?.data?.list || []).find(x => x.game === 'gomoku' && ['waiting', 'playing'].includes(x.status))
    if (active) {
      replaying = true
      await gRoom.join(active.id, { autoAccept: active.status === 'playing' })
      replaying = false
      ElMessage.success(`已接回与「${gRoom.opponentName.value}」的对局`)
      return
    }
  } catch { /* 没有进行中的对局 */ }
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

/* 本地渲染探针用：直接摆一个局面，省得手点 20 手 */
defineExpose({ board, history, drop, restart, setDiff: (k) => { diff.value = k }, getDiff: () => diff.value })
</script>

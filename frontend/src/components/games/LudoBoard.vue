<template>
  <div ref="wrapEl" class="lb-wrap">
    <!-- ===== 玩家条（玻璃壳） ===== -->
    <div class="lb-shell">
      <div class="lb-players">
        <div
          v-for="c in activeColors"
          :key="c"
          class="lb-player"
          :class="{ active: !over && turnColor === c }"
          :style="{ '--pc': META[c].main }"
        >
          <span class="lb-chip"></span>
          <div class="lb-ptxt">
            <b>{{ playerLabel(c) }}</b>
            <i><AppIcon v-if="seatIcon(c)" :icon="seatIcon(c)" :size="13" /> {{ seatStatus(c) }}</i>
          </div>
          <span class="lb-mini">
            <em v-for="k in 4" :key="k" :class="{ done: pieces[c][k - 1].prog === FINISH }"></em>
          </span>
        </div>
      </div>

      <!-- 模式（页面已选则隐藏） -->
      <div v-if="!bare" class="lb-modes">
        <button
          v-for="m in MODES"
          :key="m.key"
          class="lb-mode"
          :class="{ on: mode === m.key }"
          :disabled="mode === 'online' && roomActive"
          @click="setMode(m.key)"
        >{{ m.label }}</button>
      </div>

      <!-- 在线横幅 -->
      <div v-if="mode === 'online' && gRoom.room.value" class="lb-banner" :class="'st-' + gRoom.status.value">
        <template v-if="gRoom.status.value === 'waiting'">
          <span class="lb-pulse"></span> 邀请已发给 {{ gRoom.opponentName.value }}，等待接受…
          <button class="lb-btn" @click="cancelInvite">取消邀请</button>
        </template>
        <template v-else-if="gRoom.status.value === 'playing'">
          <span>{{ turnColor === myColor ? '轮到你掷骰' : `等 ${gRoom.opponentName.value} 掷骰…` }}</span>
          <button class="lb-btn" @click="askExit">退出对局（认输）</button>
        </template>
        <template v-else-if="gRoom.status.value === 'finished'">
          <span class="lb-result"><AppIcon v-if="onlineResultIcon" :icon="onlineResultIcon" :size="16" /> {{ onlineResultText }}</span>
          <button class="lb-btn primary" @click="reinviteSame">再来一局</button>
          <button class="lb-btn" @click="exitOnline">退出</button>
        </template>
      </div>

      <!-- 本地对局操作 -->
      <div v-if="mode !== 'online'" class="lb-status">
        <span v-if="over" class="lb-result"><AppIcon v-if="resultIcon" :icon="resultIcon" :size="16" /> {{ resultText }}</span>
        <button class="lb-btn" @click="restart">重开一局</button>
        <span class="lb-quota">归航 {{ finishedTotal }}/{{ activeColors.length * 4 }}</span>
      </div>
    </div>

    <!-- 在线：邀请面板 -->
    <div v-if="mode === 'online' && !gRoom.room.value" class="lb-online">
      <div class="lb-online-title"><AppIcon icon="🎯" /> 在线邀请对战</div>
      <p class="lb-online-desc">选一位家人发出邀请，对方接受后开局；你执红先手，掷骰与走子约 2 秒内同步。</p>
      <div class="lb-online-row">
        <MemberPicker v-model="inviteeId" :members="families" placeholder="选择一位家人…" />
        <button class="lb-btn primary" :disabled="!inviteeId || gRoom.joining.value" @click="invite">
          {{ gRoom.joining.value ? '创建中…' : '发出邀请' }}
        </button>
      </div>
      <p v-if="!families.length" class="lb-online-desc">家庭里还没有其他账号可以邀请。</p>
    </div>

    <!-- 锁定原因：棋盘外的独立一行，不遮挡棋局 -->
    <p v-if="lockHint" class="lb-locknote"><span class="lb-dot"></span>{{ lockHint }}</p>

    <!-- ===== 棋盘 ===== -->
    <div class="lb-boardwrap">
      <div class="lb-board" :class="{ locked: boardLocked }">
        <!-- 基地（四角） -->
        <div
          v-for="c in COLORS"
          :key="'base' + c"
          class="lb-base"
          :class="{ dim: !activeColors.includes(c) }"
          :style="baseStyle(c)"
        >
          <span
            v-for="k in 4"
            :key="k"
            class="lb-slot"
            :style="slotStyle(k - 1)"
          ></span>
        </div>

        <!-- 中心归航区 -->
        <div class="lb-center" :style="centerStyle">
          <span class="lb-center-star"><AppIcon icon="✦" :size="15" /></span>
        </div>

        <!-- 外圈轨道 -->
        <div
          v-for="(rc, i) in TRACK"
          :key="'t' + i"
          class="lb-cell"
          :class="{
            'own': ownTrackSet.has(i),
            'fly': i === flyRing,
            'evt': !!EVENT_CELLS[i],
            ['evt-' + EVENT_CELLS[i]]: !!EVENT_CELLS[i],
          }"
          :style="cellStyle(rc)"
        >
          <template v-if="EVENT_CELLS[i]">
            <span class="lb-evt-ico"><AppIcon :icon="EVENT_META[EVENT_CELLS[i]].icon" :size="15" /></span>
            <span class="lb-evt-tag">{{ EVENT_META[EVENT_CELLS[i]].short }}</span>
          </template>
        </div>

        <!-- 归航通道 -->
        <template v-for="c in COLORS" :key="'h' + c">
          <div
            v-for="(rc, i) in HOME[c]"
            :key="c + i"
            class="lb-cell home"
            :class="{ dim: !activeColors.includes(c) }"
            :style="cellStyle(rc, META[c].main)"
          ></div>
        </template>

        <!-- 棋子 -->
        <button
          v-for="p in pieceViews"
          :key="p.key"
          class="lb-piece"
          :class="{ movable: p.movable, finished: p.finished }"
          :style="p.style"
          :aria-label="`${playerLabel(p.color)}第${p.i + 1}架`"
          @click="onPieceClick(p)"
        >
          <svg class="lb-plane" viewBox="0 0 24 24" :style="{ transform: `rotate(${p.rot}deg)` }" aria-hidden="true">
            <path d="M12 2.5C12.9 2.5 13.6 3.3 13.6 4.3L13.6 9.2L21.5 13.6L21.5 15.7L13.6 13.3L13.6 17.6L16 19.4L16 21.2L12 20L8 21.2L8 19.4L10.4 17.6L10.4 13.3L2.5 15.7L2.5 13.6L10.4 9.2L10.4 4.3C10.4 3.3 11.1 2.5 12 2.5Z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- ===== 控制区：骰子 + 按钮 + 战报 ===== -->
    <div class="lb-ctrl">
      <div class="lb-dicebox">
        <div class="lb-dice" :class="{ rolling: rolling }">
          <i v-for="n in 9" :key="n" :class="{ on: dicePips.includes(n - 1) }"></i>
        </div>
        <button class="lb-roll" :disabled="!canRoll" @click="doRoll">{{ rollLabel }}</button>
        <!-- 棋盘下方就在手边：页面头部的「返回列表」滚下去就看不见了 -->
        <button class="lb-btn" @click="emit('exit')">返回列表</button>
      </div>
      <ul class="lb-log">
        <li v-for="(l, i) in log" :key="i" :class="{ fresh: i === log.length - 1 }"><AppIcon v-if="l.icon" :icon="l.icon" :size="13" /> {{ l.text }}</li>
      </ul>
    </div>

    <p class="lb-hint">
      掷 1 或 6 均可起飞 · 掷 6 或击落对方可再掷一次 · 踩到自己颜色前进 4 格 · 第 18 格触发飞行通道直飞 12 格 ·
      超出终点直接归航（不弹回）· 四架全部归航者获胜
    </p>

    <div class="lb-legend">
      <span class="lb-lg-title">事件格</span>
      <span
        v-for="(m, k) in EVENT_META"
        :key="k"
        class="lb-lg"
        :class="'lg-' + k"
      ><i><AppIcon :icon="m.icon" :size="15" /></i>{{ m.name }} · {{ m.tip }}</span>
    </div>
  </div>
</template>

<script setup>
/** 飞行棋（中国规则，自写，无外部依赖）。
 *
 * 为什么自写：原先用第三方静态页 `<iframe>` 嵌入（LudoEmbed.vue），
 * 它的「选择人数」弹层是 `position:fixed; inset:0` 且无 `overflow`，
 * 被 iframe 的固定高度上下裁切 → 「开始游戏」按钮落在可视区外，
 * 表现就是**点了双人/多人没反应**；而且它是同屏多人，**没有联机能力**，
 * 无法接 `postMessage` 或外部状态，「邀请家人一起玩」根本做不到。
 *
 * 现在：15×15 自绘棋盘（轨道/基地/归航通道全部按经典中国飞行棋布局），
 *  - 本地：2/3/4 人同屏（一台设备轮着掷）
 *  - 在线：2 人邀请对战，复用 useGameRoom 房间会话（1.6s 轮询同步）
 *
 * 状态机：所有变化都由**事件**驱动（resolve 只算不落地，applyEvent 才落地），
 * 本地与在线走同一条 applyEvent 路径 → 双方重放同一事件流得到同一局面。
 * 服务端对飞行棋是「客户端权威」（荣誉制，见 backend/routers/game_rooms.py），
 * 事件里带完整结果（np/cap/extra），重放无需重算随机数。
 */
import { ref, computed, onBeforeUnmount, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGameRoom } from '@/composables/useGameRoom'
import MemberPicker from '@/components/games/MemberPicker.vue'
import { familyMembers } from '@/api/lifeExtra'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'
import { sfx } from '@/utils/games/sfx'
import AppIcon from '@/components/common/AppIcon.vue'

const props = defineProps({
  initialMode: { type: String, default: '' },   // 模式由页面第一步选定
  resume: { type: Boolean, default: false },    // 从本地存档续局
  bare: { type: Boolean, default: false },      // 隐藏内置模式段
  joinRoomId: { type: Number, default: 0 },     // 受邀跳转进来：直接进指定房间
})

/* ================= 棋盘几何（经典中国飞行棋 15×15） =================
 * 外圈轨道 52 格；四角 6×6 基地；四条 6 格归航通道汇入中心。
 * 进度模型 prog：-1 = 在基地；0..50 = 轨道；51..56 = 归航通道；57 = 已归航。
 * 各色起点在环上相距 13 格，因此「同色格」= prog % 4 === 0（52 能被 4 整除）。
 */
const N = 15
const COLORS = ['red', 'green', 'yellow', 'blue']
const TRACK = [
  [6, 0], [6, 1], [6, 2], [6, 3], [6, 4], [6, 5],          // 0-5
  [5, 6], [4, 6], [3, 6], [2, 6], [1, 6], [0, 6],          // 6-11
  [0, 7],                                                    // 12
  [0, 8], [1, 8], [2, 8], [3, 8], [4, 8], [5, 8],          // 13-18
  [6, 9], [6, 10], [6, 11], [6, 12], [6, 13], [6, 14],     // 19-24
  [7, 14],                                                   // 25
  [8, 14], [8, 13], [8, 12], [8, 11], [8, 10], [8, 9],     // 26-31
  [9, 8], [10, 8], [11, 8], [12, 8], [13, 8], [14, 8],     // 32-37
  [14, 7],                                                   // 38
  [14, 6], [13, 6], [12, 6], [11, 6], [10, 6], [9, 6],     // 39-44
  [8, 5], [8, 4], [8, 3], [8, 2], [8, 1], [8, 0],          // 45-50
  [7, 0],                                                    // 51
]
const START = { red: 1, green: 14, yellow: 27, blue: 40 }   // 起飞格在环上的索引
const HOME = {
  red: [[7, 1], [7, 2], [7, 3], [7, 4], [7, 5], [7, 6]],
  green: [[1, 7], [2, 7], [3, 7], [4, 7], [5, 7], [6, 7]],
  yellow: [[7, 13], [7, 12], [7, 11], [7, 10], [7, 9], [7, 8]],
  blue: [[13, 7], [12, 7], [11, 7], [10, 7], [9, 7], [8, 7]],
}
const BASE_RC = { red: [0, 0], green: [0, 9], yellow: [9, 9], blue: [9, 0] }
const FIN_RC = { red: [7, 6.4], green: [6.4, 7], yellow: [7, 7.6], blue: [7.6, 7] }
const TRACK_MAX = 50        // 轨道最后一格（第 51 格是归航入口，在环上）
const HOME_START = 51
const FINISH = 57
const SHORTCUT_FROM = 18    // 第 18 格触发飞行通道
const SHORTCUT_STEP = 12

/* 事件格（大乱斗）：按「环上索引」布置，四色共享 —— 谁落上去都触发同一效果。
 * 刻意避开各色起点（1/14/27/40）与飞行通道触发格（6/19/32/45），
 * 免得「刚起飞」或「刚飞跃」时又被叠一层效果、读不清发生了什么。 */
const EVENT_STEP = 3
const EVENT_CELLS = {
  3: 'boost', 17: 'boost', 30: 'boost',      // ⚡ 加速带：前进 3 格
  8: 'trap', 21: 'trap', 36: 'trap',         // 🕳 陷阱：后退 3 格
  11: 'warp', 25: 'warp', 43: 'warp',        // 🌀 虫洞：与最领先的对手换位
  12: 'chest', 24: 'chest', 48: 'chest',     // 🎁 宝箱：额外再掷一次
}
const EVENT_META = {
  boost: { icon: '⚡', name: '加速带', short: '加速', tip: '前进 3 格' },
  trap: { icon: '🕳', name: '陷阱', short: '陷阱', tip: '后退 3 格' },
  warp: { icon: '🌀', name: '虫洞', short: '虫洞', tip: '与领先对手换位' },
  chest: { icon: '🎁', name: '宝箱', short: '宝箱', tip: '再掷一次' },
}

const META = {
  red: { name: '红方', main: '#e5484d', deep: '#a81f26' },
  green: { name: '绿方', main: '#2f9e63', deep: '#186b3f' },
  yellow: { name: '黄方', main: '#e0a020', deep: '#9c6a05' },
  blue: { name: '蓝方', main: '#2f80d8', deep: '#1a5599' },
}
const MODES = [
  { key: 'pvp2', label: '双人同屏', colors: ['red', 'yellow'] },
  { key: 'ai2', label: '人机 · 对机器人', colors: ['red', 'yellow'] },
  { key: 'pvp3', label: '三人同屏', colors: ['red', 'green', 'yellow'] },
  { key: 'pvp4', label: '四人同屏', colors: ['red', 'green', 'yellow', 'blue'] },
  { key: 'online', label: '在线 · 邀请对战', colors: ['red', 'yellow'] },
]
/** 在线双方固定红/黄（服务端 black_user_id 语义 = 先手方，映射到红） */
const ONLINE_COLORS = ['red', 'yellow']

/* ================= 状态 ================= */
function newPieces() {
  const mk = () => [{ prog: -1 }, { prog: -1 }, { prog: -1 }, { prog: -1 }]
  return { red: mk(), green: mk(), yellow: mk(), blue: mk() }
}
const mode = ref(props.initialMode || 'pvp2')
const pieces = ref(newPieces())
const turnColor = ref('red')
const dice = ref(0)
const phase = ref('roll')      // roll=可掷骰 / move=选子 / over=终局
const over = ref(false)
const winnerColor = ref('')
const sixStreak = ref({})
const log = ref([])
const rolling = ref(false)
let rollTimer = null

const activeColors = computed(() => {
  const m = MODES.find(x => x.key === mode.value)
  return m ? m.colors : ONLINE_COLORS
})
const modeLabel = computed(() => MODES.find(x => x.key === mode.value)?.label || '')
const finishedTotal = computed(() =>
  activeColors.value.reduce((s, c) => s + pieces.value[c].filter(p => p.prog === FINISH).length, 0))

/* ================= 在线房间 ================= */
const families = ref([])
const inviteeId = ref(null)
let lastInviteeName = ''
let exited = false

function colorOfUser(uid) {
  const black = gRoom.room.value?.black_user_id
  if (uid == null || black == null) return null
  return Number(uid) === Number(black) ? 'red' : 'yellow'
}
function onRemoteMove(action) {
  applyEvent(action)
}
function onRoomStatus(s) {
  if (s.status === 'finished') {
    over.value = true
    phase.value = 'over'
    const uid = Number(gRoom.myUserId.value)
    if (s.winner_id) winnerColor.value = colorOfUser(s.winner_id) || ''
    const reason = s.end_reason || gRoom.room.value?.end_reason || ''
    if (s.winner_id === uid && (reason === 'leave' || reason === 'timeout')) {
      if (exited) return
      exited = true
      ElMessage.info(reason === 'timeout' ? '对方已掉线，对局自动结束' : '对方已离开，对局结束')
      gRoom.reset()
      resetGame()
      emit('room-unlock')
    }
  }
}
const emit = defineEmits(['room-lock', 'room-unlock', 'exit'])
const gRoom = useGameRoom('ludo', { onRemoteMove, onStatus: onRoomStatus })

const myColor = computed(() => (mode.value === 'online' ? (gRoom.mySeat.value === 'black' ? 'red' : 'yellow') : ''))
const roomActive = computed(() =>
  mode.value === 'online' && !!gRoom.room.value && ['waiting', 'playing'].includes(gRoom.status.value))
const boardLocked = computed(() => mode.value === 'online' && (!roomActive.value || turnColor.value !== myColor.value))
const lockHint = computed(() => {
  if (mode.value !== 'online') return ''
  if (!gRoom.room.value) return '先选一位家人发出邀请，再开始对局'
  const st = gRoom.status.value
  const who = gRoom.opponentName.value || '对方'
  if (st === 'waiting') return `等「${who}」接受邀请…`
  if (st === 'playing') return turnColor.value === myColor.value ? '' : `等「${who}」掷骰…`
  if (st === 'finished') return '本局已结束'
  return ''
})
const onlineResultText = computed(() => {
  if (!winnerColor.value) return '平局'
  return winnerColor.value === myColor.value ? '你赢了' : '对方赢了'
})
const onlineResultIcon = computed(() => {
  if (!winnerColor.value) return '🤝'
  return winnerColor.value === myColor.value ? '🎉' : ''
})
watch(roomActive, (v) => emit(v ? 'room-lock' : 'room-unlock'))

/* ================= 规则核心 ================= */
function ringOf(color, prog) { return (START[color] + prog) % 52 }
function cellOf(color, prog) {
  if (prog < 0) return null
  if (prog <= TRACK_MAX) return TRACK[ringOf(color, prog)]
  if (prog < FINISH) return HOME[color][prog - HOME_START]
  return null
}
/** 机头朝向：按「当前格 → 下一格」的方向算角度（SVG 机头默认朝上，故 +90°）。
 *  纯观感，不参与走子逻辑；基地 / 已归航 / 无下一格时回正。 */
function dirAngle(color, prog) {
  if (prog < 0 || prog >= FINISH) return 0
  const a = cellOf(color, prog)
  const b = cellOf(color, prog + 1)
  if (!a || !b) return 0
  const dy = b[0] - a[0], dx = b[1] - a[1]
  if (!dx && !dy) return 0
  return Math.round(Math.atan2(dy, dx) * 180 / Math.PI + 90)
}
/** 当前可走的棋子下标（掷 1 或 6 才能从基地起飞 —— 放宽起飞门槛，减少卡手） */
function legalMoves(color, v) {
  const out = []
  pieces.value[color].forEach((pc, i) => {
    if (pc.prog === FINISH) return
    if (pc.prog === -1) { if (v === 6 || v === 1) out.push(i); return }
    out.push(i)
  })
  return out
}
const legalIdx = computed(() => (phase.value === 'move' ? legalMoves(turnColor.value, dice.value) : []))

/** 最领先的对手棋子（轨道上 prog 最大者）—— 虫洞换位的目标 */
function leadingOpponent(color) {
  let best = null
  for (const oc of activeColors.value) {
    if (oc === color) continue
    pieces.value[oc].forEach((op, oi) => {
      if (op.prog >= 1 && op.prog <= TRACK_MAX && (!best || op.prog > best.prog)) {
        best = { color: oc, i: oi, prog: op.prog }
      }
    })
  }
  return best
}

/** 把「A 色某进度所在的环位」换算成「B 色落在同一环位的进度」；落在 B 色起点外/归航口则返回 null。
 *  虫洞换位必须走这里 —— prog 是各色独立的进度，直接对调 prog 会落到不同格子。 */
function sameRingProg(fromColor, prog, toColor) {
  const ring = ringOf(fromColor, prog)
  const p = ((ring - START[toColor]) % 52 + 52) % 52
  return (p >= 1 && p <= TRACK_MAX) ? p : null
}

/** 只计算不落地：把一手棋的完整结果算出来（供本地落地 / 在线发给对方重放）。
 *  事件格效果也在这里算好、一并写进 np/wp，重放端无需再算随机数。 */
function resolve(color, i, v) {
  const from = pieces.value[color][i].prog
  let prog = from === -1 ? 0 : from + v
  if (prog > FINISH) prog = FINISH                     // 取消精确归航：超出直接归航
  let fly = ''
  if (prog >= 1 && prog <= TRACK_MAX) {
    if (prog === SHORTCUT_FROM) {
      prog += SHORTCUT_STEP; fly = 'shortcut'
      if (prog > FINISH) prog = FINISH
    } else if (prog % 4 === 0 && prog + 4 <= TRACK_MAX) {
      prog += 4; fly = 'color'
    }
  }
  // 事件格：落在带事件的格子上触发（按环上索引，四色共享）
  let evt = ''
  let wp = null                                        // 虫洞：把被换位的对手挪到哪
  if (prog >= 1 && prog <= TRACK_MAX) {
    const type = EVENT_CELLS[ringOf(color, prog)]
    if (type === 'trap') {
      evt = 'trap'; prog = Math.max(1, prog - EVENT_STEP)
    } else if (type === 'boost') {
      evt = 'boost'; prog = Math.min(FINISH, prog + EVENT_STEP)
    } else if (type === 'chest') {
      evt = 'chest'
    } else if (type === 'warp') {
      const t = leadingOpponent(color)
      const mine = t && sameRingProg(t.color, t.prog, color)   // 我换到对手的环位
      const his = t && sameRingProg(color, prog, t.color)      // 对手换到我的环位
      if (t && mine != null && his != null) { evt = 'warp'; wp = [t.color, t.i, his]; prog = mine }
    }
  }
  const cap = []
  if (prog >= 1 && prog <= TRACK_MAX) {
    const ring = ringOf(color, prog)
    for (const oc of activeColors.value) {
      if (oc === color) continue
      pieces.value[oc].forEach((op, oi) => {
        if (wp && wp[0] === oc && wp[1] === oi) return    // 被虫洞换过来的对手不判击落
        if (op.prog >= 1 && op.prog <= TRACK_MAX && ringOf(oc, op.prog) === ring) cap.push([oc, oi])
      })
    }
  }
  return { t: 'move', c: color, p: i, v, np: prog, cap, fly, evt, wp, extra: v === 6 || cap.length > 0 || evt === 'chest' }
}

/** 唯一落地入口：本地与在线共用（在线由对方重放同一事件） */
function applyEvent(ev) {
  if (!ev || typeof ev !== 'object') return
  if (ev.t === 'skip') {
    const c = ev.c || turnColor.value
    dice.value = ev.v || 0
    sfx.pass()                            // 无子可走（v2.46.20）
    addLog(`${label(c)} 掷出 ${ev.v || 0} 点，无子可走`)
    if (ev.extra) phase.value = 'roll'
    else endTurn(c)
    return
  }
  if (ev.t !== 'move') return
  const arr = pieces.value[ev.c]
  if (!arr || typeof ev.p !== 'number' || !arr[ev.p]) return
  const from = arr[ev.p].prog
  arr[ev.p].prog = ev.np
  /* 逐格跳连音（v2.46.20）：n 连音高递增的轻响比「啪一下到位」更有行进感 */
  sfx.steps(ev.v || 1)
  if (ev.wp) {                                        // 虫洞：把被换位的对手挪到我这手原来的落点
    const [oc, oi, back] = ev.wp
    const op = pieces.value[oc]?.[oi]
    if (op) op.prog = back
  }
  for (const [oc, oi] of (ev.cap || [])) {
    const op = pieces.value[oc]?.[oi]
    if (op) op.prog = -1
  }
  if ((ev.cap || []).length) sfx.capture()     // 击落重音（v2.46.20）
  if (ev.np === FINISH) sfx.coin()             // 归航进账（v2.46.20）
  dice.value = ev.v || dice.value
  let msg = from === -1 ? `${label(ev.c)} 起飞` : `${label(ev.c)} 掷出 ${ev.v} 点`
  if (ev.fly === 'shortcut') msg += ' · 触发飞行通道'
  else if (ev.fly === 'color') msg += ' · 踩到自己颜色，飞跃'
  if (ev.evt && EVENT_META[ev.evt]) {
    const m = EVENT_META[ev.evt]
    msg += ` · ${m.icon} ${m.name}（${m.tip}）`
  }
  if ((ev.cap || []).length) msg += ` · 击落 ${ev.cap.map(([oc]) => label(oc)).join('、')}`
  if (ev.np === FINISH) msg += ' · 一架归航'
  addLog(msg)

  if (arr.every(p => p.prog === FINISH)) {
    over.value = true
    phase.value = 'over'
    winnerColor.value = ev.c
    sfx.win()                                  // 胜利和弦（v2.46.20）
    addLog(`🎊 ${label(ev.c)} 四架全部归航，获胜！`)
    if (mode.value === 'online' && ev.c === myColor.value) {
      gRoom.finish(Number(gRoom.myUserId.value)).catch(() => {})
    }
    return
  }
  if (ev.extra) {
    phase.value = 'roll'
    if (ev.v === 6) addLog(`${label(ev.c)} 掷出 6 点，再掷一次`)
    else if ((ev.cap || []).length) addLog(`${label(ev.c)} 击落对方，再掷一次`)
    else if (ev.evt === 'chest') addLog(`${label(ev.c)} 宝箱奖励，再掷一次`)
    else addLog(`${label(ev.c)} 再掷一次`)
  } else {
    endTurn(ev.c)
  }
}
function endTurn(from) {
  const list = activeColors.value
  const i = list.indexOf(from || turnColor.value)
  turnColor.value = list[(i + 1) % list.length]
  phase.value = 'roll'
  dice.value = 0
}

/* ================= 交互 ================= */
const canRoll = computed(() => {
  if (over.value || phase.value !== 'roll') return false
  if (mode.value === 'online') return roomActive.value && turnColor.value === myColor.value
  if (isAiGame.value && turnColor.value === AI_COLOR) return false   // AI 自动掷
  return true
})
const rollLabel = computed(() => {
  if (over.value) return '本局已结束'
  if (mode.value === 'online' && !roomActive.value) return '等待开局'
  if (mode.value === 'online' && turnColor.value !== myColor.value) return '等对方掷骰'
  if (phase.value === 'move') return '请选择棋子'
  return '掷骰子'
})
function doRoll() {
  if (!canRoll.value) return
  const c = turnColor.value
  const v = 1 + Math.floor(Math.random() * 6)
  sfx.dice()                            // 掷骰音（v2.46.20）
  rolling.value = true
  clearTimeout(rollTimer)
  rollTimer = setTimeout(() => { rolling.value = false }, 320)
  dice.value = v

  if (v === 6) {
    sixStreak.value[c] = (sixStreak.value[c] || 0) + 1
    if (sixStreak.value[c] >= 3) {                 // 连掷三个 6 → 本轮作废
      sixStreak.value[c] = 0
      addLog(`${label(c)} 连掷三个 6，本轮作废`)
      commit({ t: 'skip', c, v, extra: false })
      return
    }
  } else {
    sixStreak.value[c] = 0
  }

  const moves = legalMoves(c, v)
  if (!moves.length) {
    addLog(`${label(c)} 掷出 ${v} 点，无子可走`)
    commit({ t: 'skip', c, v, extra: false })
    return
  }
  phase.value = 'move'
  if (moves.length === 1) {
    // 只有一种走法 → 自动走，少点一次
    rollTimer = setTimeout(() => { if (phase.value === 'move' && turnColor.value === c) doMove(moves[0]) }, 380)
  } else {
    addLog(`${label(c)} 掷出 ${v} 点，请选择棋子`)
  }
}
function doMove(i) {
  const c = turnColor.value
  if (over.value || phase.value !== 'move') return
  if (!legalIdx.value.includes(i)) return
  commit(resolve(c, i, dice.value))
}
/** 落地 + （在线时）上报服务端；事件流一致 → 双方局面一致 */
function commit(ev) {
  applyEvent(ev)
  if (mode.value === 'online') gRoom.send(ev).catch(() => { /* 下轮轮询以服务端事件流为准 */ })
}
function onPieceClick(p) {
  if (!p.movable) return
  doMove(p.i)
}

/** 战报文案开头的 emoji 提成 icon 字段（模板用 AppIcon 渲染），命中不了就原样保留。 */
const LEAD_ICON = /^([\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{1F000}-\u{1FAFF}][\uFE0F\u200D\u{1F3FB}-\u{1F3FF}]*)\s+/u
function splitIcon(msg) {
  const m = LEAD_ICON.exec(msg)
  return m ? { icon: m[1], text: msg.slice(m[0].length) } : { icon: '', text: msg }
}
function addLog(s) {
  log.value.push(splitIcon(s))
  if (log.value.length > 6) log.value.shift()
}
function label(c) { return META[c]?.name || c }
function playerLabel(c) {
  if (mode.value === 'online') {
    if (c === myColor.value) return '你'
    return gRoom.opponentName.value || '对方'
  }
  return label(c)
}
function seatStatus(c) {
  if (over.value) return winnerColor.value === c ? '获胜' : '已结束'
  if (turnColor.value !== c) return '等待'
  if (mode.value === 'online') return turnColor.value === myColor.value ? '你的回合' : '对方回合'
  return phase.value === 'move' ? '选择棋子' : '请掷骰'
}
function seatIcon(c) {
  return over.value && winnerColor.value === c ? '🎉' : ''
}
const resultText = computed(() => {
  if (!winnerColor.value) return '平局'
  return `${label(winnerColor.value)} 获胜`
})
const resultIcon = computed(() => {
  if (!winnerColor.value) return '🤝'
  return '🎊'
})

/* ================= 棋盘渲染 ================= */
const ownTrackSet = computed(() => new Set(activeColors.value.map(c => START[c])))
const flyRing = computed(() => {
  const c = activeColors.value[0]
  return (START[c] + SHORTCUT_FROM) % 52
})
function cellStyle([r, c], bg) {
  const s = { left: `${c / N * 100}%`, top: `${r / N * 100}%`, width: `${100 / N}%`, height: `${100 / N}%` }
  if (bg) s.background = bg
  return s
}
function baseStyle(c) {
  const [r0, c0] = BASE_RC[c]
  return {
    left: `${c0 / N * 100}%`, top: `${r0 / N * 100}%`,
    width: `${6 / N * 100}%`, height: `${6 / N * 100}%`,
    '--pc': META[c].main,
  }
}
function slotStyle(i) {
  const dc = i % 2 === 0 ? 1.7 : 3.7
  const dr = i < 2 ? 1.7 : 3.7
  return { left: `${dc / 6 * 100}%`, top: `${dr / 6 * 100}%` }
}
const centerStyle = {
  left: `${6 / N * 100}%`, top: `${6 / N * 100}%`,
  width: `${3 / N * 100}%`, height: `${3 / N * 100}%`,
}

function baseSlotRC(c, i) {
  const [r0, c0] = BASE_RC[c]
  return [r0 + (i < 2 ? 1.7 : 3.7), c0 + (i % 2 === 0 ? 1.7 : 3.7)]
}
function isMovable(c, i) {
  if (over.value || phase.value !== 'move') return false
  if (c !== turnColor.value) return false
  if (isAiGame.value && c === AI_COLOR) return false               // AI 自动走
  if (mode.value === 'online' && c !== myColor.value) return false
  return legalIdx.value.includes(i)
}

/* ================= AI（v2.46.31 人机模式） ================= */
const AI_COLOR = 'yellow'
const isAiGame = computed(() => mode.value === 'ai2')
let aiTimer = null

/** AI 选子：resolve 干跑算分（不改局面）。优先级：归航 > 击落 > 起飞 > 事件格/飞跃 >
 *  落点安全（身后 6 步内无敌机）> 前进进度。 */
function pickAiMove() {
  const c = turnColor.value
  const v = dice.value
  const moves = legalMoves(c, v)
  if (!moves.length) return null
  let best = moves[0], bestSc = -Infinity
  for (const i of moves) {
    const ev = resolve(c, i, v)
    let sc = ev.np === FINISH ? 1000 : 0
    sc += (ev.cap || []).length * 500
    if (pieces.value[c][i].prog === -1) sc += 120                 // 起飞
    if (ev.fly === 'shortcut' || ev.fly === 'color') sc += 80
    sc += ev.np                                                   // 前进进度
    // 落点风险：任一对手在落点环位身后 1~6 步 → 可能被吃回来
    if (ev.np >= 1 && ev.np <= TRACK_MAX) {
      const ring = ringOf(c, ev.np)
      for (const oc of activeColors.value) {
        if (oc === c) continue
        for (const op of pieces.value[oc]) {
          if (op.prog < 1 || op.prog > TRACK_MAX) continue
          const oring = ringOf(oc, op.prog)
          const d = ((ring - oring) % 52 + 52) % 52
          if (d >= 1 && d <= 6) sc -= (7 - d) * 10
        }
      }
    }
    sc += Math.random() * 8
    if (sc > bestSc) { bestSc = sc; best = i }
  }
  return best
}

watch([turnColor, phase, over, isAiGame], () => {
  clearTimeout(aiTimer)
  if (!isAiGame.value || over.value || turnColor.value !== AI_COLOR) return
  aiTimer = setTimeout(() => {
    if (over.value || turnColor.value !== AI_COLOR) return
    if (phase.value === 'roll') { doRoll(); return }
    if (phase.value === 'move') {
      const pick = pickAiMove()
      if (pick != null) doMove(pick)
    }
  }, 620)
}, { flush: 'post' })
const pieceViews = computed(() => {
  const groups = new Map()
  for (const c of activeColors.value) {
    pieces.value[c].forEach((pc, i) => {
      let key, rc
      if (pc.prog === -1) { key = `b-${c}-${i}`; rc = baseSlotRC(c, i) }
      else if (pc.prog === FINISH) { key = `f-${c}`; rc = FIN_RC[c] }
      else { key = `t-${ringOf(c, pc.prog)}`; rc = cellOf(c, pc.prog) }
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key).push({ c, i, pc, rc })
    })
  }
  const out = []
  for (const [key, list] of groups) {
    const n = list.length
    list.forEach((it, k) => {
      let [r, c] = it.rc
      if (n > 1) {
        const ang = (Math.PI * 2 * k) / n - Math.PI / 2
        const rad = n > 2 ? 0.2 : 0.15
        r += Math.sin(ang) * rad
        c += Math.cos(ang) * rad
      }
      out.push({
        key: `${key}-${it.i}`,
        color: it.c,
        i: it.i,
        rot: dirAngle(it.c, it.pc.prog),
        finished: it.pc.prog === FINISH,
        movable: isMovable(it.c, it.i),
        style: {
          left: `${(c + 0.5) / N * 100}%`,
          top: `${(r + 0.5) / N * 100}%`,
          width: `${(n > 1 ? 0.58 : 0.74) / N * 100}%`,
          '--pc': META[it.c].main,
          '--pcd': META[it.c].deep,
        },
      })
    })
  }
  return out
})
const DICE_PIPS = {
  1: [4], 2: [0, 8], 3: [0, 4, 8], 4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8],
}
const dicePips = computed(() => DICE_PIPS[dice.value] || [])

/* ================= 重置 / 模式 / 存档 ================= */
const SAVE_KEY = 'ludo'
let saveTimer = null
function resetGame() {
  clearTimeout(rollTimer)
  pieces.value = newPieces()
  turnColor.value = activeColors.value[0] || 'red'
  phase.value = 'roll'
  dice.value = 0
  over.value = false
  winnerColor.value = ''
  sixStreak.value = {}
  log.value = []
  exited = false
}
function setMode(k) {
  if (k === mode.value) return
  if (mode.value === 'online' && roomActive.value) { ElMessage.warning('对局进行中 —— 先退出对局再切换模式'); return }
  mode.value = k
  gRoom.reset()
  resetGame()
  clearGame(SAVE_KEY)
  if (k === 'online') loadFamilies()
}
function restart() {
  clearGame(SAVE_KEY)
  resetGame()
}
function saveLocal() {
  if (mode.value === 'online' || over.value || phase.value === 'move') return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveGame(SAVE_KEY, {
      mode: mode.value,
      summary: `${modeLabel.value} · 归航 ${finishedTotal.value}/${activeColors.value.length * 4}`,
      pieces: JSON.parse(JSON.stringify(pieces.value)),
      turnColor: turnColor.value,
      phase: 'roll',
      sixStreak: sixStreak.value,
    })
  }, 400)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !s.pieces || s.mode === 'online' || !s.pieces.red) return false
  mode.value = s.mode || 'pvp2'
  pieces.value = s.pieces
  turnColor.value = s.turnColor || 'red'
  phase.value = 'roll'
  dice.value = 0
  sixStreak.value = s.sixStreak || {}
  over.value = false
  winnerColor.value = ''
  log.value = []
  return true
}
watch([pieces, turnColor, phase], saveLocal, { deep: true })

/* ================= 在线：邀请 / 接回 ================= */
async function loadFamilies() {
  try {
    const res = await familyMembers()
    families.value = (res?.data?.list || []).filter(m => m.user_id && m.user_id !== Number(gRoom.myUserId.value))
  } catch { families.value = [] }
}
async function invite() {
  if (!inviteeId.value) { ElMessage.warning('先选一位家人'); return }
  lastInviteeName = families.value.find(x => x.user_id === inviteeId.value)?.display_name || '对方'
  try {
    resetGame()
    await gRoom.createInvite(inviteeId.value, 'me')   // 'me' = 我执黑 = 我先手（映射红方）
    ElMessage.success(`邀请已发出，等「${lastInviteeName}」接受`)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || e?.msg || '邀请失败')
  }
}
async function cancelInvite() {
  await gRoom.cancel()
  resetGame()
  ElMessage.success('已取消')
}
async function reinviteSame() {
  const uid = inviteeId.value
  gRoom.reset()
  resetGame()
  if (uid) { inviteeId.value = uid; await invite() }
}
function askExit() {
  ElMessageBox.confirm('退出将按认输处理，对方获胜。确定退出？', '退出对局', {
    confirmButtonText: '认输退出', cancelButtonText: '继续玩', type: 'warning',
  }).then(async () => {
    await gRoom.resign()
    gRoom.reset()
    resetGame()
    emit('room-unlock')
    ElMessage.success('已退出对局')
  }).catch(() => {})
}
function exitOnline() { gRoom.reset(); resetGame() }
async function resumeMine() {
  try {
    const res = await (await import('@/api/gameRooms')).gameRoomsApi.mine()
    const active = (res?.data?.list || []).find(x => x.game === 'ludo' && ['waiting', 'playing'].includes(x.status))
    if (!active) return
    mode.value = 'online'
    await gRoom.join(active.id, { autoAccept: active.status === 'playing' })
    ElMessage.success(`已接回与「${gRoom.opponentName.value}」的对局`)
  } catch { /* 无进行中房间，忽略 */ }
}

onMounted(async () => {
  await loadFamilies()
  if (props.joinRoomId) {
    mode.value = 'online'
    try {
      await gRoom.join(props.joinRoomId)
      ElMessage.success(`已进入与「${gRoom.opponentName.value}」的对局`)
      return
    } catch { /* 房间不可用 → 落到常规流程 */ }
  }
  if (props.resume && restoreLocal()) return
  if (mode.value === 'online') await resumeMine()
  nextTick()
})
onBeforeUnmount(() => {
  clearTimeout(rollTimer); clearTimeout(saveTimer); clearTimeout(aiTimer)
  gRoom.leaveOnUnload()
  gRoom.stopPoll()
})
</script>

<style scoped>
.lb-wrap { display: flex; flex-direction: column; align-items: center; gap: 16px; width: 100%; }

/* ===== 玩家条 / 玻璃壳 ===== */
.lb-shell {
  width: 100%; max-width: 640px; border-radius: 22px; padding: 16px 18px;
  background: linear-gradient(150deg, rgba(255,255,255,.9), rgba(255,255,255,.55));
  border: 1px solid var(--dp-line, rgba(0,0,0,.08));
  box-shadow: 0 16px 44px -14px rgba(30,40,80,.28), inset 0 1px 0 rgba(255,255,255,.85);
  backdrop-filter: blur(16px) saturate(1.35);
  display: flex; flex-direction: column; gap: 12px;
}
.lb-players { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.lb-player {
  display: flex; align-items: center; gap: 10px; padding: 9px 15px; border-radius: 16px;
  border: 1.5px solid transparent; min-width: 138px;
  background: color-mix(in srgb, var(--pc, #c7a96b) 9%, rgba(255,255,255,.55));
  transition: transform .26s cubic-bezier(.2,.8,.3,1), box-shadow .26s, border-color .26s, background .26s;
}
.lb-player.active {
  border-color: var(--pc, #c7a96b);
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--pc, #c7a96b) 26%, transparent),
    color-mix(in srgb, var(--pc, #c7a96b) 8%, transparent));
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--pc, #c7a96b) 15%, transparent),
              0 10px 26px -8px color-mix(in srgb, var(--pc, #c7a96b) 65%, transparent);
  transform: translateY(-1px);
}
.lb-chip {
  width: 20px; height: 20px; border-radius: 50%; flex: none;
  background: radial-gradient(circle at 32% 26%, color-mix(in srgb, var(--pc, #c7a96b) 42%, #fff), var(--pc, #c7a96b));
  box-shadow: 0 2px 7px color-mix(in srgb, var(--pc, #c7a96b) 55%, transparent), inset 0 1px 0 rgba(255,255,255,.6);
}
.lb-ptxt { min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.lb-ptxt b { font-size: 13.5px; font-weight: 700; color: var(--dp-text, #18202a); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 92px; }
.lb-ptxt i { font-style: normal; font-size: 10.5px; color: var(--dp-text3, #8a8f98); }
.lb-mini { display: flex; gap: 4px; margin-left: auto; }
.lb-mini em { width: 8px; height: 8px; border-radius: 50%; background: rgba(0,0,0,.13); transition: all .25s; }
.lb-mini em.done { background: var(--pc, #c7a96b); box-shadow: 0 0 0 2px color-mix(in srgb, var(--pc, #c7a96b) 28%, transparent); }

.lb-modes { display: flex; gap: 7px; flex-wrap: wrap; justify-content: center; }
.lb-mode {
  padding: 7px 16px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: rgba(255,255,255,.5); color: var(--dp-text2, #45505b); cursor: pointer; font-size: 12.5px; font-family: inherit;
  transition: transform .18s, box-shadow .18s, background .18s, color .18s;
}
.lb-mode:hover { transform: translateY(-1px); }
.lb-mode.on {
  background: linear-gradient(135deg, #ffd977, #f0a93c); border-color: transparent; color: #4a2c05; font-weight: 700;
  box-shadow: 0 6px 16px -4px rgba(224,140,40,.6);
}
.lb-mode:disabled { opacity: .38; cursor: not-allowed; }

.lb-banner { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center;
  padding: 9px 14px; border-radius: 12px; font-size: 12.5px; }
.lb-banner.st-waiting { background: rgba(199,169,107,.12); color: var(--dp-text2, #45505b); }
.lb-banner.st-playing { background: rgba(127,168,163,.12); color: var(--dp-text2, #45505b); }
.lb-banner.st-finished { background: rgba(199,169,107,.18); color: var(--dp-text, #18202a); }
.lb-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--yq-gold, #c7a96b); animation: lbpulse 1.2s infinite; }
@keyframes lbpulse { 50% { opacity: .3 } }
.lb-result { font-weight: 700; color: var(--yq-gold, #c7a96b); }
.lb-status { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--dp-text2, #45505b); flex-wrap: wrap; justify-content: center; }
.lb-quota { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.lb-btn { padding: 5px 14px; border-radius: 9px; font-size: 12px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); }
.lb-btn:not(:disabled):hover { transform: scale(1.05); }
.lb-btn:not(:disabled):active { transform: scale(.94); }
.lb-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.lb-btn:disabled { opacity: .5; cursor: default; }
.lb-roll:not(:disabled):active { transform: scale(.95); }

.lb-online {
  width: 100%; max-width: 620px; border-radius: 18px; padding: 16px 18px;
  background: linear-gradient(160deg, rgba(255,255,255,.78), rgba(255,255,255,.48));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1)); box-shadow: 0 8px 28px rgba(20,30,40,.08);
}
.lb-online-title { font-size: 15px; font-weight: 700; color: var(--dp-text, #18202a); }
.lb-online-desc { margin: 6px 0 10px; font-size: 12px; color: var(--dp-text3, #8a8f98); line-height: 1.7; }
.lb-online-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
/* 邀请按钮与选择器并排：让选择器占满剩余宽度（默认是 width:100% 会独占一行） */
.lb-online-row :deep(.mp-wrap) { width: auto; flex: 1 1 160px; min-width: 0; }

.lb-locknote {
  display: inline-flex; align-items: center; gap: 8px; margin: 0;
  font-size: 12.5px; font-weight: 600; color: var(--dp-text2, #45505b);
  background: rgba(199,169,107,.14); padding: 7px 16px; border-radius: 999px;
}
.lb-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--yq-gold, #c7a96b); animation: lbpulse 1.2s infinite; }

/* ===== 棋盘 ===== */
.lb-boardwrap { display: inline-block; }
.lb-board {
  position: relative; width: min(92vw, 640px); aspect-ratio: 1 / 1;
  border-radius: 24px; container-type: size;
  background:
    radial-gradient(88% 68% at 10% 4%, rgba(96, 224, 196, .38), rgba(96, 224, 196, 0) 60%),
    radial-gradient(84% 64% at 94% 14%, rgba(255, 158, 200, .36), rgba(255, 158, 200, 0) 62%),
    radial-gradient(96% 74% at 76% 98%, rgba(142, 174, 255, .38), rgba(142, 174, 255, 0) 60%),
    radial-gradient(120% 90% at 50% -12%, rgba(255, 255, 255, .95), rgba(255, 255, 255, 0) 62%),
    linear-gradient(135deg, #f2f7ff 0%, #ece9ff 46%, #fff0f6 100%);
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.9),
    0 0 0 6px rgba(255,255,255,.4),
    0 30px 70px -26px rgba(96, 92, 210, .42),
    0 26px 56px -20px rgba(40,50,95,.42);
  touch-action: manipulation; user-select: none; transition: filter .2s;
  --lb-line: rgba(96,116,158,.2);
  --lb-empty: rgba(255,255,255,.68);
}
.lb-board.locked { filter: saturate(.7) brightness(.96); }
.lb-board.locked .lb-piece { cursor: default; }

/* 基地 */
.lb-base {
  position: absolute; border-radius: 16px;
  background: radial-gradient(circle at 30% 24%, color-mix(in srgb, var(--pc) 34%, #fff), color-mix(in srgb, var(--pc) 16%, #fff));
  border: 2px solid color-mix(in srgb, var(--pc) 62%, #fff);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.75), 0 8px 20px -8px color-mix(in srgb, var(--pc) 60%, transparent);
}
.lb-base.dim { opacity: .3; }
.lb-slot {
  position: absolute; width: 15%; aspect-ratio: 1/1; border-radius: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255,255,255,.72); box-shadow: inset 0 0 0 1px rgba(0,0,0,.09), 0 1px 2px rgba(0,0,0,.06);
}

/* 中心归航区 */
.lb-center {
  position: absolute; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  background:
    conic-gradient(from 45deg,
      #f2757a 0 25%, #4fbe86 25% 50%, #f2be4a 50% 75%, #4f9de6 75% 100%);
  box-shadow: inset 0 0 0 2.5px rgba(255,255,255,.85), 0 6px 18px -4px rgba(30,40,80,.4);
}
.lb-center-star { font-size: 15px; color: #fff; text-shadow: 0 1px 4px rgba(0,0,0,.35); }

/* 轨道格 / 归航通道格 */
.lb-cell {
  position: absolute; box-sizing: border-box;
  background: var(--lb-empty); border: 1px solid var(--lb-line); border-radius: 6px;
}
.lb-cell.own { background: linear-gradient(135deg, rgba(255,214,110,.72), rgba(255,186,72,.56)); border-color: rgba(224,150,40,.4); }
/* 事件格：四色共享的特殊格，用颜色 + 图标 + 短名一起区分类型（只看图看不懂） */
.lb-cell.evt {
  display: flex; flex-direction: column; align-items: center; justify-content: center; line-height: 1;
  background: color-mix(in srgb, var(--evt, #888) 34%, #fff);
  border-color: color-mix(in srgb, var(--evt, #888) 55%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--evt, #888) 40%, transparent);
}
.lb-cell.evt-boost { --evt: #22b573; }
.lb-cell.evt-trap  { --evt: #f0564f; }
.lb-cell.evt-warp  { --evt: #8a5cf0; }
.lb-cell.evt-chest { --evt: #f0a91c; }
.lb-evt-ico { font-size: clamp(9px, 2.8cqw, 18px); line-height: 1; }
.lb-evt-tag {
  margin-top: 1px; font-size: clamp(6.5px, 2.05cqw, 11px); font-weight: 800; letter-spacing: -.2px;
  color: color-mix(in srgb, var(--evt, #666) 82%, #1b2233);
}
.lb-cell.fly::after {
  content: '✈'; position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: clamp(8px, 2.2cqw, 14px); color: rgba(70,95,140,.7);
}
.lb-cell.home { border-color: rgba(255,255,255,.8); box-shadow: inset 0 0 0 1px rgba(0,0,0,.1); }
.lb-cell.home.dim { opacity: .3; }

/* 棋子：圆润机身 + 白色飞机 */
.lb-piece {
  position: absolute; transform: translate(-50%, -50%); aspect-ratio: 1/1; padding: 0;
  border-radius: 50%; border: 2px solid rgba(255,255,255,.95); cursor: pointer;
  background: radial-gradient(circle at 32% 26%, color-mix(in srgb, var(--pc) 46%, #fff), var(--pcd));
  box-shadow: 0 3px 9px rgba(10,20,45,.42), inset 0 -2px 6px rgba(0,0,0,.24), inset 0 2px 5px rgba(255,255,255,.45);
  display: flex; align-items: center; justify-content: center;
  transition: left .26s ease, top .26s ease, width .2s ease, transform .2s ease; z-index: 3;
}
.lb-plane {
  width: 78%; height: 78%; fill: rgba(255,255,255,.97);
  filter: drop-shadow(0 1px 1px rgba(0,0,0,.42));
  transition: transform .3s ease;
}
.lb-piece.movable {
  z-index: 6; animation: lbfloat 1.1s ease-in-out infinite;
  box-shadow: 0 0 0 3px rgba(255,255,255,.92), 0 0 18px 6px color-mix(in srgb, var(--pc) 72%, transparent), 0 3px 9px rgba(10,20,45,.42);
}
.lb-piece.movable:hover { transform: translate(-50%, -50%) scale(1.16); }
.lb-piece.finished { border-color: #ffd977; box-shadow: 0 0 0 2px rgba(255,217,119,.95), 0 0 14px 4px rgba(255,200,60,.6), 0 2px 8px rgba(0,0,0,.3); }
@keyframes lbfloat { 50% { transform: translate(-50%, -50%) scale(1.09) } }

/* ===== 控制区 ===== */
.lb-ctrl {
  width: 100%; max-width: 640px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
  padding: 14px 18px; border-radius: 20px;
  background: linear-gradient(150deg, rgba(255,255,255,.82), rgba(255,255,255,.5));
  border: 1px solid var(--dp-line, rgba(0,0,0,.08));
  box-shadow: 0 12px 32px -12px rgba(30,40,80,.3);
  backdrop-filter: blur(14px) saturate(1.3);
}
.lb-dicebox { display: flex; align-items: center; gap: 12px; }
.lb-dice {
  width: 54px; height: 54px; flex: none; border-radius: 15px; padding: 8px; box-sizing: border-box;
  display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 2.5px;
  background: linear-gradient(155deg, #ffffff, #eef0f7);
  border: 1px solid rgba(90,110,150,.22);
  box-shadow: 0 6px 16px -4px rgba(30,40,80,.35), inset 0 1px 0 #fff;
}
.lb-dice.rolling { animation: lbroll .32s ease; }
@keyframes lbroll { 50% { transform: rotate(180deg) scale(.86) } }
.lb-dice i { border-radius: 50%; }
.lb-dice i.on { background: radial-gradient(circle at 35% 30%, #6b5cff, #2b1fa8); }
.lb-roll {
  padding: 12px 26px; border-radius: 15px; font-size: 15px; font-weight: 800; letter-spacing: .4px;
  cursor: pointer; font-family: inherit; border: none; color: #4a2c05;
  background: linear-gradient(135deg, #ffdd85, #f2ad3f 55%, #e5841f);
  box-shadow: 0 8px 22px -6px rgba(224,140,40,.75), inset 0 1px 0 rgba(255,255,255,.65);
  transition: transform .16s, box-shadow .16s, filter .16s;
}
.lb-roll:not(:disabled):hover { transform: translateY(-2px); filter: brightness(1.05); }
.lb-roll:disabled { opacity: .45; cursor: default; box-shadow: none; }
.lb-log { list-style: none; margin: 0; padding: 0; flex: 1; min-width: 190px; display: flex; flex-direction: column; gap: 3px; }
.lb-log li { font-size: 11.5px; line-height: 1.55; color: var(--dp-text3, #8a8f98); }
.lb-log li.fresh { color: var(--dp-text, #18202a); font-weight: 700; }

.lb-hint { max-width: 640px; font-size: 11.5px; line-height: 1.8; color: var(--dp-text3, #8a8f98); text-align: center; margin: 0; }

/* 事件格图例 */
.lb-legend { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center; max-width: 640px; font-size: 11.5px; }
.lb-lg-title { font-weight: 700; color: var(--dp-text3, #8a8f98); }
.lb-lg {
  display: inline-flex; align-items: center; gap: 5px; padding: 5px 13px; border-radius: 999px;
  font-weight: 600; color: var(--dp-text2, #45505b);
  background: color-mix(in srgb, var(--evt, #888) 18%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--evt, #888) 34%, transparent);
}
.lb-lg i { font-style: normal; font-size: 13px; }
.lb-lg.lg-boost { --evt: #22b573; }
.lb-lg.lg-trap  { --evt: #f0564f; }
.lb-lg.lg-warp  { --evt: #8a5cf0; }
.lb-lg.lg-chest { --evt: #f0a91c; }

@media (max-width: 520px) {
  .lb-shell { padding: 12px 13px; border-radius: 18px; }
  .lb-player { min-width: 108px; padding: 7px 10px; }
  .lb-ptxt b { max-width: 68px; font-size: 12px; }
  .lb-board { width: min(96vw, 640px); border-radius: 20px; }
  .lb-ctrl { padding: 11px 13px; gap: 11px; border-radius: 16px; }
  .lb-log { min-width: 140px; }
  .lb-dice { width: 46px; height: 46px; border-radius: 13px; padding: 6px; }
  .lb-roll { padding: 10px 18px; font-size: 13.5px; }
}

/* ===== 夜间主题：深空靛蓝玻璃 + 夜光棋盘（此前白壳压黑底发灰看不清） ===== */
:root[data-theme="night"] .lb-shell,
:root[data-theme="night"] .lb-online,
:root[data-theme="night"] .lb-ctrl {
  background: linear-gradient(150deg, rgba(38,44,72,.92), rgba(20,24,42,.94));
  border-color: rgba(140,150,220,.24);
  box-shadow: 0 16px 44px -14px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.08);
}
:root[data-theme="night"] .lb-player { background: color-mix(in srgb, var(--pc, #c7a96b) 16%, rgba(255,255,255,.04)); }
:root[data-theme="night"] .lb-ptxt b { color: #f2f0fa; }
:root[data-theme="night"] .lb-ptxt i { color: #a9a6c8; }
:root[data-theme="night"] .lb-mini em { background: rgba(255,255,255,.16); }
:root[data-theme="night"] .lb-online-title { color: #f2f0fa; }
:root[data-theme="night"] .lb-online-desc,
:root[data-theme="night"] .lb-quota,
:root[data-theme="night"] .lb-log li { color: #a9a6c8; }
:root[data-theme="night"] .lb-log li.fresh { color: #f6f4ff; }
:root[data-theme="night"] .lb-status { color: #d8d5ee; }
:root[data-theme="night"] .lb-hint { color: #9d99bb; }
:root[data-theme="night"] .lb-btn { background: rgba(255,255,255,.09); border-color: rgba(255,255,255,.2); color: #ece9f8; }
:root[data-theme="night"] .lb-btn.primary { background: #c7a96b; border-color: #c7a96b; color: #1a1509; }
:root[data-theme="night"] .lb-mode { color: #d8d5ee; border-color: rgba(255,255,255,.18); background: rgba(255,255,255,.05); }
:root[data-theme="night"] .lb-mode.on { background: linear-gradient(135deg, #ffd977, #f0a93c); border-color: transparent; color: #2a1a03; }

:root[data-theme="night"] .lb-banner.st-waiting { background: rgba(199,169,107,.2); color: #d8d5ee; }
:root[data-theme="night"] .lb-banner.st-playing { background: rgba(127,168,163,.22); color: #d8d5ee; }
:root[data-theme="night"] .lb-banner.st-finished { background: rgba(199,169,107,.26); color: #f6f4ff; }
:root[data-theme="night"] .lb-locknote { background: rgba(199,169,107,.22); color: #d8d5ee; }
:root[data-theme="night"] .lb-board {
  background:
    radial-gradient(120% 90% at 50% -12%, rgba(140,150,220,.28), rgba(140,150,220,0) 60%),
    linear-gradient(135deg, #232a52 0%, #1b1f3e 45%, #241a3a 100%);
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.14),
    0 0 0 6px rgba(255,255,255,.06),
    0 26px 56px -20px rgba(0,0,0,.8);
  --lb-line: rgba(150,165,220,.3);
  --lb-empty: rgba(255,255,255,.1);
}
:root[data-theme="night"] .lb-cell.fly::after { color: rgba(190,205,255,.8); }
:root[data-theme="night"] .lb-cell.evt {
  background: color-mix(in srgb, var(--evt, #888) 46%, #171b30);
  border-color: color-mix(in srgb, var(--evt, #888) 62%, transparent);
}
:root[data-theme="night"] .lb-evt-tag { color: #eef0ff; }
:root[data-theme="night"] .lb-legend,
:root[data-theme="night"] .lb-lg-title { color: #a9a6c8; }
:root[data-theme="night"] .lb-lg { color: #d8d5ee; background: color-mix(in srgb, var(--evt, #888) 30%, transparent); }
:root[data-theme="night"] .lb-cell.own { background: linear-gradient(135deg, rgba(255,214,110,.5), rgba(255,186,72,.36)); border-color: rgba(224,150,40,.35); }
:root[data-theme="night"] .lb-base {
  background: radial-gradient(circle at 30% 24%, color-mix(in srgb, var(--pc) 40%, #1b1f38), color-mix(in srgb, var(--pc) 22%, #1b1f38));
  border-color: color-mix(in srgb, var(--pc) 68%, #fff);
}
:root[data-theme="night"] .lb-slot { background: rgba(0,0,0,.34); box-shadow: inset 0 0 0 1px rgba(255,255,255,.16); }
:root[data-theme="night"] .lb-dice { background: linear-gradient(155deg, #eef0f7, #c9cede); border-color: rgba(0,0,0,.3); }
</style>
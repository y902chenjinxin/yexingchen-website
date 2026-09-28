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
          <span class="lb-chip" :style="{ background: META[c].main }"></span>
          <div class="lb-ptxt">
            <b>{{ playerLabel(c) }}</b>
            <i>{{ seatStatus(c) }}</i>
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
          <span class="lb-result">{{ onlineResultText }}</span>
          <button class="lb-btn primary" @click="reinviteSame">再来一局</button>
          <button class="lb-btn" @click="exitOnline">退出</button>
        </template>
      </div>

      <!-- 本地对局操作 -->
      <div v-if="mode !== 'online'" class="lb-status">
        <span v-if="over" class="lb-result">{{ resultText }}</span>
        <button class="lb-btn" @click="restart">重开一局</button>
        <span class="lb-quota">归航 {{ finishedTotal }}/{{ activeColors.length * 4 }}</span>
      </div>
    </div>

    <!-- 在线：邀请面板 -->
    <div v-if="mode === 'online' && !gRoom.room.value" class="lb-online">
      <div class="lb-online-title">🎯 在线邀请对战</div>
      <p class="lb-online-desc">选一位家人发出邀请，对方接受后开局；你执红先手，掷骰与走子约 2 秒内同步。</p>
      <div class="lb-online-row">
        <select v-model="inviteeId" class="lb-select">
          <option v-for="f in families" :key="f.user_id" :value="f.user_id">{{ f.avatar }} {{ f.display_name }}</option>
        </select>
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
          <span class="lb-center-star">✦</span>
        </div>

        <!-- 外圈轨道 -->
        <div
          v-for="(rc, i) in TRACK"
          :key="'t' + i"
          class="lb-cell"
          :class="{ 'own': ownTrackSet.has(i), 'fly': i === flyRing }"
          :style="cellStyle(rc)"
        ></div>

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
        ><span>{{ p.i + 1 }}</span></button>
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
        <li v-for="(l, i) in log" :key="i" :class="{ fresh: i === log.length - 1 }">{{ l }}</li>
      </ul>
    </div>

    <p class="lb-hint">
      掷 6 才能起飞 · 掷 6 或击落对方可再掷一次 · 踩到自己颜色前进 4 格 · 第 18 格触发飞行通道直飞 12 格 ·
      需正好点数归航（超出弹回）· 四架全部归航者获胜
    </p>
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
import { familyMembers } from '@/api/lifeExtra'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'

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

const META = {
  red: { name: '红方', main: '#e5484d', deep: '#a81f26' },
  green: { name: '绿方', main: '#2f9e63', deep: '#186b3f' },
  yellow: { name: '黄方', main: '#e0a020', deep: '#9c6a05' },
  blue: { name: '蓝方', main: '#2f80d8', deep: '#1a5599' },
}
const MODES = [
  { key: 'pvp2', label: '双人同屏', colors: ['red', 'yellow'] },
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
  if (!winnerColor.value) return '🤝 平局'
  return winnerColor.value === myColor.value ? '🎉 你赢了' : '对方赢了'
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
/** 当前可走的棋子下标（掷 6 才能从基地起飞） */
function legalMoves(color, v) {
  const out = []
  pieces.value[color].forEach((pc, i) => {
    if (pc.prog === FINISH) return
    if (pc.prog === -1) { if (v === 6) out.push(i); return }
    out.push(i)
  })
  return out
}
const legalIdx = computed(() => (phase.value === 'move' ? legalMoves(turnColor.value, dice.value) : []))

/** 只计算不落地：把一手棋的完整结果算出来（供本地落地 / 在线发给对方重放） */
function resolve(color, i, v) {
  const from = pieces.value[color][i].prog
  let prog = from === -1 ? 0 : from + v
  if (prog > FINISH) prog = 2 * FINISH - prog          // 超出终点 → 弹回
  let fly = ''
  if (prog >= 1 && prog <= TRACK_MAX) {
    if (prog === SHORTCUT_FROM) {
      prog += SHORTCUT_STEP; fly = 'shortcut'
      if (prog > FINISH) prog = 2 * FINISH - prog
    } else if (prog % 4 === 0 && prog + 4 <= TRACK_MAX) {
      prog += 4; fly = 'color'
    }
  }
  const cap = []
  if (prog >= 1 && prog <= TRACK_MAX) {
    const ring = ringOf(color, prog)
    for (const oc of activeColors.value) {
      if (oc === color) continue
      pieces.value[oc].forEach((op, oi) => {
        if (op.prog >= 1 && op.prog <= TRACK_MAX && ringOf(oc, op.prog) === ring) cap.push([oc, oi])
      })
    }
  }
  return { t: 'move', c: color, p: i, v, np: prog, cap, fly, extra: v === 6 || cap.length > 0 }
}

/** 唯一落地入口：本地与在线共用（在线由对方重放同一事件） */
function applyEvent(ev) {
  if (!ev || typeof ev !== 'object') return
  if (ev.t === 'skip') {
    const c = ev.c || turnColor.value
    dice.value = ev.v || 0
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
  for (const [oc, oi] of (ev.cap || [])) {
    const op = pieces.value[oc]?.[oi]
    if (op) op.prog = -1
  }
  dice.value = ev.v || dice.value
  let msg = from === -1 ? `${label(ev.c)} 起飞` : `${label(ev.c)} 掷出 ${ev.v} 点`
  if (ev.fly === 'shortcut') msg += ' · 触发飞行通道 ✈️'
  else if (ev.fly === 'color') msg += ' · 踩到自己颜色，飞跃 ✈️'
  if ((ev.cap || []).length) msg += ` · 击落 ${ev.cap.map(([oc]) => label(oc)).join('、')}`
  if (ev.np === FINISH) msg += ' · 一架归航 🎉'
  addLog(msg)

  if (arr.every(p => p.prog === FINISH)) {
    over.value = true
    phase.value = 'over'
    winnerColor.value = ev.c
    addLog(`🎊 ${label(ev.c)} 四架全部归航，获胜！`)
    if (mode.value === 'online' && ev.c === myColor.value) {
      gRoom.finish(Number(gRoom.myUserId.value)).catch(() => {})
    }
    return
  }
  if (ev.extra) {
    phase.value = 'roll'
    addLog(ev.v === 6 ? `${label(ev.c)} 掷出 6 点，再掷一次` : `${label(ev.c)} 击落对方，再掷一次`)
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

function addLog(s) {
  log.value.push(s)
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
  if (over.value) return winnerColor.value === c ? '获胜 🎉' : '已结束'
  if (turnColor.value !== c) return '等待'
  if (mode.value === 'online') return turnColor.value === myColor.value ? '你的回合' : '对方回合'
  return phase.value === 'move' ? '选择棋子' : '请掷骰'
}
const resultText = computed(() => {
  if (!winnerColor.value) return '🤝 平局'
  return `🎊 ${label(winnerColor.value)} 获胜`
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
  if (mode.value === 'online' && c !== myColor.value) return false
  return legalIdx.value.includes(i)
}
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
  clearTimeout(rollTimer); clearTimeout(saveTimer)
  gRoom.leaveOnUnload()
  gRoom.stopPoll()
})
</script>

<style scoped>
.lb-wrap { display: flex; flex-direction: column; align-items: center; gap: 14px; width: 100%; }

/* ===== 玩家条 / 玻璃壳 ===== */
.lb-shell {
  width: 100%; max-width: 620px; border-radius: 18px; padding: 14px 16px;
  background: linear-gradient(160deg, rgba(255,255,255,.78), rgba(255,255,255,.48));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  box-shadow: 0 8px 28px rgba(20,30,40,.08), inset 0 1px 0 rgba(255,255,255,.6);
  display: flex; flex-direction: column; gap: 11px;
}
.lb-players { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.lb-player {
  display: flex; align-items: center; gap: 9px; padding: 7px 12px; border-radius: 13px;
  border: 1px solid transparent; transition: all .25s; min-width: 128px;
}
.lb-player.active {
  border-color: var(--pc, #c7a96b); background: color-mix(in srgb, var(--pc, #c7a96b) 14%, transparent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--pc, #c7a96b) 16%, transparent);
}
.lb-chip { width: 16px; height: 16px; border-radius: 50%; flex: none; box-shadow: 0 2px 5px rgba(0,0,0,.28); }
.lb-ptxt { min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.lb-ptxt b { font-size: 13px; color: var(--dp-text, #18202a); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 92px; }
.lb-ptxt i { font-style: normal; font-size: 10.5px; color: var(--dp-text3, #8a8f98); }
.lb-mini { display: flex; gap: 3px; margin-left: auto; }
.lb-mini em { width: 7px; height: 7px; border-radius: 50%; background: rgba(0,0,0,.14); }
.lb-mini em.done { background: var(--pc, #c7a96b); box-shadow: 0 0 0 2px color-mix(in srgb, var(--pc, #c7a96b) 25%, transparent); }

.lb-modes { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.lb-mode {
  padding: 6px 14px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 12.5px; font-family: inherit; transition: all .2s;
}
.lb-mode.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
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
.lb-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.lb-btn:disabled { opacity: .5; cursor: default; }

.lb-online {
  width: 100%; max-width: 620px; border-radius: 18px; padding: 16px 18px;
  background: linear-gradient(160deg, rgba(255,255,255,.78), rgba(255,255,255,.48));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1)); box-shadow: 0 8px 28px rgba(20,30,40,.08);
}
.lb-online-title { font-size: 15px; font-weight: 700; color: var(--dp-text, #18202a); }
.lb-online-desc { margin: 6px 0 10px; font-size: 12px; color: var(--dp-text3, #8a8f98); line-height: 1.7; }
.lb-online-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.lb-select { flex: 1; min-width: 160px; border: 1px solid var(--dp-line, rgba(0,0,0,.14)); border-radius: 10px;
  padding: 9px 11px; font-size: 13.5px; background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-family: inherit; }

.lb-locknote {
  display: inline-flex; align-items: center; gap: 8px; margin: 0;
  font-size: 12.5px; font-weight: 600; color: var(--dp-text2, #45505b);
  background: rgba(199,169,107,.14); padding: 7px 16px; border-radius: 999px;
}
.lb-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--yq-gold, #c7a96b); animation: lbpulse 1.2s infinite; }

/* ===== 棋盘 ===== */
.lb-boardwrap { display: inline-block; }
.lb-board {
  position: relative; width: min(92vw, 620px); aspect-ratio: 1 / 1;
  border-radius: 16px; background: linear-gradient(135deg, #efe6d2, #ddcfae);
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.16), 0 12px 34px rgba(20,30,40,.14);
  touch-action: manipulation; user-select: none; transition: filter .2s;
  --lb-line: rgba(60,45,20,.28);
  --lb-empty: rgba(255,255,255,.5);
}
.lb-board.locked { filter: saturate(.72) brightness(.95); }
.lb-board.locked .lb-piece { cursor: default; }

/* 基地 */
.lb-base {
  position: absolute; border-radius: 12px;
  background: color-mix(in srgb, var(--pc) 26%, #fff);
  border: 2px solid color-mix(in srgb, var(--pc) 60%, #fff);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.5);
}
.lb-base.dim { opacity: .35; }
.lb-slot {
  position: absolute; width: 15%; aspect-ratio: 1/1; border-radius: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255,255,255,.55); box-shadow: inset 0 0 0 1px rgba(0,0,0,.1);
}

/* 中心归航区 */
.lb-center {
  position: absolute; border-radius: 10px; display: flex; align-items: center; justify-content: center;
  background:
    conic-gradient(from 45deg,
      color-mix(in srgb, #e5484d 55%, #fff) 0 25%,
      color-mix(in srgb, #2f9e63 55%, #fff) 25% 50%,
      color-mix(in srgb, #e0a020 55%, #fff) 50% 75%,
      color-mix(in srgb, #2f80d8 55%, #fff) 75% 100%);
  box-shadow: inset 0 0 0 2px rgba(255,255,255,.7), 0 3px 10px rgba(0,0,0,.12);
}
.lb-center-star { font-size: 13px; color: rgba(255,255,255,.95); text-shadow: 0 1px 3px rgba(0,0,0,.35); }

/* 轨道格 / 归航通道格 */
.lb-cell {
  position: absolute; box-sizing: border-box;
  background: var(--lb-empty); border: 1px solid var(--lb-line); border-radius: 3px;
}
.lb-cell.own { background: rgba(199,169,107,.4); }
.lb-cell.fly::after {
  content: '✈'; position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 9px; color: rgba(60,45,20,.6);
}
.lb-cell.home { border-color: rgba(255,255,255,.65); box-shadow: inset 0 0 0 1px rgba(0,0,0,.14); }
.lb-cell.home.dim { opacity: .3; }

/* 棋子 */
.lb-piece {
  position: absolute; transform: translate(-50%, -50%); aspect-ratio: 1/1; padding: 0;
  border-radius: 50%; border: 2px solid rgba(255,255,255,.9); cursor: pointer;
  background: radial-gradient(circle at 34% 28%, color-mix(in srgb, var(--pc) 55%, #fff), var(--pcd));
  box-shadow: 0 2px 6px rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center;
  transition: left .26s ease, top .26s ease, width .2s ease, transform .2s ease; z-index: 3;
}
.lb-piece span { font-size: 9px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.5); }
.lb-piece.movable { z-index: 5; animation: lbfloat 1.1s ease-in-out infinite; box-shadow: 0 0 0 3px rgba(255,255,255,.85), 0 0 12px 3px color-mix(in srgb, var(--pc) 70%, transparent); }
.lb-piece.movable:hover { transform: translate(-50%, -50%) scale(1.14); }
.lb-piece.finished { border-color: #f6d76b; box-shadow: 0 0 0 2px rgba(246,215,107,.9), 0 2px 8px rgba(0,0,0,.3); }
@keyframes lbfloat { 50% { transform: translate(-50%, -50%) scale(1.09) } }

/* ===== 控制区 ===== */
.lb-ctrl {
  width: 100%; max-width: 620px; display: flex; gap: 14px; align-items: center; flex-wrap: wrap;
  padding: 12px 16px; border-radius: 16px;
  background: linear-gradient(160deg, rgba(255,255,255,.7), rgba(255,255,255,.42));
  border: 1px solid var(--dp-line, rgba(0,0,0,.1)); box-shadow: 0 6px 20px rgba(20,30,40,.07);
}
.lb-dicebox { display: flex; align-items: center; gap: 12px; }
.lb-dice {
  width: 46px; height: 46px; flex: none; border-radius: 11px; padding: 6px; box-sizing: border-box;
  display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 2px;
  background: linear-gradient(160deg, #fff, #e9e3d4); border: 1px solid rgba(0,0,0,.16);
  box-shadow: 0 3px 9px rgba(20,30,40,.18), inset 0 1px 0 #fff;
}
.lb-dice.rolling { animation: lbroll .32s ease; }
@keyframes lbroll { 50% { transform: rotate(180deg) scale(.86) } }
.lb-dice i { border-radius: 50%; }
.lb-dice i.on { background: radial-gradient(circle at 35% 30%, #4a4a4a, #111); }
.lb-roll {
  padding: 10px 20px; border-radius: 12px; font-size: 13.5px; font-weight: 600; cursor: pointer; font-family: inherit;
  border: 1px solid var(--yq-gold, #c7a96b); background: var(--yq-gold, #c7a96b); color: #fff;
  box-shadow: 0 4px 12px rgba(199,169,107,.35); transition: all .18s;
}
.lb-roll:disabled { opacity: .45; cursor: default; box-shadow: none; }
.lb-roll:not(:disabled):hover { filter: brightness(1.06); }
.lb-log { list-style: none; margin: 0; padding: 0; flex: 1; min-width: 180px; display: flex; flex-direction: column; gap: 2px; }
.lb-log li { font-size: 11.5px; line-height: 1.55; color: var(--dp-text3, #8a8f98); }
.lb-log li.fresh { color: var(--dp-text, #18202a); font-weight: 600; }

.lb-hint { max-width: 620px; font-size: 11px; line-height: 1.75; color: var(--dp-text3, #8a8f98); text-align: center; margin: 0; }

@media (max-width: 520px) {
  .lb-shell { padding: 11px 12px; }
  .lb-player { min-width: 104px; padding: 6px 9px; }
  .lb-ptxt b { max-width: 66px; font-size: 12px; }
  .lb-board { width: min(96vw, 620px); }
  .lb-ctrl { padding: 10px 12px; gap: 10px; }
  .lb-log { min-width: 140px; }
}

/* ===== 夜间主题：深色玻璃壳 + 深木纹棋盘（此前白壳压黑底发灰看不清） ===== */
:root[data-theme="night"] .lb-shell,
:root[data-theme="night"] .lb-online,
:root[data-theme="night"] .lb-ctrl {
  background: linear-gradient(160deg, rgba(38,44,58,.94), rgba(22,26,36,.92));
  border-color: rgba(199,169,107,.3);
  box-shadow: 0 8px 28px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.07);
}
:root[data-theme="night"] .lb-ptxt b { color: #f2eee4; }
:root[data-theme="night"] .lb-ptxt i { color: #b9b3cc; }
:root[data-theme="night"] .lb-mini em { background: rgba(255,255,255,.18); }
:root[data-theme="night"] .lb-online-title { color: #f2eee4; }
:root[data-theme="night"] .lb-online-desc,
:root[data-theme="night"] .lb-quota,
:root[data-theme="night"] .lb-log li { color: #b9b3cc; }
:root[data-theme="night"] .lb-log li.fresh { color: #f6f2e8; }
:root[data-theme="night"] .lb-status { color: #ded9ee; }
:root[data-theme="night"] .lb-hint { color: #a9a3bd; }
:root[data-theme="night"] .lb-btn { background: rgba(255,255,255,.09); border-color: rgba(255,255,255,.2); color: #ece7dc; }
:root[data-theme="night"] .lb-btn.primary { background: #c7a96b; border-color: #c7a96b; color: #1a1509; }
:root[data-theme="night"] .lb-mode { color: #ded9ee; border-color: rgba(255,255,255,.2); }
:root[data-theme="night"] .lb-mode.on { background: #c7a96b; border-color: #c7a96b; color: #1a1509; }
:root[data-theme="night"] .lb-select { background: rgba(255,255,255,.07); color: #f2eee4; border-color: rgba(255,255,255,.2); }
:root[data-theme="night"] .lb-banner.st-waiting { background: rgba(199,169,107,.2); color: #ded9ee; }
:root[data-theme="night"] .lb-banner.st-playing { background: rgba(127,168,163,.22); color: #ded9ee; }
:root[data-theme="night"] .lb-banner.st-finished { background: rgba(199,169,107,.26); color: #f6f2e8; }
:root[data-theme="night"] .lb-locknote { background: rgba(199,169,107,.22); color: #ded9ee; }
:root[data-theme="night"] .lb-board {
  background: linear-gradient(135deg, #6d5836, #4b3c24);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.14), 0 12px 34px rgba(0,0,0,.6);
  --lb-line: rgba(255,236,190,.32);
  --lb-empty: rgba(255,255,255,.13);
}
:root[data-theme="night"] .lb-cell.fly::after { color: rgba(255,236,190,.75); }
:root[data-theme="night"] .lb-base { background: color-mix(in srgb, var(--pc) 32%, #201c26); border-color: color-mix(in srgb, var(--pc) 70%, #fff); }
:root[data-theme="night"] .lb-slot { background: rgba(0,0,0,.32); box-shadow: inset 0 0 0 1px rgba(255,255,255,.18); }
:root[data-theme="night"] .lb-dice { background: linear-gradient(160deg, #efe9da, #cfc7b3); border-color: rgba(0,0,0,.3); }
</style>
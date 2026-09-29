<template>
  <div class="jq-wrap" :class="{ 'is-big': big }" :style="{ '--board-w': boardW + 'px', '--side-w': sideW + 'px', '--tilt': (big ? TILT_DEG : 0) + 'deg' }">
    <!-- ===== 辅栏 ===== -->
    <div class="jq-side">
      <div class="jq-shell">
        <div class="jq-players">
          <div class="jq-player" :class="{ active: !over && turnIdx === 0 }">
            <span class="jq-dot" :class="dotClass(0)"></span>
            <div class="jq-player-txt">
              <b>{{ nameOf(0) }}</b>
              <i>{{ subOf(0) }}</i>
            </div>
          </div>
          <span class="jq-vs">⚔</span>
          <div class="jq-player" :class="{ active: !over && turnIdx === 1 }">
            <span class="jq-dot" :class="dotClass(1)"></span>
            <div class="jq-player-txt">
              <b>{{ nameOf(1) }}</b>
              <i>{{ subOf(1) }}</i>
            </div>
          </div>
        </div>

        <div v-if="!bare" class="jq-modes" :class="{ locked: roomLocked }">
          <button
            v-for="m in MODES"
            :key="m.key"
            class="jq-mode"
            :class="{ on: mode === m.key }"
            :disabled="roomLocked && mode !== m.key"
            @click="setMode(m.key)"
          >{{ m.label }}</button>
        </div>

        <div v-if="mode !== 'online'" class="jq-status">
          <span v-if="over" class="jq-result">{{ resultText }}</span>
          <span v-else-if="isFlip" class="jq-quota">{{ flippedCount }} / {{ PIECE_N }} 已翻</span>
          <button class="jq-btn" @click="restart">重开</button>
          <button class="jq-btn" :disabled="!canUndo" @click="undoLocal">悔棋</button>
        </div>

        <div v-if="mode === 'online' && gRoom.room.value" class="jq-banner" :class="'st-' + gRoom.status.value">
          <template v-if="gRoom.status.value === 'waiting'">
            <span class="jq-pulse"></span> 邀请已发给 {{ gRoom.opponentName.value }}，等待接受…
            <span class="jq-firstnote">{{ gRoom.room.value.black_name }} 先行</span>
            <button class="jq-btn" @click="cancelInvite">取消邀请</button>
            <button class="jq-btn" @click="refreshRoom">刷新</button>
          </template>
          <template v-else-if="gRoom.status.value === 'playing'">
            <span>{{ gRoom.myTurn.value ? '轮到你' : '等对方行动…' }}</span>
            <button class="jq-btn" @click="askExit">退出对局（认输）</button>
          </template>
          <template v-else-if="gRoom.status.value === 'finished'">
            <span class="jq-result">{{ onlineResultText }}</span>
            <button class="jq-btn primary" @click="reinviteSame">再来一局</button>
            <button class="jq-btn" @click="exitOnline">退出</button>
          </template>
        </div>

        <!-- 战况：双方剩余子力 -->
        <div class="jq-stats">
          <div class="jq-stat">
            <span class="jq-dot red"></span>
            <span>红 {{ aliveOf(RED) }} 子</span>
            <span v-if="isFlip" class="jq-mine">雷 {{ minesOf(RED) }}</span>
          </div>
          <div class="jq-stat">
            <span class="jq-dot black"></span>
            <span>黑 {{ aliveOf(BLACK) }} 子</span>
            <span v-if="isFlip" class="jq-mine">雷 {{ minesOf(BLACK) }}</span>
          </div>
        </div>
      </div>

      <div v-if="mode === 'online' && !gRoom.room.value" class="jq-online">
        <div class="jq-online-title">🎯 在线邀请对战</div>
        <p class="jq-online-desc">
          {{ isFlip ? '翻棋：50 枚棋子随机背面撒盘，先翻定色；吃掉对方三颗地雷后才能拔旗。'
                    : '明棋：双方布阵全明，铁路快行、行营免攻、大本营内的子不可再动。' }}
        </p>
        <div class="jq-online-row">
          <MemberPicker v-model="inviteeId" :members="families" placeholder="选择一位家人…" />
        </div>
        <div class="jq-online-row">
          <span class="jq-first-label">先手：</span>
          <button class="jq-mode" :class="{ on: firstPick === 'me' }" @click="firstPick = 'me'">我先走</button>
          <button class="jq-mode" :class="{ on: firstPick === 'other' }" @click="firstPick = 'other'">对方先走</button>
        </div>
        <div class="jq-online-row">
          <button class="jq-btn primary" :disabled="!inviteeId || gRoom.joining.value" @click="invite">
            {{ gRoom.joining.value ? '创建中…' : '发出邀请' }}
          </button>
        </div>
        <p v-if="!families.length" class="jq-online-desc">家庭里还没有其他账号可以邀请。</p>
      </div>

      <p v-if="lockHint" class="jq-locknote"><span class="jq-dot-sm"></span>{{ lockHint }}</p>
    </div>

    <!-- ===== 主区：棋盘 ===== -->
    <div ref="mainEl" class="jq-main">
      <div class="jq-board" :style="{ width: boardW + 'px', height: boardH + 'px' }">
        <!-- eslint-disable-next-line vue/no-v-html -- 本地常量 SVG，无外部输入 -->
        <svg class="jq-svg" :viewBox="`0 0 ${boardW} ${boardH}`" aria-hidden="true" v-html="svgMarkup"></svg>
        <button
          v-for="(p, i) in board"
          :key="i"
          class="jq-cell"
          :class="{ sel: selIdx === i, target: targets.includes(i), last: lastIdx === i }"
          :style="cellStyle(i)"
          :aria-label="ariaOf(i, p)"
          @click="tap(i)"
        >
          <span v-if="!p" class="jq-slot"></span>
          <span v-else-if="!p.up" class="jq-back" :class="{ fresh: freshIdx === i }"><i>❖</i></span>
          <span
            v-else
            class="jq-piece"
            :class="[p.c === RED ? 'red' : 'black', { fresh: freshIdx === i }]"
          >{{ LABEL[p.t] }}</span>
        </button>
      </div>
    </div>

    <p class="jq-hint">
      <template v-if="mode === 'online'">在线模式 · 对方行动约 2 秒内自动出现</template>
      <template v-else-if="isFlip">先翻子定色 · 工兵可拐弯 · 炸弹同归于尽 · 工兵排雷 · 吃光对方三雷后方可拔旗</template>
      <template v-else>红先 · 司令＞军长＞师长＞旅长＞团长＞营长＞连长＞排长＞工兵 · 同级同归于尽 · 行营免攻</template>
    </p>
  </div>
</template>

<script setup>
/** 军棋（陆战棋）· 明棋 + 翻棋（自写，无外部依赖）。
 *
 * 棋盘：12 行 × 5 列 = 60 点；每方 2 大本营、5 行营、23 兵站。
 * 铁路：横线第 2/6/7/11 行 + 纵线第 2/4 列（纵向仅 1~10 行）；工兵可在铁路上拐弯，其余只能直行。
 * 行营：安全岛，不可被吃；行营内的子只能走一步。大本营：明棋中进入后不可再动（翻棋可动）。
 * 碰子：军阶低者亡；同级同归于尽；炸弹碰任何子同归于尽；工兵排雷（雷亡兵存）；
 *       其余子碰雷则亡（雷留）；军旗被吃即负。
 * 翻棋：50 枚棋子随机背面撒在 50 个非行营点，先翻定色；必须先清光对方 3 颗地雷才能拔旗。
 * 对手：双人同屏 / 单机（贪心 AI）/ 在线邀请（轮询同步，客户端权威）。
 */
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGameRoom } from '@/composables/useGameRoom'
import MemberPicker from '@/components/games/MemberPicker.vue'
import { familyMembers } from '@/api/lifeExtra'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'

const emit = defineEmits(['room-lock', 'room-unlock', 'exit'])
const props = defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
  joinRoomId: { type: Number, default: 0 },
  boardSize: { type: Number, default: 0 },
  big: { type: Boolean, default: false },
  gameKey: { type: String, default: 'junqi' },
})

const MODES = [
  { key: 'pvp', label: '双人（同屏）' },
  { key: 'easy', label: '单机 · 电脑' },
  { key: 'online', label: '在线 · 邀请对战' },
]

const COLS = 5, ROWS = 12, N = COLS * ROWS
const PAD = 22
const RED = 'r', BLACK = 'b'
const other = c => (c === RED ? BLACK : RED)
const isFlip = computed(() => String(props.gameKey).endsWith('_flip'))
const GAME_KEY = computed(() => props.gameKey || 'junqi')

const LABEL = {
  S: '司令', J: '军长', Z: '师长', L: '旅长', T: '团长', Y: '营长',
  C: '连长', P: '排长', G: '工兵', B: '炸弹', D: '地雷', F: '军旗',
}
const RANKV = { S: 9, J: 8, Z: 7, L: 6, T: 5, Y: 4, C: 3, P: 2, G: 1 }
const VAL = { S: 90, J: 70, Z: 45, L: 32, T: 24, Y: 16, C: 10, P: 6, G: 14, B: 42, D: 26, F: 900 }

/* ---------- 棋盘拓扑 ---------- */
const idx = (r, c) => r * COLS + c
const rowOf = i => (i / COLS) | 0
const colOf = i => i % COLS
const CAMP_LIST = [[2, 1], [2, 3], [3, 2], [4, 1], [4, 3], [7, 1], [7, 3], [8, 2], [9, 1], [9, 3]]
const HQ_LIST = [[0, 1], [0, 3], [11, 1], [11, 3]]
const CAMPS = new Set(CAMP_LIST.map(([r, c]) => idx(r, c)))
const HQS = new Set(HQ_LIST.map(([r, c]) => idx(r, c)))
const RAIL_ROWS = new Set([1, 5, 6, 10])
const RAIL_COLS = new Set([1, 3])
function isRailPoint(r, c) {
  if (r < 0 || r >= ROWS || c < 0 || c >= COLS) return false
  if (RAIL_ROWS.has(r)) return true
  return RAIL_COLS.has(c) && r >= 1 && r <= 10
}
/** 行营斜线：中营 ↔ 四角行营 */
const CAMP_DIAG = [
  [idx(2, 1), idx(3, 2)], [idx(2, 3), idx(3, 2)], [idx(4, 1), idx(3, 2)], [idx(4, 3), idx(3, 2)],
  [idx(7, 1), idx(8, 2)], [idx(7, 3), idx(8, 2)], [idx(9, 1), idx(8, 2)], [idx(9, 3), idx(8, 2)],
]
const NEI = (() => {
  const a = Array.from({ length: N }, () => [])
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
    const i = idx(r, c)
    for (const [dr, dc] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nr = r + dr, nc = c + dc
      if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) a[i].push(idx(nr, nc))
    }
  }
  for (const [x, y] of CAMP_DIAG) { a[x].push(y); a[y].push(x) }
  return a
})()
const RAIL_NB = (() => {
  const a = Array.from({ length: N }, () => [])
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
    const i = idx(r, c)
    if (!isRailPoint(r, c)) continue
    for (const [dr, dc] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
      const nr = r + dr, nc = c + dc
      if (!isRailPoint(nr, nc)) continue
      a[i].push(idx(nr, nc))
    }
  }
  return a
})()

/* ---------- 布阵 ---------- */
// 红方（下方）固定布阵：军旗在大本营、地雷在最后两排、炸弹不在第一排
const BOTTOM_LAYOUT = [
  [6, 0, 'Y'], [6, 1, 'C'], [6, 2, 'C'], [6, 3, 'C'], [6, 4, 'Y'],
  [7, 0, 'Z'], [7, 2, 'L'], [7, 4, 'Z'],
  [8, 0, 'J'], [8, 1, 'G'], [8, 3, 'L'], [8, 4, 'S'],
  [9, 0, 'T'], [9, 2, 'B'], [9, 4, 'G'],
  [10, 0, 'D'], [10, 1, 'T'], [10, 2, 'D'], [10, 3, 'P'], [10, 4, 'D'],
  [11, 0, 'P'], [11, 1, 'F'], [11, 2, 'B'], [11, 3, 'P'], [11, 4, 'G'],
]
const PIECE_N = BOTTOM_LAYOUT.length * 2   // 翻棋棋子总数（红黑各 25 = 50），棋盘格数 N=60 含 10 个行营空格
function openSetup() {
  const bd = new Array(N).fill(null)
  for (const [r, c, t] of BOTTOM_LAYOUT) bd[idx(r, c)] = { c: RED, t, up: true }
  for (const [r, c, t] of BOTTOM_LAYOUT) bd[idx(ROWS - 1 - r, COLS - 1 - c)] = { c: BLACK, t, up: true }
  return bd
}
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
/** 翻棋：50 枚棋子（红黑各 25）随机背面撒在 50 个非行营点 */
function flipSetup(seed) {
  const deck = []
  for (const [, , t] of BOTTOM_LAYOUT) { deck.push({ c: RED, t, up: false }); deck.push({ c: BLACK, t, up: false }) }
  const rnd = mulberry32(seed || ((Date.now() ^ 0x2f7d) & 0x7fffffff))
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1))
    const t = deck[i]; deck[i] = deck[j]; deck[j] = t
  }
  const spots = []
  for (let i = 0; i < N; i++) if (!CAMPS.has(i)) spots.push(i)
  const bd = new Array(N).fill(null)
  spots.forEach((s, k) => { bd[s] = deck[k] })
  return bd
}

/* ---------- 碰子 ---------- */
/** 攻方 att 碰守方 def：'att'=攻方占据 / 'both'=同归于尽 / 'def'=攻方亡、守方留 */
function clash(att, def) {
  if (def.t === 'F') return 'att'
  if (att.t === 'B' || def.t === 'B') return 'both'
  if (def.t === 'D') return att.t === 'G' ? 'att' : 'def'
  if (att.t === 'D' || att.t === 'F') return 'def'
  if (RANKV[att.t] === RANKV[def.t]) return 'both'
  return RANKV[att.t] > RANKV[def.t] ? 'att' : 'def'
}
function minesLeft(bd, color) {
  let n = 0
  for (const p of bd) if (p && p.c === color && p.t === 'D') n++
  return n
}
function canLandOn(bd, from, to) {
  const p = bd[from]
  if (!p) return false
  if (CAMPS.has(to)) return false                       // 行营免攻
  const q = bd[to]
  if (!q) return true
  if (isFlip.value && !q.up) return false               // 翻棋：暗子不可碰
  if (q.c === p.c) return false
  if (isFlip.value && q.t === 'F' && minesLeft(bd, q.c) > 0) return false   // 翻棋：先清雷
  return true
}
/** 铁路直行（不可拐弯），纵向铁路只覆盖 1~10 行 */
function railLine(bd, i) {
  const r = rowOf(i), c = colOf(i)
  const out = []
  const step = (dr, dc, rMin, rMax) => {
    let nr = r + dr, nc = c + dc
    while (nr >= rMin && nr <= rMax && nc >= 0 && nc < COLS && isRailPoint(nr, nc)) {
      const j = idx(nr, nc)
      const q = bd[j]
      if (!q) out.push(j)
      else { if (canLandOn(bd, i, j)) out.push(j); break }
      nr += dr; nc += dc
    }
  }
  if (RAIL_ROWS.has(r)) { step(0, 1, 0, ROWS - 1); step(0, -1, 0, ROWS - 1) }
  if (RAIL_COLS.has(c) && r >= 1 && r <= 10) { step(1, 0, 1, 10); step(-1, 0, 1, 10) }
  return out
}
/** 工兵铁路 BFS：可拐弯，穿过空格，止于第一枚可吃的敌子 */
function railReach(bd, i) {
  const seen = new Set([i])
  const out = []
  const q = [i]
  while (q.length) {
    const cur = q.shift()
    for (const j of RAIL_NB[cur]) {
      if (seen.has(j)) continue
      seen.add(j)
      if (!bd[j]) { out.push(j); q.push(j) }
      else if (canLandOn(bd, i, j)) out.push(j)
    }
  }
  return out
}
function targetsFrom(bd, i) {
  const p = bd[i]
  if (!p) return []
  if (p.t === 'F' || p.t === 'D') return []
  if (!isFlip.value && HQS.has(i)) return []            // 明棋：大本营内不可动
  const out = []
  const push = j => { if (!out.includes(j) && canLandOn(bd, i, j)) out.push(j) }
  if (!CAMPS.has(i) && isRailPoint(rowOf(i), colOf(i))) {
    if (p.t === 'G') for (const j of railReach(bd, i)) push(j)
    else for (const j of railLine(bd, i)) push(j)
  }
  for (const j of NEI[i]) push(j)
  return out
}

/* ---------- 状态 ---------- */
const mode = ref(props.initialMode || 'easy')
const seed = ref(0)
const board = ref(isFlip.value ? flipSetup(0) : openSetup())
const turnIdx = ref(0)
const firstColor = ref(isFlip.value ? '' : RED)
const selIdx = ref(-1)
const lastIdx = ref(-1)
const freshIdx = ref(-1)
const over = ref(false)
const winnerColor = ref('')
const history = ref([])
const thinking = ref(false)
let timer = null

const cellPx = ref(40)
const mainEl = ref(null)
const boardW = computed(() => (COLS - 1) * cellPx.value + PAD * 2)
const boardH = computed(() => (ROWS - 1) * cellPx.value + PAD * 2)
const sideW = computed(() => Math.max(boardW.value, 396))

// 放大时棋盘绕底边后仰 TILT_DEG 度（与 <style> 的 .jq-board 一致）；视觉高度 = 实际 × cos
const TILT_DEG = 24
const TILT_COS = Math.cos((TILT_DEG * Math.PI) / 180)

function measureCell() {
  const el = mainEl.value
  const availW = el?.clientWidth || 0
  const availH = el?.clientHeight || 0
  const capW = props.big ? 440 : 360
  let c = Math.floor((Math.min(availW || capW, capW) - PAD * 2) / (COLS - 1))
  if (availH > 260) {
    const usableH = props.big ? availH / TILT_COS : availH
    c = Math.min(c, Math.floor((usableH - PAD * 2 - 30) / (ROWS - 1)))
  }
  cellPx.value = Math.max(24, Math.min(props.big ? 70 : 50, c))
}
function cellStyle(i) {
  const c = cellPx.value
  const w = Math.round(c * 0.86), h = Math.round(c * 0.6)
  return {
    left: PAD + colOf(i) * c - w / 2 + 'px',
    top: PAD + rowOf(i) * c - h / 2 + 'px',
    width: w + 'px',
    height: h + 'px',
    fontSize: Math.round(c * 0.34) + 'px',
  }
}
const svgMarkup = computed(() => {
  const c = cellPx.value
  const X = i => PAD + i * c
  const Y = j => PAD + j * c
  const L = []
  for (let r = 0; r < ROWS; r++) for (let col = 0; col < COLS; col++) {
    const i = idx(r, col)
    for (const j of NEI[i]) {
      if (j < i) continue
      const dr = Math.abs(rowOf(j) - r), dc = Math.abs(colOf(j) - col)
      if (dr + dc !== 1) continue                        // 正交公路单独画，斜线下面补
      L.push(`<line class="jq-road" x1="${X(col)}" y1="${Y(r)}" x2="${X(colOf(j))}" y2="${Y(rowOf(j))}"/>`)
    }
  }
  for (const [a, b] of CAMP_DIAG) {
    L.push(`<line class="jq-road" x1="${X(colOf(a))}" y1="${Y(rowOf(a))}" x2="${X(colOf(b))}" y2="${Y(rowOf(b))}"/>`)
  }
  for (const r of RAIL_ROWS) L.push(`<line class="jq-rail" x1="${X(0)}" y1="${Y(r)}" x2="${X(COLS - 1)}" y2="${Y(r)}"/>`)
  for (const col of RAIL_COLS) L.push(`<line class="jq-rail" x1="${X(col)}" y1="${Y(1)}" x2="${X(col)}" y2="${Y(10)}"/>`)
  for (const i of CAMPS) L.push(`<circle class="jq-camp" cx="${X(colOf(i))}" cy="${Y(rowOf(i))}" r="${Math.round(c * 0.4)}"/>`)
  for (const i of HQS) {
    L.push(`<rect class="jq-hq" x="${X(colOf(i)) - c * 0.44}" y="${Y(rowOf(i)) - c * 0.34}" width="${c * 0.88}" height="${c * 0.68}" rx="${c * 0.16}"/>`)
  }
  return `<g>${L.join('')}</g>`
})

function colorOf(k) {
  if (!isFlip.value) return k === 0 ? RED : BLACK
  if (!firstColor.value) return ''
  return k === 0 ? firstColor.value : other(firstColor.value)
}
const turnColor = computed(() => colorOf(turnIdx.value))
const flippedCount = computed(() => board.value.filter(p => p && p.up).length)
const aliveOf = c => board.value.filter(p => p && p.c === c).length
const minesOf = c => minesLeft(board.value, c)
const targets = computed(() => {
  if (selIdx.value < 0 || over.value) return []
  return targetsFrom(board.value, selIdx.value)
})
function ariaOf(i, p) {
  const s = `第${rowOf(i) + 1}行第${colOf(i) + 1}列`
  if (!p) return `${s} 空`
  if (!p.up) return `${s} 未翻开的棋子`
  return `${s} ${p.c === RED ? '红' : '黑'}${LABEL[p.t]}`
}

/* ---------- 行动 ---------- */
function snapshot() { return board.value.map(p => (p ? { ...p } : null)) }
function doFlip(i) {
  const p = board.value[i]
  if (!p || p.up) return false
  p.up = true
  if (!firstColor.value) firstColor.value = p.c
  freshIdx.value = i
  lastIdx.value = -1
  return true
}
function doMove(from, to) {
  const bd = board.value
  const p = bd[from], q = bd[to]
  if (!p) return false
  if (q) {
    if (q.t === 'F') { bd[to] = p; bd[from] = null; return 'flag' }
    const res = clash(p, q)
    if (res === 'att') { bd[to] = p; bd[from] = null }
    else if (res === 'both') { bd[to] = null; bd[from] = null }
    else { bd[from] = null }
  } else {
    bd[to] = p; bd[from] = null
  }
  freshIdx.value = -1
  lastIdx.value = to
  return true
}
function act(a) {
  const snap = snapshot()
  const before = turnIdx.value
  let ok
  if (typeof a.flip === 'number') ok = doFlip(a.flip)
  else ok = doMove(a.from, a.to)
  if (!ok) return
  history.value.push({ a, snap, before })
  if (mode.value === 'online') gRoom.send(a).catch(() => { /* 下轮轮询以服务端事件流为准 */ })
  if (ok === 'flag') {
    over.value = true
    winnerColor.value = turnColor.value
    afterAction(true)
    return
  }
  afterAction(false)
}
function afterAction(finished) {
  turnIdx.value = 1 - turnIdx.value
  selIdx.value = -1
  if (!finished) settle()
  if (mode.value === 'online' && over.value) reportFinish()
  if (!over.value && aiTurn.value) scheduleAI()
}
function settle() {
  const c0 = colorOf(0), c1 = colorOf(1)
  if (c0 && c1) {
    if (!aliveOf(c0) || !aliveOf(c1)) { over.value = true; winnerColor.value = aliveOf(c0) ? c0 : c1; return }
  }
  if (!sideHasAction(turnIdx.value)) {
    over.value = true
    winnerColor.value = sideHasAction(1 - turnIdx.value) ? colorOf(1 - turnIdx.value) : ''
  }
}
function sideHasAction(k) {
  if (isFlip.value && board.value.some(p => p && !p.up)) return true
  const col = colorOf(k)
  if (!col) return true
  for (let i = 0; i < N; i++) {
    const p = board.value[i]
    if (p && p.up && p.c === col && targetsFrom(board.value, i).length) return true
  }
  return false
}

/* ---------- 交互 ---------- */
const aiIdx = 1
const aiTurn = computed(() => mode.value === 'easy' && turnIdx.value === aiIdx)
const boardLocked = computed(() => {
  if (over.value) return true
  if (mode.value === 'online') return !onlineMyTurn.value
  return aiTurn.value || thinking.value
})
function tap(i) {
  if (boardLocked.value) return
  const p = board.value[i]
  if (!p) { selIdx.value = -1; return }
  if (!p.up) { act({ flip: i }); return }
  if (selIdx.value >= 0 && targets.value.includes(i)) { act({ from: selIdx.value, to: i }); return }
  if (p.c === turnColor.value) selIdx.value = i
  else selIdx.value = -1
}

/* ---------- AI ---------- */
function scheduleAI() {
  thinking.value = true
  clearTimeout(timer)
  timer = setTimeout(() => {
    const a = aiChoose()
    thinking.value = false
    if (!a) return
    const snap = snapshot()
    const before = turnIdx.value
    const ok = typeof a.flip === 'number' ? doFlip(a.flip) : doMove(a.from, a.to)
    if (!ok) return
    history.value.push({ a, snap, before })
    if (ok === 'flag') { over.value = true; winnerColor.value = turnColor.value; afterAction(true) }
    else afterAction(false)
  }, 340)
}
function riskAt(bd, j) {
  const p = bd[j]
  if (!p) return 0
  let worst = 0
  for (let k = 0; k < N; k++) {
    const q = bd[k]
    if (!q || q.c === p.c || !q.up) continue
    if (!targetsFrom(bd, k).includes(j)) continue
    const res = clash(q, p)
    if (res === 'att') worst = Math.max(worst, VAL[p.t])
    else if (res === 'both') worst = Math.max(worst, VAL[p.t] - VAL[q.t])
  }
  return worst
}
function scoreMove(bd, me, a) {
  if (typeof a.flip === 'number') return 2
  const from = a.from, to = a.to
  const p = bd[from], q = bd[to]
  const nb = bd.slice()
  let sc = 0
  if (q) {
    if (q.t === 'F') return 5000
    const res = clash(p, q)
    if (res === 'att') { nb[to] = p; nb[from] = null; sc += VAL[q.t] }
    else if (res === 'both') { nb[to] = null; nb[from] = null; sc += VAL[q.t] - VAL[p.t] }
    else { nb[from] = null; sc -= VAL[p.t] }
  } else { nb[to] = p; nb[from] = null }
  if (sc < -1) return sc
  const dir = me === RED ? -1 : 1
  sc += (rowOf(to) - rowOf(from)) * dir * 1.4
  if (isRailPoint(rowOf(to), colOf(to))) sc += 1.2
  if (nb[to]) sc -= riskAt(nb, to) * 0.85
  return sc
}
function aiChoose() {
  const me = colorOf(aiIdx)
  const bd = board.value
  const cands = []
  if (isFlip.value) {
    for (let i = 0; i < N; i++) if (bd[i] && !bd[i].up) cands.push({ flip: i, sc: 2 })
  }
  for (let i = 0; i < N; i++) {
    const p = bd[i]
    if (!p || !p.up || p.c !== me) continue
    for (const j of targetsFrom(bd, i)) cands.push({ from: i, to: j, sc: scoreMove(bd, me, { from: i, to: j }) })
  }
  if (!cands.length) return null
  for (const c of cands) c.sc += Math.random() * 2.5
  cands.sort((a, b) => b.sc - a.sc)
  const top = cands.slice(0, Math.min(3, cands.length))
  return top[(Math.random() * top.length) | 0]
}

/* ---------- 悔棋（仅本地） ---------- */
const canUndo = computed(() => mode.value !== 'online' && !thinking.value && history.value.length > 0 && !over.value)
function undoLocal() {
  if (!canUndo.value) return
  const h = history.value.pop()
  if (!h) return
  board.value = h.snap
  turnIdx.value = h.before
  selIdx.value = -1
  lastIdx.value = -1
  freshIdx.value = -1
  over.value = false
  winnerColor.value = ''
}

/* ---------- 在线对战 ---------- */
const families = ref([])
const inviteeId = ref(null)
const firstPick = ref('me')
const onlineWinner = ref('')
const lastInviteeName = ref('')
let exited = false
let finishedReported = false

function onRemoteMove(action) {
  let ok
  if (typeof action?.flip === 'number') ok = doFlip(action.flip)
  else if (typeof action?.from === 'number' && typeof action?.to === 'number') ok = doMove(action.from, action.to)
  else return
  if (!ok) return
  turnIdx.value = 1 - turnIdx.value
  selIdx.value = -1
  if (ok === 'flag') { over.value = true; winnerColor.value = turnColor.value; return }
  settle()
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

const myIdx = computed(() => (gRoom.mySeat.value === 'black' ? 0 : 1))
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
  if (st === 'playing') return gRoom.myTurn.value ? '' : `等「${who}」行动…`
  if (st === 'finished') return '本局已结束'
  return ''
})
/** 在线终局上报：只由「走出终局的那一方」上报一次，避免双方重复 finish */
function reportFinish() {
  if (finishedReported || !gRoom.room.value) return
  finishedReported = true
  const uid = Number(gRoom.myUserId.value)
  const mine = colorOf(myIdx.value)
  const oppId = gRoom.room.value.owner_id === uid ? gRoom.room.value.invitee_id : gRoom.room.value.owner_id
  gRoom.finish(winnerColor.value ? (winnerColor.value === mine ? uid : Number(oppId)) : 0)
    .catch(() => { /* 对方可能已上报终局 */ })
}

function nameOf(k) {
  const col = colorOf(k)
  if (mode.value === 'online' && gRoom.room.value) {
    const who = myIdx.value === k ? '你' : (gRoom.opponentName.value || '对方')
    return col ? `${who}（${col === RED ? '红' : '黑'}）` : who
  }
  if (mode.value === 'pvp') {
    const base = isFlip.value ? (k === 0 ? '先手' : '后手') : (k === 0 ? '红方' : '黑方')
    return isFlip.value && col ? `${base}（${col === RED ? '红' : '黑'}）` : base
  }
  const base = k === 0 ? '你' : '电脑'
  return col ? `${base}（${col === RED ? '红' : '黑'}）` : base
}
function subOf(k) {
  if (over.value) return ''
  if (isFlip.value && !firstColor.value) return k === 0 ? '请翻子定色' : '待翻'
  return turnIdx.value === k ? '行动中' : '待走'
}
function dotClass(k) {
  const col = colorOf(k)
  if (!col) return 'none'
  return col === RED ? 'red' : 'black'
}
const resultText = computed(() => {
  if (!winnerColor.value) return over.value ? '🤝 平局' : ''
  if (mode.value === 'pvp') return winnerColor.value === RED ? '🎉 红方胜' : '🎉 黑方胜'
  return winnerColor.value === colorOf(aiIdx) ? '电脑赢了，再来' : '🎉 你赢了'
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
    const r = await gRoom.createInvite(inviteeId.value, firstPick.value)
    if (isFlip.value && r?.id) resetWithSeed(r.id)
    ElMessage.success(`邀请已发出（${firstPick.value === 'me' ? '你' : lastInviteeName.value || '对方'}先行），等对方接受`)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || e?.response?.data?.msg || e?.msg || '邀请失败')
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
      const r = await gRoom.createInvite(uid, firstPick.value)
      if (isFlip.value && r?.id) resetWithSeed(r.id)
      ElMessage.success(`新对局已发出（${firstPick.value === 'me' ? '你' : '对方'}先行）`)
    } catch (e) { ElMessage.warning(e?.response?.data?.detail || e?.response?.data?.msg || e?.msg || '邀请失败') }
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

/** 在线翻棋：以房间号为种子重铺暗子（两端完全一致） */
function resetWithSeed(id) {
  seed.value = id
  board.value = flipSetup(id)
  turnIdx.value = 0
  firstColor.value = ''
  selIdx.value = -1
  lastIdx.value = -1
  freshIdx.value = -1
  over.value = false
  winnerColor.value = ''
  history.value = []
  thinking.value = false
  onlineWinner.value = ''
  finishedReported = false
}
async function resumeMine() {
  try {
    const res = await (await import('@/api/gameRooms')).gameRoomsApi.mine()
    const active = (res?.data?.list || []).find(x => x.game === GAME_KEY.value && ['waiting', 'playing'].includes(x.status))
    if (!active) return
    mode.value = 'online'
    if (isFlip.value) resetWithSeed(active.id)
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
      seed: seed.value,
      turnIdx: turnIdx.value,
      firstColor: firstColor.value,
      history: history.value,
      lastIdx: lastIdx.value,
      flip: isFlip.value,
    })
  }, 400)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !Array.isArray(s.board) || s.board.length !== N || s.mode === 'online') return false
  if (!!s.flip !== isFlip.value) return false
  if (s.mode) mode.value = s.mode
  seed.value = s.seed || 0
  board.value = s.board
  turnIdx.value = s.turnIdx || 0
  firstColor.value = s.firstColor || (isFlip.value ? '' : RED)
  history.value = s.history || []
  lastIdx.value = s.lastIdx ?? -1
  over.value = false
  winnerColor.value = ''
  settle()
  return true
}
watch([board, over], saveLocal, { deep: true })

function clearLocal() {
  clearTimeout(timer)
  seed.value = 0
  board.value = isFlip.value ? flipSetup(0) : openSetup()
  turnIdx.value = 0
  firstColor.value = isFlip.value ? '' : RED
  selIdx.value = -1
  lastIdx.value = -1
  freshIdx.value = -1
  over.value = false
  winnerColor.value = ''
  history.value = []
  thinking.value = false
  onlineWinner.value = ''
  finishedReported = false
}
function setMode(k) {
  if (roomLocked.value && k !== mode.value) { ElMessage.warning('对局进行中 —— 先点「退出对局」再切换模式'); return }
  mode.value = k
  clearLocal()
  gRoom.reset()
  if (k === 'online') loadFamilies()
  else if (k === 'easy') scheduleAI()
}
function restart() {
  if (mode.value === 'online') { ElMessage.info('在线模式请用「再来一局」或「退出对局」'); return }
  clearTimeout(saveTimer)
  clearGame(SAVE_KEY)
  clearLocal()
  if (mode.value === 'easy') scheduleAI()
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
    if (isFlip.value) resetWithSeed(props.joinRoomId)
    try { await gRoom.join(props.joinRoomId, { autoAccept: true }) } catch { /* 忽略 */ }
    emit('room-lock')
  } else if (mode.value === 'online') {
    await resumeMine()
  } else if (!restored && aiTurn.value) {
    scheduleAI()
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  clearTimeout(timer); clearTimeout(saveTimer)
  if (roomActive.value) gRoom.leaveOnUnload()
})
</script>

<style scoped>
.jq-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.jq-side { width: var(--side-w, 100%); max-width: 100%; display: flex; flex-direction: column; gap: 10px; }
.jq-main {
  width: 100%; display: flex; justify-content: center;
  /* 透视容器：放大后棋盘绕底边后仰平躺，像摆在桌面上（与象棋同一套透视语言） */
  perspective: 1180px; perspective-origin: 50% 26%;
}

/* ===== 玩家条 ===== */
.jq-shell {
  border-radius: 18px; padding: 12px 14px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  background: var(--color-bg-glass, rgba(255,255,255,.6));
  backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  box-shadow: var(--shadow-glass, 0 8px 24px rgba(20,30,40,.08));
  display: flex; flex-direction: column; gap: 10px;
}
.jq-players { display: flex; align-items: center; justify-content: center; gap: 14px; }
.jq-player { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 12px; transition: all .2s; }
.jq-player.active { background: var(--yq-gold-faint, rgba(199,169,107,.16)); box-shadow: inset 0 0 0 1px var(--yq-gold, #c7a96b); }
.jq-dot { width: 14px; height: 14px; border-radius: 50%; flex: none; }
.jq-dot.red { background: radial-gradient(circle at 34% 30%, #f6b3a5, #c0392b 70%); }
.jq-dot.black { background: radial-gradient(circle at 34% 30%, #7b8494, #1f2630 70%); }
.jq-dot.none { background: transparent; box-shadow: inset 0 0 0 1.5px var(--dp-line, rgba(0,0,0,.25)); }
.jq-player-txt { display: flex; flex-direction: column; line-height: 1.25; }
.jq-player-txt b { font-size: 13px; color: var(--dp-text, #18202a); }
.jq-player-txt i { font-style: normal; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.jq-vs { color: var(--yq-gold, #c7a96b); font-size: 13px; }

.jq-modes { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.jq-mode {
  padding: 6px 12px; border-radius: 999px; font-size: 12px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: transparent;
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.jq-mode:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.jq-mode.on {
  background: var(--yq-gold-faint, rgba(199,169,107,.16));
  border-color: var(--yq-gold, #c7a96b);
  color: var(--yq-gold-deep, var(--yq-gold, #c7a96b));
  box-shadow: 0 6px 18px var(--yq-gold-glow, rgba(199,169,107,.16));
}
.jq-mode:disabled { opacity: .4; cursor: not-allowed; }

.jq-status { display: flex; align-items: center; gap: 8px; justify-content: center; flex-wrap: wrap; }
.jq-btn {
  padding: 6px 13px; border-radius: 999px; font-size: 12.5px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.jq-btn:hover:not(:disabled) { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.jq-btn:disabled { opacity: .4; cursor: not-allowed; }
.jq-btn.primary { background: var(--yq-gold, #c7a96b); color: #fff; border-color: transparent; }
.jq-quota { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.jq-result { font-size: 13px; font-weight: 600; color: var(--yq-gold-deep, var(--yq-gold, #c7a96b)); }

.jq-stats { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }
.jq-stat { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--dp-text2, #45505b); }
.jq-mine { color: var(--dp-text3, #8a8f98); }

.jq-banner {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center;
  font-size: 12.5px; color: var(--dp-text2, #45505b);
}
.jq-firstnote { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.jq-pulse {
  width: 8px; height: 8px; border-radius: 50%; background: var(--yq-gold, #c7a96b);
  animation: jqPulse 1.4s ease-in-out infinite;
}
@keyframes jqPulse { 0%, 100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1.15); } }

.jq-online {
  border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 10px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  background: var(--color-bg-glass, rgba(255,255,255,.5));
}
.jq-online-title { font-size: 13.5px; font-weight: 600; color: var(--dp-text, #18202a); }
.jq-online-desc { font-size: 12px; line-height: 1.7; margin: 0; color: var(--dp-text2, #8a8f98); }
.jq-online-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.jq-first-label { font-size: 12px; color: var(--dp-text2, #8a8f98); }
.jq-locknote {
  margin: 0; font-size: 12px; color: var(--dp-text2, #8a8f98);
  display: flex; align-items: center; gap: 6px; justify-content: center;
}
.jq-dot-sm { width: 6px; height: 6px; border-radius: 50%; background: var(--yq-gold, #c7a96b); }

/* ===== 棋盘：青玉 / 墨玉盘面 + 立体盘厚（与象棋明棋/翻棋同一套材质语言） ===== */
.jq-board {
  position: relative; border-radius: 16px;
  background:
    radial-gradient(135% 100% at 50% -12%, rgba(255,255,255,.72), rgba(255,255,255,0) 58%),
    repeating-linear-gradient(92deg, rgba(58,96,88,.05) 0 1px, rgba(0,0,0,0) 1px 6px),
    linear-gradient(158deg, #e9f1ea 0%, #d2e1d7 46%, #b6ccc0 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.7),
    inset 0 0 0 1px rgba(96,124,108,.35),
    inset 0 -10px 22px -12px rgba(20,44,38,.4),
    0 8px 0 -1px #a6bbae,
    0 15px 0 -2px #82988c,
    0 22px 0 -3px #63776d,
    0 29px 0 -6px #46574f,
    0 46px 56px -22px rgba(20, 34, 30, .6);
  transform-origin: 50% 100%;
  transform: rotateX(var(--tilt, 0deg));
  transition: transform .3s cubic-bezier(.4, .1, .2, 1);
  will-change: transform;
}
.jq-wrap.is-big .jq-board {
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
html[data-theme="night"] .jq-board {
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
html[data-theme="night"] .jq-wrap.is-big .jq-board {
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
.jq-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.jq-svg :deep(line.jq-road) { stroke: rgba(146, 114, 52, .42); stroke-width: 1; }
.jq-svg :deep(line.jq-rail) { stroke: rgba(146, 114, 52, .72); stroke-width: 3.4; stroke-linecap: round; }
.jq-svg :deep(circle.jq-camp) {
  fill: rgba(199, 169, 107, .16); stroke: rgba(146, 114, 52, .58); stroke-width: 1.4;
}
.jq-svg :deep(rect.jq-hq) {
  fill: rgba(199, 169, 107, .2); stroke: rgba(146, 114, 52, .64); stroke-width: 1.4;
}
html[data-theme="night"] .jq-svg :deep(line.jq-road) { stroke: rgba(214, 190, 140, .3); }
html[data-theme="night"] .jq-svg :deep(line.jq-rail) { stroke: rgba(214, 190, 140, .62); }
html[data-theme="night"] .jq-svg :deep(circle.jq-camp) { fill: rgba(199,169,107,.12); stroke: rgba(214,190,140,.5); }
html[data-theme="night"] .jq-svg :deep(rect.jq-hq) { fill: rgba(199,169,107,.16); stroke: rgba(214,190,140,.55); }

.jq-cell {
  position: absolute; padding: 0; cursor: pointer; border: none; background: transparent;
  display: grid; place-items: center; border-radius: 8px;
  transition: box-shadow .16s, transform .16s;
}
.jq-slot { width: 100%; height: 100%; border-radius: 8px; }
.jq-back {
  width: 100%; height: 100%; border-radius: 10px; display: grid; place-items: center;
  /* 磨砂玉色牌背：保留斜纹暗花，叠加玻璃高光，与正面水晶牌同一材质语言 */
  background:
    radial-gradient(circle at 30% 20%, rgba(255,255,255,.85) 0 14%, transparent 36%),
    repeating-linear-gradient(45deg, rgba(96,124,108,.1) 0 3px, transparent 3px 7px),
    linear-gradient(150deg, rgba(214,232,222,.9), rgba(170,198,184,.84) 52%, rgba(132,166,152,.88));
  box-shadow:
    0 3px 8px rgba(24, 44, 38, .3),
    inset 0 0 0 1.3px rgba(255,255,255,.55),
    inset -2px -3px 8px rgba(40, 70, 60, .26);
}
html[data-theme="night"] .jq-back {
  background:
    radial-gradient(circle at 30% 20%, rgba(255,255,255,.3) 0 14%, transparent 36%),
    repeating-linear-gradient(45deg, rgba(199,169,107,.12) 0 3px, transparent 3px 7px),
    linear-gradient(150deg, rgba(58,84,78,.88), rgba(34,52,48,.86) 52%, rgba(20,32,30,.9));
  box-shadow:
    0 3px 8px rgba(0,0,0,.6),
    inset 0 0 0 1.3px rgba(199,169,107,.42),
    inset -2px -3px 8px rgba(0,0,0,.35);
}
.jq-back i { font-style: normal; font-size: .8em; color: rgba(52, 88, 76, .6); }
html[data-theme="night"] .jq-back i { color: rgba(214, 190, 140, .62); }
.jq-back.fresh { animation: jqFlipIn .42s ease-out; }

.jq-piece {
  position: relative;
  width: 100%; height: 100%; border-radius: 10px; display: grid; place-items: center;
  font-family: "Songti SC", "STSong", "SimSun", serif; font-weight: 700; line-height: 1;
  letter-spacing: .02em; user-select: none; white-space: nowrap;
  /* 透明水晶牌：半透明玻璃体 + 内部高光 + 折射边 + 玉环嵌口（加浓底色，昼夜都更清晰） */
  background:
    radial-gradient(circle at 30% 22%, rgba(255,255,255,.9) 0 12%, transparent 32%),
    radial-gradient(circle at 72% 82%, rgba(255,255,255,.28) 0 12%, transparent 36%),
    radial-gradient(circle at 50% 46%, rgba(255,255,255,.17) 0 58%, transparent 74%),
    linear-gradient(150deg, rgba(176,208,224,.6), rgba(236,228,210,.42) 46%, rgba(150,178,204,.56));
  box-shadow:
    inset 0 0 0 1.5px rgba(255,255,255,.6),
    inset 2px 3px 7px rgba(255,255,255,.58),
    inset -3px -4px 10px rgba(96,122,156,.44),
    0 4px 10px rgba(30, 48, 74, .34);
}
.jq-piece::before {
  content: ''; position: absolute; inset: 0; border-radius: 10px; pointer-events: none;
  box-shadow:
    inset 0 0 0 2px rgba(255,255,255,.44),
    inset 0 0 0 3.4px rgba(64,96,138,.28),
    inset 0 0 9px rgba(255,255,255,.18);
}
.jq-piece.red {
  color: #9e1a14;
  text-shadow: 0 1px 2px rgba(120, 20, 12, .38), 0 0 7px rgba(255, 170, 158, .5);
}
.jq-piece.black {
  color: #0a0f16;
  text-shadow: 0 1px 2px rgba(6, 10, 16, .42), 0 0 7px rgba(210, 224, 250, .45);
}
html[data-theme="night"] .jq-piece {
  background:
    radial-gradient(circle at 30% 22%, rgba(255,255,255,.4) 0 12%, transparent 32%),
    radial-gradient(circle at 72% 82%, rgba(255,255,255,.14) 0 12%, transparent 36%),
    radial-gradient(circle at 50% 46%, rgba(255,255,255,.09) 0 58%, transparent 74%),
    linear-gradient(150deg, rgba(140,178,208,.4), rgba(255,255,255,.12) 46%, rgba(108,146,186,.38));
  box-shadow:
    inset 0 0 0 1.5px rgba(255,255,255,.32),
    inset 2px 3px 7px rgba(255,255,255,.2),
    inset -3px -4px 10px rgba(74, 106, 148, .46),
    0 4px 10px rgba(0,0,0,.6);
}
html[data-theme="night"] .jq-piece::before {
  box-shadow:
    inset 0 0 0 2px rgba(255,255,255,.24),
    inset 0 0 0 3.4px rgba(130, 172, 216, .3),
    inset 0 0 9px rgba(255,255,255,.1);
}
html[data-theme="night"] .jq-piece.red { color: #ffb0a6; text-shadow: 0 1px 3px rgba(90, 14, 8, .62), 0 0 9px rgba(255,130,118,.42); }
html[data-theme="night"] .jq-piece.black { color: #f2f6fc; text-shadow: 0 1px 3px rgba(0,0,0,.7), 0 0 9px rgba(200,220,255,.4); }
.jq-piece.fresh { animation: jqFlipIn .42s ease-out; }
@keyframes jqFlipIn {
  from { transform: rotateY(90deg) scale(.88); opacity: .35; }
  to { transform: rotateY(0deg) scale(1); opacity: 1; }
}

.jq-cell.sel { box-shadow: 0 0 0 3px var(--yq-gold, #c7a96b), 0 0 14px rgba(199,169,107,.55); }
.jq-cell.last { box-shadow: 0 0 0 2px rgba(80, 140, 200, .75); }
.jq-cell.target { box-shadow: 0 0 0 3px rgba(199, 169, 107, .85); }
.jq-cell.target::after {
  content: ''; position: absolute; width: 30%; height: 30%; border-radius: 50%;
  background: var(--yq-gold, #c7a96b); opacity: .8;
}
.jq-cell.target:has(.jq-piece)::after, .jq-cell.target:has(.jq-back)::after { display: none; }

.jq-hint {
  margin: 0; font-size: 12px; line-height: 1.7; text-align: center;
  color: var(--dp-text3, #8a8f98);
}

/* ===== 放大：左主棋盘 + 右辅栏 ===== */
.jq-wrap.is-big {
  display: grid; grid-template-columns: minmax(0, 1fr) 330px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px 22px; width: 100%; height: 100%; min-height: 0;
}
.jq-wrap.is-big .jq-side {
  grid-column: 2; grid-row: 1 / span 2; width: 100%; max-height: 100%;
  overflow-y: auto; align-self: start;
}
.jq-wrap.is-big .jq-main {
  grid-column: 1; grid-row: 1; width: 100%; height: 100%; min-height: 0; align-items: center;
}
.jq-wrap.is-big .jq-hint { grid-column: 1; grid-row: 2; }
@media (max-width: 900px) {
  .jq-wrap.is-big { display: flex; flex-direction: column; }
  .jq-wrap.is-big .jq-side, .jq-wrap.is-big .jq-main { grid-column: auto; grid-row: auto; max-height: none; }
}
</style>
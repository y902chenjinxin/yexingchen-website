<template>
  <div class="g3d-board">
    <!-- 顶栏承担全部操作（棋盘倾斜后上下都没有安全区放浮动条） -->
    <header v-if="showTopbar" class="g3d-topbar">
      <div class="g3d-title">
        <span class="g3d-logo">3D</span>
        <div class="g3d-tx">
          <b>3D 象棋</b>
          <i>电脑 {{ alive.black }} 子 · {{ statusText }}</i>
        </div>
      </div>
      <div class="g3d-ops">
        <button class="g3d-op ghost" title="点击切换难度" @click="cycleDiff">{{ diffLabel }}</button>
        <button class="g3d-op ghost" :disabled="!canUndo" @click="undo">悔棋</button>
        <button class="g3d-op" @click="restart">重开</button>
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
import {
  COLS, ROWS, RED, BLACK, GLYPH,
  xOf, yOf, initialBoard, pieceTargets, applyMove, aiPick, inCheck, legalMoves, other,
} from '@/utils/xiangqiRules'
import AppIcon from '@/components/common/AppIcon.vue'
import '@/assets/styles/games3d.css'

defineProps({
  showTopbar: { type: Boolean, default: true },
})
defineEmits(['exit'])

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

/* ---------- 交互 ---------- */
function tap(i) {
  if (over.value || thinking.value) return
  if (turn.value !== RED) return
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
  cap ? sfx.capture() : sfx.wood()
  turn.value = other(turn.value)
  if (inCheck(board.value, turn.value)) sfx.check()
  settle()
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
  aiTimer = setTimeout(() => {
    const m = aiPick(board.value, BLACK, depth())
    thinking.value = false
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

onMounted(() => {
  sfx.preload()
  window.addEventListener('resize', onResize)
  window.addEventListener('orientationchange', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('orientationchange', onResize)
  clearTimeout(aiTimer)
  clearTimeout(toastTimer)
  clearTimeout(shakeTimer)
  clearTimeout(resultTimer)
})

defineExpose({ board, history, doMove, restart })
</script>

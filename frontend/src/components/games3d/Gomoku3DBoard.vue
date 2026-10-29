<template>
  <div class="g3d-board">
    <!-- 顶栏：所有操作塞这里，舞台内不放任何浮动条 ——
         3D 透视下棋盘远端会向上延伸，任何 absolute 浮动条都会压盘（v2.46.263 的教训）。 -->
    <header v-if="showTopbar" class="g3d-topbar">
      <div class="g3d-title">
        <span class="g3d-logo">3D</span>
        <div class="g3d-tx">
          <b>3D 五子棋</b>
          <i>电脑 {{ count.white }} 子 · {{ over ? '已结束' : (thinking ? '思考中…' : (turn === BLACK ? '轮到你走' : '轮到电脑')) }}</i>
        </div>
      </div>
      <div class="g3d-ops">
        <button class="g3d-op ghost" title="点击切换难度" @click="cycleDiff">{{ diffLabel }}</button>
        <button class="g3d-op ghost" :disabled="!canUndo" @click="undo">悔棋</button>
        <button class="g3d-op" @click="restart">重开</button>
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
import { BLACK, WHITE, EMPTY, SIZE, checkWinFrom, bestMove } from '@/utils/games/gomokuAI'
import AppIcon from '@/components/common/AppIcon.vue'
/* 样式由组件自己引：别的入口（棋类大厅直达）不经过 Games3DView，
   否则在线/直达场景会渲染成一堆无样式方块（v2.46.263 踩过） */
import '@/assets/styles/games3d.css'

defineProps({
  showTopbar: { type: Boolean, default: true },
})
defineEmits(['exit'])

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
  if (turn.value !== BLACK) { say('等电脑落子'); return }
  if (board.value[i]) return
  drop(i, BLACK)
}

function drop(i, color) {
  board.value[i] = color
  history.value.push(i)
  lastIdx.value = i
  sfx.stone()

  const line = checkWinFrom(board.value, i, color)
  if (line) {
    winLine.value = line
    winner.value = color
    over.value = true
    thinking.value = false
    sfx.win()
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
  if (turn.value === WHITE) scheduleAI()
}

function scheduleAI() {
  clearTimeout(aiTimer)
  thinking.value = true
  /* 先让浏览器把这一手画出来再算 —— AI 在主线程，同步搜索会把落子动画卡住 */
  aiTimer = setTimeout(() => {
    const i = bestMove(board.value, depth())
    thinking.value = false
    if (i < 0 || board.value[i]) return
    drop(i, WHITE)
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

/* 本地渲染探针用：直接摆一个局面，省得手点 20 手 */
defineExpose({ board, history, drop, restart })
</script>

<template>
  <div class="xf-wrap" :class="{ 'is-big': big }" :style="{ '--board-w': boardW + 'px', '--tilt': (big ? TILT_DEG : 0) + 'deg' }">
    <!-- ===== 辅栏：玩家条 + 状态 + 操作 + 邀请 ===== -->
    <div class="xf-side">
      <div class="xf-shell">
        <div class="xf-players">
          <div class="xf-player" :class="{ active: !over && turnIdx === 0 }">
            <span class="xf-dot" :class="dotClass(0)"></span>
            <div class="xf-player-txt">
              <b>{{ nameOf(0) }}</b>
              <i>{{ subOf(0) }}</i>
            </div>
          </div>
          <span class="xf-vs">⚔</span>
          <div class="xf-player" :class="{ active: !over && turnIdx === 1 }">
            <span class="xf-dot" :class="dotClass(1)"></span>
            <div class="xf-player-txt">
              <b>{{ nameOf(1) }}</b>
              <i>{{ subOf(1) }}</i>
            </div>
          </div>
        </div>

        <!-- 模式（页面已选则隐藏；房间激活时锁定） -->
        <div v-if="!bare" class="xf-modes" :class="{ locked: roomLocked }">
          <button
            v-for="m in MODES"
            :key="m.key"
            class="xf-mode"
            :class="{ on: mode === m.key }"
            :disabled="roomLocked && mode !== m.key"
            @click="setMode(m.key)"
          >{{ m.label }}</button>
        </div>

        <!-- 本地对局操作 -->
        <div v-if="mode !== 'online'" class="xf-status">
          <span v-if="over" class="xf-result">{{ resultText }}</span>
          <span v-else class="xf-quota">{{ flippedCount }} / {{ PIECE_N }} 已翻</span>
          <button class="xf-btn" @click="restart">重开</button>
          <button
            class="xf-btn"
            :disabled="!canUndoLocal"
            :title="undoPlan.plies === 2 ? '连对方那一手一起撤 2 手' : '撤掉自己刚走的那一手'"
            @click="undoLocal"
          >悔棋</button>
          <span class="xf-quota">{{ undoLabel }} · {{ history.length }} 手</span>
        </div>

        <!-- 在线横幅 -->
        <div v-if="mode === 'online' && gRoom.room.value" class="xf-banner" :class="'st-' + gRoom.status.value">
          <template v-if="gRoom.status.value === 'waiting'">
            <span class="xf-pulse"></span> 邀请已发给 {{ gRoom.opponentName.value }}，等待接受…
            <span class="xf-firstnote">{{ gRoom.room.value.black_name }} 先翻</span>
            <button class="xf-btn" @click="cancelInvite">取消邀请</button>
            <button class="xf-btn" @click="refreshRoom">刷新</button>
          </template>
          <template v-else-if="gRoom.status.value === 'playing'">
            <span>{{ gRoom.myTurn.value ? '轮到你翻子/走子' : '等对方行动…' }}</span>
            <button
              class="xf-btn"
              :disabled="!canUndoOnline"
              :title="undoPlan.plies === 2 ? '连对方那一手一起撤 2 手' : '撤掉自己刚走的那一手'"
              @click="undoOnline"
            >悔棋（余 {{ onlineUndoRemain }}）</button>
            <button class="xf-btn" @click="askExit">退出对局（认输）</button>
          </template>
          <template v-else-if="gRoom.status.value === 'finished'">
            <span class="xf-result">{{ onlineResultText }}</span>
            <button class="xf-btn primary" @click="reinviteSame">再来一局</button>
            <button class="xf-btn" @click="exitOnline">退出</button>
          </template>
        </div>
      </div>

      <!-- 在线邀请面板 -->
      <div v-if="mode === 'online' && !gRoom.room.value" class="xf-online">
        <div class="xf-online-title">🎯 在线邀请对战</div>
        <p class="xf-online-desc">按标准开局布局摆好 32 子后全部翻面洗牌，双方都看不到；先手翻出的颜色即为自己的阵营，明子按棋子自身的真实走法行动。</p>
        <div class="xf-online-row">
          <MemberPicker v-model="inviteeId" :members="families" placeholder="选择一位家人…" />
        </div>
        <div class="xf-online-row">
          <span class="xf-first-label">先翻：</span>
          <button class="xf-mode" :class="{ on: firstPick === 'me' }" @click="firstPick = 'me'">我先翻</button>
          <button class="xf-mode" :class="{ on: firstPick === 'other' }" @click="firstPick = 'other'">对方先翻</button>
        </div>
        <div class="xf-online-row">
          <button class="xf-btn primary" :disabled="!inviteeId || gRoom.joining.value" @click="invite">
            {{ gRoom.joining.value ? '创建中…' : '发出邀请' }}
          </button>
        </div>
        <p v-if="!families.length" class="xf-online-desc">家庭里还没有其他账号可以邀请。</p>
      </div>

      <p v-if="lockHint" class="xf-locknote"><span class="xf-dot-sm"></span>{{ lockHint }}</p>
    </div>

    <!-- ===== 主区：棋盘 ===== -->
    <div ref="mainEl" class="xf-main">
      <div class="xf-boardwrap">
        <div class="xf-board" :style="{ width: boardW + 'px', height: boardH + 'px' }">
          <!-- eslint-disable-next-line vue/no-v-html -- 本地常量 SVG，无外部输入 -->
          <svg class="xf-svg" :viewBox="`0 0 ${boardW} ${boardH}`" aria-hidden="true" v-html="svgMarkup"></svg>
          <button
            v-for="(p, i) in cells"
            :key="i"
            class="xf-cell"
            :class="{
              sel: selIdx === i,
              target: targets.includes(i),
              last: lastIdx === i,
              cap: !!p && p.up && p.c !== turnColor && targets.includes(i),
              incoming: !!anim && anim.to === i,
            }"
            :style="cellStyle(i)"
            :aria-label="ariaOf(i, p)"
            @click="tap(i)"
          >
            <span v-if="!p" class="xf-hole"></span>
            <span v-else-if="!p.up" class="xf-back" :class="{ fresh: flipIdx === i }">
              <i class="xf-back-mark">❖</i>
            </span>
            <span
              v-else
              class="xf-piece"
              :class="[p.c === 'r' ? 'red' : 'black', { fresh: flipIdx === i }]"
            >{{ glyph(p) }}</span>
          </button>

          <!-- 动效层：走子飞行 / 被吃子爆开 / 落点金环（纯视觉，pointer-events 全关） -->
          <template v-if="anim">
            <span :key="'fly' + anim.key" class="xf-fly" :style="flyStyle(anim)" @animationend="endAnim">
              <span class="xf-piece" :class="anim.color === 'r' ? 'red' : 'black'">{{ anim.glyph }}</span>
            </span>
            <template v-if="anim.capGlyph">
              <span :key="'dead' + anim.key" class="xf-fly xf-dead" :style="cellStyle(anim.to)">
                <span class="xf-piece" :class="anim.capColor === 'r' ? 'red' : 'black'">{{ anim.capGlyph }}</span>
              </span>
              <span :key="'boom' + anim.key" class="xf-boom" :style="cellStyle(anim.to)"></span>
            </template>
          </template>
        </div>
      </div>
    </div>

    <p class="xf-hint">
      <template v-if="mode === 'online'">在线模式 · 对方行动约 2 秒内自动出现</template>
      <template v-else>标准开局布局 · 32 子背面洗牌 · 先翻定色 · 明子按自身走法（车直行 · 马日字蹩腿 · 相田字可越河 · 士斜一格可越河 · 将帅兵卒四向一格 · 炮隔子吃）· 吃将即胜</template>
    </p>
  </div>
</template>

<script setup>
/** 中国象棋 · 翻棋（暗棋 / 揭棋式，自写，无外部依赖）。
 *
 * 规则（标准棋盘暗棋）：
 * - 标准 9×10 棋盘；**开局布局与明棋完全相同**（车马相士将士相马车 / 炮 / 兵卒共 32 点），
 *   32 枚棋子在这 32 个点内洗牌后**背面朝上**摆放 —— 只洗棋子，不洗位置。
 * - 每次行动 = 翻一枚暗子，或走一枚己方明子。
 * - **明子严格按棋子自身的走法行动与吃子**（引擎 relaxed 模式）：
 *   车走直线任意格；马走「日」字（蹩马腿生效）；相走「田」字（塞象眼生效，**可越河**）；
 *   士斜走一格且**可越河**；将/帅走一格且**可越河**；
 *   兵/卒按「单格位移」**上下左右各一格**（可横走、可后退，与将帅同款；河界在暗棋里整体不生效）；
 *   炮不吃子时同车，吃子时必须隔一个棋子（炮架）。
 * - 未翻开的暗子不能吃、也不能被吃，但会挡路、可当炮架。
 * - 吃掉对方的将/帅即胜；一方无子可动（无暗子可翻且无明子可走）即负。
 * 对手：双人同屏 / 单机（贪心 AI）/ 在线邀请（轮询同步，客户端权威）。
 * 在线：useGameRoom('xiangqi_flip')，开局布局由**房间号播种**生成，两端一致。
 */
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useGameRoom } from '@/composables/useGameRoom'
import MemberPicker from '@/components/games/MemberPicker.vue'
import { familyMembers } from '@/api/lifeExtra'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'
import { COLS, ROWS, GLYPH, VAL, BLACK, other, xOf, yOf, pieceTargets, flipDeal } from '@/utils/xiangqiRules'

const emit = defineEmits(['room-lock', 'room-unlock', 'exit'])
const props = defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
  joinRoomId: { type: Number, default: 0 },
  boardSize: { type: Number, default: 0 },
  big: { type: Boolean, default: false },
  gameKey: { type: String, default: 'xiangqi_flip' },
})

const MODES = [
  { key: 'pvp', label: '双人（同屏）' },
  { key: 'easy', label: '单机 · 电脑' },
  { key: 'online', label: '在线 · 邀请对战' },
]

const GAME_KEY = computed(() => props.gameKey || 'xiangqi_flip')
const N = COLS * ROWS
const PIECE_N = 32
const PAD = 22
const RED = 'r'

/* ---------- 开局：发牌交给引擎（在线用房间号当种子，两端一致） ----------
 * 位置固定为标准开局 32 点，只洗棋子（V2442-007）。见 xiangqiRules.flipDeal。 */
const shuffleDeal = flipDeal

/* ---------- 状态 ---------- */
const mode = ref(props.initialMode || 'easy')
const seed = ref(0)
const cells = ref(shuffleDeal(0))
const turnIdx = ref(0)          // 0=先手 1=后手
const firstColor = ref('')      // 先手翻出的颜色（'' = 尚未定色）
const selIdx = ref(-1)
const lastIdx = ref(-1)
const flipIdx = ref(-1)         // 刚翻开的格子（播放翻牌动效）
const over = ref(false)
const winnerColor = ref('')
const kingDead = ref('')        // 被吃掉的将/帅颜色（'' = 未分胜负）
const history = ref([])         // 行动事件（本地存档用）
const thinking = ref(false)
let timer = null

const cellPx = ref(44)
const mainEl = ref(null)
const boardW = computed(() => (COLS - 1) * cellPx.value + PAD * 2)
const boardH = computed(() => (ROWS - 1) * cellPx.value + PAD * 2)

// 放大时棋盘绕底边后仰 TILT_DEG 度（与 <style> 的 .xf-board 一致）；视觉高度 = 实际 × cos
const TILT_DEG = 26
const TILT_COS = Math.cos((TILT_DEG * Math.PI) / 180)

function measureCell() {
  const el = mainEl.value
  const availW = el?.clientWidth || 0
  const availH = el?.clientHeight || 0
  const capW = props.big ? 700 : 540
  let c = Math.floor((Math.min(availW || capW, capW) - PAD * 2) / (COLS - 1))
  if (availH > 240) {
    const usableH = props.big ? availH / TILT_COS : availH
    c = Math.min(c, Math.floor((usableH - PAD * 2 - 24) / (ROWS - 1)))
  }
  cellPx.value = Math.max(26, Math.min(props.big ? 70 : 50, c))
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
  for (let j = 0; j < ROWS; j++) ln(X(0), Y(j), X(8), Y(j))
  ln(X(0), Y(0), X(0), Y(9)); ln(X(8), Y(0), X(8), Y(9))
  for (let i = 1; i <= 7; i++) { ln(X(i), Y(0), X(i), Y(4)); ln(X(i), Y(5), X(i), Y(9)) }
  ln(X(3), Y(0), X(5), Y(2)); ln(X(5), Y(0), X(3), Y(2))
  ln(X(3), Y(7), X(5), Y(9)); ln(X(5), Y(7), X(3), Y(9))
  L.push(`<rect x="${X(0)}" y="${Y(0)}" width="${X(8) - X(0)}" height="${Y(9) - Y(0)}" fill="none" stroke-width="2"/>`)
  const fs = Math.max(13, Math.round(c * 0.5))
  const my = (Y(4) + Y(5)) / 2 + fs / 3
  L.push(`<text x="${X(2)}" y="${my}" text-anchor="middle" font-size="${fs}" class="xf-river">楚 河</text>`)
  L.push(`<text x="${X(6)}" y="${my}" text-anchor="middle" font-size="${fs}" class="xf-river">漢 界</text>`)
  return `<g>${L.join('')}</g>`
})

const flippedCount = computed(() => cells.value.filter(p => p && p.up).length)
const turnColor = computed(() => colorOf(turnIdx.value))
function colorOf(k) {
  if (!firstColor.value) return ''
  return k === 0 ? firstColor.value : other(firstColor.value)
}
function glyph(p) { return GLYPH[p.c][p.t] }
function ariaOf(i, p) {
  const s = `第${yOf(i) + 1}行第${xOf(i) + 1}列`
  if (!p) return `${s} 空`
  if (!p.up) return `${s} 未翻开的棋子`
  return `${s} ${p.c === RED ? '红' : '黑'}${glyph(p)}`
}

/* ---------- 走法：明子按真实走法（引擎 relaxed 模式） ----------
 * relaxed = 放开「九宫/河界」两处限制（士/象/将可越河、可出九宫；兵/卒四向一格可后退），
 * 走法形态一律保留：马蹩腿、相塞象眼、炮隔子吃 —— 与夜星口径一致（逐类实测见 docs/ISSUES.md V2442-007/010）。 */
/** 把明暗混合的棋盘映射成引擎认识的字符串盘（暗子也占位：挡路 / 当炮架） */
function stringBoard() {
  return cells.value.map(p => (p ? p.c + p.t : ''))
}
/** 明子的可走目标：真实走法，但暗子不可吃 */
function targetsOf(i) {
  const p = cells.value[i]
  if (!p || !p.up) return []
  const b = stringBoard()
  return pieceTargets(b, i, { relaxed: true }).filter((to) => {
    const q = cells.value[to]
    return !q || (q.up && q.c !== p.c)     // 只能吃「已翻开的敌子」
  })
}
const targets = computed(() => {
  if (selIdx.value < 0 || over.value) return []
  return targetsOf(selIdx.value)
})

/* ---------- 走子 / 吃子动效（纯视觉层，不改棋局逻辑） ----------
 * 翻子已有 xfFlipIn 翻牌动效；这里补走子飞行、被吃子爆开、落点金环三件套，
 * 让「谁走到了哪、谁被吃了」一眼可辨。棋盘状态立即落地，动画只是盖在上面的浮层。 */
const anim = ref(null)              // { key, from, to, color, glyph, capColor, capGlyph }
let animSeq = 0
let animTimer = null
function playAnim(from, to, cap) {
  const mover = cells.value[from]
  if (!mover) return
  anim.value = {
    key: ++animSeq, from, to,
    color: mover.c, glyph: glyph(mover),
    capColor: cap ? cap.c : '', capGlyph: cap ? glyph(cap) : '',
  }
  clearTimeout(animTimer)
  animTimer = setTimeout(() => { anim.value = null }, 700)   // 兜底：animationend 没到也要收摊
}
function endAnim() { clearTimeout(animTimer); anim.value = null }
function flyStyle(a) {
  const c = cellPx.value
  const r = Math.round(c * 0.44)
  return {
    left: PAD + xOf(a.from) * c - r + 'px',
    top: PAD + yOf(a.from) * c - r + 'px',
    width: r * 2 + 'px',
    height: r * 2 + 'px',
    fontSize: Math.round(r * 0.98) + 'px',
    '--dx': (xOf(a.to) - xOf(a.from)) * c + 'px',
    '--dy': (yOf(a.to) - yOf(a.from)) * c + 'px',
  }
}

/* ---------- 行动 ---------- */
function doFlip(i) {
  const p = cells.value[i]
  if (!p || p.up) return false
  p.up = true
  if (!firstColor.value) firstColor.value = p.c
  flipIdx.value = i
  lastIdx.value = -1
  // by 在定色之后取：先手翻出的颜色即先手阵营；c 供悔棋时重算 firstColor
  history.value.push({ flip: i, c: p.c, by: colorOf(turnIdx.value) })
  return true
}
function doMove(from, to) {
  const p = cells.value[from]
  const q = cells.value[to]
  if (!p || !p.up) return false
  playAnim(from, to, q)
  if (q && q.up && q.t === 'K') kingDead.value = q.c     // 吃将/帅 → 立即终局
  cells.value[to] = p
  cells.value[from] = null
  history.value.push({
    from, to, by: colorOf(turnIdx.value),
    cap: q ? q.t : '', capColor: q ? q.c : '',
  })
  lastIdx.value = to
  flipIdx.value = -1
  return true
}

function afterAction() {
  turnIdx.value = 1 - turnIdx.value
  selIdx.value = -1
  settle()
  if (mode.value === 'online' && over.value) reportFinish()
}
function settle() {
  if (kingDead.value) {
    over.value = true
    winnerColor.value = other(kingDead.value)
    return
  }
  if (!sideHasAction(turnIdx.value)) {
    const rival = sideHasAction(1 - turnIdx.value)
    over.value = true
    winnerColor.value = rival ? colorOf(1 - turnIdx.value) : ''
  }
}
function sideHasAction(k) {
  if (cells.value.some(p => p && !p.up)) return true    // 还有暗子 → 可翻
  const col = colorOf(k)
  if (!col) return true
  for (let i = 0; i < N; i++) {
    const p = cells.value[i]
    if (p && p.up && p.c === col && targetsOf(i).length) return true
  }
  return false
}

/* ---------- 悔棋（每方每局 3 次） ----------
 * 口径与象棋明棋 / 五子棋在线一致：最后一手是我下的（对方还没应）→ 撤 1 手；
 * 对方已经应了 → 连对方那一手一起撤 2 手（撤完回到我该走的局面）。
 * 一次悔棋只扣 1 次配额，与撤几手无关。
 * 双人同屏没有「我」，按「撤掉最后一手」算，配额记在被撤掉的那一方头上。
 * 翻棋的「颜色」由先手翻出的第一枚子决定，悔棋若撤掉了定色那一翻，firstColor 需一并回退。 */
const UNDO_QUOTA = 3
const undoLeft = ref({ r: UNDO_QUOTA, b: UNDO_QUOTA })
const onlineUndoUsed = ref({ r: 0, b: 0 })      // 在线：服务端不校验翻棋悔棋，配额在本地按事件流记
const myColor = computed(() => colorOf(mode.value === 'online' ? myIdx.value : 0))
const undoPlan = computed(() => {
  const h = history.value
  if (!h.length || over.value || thinking.value) return { plies: 0, color: '' }
  if (mode.value === 'pvp') {
    const color = h[h.length - 1].by || ''
    return { plies: color ? 1 : 0, color }
  }
  const color = myColor.value
  if (!color) return { plies: 0, color: '' }
  if (h[h.length - 1].by === color) return { plies: 1, color }
  if (h.length >= 2 && h[h.length - 2].by === color) return { plies: 2, color }
  return { plies: 0, color }
})
const undoLabel = computed(() => (
  mode.value === 'pvp'
    ? `红 ${undoLeft.value.r} · 黑 ${undoLeft.value.b}`
    : `悔棋余 ${undoLeft.value[myColor.value] ?? UNDO_QUOTA}`
))
const onlineUndoRemain = computed(() => Math.max(0,
  (undoLeft.value[myColor.value] ?? UNDO_QUOTA) - (onlineUndoUsed.value[myColor.value] || 0)))
const canUndoLocal = computed(() => (
  mode.value !== 'online' && undoPlan.value.plies > 0
  && (undoLeft.value[undoPlan.value.color] || 0) > 0
))
const canUndoOnline = computed(() => (
  onlinePlaying.value && !over.value && undoPlan.value.plies > 0
  && onlineUndoRemain.value > 0
))

/** 撤 n 手：逐手回滚（翻子重新扣回、走子连被吃子一起还原）并翻转轮次 */
function popHistory(n) {
  for (let k = 0; k < n; k++) {
    const h = history.value.pop()
    if (!h) break
    if (typeof h.flip === 'number') {
      const p = cells.value[h.flip]
      if (p) p.up = false
      lastIdx.value = -1
    } else {
      const b = cells.value.slice()
      b[h.from] = b[h.to]
      b[h.to] = h.capColor ? { c: h.capColor, t: h.cap, up: true } : null
      cells.value = b
      if (h.cap === 'K') kingDead.value = ''
      lastIdx.value = h.from
    }
    turnIdx.value = 1 - turnIdx.value
  }
  const firstFlip = history.value.find(x => typeof x.flip === 'number')
  firstColor.value = firstFlip ? firstFlip.c : ''
  anim.value = null
  flipIdx.value = -1
  selIdx.value = -1
  over.value = false
  winnerColor.value = ''
  settle()
}
function undoLocal() {
  const { plies, color } = undoPlan.value
  if (mode.value === 'online' || !plies) return
  if ((undoLeft.value[color] || 0) <= 0) {
    ElMessage.info(`「${color === RED ? '红' : '黑'}方」本局悔棋次数已用完`)
    return
  }
  popHistory(plies)
  undoLeft.value[color] -= 1
}
/** 在线悔棋：把 `{undo:N}` 当普通动作上报（翻棋是客户端权威，服务端只记事件流），
 *  对方在下一轮轮询里按同一套重放规则弹出 N 手，两端棋盘保持一致。 */
function undoOnline() {
  if (!canUndoOnline.value) return
  const plies = undoPlan.value.plies
  const color = myColor.value
  popHistory(plies)
  onlineUndoUsed.value[color] += 1
  gRoom.send({ undo: plies }).catch(() => { /* 下轮轮询以服务端事件流为准 */ })
  // 悔棋后必然回到「我该走」的局面（撤 1 手或连对方那手一起撤 2 手，末手都归对方）。
  // 乐观翻转 my_turn，免去最长 1.6s 的轮询空窗把棋盘锁住。
  if (gRoom.room.value) gRoom.room.value.my_turn = true
}

/* ---------- 交互 ---------- */
const localAiIdx = 1
const aiTurn = computed(() => mode.value === 'easy' && turnIdx.value === localAiIdx)
const boardLocked = computed(() => {
  if (over.value) return true
  if (mode.value === 'online') return !onlineMyTurn.value
  return aiTurn.value || thinking.value
})

function tap(i) {
  if (boardLocked.value) return
  // 「落点」必须先判：明子绝大多数走法是**走到空格**，而下面的空格分支是「取消选择」。
  // 先走空格分支会把落点吃掉 → 明子只能吃子、永远走不动，整局就卡住了。
  if (selIdx.value >= 0 && targets.value.includes(i)) {
    act({ from: selIdx.value, to: i })
    return
  }
  const p = cells.value[i]
  if (!p) { selIdx.value = -1; return }
  if (!p.up) { act({ flip: i }); return }
  if (p.c === turnColor.value) selIdx.value = i
  else selIdx.value = -1
}

/** 统一入口：本地应用 + （在线时）上报 */
function act(a) {
  const ok = typeof a.flip === 'number' ? doFlip(a.flip) : doMove(a.from, a.to)
  if (!ok) return
  if (mode.value === 'online') gRoom.send(a)
  afterAction()
  if (!over.value) maybeScheduleAI()
}

function scheduleAI() {
  thinking.value = true
  clearTimeout(timer)
  timer = setTimeout(() => {
    const a = aiChoose()
    thinking.value = false
    if (!a) return
    const ok = typeof a.flip === 'number' ? doFlip(a.flip) : doMove(a.from, a.to)
    if (ok) afterAction()
  }, 320)
}
/** AI 行动的唯一入口：只在「本地单机 + 确实轮到 AI」时才动。
 *  修 V2442-006：setMode('easy') 原先无条件 scheduleAI()，
 *  切换模式时 AI 会抢在玩家（先手）之前翻子。 */
function maybeScheduleAI() {
  if (mode.value !== 'easy') return
  if (thinking.value || over.value) return
  if (!aiTurn.value) return
  scheduleAI()
}
function aiChoose() {
  const col = colorOf(localAiIdx)
  const caps = [], moves = [], downs = []
  for (let i = 0; i < N; i++) {
    const p = cells.value[i]
    if (!p) continue
    if (!p.up) { downs.push(i); continue }
    if (p.c !== col) continue
    for (const to of targetsOf(i)) {
      const q = cells.value[to]
      if (q) caps.push({ from: i, to, v: VAL[q.t] || 0 })
      else moves.push({ from: i, to })
    }
  }
  if (caps.length) {
    caps.sort((a, b) => b.v - a.v)
    const pool = caps.filter(c => c.v === caps[0].v)
    const c = pool[(Math.random() * pool.length) | 0]
    return { from: c.from, to: c.to }
  }
  if (downs.length && (Math.random() < 0.5 || !moves.length)) return { flip: downs[(Math.random() * downs.length) | 0] }
  if (moves.length) return moves[(Math.random() * moves.length) | 0]
  if (downs.length) return { flip: downs[(Math.random() * downs.length) | 0] }
  return null
}

/* ---------- 在线对战 ---------- */
const families = ref([])
const inviteeId = ref(null)
const firstPick = ref('me')
const onlineWinner = ref('')
const lastInviteeName = ref('')
let exited = false
let finishedReported = false

function onRemoteMove(action, userId) {
  if (action?.undo) {
    // 对方（或恢复对局时重放的自己）撤棋：两端按同一套规则弹出 N 手
    const plies = action.undo === 2 ? 2 : 1
    popHistory(plies)
    const mine = Number(userId) === Number(gRoom.myUserId.value)
    const c = mine ? myColor.value : (myColor.value ? other(myColor.value) : '')
    if (c === RED || c === BLACK) onlineUndoUsed.value[c] += 1
    return
  }
  if (typeof action?.flip === 'number') doFlip(action.flip)
  else if (typeof action?.from === 'number' && typeof action?.to === 'number') doMove(action.from, action.to)
  else return
  turnIdx.value = 1 - turnIdx.value
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
  gRoom.finish(winnerColor.value && winnerColor.value !== mine ? Number(oppId) : (winnerColor.value ? uid : 0))
    .catch(() => { /* 对方可能已上报终局 */ })
}

function seatName(k) {
  if (mode.value === 'online' && gRoom.room.value) {
    return myIdx.value === k ? '你' : (gRoom.opponentName.value || '对方')
  }
  if (mode.value === 'pvp') return k === 0 ? '先手' : '后手'
  return k === 0 ? '你' : '电脑'
}
function nameOf(k) {
  const col = colorOf(k)
  return `${seatName(k)}${col ? `（${col === RED ? '红' : '黑'}）` : ''}`
}
function subOf(k) {
  if (over.value) return ''
  if (!firstColor.value) return k === 0 ? '请翻子定色' : '待翻'
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
  return winnerColor.value === colorOf(localAiIdx) ? '🎉 你赢了' : '电脑赢了，再来'
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
    if (r?.id) resetWithSeed(r.id)          // 开局布局由房间号播种 → 两端一致
    ElMessage.success(`邀请已发出（${firstPick.value === 'me' ? '你' : lastInviteeName.value || '对方'}先翻），等对方接受`)
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
      if (r?.id) resetWithSeed(r.id)
      ElMessage.success(`新对局已发出（${firstPick.value === 'me' ? '你' : '对方'}先翻）`)
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

/** 在线：以房间号为种子重铺牌面（两端完全一致） */
function resetWithSeed(id) {
  seed.value = id
  cells.value = shuffleDeal(id)
  turnIdx.value = 0
  firstColor.value = ''
  selIdx.value = -1
  lastIdx.value = -1
  flipIdx.value = -1
  over.value = false
  winnerColor.value = ''
  kingDead.value = ''
  history.value = []
  thinking.value = false
  onlineWinner.value = ''
  finishedReported = false
  anim.value = null
  undoLeft.value = { r: UNDO_QUOTA, b: UNDO_QUOTA }
  onlineUndoUsed.value = { r: 0, b: 0 }
}
async function resumeMine() {
  try {
    const res = await (await import('@/api/gameRooms')).gameRoomsApi.mine()
    const active = (res?.data?.list || []).find(x => x.game === GAME_KEY.value && ['waiting', 'playing'].includes(x.status))
    if (!active) return
    mode.value = 'online'
    resetWithSeed(active.id)
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
      summary: `${mode.value === 'pvp' ? '双人同屏' : '单机'} · 已翻 ${flippedCount.value} 子`,
      cells: cells.value,
      seed: seed.value,
      turnIdx: turnIdx.value,
      firstColor: firstColor.value,
      history: history.value,
      lastIdx: lastIdx.value,
    })
  }, 400)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !Array.isArray(s.cells) || s.cells.length !== N || s.mode === 'online') return false
  if (s.mode) mode.value = s.mode
  seed.value = s.seed || 0
  cells.value = s.cells
  turnIdx.value = s.turnIdx || 0
  firstColor.value = s.firstColor || ''
  history.value = s.history || []
  lastIdx.value = s.lastIdx ?? -1
  over.value = false
  winnerColor.value = ''
  kingDead.value = ''
  settle()
  return true
}
watch([cells, over], saveLocal, { deep: true })

function clearLocal() {
  clearTimeout(timer)
  seed.value = 0
  cells.value = shuffleDeal(0)
  turnIdx.value = 0
  firstColor.value = ''
  selIdx.value = -1
  lastIdx.value = -1
  flipIdx.value = -1
  over.value = false
  winnerColor.value = ''
  kingDead.value = ''
  history.value = []
  thinking.value = false
  onlineWinner.value = ''
  finishedReported = false
  anim.value = null
  undoLeft.value = { r: UNDO_QUOTA, b: UNDO_QUOTA }
  onlineUndoUsed.value = { r: 0, b: 0 }
}

function setMode(k) {
  if (roomLocked.value && k !== mode.value) { ElMessage.warning('对局进行中 —— 先点「退出对局」再切换模式'); return }
  mode.value = k
  clearLocal()
  gRoom.reset()
  if (k === 'online') loadFamilies()
  else if (k === 'easy') maybeScheduleAI()
}
function restart() {
  if (mode.value === 'online') { ElMessage.info('在线模式请用「再来一局」或「退出对局」'); return }
  clearTimeout(saveTimer)
  clearGame(SAVE_KEY)
  clearLocal()
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
    resetWithSeed(props.joinRoomId)
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
  clearTimeout(timer); clearTimeout(saveTimer); clearTimeout(animTimer)
  if (roomActive.value) gRoom.leaveOnUnload()
})
</script>

<style scoped>
.xf-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.xf-side { width: var(--board-w, 100%); max-width: 100%; display: flex; flex-direction: column; gap: 10px; }
.xf-main { width: 100%; display: flex; justify-content: center; }
/* 透视容器：放大后棋盘绕底边后仰平躺，透视更强、立体感更足 */
.xf-boardwrap {
  display: flex; justify-content: center;
  perspective: 1300px; perspective-origin: 50% 30%;
}

/* ===== 玩家条 ===== */
.xf-shell {
  border-radius: 18px; padding: 12px 14px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  background: var(--color-bg-glass, rgba(255,255,255,.6));
  backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  box-shadow: var(--shadow-glass, 0 8px 24px rgba(20,30,40,.08));
  display: flex; flex-direction: column; gap: 10px;
}
.xf-players { display: flex; align-items: center; justify-content: center; gap: 14px; }
.xf-player { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 12px; transition: all .2s; }
.xf-player.active { background: var(--yq-gold-faint, rgba(199,169,107,.16)); box-shadow: inset 0 0 0 1px var(--yq-gold, #c7a96b); }
.xf-dot { width: 14px; height: 14px; border-radius: 50%; flex: none; }
.xf-dot.red { background: radial-gradient(circle at 34% 30%, #f6b3a5, #c0392b 70%); }
.xf-dot.black { background: radial-gradient(circle at 34% 30%, #7b8494, #1f2630 70%); }
.xf-dot.none { background: transparent; box-shadow: inset 0 0 0 1.5px var(--dp-line, rgba(0,0,0,.25)); }
.xf-player-txt { display: flex; flex-direction: column; line-height: 1.25; }
.xf-player-txt b { font-size: 13px; color: var(--dp-text, #18202a); }
.xf-player-txt i { font-style: normal; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.xf-vs { color: var(--yq-gold, #c7a96b); font-size: 13px; }

.xf-modes { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.xf-mode {
  padding: 6px 12px; border-radius: 999px; font-size: 12px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: transparent;
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.xf-mode:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.xf-mode.on {
  background: var(--yq-gold-faint, rgba(199,169,107,.16));
  border-color: var(--yq-gold, #c7a96b);
  color: var(--yq-gold-deep, var(--yq-gold, #c7a96b));
  box-shadow: 0 6px 18px var(--yq-gold-glow, rgba(199,169,107,.16));
}
.xf-mode:disabled { opacity: .4; cursor: not-allowed; }

.xf-status { display: flex; align-items: center; gap: 8px; justify-content: center; flex-wrap: wrap; }
.xf-btn {
  padding: 6px 13px; border-radius: 999px; font-size: 12.5px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.xf-btn:hover:not(:disabled) { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.xf-btn:disabled { opacity: .4; cursor: not-allowed; }
.xf-btn.primary { background: var(--yq-gold, #c7a96b); color: #fff; border-color: transparent; }
.xf-quota { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.xf-result { font-size: 13px; font-weight: 600; color: var(--yq-gold-deep, var(--yq-gold, #c7a96b)); }

.xf-banner {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center;
  font-size: 12.5px; color: var(--dp-text2, #45505b);
}
.xf-firstnote { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.xf-pulse {
  width: 8px; height: 8px; border-radius: 50%; background: var(--yq-gold, #c7a96b);
  animation: xfPulse 1.4s ease-in-out infinite;
}
@keyframes xfPulse { 0%, 100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1.15); } }

.xf-online {
  border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 10px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  background: var(--color-bg-glass, rgba(255,255,255,.5));
}
.xf-online-title { font-size: 13.5px; font-weight: 600; color: var(--dp-text, #18202a); }
.xf-online-desc { font-size: 12px; line-height: 1.7; margin: 0; color: var(--dp-text2, #8a8f98); }
.xf-online-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.xf-first-label { font-size: 12px; color: var(--dp-text2, #8a8f98); }
.xf-locknote {
  margin: 0; font-size: 12px; color: var(--dp-text2, #8a8f98);
  display: flex; align-items: center; gap: 6px; justify-content: center;
}
.xf-dot-sm { width: 6px; height: 6px; border-radius: 50%; background: var(--yq-gold, #c7a96b); }

/* ===== 棋盘：青玉 / 墨玉盘面 + 立体盘厚（与象棋明棋同一套材质语言） ===== */
.xf-board {
  position: relative; border-radius: 16px;
  background:
    radial-gradient(135% 100% at 50% -12%, rgba(255,255,255,.72), rgba(255,255,255,0) 58%),
    repeating-linear-gradient(92deg, rgba(58,96,88,.05) 0 1px, rgba(0,0,0,0) 1px 6px),
    linear-gradient(158deg, #e9f1ea 0%, #d2e1d7 46%, #b6ccc0 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.7),
    inset 0 0 0 1px rgba(96,124,108,.35),
    inset 0 -10px 22px -12px rgba(20,44,38,.4),
    0 7px 0 -1px #9db3a6,
    0 13px 0 -2px #7b9287,
    0 19px 0 -4px #5a6e65,
    0 36px 44px -20px rgba(20, 34, 30, .55);
  transform-origin: 50% 100%;
  transform: rotateX(var(--tilt, 0deg));
  transition: transform .3s cubic-bezier(.4, .1, .2, 1);
  will-change: transform;
}
.xf-wrap.is-big .xf-board {
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.7),
    inset 0 0 0 1px rgba(96,124,108,.35),
    inset 0 -12px 26px -12px rgba(20,44,38,.42),
    0 9px 0 -1px #9db3a6,
    0 17px 0 -2px #7b9287,
    0 25px 0 -5px #556a61,
    0 54px 62px -26px rgba(18, 30, 27, .62);
}
html[data-theme="night"] .xf-board {
  background:
    radial-gradient(135% 100% at 50% -12%, rgba(127,168,163,.2), rgba(0,0,0,0) 62%),
    repeating-linear-gradient(92deg, rgba(255,255,255,.025) 0 1px, rgba(0,0,0,0) 1px 6px),
    linear-gradient(158deg, #223130 0%, #17211f 48%, #0c1211 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.12),
    inset 0 0 0 1px rgba(199,169,107,.34),
    inset 0 -12px 26px -12px rgba(0,0,0,.7),
    0 7px 0 -1px #101a18,
    0 13px 0 -2px #0b1312,
    0 19px 0 -4px #070d0c,
    0 36px 46px -20px rgba(0,0,0,.85);
}
html[data-theme="night"] .xf-wrap.is-big .xf-board {
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.12),
    inset 0 0 0 1px rgba(199,169,107,.34),
    inset 0 -14px 30px -12px rgba(0,0,0,.72),
    0 9px 0 -1px #101a18,
    0 17px 0 -2px #0b1312,
    0 25px 0 -5px #060b0a,
    0 54px 64px -26px rgba(0,0,0,.9);
}
.xf-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.xf-svg :deep(line), .xf-svg :deep(rect) { stroke: rgba(146, 114, 52, .62); }
html[data-theme="night"] .xf-svg :deep(line),
html[data-theme="night"] .xf-svg :deep(rect) { stroke: rgba(199, 169, 107, .6); }
.xf-svg :deep(text.xf-river) {
  fill: rgba(138, 106, 46, .7); font-weight: 600; letter-spacing: .18em;
  font-family: "Songti SC", "STSong", "SimSun", serif;
}
html[data-theme="night"] .xf-svg :deep(text.xf-river) { fill: rgba(199, 169, 107, .66); }

.xf-cell {
  position: absolute; border-radius: 50%; padding: 0; cursor: pointer;
  background: transparent; border: none; display: grid; place-items: center;
  transition: box-shadow .16s, transform .16s;
}
.xf-hole { width: 100%; height: 100%; border-radius: 50%; }

/* 背面：玉色暗纹牌背（与正面水晶同一材质语言） */
.xf-back {
  position: relative;
  width: 100%; height: 100%; border-radius: 50%; display: grid; place-items: center;
  background:
    radial-gradient(circle at 32% 26%, rgba(255,255,255,.9) 0 12%, transparent 34%),
    repeating-linear-gradient(45deg, rgba(96,124,108,.1) 0 3px, transparent 3px 7px),
    linear-gradient(150deg, rgba(214,232,222,.92), rgba(170,198,184,.86) 52%, rgba(132,166,152,.9));
  box-shadow:
    0 3px 8px rgba(24, 44, 38, .3),
    inset 0 0 0 1.4px rgba(255,255,255,.55),
    inset -2px -3px 8px rgba(40, 70, 60, .26);
}
html[data-theme="night"] .xf-back {
  background:
    radial-gradient(circle at 32% 26%, rgba(255,255,255,.3) 0 12%, transparent 34%),
    repeating-linear-gradient(45deg, rgba(199,169,107,.12) 0 3px, transparent 3px 7px),
    linear-gradient(150deg, rgba(58,84,78,.9), rgba(34,52,48,.88) 52%, rgba(20,32,30,.92));
  box-shadow:
    0 3px 8px rgba(0,0,0,.6),
    inset 0 0 0 1.4px rgba(199,169,107,.42),
    inset -2px -3px 8px rgba(0,0,0,.35);
}
.xf-back-mark { font-style: normal; font-size: .62em; color: rgba(52, 88, 76, .62); }
html[data-theme="night"] .xf-back-mark { color: rgba(214, 190, 140, .62); }
.xf-back.fresh { animation: xfFlipIn .42s ease-out; }

/* 正面：棋子圆牌（透明水晶质感，与象棋明棋同一套语言） */
.xf-piece {
  position: relative;
  width: 100%; height: 100%; border-radius: 50%; display: grid; place-items: center;
  font-family: "Songti SC", "STSong", "SimSun", serif; font-weight: 700; line-height: 1;
  user-select: none;
  background:
    radial-gradient(circle at 32% 26%, rgba(255,255,255,.88) 0 12%, transparent 30%),
    radial-gradient(circle at 68% 78%, rgba(255,255,255,.26) 0 12%, transparent 34%),
    radial-gradient(circle at 50% 46%, rgba(255,255,255,.16) 0 58%, transparent 72%),
    linear-gradient(150deg, rgba(176,208,224,.6), rgba(236,228,210,.42) 46%, rgba(150,178,204,.56));
  box-shadow:
    inset 0 0 0 1.6px rgba(255,255,255,.6),
    inset 2px 3px 7px rgba(255,255,255,.55),
    inset -3px -4px 10px rgba(96,122,156,.42),
    0 4px 10px rgba(30, 48, 74, .34);
}
.xf-piece::before {
  content: ''; position: absolute; inset: 0; border-radius: 50%;
  box-shadow:
    inset 0 0 0 2px rgba(255,255,255,.45),
    inset 0 0 0 3.6px rgba(64,96,138,.3),
    inset 0 0 10px rgba(255,255,255,.18);
}
.xf-piece::after {
  content: ''; position: absolute; inset: 22%; border-radius: 50%;
  box-shadow: inset 0 0 8px rgba(255,255,255,.34), inset 0 0 0 1px rgba(255,255,255,.2);
}
.xf-piece.red {
  color: #9e1a14;
  text-shadow: 0 1px 2px rgba(120, 20, 12, .38), 0 0 7px rgba(255, 170, 158, .5);
}
.xf-piece.black {
  color: #0a0f16;
  text-shadow: 0 1px 2px rgba(6, 10, 16, .42), 0 0 7px rgba(210, 224, 250, .45);
}
html[data-theme="night"] .xf-piece {
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
html[data-theme="night"] .xf-piece::before {
  box-shadow:
    inset 0 0 0 2px rgba(255,255,255,.24),
    inset 0 0 0 3.6px rgba(130, 172, 216, .3),
    inset 0 0 10px rgba(255,255,255,.1);
}
html[data-theme="night"] .xf-piece.red { color: #ffb0a6; text-shadow: 0 1px 3px rgba(90, 14, 8, .62), 0 0 9px rgba(255,130,118,.42); }
html[data-theme="night"] .xf-piece.black { color: #f2f6fc; text-shadow: 0 1px 3px rgba(0,0,0,.7), 0 0 9px rgba(200,220,255,.4); }
.xf-piece.fresh { animation: xfFlipIn .42s ease-out; }
@keyframes xfFlipIn {
  from { transform: rotateY(90deg) scale(.86); opacity: .35; }
  to { transform: rotateY(0deg) scale(1); opacity: 1; }
}

/* ---------- 走子 / 吃子动效 ---------- */
/* 飞行体：起点由内联 left/top 定位，位移交给 --dx/--dy（中段略微上抛，像被拎起来走） */
.xf-fly {
  position: absolute; z-index: 7; pointer-events: none;
  animation: xfFly .32s cubic-bezier(.34, .72, .26, 1) forwards;
}
@keyframes xfFly {
  0% { transform: translate(0, 0) scale(1); }
  55% { transform: translate(calc(var(--dx) * .58), calc(var(--dy) * .58 - 5px)) scale(1.12); }
  100% { transform: translate(var(--dx), var(--dy)) scale(1); }
}
/* 被吃子：原地炸开淡出（本类写在 .xf-fly 之后，用来覆盖它的 animation） */
.xf-dead { z-index: 6; animation: xfDead .32s ease-in forwards; }
@keyframes xfDead {
  0% { opacity: 1; transform: scale(1); }
  30% { opacity: 1; transform: scale(1.18) rotate(-5deg); }
  100% { opacity: 0; transform: scale(.4) rotate(22deg); }
}
/* 落点冲击环 */
.xf-boom {
  position: absolute; z-index: 6; pointer-events: none; border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(199, 169, 107, .95), 0 0 20px rgba(199, 169, 107, .6);
  animation: xfBoom .34s ease-out forwards;
}
@keyframes xfBoom {
  0% { transform: scale(.34); opacity: 1; }
  100% { transform: scale(2.15); opacity: 0; }
}
/* 飞行期间先藏住落点上的真子，落定那一刻才显形（否则一子两影） */
.xf-cell.incoming .xf-piece { opacity: 0; }

.xf-cell.sel { box-shadow: 0 0 0 3px var(--yq-gold, #c7a96b), 0 0 14px rgba(199,169,107,.55); }
.xf-cell.last { box-shadow: 0 0 0 2px rgba(80, 140, 200, .75); }
.xf-cell.target { box-shadow: inset 0 0 0 3px rgba(199, 169, 107, .8); }
.xf-cell.target::after {
  content: ''; position: absolute; width: 26%; height: 26%; border-radius: 50%;
  background: var(--yq-gold, #c7a96b); opacity: .8;
}
.xf-cell.target:has(.xf-piece)::after, .xf-cell.target:has(.xf-back)::after { display: none; }

.xf-hint {
  margin: 0; font-size: 12px; line-height: 1.7; text-align: center;
  color: var(--dp-text3, #8a8f98);
}

/* ===== 放大：左主棋盘 + 右辅栏 ===== */
.xf-wrap.is-big {
  display: grid; grid-template-columns: minmax(0, 1fr) 330px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px 22px; width: 100%; height: 100%; min-height: 0;
}
.xf-wrap.is-big .xf-side {
  grid-column: 2; grid-row: 1 / span 2; width: 100%; max-height: 100%;
  overflow-y: auto; align-self: start;
}
.xf-wrap.is-big .xf-main {
  grid-column: 1; grid-row: 1; width: 100%; height: 100%; min-height: 0; align-items: center;
}
.xf-wrap.is-big .xf-hint { grid-column: 1; grid-row: 2; }
@media (max-width: 900px) {
  .xf-wrap.is-big { display: flex; flex-direction: column; }
  .xf-wrap.is-big .xf-side, .xf-wrap.is-big .xf-main { grid-column: auto; grid-row: auto; max-height: none; }
}
/* 系统开了「减少动态效果」时让动画瞬间结束（animationend 立刻触发 → 落点子即时显形，不留空档） */
@media (prefers-reduced-motion: reduce) {
  .xf-fly, .xf-dead, .xf-boom { animation-duration: .01ms; }
}
</style>
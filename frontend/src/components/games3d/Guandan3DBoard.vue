<template>
  <div class="g3d-board">
    <!-- 顶栏 -->
    <header class="g3d-topbar">
      <div class="g3d-title">
        <span class="g3d-logo">3D</span>
        <div class="g3d-tx">
          <b>3D 掼蛋</b>
          <i>第 {{ roundNo }} 局 · 我方 {{ G.levelText(myLevel) }} / 对方 {{ G.levelText(oppLevel) }}</i>
        </div>
      </div>
      <div class="g3d-ops">
        <button class="g3d-op ghost" @click="$emit('exit')">返回</button>
        <button class="g3d-op" @click="restart">重新开始</button>
      </div>
    </header>

    <!-- 3D 舞台 -->
    <div class="g3d-stage">
      <div class="g3d-world" :style="{ transform: worldTF }">
        <!-- 牌桌 -->
        <div class="gt3-table" :style="boxVars(660, 660, 30)">
          <div class="gt3-face gt3-top">
            <div class="gt3-felt">
              <div class="gt3-woven"></div>
              <div class="gt3-vignette"></div>
              <div class="gt3-compass">
                <span class="cw cw-n">北</span><span class="cw cw-e">东</span>
                <span class="cw cw-s">南</span><span class="cw cw-w">西</span>
                <span class="cw-core">中</span>
              </div>
            </div>
          </div>
          <div class="gt3-face gt3-bottom"></div>
          <div class="gt3-face gt3-left"></div>
          <div class="gt3-face gt3-right"></div>
          <div class="gt3-face gt3-front"></div>
          <div class="gt3-face gt3-back"></div>
        </div>

        <!-- 座位铭牌：头像 / 名字 / 积分 分栏 -->
        <div
          v-for="s in SEATS"
          :key="s"
          class="gt3-seat"
          :class="{ 'is-turn': isTurn(s) }"
          :style="seatTF(SEAT_SLOT[screenPos(s, 0)])"
        >
          <div class="gt3-ava" :style="{ background: seatColors[s] }"><AppIcon :icon="seatAvatar(s)" /></div>
          <div class="gt3-meta">
            <b>{{ seatName(s) }}</b>
            <i :class="{ turn: isTurn(s) }">{{ seatSub(s) }}</i>
          </div>
          <div class="gt3-score" :class="{ 'is-you': s === 0 }">
            <span class="snum">{{ G.levelText(scores[s]) }}</span><span class="slbl">级</span>
          </div>
        </div>

        <!-- 对手牌背：1 右(E) / 2 上(N) / 3 左(W)，各 5 张 -->
        <div v-for="o in OPP" :key="'opp' + o.seat">
          <div
            v-for="k in 5"
            :key="o.side + k"
            class="pc3d gd-back"
            :style="pieceBox(true, 46, 64, 12, oppTF(o.side, k - 1, 5), k - 1, false, false)"
          >
            <div class="pc-face pc-front card-back"></div>
            <div class="pc-face pc-back card-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </div>

        <!-- 我的手牌（座位 0） -->
        <div
          v-for="(c, i) in hands[0]"
          :key="c.id"
          class="pc3d gd-hand"
          :class="{ sel: sel.includes(c.id), wild: isWildCard(c) }"
          :style="pieceBox(dealt, 46, 64, 11, handTF(i, hands[0].length, false, 324, sel.includes(c.id) ? 31 : 0), i, true, false)"
          @click="toggleSel(c)"
        >
          <div class="pc-face pc-front card-front" :class="isRed(c) ? 'red' : 'blk'">
            <span class="cf-rank">{{ cardText(c) }}</span>
            <span class="cf-suit">{{ cardSuit(c) }}</span>
          </div>
          <div class="pc-face pc-back card-back"></div>
          <div class="pc-face pc-top mj-ivory"></div>
          <div class="pc-face pc-bottom mj-ivory"></div>
          <div class="pc-face pc-left mj-edge"></div>
          <div class="pc-face pc-right mj-edge"></div>
        </div>

        <!-- 中央出牌区：每个已出座位显示其最新一手，按屏幕位给原点偏移 -->
        <template v-for="seat in throwSeats" :key="'gc' + seat">
          <div
            v-for="(c, i) in seatThrows[seat].cards"
            :key="c.id"
            class="pc3d gd-hand mj-center"
            :class="{ wild: isWildCard(c) }"
            :style="pieceBox(dealt, 46, 64, 11, centerTF(i, 40, CENTER_OFF[screenPos(seat, 0)]), i, false, false)"
          >
            <div class="pc-face pc-front card-front" :class="isRed(c) ? 'red' : 'blk'">
              <span class="cf-rank">{{ cardText(c) }}</span>
              <span class="cf-suit">{{ cardSuit(c) }}</span>
            </div>
            <div class="pc-face pc-back card-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </template>
      </div>
    </div>

    <!-- 操作条 -->
    <div class="g3d-ctl">
      <button class="g3d-btn ghost" :disabled="!canAct" @click="doHint">提示</button>
      <button class="g3d-btn" :disabled="!canAct || !target" @click="doPass">不要</button>
      <button class="g3d-btn primary" :disabled="!canAct || !canPlay" @click="doPlay">出牌</button>
    </div>

    <!-- 提示条 -->
    <div v-if="toast" class="g3d-toast">{{ toast }}</div>

    <!-- 结算浮层 -->
    <div v-if="phase === 'settled'" class="g3d-over">
      <div class="ov-card">
        <h2>{{ iWon ? '本局获胜' : '本局结束' }}</h2>
        <p>名次：{{ roundResult.order.map(seatName).join(' > ') }}</p>
        <p>升 {{ roundResult.up }} 级 · {{ matchOver ? '整场结束（打过 A）' : '继续下一局' }}</p>
        <div class="ov-acts">
          <button class="g3d-btn ghost" @click="restart">重新开始</button>
          <button class="g3d-btn primary" @click="nextRound">再来一局</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 3D 掼蛋：复用 2D 单机对局循环（components/games/GuandanBoard.vue solo 分支）+ 规则引擎 utils/games/guandan.js。
   人类固定坐座位 0（HUMAN_SEATS=[0]），1/2/3 为 AI；无任何 online 分支。 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import * as G from '@/utils/games/guandan.js'
import {
  VIEW_RX, boxVars, pieceBox, handTF, oppTF, centerTF, seatTF, SEAT_SLOT, screenPos,
} from '@/components/games3d/use3dTable.js'
import AppIcon from '@/components/common/AppIcon.vue'

defineEmits(['exit'])

/* ---------- 常量 ---------- */
const HUMAN_SEATS = [0]
const SEATS = [0, 1, 2, 3]
const AI_AVATARS = { 1: '🐯', 2: '🦊', 3: '🐼' }
const seatColors = [
  'linear-gradient(160deg,#e9c877,#a9812f)', // 0 你
  'linear-gradient(160deg,#67a,#345)',       // 1 右家
  'linear-gradient(160deg,#3a7,#276)',       // 2 对家
  'linear-gradient(160deg,#a76,#743)',       // 3 左家
]
/** 对手（座位 → 屏幕朝向）：1 右 E / 2 上 N / 3 左 W */
const OPP = [
  { seat: 1, side: 'E' },
  { seat: 2, side: 'N' },
  { seat: 3, side: 'W' },
]
/** 中央出牌区按屏幕位（0下 1右 2上 3左）的原点偏移 */
const CENTER_OFF = [
  { x: 0, y: 110 }, { x: 150, y: 0 }, { x: 0, y: -110 }, { x: -150, y: 0 },
]
const worldTF = `rotateX(${VIEW_RX}deg) scale3d(.94,.94,.94)`

const AI_THINK_MIN = 3000
const AI_THINK_MAX = 3500

/* ---------- 状态 ---------- */
const teamLevel = ref([2, 2])
const roundLevel = ref(2)
const roundNo = ref(1)
const hands = ref([[], [], [], []])
const turn = ref(0)
const target = ref(null)        // { seat, cards, pattern }
const seatThrows = ref({})
const passCount = ref(0)
const finished = ref([])
const phase = ref('playing')    // playing | settled
const sel = ref([])
const toast = ref('')
const history = ref([])         // 结构化出牌记录（最新在前）
const roundResult = ref({ up: 0, winTeam: 0, order: [] })
const matchOver = ref(false)
const firstSeat = ref(0)
const dealt = ref(false)        // 发牌错峰：新一局先收拢到中央再展开

/* ---------- 派生 ---------- */
const myLevel = computed(() => teamLevel.value[0])
const oppLevel = computed(() => teamLevel.value[1])
const iWon = computed(() => roundResult.value.winTeam === 0)
/** 积分栏：各座位所属队伍当前级数 */
const scores = computed(() => [0, 1, 2, 3].map(s => teamLevel.value[G.TEAM_OF[s]]))
const throwSeats = computed(() => Object.keys(seatThrows.value).map(Number))
const selCards = computed(() => hands.value[0].filter(c => sel.value.includes(c.id)))
const selPattern = computed(() => G.detectPattern(selCards.value, roundLevel.value))
const canPlay = computed(() => !!selPattern.value && G.canBeat(selPattern.value, target.value?.pattern ?? null))
const canAct = computed(() => phase.value === 'playing' && turn.value === 0 && !finished.value.includes(0))

/* ---------- 小工具 ---------- */
function cardText(c) { return c.joker ? (c.joker === 'big' ? '大' : '小') : G.RANK_TEXT[c.rank] }
function cardSuit(c) { return c.joker ? '' : c.suit }
function isRed(c) { return !c.joker && (c.suit === '♥' || c.suit === '♦') }
function isWildCard(c) { return G.isWild(c, roundLevel.value) }
function seatName(s) { return G.SEAT_NAME[s] }
function seatAvatar(s) { return s === 0 ? '🙂' : (AI_AVATARS[s] || '🤖') }
function handCount(s) { return hands.value[s].length }
function isTurn(s) { return phase.value === 'playing' && turn.value === s }
function seatSub(s) {
  if (finished.value.includes(s)) return `第 ${finished.value.indexOf(s) + 1} 名`
  return `${handCount(s)} 张`
}

function setThrow(seat, h) { seatThrows.value = { [seat]: h } }
function clearThrows() { seatThrows.value = {} }
function pushHistory(item) { history.value.unshift(item) }

let toastTimer = null
function toastMsg(t) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1800)
}

/* ---------- 局流程 ---------- */
let dealTimer = null
function newRound() {
  const dealt4 = G.deal(roundLevel.value)
  hands.value = dealt4
  turn.value = firstSeat.value
  target.value = null
  passCount.value = 0
  finished.value = []
  phase.value = 'playing'
  sel.value = []
  clearThrows()
  history.value = []
  // 发牌动画：先收拢到中央，下一帧展开
  dealt.value = false
  clearTimeout(dealTimer)
  dealTimer = setTimeout(() => { dealt.value = true }, 32)
  scheduleAI()
}

function nextActive(from) {
  for (let i = 1; i <= 4; i++) {
    const s = (from + i) % 4
    if (!finished.value.includes(s)) return s
  }
  return from
}

function advance() {
  if (phase.value !== 'playing') return
  if (finished.value.length >= 3) return endRound()
  const actives = [0, 1, 2, 3].filter(s => !finished.value.includes(s))
  if (actives.length <= 1) return endRound()

  if (target.value) {
    const need = actives.filter(s => s !== target.value.seat).length
    if (passCount.value >= need) {
      const lead = target.value.seat
      if (!finished.value.includes(lead)) {
        turn.value = lead
      } else {
        // 接风：出完牌的一方由对家先出，对家也出完则顺延
        const partner = (lead + 2) % 4
        turn.value = !finished.value.includes(partner) ? partner : nextActive(lead)
      }
      target.value = null
      passCount.value = 0
      sel.value = []
      clearThrows()   // 一圈结束，中央出牌区清空
      scheduleAI()
      return
    }
  }
  turn.value = nextActive(turn.value)
  sel.value = []
  scheduleAI()
}

function applyPlay(seat, cards) {
  const pat = G.detectPattern(cards, roundLevel.value)
  if (!pat) return
  const ids = new Set(cards.map(c => c.id))
  hands.value[seat] = hands.value[seat].filter(c => !ids.has(c.id))
  // 领出者再次领出 = 新一圈，先清掉上一圈的牌
  if (target.value?.seat === seat) clearThrows()
  setThrow(seat, { seat, cards, pattern: pat })
  target.value = { seat, cards, pattern: pat }
  passCount.value = 0
  pushHistory({ kind: 'play', seat, cards, pattern: pat })
  if (hands.value[seat].length === 0 && !finished.value.includes(seat)) {
    finished.value.push(seat)
    firstSeat.value = seat
    toastMsg(`${seatName(seat)} 出完，第 ${finished.value.length} 名`)
  }
  sel.value = []
  advance()
}

function applyPass(seat) {
  passCount.value++
  pushHistory({ kind: 'pass', seat })
  sel.value = []
  advance()
}

function endRound() {
  for (const s of [0, 1, 2, 3]) if (!finished.value.includes(s)) finished.value.push(s)
  const order = finished.value.slice(0, 4)
  const up = G.upgradeFor(order)
  const winTeam = G.TEAM_OF[order[0]]
  teamLevel.value[winTeam] = G.nextLevel(teamLevel.value[winTeam], up)
  roundResult.value = { up, winTeam, order }
  matchOver.value = teamLevel.value[winTeam] > G.MAX_LEVEL
  phase.value = 'settled'
}

function nextRound() {
  roundNo.value++
  const winTeam = roundResult.value.winTeam
  if (matchOver.value) {
    teamLevel.value = [2, 2]
    roundLevel.value = 2
    matchOver.value = false
    roundNo.value = 1
  } else {
    roundLevel.value = Math.min(G.MAX_LEVEL, teamLevel.value[winTeam])
  }
  newRound()
}

/* ---------- AI ---------- */
let aiTimer = null
function aiThink() { return AI_THINK_MIN + Math.floor(Math.random() * (AI_THINK_MAX - AI_THINK_MIN)) }
function scheduleAI() {
  clearTimeout(aiTimer)
  if (phase.value !== 'playing') return
  if (HUMAN_SEATS.includes(turn.value)) return
  aiTimer = setTimeout(aiTurn, aiThink())
}
function aiTurn() {
  if (phase.value !== 'playing') return
  const s = turn.value
  if (HUMAN_SEATS.includes(s)) return
  const tgt = target.value
  const lastIsTeammate = !!tgt && G.TEAM_OF[tgt.seat] === G.TEAM_OF[s]
  const oppMin = Math.min(...[0, 1, 2, 3]
    .filter(o => G.TEAM_OF[o] !== G.TEAM_OF[s] && hands.value[o].length)
    .map(o => hands.value[o].length), 99)
  const hiSingle = G.highestRemainingSingle(hands.value[s], roundLevel.value, history.value)
  const pick = G.aiChoose(hands.value[s], tgt?.pattern ?? null, roundLevel.value,
    { lastIsTeammate, pressure: oppMin, highestSingle: hiSingle })
  if (pick && pick.length) applyPlay(s, pick)
  else applyPass(s)
}

/* ---------- 交互 ---------- */
function toggleSel(c) {
  if (!canAct.value) return
  const i = sel.value.indexOf(c.id)
  if (i >= 0) sel.value = sel.value.filter(x => x !== c.id)
  else sel.value = [...sel.value, c.id]
}

function doPlay() {
  if (!canAct.value) return
  if (!selPattern.value) { toastMsg('这不是合法牌型'); return }
  if (!G.canBeat(selPattern.value, target.value?.pattern ?? null)) { toastMsg('压不过上一手'); return }
  applyPlay(0, selCards.value)
}

function doPass() {
  if (!canAct.value) return
  if (!target.value) { toastMsg('本轮由你先出，必须出牌'); return }
  applyPass(0)
}

function doHint() {
  if (!canAct.value) return
  const tgt = target.value
  const lastIsTeammate = !!tgt && G.TEAM_OF[tgt.seat] === G.TEAM_OF[0]
  const pick = G.aiChoose(hands.value[0], tgt?.pattern ?? null, roundLevel.value, { lastIsTeammate })
  if (pick && pick.length) sel.value = pick.map(c => c.id)
  else toastMsg('没有能压过的牌，只能「不要」')
}

function restart() {
  clearTimeout(aiTimer)
  clearTimeout(dealTimer)
  clearTimeout(toastTimer)
  teamLevel.value = [2, 2]
  roundLevel.value = 2
  roundNo.value = 1
  matchOver.value = false
  firstSeat.value = 0
  toast.value = ''
  newRound()
}

/* ---------- 生命周期 ---------- */
onMounted(() => { newRound() })
onBeforeUnmount(() => {
  clearTimeout(aiTimer)
  clearTimeout(dealTimer)
  clearTimeout(toastTimer)
})
</script>

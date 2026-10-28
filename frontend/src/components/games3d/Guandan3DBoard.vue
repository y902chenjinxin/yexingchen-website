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
        <!-- v2.46.154：自己的铭牌不再走 3D 世界（手牌占满底部，它必然压牌），改到左下角 HUD -->
        <div
          v-for="s in OPP_SEATS"
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
            :style="pieceBox(true, 50, 72, 12, oppTF(o.side, k - 1, 5), k - 1, false, false)"
          >
            <div class="pc-face pc-front card-back"></div>
            <div class="pc-face pc-back card-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </div>

        <!-- 中央出牌区：每个已出座位显示其最新一手，按屏幕位给原点偏移 -->
        <template v-for="seat in throwSeats" :key="'gc' + seat">
          <div
            v-for="(c, i) in seatThrows[seat].cards"
            :key="c.id"
            class="pc3d gd-hand mj-center"
            :class="{ wild: isWildCard(c) }"
            :style="pieceBox(dealt, 52, 74, 12, centerTF(i, 40, CENTER_OFF[screenPos(seat, 0)]), i, false, false)"
          >
            <!-- 出牌区的牌少（一手 1~8 张）、间距大，保留右下角大花色做视觉重心 -->
            <div class="pc-face pc-front card-front" :class="[isRed(c) ? 'red' : 'blk', c.joker ? 'joker' : '']">
              <span class="cf-corner"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
              <span v-if="!c.joker" class="cf-suit-big">{{ cardSuit(c) }}</span>
            </div>
            <div class="pc-face pc-back card-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </template>
      </div>
      <!-- 我的手牌（v2.46.240：**移出 3D 世界**，改成屏幕层的 2D 牌扇）
           🔴 为什么必须挪出来：27 张牌作为 preserve-3d 的子元素时 z 全部相同，
           浏览器做 3D 排序会在线程中间翻转绘制顺序 —— 实测右半边 13 张的点数
           被压在下一张牌底下，只剩一个淡花色（DOM 里 .cf-corner 明明都在）。
           腾讯斗地主的手牌本来就是 2D 平面，挪出来既绕开这个 bug，
           又能把阴影 / 描边 / 扇形弧度做扎实。 -->
      <div
        ref="handEl"
        class="g3d-hand2d"
        :style="{ '--hn': viewHand.length }"
        @contextmenu.prevent
      >
        <div
          v-for="(c, i) in viewHand"
          :key="c.id"
          class="hcard"
          :class="{
            sel: sel.includes(c.id),
            wild: isWildCard(c),
            grouped: i < headCount,
            lifting: dragLiftId === c.id,
          }"
          :style="hcardStyle(i)"
          @pointerdown="onCardDown(c, i, $event)"
        >
          <div class="hcard-face card-front" :class="[isRed(c) ? 'red' : 'blk', c.joker ? 'joker' : '']">
            <span class="cf-corner"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
            <span v-if="!c.joker" class="cf-suit-big">{{ cardSuit(c) }}</span>
          </div>
        </div>
      </div>

      <!-- v2.46.238：手牌底座（托住手牌，不再像浮在桌面上） -->
      <div class="gt3-handbed"></div>
    </div>

    <!-- 手牌工具条（v2.46.239）：牌型识别 / 提示 / 挪左 / 挪右 / 重选
         2D 板这套工具在「手牌上方」，3D 放在底栏上方一行，视线落点一致。 -->
    <div class="g3d-handtools">
      <span
        class="g3d-pat"
        :class="{ 'is-ok': sel.length && canPlay, 'is-bad': sel.length && !canPlay }"
      >{{ patLabel }}</span>
      <button class="g3d-btn ghost sm" :disabled="!canAct" @click="doHint">提示</button>
      <button
        class="g3d-btn ghost sm"
        :disabled="!canAct || (!sel.length && !seqGroups.length)"
        :title="sel.length || seqGroups.length ? '把选中的牌（未选则第一组同花顺/顺子）钉到最左' : '先选牌，再挪到左侧'"
        @click="pinSeqToLeft"
      >挪左</button>
      <button
        class="g3d-btn ghost sm"
        :disabled="!sel.length"
        title="把选中的牌按牌值归位到整手降序序列里"
        @click="pinToRight"
      >挪右</button>
      <button class="g3d-btn ghost sm" :disabled="!sel.length" @click="clearSel">重选</button>
    </div>

    <!-- 操作条 -->
    <div class="g3d-ctl right">
      <button class="g3d-btn ghost" :disabled="!canAct" @click="doHint">提示</button>
      <button class="g3d-btn" :disabled="!canAct || !target" @click="doPass">不要</button>
      <button class="g3d-btn primary" :disabled="!canAct || !canPlay" @click="doPlay">出牌</button>
    </div>

    <!-- 我：左下角 HUD（屏幕坐标系，不参与 3D 变换） -->
    <div class="gt3-seat gt3-self" :class="{ 'is-turn': isTurn(0) }">
      <div class="gt3-ava" :style="{ background: seatColors[0] }"><AppIcon :icon="seatAvatar(0)" /></div>
      <div class="gt3-meta">
        <b>{{ seatName(0) }}</b>
        <i :class="{ turn: isTurn(0) }">{{ seatSub(0) }}</i>
      </div>
      <div class="gt3-score is-you">
        <span class="snum">{{ G.levelText(scores[0]) }}</span><span class="slbl">级</span>
      </div>
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
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import * as G from '@/utils/games/guandan.js'
import {
  VIEW_RX, boxVars, pieceBox, oppTF, centerTF, seatTF, SEAT_SLOT, screenPos,
} from '@/components/games3d/use3dTable.js'
/* v2.46.240：手牌已移出 3D 世界（改 2D 牌扇），本组件不再用 handTF；
 * 麻将板（Mahjong3DBoard）仍走 3D 立牌，那边继续用。 */
import AppIcon from '@/components/common/AppIcon.vue'
/* v2.46.154：3D 牌桌此前**完全没接音效**（2D 板有），所以出牌/不要/发牌都是静的。
   这里直接复用 2D 掼蛋那套采样 + 声像，听感一致。 */
import { sfx, panOf } from '@/utils/games/sfx'

defineEmits(['exit'])

/* ---------- 常量 ---------- */
const HUMAN_SEATS = [0]
/** 对手座位（自己的铭牌走左下角 HUD，不再参与 3D 座位循环） */
const OPP_SEATS = [1, 2, 3]
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
/* 手牌归集（v2.46.239，从 2D 板移植）：
 *   pinnedGroups = 每次「挪左」钉住的 ids 数组，按操作顺序；
 *   rightDocks  = 每次「挪右」的 ids 数组（按牌值插入降序 continuum）。
 * 出掉对应的牌会自动失效（按 base 里的 id 过滤），新局清空。 */
const pinnedGroups = ref([])
const rightDocks = ref([])

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

/* ---------- 手牌展示顺序：左区（钉组 + 同花顺组）| 散牌区 ----------
 * 与 2D GuandanBoard.vue 的 handParts 同口径（那边注释里有更详细的历史），规则：
 *  ① 手动「挪右」最优先——被挪右的牌不进左区（旧版 dock 会被同花顺抢走，
 *     导致「同花顺不能往右挪」）；
 *  ② 手动「挪左」钉的组按钉的顺序进左区，与挪右撞牌时让位（挪右是更新的操作）；
 *  ③ 天然同花顺（不含逢人配）从大到小**贪心取互不重叠的 5 张组**进左区，
 *     同花 6~9 张只取最大 5 张、剩余回散牌区；同花 10 张自动拆两组；
 *  ④ 只要存在挪右的牌，整手按牌值降序排成一条 continuum（顺子/三张被拆开）。
 * 3D 之前完全没有这套，手上有没有同花顺全靠自己数——这是夜星提的主要差距。 */
const handParts = computed(() => {
  const base = hands.value[0] || []
  if (phase.value === 'settled' || !base.length) return { head: [], mid: base }
  const inBase = new Set(base.map(c => c.id))
  const val = c => G.cardValue(c, roundLevel.value)
  const asc = (a, b) => val(a) - val(b)
  const docks = rightDocks.value
    .map(d => ({ ids: d.ids.filter(id => inBase.has(id)) }))
    .filter(d => d.ids.length)
  const dockIds = new Set()
  for (const d of docks) for (const id of d.ids) dockIds.add(id)
  const pinGroups = pinnedGroups.value
    .map(g => g.filter(id => inBase.has(id) && !dockIds.has(id)))
    .filter(g => g.length)
  const pinnedIds = new Set(pinGroups.flat())
  const naturals = base.filter(c => !G.isWild(c, roundLevel.value) && !pinnedIds.has(c.id) && !dockIds.has(c.id))
  const flushGroups = []
  const usedF = new Set()
  for (const cs of G.findFlushBombs(naturals, roundLevel.value)) {
    if (cs.some(c => usedF.has(c.id))) continue
    flushGroups.push(cs)
    for (const c of cs) usedF.add(c.id)
  }
  if (!pinGroups.length && !flushGroups.length && !docks.length) return { head: [], mid: base }
  if (docks.length) {
    let seq = base.filter(c => !pinnedIds.has(c.id)).sort((a, b) => val(b) - val(a))
    for (const d of docks) {
      const set = new Set(d.ids)
      seq = seq.filter(c => !set.has(c.id))
      for (const c of base.filter(c => set.has(c.id)).sort((a, b) => val(b) - val(a))) {
        let at = seq.findIndex(x => val(x) < val(c))
        if (at < 0) at = seq.length
        seq = seq.slice(0, at).concat([c], seq.slice(at))
      }
    }
    const head = pinGroups.map(ids => base.filter(c => ids.includes(c.id)).sort(asc)).flat()
    return { head, mid: seq }
  }
  const groups = [
    ...pinGroups.map(ids => base.filter(c => ids.includes(c.id)).sort(asc)),
    ...flushGroups.map(cs => cs.slice().sort(asc)),
  ].sort((a, b) => Math.max(...b.map(val)) - Math.max(...a.map(val)))
  const head = groups.flat()
  const usedL = new Set(head.map(c => c.id))
  const mid = base.filter(c => !usedL.has(c.id) && !dockIds.has(c.id)).sort((a, b) => val(b) - val(a))
  return { head, mid }
})
const viewHand = computed(() => handParts.value.head.concat(handParts.value.mid))
/** 左区牌数（前 headCount 张带「已归集」标记） */
const headCount = computed(() => handParts.value.head.length)
/** 「挪左」的保底候选：同花顺优先，其次普通顺子 */
const seqGroups = computed(() => G.findSeqGroups(hands.value[0], roundLevel.value))
/** 牌型提示文案 */
const patLabel = computed(() => {
  if (!sel.value.length) {
    return headCount.value ? `已归集 ${headCount.value} 张` : '选牌'
  }
  if (!selPattern.value) return '牌型无效'
  const name = G.PATTERN_NAME[selPattern.value.type] || '出牌'
  return canPlay.value ? name : `${name} · 压不过`
})

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
  pinnedGroups.value = []
  rightDocks.value = []
  clearThrows()
  history.value = []
  // 发牌动画：先收拢到中央，下一帧展开
  dealt.value = false
  clearTimeout(dealTimer)
  dealTimer = setTimeout(() => { dealt.value = true; sfx.deal() }, 32)
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
  sfx.play(panOf(seat, 0))
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
  sfx.pass(panOf(seat, 0))
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
  if (winTeam === G.TEAM_OF[0]) sfx.win()
  else sfx.lose()
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
  sfx.pick()
  const i = sel.value.indexOf(c.id)
  if (i >= 0) sel.value = sel.value.filter(x => x !== c.id)
  else sel.value = [...sel.value, c.id]
}

/* ================= 手牌手势（v2.46.244） =================
 * 三种操作，全部走 pointer 事件（鼠标 / 触摸 / 笔一致）：
 *   ① 点按        —— 切换单张选中（立即响应，不做双击延迟）
 *   ② 左右滑动    —— 划过的牌**追加**到选中（从按下那张到当前那张的区间）；
 *                    若这一片本来都已选，同一次滑动改为**取消**
 *                    （v2.46.260：夜星「选完再左右滑没法取消」）
 *   ③ 向上滑动    —— 抬起过 50px 就把这张当单张打出
 *   ④ 双击        —— 快速点同一张两次 = 出单张（与向上滑动等价）
 *
 * 按项目既有规矩实现（见 docs/ISSUES.md）：
 *   - 监听挂 window，不依赖 setPointerCapture（划出牌面也能继续）
 *   - 用位移阈值区分「点按 / 划选 / 上滑」，阈值 10px（横向）/ 16px（纵向）
 *   - 触发过拖动就不再当成点按，避免「划完松手又切换了一次选中」
 */
const handEl = ref(null)
const dragLiftId = ref('')     // 上滑中的那张（CSS 抬起来）
let drag = null                // { id, idx, x0, y0, mode, base, lastIdx }
let lastTap = { id: null, t: 0 }

/** 指针 x 落在哪张牌上：后面的牌画在上层，取最后一个命中的。
 *  clamp=true 时越界钳到两端 —— 滑出手牌区（尤其想整段取消）也能取到边界那张。 */
function idxAtX(x, clamp = false) {
  const root = handEl.value
  if (!root) return -1
  const els = root.querySelectorAll('.hcard')
  if (!els.length) return -1
  let idx = -1
  for (let i = 0; i < els.length; i++) {
    const r = els[i].getBoundingClientRect()
    if (x >= r.left && x <= r.right) idx = i
  }
  if (idx < 0 && clamp) {
    const first = els[0].getBoundingClientRect()
    const last = els[els.length - 1].getBoundingClientRect()
    if (x < first.left) return 0
    if (x > last.right) return els.length - 1
  }
  return idx
}

/** 从 base 出发应用 [a..b] 区间。mode：'add' 追加 / 'drop' 取消。
 *
 *  v2.46.260 支持「滑动取消」（夜星：选完再左右滑没法取消）：
 *  手势方向由**第一段区间**决定 —— 区间内全部已选就是取消，否则是追加，
 *  一旦确定整段手势不再翻转（否则「A 滑到 G 再滑回 C」会莫名其妙全取消）。
 *  判断用 `base`（按下瞬间的选区快照）而不是实时选区，所以同一手势内稳定。
 *  于是「选完一段，从任一端滑回来」直接取消，不用先点一下再滑。
 */
function applyRange(base, a, b, mode = 'add') {
  const lo = Math.min(a, b)
  const hi = Math.max(a, b)
  const ids = viewHand.value.slice(lo, hi + 1).map(c => c.id)
  const baseSet = new Set(base)
  let next
  if (mode === 'drop') {
    const drop = new Set(ids)
    next = [...baseSet].filter(id => !drop.has(id))
  } else {
    next = [...baseSet, ...ids]
  }
  const keep = new Set(next)
  sel.value = viewHand.value.filter(c => keep.has(c.id)).map(c => c.id)
  return ids
}

/** [a..b] 区间内的牌是否在 base 里**全部**已选（决定这次滑动是取消还是追加） */
function rangeAllSelected(base, a, b) {
  const lo = Math.min(a, b)
  const hi = Math.max(a, b)
  const ids = viewHand.value.slice(lo, hi + 1).map(c => c.id)
  if (!ids.length) return false
  const set = new Set(base)
  return ids.every(id => set.has(id))
}

function onCardDown(c, idx, e) {
  if (!canAct.value) return
  if (e.pointerType === 'mouse' && e.button !== 0) return
  drag = { id: c.id, idx, x0: e.clientX, y0: e.clientY, mode: '', base: sel.value.slice(), lastIdx: -1, swipeMode: '' }
}

function onWinMove(e) {
  if (!drag) return
  const dx = e.clientX - drag.x0
  const dy = e.clientY - drag.y0
  if (!drag.mode) {
    if (Math.abs(dx) > 10 && Math.abs(dx) >= Math.abs(dy)) drag.mode = 'select'
    else if (dy < -16 && Math.abs(dy) > Math.abs(dx)) drag.mode = 'up'
    else return
  }
  if (drag.mode === 'select') {
    const idx = idxAtX(e.clientX, true)   // 滑出手牌区也算到边界，整段取消更顺手
    if (idx >= 0 && idx !== drag.lastIdx) {
      drag.lastIdx = idx
      if (!drag.swipeMode) {
        // 第一段区间定方向：全已选 = 取消，否则 = 追加；之后整段手势不再翻转
        drag.swipeMode = rangeAllSelected(drag.base, drag.idx, idx) ? 'drop' : 'add'
      }
      applyRange(drag.base, drag.idx, idx, drag.swipeMode)
    }
  } else if (drag.mode === 'up') {
    // 超过 40px 才抬起示意，避免轻扫就跳起来
    dragLiftId.value = dy < -40 ? drag.id : ''
  }
}

function onWinUp(e) {
  if (!drag) return
  const dx = e.clientX - drag.x0
  const dy = e.clientY - drag.y0
  const d = drag
  drag = null
  dragLiftId.value = ''
  if (d.mode === 'up') {
    if (dy < -50) playSingleById(d.id)
    return
  }
  if (d.mode === 'select') return        // 划选已经生效，松手不再切换
  // 位移没到阈值 = 点按
  void dx
  handleTap(d.id)
}

/** 点按：同一张 300ms 内点第二次 = 出单张；否则切换选中 */
function handleTap(id) {
  const now = Date.now()
  if (lastTap.id === id && now - lastTap.t < 300) {
    lastTap = { id: null, t: 0 }
    playSingleById(id)
    return
  }
  lastTap = { id, t: now }
  const c = hands.value[0].find(x => x.id === id)
  if (c) toggleSel(c)
}

/** 把某一张当单张打出去（双击 / 上滑共用） */
function playSingleById(id) {
  if (!canAct.value) return
  const c = hands.value[0].find(x => x.id === id)
  if (!c) return
  const pat = G.detectPattern([c], roundLevel.value)
  if (!pat) { toastMsg('这张牌打不出去'); return }
  if (!G.canBeat(pat, target.value?.pattern ?? null)) {
    toastMsg('单张压不过上一手')
    sfx.pick()
    return
  }
  sel.value = [id]
  applyPlay(0, [c])
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
  if (pick && pick.length) { sel.value = pick.map(c => c.id); sfx.pick() }
  else toastMsg('没有能压过的牌，只能「不要」')
}

/* ---------- 手牌归集操作（v2.46.239，与 2D 板同语义） ---------- */
/** 「挪左」：把选中的牌钉到最左；没选中时退而钉第一组同花顺/顺子。 */
function pinSeqToLeft() {
  let ids = sel.value.slice()
  if (!ids.length) {
    if (!seqGroups.value.length) { toastMsg('手上没有顺子或同花顺'); return }
    ids = seqGroups.value[0].map(c => c.id)
  }
  pinnedGroups.value = [
    ...pinnedGroups.value.map(g => g.filter(id => !ids.includes(id))).filter(g => g.length),
    ids,
  ]
  if (rightDocks.value.length) {
    rightDocks.value = rightDocks.value
      .map(d => ({ ids: d.ids.filter(id => !ids.includes(id)) }))
      .filter(d => d.ids.length)
  }
  toastMsg(sel.value.length ? '已挪到左侧' : '已把第一组同花顺/顺子挪到左侧')
  sfx.pick()
  sel.value = []
}

/** 「挪右」：把选中的牌按牌值归位到整手降序序列里（组合会被拆开，与 2D 一致）。 */
function pinToRight() {
  const ids = sel.value.slice()
  if (!ids.length) { toastMsg('先选牌，再点「挪右」'); return }
  rightDocks.value = [
    ...rightDocks.value.map(d => ({ ids: d.ids.filter(id => !ids.includes(id)) })).filter(d => d.ids.length),
    { ids },
  ]
  // 挪右解除左钉（dock 优先于自动同花顺与钉组）
  if (pinnedGroups.value.length) {
    pinnedGroups.value = pinnedGroups.value
      .map(g => g.filter(id => !ids.includes(id)))
      .filter(g => g.length)
  }
  sel.value = []
  toastMsg(`已挪到右侧 ${ids.length} 张`)
  sfx.pick()
}

function clearSel() {
  if (!sel.value.length) return
  sel.value = []
  sfx.pick()
}

/* ---------- 2D 牌扇的每张牌定位（v2.46.240） ----------
 * 用 CSS 变量把「旋转 / 弧度 / 入场延迟」传给样式，避免每张牌算一长串内联样式：
 *   --rot   ：绕牌底外一点微转，两端外张 → 扇形
 *   --arc   ：两端略抬高 → 弧
 *   --delay ：发牌错峰（18ms/张，27 张约 0.5s 铺完）
 * zIndex 递增保证绘制顺序恒为「从左到右压在上一层」，不再依赖 3D 排序。 */
function hcardStyle(i) {
  const n = viewHand.value.length || 1
  const t = n > 1 ? (i - (n - 1) / 2) / ((n - 1) / 2) : 0
  return {
    zIndex: 10 + i,
    '--rot': (-t * 2.4).toFixed(2) + 'deg',
    '--arc': (-Math.abs(t) * Math.abs(t) * 7).toFixed(1) + 'px',
    '--delay': (i * 18) + 'ms',
  }
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

/* ---------- 「轮到你」提醒（v2.46.239） ----------
 * 3D 板之前没有这一步：AI 出完牌轮到你了，画面只是铭牌描边变金色，
 * 视线在牌上时完全察觉不到（夜星：「出牌的声音等等」）。
 * 用 sfx.alert（双音 + 轻震），只在**从别人转到自己**时响，新开局也响一次。 */
watch(turn, (now, prev) => {
  if (now !== 0 || phase.value !== 'playing') return
  if (prev === 0) return
  sfx.alert()
})

/* ---------- 生命周期 ---------- */
onMounted(() => {
  sfx.preload()   // 预热采样，消掉第一手出牌的取包延迟
  newRound()
  // 手牌手势：move/up 挂 window，划出牌面也不会丢事件
  window.addEventListener('pointermove', onWinMove, { passive: true })
  window.addEventListener('pointerup', onWinUp)
  window.addEventListener('pointercancel', onWinUp)
})
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onWinMove)
  window.removeEventListener('pointerup', onWinUp)
  window.removeEventListener('pointercancel', onWinUp)
  clearTimeout(aiTimer)
  clearTimeout(dealTimer)
  clearTimeout(toastTimer)
})
</script>

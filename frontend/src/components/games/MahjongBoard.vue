<template>
  <div class="gt-landscape">
    <div class="gt-shell mj" :class="{ 'is-big': big }">
      <!-- ===== 顶栏 ===== -->
      <header class="mj-top">
        <span class="gt-title">四川麻将 · 血战到底</span>
        <span class="gt-pill gold">第 {{ roundNo }} 局</span>
        <span class="gt-pill">余牌 {{ wall.length }}</span>
        <span v-if="missing[0]" class="gt-pill">你的缺门 {{ M.SUIT_NAME[missing[0]] }}</span>
        <span class="gt-spacer"></span>
        <button class="gt-btn sm ghost" :title="muted ? '取消静音' : '静音'" @click="toggleMute">
          {{ muted ? '🔇' : '🔊' }}
        </button>
        <button class="gt-btn sm ghost" @click="doExit">退出对局</button>
      </header>

      <!-- ===== 牌桌 ===== -->
      <div class="mj-table">
        <!-- 对家 / 左右家 -->
        <div
          v-for="s in PANEL_SEATS"
          :key="s"
          class="mj-seat"
          :class="seatAreaCls(s)"
        >
          <div class="gt-seat" :class="seatCls(s)">
            <span class="gt-seat-av">{{ seatAvatar(s) }}</span>
            <span class="gt-seat-tx">
              <b class="gt-seat-name">{{ seatName(s) }}</b>
              <i class="gt-seat-sub">{{ seatSub(s) }}</i>
            </span>
            <span v-if="isTurn(s) && !out[s]" class="gt-seat-badge">出牌中</span>
            <span v-else-if="out[s]" class="gt-seat-badge">已胡</span>
          </div>

          <div v-if="melds[s].length" class="mj-melds">
            <span v-for="(md, i) in melds[s]" :key="i" class="gt-meld">
              <span
                v-for="(t, k) in meldTiles(md)"
                :key="k"
                class="gt-tile mini"
                :class="suitCls(t)"
              ><span class="num">{{ t.rank }}</span></span>
            </span>
          </div>

          <div class="mj-backs">
            <span v-for="n in backCount(s)" :key="n" class="gt-tile mini is-back"></span>
          </div>

          <div class="mj-discards">
            <span
              v-for="t in discards[s]"
              :key="t.id"
              class="gt-tile mini"
              :class="suitCls(t)"
            ><span class="num">{{ t.rank }}</span></span>
          </div>
        </div>

        <!-- 中央：最近舍牌 + 战报 -->
        <div class="mj-seat mj-center">
          <div class="mj-center-head">
            <span v-if="lastDiscard" class="gt-pill gold">
              {{ seatName(lastDiscard.seat) }} 打出 {{ tileText(lastDiscard.tile) }}
            </span>
            <span v-else class="gt-pill">开局</span>
            <span v-if="phase === 'playing' && !pending" class="gt-pill">
              轮到 {{ seatName(turn) }}
            </span>
          </div>
          <div class="mj-center-tile">
            <span
              v-if="lastDiscard"
              class="gt-tile gt-anim-play"
              :class="suitCls(lastDiscard.tile)"
            >
              <span class="num">{{ lastDiscard.tile.rank }}</span>
              <span class="suit">{{ M.SUIT_GLYPH[lastDiscard.tile.suit] }}</span>
            </span>
          </div>
          <div class="mj-log">
            <span v-for="(l, i) in logs.slice(0, 4)" :key="i">{{ l }}</span>
          </div>
        </div>
      </div>

      <!-- ===== 听牌提示 ===== -->
      <div v-if="phase === 'playing' && viewSeat !== null" class="mj-tingbar">
        <span class="mj-ting-label">听牌提示</span>
        <template v-if="tingInfo.length">
          <span v-for="(info, i) in tingInfo.slice(0, 4)" :key="i" class="mj-ting-item">
            打 <b>{{ tileText(info.tile) }}</b> 听
            <b>{{ info.waits.map(tileText).join(' / ') }}</b>
          </span>
        </template>
        <span v-else class="mj-ting-none">尚未听牌</span>
      </div>

      <!-- ===== 底部：手牌 + 操作 ===== -->
      <footer class="mj-bottom">
        <div class="mj-handbar">
          <span class="gt-pill gold">{{ seatName(viewSeat) }}的手牌 · {{ viewHand.length }} 张</span>
          <span v-if="melds[viewSeat]?.length" class="gt-pill">副露 {{ melds[viewSeat].length }} 组</span>
          <span class="gt-spacer"></span>
          <span class="gt-sub">{{ statusLine }}</span>
        </div>

        <div class="mj-hand">
          <span
            v-for="t in viewHand"
            :key="t.id"
            class="gt-tile"
            :class="[suitCls(t), { pickable: canDiscard, 'is-sel': selId === t.id }]"
            @click="pick(t)"
          >
            <span class="num">{{ t.rank }}</span>
            <span class="suit">{{ M.SUIT_GLYPH[t.suit] }}</span>
          </span>
          <span
            v-if="viewDrawn"
            class="gt-tile is-drawn"
            :class="[suitCls(viewDrawn), { pickable: canDiscard, 'is-sel': selId === viewDrawn.id }]"
            @click="pick(viewDrawn)"
          >
            <span class="num">{{ viewDrawn.rank }}</span>
            <span class="suit">{{ M.SUIT_GLYPH[viewDrawn.suit] }}</span>
          </span>
          <p v-if="!viewHand.length && !viewDrawn" class="mj-hand-empty">— 无手牌 —</p>
        </div>

        <!-- 反应窗口：碰 / 杠 / 胡 / 过 -->
        <div v-if="pending" class="gt-actions mj-actions">
          <span class="gt-pill gold">可操作：{{ pending.kinds.map(k => REACT_NAME[k]).join(' / ') }}</span>
          <button v-if="pending.kinds.includes('hu')" class="gt-btn" @click="onReact('hu')">胡</button>
          <button v-if="pending.kinds.includes('kong')" class="gt-btn" @click="onReact('kong')">杠</button>
          <button v-if="pending.kinds.includes('pong')" class="gt-btn" @click="onReact('pong')">碰</button>
          <button class="gt-btn ghost" @click="onReact('pass')">过</button>
        </div>

        <!-- 自己回合的操作 -->
        <div v-else class="gt-actions mj-actions">
          <button class="gt-btn" :disabled="!canDiscard || selId === null" @click="discardSel">出牌</button>
          <button class="gt-btn" :disabled="!canDiscard || !canZimo" @click="doZimo">自摸</button>
          <button
            v-if="canDiscard && ankongs.length"
            class="gt-btn ghost"
            @click="doAnkong(ankongs[0])"
          >暗杠 {{ tileText(ankongs[0]) }}</button>
          <button
            v-if="canDiscard && bugangs.length"
            class="gt-btn ghost"
            @click="doBugang(bugangs[0])"
          >补杠 {{ tileText(bugangs[0]) }}</button>
          <button class="gt-btn ghost" :disabled="!canDiscard" @click="doHint">提示</button>
        </div>
      </footer>

      <!-- ===== 定缺（页内，不弹窗） ===== -->
      <div v-if="phase === 'dingque'" class="gt-over">
        <div class="gt-over-card">
          <h3>定缺</h3>
          <p>
            请为 <b>{{ seatName(dingqueSeat) }}</b> 选一门花色作为「缺门」。<br>
            手上该门牌必须先打完，之后才能碰、杠、胡。
          </p>
          <div class="gt-actions">
            <button
              v-for="s in M.SUITS"
              :key="s"
              class="gt-btn"
              @click="chooseMissing(s)"
            >{{ M.SUIT_NAME[s] }}（{{ suitCount(dingqueSeat, s) }} 张）</button>
          </div>
        </div>
      </div>

      <!-- ===== 结算（页内，不弹窗） ===== -->
      <div v-if="phase === 'settled'" class="gt-over">
        <div class="gt-over-card">
          <h3>{{ result?.title }}</h3>
          <p>
            <template v-if="result?.hus?.length">
              <span v-for="(h, i) in result.hus" :key="i">
                {{ seatName(h.seat) }}：{{ h.names.join(' · ') }} {{ h.fan }} 番
                <em>（{{ h.zimo ? '自摸' : '点炮' }}）</em><br>
              </span>
            </template>
            <template v-else>流局：牌墙摸完，无人胡牌。</template>
            <br>
            你的得分：<b>{{ result?.delta > 0 ? '+' : '' }}{{ result?.delta }}</b> 点
          </p>
          <div class="gt-actions">
            <button class="gt-btn" @click="nextRound">再来一局</button>
            <button class="gt-btn ghost" @click="doExit">返回列表</button>
          </div>
        </div>
      </div>

      <div v-if="toast" class="gt-toast">{{ toast }}</div>
      <div class="gt-watermark">四 川 麻 将 · 血 战 到 底 · 定 缺 开 局</div>
    </div>
  </div>
</template>

<script setup>
/** 四川麻将 · 血战到底 牌桌（v2.43）。
 *
 * 纯前端同屏对局：solo = 1 真人 + 3 AI；duo = 2 真人同屏 + 2 AI；quad = 4 真人轮流。
 * 规则核心在 `utils/games/mahjong.js`（和牌判定 / 番种 / 听牌 / 向听 / AI）。
 * 视觉走 `assets/styles/game-table.css` 的独立牌桌皮肤，不污染全站玄黄主题。
 *
 * 简化声明（与引擎注释一致）：
 * 1. 点炮只取「一家胡」（标准血战支持一炮多响，这里按优先级单家结算）。
 * 2. 流局不做「查大叫 / 查花猪」赔付，直接按已胡番数结算。
 * 3. 在线开房（服务端权威发牌）为后续项，本期为本地同屏。
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import * as M from '@/utils/games/mahjong.js'
import { sfx, setMuted, isMuted } from '@/utils/games/sfx'
import { loadGame, saveGame } from '@/utils/gameSave'
import { reportSettle } from '@/api/gameEconomy'

const props = defineProps({
  gameKey: { type: String, default: 'mahjong' },
  initialMode: { type: String, default: 'solo' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: true },
  big: { type: Boolean, default: false },
  joinRoomId: { type: Number, default: 0 },
})
const emit = defineEmits(['exit', 'room-lock', 'room-unlock'])

const SAVE_KEY = 'mahjong'
const SEAT_LABEL = { 0: '你', 1: '右家', 2: '对家', 3: '左家' }
const AI_AVATARS = { 1: '🐯', 2: '🦊', 3: '🐼' }
const REACT_NAME = { hu: '胡', kong: '杠', pong: '碰' }
const PANEL_SEATS = [2, 3, 1]
const STAKE = 100
const BASE = 10

/* ---------- 状态 ---------- */
const mode = ref(props.initialMode || 'solo')
const phase = ref('dingque')        // dingque | playing | settled
const roundNo = ref(1)
const dealer = ref(0)
const wall = ref([])
const hands = ref([[], [], [], []])
const melds = ref([[], [], [], []])
const discards = ref([[], [], [], []])
const missing = ref(['', '', '', ''])
const out = ref([false, false, false, false])   // 已胡下桌
const turn = ref(0)
const drawn = ref(null)
const lastDiscard = ref(null)
// 注意：牌堆 id 从 0 起，不能用 0 当「未选中」哨兵，否则 id=0 那张牌永远打不出去
const selId = ref(null)
const logs = ref([])
const huResults = ref([])
const result = ref(null)
const pending = ref(null)          // { seat, from, tile, kinds }
const reactQueue = ref([])
const reactFrom = ref(null)
const dingqueSeat = ref(0)
const toast = ref('')
const muted = ref(isMuted())

/* ---------- 派生 ---------- */
const HUMAN_SEATS = computed(() => {
  if (mode.value === 'solo') return [0]
  if (mode.value === 'duo') return [0, 2]
  return [0, 1, 2, 3]
})
function isHuman(s) { return HUMAN_SEATS.value.includes(s) }

const viewSeat = computed(() => {
  if (phase.value === 'dingque') return dingqueSeat.value
  if (isHuman(turn.value) && !out.value[turn.value]) return turn.value
  return HUMAN_SEATS.value[0]
})
const viewHand = computed(() => hands.value[viewSeat.value] || [])
const viewDrawn = computed(() =>
  (turn.value === viewSeat.value && drawn.value) ? drawn.value : null)
const canDiscard = computed(() =>
  phase.value === 'playing' && !pending.value
  && isHuman(turn.value) && !out.value[turn.value] && turn.value === viewSeat.value)

const poolOfView = computed(() =>
  viewDrawn.value ? viewHand.value.concat([viewDrawn.value]) : viewHand.value.slice())

const canZimo = computed(() => {
  if (!canDiscard.value) return false
  return M.canHu(poolOfView.value, melds.value[turn.value].length, missing.value[turn.value])
})
const ankongs = computed(() => {
  if (!canDiscard.value) return []
  return M.findAnkongs(hands.value[turn.value])
})
const bugangs = computed(() => {
  if (!canDiscard.value) return []
  const h = drawn.value ? hands.value[turn.value].concat([drawn.value]) : hands.value[turn.value]
  return M.findBugangs(h, melds.value[turn.value])
})

const statusLine = computed(() => {
  if (phase.value === 'settled') return '本局结束，点「再来一局」继续'
  if (phase.value === 'dingque') return '请先定缺'
  if (pending.value) return '请选择「碰 / 杠 / 胡 / 过」'
  if (!isHuman(turn.value)) return `${SEAT_LABEL[turn.value]} 思考中…`
  if (turn.value !== viewSeat.value) return `轮到 ${SEAT_LABEL[turn.value]}`
  return '点一张牌选中，再点「出牌」'
})

/** 听牌提示：打哪张、听哪些 */
const tingInfo = computed(() => {
  if (phase.value !== 'playing') return []
  const seat = viewSeat.value
  const h = hands.value[seat]
  if (h.length % 3 !== 1) return []
  const mc = melds.value[seat].length
  const miss = missing.value[seat]
  const res = []
  const seen = new Set()
  for (const t of h) {
    const k = `${t.suit}${t.rank}`
    if (seen.has(k)) continue
    seen.add(k)
    const rest = h.filter(x => x.id !== t.id)
    const waits = M.tingTiles(rest, mc, miss)
    if (waits.length) res.push({ tile: t, waits })
  }
  return res
})

/* ---------- 小工具 ---------- */
function suitCls(t) {
  if (!t) return ''
  return t.suit === 'm' ? 'is-wan' : t.suit === 's' ? 'is-tiao' : 'is-tong'
}
function tileText(t) { return t ? `${t.rank}${M.SUIT_NAME[t.suit]}` : '' }
function meldTiles(md) {
  const n = md.type === 'pong' ? 3 : 4
  return Array.from({ length: n }, () => md.tile)
}
function backCount(s) { return hands.value[s].length }
function countIn(hand, tile) {
  return hand.filter(t => t.suit === tile.suit && t.rank === tile.rank).length
}
function seatName(s) {
  if (isHuman(s)) return s === 0 ? '你' : `玩家${s === 2 ? '二' : s === 1 ? '一' : '三'}`
  return SEAT_LABEL[s]
}
function seatAvatar(s) {
  if (isHuman(s)) return s === 0 ? '🙂' : '🙃'
  return AI_AVATARS[s]
}
function isTurn(s) { return phase.value === 'playing' && turn.value === s }
function seatAreaCls(s) {
  return s === 2 ? 'mj-seat-top' : s === 3 ? 'mj-seat-left' : 'mj-seat-right'
}
function seatCls(s) {
  return { 'is-active': isTurn(s) && !out.value[s], 'is-out': out.value[s] }
}
function seatSub(s) {
  if (out.value[s]) return '已胡下桌'
  return `${hands.value[s].length} 张 · 副露 ${melds.value[s].length}`
}
function suitCount(seat, suit) {
  return hands.value[seat].filter(t => t.suit === suit).length
}
function toggleMute() { muted.value = !muted.value; setMuted(muted.value) }
let toastTimer = null
function toastMsg(t) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1900)
}
function log(t) { logs.value.unshift(t); logs.value = logs.value.slice(0, 8) }

/* ---------- 开局 ---------- */
function newRound() {
  const deck = M.shuffle(M.buildDeck())
  wall.value = deck.slice(52)
  hands.value = [0, 1, 2, 3].map(i => M.sortHand(deck.slice(i * 13, i * 13 + 13)))
  melds.value = [[], [], [], []]
  discards.value = [[], [], [], []]
  missing.value = ['', '', '', '']
  out.value = [false, false, false, false]
  huResults.value = []
  result.value = null
  pending.value = null
  reactQueue.value = []
  reactFrom.value = null
  drawn.value = null
  lastDiscard.value = null
  selId.value = null
  logs.value = []
  phase.value = 'dingque'
  dealer.value = (roundNo.value - 1) % 4
  pendingDingqueHumans.value = []
  sfx.deal()
  startDingque()
}

function nextRound() {
  roundNo.value++
  newRound()
}

const pendingDingqueHumans = ref([])

function startDingque() {
  const humans = HUMAN_SEATS.value.slice()
  // AI 先自动定缺
  for (const s of [0, 1, 2, 3]) if (!isHuman(s)) missing.value[s] = autoMissing(s)
  if (humans.length) {
    dingqueSeat.value = humans[0]
    pendingDingqueHumans.value = humans.slice(1)
  } else {
    beginPlay()
  }
}

function autoMissing(seat) {
  let best = M.SUITS[0], bestN = Infinity
  for (const s of M.SUITS) {
    const n = suitCount(seat, s)
    if (n < bestN) { bestN = n; best = s }
  }
  return best
}

function chooseMissing(suit) {
  missing.value[dingqueSeat.value] = suit
  sfx.pick()
  const rest = pendingDingqueHumans.value
  if (rest.length) {
    dingqueSeat.value = rest[0]
    pendingDingqueHumans.value = rest.slice(1)
  } else {
    beginPlay()
  }
}

function beginPlay() {
  phase.value = 'playing'
  turn.value = dealer.value
  drawFor(dealer.value)
}

/* ---------- 摸牌 ---------- */
function drawFor(seat) {
  if (phase.value !== 'playing') return
  if (wall.value.length === 0) return endRound('liuju')
  turn.value = seat
  drawn.value = wall.value.pop()
  selId.value = null
  sfx.pick()
  if (isHuman(seat)) return
  scheduleAI()
}

function nextDraw(from) {
  if (phase.value !== 'playing') return
  if (checkRoundEnd()) return
  let s = from
  for (let i = 1; i <= 4; i++) {
    const t = (from + i) % 4
    if (!out.value[t]) { s = t; break }
  }
  drawFor(s)
}

function checkRoundEnd() {
  if (out.value.filter(Boolean).length >= 3) { endRound('allhu'); return true }
  return false
}

/* ---------- 出牌 ---------- */
function doDiscard(seat, tile) {
  const h = hands.value[seat]
  if (drawn.value && drawn.value.id === tile.id) {
    drawn.value = null
  } else {
    const i = h.findIndex(t => t.id === tile.id)
    if (i >= 0) h.splice(i, 1)
    if (drawn.value) { h.push(drawn.value); drawn.value = null }
    hands.value[seat] = M.sortHand(h)
  }
  discards.value[seat].push(tile)
  lastDiscard.value = { seat, tile }
  selId.value = null
  log(`${seatName(seat)} 打出 ${tileText(tile)}`)
  sfx.play()
  resolveReactions(seat, tile)
}

/* ---------- 反应（胡 / 杠 / 碰） ---------- */
function resolveReactions(from, tile) {
  if (phase.value !== 'playing') return
  // 1) 胡（点炮）：优先级最高
  const huSeats = []
  for (const s of [0, 1, 2, 3]) {
    if (s === from || out.value[s]) continue
    if (M.canHu(hands.value[s].concat([tile]), melds.value[s].length, missing.value[s])) huSeats.push(s)
  }
  if (huSeats.length) {
    const aiHu = huSeats.filter(s => !isHuman(s))
    for (const s of aiHu) doHu(s, tile, from, false)
    const humanSeat = huSeats.find(s => isHuman(s))
    if (humanSeat != null && !out.value[humanSeat]) {
      pending.value = { seat: humanSeat, from, tile, kinds: ['hu'] }
      return
    }
    if (checkRoundEnd()) return
    nextDraw(from)
    return
  }
  // 2) 杠 / 碰：按座次
  const q = []
  for (let off = 1; off <= 3; off++) {
    const s = (from + off) % 4
    if (out.value[s]) continue
    const kinds = []
    if (countIn(hands.value[s], tile) >= 3) kinds.push('kong')
    if (countIn(hands.value[s], tile) >= 2) kinds.push('pong')
    if (kinds.length) q.push({ seat: s, kinds })
  }
  reactQueue.value = q
  reactFrom.value = { from, tile }
  stepReactions()
}

function stepReactions() {
  const q = reactQueue.value
  const rf = reactFrom.value
  if (!rf) return
  while (q.length) {
    const cur = q[0]
    const s = cur.seat
    if (out.value[s]) { q.shift(); continue }
    if (isHuman(s)) {
      pending.value = { seat: s, from: rf.from, tile: rf.tile, kinds: cur.kinds }
      return
    }
    if (cur.kinds.includes('kong')
      && M.aiWantKong(hands.value[s], rf.tile, melds.value[s].length, missing.value[s], { level: 'normal' })) {
      q.shift(); doKongFromDiscard(s, rf.tile, rf.from); return
    }
    if (cur.kinds.includes('pong')
      && M.aiWantPong(hands.value[s], rf.tile, melds.value[s].length, missing.value[s], { level: 'normal' })) {
      q.shift(); doPong(s, rf.tile, rf.from); return
    }
    q.shift()
  }
  nextDraw(rf.from)
}

function takeFromDiscard(from) {
  const pile = discards.value[from]
  if (pile.length) pile.pop()
}

function doPong(seat, tile, from) {
  const h = hands.value[seat]
  let removed = 0
  for (let i = h.length - 1; i >= 0 && removed < 2; i--) {
    if (h[i].suit === tile.suit && h[i].rank === tile.rank) { h.splice(i, 1); removed++ }
  }
  hands.value[seat] = M.sortHand(h)
  melds.value[seat].push({ type: 'pong', tile, from })
  takeFromDiscard(from)
  drawn.value = null
  turn.value = seat
  selId.value = null
  log(`${seatName(seat)} 碰 ${tileText(tile)}`)
  sfx.pong()
  if (isHuman(seat)) return
  scheduleAI()
}

function doKongFromDiscard(seat, tile, from) {
  const h = hands.value[seat]
  let removed = 0
  for (let i = h.length - 1; i >= 0 && removed < 3; i--) {
    if (h[i].suit === tile.suit && h[i].rank === tile.rank) { h.splice(i, 1); removed++ }
  }
  hands.value[seat] = M.sortHand(h)
  melds.value[seat].push({ type: 'kong', tile, from })
  takeFromDiscard(from)
  log(`${seatName(seat)} 杠 ${tileText(tile)}`)
  sfx.kong()
  turn.value = seat
  drawReplacement(seat)
}

function doAnkong(tileInfo) {
  const seat = turn.value
  const h = hands.value[seat]
  let removed = 0
  for (let i = h.length - 1; i >= 0 && removed < 4; i--) {
    if (h[i].suit === tileInfo.suit && h[i].rank === tileInfo.rank) { h.splice(i, 1); removed++ }
  }
  hands.value[seat] = M.sortHand(h)
  melds.value[seat].push({ type: 'ankong', tile: tileInfo })
  log(`${seatName(seat)} 暗杠 ${tileText(tileInfo)}`)
  sfx.kong()
  drawReplacement(seat)
}

function doBugang(tileInfo) {
  const seat = turn.value
  const h = hands.value[seat]
  let removed = false
  if (drawn.value && drawn.value.suit === tileInfo.suit && drawn.value.rank === tileInfo.rank) {
    drawn.value = null; removed = true
  } else {
    const i = h.findIndex(t => t.suit === tileInfo.suit && t.rank === tileInfo.rank)
    if (i >= 0) { h.splice(i, 1); removed = true }
    if (drawn.value) { h.push(drawn.value); drawn.value = null }
    hands.value[seat] = M.sortHand(h)
  }
  if (!removed) return
  const md = melds.value[seat].find(m => m.type === 'pong' && m.tile.suit === tileInfo.suit && m.tile.rank === tileInfo.rank)
  if (md) md.type = 'bugang'
  log(`${seatName(seat)} 补杠 ${tileText(tileInfo)}`)
  sfx.kong()
  drawReplacement(seat)
}

function drawReplacement(seat) {
  if (wall.value.length === 0) return endRound('liuju')
  drawn.value = wall.value.pop()
  turn.value = seat
  selId.value = null
  if (isHuman(seat)) return
  scheduleAI()
}

/* ---------- 胡 ---------- */
function doHu(seat, tile, from, zimo) {
  if (out.value[seat]) return
  out.value[seat] = true
  const winning = zimo
    ? (drawn.value ? hands.value[seat].concat([drawn.value]) : hands.value[seat].slice())
    : hands.value[seat].concat([tile])
  const sc = M.scoreHu(winning, melds.value[seat], {})
  huResults.value.push({ seat, fan: sc.fan, names: sc.names, zimo, from })
  log(`${seatName(seat)} ${zimo ? '自摸' : '胡'} ${sc.names.join('·')} ${sc.fan}番`)
  sfx.win()
  toastMsg(`${seatName(seat)} ${zimo ? '自摸' : '胡牌'}！${sc.names.join(' · ')} ${sc.fan} 番`)
}

function doZimo() {
  if (!canZimo.value) return
  const seat = turn.value
  doHu(seat, null, null, true)
  if (checkRoundEnd()) return
  nextDraw(seat)
}

/* ---------- 人类操作 ---------- */
function pick(t) {
  if (!canDiscard.value) return
  selId.value = selId.value === t.id ? null : t.id
  sfx.pick()
}
function discardSel() {
  if (!canDiscard.value || selId.value === null) return
  const pool = poolOfView.value
  const t = pool.find(x => x.id === selId.value)
  if (!t) return
  doDiscard(turn.value, t)
}
function doHint() {
  if (!canDiscard.value) return
  if (tingInfo.value.length) {
    const first = tingInfo.value[0]
    selId.value = first.tile.id
    toastMsg(`打 ${tileText(first.tile)} 可听 ${first.waits.map(tileText).join(' / ')}`)
  } else {
    const d = M.aiDiscard(poolOfView.value, melds.value[turn.value].length, missing.value[turn.value], { level: 'normal' })
    if (d) { selId.value = d.id; toastMsg(`建议打 ${tileText(d)}`) }
  }
}
function onReact(kind) {
  const p = pending.value
  if (!p) return
  if (kind === 'pass') {
    pending.value = null
    reactQueue.value.shift()
    stepReactions()
    return
  }
  if (kind === 'hu') {
    pending.value = null
    doHu(p.seat, p.tile, p.from, false)
    if (checkRoundEnd()) return
    nextDraw(p.from)
    return
  }
  if (kind === 'pong') {
    pending.value = null
    reactQueue.value.shift()
    doPong(p.seat, p.tile, p.from)
    return
  }
  if (kind === 'kong') {
    pending.value = null
    reactQueue.value.shift()
    doKongFromDiscard(p.seat, p.tile, p.from)
  }
}

/* ---------- AI ---------- */
let aiTimer = null
function scheduleAI() {
  clearTimeout(aiTimer)
  if (phase.value !== 'playing') return
  if (isHuman(turn.value) || out.value[turn.value]) return
  aiTimer = setTimeout(aiTurn, 640)
}
function aiTurn() {
  if (phase.value !== 'playing') return
  const s = turn.value
  if (isHuman(s) || out.value[s]) return
  const full = drawn.value ? hands.value[s].concat([drawn.value]) : hands.value[s].slice()
  const mc = melds.value[s].length
  const miss = missing.value[s]
  // 自摸
  if (M.canHu(full, mc, miss)) {
    doHu(s, null, null, true)
    if (checkRoundEnd()) return
    nextDraw(s)
    return
  }
  // 暗杠 / 补杠
  const aks = M.findAnkongs(hands.value[s])
  if (aks.length) { doAnkong(aks[0]); return }
  const bgs = M.findBugangs(full, melds.value[s])
  if (bgs.length) { doBugang(bgs[0]); return }
  // 出牌
  const d = M.aiDiscard(full, mc, miss, { level: 'normal' })
  if (d) doDiscard(s, d)
}

/* ---------- 结算 ---------- */
function computeDelta() {
  let delta = 0
  for (const r of huResults.value) {
    const gain = BASE * r.fan
    if (r.zimo) {
      if (r.seat === 0) delta += 3 * gain
      else delta -= gain
    } else {
      if (r.seat === 0) delta += 2 * gain
      else if (r.from === 0) delta -= 2 * gain
    }
  }
  return delta
}

function endRound(reason) {
  clearTimeout(aiTimer)
  phase.value = 'settled'
  pending.value = null
  const delta = computeDelta()
  const win = delta > 0
  result.value = {
    reason,
    hus: huResults.value.slice(),
    delta,
    title: (reason === 'liuju' && !huResults.value.length)
      ? '流局'
      : delta > 0 ? '本局小赚' : delta < 0 ? '本局小亏' : '本局平局',
  }
  sfx.settle()
  if (win) sfx.win()
  else if (delta < 0) sfx.lose()
  saveState()
  reportSettle('mahjong', win ? 'win' : 'lose', win ? STAKE : -STAKE, STAKE).catch(() => {})
}

/* ---------- 存档 ---------- */
function saveState() {
  saveGame(SAVE_KEY, {
    mode: mode.value,
    summary: `第 ${roundNo.value} 局 · ${huResults.value.length} 家胡`,
    roundNo: roundNo.value,
  })
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || s.mode !== mode.value) return false
  roundNo.value = s.roundNo || 1
  return true
}

/* ---------- 退出 ---------- */
function doExit() {
  saveState()
  emit('exit')
}

/* ---------- 生命周期 ---------- */
onMounted(() => {
  if (props.resume && restoreLocal()) toastMsg('已接着上一局继续')
  newRound()
})
onBeforeUnmount(() => {
  clearTimeout(aiTimer)
  clearTimeout(toastTimer)
})
</script>

<style scoped>
.mj {
  display: flex; flex-direction: column; gap: 10px;
  padding: 12px 16px 14px; min-height: 600px;
}
.mj.is-big { min-height: calc(100vh - 150px); }
.mj-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* ===== 牌桌 ===== */
.mj-table {
  flex: 1; min-height: 0;
  display: grid; gap: 8px;
  grid-template-columns: 1fr minmax(0, 1.3fr) 1fr;
  grid-template-rows: auto 1fr;
  grid-template-areas: "top top top" "left center right";
  padding: 10px; border-radius: 16px;
  background: radial-gradient(90% 70% at 50% 40%, rgba(255, 255, 255, .07), transparent 70%);
  border: 1px solid var(--gt-line);
}
.mj-seat { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.mj-seat-top { grid-area: top; align-items: center; }
.mj-seat-left { grid-area: left; align-items: flex-start; }
.mj-seat-right { grid-area: right; align-items: flex-end; }
.mj-seat-top .gt-seat { max-width: 260px; }

.mj-melds { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; }
.mj-backs { display: flex; flex-wrap: wrap; gap: 2px; justify-content: center; }
.mj-seat-left .mj-backs, .mj-seat-right .mj-backs { max-width: 100%; }
.mj-discards {
  display: flex; flex-wrap: wrap; gap: 2px; justify-content: center;
  max-width: 240px; max-height: 96px; overflow-y: auto;
  padding: 4px; border-radius: 8px; background: rgba(0, 0, 0, .18);
  border: 1px solid var(--gt-line);
}
.mj-seat-left .mj-discards, .mj-seat-right .mj-discards { max-width: 132px; }

/* 中央 */
.mj-center {
  grid-area: center; align-items: center; justify-content: center; gap: 8px;
  padding: 12px; border-radius: 14px;
  background: rgba(0, 0, 0, .22); border: 1px solid var(--gt-line);
}
.mj-center-head { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.mj-center-tile { min-height: 60px; display: grid; place-items: center; }
.mj-log { display: flex; flex-direction: column; align-items: center; gap: 1px; }
.mj-log span { font-size: 11px; color: rgba(255, 255, 255, .5); }

/* ===== 听牌条 ===== */
.mj-tingbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 7px 12px; border-radius: 12px;
  background: rgba(233, 200, 119, .1); border: 1px solid rgba(233, 200, 119, .3);
}
.mj-ting-label { font-size: 11.5px; font-weight: 700; color: var(--gt-gold); }
.mj-ting-item { font-size: 11.5px; color: var(--gt-ink-dim); }
.mj-ting-item b { color: var(--gt-ink); font-weight: 700; }
.mj-ting-none { font-size: 11.5px; color: var(--gt-ink-dim); }

/* ===== 底部 ===== */
.mj-bottom { display: flex; flex-direction: column; gap: 8px; }
.mj-handbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mj-hand {
  display: flex; gap: 3px; overflow-x: auto; overflow-y: visible;
  padding: 16px 4px 10px; min-height: 96px; align-items: flex-end;
  scrollbar-width: thin;
}
.mj-hand-empty { margin: 0 auto; font-size: 12px; color: var(--gt-ink-dim); }
.mj-actions { justify-content: center; }

/* 花色着色 */
.gt-tile.is-wan { color: #b3261e; }
.gt-tile.is-tiao { color: #1f6b3a; }
.gt-tile.is-tong { color: #1b4f8a; }
.gt-tile.is-drawn {
  margin-left: 12px;
  box-shadow: 0 0 0 2px var(--gt-gold), 0 4px 0 #b9b19b, 0 12px 18px -10px rgba(0, 0, 0, .9);
}
.gt-over-card em { font-style: normal; opacity: .7; }

@media (max-width: 900px) {
  .mj { min-width: 860px; }
}
</style>

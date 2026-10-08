<template>
  <div class="gt-landscape">
    <div ref="rootRef" class="gt-shell mj" :class="{ 'is-big': big }" :style="{ '--gt-h': rootH + 'px' }">
      <!-- ===== 顶栏 ===== -->
      <header class="mj-top">
        <span class="gt-title">四川麻将</span>
        <span class="gt-pill gold">血战到底 · 第 {{ roundNo }} 局</span>
        <span class="gt-pill">余牌 {{ wall.length }}</span>
        <span v-if="myMissing" class="gt-pill">你的缺门 {{ M.SUIT_NAME[myMissing] }}</span>
        <span class="gt-spacer"></span>
        <button class="gt-btn sm ghost" :title="muted ? '取消静音' : '静音'" @click="toggleMute">
          {{ muted ? '🔇' : '🔊' }}
        </button>
        <button class="gt-btn sm ghost" @click="doExit">退出对局</button>
      </header>

      <!-- ===== 牌桌：三家席位 + 中央（四方弃牌） ===== -->
      <div class="mj-table">
        <!-- 对家 / 左家 / 右家：席位 + 副露 + 手牌背面（左右家竖排，对家横排） -->
        <div
          v-for="p in PANEL_SEATS"
          :key="p.seat"
          class="mj-seat"
          :class="p.cls"
        >
          <div class="gt-seat" :class="seatCls(p.seat)">
            <span class="gt-seat-av">{{ seatAvatar(p.seat) }}</span>
            <span class="gt-seat-tx">
              <b class="gt-seat-name">{{ seatName(p.seat) }}</b>
              <i class="gt-seat-sub">{{ seatSub(p.seat) }}</i>
            </span>
            <span v-if="isTurn(p.seat) && !out[p.seat]" class="gt-seat-badge">出牌中</span>
            <span v-else-if="out[p.seat]" class="gt-seat-badge">已胡</span>
          </div>

          <div v-if="melds[p.seat].length" class="mj-melds" :class="p.dir">
            <span v-for="(md, i) in melds[p.seat]" :key="i" class="gt-meld">
              <span
                v-for="(t, k) in meldTiles(md)"
                :key="k"
                class="gt-tile mini"
                :class="suitCls(t)"
              ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
            </span>
          </div>

          <div class="mj-backs" :class="p.dir">
            <span v-for="n in backCount(p.seat)" :key="n" class="gt-tile mini is-back"></span>
          </div>
        </div>

        <!-- 中央：四方弃牌（上=对家 / 下=自己 / 左=左家 / 右=右家）+ 中心信息 -->
        <div class="mj-center">
          <div class="mj-dis mj-dis-up">
            <span
              v-for="t in discards[2]"
              :key="t.id"
              class="gt-tile mini"
              :class="suitCls(t)"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>

          <div class="mj-dis mj-dis-left">
            <span
              v-for="t in discards[3]"
              :key="t.id"
              class="gt-tile mini"
              :class="suitCls(t)"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>

          <div class="mj-center-info">
            <span v-if="lastDiscard" class="mj-last-tile gt-anim-play">
              <span class="gt-tile"><MahjongTileFace :suit="faceSuit(lastDiscard.tile)" :rank="lastDiscard.tile.rank" /></span>
            </span>
            <b v-if="lastDiscard" class="mj-center-who">{{ seatName(lastDiscard.seat) }} 打出</b>
            <b v-else class="mj-center-who">开局</b>
            <i v-if="phase === 'playing' && !pending" class="mj-center-turn">轮到 {{ seatName(turn) }}</i>
            <div class="mj-log">
              <span v-for="(l, i) in logs.slice(0, 3)" :key="i">{{ l }}</span>
            </div>
          </div>

          <div class="mj-dis mj-dis-right">
            <span
              v-for="t in discards[1]"
              :key="t.id"
              class="gt-tile mini"
              :class="suitCls(t)"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>

          <div class="mj-dis mj-dis-down">
            <span
              v-for="t in discards[0]"
              :key="t.id"
              class="gt-tile mini"
              :class="suitCls(t)"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
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
          <!-- 全屏时顶栏被隐藏，余牌 / 缺门这类关键信息挪到这里，保证一直可见 -->
          <span class="gt-pill">余牌 {{ wall.length }}</span>
          <span v-if="myMissing" class="gt-pill">缺门 {{ M.SUIT_NAME[myMissing] }}</span>
          <span v-if="melds[viewSeat]?.length" class="gt-pill">副露 {{ melds[viewSeat].length }} 组</span>
          <span class="gt-spacer"></span>
          <span class="gt-sub">{{ statusLine }}</span>
        </div>

        <div class="mj-hand" :style="{ '--ntiles': Math.max(1, handTiles.length) }">
          <span
            v-for="t in viewHand"
            :key="t.id"
            class="gt-tile"
            :class="[suitCls(t), { pickable: canDiscard, 'is-sel': selId === t.id }]"
            @click="pick(t)"
          >
            <MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" />
          </span>
          <span
            v-if="viewDrawn"
            class="gt-tile is-drawn"
            :class="[suitCls(viewDrawn), { pickable: canDiscard, 'is-sel': selId === viewDrawn.id }]"
            @click="pick(viewDrawn)"
          >
            <MahjongTileFace :suit="faceSuit(viewDrawn)" :rank="viewDrawn.rank" />
          </span>
          <p v-if="!handTiles.length" class="mj-hand-empty">— 无手牌 —</p>
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
      <div v-if="showDingque" class="gt-over">
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
 * 3. 在线开房（v2.44）：服务端权威发牌，前端只渲染投影、动作 emit('act') 上抛；
 *    本地同屏（solo/duo/quad）逻辑完全不变，在线分支统一走 `isOnline`。
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import * as M from '@/utils/games/mahjong.js'
import { sfx, setMuted, isMuted } from '@/utils/games/sfx'
import { loadGame, saveGame } from '@/utils/gameSave'
import { reportSettle } from '@/api/gameEconomy'
import MahjongTileFace from '@/components/games/MahjongTileFace.vue'
import { useRootHeight } from '@/composables/useRootHeight'

const props = defineProps({
  gameKey: { type: String, default: 'mahjong' },
  initialMode: { type: String, default: 'solo' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: true },
  big: { type: Boolean, default: false },
  joinRoomId: { type: Number, default: 0 },
  // v2.44 在线：服务端投影渲染，动作 emit 给等待房页转 /act
  online: { type: Boolean, default: false },
  onlineView: { type: Object, default: null },
  onlineSeat: { type: Number, default: 0 },
  seatNames: { type: Array, default: () => [] },
  acting: { type: Boolean, default: false },
  isHost: { type: Boolean, default: false },
})
const emit = defineEmits(['exit', 'room-lock', 'room-unlock', 'act', 'rematch'])

const SAVE_KEY = 'mahjong'
const SEAT_LABEL = { 0: '你', 1: '右家', 2: '对家', 3: '左家' }
const AI_AVATARS = { 1: '🐯', 2: '🦊', 3: '🐼' }
const REACT_NAME = { hu: '胡', kong: '杠', pong: '碰' }
/** 三家席位的方位与排布方向：对家横排，左右家竖排（v2.46 起不再四个方向都横着摆） */
const PANEL_SEATS = [
  { seat: 2, cls: 'mj-seat-top', dir: 'is-h' },
  { seat: 3, cls: 'mj-seat-left', dir: 'is-v' },
  { seat: 1, cls: 'mj-seat-right', dir: 'is-v' },
]
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
const isOnline = computed(() => props.online)
const oSeat = computed(() => Number(props.onlineSeat ?? 0))
const HUMAN_SEATS = computed(() => {
  if (mode.value === 'solo') return [0]
  if (mode.value === 'duo') return [0, 2]
  return [0, 1, 2, 3]
})
function isHuman(s) { return HUMAN_SEATS.value.includes(s) }

const viewSeat = computed(() => {
  if (isOnline.value) return oSeat.value
  if (phase.value === 'dingque') return dingqueSeat.value
  if (isHuman(turn.value) && !out.value[turn.value]) return turn.value
  return HUMAN_SEATS.value[0]
})
/** 定缺浮层：在线只在轮到自己定缺时展示，避免暴露/误操作他人缺门 */
const showDingque = computed(() =>
  phase.value === 'dingque'
  && (!isOnline.value || (props.onlineView?.me?.options || []).includes('missing')))
/** 顶栏「你的缺门」：本地固定座位 0，在线取自己座位 */
const myMissing = computed(() => (isOnline.value ? missing.value[oSeat.value] : missing.value[0]))
const viewHand = computed(() => hands.value[viewSeat.value] || [])
const viewDrawn = computed(() =>
  (turn.value === viewSeat.value && drawn.value) ? drawn.value : null)
/** 手牌 + 刚摸的那张（手牌尺寸按这个数均分可用宽度） */
const handTiles = computed(() =>
  viewDrawn.value ? viewHand.value.concat([viewDrawn.value]) : viewHand.value)
const canDiscard = computed(() => {
  if (isOnline.value) {
    if (props.acting) return false
    return (props.onlineView?.me?.options || []).includes('discard')
  }
  return phase.value === 'playing' && !pending.value
  && isHuman(turn.value) && !out.value[turn.value] && turn.value === viewSeat.value
})

const poolOfView = computed(() =>
  viewDrawn.value ? viewHand.value.concat([viewDrawn.value]) : viewHand.value.slice())

const canZimo = computed(() => {
  if (isOnline.value) {
    if (props.acting) return false
    return (props.onlineView?.me?.options || []).includes('hu')
  }
  if (!canDiscard.value) return false
  return M.canHu(poolOfView.value, melds.value[turn.value].length, missing.value[turn.value])
})
const ankongs = computed(() => {
  if (isOnline.value) {
    if (props.acting || !(props.onlineView?.me?.options || []).includes('ankong')) return []
    return props.onlineView?.me?.ankongs || []
  }
  if (!canDiscard.value) return []
  return M.findAnkongs(hands.value[turn.value])
})
const bugangs = computed(() => {
  if (isOnline.value) {
    if (props.acting || !(props.onlineView?.me?.options || []).includes('bugang')) return []
    return props.onlineView?.me?.bugangs || []
  }
  if (!canDiscard.value) return []
  const h = drawn.value ? hands.value[turn.value].concat([drawn.value]) : hands.value[turn.value]
  return M.findBugangs(h, melds.value[turn.value])
})

const statusLine = computed(() => {
  if (isOnline.value) {
    if (phase.value === 'settled') return '本局结束，等房主「再来一局」'
    if (phase.value === 'dingque') {
      return turn.value === oSeat.value ? '请选择缺门' : `等 ${seatName(turn.value)} 定缺…`
    }
    if (pending.value) return '请选择「碰 / 杠 / 胡 / 过」'
    if (turn.value === oSeat.value) return '点一张牌选中，再点「出牌」'
    return `等 ${seatName(turn.value)} 行动…`
  }
  if (phase.value === 'settled') return '本局结束，点「再来一局」继续'
  if (phase.value === 'dingque') return '请先定缺'
  if (pending.value) return '请选择「碰 / 杠 / 胡 / 过」'
  if (!isHuman(turn.value)) return `${SEAT_LABEL[turn.value]} 思考中…`
  if (turn.value !== viewSeat.value) return `轮到 ${SEAT_LABEL[turn.value]}`
  return '点一张牌选中，再点「出牌」'
})

/** 听牌提示：打哪张、听哪些。在线仅在自己可出牌时计算（只读自己的手牌，不涉暗信息） */
const tingInfo = computed(() => {
  if (phase.value !== 'playing') return []
  if (isOnline.value && !canDiscard.value) return []
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
/** 花色键（m/s/p）→ 牌面组件的花纹名 */
function faceSuit(t) {
  if (!t) return 'wan'
  return t.suit === 'm' ? 'wan' : t.suit === 's' ? 'tiao' : 'tong'
}
function suitCls(t) {
  if (!t) return ''
  return t.suit === 'm' ? 'is-wan' : t.suit === 's' ? 'is-tiao' : 'is-tong'
}
function tileText(t) { return t ? `${t.rank}${M.SUIT_NAME[t.suit]}` : '' }
function meldTiles(md) {
  const n = md.type === 'pong' ? 3 : 4
  return Array.from({ length: n }, () => md.tile)
}
function backCount(s) {
  if (isOnline.value) return props.onlineView?.players?.[s]?.hand_count ?? 0
  return hands.value[s].length
}
function countIn(hand, tile) {
  return hand.filter(t => t.suit === tile.suit && t.rank === tile.rank).length
}
function seatName(s) {
  if (isOnline.value) {
    if (s === oSeat.value) return '你'
    return props.seatNames[s] || `座位${s + 1}`
  }
  if (isHuman(s)) return s === 0 ? '你' : `玩家${s === 2 ? '二' : s === 1 ? '一' : '三'}`
  return SEAT_LABEL[s]
}
function seatAvatar(s) {
  if (isOnline.value) {
    if (s === oSeat.value) return '🙂'
    // 服务端 AI 席位命名为「机器人N」（见 game_tables 补位逻辑），据此区分机器人 / 真人
    return String(props.seatNames[s] || '').startsWith('机器人') ? '🤖' : '🙃'
  }
  if (isHuman(s)) return s === 0 ? '🙂' : '🙃'
  return AI_AVATARS[s]
}
function isTurn(s) { return phase.value === 'playing' && turn.value === s }
function seatCls(s) {
  return { 'is-active': isTurn(s) && !out.value[s], 'is-out': out.value[s] }
}
function seatSub(s) {
  if (out.value[s]) return '已胡下桌'
  if (isOnline.value) {
    const p = props.onlineView?.players?.[s]
    return `${p?.hand_count ?? 0} 张 · 副露 ${(p?.melds || []).length}`
  }
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

/* ---------- 在线：服务端投影 → 展示态 ---------- */
const PHASE_MAP = { missing: 'dingque', playing: 'playing', finished: 'settled' }
function syncFromView(v) {
  if (!v) return
  const me = v.me || {}
  // 服务端 me.hand 已含刚摸的 last_draw；本地模板把「刚摸」单列渲染，这里拆开避免重复
  const hand = (me.hand || []).slice()
  const drawnTile = me.last_draw || null
  if (drawnTile) {
    const i = hand.findIndex(t => t.id === drawnTile.id)
    if (i >= 0) hand.splice(i, 1)
  }
  const nextHands = [[], [], [], []]
  nextHands[oSeat.value] = hand
  hands.value = nextHands
  melds.value = [0, 1, 2, 3].map(s => v.players?.[s]?.melds || [])
  discards.value = [0, 1, 2, 3].map(s => v.players?.[s]?.discards || [])
  missing.value = [0, 1, 2, 3].map(s => v.players?.[s]?.missing || '')
  out.value = [0, 1, 2, 3].map(s => !!v.players?.[s]?.hu)
  turn.value = (v.turn === null || v.turn === undefined) ? -1 : v.turn
  drawn.value = drawnTile
  lastDiscard.value = v.last_discard || null
  wall.value = new Array(v.wall_left || 0)
  phase.value = PHASE_MAP[v.phase] || 'playing'
  roundNo.value = v.round_no || 1
  dealer.value = v.dealer ?? 0
  dingqueSeat.value = oSeat.value
  logs.value = v.logs || []
  const cl = v.claim
  pending.value = (cl && cl.seat === oSeat.value)
    ? { seat: cl.seat, from: cl.from, tile: cl.tile, kinds: (cl.options || []).slice() }
    : null
  const huInfo = v.result?.hu_info || {}
  const hus = (v.result?.hu || []).map(s => {
    const hi = huInfo[String(s)] || {}
    return { seat: s, fan: hi.fan || 0, names: hi.names || [], zimo: !!hi.zimo, from: hi.from }
  })
  huResults.value = hus
  if (v.result) {
    const delta = Number((v.result.deltas || {})[String(oSeat.value)] || 0)
    result.value = {
      reason: hus.length ? 'hu' : 'liuju',
      hus,
      delta,
      title: !hus.length ? '流局' : delta > 0 ? '本局小赚' : delta < 0 ? '本局小亏' : '本局平局',
    }
  } else {
    result.value = null
  }
  const ids = new Set(hand.map(t => t.id).concat(drawnTile ? [drawnTile.id] : []))
  if (selId.value !== null && !ids.has(selId.value)) selId.value = null
}
watch(() => props.onlineView, (v) => { if (isOnline.value) syncFromView(v) }, { immediate: true, deep: true })

/* ---------- 在线：动作上抛 ---------- */
function actOnline(action) { emit('act', action) }

/* ---------- 开局 ---------- */
function newRound() {
  if (isOnline.value) return   // 在线由服务端发牌，前端不本地开新局
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
  if (isOnline.value) { emit('rematch'); return }
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
  if (isOnline.value) { sfx.pick(); actOnline({ type: 'missing', suit }); return }
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
  if (isOnline.value) {
    sfx.kong()
    actOnline({ type: 'ankong', tile: { suit: tileInfo.suit, rank: tileInfo.rank } })
    return
  }
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
  if (isOnline.value) {
    sfx.kong()
    actOnline({ type: 'bugang', tile: { suit: tileInfo.suit, rank: tileInfo.rank } })
    return
  }
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
  if (isOnline.value) { sfx.win(); actOnline({ type: 'hu' }); return }
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
  if (isOnline.value) { sfx.play(); actOnline({ type: 'discard', tile_id: t.id }); return }
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
  if (isOnline.value) {
    if (kind === 'hu') sfx.win()
    else if (kind === 'kong') sfx.kong()
    else if (kind === 'pong') sfx.pong()
    actOnline({ type: kind })
    return
  }
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
  if (isOnline.value) return   // 在线由服务端 AI 推进
  if (phase.value !== 'playing') return
  if (isHuman(turn.value) || out.value[turn.value]) return
  aiTimer = setTimeout(aiTurn, 640)
}
function aiTurn() {
  if (isOnline.value) return
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
  // 在线结算由服务端负责，本地不再重复上报经济
  if (!isOnline.value) reportSettle('mahjong', win ? 'win' : 'lose', win ? STAKE : -STAKE, STAKE).catch(() => {})
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
  if (!isOnline.value) saveState()
  emit('exit')
}

/* ---------- 生命周期 ---------- */
/* ---------- 尺寸基准：把实际渲染高度写进 --gt-h，迷你牌/手牌据此定尺寸 ---------- */
const { rootRef, rootH } = useRootHeight()

onMounted(() => {
  if (isOnline.value) { syncFromView(props.onlineView); return }
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
  display: flex; flex-direction: column; gap: 8px;
  padding: 10px 14px 12px; min-height: 600px;
  /* --gt-h 由 JS 按实际渲染高度写入（上限 760），迷你牌/手牌尺寸都跟着它走，
     这样同一套 CSS 在手机横屏（约 390 高）与桌面大屏都能自动取到合适的牌面大小 */
  --mini-w: clamp(15px, calc(var(--gt-h, 420px) * 0.046), 25px);
  --mini-h: calc(var(--mini-w) * 1.38);
}
.mj.is-big { min-height: calc(100vh - 150px); }
.mj-top {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 7px 12px; border-radius: 12px;
  background: rgba(0, 0, 0, .24);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .07);
}
/* 全屏时顶栏让位给牌桌：余牌 / 缺门 / 副露 这些关键信息底栏（.mj-handbar）已经有一份，
   重复摆两处只会白占高度（与掼蛋 `.gd.is-big .gd-top` 同一策略） */
.mj.is-big .mj-top { display: none; }

/* ===== 牌桌：绿色绒布 + 四方围成矩形 ===== */
.mj-table {
  flex: 1; min-height: 0;
  display: grid; gap: 6px;
  /* 上（对家）独占一行；左右两家与中央同占中行 —— 四家 + 中央正好围成一个矩形 */
  grid-template-columns: auto minmax(0, 1fr) auto;
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas: "top top top" "left center right";
  padding: 10px 12px; border-radius: 18px;
  /* 绒布：中心一圈微亮的墨绿，外缘压暗，做出「桌面」而非「色块」的观感 */
  background:
    radial-gradient(120% 100% at 50% 0%, rgba(255, 255, 255, .1), transparent 55%),
    radial-gradient(100% 80% at 50% 50%, #227154 0%, #17573f 48%, #0d3a2b 100%);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, .08),
    inset 0 0 60px -10px rgba(0, 0, 0, .55);
}
.mj-seat { display: flex; flex-direction: column; gap: 4px; min-width: 0; min-height: 0; }
.mj-seat-top { grid-area: top; align-items: center; }
.mj-seat-left { grid-area: left; align-items: flex-start; }
.mj-seat-right { grid-area: right; align-items: flex-end; }
.mj-seat-top .gt-seat { max-width: 260px; }

/* ---------- 副露 / 手牌背面 ----------
 * 对家（上）横排；**左右两家必须竖排**。
 * 旧版靠 `flex-flow: column wrap` 自适应，但容器高度一不够就自动拆成「多列并排」——
 * 视觉上就是「左右两方还是横着摆」。现在改 flex column + 等分（flex: 1 1 0）：
 * 张数再多也**永远只有一列**，牌身跟着容器高度自动压扁，既不换列也不会溢出。 */
.mj-melds { display: flex; gap: 3px; }
.mj-backs { display: flex; gap: 2px; }
.mj-melds.is-h, .mj-backs.is-h {
  flex-flow: row wrap; justify-content: center; align-content: flex-start;
}
.mj-melds.is-v, .mj-backs.is-v {
  flex-direction: column; justify-content: center; align-items: center;
  min-height: 0; overflow: hidden;
}
.mj-melds.is-v { flex: 0 1 auto; }
.mj-backs.is-v { flex: 1 1 auto; }
/* 竖排的牌：宽度固定、高度按列等分 —— 牌背是纯色块，压扁不影响辨识；
   有牌面的副露靠 SVG 的 preserveAspectRatio 保比例，同样只会变小不会变形。 */
.mj-backs.is-v .gt-tile { flex: 1 1 0; height: auto; min-height: 5px; max-height: var(--mini-h); }
.mj-melds.is-v .gt-tile { flex: 1 1 0; height: auto; min-height: 7px; max-height: var(--mini-h); }

/* 中央：四方弃牌围成一圈（上=对家 / 下=自己 / 左=左家 / 右=右家），中心放最近舍牌与战报 */
.mj-center {
  grid-area: center; min-width: 0; min-height: 0;
  display: grid; gap: 4px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  grid-template-rows: auto minmax(0, 1fr) auto;
  grid-template-areas: "up up up" "left info right" "down down down";
  padding: 8px; border-radius: 14px;
  background: rgba(0, 0, 0, .2);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .07);
}
/* 弃牌一律用 grid 明确行列数，不再依赖 flex-wrap 的「空间不够就多开一列」——
   那正是左右两方看起来「横着摆」的另一条成因。 */
.mj-dis { display: grid; gap: 2px; min-width: 0; min-height: 0; }
/* 上下两家：按容器宽度自动铺列（窄屏列少、宽屏列多），多了换行 */
.mj-dis-up, .mj-dis-down {
  grid-template-columns: repeat(auto-fill, var(--mini-w));
  justify-content: center;
}
.mj-dis-up { grid-area: up; align-content: flex-start; }
.mj-dis-down { grid-area: down; align-content: flex-end; }
/* 左右两家：每列按可用高度自动铺满，多出的**向外**再起一列 */
.mj-dis-left, .mj-dis-right {
  grid-auto-flow: column;
  grid-template-rows: repeat(auto-fill, var(--mini-h));
  align-content: center;
}
.mj-dis-left { grid-area: left; justify-content: start; }
.mj-dis-right { grid-area: right; justify-content: end; }

.mj-center-info {
  grid-area: info; min-width: 0; min-height: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
  padding: 4px 10px; border-radius: 12px;
  background: radial-gradient(120% 120% at 50% 0%, rgba(255, 255, 255, .08), rgba(0, 0, 0, .2));
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .06);
}
.mj-last-tile { display: block; animation: gt-pop .22s ease-out both; }
.mj-center-who { font-size: 12px; color: var(--gt-ink); letter-spacing: .02em; }
.mj-center-turn {
  font-style: normal; font-size: 11.5px; font-weight: 700; color: var(--gt-gold);
  text-shadow: 0 0 12px rgba(233, 200, 119, .45);
}
.mj-log { display: flex; flex-direction: column; align-items: center; gap: 1px; max-width: 100%; }
.mj-log span {
  font-size: 10.5px; color: rgba(255, 255, 255, .5);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}

/* ===== 听牌条 ===== */
.mj-tingbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 7px 12px; border-radius: 12px;
  background: rgba(233, 200, 119, .1);
  box-shadow: inset 0 0 0 1px rgba(233, 200, 119, .28), inset 3px 0 0 var(--gt-gold);
}
.mj-ting-label { font-size: 11.5px; font-weight: 700; color: var(--gt-gold); }
.mj-ting-item { font-size: 11.5px; color: var(--gt-ink-dim); }
.mj-ting-item b { color: var(--gt-ink); font-weight: 700; }
.mj-ting-none { font-size: 11.5px; color: var(--gt-ink-dim); }

/* ===== 底部 ===== */
.mj-bottom { display: flex; flex-direction: column; gap: 6px; min-height: 0; }
.mj-handbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
/* 手牌铺满可用宽度：牌宽 = min(按屏高算的上限, 按张数均分)，
   高按 5:7 跟着走 —— 手机横屏约 52~62px 宽，电脑大屏约 89px，都比旧版 40px 大一截。
   上留白 = 选中上浮(-11px) + 落影，俯视时不至于被裁。 */
.mj-hand {
  display: flex; gap: 3px; align-items: flex-end; justify-content: center;
  padding: 18px 4px 6px; min-height: 0; flex-wrap: nowrap;
}
.mj-hand .gt-tile {
  width: min(
    calc(var(--gt-h, 420px) * 0.155),
    calc((100% - (var(--ntiles, 14) - 1) * 3px) / var(--ntiles, 14))
  );
  height: auto; aspect-ratio: 5 / 7;
}
/* 牌面 SVG 铺满整张牌（绝对定位，避免百分比高度在 aspect-ratio 盒子里解析不确定） */
.mj .gt-tile > :deep(svg) { position: absolute; inset: 0; }
.mj-hand-empty { margin: 0 auto; font-size: 12px; color: var(--gt-ink-dim); }
.mj-actions { justify-content: center; }

/* ===== 牌：象牙白 + 玉质感 =====
   覆盖全局 .gt-tile 那套「浅色平面 + 单层投影」的塑料感：改成三层阴影 ——
   一层内高光（顶部受光）、两层错开的实心投影（牌身厚度）、一层柔和落影（离地感）。 */
.mj .gt-tile {
  background: linear-gradient(172deg, #fffefb 0%, #f8f4ea 55%, #eae3d1 100%);
  border: 1px solid #d6ceb8;
  border-radius: 5px 5px 4px 4px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .95),
    0 2px 0 #cfc6ad,
    0 4px 0 #b6ac91,
    0 10px 16px -9px rgba(0, 0, 0, .75);
}
/* 牌背：翡翠绿（与绒布桌同色系，不再是突兀的蓝） */
.mj .gt-tile.is-back {
  background: linear-gradient(172deg, #3f9e7a 0%, #2a7d5e 55%, #1b5c45 100%);
  border-color: #15503b;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .22),
    0 2px 0 #144634,
    0 4px 0 #0d3225,
    0 10px 16px -9px rgba(0, 0, 0, .8);
}
/* 迷你牌（背面 / 弃牌 / 副露）尺寸跟随屏高 */
.mj .gt-tile.mini { width: var(--mini-w); height: var(--mini-h); border-radius: 3px; }
/* 迷你牌不需要「厚度」层，否则小尺寸下投影糊成一团 */
.mj .gt-tile.mini {
  box-shadow: 0 1px 0 rgba(150, 140, 115, .6), 0 3px 5px -3px rgba(0, 0, 0, .6);
}
.mj .gt-tile.mini.is-back {
  box-shadow: 0 1px 0 rgba(9, 48, 35, .85), 0 3px 5px -3px rgba(0, 0, 0, .7);
}

/* 花色着色（牌面由 SVG 绘制，此处仅作兜底与选中描边色） */
.mj .gt-tile.is-wan { --tile-accent: #b3261e; }
.mj .gt-tile.is-tiao { --tile-accent: #1f6b3a; }
.mj .gt-tile.is-tong { --tile-accent: #1b4f8a; }
.mj .gt-tile.is-drawn {
  margin-left: 12px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .95),
    0 0 0 2px var(--gt-gold),
    0 2px 0 #cfc6ad, 0 4px 0 #b6ac91,
    0 14px 20px -10px rgba(0, 0, 0, .85);
}
/* 手牌选中：抬起来 + 金色描边 */
.mj-hand .gt-tile.is-sel {
  transform: translateY(-11px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .95),
    0 0 0 2px var(--gt-gold), 0 0 18px -2px rgba(233, 200, 119, .7),
    0 2px 0 #cfc6ad, 0 4px 0 #b6ac91,
    0 16px 22px -10px rgba(0, 0, 0, .9);
}
.gt-over-card em { font-style: normal; opacity: .7; }

@media (max-width: 900px) {
  .mj { min-width: 860px; }
}
</style>

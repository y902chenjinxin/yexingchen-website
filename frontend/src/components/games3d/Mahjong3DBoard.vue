<template>
  <div class="g3d-board">
    <!-- 顶栏（外层在线牌桌自带顶栏时隐藏，v2.46.268） -->
    <header v-if="showTopbar" class="g3d-topbar">
      <div class="g3d-title">
        <span class="g3d-logo">3D</span>
        <div class="g3d-tx">
          <b>3D 麻将</b>
          <!-- 在线没有本地牌墙，别显示「剩余 0 张」误导 -->
          <i>庄家 {{ seatName(dealer) }}<template v-if="!isOnline"> · 剩余 {{ wall.length }} 张</template>{{ tingText }}</i>
        </div>
      </div>
      <div class="g3d-ops">
        <button class="g3d-op ghost" @click="$emit('exit')">返回</button>
        <button v-if="!isOnline" class="g3d-op" @click="startGame">重新开始</button>
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
          :key="'seat' + s"
          class="gt3-seat"
          :class="{ 'is-turn': isTurn(s) }"
          :style="seatTF(SEAT_SLOT[screenPos(s, povSeat)])"
        >
          <div class="gt3-ava" :style="{ background: seatColors[s] }"><AppIcon :icon="seatAvatar(s)" /></div>
          <div class="gt3-meta"><b>{{ seatName(s) }}</b><i :class="{ turn: isTurn(s) }">{{ seatSub(s) }}</i></div>
          <div class="gt3-score" :class="{ 'is-you': s === 0 }"><span class="snum">{{ scores[s] }}</span><span class="slbl">分</span></div>
        </div>

        <!-- 牌墙（三面：对家 N / 右家 E / 左家 W）：随摸牌消耗淡出已吃掉的墩 -->
        <div
          v-for="w in wallStacks"
          :key="'w' + w.key"
          class="pc3d mj-wall"
          :style="{ ...pieceBox(dealt, 46, 60, 16, wallTF(w.side, w.i, M.MJ_STACKS), w.i, false, false), opacity: w.n ? 1 : 0.12 }"
        >
          <div class="pc-face pc-back mj-back"></div>
          <div class="pc-face pc-front mj-ivory"></div>
          <div class="pc-face pc-top mj-edge"></div>
          <div class="pc-face pc-bottom mj-edge"></div>
          <div class="pc-face pc-left mj-ivory"></div>
          <div class="pc-face pc-right mj-ivory"></div>
        </div>

        <!-- 副露（各座位面前的明牌平铺） -->
        <template v-for="s in SEATS" :key="'meld' + s">
          <div
            v-for="(t, k) in meldRow(s)"
            :key="'meld' + s + '-' + k"
            class="pc3d mj-hand"
            :style="pieceBox(dealt, 46, 62, 16, meldTF(s, k, meldRow(s).length), k, false, false)"
          >
            <div class="pc-face pc-front mj-front"><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></div>
            <div class="pc-face pc-back mj-ivory"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </template>

        <!-- 中央牌河：每座位按其屏幕位给原点偏移 -->
        <template v-for="s in SEATS" :key="'dis' + s">
          <div
            v-for="(t, i) in discards[s]"
            :key="'dis' + s + '-' + t.id"
            class="pc3d mj-hand mj-center"
            :style="pieceBox(dealt, 46, 62, 16, centerTF(i, 40, CENTER_OFF[screenPos(s, povSeat)]), i, false, false)"
          >
            <div class="pc-face pc-front mj-front"><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></div>
            <div class="pc-face pc-back mj-ivory"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </template>

        <!-- 我的手牌（座位 0） -->
        <div
          v-for="(t, i) in hand"
          :key="'h' + t.id"
          class="pc3d mj-hand"
          :class="{ sel: selId === t.id }"
          :style="pieceBox(dealt, 46, 62, 16, handTF(i, handTotal, true, 324, selId === t.id ? 26 : 0), i, true, false)"
          @click="pickTile(t)"
        >
          <div class="pc-face pc-front mj-front"><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></div>
          <div class="pc-face pc-back mj-ivory"></div>
          <div class="pc-face pc-top mj-ivory"></div>
          <div class="pc-face pc-bottom mj-ivory"></div>
          <div class="pc-face pc-left mj-edge"></div>
          <div class="pc-face pc-right mj-edge"></div>
        </div>

        <!-- 新摸到的那张（可打） -->
        <div
          v-if="viewDrawn"
          :key="'hd' + viewDrawn.id"
          class="pc3d mj-hand fresh"
          :class="{ sel: selId === viewDrawn.id }"
          :style="pieceBox(dealt, 46, 62, 16, handTF(hand.length, handTotal, true, 324, selId === viewDrawn.id ? 26 : 0), hand.length, true, true)"
          @click="pickTile(viewDrawn)"
        >
          <div class="pc-face pc-front mj-front"><MahjongTileFace :suit="faceSuit(viewDrawn)" :rank="viewDrawn.rank" /></div>
          <div class="pc-face pc-back mj-ivory"></div>
          <div class="pc-face pc-top mj-ivory"></div>
          <div class="pc-face pc-bottom mj-ivory"></div>
          <div class="pc-face pc-left mj-edge"></div>
          <div class="pc-face pc-right mj-edge"></div>
        </div>
      </div>
    </div>

    <!-- 操作条 -->
    <div class="g3d-ctl">
      <button v-if="canHu" class="g3d-btn primary" @click="doHuAction">胡</button>
      <button v-if="canKong" class="g3d-btn" @click="react('kong')">杠</button>
      <button v-if="canPong" class="g3d-btn" @click="react('pong')">碰</button>
      <button v-if="canChi" class="g3d-btn" @click="react('chi')">吃</button>
      <button v-if="canPass" class="g3d-btn ghost" @click="react('pass')">过</button>
      <button v-if="canAnkong" class="g3d-btn" @click="doAnkong(ankongs[0])">暗杠 {{ tileText(ankongs[0]) }}</button>
      <button v-if="canBugang" class="g3d-btn" @click="doBugang(bugangs[0])">补杠 {{ tileText(bugangs[0]) }}</button>
      <button v-if="canHint" class="g3d-btn ghost" @click="doHint">提示</button>
    </div>

    <!-- 提示条 -->
    <div v-if="toast" class="g3d-toast">{{ toast }}</div>

    <!-- 结算浮层 -->
    <div v-if="phase === 'settled'" class="g3d-over">
      <div class="ov-card">
        <h2>{{ overTitle }}</h2>
        <p v-if="huResults.length">
          {{ seatName(huResults[0].seat) }}：{{ huResults[0].names.join(' · ') }} {{ huResults[0].fan }} 番（{{ huResults[0].zimo ? '自摸' : '点炮' }}）
        </p>
        <p v-else>流局：牌墙摸完，无人胡牌。</p>
        <p>你的得分：{{ scores[0] > 0 ? '+' : '' }}{{ scores[0] }} 分</p>
        <div class="ov-acts">
          <button class="g3d-btn ghost" @click="$emit('exit')">返回</button>
          <button class="g3d-btn primary" @click="nextRound">再来一局</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/** 3D 麻将（单机）：复用 2D 四川麻将规则引擎 utils/games/mahjong.js。
 *
 * 口径与 2D MahjongBoard.vue 一致（v2.46.17 起）：
 *  - 无定缺；和牌型 4 面子 + 1 将 / 七对；**胡牌即结束**，一炮只取一家；
 *    番种 平胡1 / 对对胡2 / 清一色4 / 七对4 / 龙七对8 / 将将胡4 / 金钩钓4。
 *  - 庄家轮换：上一局胡牌者下局坐庄，首局 0 号位。
 *
 * 3D 呈现：手牌 / 副露明牌 / 中央牌河 / 三面牌墙全部走 use3dTable 的纯函数变换 +
 * games3d.css 的全局类，组件不自带 <style>。
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import * as M from '@/utils/games/mahjong.js'
import MahjongTileFace from '@/components/games/MahjongTileFace.vue'
import {
  VIEW_RX, boxVars, pieceBox, wallTF, handTF, centerTF, seatTF, SEAT_SLOT, screenPos,
} from '@/components/games3d/use3dTable.js'
import AppIcon from '@/components/common/AppIcon.vue'
/* v2.46.154：接 2D 麻将那套音效（摸牌 pick / 打牌 tileDown / 碰 / 杠 / 胡），此前 3D 版全静音 */
import { sfx, panOf } from '@/utils/games/sfx'
/* v2.46.262：3D 麻将此前只有「啪」的落桌声，不报牌面（夜星：「只有出牌音效，没有具体牌的内容」）。
   复用 2D 那套 TTS：按座位分声，打完念「八万」，碰杠胡也各有报词。 */
import { speak, tileSpeech } from '@/utils/games/tts'
/* 样式必须由组件自己引：在线牌桌是直接异步加载本组件的，不经 Games3DView */
import '@/assets/styles/games3d.css'

const props = defineProps({
  online: { type: Boolean, default: false },
  onlineView: { type: Object, default: null },
  onlineSeat: { type: Number, default: 0 },
  acting: { type: Boolean, default: false },
  /** 外层（在线牌桌）自带顶栏时传 false */
  showTopbar: { type: Boolean, default: true },
  /** 各座位显示名 */
  seatNames: { type: Array, default: null },
})
const emit = defineEmits(['exit', 'act'])

/* ---------- 在线（v2.46.268） ----------
 * 服务端权威：手牌/牌河/副露/轮次/可选动作全部来自 onlineView，前端只发动作。
 * 约定同 3D 掼蛋：**我的手牌永远写进 hands[0]**，渲染层统一读 0 号位；
 * 座位投影用 povSeat，我坐 1/2/3 号位时其余三家跟着转。 */
const isOnline = computed(() => !!props.online)
const oSeat = computed(() => (isOnline.value ? Number(props.onlineSeat ?? 0) : 0))
const povSeat = computed(() => oSeat.value)

/* ---------- 常量 ---------- */
const SEATS = [0, 1, 2, 3]
const SEAT_LABEL = { 0: '你', 1: '右家', 2: '对家', 3: '左家' }
const AI_AVATARS = { 1: '🐯', 2: '🦊', 3: '🐼' }
const seatColors = [
  'linear-gradient(160deg,#e9c877,#a9812f)', // 0 你
  'linear-gradient(160deg,#67a,#345)',       // 1 右家
  'linear-gradient(160deg,#3a7,#276)',       // 2 对家
  'linear-gradient(160deg,#a76,#743)',       // 3 左家
]
/** 中央牌河按屏幕位（0下 1右 2上 3左）的原点偏移 */
const CENTER_OFF = [
  { x: 0, y: 110 }, { x: 150, y: 0 }, { x: 0, y: -110 }, { x: -150, y: 0 },
]
/** 牌墙三面（屏幕位 2 对家 N / 1 右家 E / 3 左家 W；本门下方留给手牌） */
const WALL_SIDES = [
  { side: 'N', seat: 2 },
  { side: 'E', seat: 1 },
  { side: 'W', seat: 3 },
]
const BASE = 10
const worldTF = `rotateX(${VIEW_RX}deg) scale3d(.94,.94,.94)`
const AI_THINK_MIN = 900
const AI_THINK_MAX = 1500

/* ---------- 状态 ---------- */
const phase = ref('playing')      // playing | settled
const roundNo = ref(1)
const dealer = ref(0)
const wall = ref([])
const hands = ref([[], [], [], []])
/* 在线：各座位张数（绝对座位）。单机不用 */
const seatCounts = ref([0, 0, 0, 0])
const melds = ref([[], [], [], []])
const discards = ref([[], [], [], []])
const out = ref([false, false, false, false])   // 胡牌即结束 → 一局最多一家为 true
const turn = ref(0)
const drawn = ref(null)
const dice = ref(null)
const openRel = ref(-1)
const openIdx = ref(0)
const lastDiscard = ref(null)
const selId = ref(null)
const huResults = ref([])
const result = ref(null)
const pending = ref(null)         // { seat, from, tile, kinds }
const reactQueue = ref([])
const reactFrom = ref(null)
/** 本张弃牌上已选「不胡」的座位：顺延给下一家（胡牌即结束，一炮只取一家） */
const huDeclined = ref([])
/** 本局胡牌的座位（庄家轮换用）：null = 流局 */
const lastWinnerSeat = ref(null)
const dealt = ref(false)          // 发牌错峰：新一局先收拢到中央再展开
const toast = ref('')

/* ---------- 派生 ---------- */
const hand = computed(() => hands.value[0] || [])
const viewDrawn = computed(() => (turn.value === 0 && !out.value[0] ? drawn.value : null))
const handTotal = computed(() => hand.value.length + (viewDrawn.value ? 1 : 0))
const poolOfView = computed(() => (viewDrawn.value ? hand.value.concat([viewDrawn.value]) : hand.value.slice()))
const canDiscard = computed(() => (isOnline.value
  ? phase.value === 'playing' && optSet.value.has('discard')
  : (phase.value === 'playing' && !pending.value && turn.value === 0 && !out.value[0])))

/** 本局积分：按 huResults 现算（自摸三家各付、点炮放炮者付两倍） */
function seatScore(s) {
  let v = 0
  for (const r of huResults.value) {
    const gain = BASE * r.fan
    if (r.zimo) v += (s === r.seat ? 3 : -1) * gain
    else if (s === r.seat) v += 2 * gain
    else if (s === r.from) v -= 2 * gain
  }
  return v
}
const scores = computed(() => SEATS.map(seatScore))

/** 牌墙可视化：摸墙墩序 → 每墩剩余张数（M.stackRemain），已被摸走的墩用低透明度 */
const wallStacks = computed(() => {
  const arr = []
  const left = wall.value.length
  for (const w of WALL_SIDES) {
    const rel = (((w.seat - dealer.value) % 4) + 4) % 4
    const rp = M.MJ_RING.indexOf(rel)
    for (let i = 0; i < M.MJ_STACKS; i++) {
      arr.push({ key: w.side + i, side: w.side, i, n: M.stackRemain(rp * M.MJ_STACKS + i, left) })
    }
  }
  return arr
})

/* ================= 在线投影（v2.46.268） =================
 * 服务端一个 view 里给全：我的手牌 / 各家张数 / 牌河 / 副露 / 轮次 / 可选动作。
 * 约定：**我的手牌写进 hands[0]**（渲染层统一读 0 号位），张数走 seatCounts。
 */
const optSet = computed(() => new Set(props.onlineView?.me?.options || []))

function syncFromView(v) {
  if (!v) return
  const me = v.me || {}
  const next = hands.value.slice()
  next[0] = Array.isArray(me.hand) ? me.hand : []
  hands.value = next
  seatCounts.value = [0, 1, 2, 3].map(s => (
    s === oSeat.value ? (me.hand?.length || 0) : (v.players?.[s]?.hand_count ?? 0)
  ))
  // 牌河 / 副露 / 胡牌状态：直接按绝对座位映射（渲染时再按 povSeat 摆位）
  const ds = [[], [], [], []]
  const ms = [[], [], [], []]
  const oo = [false, false, false, false]
  for (const p of (v.players || [])) {
    const s = Number(p.seat)
    if (s < 0 || s > 3) continue
    ds[s] = p.discards || []
    ms[s] = p.melds || []
    oo[s] = !!p.hu
  }
  discards.value = ds
  melds.value = ms
  out.value = oo
  turn.value = v.turn ?? 0
  drawn.value = me.last_draw || null
  dealt.value = true
  phase.value = (v.phase === 'playing') ? 'playing' : 'settled'
  // 最近一张弃牌（中央高亮 / 碰杠胡的来源）
  const ld = v.last_discard
  lastDiscard.value = ld ? { seat: ld.seat, tile: ld.tile } : null
  if (phase.value === 'settled') {
    const hu = (v.players || []).filter(p => p.hu).map(p => ({ seat: p.seat, ...(p.hu_info || {}) }))
    huResults.value = hu
    result.value = v.result || null
  }
}

watch(() => props.onlineView, (v) => { if (isOnline.value && v) syncFromView(v) }, { deep: false })
watch(() => props.online, (on) => { if (on && props.onlineView) syncFromView(props.onlineView) })

/* ---------- 碰杠胡 可操作项 ---------- */
const zimoReady = computed(() => canDiscard.value && M.canHu(poolOfView.value, melds.value[0].length))
/* v2.46.268：在线时「能做什么」由服务端 me.options 说了算，本地 pending 不参与 */
const canHu = computed(() => (isOnline.value
  ? optSet.value.has('hu')
  : ((!!pending.value && pending.value.kinds.includes('hu')) || zimoReady.value)))
const canPong = computed(() => (isOnline.value ? optSet.value.has('pong') : (!!pending.value && pending.value.kinds.includes('pong'))))
const canKong = computed(() => (isOnline.value ? optSet.value.has('kong') : (!!pending.value && pending.value.kinds.includes('kong'))))
const canChi = computed(() => (isOnline.value ? optSet.value.has('chi') : (!!pending.value && pending.value.kinds.includes('chi'))))
const canPass = computed(() => (isOnline.value ? optSet.value.has('pass') : !!pending.value))
const canHint = computed(() => canDiscard.value)
/** 自己回合的暗杠候选（手里 4 张相同的牌） */
const ankongs = computed(() => (canDiscard.value ? M.findAnkongs(hands.value[0]) : []))
/** 自己回合的补杠候选（已碰过的牌又摸到第 4 张；含新摸那张） */
const bugangs = computed(() => (canDiscard.value ? M.findBugangs(poolOfView.value, melds.value[0]) : []))
const canAnkong = computed(() => ankongs.value.length > 0)
const canBugang = computed(() => bugangs.value.length > 0)

/* ---------- 听牌提示 ---------- */
const waitingTing = computed(() => {
  if (phase.value !== 'playing' || canDiscard.value) return []
  const h = hand.value
  if (h.length % 3 !== 1) return []
  return M.tingTiles(h, melds.value[0].length)
})
const isTing = computed(() => waitingTing.value.length > 0)
const tingText = computed(() => (isTing.value ? ` · 听 ${waitingTing.value.map(tileText).join('/')}` : ''))
/** 一向听：打哪张能听什么 */
const tingInfo = computed(() => {
  if (!canDiscard.value) return []
  const h = poolOfView.value
  if (h.length % 3 !== 2) return []
  const res = []
  const seen = new Set()
  for (const t of h) {
    const k = `${t.suit}${t.rank}`
    if (seen.has(k)) continue
    seen.add(k)
    const waits = M.tingTiles(h.filter(x => x.id !== t.id), melds.value[0].length)
    if (waits.length) res.push({ tile: t, waits })
  }
  return res
})

const overTitle = computed(() => {
  if (!huResults.value.length) return '流局'
  return `${seatName(huResults.value[0].seat)}${huResults.value[0].zimo ? ' 自摸' : ' 胡牌'}！`
})

/* ---------- 小工具 ---------- */
function isHuman(s) { return s === 0 }
/* v2.46.268：座位名/头像跟着「我的座位」走。在线时我可能坐 1/2/3 号位，
   写死 SEAT_LABEL（0 号叫「你」）会把我自己的铭牌画在别人那侧。 */
function seatName(s) {
  const n = props.seatNames?.[s]
  if (n) return n
  if (isOnline.value) return s === oSeat.value ? '你' : SEAT_LABEL[s]
  return SEAT_LABEL[s]
}
function seatAvatar(s) {
  if (isOnline.value) return s === oSeat.value ? '🙂' : (AI_AVATARS[s] || '🤖')
  return isHuman(s) ? '🙂' : (AI_AVATARS[s] || '🤖')
}
function isTurn(s) { return phase.value === 'playing' && turn.value === s && !out.value[s] }
function seatSub(s) {
  if (out.value[s]) return '已胡'
  if (isTurn(s)) return '出牌中'
  const n = isOnline.value ? (seatCounts.value[s] ?? 0) : hands.value[s].length
  return `${n} 张${melds.value[s].length ? ` · 副露${melds.value[s].length}` : ''}`
}
function faceSuit(t) {
  if (!t) return 'wan'
  return t.suit === 'm' ? 'wan' : t.suit === 's' ? 'tiao' : t.suit === 'z' ? 'zi' : 'tong'
}
function tileText(t) {
  if (!t) return ''
  return t.suit === 'z' ? (M.HONOR_NAME[t.rank] || `${t.rank}字`) : `${t.rank}${M.SUIT_NAME[t.suit]}`
}
function countIn(h, tile) { return h.filter(t => t.suit === tile.suit && t.rank === tile.rank).length }
function meldTiles(md) {
  if (md.type === 'chi') {
    // 吃副露按点数升序展示（v2.46.43）：避免「四萬六萬伍萬」这种乱序
    return [...(md.combo || []), md.tile]
      .sort((a, b) => M.idxOf(a.suit, a.rank) - M.idxOf(b.suit, b.rank))
  }
  const n = md.type === 'pong' ? 3 : 4   // 杠 / 暗杠 / 补杠 均为 4 张
  return Array.from({ length: n }, () => md.tile)
}
function meldRow(s) { return melds.value[s].flatMap(meldTiles) }
/** 副露明牌平铺：z 略低于手牌（32px），各座位贴自己那一侧 */
function meldTF(seat, i, n) {
  const step = 40
  const off = (i - (n - 1) / 2) * step
  if (seat === 0) return `translate(-50%,-50%) translate3d(${off}px,255px,32px) rotateX(-90deg)`
  if (seat === 2) return `translate(-50%,-50%) translate3d(${off}px,-205px,32px) rotateX(-90deg)`
  if (seat === 1) return `translate(-50%,-50%) translate3d(205px,${off}px,32px) rotateX(-90deg)`
  return `translate(-50%,-50%) translate3d(-205px,${off}px,32px) rotateX(-90deg)`
}

let toastTimer = null
function showToast(t) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1800)
}

/* ---------- 开局 ---------- */
let dealTimer = null
let aiTimer = null

function dealRound() {
  const deck = M.shuffle(M.buildDeck())
  // 开牌仪式（与 2D / 后端镜像）：两骰定开门边与墩位 → 三轮流牌 → 庄家跳牌 14 张开打
  const dealerSeat = roundNo.value === 1 ? 0 : (lastWinnerSeat.value ?? 0)
  const d1 = 1 + Math.floor(Math.random() * 6)
  const d2 = 1 + Math.floor(Math.random() * 6)
  const deal = M.dealOpening(deck, dealerSeat, d1, d2)
  wall.value = [...deal.wall].reverse()   // 存反序：drawOne 的 pop() 取摸墙序队头
  hands.value = deal.hands.map(M.sortHand)
  melds.value = [[], [], [], []]
  discards.value = [[], [], [], []]
  out.value = [false, false, false, false]
  huResults.value = []
  result.value = null
  pending.value = null
  reactQueue.value = []
  reactFrom.value = null
  huDeclined.value = []
  lastDiscard.value = null
  selId.value = null
  drawn.value = deal.lastDraw          // 庄家跳牌第 14 张，亮为「刚摸」，直接打牌开局
  dice.value = [d1, d2]
  openRel.value = deal.openRel
  openIdx.value = deal.openIdx
  phase.value = 'playing'
  dealer.value = dealerSeat
  turn.value = dealerSeat
  // 发牌动画：先收拢到中央，下一帧展开
  dealt.value = false
  clearTimeout(dealTimer)
  dealTimer = setTimeout(() => { dealt.value = true; sfx.deal() }, 32)
  if (!isHuman(dealerSeat)) scheduleAI()
}

function startGame() {
  clearTimeout(aiTimer)
  clearTimeout(dealTimer)
  clearTimeout(toastTimer)
  phase.value = 'playing'
  roundNo.value = 1
  lastWinnerSeat.value = null
  result.value = null
  toast.value = ''
  dealRound()
}

function nextRound() {
  roundNo.value++
  dealRound()
}

/* ---------- 摸牌 ---------- */
function drawOne(seat) {
  if (phase.value !== 'playing') return
  if (wall.value.length === 0) return endRound('liuju')
  turn.value = seat
  drawn.value = wall.value.pop()
  sfx.pick()
  selId.value = null
  if (isHuman(seat)) return
  scheduleAI()
}

function advance(from) {
  if (phase.value !== 'playing') return
  if (out.value.some(Boolean)) { endRound('hu'); return }
  let s = from
  for (let i = 1; i <= 4; i++) {
    const t = (from + i) % 4
    if (!out.value[t]) { s = t; break }
  }
  drawOne(s)
}

/* ---------- 出牌 ---------- */
function discardTile(seat, tile) {
  const h = hands.value[seat]
  if (drawn.value && drawn.value.id === tile.id) {
    drawn.value = null
  } else {
    const i = h.findIndex(t => t.id === tile.id)
    if (i >= 0) h.splice(i, 1)
    if (drawn.value) { h.push(drawn.value); drawn.value = null }
    hands.value[seat] = M.sortHand(h)
  }
  sfx.tileDown(panOf(seat, 0))
  speak(tileSpeech(tile), seat)   // v2.46.262：报牌面「八万 / 红中」
  discards.value[seat].push(tile)
  lastDiscard.value = { seat, tile }
  selId.value = null
  huDeclined.value = []          // 每张新弃牌的「不胡」名单重新开始
  resolveReactions(seat, tile)
}

/* ---------- 反应（碰 / 杠 / 胡 / 过） ---------- */
function takeFromDiscard(from) {
  const pile = discards.value[from]
  if (pile.length) pile.pop()
}

function resolveReactions(from, tile) {
  if (phase.value !== 'playing') return
  // 1) 胡（点炮）：胡牌即结束 —— 从放炮者下家起逆时针找第一家能胡的，只此一家
  for (let off = 1; off <= 3; off++) {
    const s = (from + off) % 4
    if (out.value[s] || huDeclined.value.includes(s)) continue
    if (!M.canHu(hands.value[s].concat([tile]), melds.value[s].length)) continue
    if (isHuman(s)) {
      pending.value = { seat: s, from, tile, kinds: ['hu'] }
      showToast(`${seatName(from)} 打出 ${tileText(tile)}，可胡`)
      return
    }
    doHu(s, tile, from, false)
    return
  }
  // 2) 杠 / 碰 / 吃：按座次（吃只有下家能吃，v2.46.24）
  const q = []
  for (let off = 1; off <= 3; off++) {
    const s = (from + off) % 4
    if (out.value[s]) continue
    const kinds = []
    if (countIn(hands.value[s], tile) >= 3) kinds.push('kong')
    if (countIn(hands.value[s], tile) >= 2) kinds.push('pong')
    if (off === 1 && M.chiCombos(hands.value[s], tile).length) kinds.push('chi')
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
      showToast(`${seatName(rf.from)} 打出 ${tileText(rf.tile)}`)
      return
    }
    if (cur.kinds.includes('kong')
      && M.aiWantKong(hands.value[s], rf.tile, melds.value[s].length, null, { level: 'normal' })) {
      q.shift(); doKongFromDiscard(s, rf.tile, rf.from); return
    }
    if (cur.kinds.includes('pong')
      && M.aiWantPong(hands.value[s], rf.tile, melds.value[s].length, null, { level: 'normal' })) {
      q.shift(); doPong(s, rf.tile, rf.from); return
    }
    if (cur.kinds.includes('chi')
      && M.aiWantChi(hands.value[s], rf.tile, melds.value[s].length, null, { level: 'normal' })) {
      q.shift(); doChi(s, rf.tile, rf.from); return
    }
    q.shift()
  }
  advance(rf.from)
}

function doPong(seat, tile, from) {
  const h = hands.value[seat]
  let removed = 0
  for (let i = h.length - 1; i >= 0 && removed < 2; i--) {
    if (h[i].suit === tile.suit && h[i].rank === tile.rank) { h.splice(i, 1); removed++ }
  }
  hands.value[seat] = M.sortHand(h)
  sfx.pong(panOf(seat, 0))
  speak('碰', seat)
  melds.value[seat].push({ type: 'pong', tile, from })
  takeFromDiscard(from)
  drawn.value = null
  turn.value = seat
  selId.value = null
  showToast(`${seatName(seat)} 碰 ${tileText(tile)}`)
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
  sfx.kong(panOf(seat, 0))
  speak('杠', seat)
  melds.value[seat].push({ type: 'kong', tile, from })
  takeFromDiscard(from)
  showToast(`${seatName(seat)} 杠 ${tileText(tile)}`)
  turn.value = seat
  drawReplacement(seat)
}

/** 吃（v2.46.24）：上家弃牌 + 手里两张连张成顺子。组合由 chiCombos 给出，取第一组。 */
function doChi(seat, tile, from) {
  const combos = M.chiCombos(hands.value[seat], tile)
  if (!combos.length) return
  const combo = combos[0]
  const h = hands.value[seat]
  for (const t of combo) {
    const i = h.findIndex(x => x.id === t.id)
    if (i >= 0) h.splice(i, 1)
  }
  hands.value[seat] = M.sortHand(h)
  melds.value[seat].push({ type: 'chi', tile, from, combo: combo.map(t => ({ suit: t.suit, rank: t.rank })) })
  takeFromDiscard(from)
  drawn.value = null
  turn.value = seat
  selId.value = null
  showToast(`${seatName(seat)} 吃 ${tileText(tile)}`)
  sfx.pick()                 // 吃牌此前完全无声（v2.46.262 补上）
  speak('吃', seat)
  if (isHuman(seat)) return
  scheduleAI()
}

/** 暗杠：手里 4 张相同的牌，摆进 melds 后摸一张补牌 */
function doAnkong(tileInfo) {
  if (!tileInfo) return
  const seat = turn.value
  const h = hands.value[seat]
  let removed = 0
  for (let i = h.length - 1; i >= 0 && removed < 4; i--) {
    if (h[i].suit === tileInfo.suit && h[i].rank === tileInfo.rank) { h.splice(i, 1); removed++ }
  }
  hands.value[seat] = M.sortHand(h)
  melds.value[seat].push({ type: 'ankong', tile: tileInfo })
  showToast(`${seatName(seat)} 暗杠 ${tileText(tileInfo)}`)
  drawReplacement(seat)
}

/** 补杠：把已碰过的牌升级为 'bugang'，摸一张补牌 */
function doBugang(tileInfo) {
  if (!tileInfo) return
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
  const md = melds.value[seat].find(m => m.type === 'pong'
    && m.tile.suit === tileInfo.suit && m.tile.rank === tileInfo.rank)
  if (md) md.type = 'bugang'
  showToast(`${seatName(seat)} 补杠 ${tileText(tileInfo)}`)
  drawReplacement(seat)
}

function drawReplacement(seat) {
  if (wall.value.length === 0) return endRound('liuju')
  drawn.value = wall.value.pop()
  sfx.pick()
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
  huResults.value.push({
    seat, fan: sc.fan, names: sc.names, zimo, from,
    hand: winning.concat(flatMeldTiles(melds.value[seat])),
  })
  showToast(`${seatName(seat)} ${zimo ? '自摸' : '胡牌'}！${sc.names.join(' · ')} ${sc.fan} 番`)
  speak(zimo ? '自摸' : '胡', seat)
  endRound('hu')
}

/** 副露展开成可渲染牌数组（碰 3 / 杠 4），id 加后缀防 key 冲突 */
function flatMeldTiles(list) {
  return (list || []).flatMap((md, mi) => meldTiles(md).map((t, k) => ({
    ...t, id: `${t.id ?? t.suit + t.rank}-m${mi}-${k}`,
  })))
}

/* ---------- 人类操作 ---------- */
/** 自己回合点手牌即打出（摸到的那张也可打） */
function pickTile(t) {
  if (!canDiscard.value || !t) return
  if (isOnline.value) {
    // 服务端权威：只上报 tile_id（本地不改状态，等 view 回来）
    emit('act', { type: 'discard', tile_id: t.id })
    selId.value = null
    return
  }
  discardTile(0, t)
}

function doHuAction() {
  if (isOnline.value) { emit('act', { type: 'hu' }); return }
  if (pending.value && pending.value.kinds.includes('hu')) { react('hu'); return }
  if (zimoReady.value) doHu(0, null, null, true)
}

function react(kind) {
  if (isOnline.value) { emit('act', { type: kind }); return }
  const p = pending.value
  if (!p) return
  if (kind === 'pass') {
    pending.value = null
    // 点炮胡被放弃：记下这家后继续往后找（胡牌即结束，一炮只取一家）
    if (p.kinds.length === 1 && p.kinds[0] === 'hu') {
      huDeclined.value.push(p.seat)
      resolveReactions(p.from, p.tile)
      return
    }
    reactQueue.value.shift()
    stepReactions()
    return
  }
  if (kind === 'hu') { pending.value = null; doHu(p.seat, p.tile, p.from, false); return }
  if (kind === 'pong') { pending.value = null; reactQueue.value.shift(); doPong(p.seat, p.tile, p.from); return }
  if (kind === 'kong') { pending.value = null; reactQueue.value.shift(); doKongFromDiscard(p.seat, p.tile, p.from); return }
  if (kind === 'chi') { pending.value = null; reactQueue.value.shift(); doChi(p.seat, p.tile, p.from) }
}

function doHint() {
  if (!canDiscard.value) return
  if (tingInfo.value.length) {
    const first = tingInfo.value[0]
    selId.value = first.tile.id
    showToast(`打 ${tileText(first.tile)} 可听 ${first.waits.map(tileText).join(' / ')}`)
  } else {
    const d = M.aiDiscard(poolOfView.value, melds.value[0].length, { level: 'normal' })
    if (d) { selId.value = d.id; showToast(`建议打 ${tileText(d)}`) }
  }
}

/* ---------- AI ---------- */
function scheduleAI() {
  clearTimeout(aiTimer)
  if (isOnline.value) return          // 在线：轮到谁由服务端决定，前端不跑 AI
  if (phase.value !== 'playing') return
  if (isHuman(turn.value) || out.value[turn.value]) return
  aiTimer = setTimeout(aiTurn, AI_THINK_MIN + Math.floor(Math.random() * (AI_THINK_MAX - AI_THINK_MIN)))
}

function aiTurn() {
  if (phase.value !== 'playing') return
  const s = turn.value
  if (isHuman(s) || out.value[s]) return
  const full = drawn.value ? hands.value[s].concat([drawn.value]) : hands.value[s].slice()
  const mc = melds.value[s].length
  if (M.canHu(full, mc)) { doHu(s, null, null, true); return }
  // 暗杠 / 补杠
  const aks = M.findAnkongs(hands.value[s])
  if (aks.length) { doAnkong(aks[0]); return }
  const bgs = M.findBugangs(full, melds.value[s])
  if (bgs.length) { doBugang(bgs[0]); return }
  // 出牌：有对手听牌时按危险度选安全牌（v2.46.31 防守口径）
  const oppTing = SEATS.some(o => o !== s && !out.value[o]
    && M.shanten(hands.value[o], melds.value[o].length) === 0)
  let ctx = { level: 'normal' }
  if (oppTing) {
    const safe = new Set()
    const visible = new Array(36).fill(0)
    for (let o = 0; o < 4; o++) {
      if (o === s) continue
      if (M.shanten(hands.value[o], melds.value[o].length) === 0) {
        for (const t of discards.value[o]) safe.add(M.idxOf(t.suit, t.rank))
      }
      for (const t of discards.value[o]) visible[M.idxOf(t.suit, t.rank)]++
      for (const m of melds.value[o]) visible[M.idxOf(m.tile.suit, m.tile.rank)] += m.type === 'chi' ? 2 : 3
    }
    ctx = { level: 'normal', threat: true, safe, visible }
  }
  const d = M.aiDiscard(full, mc, ctx)
  if (d) discardTile(s, d)
  else advance(s)
}

/* ---------- 结算 ---------- */
function endRound(reason) {
  clearTimeout(aiTimer)
  clearTimeout(dealTimer)
  phase.value = 'settled'
  pending.value = null
  reactQueue.value = []
  reactFrom.value = null
  // 庄家轮换：本局胡牌者下局坐庄（流局则回到 0 号位）
  lastWinnerSeat.value = huResults.value.length ? huResults.value[0].seat : null
  result.value = { reason, hus: huResults.value.slice(), delta: seatScore(0) }
}

/* ---------- 生命周期 ---------- */
onMounted(() => {
  sfx.preload()   // 预热采样
  // 在线：状态全部来自服务端投影，绝不本地发牌（否则先亮一手假牌再被覆盖）
  if (isOnline.value) {
    if (props.onlineView) syncFromView(props.onlineView)
  } else {
    startGame()
  }
})
onBeforeUnmount(() => {
  clearTimeout(aiTimer)
  clearTimeout(dealTimer)
  clearTimeout(toastTimer)
})
</script>

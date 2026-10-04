<template>
  <div class="gt-landscape gd-wrap">
    <div class="gt-shell gt-skin-blue gd" :class="{ 'is-big': big }">
      <!-- ===== 顶栏 ===== -->
      <header class="gd-top">
        <span class="gt-title">掼蛋</span>
        <span class="gt-pill gold">主级牌 {{ G.levelText(roundLevel) }}</span>
        <span class="gt-pill">我方 {{ G.levelText(teamLevel[0]) }}</span>
        <span class="gt-pill">对方 {{ G.levelText(teamLevel[1]) }}</span>
        <span class="gt-pill">第 {{ roundNo }} 局</span>
        <span class="gt-spacer"></span>
        <button class="gt-btn sm ghost" :title="muted ? '取消静音' : '静音'" @click="toggleMute">
          {{ muted ? '🔇' : '🔊' }}
        </button>
        <button class="gt-btn sm ghost" @click="doExit">退出对局</button>
      </header>

      <!-- ===== 牌桌：主区 + 右侧出牌历史竖栏 ===== -->
      <div class="gd-table">
        <div class="gd-main">
          <!-- 对家 -->
          <div class="gd-row gd-row-top">
            <div class="gt-seat" :class="seatCls(2)">
              <span class="gt-seat-av">{{ seatAvatar(2) }}</span>
              <span class="gt-seat-tx">
                <b class="gt-seat-name">{{ seatName(2) }}</b>
                <i class="gt-seat-sub">{{ seatSub(2) }}</i>
              </span>
              <span v-if="isTurn(2)" class="gt-seat-badge">出牌中</span>
            </div>
          </div>

          <div class="gd-row gd-row-mid">
            <!-- 左家 -->
            <div class="gt-seat gd-seat-side" :class="seatCls(3)">
              <span class="gt-seat-av">{{ seatAvatar(3) }}</span>
              <span class="gt-seat-tx">
                <b class="gt-seat-name">{{ seatName(3) }}</b>
                <i class="gt-seat-sub">{{ seatSub(3) }}</i>
              </span>
              <span v-if="isTurn(3)" class="gt-seat-badge">出牌中</span>
            </div>

            <!-- 中央：本轮出牌 -->
            <div class="gd-center">
              <div class="gd-center-head">
                <span v-if="lastPlay" class="gt-pill gold">{{ G.PATTERN_NAME[lastPlay.pattern.type] }} · {{ seatName(lastPlay.seat) }}</span>
                <span v-else class="gt-pill">本轮先手</span>
                <span v-if="target" class="gt-pill">待压 · {{ G.PATTERN_NAME[target.pattern.type] }}</span>
              </div>
              <div class="gd-center-cards">
                <template v-if="lastPlay">
                  <span
                    v-for="c in lastPlay.cards"
                    :key="c.id"
                    class="gt-card gt-anim-play"
                    :class="cardCls(c)"
                  >
                    <span class="c-tl"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
                    <span class="c-mid">{{ cardSuit(c) }}</span>
                    <span class="c-br"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
                    <span v-if="isWildCard(c)" class="tag">配</span>
                  </span>
                </template>
                <p v-else class="gd-center-empty">
                  {{ phase === 'playing' ? '轮到 ' + seatName(turn) + ' 出牌' : '本局结束' }}
                </p>
              </div>
            </div>

            <!-- 右家 -->
            <div class="gt-seat gd-seat-side" :class="seatCls(1)">
              <span class="gt-seat-av">{{ seatAvatar(1) }}</span>
              <span class="gt-seat-tx">
                <b class="gt-seat-name">{{ seatName(1) }}</b>
                <i class="gt-seat-sub">{{ seatSub(1) }}</i>
              </span>
              <span v-if="isTurn(1)" class="gt-seat-badge">出牌中</span>
            </div>
          </div>
        </div>

        <!-- 右侧竖栏：出牌历史（最新在上，可上下滑动回看） -->
        <aside class="gd-history" aria-label="出牌历史">
          <div class="gd-history-head">
            <span>出牌记录</span>
            <i>{{ history.length }}</i>
          </div>
          <ol class="gd-history-list">
            <li v-for="(h, i) in history" :key="i" class="gd-his" :class="'is-' + h.kind">
              <template v-if="h.kind === 'play'">
                <span class="gd-his-seat">{{ seatName(h.seat) }}</span>
                <span class="gd-his-pat">{{ G.PATTERN_NAME[h.pattern?.type] || '出牌' }}</span>
                <span class="gd-his-cards">
                  <i v-for="c in (h.cards || []).slice(0, 8)" :key="c.id" :class="{ red: isRed(c) }">{{ cardText(c) }}{{ cardSuit(c) }}</i>
                  <em v-if="(h.cards || []).length > 8">+{{ h.cards.length - 8 }}</em>
                </span>
              </template>
              <template v-else-if="h.kind === 'pass'">
                <span class="gd-his-seat">{{ seatName(h.seat) }}</span>
                <span class="gd-his-pat dim">不要</span>
              </template>
              <template v-else>
                <span class="gd-his-pat gold">本局结束 · {{ (h.ranking || []).map(s => seatName(s)).join(' → ') }}</span>
              </template>
            </li>
            <li v-if="!history.length" class="gd-his-empty">暂无出牌</li>
          </ol>
        </aside>
      </div>

      <!-- ===== 底部：手牌 + 操作 ===== -->
      <footer class="gd-bottom">
        <div class="gd-bottom-bar">
          <span class="gt-pill gold">{{ seatName(viewSeat) }}的手牌 · {{ viewHand.length }} 张</span>
          <span v-if="viewTing.length" class="gt-pill">可出：{{ viewTing.length }} 种</span>
          <span v-if="canAct" class="gt-pill">已选 {{ sel.length }} 张</span>
          <span class="gt-spacer"></span>
          <span class="gt-sub">{{ statusLine }}</span>
        </div>

        <div
          class="gd-hand"
          ref="handRef"
          :style="{ '--gd-overlap': overlap + 'px' }"
          @touchstart="onHandTouchStart"
          @touchmove="onHandTouchMove"
          @touchend="onHandTouchEnd"
          @touchcancel="onHandTouchEnd"
        >
          <span
            v-for="(c, i) in viewHand"
            :key="c.id"
            class="gt-card"
            :class="cardCls(c, i)"
            :data-idx="i"
            @click="onPick(c, i, $event)"
          >
            <span class="c-tl"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
            <span class="c-mid">{{ cardSuit(c) }}</span>
            <span class="c-br"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
            <span v-if="isWildCard(c)" class="tag">配</span>
          </span>
          <p v-if="!viewHand.length" class="gd-hand-empty">— 无手牌 —</p>
        </div>

        <div class="gt-actions gd-actions" v-if="!returnPending">
          <button class="gt-btn" :disabled="!canAct || !canPlay" @click="doPlay">出牌</button>
          <button class="gt-btn ghost" :disabled="!canAct || !target" @click="doPass">不要</button>
          <button class="gt-btn ghost" :disabled="!canAct" @click="doHint">提示</button>
          <button class="gt-btn ghost" :disabled="!sel.length" @click="clearSel">重选</button>
        </div>

        <!-- 还贡（在线 · 服务端要求 ≤10） -->
        <div v-else class="gd-return">
          <div class="gd-return-tip">还贡：点一张 ≤10 的牌还给对方（不能还级牌 / 王，30 秒）</div>
          <div class="gd-return-cards">
            <span
              v-for="c in returnOptions"
              :key="c.id"
              class="gt-card pickable"
              :class="cardCls(c)"
              @click="doReturn(c)"
            >
              <span class="c-tl"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
              <span class="c-mid">{{ cardSuit(c) }}</span>
              <span class="c-br"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
            </span>
            <p v-if="!returnOptions.length" class="gd-hand-empty">手上没有 ≤10 的牌可还，系统将自动处理</p>
          </div>
        </div>
      </footer>

      <!-- ===== 结算（页内，不弹窗） ===== -->
      <div v-if="phase === 'settled'" class="gt-over">
        <div class="gt-over-card">
          <h3>{{ matchOver ? (roundResult.winTeam === 0 ? '我方打过 A，全场获胜！' : '对方打过 A，本场落败') : (roundResult.winTeam === 0 ? '我方升级！' : '对方升级') }}</h3>
          <p>
            名次：<b>{{ roundResult.order.map(s => seatName(s)).join(' → ') }}</b><br>
            升级：{{ roundResult.winTeam === 0 ? '我方' : '对方' }} +{{ roundResult.up }} 级<br>
            当前级数：我方 {{ G.levelText(teamLevel[0]) }} · 对方 {{ G.levelText(teamLevel[1]) }}
          </p>
          <div class="gt-actions">
            <button v-if="!isOnline || isHost" class="gt-btn" @click="nextRound">再来一局</button>
            <button class="gt-btn ghost" @click="doExit">返回列表</button>
          </div>
          <p v-if="isOnline && !isHost" class="gd-wait-host">等房主开下一局…</p>
        </div>
      </div>

      <div v-if="toast" class="gt-toast">{{ toast }}</div>
      <div class="gt-watermark">掼 蛋 · 两 副 牌 108 张 · 逢 人 配</div>
    </div>
  </div>
</template>

<script setup>
/** 掼蛋牌桌（v2.43 / v2.44 在线）。
 *
 * 本地：solo = 1 真人 + 3 AI（同屏多人已下线）。
 * 在线：服务端权威发牌，本组件只渲染 `onlineView` 投影态，动作 emit 给等待房页转 /act。
 * 规则核心在 `utils/games/guandan.js`（牌型/比大小/AI/升级）。
 *
 * UI（PRD §7）：
 * - 手牌一屏展示全：按张数自适应重叠度，不横向滚动。
 * - 选牌效率：PC Shift+首尾区间选；手机滑动划选（划回取消）。
 * - 出牌历史：右侧竖向栏，最新在上，可上下滑动回看。
 * - 牌面：王 / 级牌 / 逢人配强区分，花色清晰，选中上浮描边，hover 放大预览。
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import * as G from '@/utils/games/guandan.js'
import { sfx, setMuted, isMuted } from '@/utils/games/sfx'
import { loadGame, saveGame } from '@/utils/gameSave'

const props = defineProps({
  gameKey: { type: String, default: 'guandan' },
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

const SAVE_KEY = 'guandan'
const SEAT_LABEL = { 0: '你', 1: '右家', 2: '对家', 3: '左家' }
const AI_AVATARS = { 1: '🐯', 2: '🦊', 3: '🐼' }
const CARD_W = 62

/* ---------- 状态 ---------- */
const mode = ref(props.initialMode || 'solo')
const teamLevel = ref([2, 2])
const roundLevel = ref(2)
const roundNo = ref(1)
const hands = ref([[], [], [], []])
const turn = ref(0)
const target = ref(null)        // { seat, cards, pattern }
const lastPlay = ref(null)      // 展示用
const passCount = ref(0)
const finished = ref([])
const phase = ref('playing')    // playing | settled
const sel = ref([])
const toast = ref('')
const muted = ref(isMuted())
const history = ref([])         // 结构化出牌记录（最新在前）
const roundResult = ref({ up: 0, winTeam: 0, order: [] })
const matchOver = ref(false)
const firstSeat = ref(0)

/* ---------- 派生 ---------- */
const isOnline = computed(() => props.online)
const oSeat = computed(() => Number(props.onlineSeat ?? 0))
const HUMAN_SEATS = computed(() => {
  if (isOnline.value) return (props.onlineView?.players || []).map(p => p.seat)
  if (mode.value === 'solo') return [0]
  if (mode.value === 'duo') return [0, 2]
  return [0, 1, 2, 3]
})
const viewSeat = computed(() => {
  if (isOnline.value) return oSeat.value
  if (mode.value === 'solo') return 0
  if (HUMAN_SEATS.value.includes(turn.value)) return turn.value
  return HUMAN_SEATS.value[0]
})
const viewHand = computed(() =>
  isOnline.value ? (props.onlineView?.me?.hand || []) : (hands.value[viewSeat.value] || []))
/** 别家手牌张数：在线从投影取，本地从 hands 取 */
function handCount(s) {
  if (isOnline.value) return props.onlineView?.players?.[s]?.hand_count ?? 0
  return hands.value[s]?.length ?? 0
}
const canAct = computed(() => {
  if (isOnline.value) {
    return props.onlineView?.phase === 'playing' && turn.value === oSeat.value && !props.acting
  }
  return phase.value === 'playing' && HUMAN_SEATS.value.includes(turn.value) && turn.value === viewSeat.value
})
const selCards = computed(() => viewHand.value.filter(c => sel.value.includes(c.id)))
const selPattern = computed(() => sel.value.length ? G.detectPattern(selCards.value, roundLevel.value) : null)
const canPlay = computed(() => !!selPattern.value && G.canBeat(selPattern.value, target.value?.pattern ?? null))
/** 当前手牌里所有能压过 target 的候选（给「提示」按钮显示可用性） */
const viewTing = computed(() => {
  if (phase.value !== 'playing' || !canAct.value) return []
  const tgt = target.value
  const ctx = { lastIsTeammate: !!tgt && G.TEAM_OF[tgt.seat] === G.TEAM_OF[turn.value] }
  return G.aiChoose(viewHand.value, tgt?.pattern ?? null, roundLevel.value, ctx).length ? [1] : []
})
const statusLine = computed(() => {
  if (phase.value === 'settled') return isOnline.value ? '本局结束，等房主「再来一局」' : '本局结束，点「再来一局」继续'
  if (isOnline.value && props.onlineView?.phase === 'tribute') return '进贡中…'
  if (isOnline.value && props.onlineView?.phase === 'return') {
    return turn.value === oSeat.value ? '请选择一张 ≤10 的牌还贡（30 秒）' : '等对方还贡…'
  }
  if (!HUMAN_SEATS.value.includes(turn.value)) return `${seatName(turn.value)} 思考中…`
  if (turn.value !== viewSeat.value) return `轮到 ${seatName(turn.value)}`
  return target.value ? '请压过上一手，或选择「不要」' : '本轮由你先出牌'
})
/** 还贡候选项（仅在线 return 阶段、轮到自己时） */
const returnPending = computed(() =>
  isOnline.value && props.onlineView?.phase === 'return' && turn.value === oSeat.value)
const returnOptions = computed(() => props.onlineView?.me?.return_options || [])

/* ---------- 手牌自适应重叠（一屏展示全，不滑动） ---------- */
const handRef = ref(null)
const handW = ref(0)
let ro = null
const overlap = computed(() => {
  const n = viewHand.value.length
  const avail = handW.value
  if (!n || !avail || n < 2) return 0
  const need = n * CARD_W
  if (need <= avail) return 0
  const o = (need - avail) / (n - 1)
  return Math.min(CARD_W - 22, Math.max(0, o))   // 每张至少露 22px（够看左上角点数花色）
})
function measureHand() {
  // clientWidth 含左右各 4px padding，扣掉才是真正可摆牌的内容宽
  if (handRef.value) handW.value = handRef.value.clientWidth - 8
}

/* ---------- 小工具 ---------- */
function cardText(c) { return c.joker ? (c.joker === 'big' ? '大' : '小') : G.RANK_TEXT[c.rank] }
function cardSuit(c) { return c.joker ? '🃏' : c.suit }
function isRed(c) { return !c.joker && (c.suit === '♥' || c.suit === '♦') }
function isWildCard(c) { return G.isWild(c, roundLevel.value) }
function cardCls(c, i) {
  const cls = {
    'is-red': isRed(c),
    'is-joker': !!c.joker,
    'is-level': !c.joker && c.rank === roundLevel.value,
    'is-wild': isWildCard(c),
    'is-sel': sel.value.includes(c.id),
  }
  if (i !== undefined) cls.pickable = canAct.value
  return cls
}
function seatName(s) {
  if (s === null || s === undefined || s < 0) return '—'
  if (isOnline.value) {
    if (s === oSeat.value) return '你'
    return props.seatNames[s] || `座位${s + 1}`
  }
  if (s === 0) return '你'
  return HUMAN_SEATS.value.includes(s) ? `玩家${s === 2 ? '二' : '三'}` : SEAT_LABEL[s]
}
function seatAvatar(s) {
  if (isOnline.value) {
    if (s === oSeat.value) return '🙂'
    const p = props.onlineView?.players?.[s]
    return p && p.team === (props.onlineView?.players?.[oSeat.value]?.team) ? '🙃' : '🤖'
  }
  if (s === 0) return '🙂'
  return HUMAN_SEATS.value.includes(s) ? '🙃' : AI_AVATARS[s]
}
function isTurn(s) { return phase.value === 'playing' && turn.value === s }
function seatSub(s) {
  if (finished.value.includes(s)) return `第 ${finished.value.indexOf(s) + 1} 名`
  return `${handCount(s)} 张`
}
function seatCls(s) {
  return {
    'is-active': isTurn(s),
    'is-out': finished.value.includes(s),
    'is-me': isOnline.value && s === oSeat.value,
  }
}
function toggleMute() { muted.value = !muted.value; setMuted(muted.value) }
let toastTimer = null
function toastMsg(t) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1800)
}

/* ---------- 出牌历史 ---------- */
function pushHistory(item) {
  history.value.unshift(item)
  if (history.value.length > 60) history.value.length = 60
}

/* ---------- 在线：服务端投影 → 展示态 ---------- */
const PHASE_MAP = { playing: 'playing', tribute: 'playing', return: 'playing', finished: 'settled' }
/** 服务端 pattern 是 snake_case（bomb_level），前端 canBeat 用 camelCase（bombLevel），此处归一 */
function normPlay(p) {
  if (!p) return null
  const pat = p.pattern
  return {
    seat: p.seat,
    cards: p.cards || [],
    pattern: pat ? { type: pat.type, len: pat.len, key: pat.key, bombLevel: pat.bomb_level || 0 } : null,
  }
}
function syncFromView(v) {
  if (!v) return
  const empty = [[], [], [], []]
  empty[oSeat.value] = v.me?.hand || []
  hands.value = empty
  turn.value = (v.turn === null || v.turn === undefined) ? -1 : v.turn
  target.value = normPlay(v.target)
  lastPlay.value = normPlay(v.last_play)
  // 服务端 history 按时间正序，取最新在前
  history.value = (v.history || []).slice().reverse()
  roundLevel.value = v.level ?? 2
  teamLevel.value = v.team_levels || [2, 2]
  roundNo.value = v.round_no || 1
  const ranked = (v.players || []).filter(p => p.rank > 0).sort((a, b) => a.rank - b.rank)
  finished.value = ranked.map(p => p.seat)
  phase.value = PHASE_MAP[v.phase] || 'playing'
  if (v.result) {
    roundResult.value = { up: v.result.up || 0, winTeam: v.result.win_team ?? 0, order: v.result.ranking || [] }
    matchOver.value = !!v.result.match_over
  }
  const ids = new Set((v.me?.hand || []).map(c => c.id))
  sel.value = sel.value.filter(id => ids.has(id))
}
watch(() => props.onlineView, (v) => { if (isOnline.value) syncFromView(v) }, { immediate: true, deep: true })

/* ---------- 在线：动作上抛 ---------- */
function actOnline(action) { emit('act', action) }
function doReturn(card) {
  if (!returnPending.value) return
  sel.value = []
  actOnline({ type: 'return', card_id: card.id })
}
function doRematch() { emit('rematch') }

/* ---------- 局流程 ---------- */
function newRound() {
  if (isOnline.value) return   // 在线由服务端发牌，前端不本地开新局
  const dealt = G.deal(roundLevel.value)
  hands.value = dealt
  turn.value = firstSeat.value
  target.value = null
  lastPlay.value = null
  passCount.value = 0
  finished.value = []
  phase.value = 'playing'
  sel.value = []
  history.value = []
  sfx.deal()
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
      lastPlay.value = null
      sel.value = []
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
  target.value = { seat, cards, pattern: pat }
  lastPlay.value = { seat, cards, pattern: pat }
  passCount.value = 0
  pushHistory({ kind: 'play', seat, cards, pattern: pat })
  sfx.play()
  if (hands.value[seat].length === 0 && !finished.value.includes(seat)) {
    finished.value.push(seat)
    firstSeat.value = seat
    toastMsg(`${seatName(seat)} 出完，第 ${finished.value.length} 名`)
  }
  advance()
}

function applyPass(seat) {
  passCount.value++
  pushHistory({ kind: 'pass', seat })
  sfx.pass()
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
  pushHistory({ kind: 'finish', ranking: order, up, winTeam })
  if (matchOver.value) sfx.win()
  else if (winTeam === 0) sfx.win()
  else sfx.lose()
  saveState()
}

function nextRound() {
  if (isOnline.value) { doRematch(); return }
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
function scheduleAI() {
  clearTimeout(aiTimer)
  if (isOnline.value) return   // 在线由服务端 AI 推进
  if (phase.value !== 'playing') return
  if (HUMAN_SEATS.value.includes(turn.value)) return
  aiTimer = setTimeout(aiTurn, 720)
}
function aiTurn() {
  if (phase.value !== 'playing') return
  const s = turn.value
  if (HUMAN_SEATS.value.includes(s)) return
  const tgt = target.value
  const lastIsTeammate = !!tgt && G.TEAM_OF[tgt.seat] === G.TEAM_OF[s]
  const pick = G.aiChoose(hands.value[s], tgt?.pattern ?? null, roundLevel.value, { lastIsTeammate })
  if (pick && pick.length) applyPlay(s, pick)
  else applyPass(s)
}

/* ---------- 选牌：点选 / Shift 区间 / 手机划选 ---------- */
const anchorIdx = ref(null)      // Shift 区间锚点
let suppressClick = false        // 划选后抑制一次 click
let swipeMode = null             // true=选, false=取消
let swipeLast = -1

function selectRange(from, to, state) {
  const lo = Math.min(from, to)
  const hi = Math.max(from, to)
  const ids = new Set(sel.value)
  for (let i = lo; i <= hi; i++) {
    const id = viewHand.value[i]?.id
    if (id == null) continue
    if (state) ids.add(id)
    else ids.delete(id)
  }
  sel.value = [...ids]
}

function onPick(c, idx, ev) {
  if (!canAct.value) return
  if (suppressClick) return
  if (ev && ev.shiftKey && anchorIdx.value !== null) {
    selectRange(anchorIdx.value, idx, !sel.value.includes(c.id))
    sfx.pick()
    return
  }
  const i = sel.value.indexOf(c.id)
  if (i >= 0) sel.value.splice(i, 1)
  else sel.value.push(c.id)
  anchorIdx.value = idx
  sfx.pick()
}

/** 划选命中：**按几何位置**取 x 处最上层（索引最大）的牌，而不是 elementFromPoint。
 *  原因：选中的牌会加 `z-index: 5` 抬到邻牌之上，elementFromPoint 会被上一张已选牌
 *  截胡 —— 表现为「划过 5 张只选中第 0/2/4 张」（隔一张漏一张）。
 *  牌是线性排布，布局在划选期间不变，故在 touchstart 缓存一次矩形即可。 */
let cardRects = []
function cacheCardRects() {
  cardRects = []
  if (!handRef.value) return
  handRef.value.querySelectorAll('.gt-card').forEach((el, i) => {
    const r = el.getBoundingClientRect()
    cardRects.push({ i, left: r.left, right: r.right })
  })
}
function cardIndexAt(x, y) {
  if (!handRef.value) return -1
  const hr = handRef.value.getBoundingClientRect()
  if (y < hr.top - 24 || y > hr.bottom + 24) return -1
  let hit = -1
  for (const c of cardRects) {
    if (x >= c.left && x <= c.right) hit = c.i
  }
  return hit
}
function applySwipe(idx) {
  if (idx === swipeLast || idx < 0) return
  swipeLast = idx
  const id = viewHand.value[idx]?.id
  if (id == null) return
  const has = sel.value.includes(id)
  if (swipeMode && !has) sel.value.push(id)
  else if (!swipeMode && has) sel.value = sel.value.filter(x => x !== id)
  sfx.pick()
}
function onHandTouchStart(e) {
  if (!canAct.value) return
  cacheCardRects()
  const t = e.touches[0]
  const idx = cardIndexAt(t.clientX, t.clientY)
  if (idx < 0) return
  swipeMode = !sel.value.includes(viewHand.value[idx].id)
  swipeLast = -1
  suppressClick = true
  applySwipe(idx)
}
function onHandTouchMove(e) {
  if (swipeMode === null) return
  if (e.cancelable) e.preventDefault()
  const t = e.touches[0]
  applySwipe(cardIndexAt(t.clientX, t.clientY))
}
function onHandTouchEnd() {
  swipeMode = null
  swipeLast = -1
  // 触控结束后浏览器还会补发一次 click，留足窗口抑制它，避免把最后一张又点掉
  setTimeout(() => { suppressClick = false }, 350)
}

function clearSel() { sel.value = []; anchorIdx.value = null }
function doPlay() {
  if (!canAct.value) return
  const pat = selPattern.value
  if (!pat) { toastMsg('这不是合法牌型'); return }
  if (!G.canBeat(pat, target.value?.pattern ?? null)) { toastMsg('压不过上一手'); return }
  if (isOnline.value) { sfx.play(); actOnline({ type: 'play', card_ids: selCards.value.map(c => c.id) }); return }
  applyPlay(turn.value, selCards.value)
}
function doPass() {
  if (!canAct.value) return
  if (!target.value) { toastMsg('本轮由你先出，必须出牌'); return }
  if (isOnline.value) { sfx.pass(); actOnline({ type: 'pass' }); return }
  applyPass(turn.value)
}
function doHint() {
  if (!canAct.value) return
  const tgt = target.value
  const lastIsTeammate = !!tgt && G.TEAM_OF[tgt.seat] === G.TEAM_OF[turn.value]
  const pick = G.aiChoose(viewHand.value, tgt?.pattern ?? null, roundLevel.value, { lastIsTeammate })
  if (pick && pick.length) { sel.value = pick.map(c => c.id); sfx.pick() }
  else toastMsg('没有能压过的牌，只能「不要」')
}

/* ---------- 存档 ---------- */
function saveState() {
  saveGame(SAVE_KEY, {
    mode: mode.value,
    summary: `第 ${roundNo.value} 局 · 我方 ${G.levelText(teamLevel.value[0])} / 对方 ${G.levelText(teamLevel.value[1])}`,
    teamLevel: teamLevel.value.slice(),
    roundLevel: roundLevel.value,
    roundNo: roundNo.value,
    firstSeat: firstSeat.value,
  })
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || s.mode !== mode.value) return false
  if (Array.isArray(s.teamLevel)) teamLevel.value = s.teamLevel.slice()
  roundLevel.value = s.roundLevel || 2
  roundNo.value = s.roundNo || 1
  firstSeat.value = s.firstSeat ?? 0
  return true
}

/* ---------- 退出 ---------- */
function doExit() {
  if (!isOnline.value) saveState()
  emit('exit')
}

/* ---------- 生命周期 ---------- */
onMounted(() => {
  if (typeof ResizeObserver !== 'undefined' && handRef.value) {
    ro = new ResizeObserver(() => measureHand())
    ro.observe(handRef.value)
  }
  measureHand()
  if (isOnline.value) { syncFromView(props.onlineView); return }
  if (props.resume && restoreLocal()) toastMsg('已接着上一局继续')
  newRound()
})
onBeforeUnmount(() => {
  clearTimeout(aiTimer)
  clearTimeout(toastTimer)
  if (ro) ro.disconnect()
})
watch(() => viewHand.value.length, () => { requestAnimationFrame(measureHand) })
</script>

<style scoped>
.gd-wrap { width: 100%; }
.gd {
  display: flex; flex-direction: column; gap: 10px;
  padding: 12px 16px 14px; min-height: 560px;
}
.gd.is-big { min-height: calc(100vh - 140px); }

/* 顶栏 */
.gd-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* 牌桌：主区 + 右侧历史竖栏 */
.gd-table {
  flex: 1; min-height: 0; display: flex; gap: 10px;
  padding: 10px; border-radius: 16px;
  background: radial-gradient(90% 70% at 50% 40%, rgba(255, 255, 255, .07), transparent 70%);
  border: 1px solid var(--gt-line);
}
.gd-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.gd-row { display: flex; align-items: center; }
.gd-row-top { justify-content: center; }
.gd-row-mid { flex: 1; min-height: 0; justify-content: space-between; align-items: center; gap: 8px; }
.gd-seat-side { flex-direction: column; text-align: center; max-width: 96px; padding: 8px 6px; }
.gd-seat-side .gt-seat-tx { align-items: center; }
.gd-seat-side .gt-seat-name { max-width: 84px; }

/* 中央出牌区 */
.gd-center {
  flex: 1; min-width: 0; min-height: 150px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
  padding: 12px; border-radius: 14px;
  background: rgba(0, 0, 0, .22); border: 1px solid var(--gt-line);
}
.gd-center-head { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.gd-center-cards { display: flex; gap: 5px; flex-wrap: wrap; justify-content: center; min-height: 90px; align-items: center; }
.gd-center-empty { margin: 0; font-size: 12.5px; color: var(--gt-ink-dim); }

/* 右侧出牌历史竖栏 */
.gd-history {
  width: 186px; flex: none; display: flex; flex-direction: column; gap: 6px;
  border-radius: 12px; padding: 8px 6px 8px 8px;
  background: rgba(0, 0, 0, .26); border: 1px solid var(--gt-line);
}
.gd-history-head {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 11.5px; font-weight: 600; color: var(--gt-ink-dim);
  padding: 0 4px 4px; border-bottom: 1px solid var(--gt-line);
}
.gd-history-head i { font-style: normal; font-size: 10.5px; opacity: .7; font-variant-numeric: tabular-nums; }
.gd-history-list {
  flex: 1; min-height: 0; margin: 0; padding: 2px 4px 2px 0; list-style: none;
  overflow-y: auto; display: flex; flex-direction: column; gap: 4px;
  scrollbar-width: thin;
}
.gd-his {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px;
  padding: 4px 6px; border-radius: 7px; font-size: 11px;
  background: rgba(255, 255, 255, .05); border: 1px solid transparent;
}
.gd-his.is-play { border-color: rgba(233, 200, 119, .28); }
.gd-his.is-pass { opacity: .72; }
.gd-his.is-finish { background: rgba(233, 200, 119, .14); border-color: rgba(233, 200, 119, .45); }
.gd-his-seat { font-weight: 600; color: var(--gt-ink); flex: none; }
.gd-his-pat { color: var(--gt-gold); flex: none; }
.gd-his-pat.dim { color: var(--gt-ink-dim); }
.gd-his-pat.gold { color: var(--gt-gold); }
.gd-his-cards { display: inline-flex; flex-wrap: wrap; gap: 3px; }
.gd-his-cards i {
  font-style: normal; font-size: 10.5px; padding: 0 3px; border-radius: 3px;
  background: rgba(255, 255, 255, .92); color: #1b1b1b; line-height: 1.5;
}
.gd-his-cards i.red { color: #c62828; }
.gd-his-cards em { font-style: normal; font-size: 10px; color: var(--gt-ink-dim); align-self: center; }
.gd-his-empty { font-size: 11px; color: var(--gt-ink-dim); text-align: center; padding: 10px 0; }

/* 底部手牌 */
.gd-bottom { display: flex; flex-direction: column; gap: 8px; }
.gd-bottom-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gd-hand {
  display: flex; gap: 0; justify-content: center; align-items: flex-end;
  padding: 16px 4px 8px; min-height: 112px;
  overflow: visible;
}
.gd-hand .gt-card { margin-right: calc(-1 * var(--gd-overlap, 0px)); }
.gd-hand .gt-card:last-child { margin-right: 0; }
.gd-hand .gt-card:hover, .gd-hand .gt-card.is-sel { z-index: 5; }
.gd-hand-empty { margin: auto; font-size: 12px; color: var(--gt-ink-dim); }
.gd-actions { justify-content: center; }

/* 出牌方光效（PRD §7.3）：当前行动席位加一圈脉动光，避免误解轮到谁 */
.gd .gt-seat.is-active {
  box-shadow: 0 0 0 2px rgba(199, 169, 107, .55), 0 0 22px rgba(199, 169, 107, .35);
  animation: gd-pulse 1.6s ease-in-out infinite;
}
.gd .gt-seat.is-me .gt-seat-name { color: var(--yq-gold, #c7a96b); }
@keyframes gd-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(199, 169, 107, .5), 0 0 16px rgba(199, 169, 107, .28); }
  50% { box-shadow: 0 0 0 3px rgba(199, 169, 107, .8), 0 0 30px rgba(199, 169, 107, .5); }
}
@media (prefers-reduced-motion: reduce) {
  .gd .gt-seat.is-active { animation: none; }
}

/* 还贡面板 */
.gd-return { display: flex; flex-direction: column; gap: 6px; padding: 6px 2px; }
.gd-return-tip { font-size: 12.5px; color: var(--gt-ink-dim, #b9b3a6); text-align: center; }
.gd-return-cards { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.gd-wait-host { margin: 8px 0 0; font-size: 12.5px; color: var(--gt-ink-dim, #b9b3a6); }

@media (max-width: 900px) {
  .gd { min-width: 860px; }
}
</style>

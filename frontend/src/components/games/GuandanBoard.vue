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

      <!-- ===== 牌桌 ===== -->
      <div class="gd-table">
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
                  :class="{ 'is-red': isRed(c), 'is-back': false }"
                >
                  <span class="r">{{ cardText(c) }}</span>
                  <span class="s">{{ cardSuit(c) }}</span>
                  <span class="big">{{ cardSuit(c) }}</span>
                  <span v-if="isWildCard(c)" class="tag">配</span>
                </span>
              </template>
              <p v-else class="gd-center-empty">
                {{ phase === 'playing' ? '轮到 ' + seatName(turn) + ' 出牌' : '本局结束' }}
              </p>
            </div>
            <div class="gd-center-log">
              <span v-for="(l, i) in logs.slice(0, 3)" :key="i">{{ l }}</span>
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

      <!-- ===== 底部：手牌 + 操作 ===== -->
      <footer class="gd-bottom">
        <div class="gd-bottom-bar">
          <span class="gt-pill gold">{{ seatName(viewSeat) }}的手牌 · {{ viewHand.length }} 张</span>
          <span v-if="viewTing.length" class="gt-pill">可出：{{ viewTing.length }} 种</span>
          <span class="gt-spacer"></span>
          <span class="gt-sub">{{ statusLine }}</span>
        </div>

        <div class="gd-hand">
          <span
            v-for="c in viewHand"
            :key="c.id"
            class="gt-card"
            :class="{ 'is-red': isRed(c), pickable: canAct, 'is-sel': sel.includes(c.id) }"
            @click="onPick(c)"
          >
            <span class="r">{{ cardText(c) }}</span>
            <span class="s">{{ cardSuit(c) }}</span>
            <span class="big">{{ cardSuit(c) }}</span>
            <span v-if="isWildCard(c)" class="tag">配</span>
          </span>
          <p v-if="!viewHand.length" class="gd-hand-empty">— 无手牌 —</p>
        </div>

        <div class="gt-actions gd-actions">
          <button class="gt-btn" :disabled="!canAct || !canPlay" @click="doPlay">出牌</button>
          <button class="gt-btn ghost" :disabled="!canAct || !target" @click="doPass">不要</button>
          <button class="gt-btn ghost" :disabled="!canAct" @click="doHint">提示</button>
          <button class="gt-btn ghost" :disabled="!sel.length" @click="clearSel">重选</button>
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
            <button class="gt-btn" @click="nextRound">再来一局</button>
            <button class="gt-btn ghost" @click="doExit">返回列表</button>
          </div>
        </div>
      </div>

      <div v-if="toast" class="gt-toast">{{ toast }}</div>
      <div class="gt-watermark">掼 蛋 · 两 副 牌 108 张 · 逢 人 配</div>
    </div>
  </div>
</template>

<script setup>
/** 掼蛋牌桌（v2.43）。
 *
 * 纯前端同屏对局：solo = 1 真人 + 3 AI；duo = 2 真人同屏（对家同队）+ 2 AI；quad = 4 真人轮流。
 * 规则核心在 `utils/games/guandan.js`（牌型/比大小/AI/升级）。
 * 视觉走 `assets/styles/game-table.css` 的独立牌桌皮肤（腾讯棋牌风），不污染全站玄黄主题。
 *
 * 简化声明（与引擎注释一致）：不做进贡/还贡/抗贡；炸弹上限 8 张；打过 A 即整场获胜。
 * 在线开房（服务端权威发牌）为后续项 —— 见 PRD §8，需服务端牌局引擎，本期未接。
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
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
})
const emit = defineEmits(['exit', 'room-lock', 'room-unlock'])

const SAVE_KEY = 'guandan'
const SEAT_LABEL = { 0: '你', 1: '右家', 2: '对家', 3: '左家' }
const AI_AVATARS = { 1: '🐯', 2: '🦊', 3: '🐼' }

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
const logs = ref([])
const roundResult = ref({ up: 0, winTeam: 0, order: [] })
const matchOver = ref(false)
const firstSeat = ref(0)

/* ---------- 派生 ---------- */
const HUMAN_SEATS = computed(() => {
  if (mode.value === 'solo') return [0]
  if (mode.value === 'duo') return [0, 2]
  return [0, 1, 2, 3]
})
const viewSeat = computed(() => {
  if (mode.value === 'solo') return 0
  if (HUMAN_SEATS.value.includes(turn.value)) return turn.value
  return HUMAN_SEATS.value[0]
})
const viewHand = computed(() => hands.value[viewSeat.value] || [])
const canAct = computed(() =>
  phase.value === 'playing' && HUMAN_SEATS.value.includes(turn.value) && turn.value === viewSeat.value)
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
  if (phase.value === 'settled') return '本局结束，点「再来一局」继续'
  if (!HUMAN_SEATS.value.includes(turn.value)) return `${SEAT_LABEL[turn.value]} 思考中…`
  if (turn.value !== viewSeat.value) return `轮到 ${SEAT_LABEL[turn.value]}`
  return target.value ? '请压过上一手，或选择「不要」' : '本轮由你先出牌'
})

/* ---------- 小工具 ---------- */
function cardText(c) { return c.joker ? (c.joker === 'big' ? '大' : '小') : G.RANK_TEXT[c.rank] }
function cardSuit(c) { return c.joker ? '🃏' : c.suit }
function isRed(c) { return !c.joker && (c.suit === '♥' || c.suit === '♦') }
function isWildCard(c) { return G.isWild(c, roundLevel.value) }
function seatName(s) {
  if (s === 0) return '你'
  return HUMAN_SEATS.value.includes(s) ? `玩家${s === 2 ? '二' : '三'}` : SEAT_LABEL[s]
}
function seatAvatar(s) {
  if (s === 0) return '🙂'
  return HUMAN_SEATS.value.includes(s) ? '🙃' : AI_AVATARS[s]
}
function isTurn(s) { return phase.value === 'playing' && turn.value === s }
function seatSub(s) {
  if (finished.value.includes(s)) return `第 ${finished.value.indexOf(s) + 1} 名`
  return `${hands.value[s].length} 张`
}
function seatCls(s) {
  return {
    'is-active': isTurn(s),
    'is-out': finished.value.includes(s),
  }
}
function toggleMute() { muted.value = !muted.value; setMuted(muted.value) }
let toastTimer = null
function toastMsg(t) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1800)
}

/* ---------- 局流程 ---------- */
function newRound() {
  const dealt = G.deal(roundLevel.value)
  hands.value = dealt
  turn.value = firstSeat.value
  target.value = null
  lastPlay.value = null
  passCount.value = 0
  finished.value = []
  phase.value = 'playing'
  sel.value = []
  logs.value = []
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
  logs.value.unshift(`${seatName(seat)} 出「${G.PATTERN_NAME[pat.type]}」`)
  logs.value = logs.value.slice(0, 6)
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
  logs.value.unshift(`${seatName(seat)} 不要`)
  logs.value = logs.value.slice(0, 6)
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
  if (matchOver.value) sfx.win()
  else if (winTeam === 0) sfx.win()
  else sfx.lose()
  saveState()
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
function scheduleAI() {
  clearTimeout(aiTimer)
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

/* ---------- 人类操作 ---------- */
function onPick(c) {
  if (!canAct.value) return
  const i = sel.value.indexOf(c.id)
  if (i >= 0) sel.value.splice(i, 1)
  else sel.value.push(c.id)
  sfx.pick()
}
function clearSel() { sel.value = [] }
function doPlay() {
  if (!canAct.value) return
  const pat = selPattern.value
  if (!pat) { toastMsg('这不是合法牌型'); return }
  if (!G.canBeat(pat, target.value?.pattern ?? null)) { toastMsg('压不过上一手'); return }
  applyPlay(turn.value, selCards.value)
}
function doPass() {
  if (!canAct.value) return
  if (!target.value) { toastMsg('本轮由你先出，必须出牌'); return }
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
.gd-wrap { width: 100%; }
.gd {
  display: flex; flex-direction: column; gap: 10px;
  padding: 12px 16px 14px; min-height: 560px;
}
.gd.is-big { min-height: calc(100vh - 150px); }

/* 顶栏 */
.gd-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* 牌桌 */
.gd-table {
  flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 8px;
  padding: 10px; border-radius: 16px;
  background: radial-gradient(90% 70% at 50% 40%, rgba(255, 255, 255, .07), transparent 70%);
  border: 1px solid var(--gt-line);
}
.gd-row { display: flex; align-items: center; }
.gd-row-top { justify-content: center; }
.gd-row-mid { flex: 1; min-height: 0; justify-content: space-between; align-items: center; gap: 8px; }
.gd-seat-side { flex-direction: column; text-align: center; max-width: 96px; padding: 8px 6px; }
.gd-seat-side .gt-seat-tx { align-items: center; }
.gd-seat-side .gt-seat-name { max-width: 84px; }

/* 中央 */
.gd-center {
  flex: 1; min-width: 0; min-height: 150px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
  padding: 12px; border-radius: 14px;
  background: rgba(0, 0, 0, .22); border: 1px solid var(--gt-line);
}
.gd-center-head { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.gd-center-cards { display: flex; gap: 5px; flex-wrap: wrap; justify-content: center; min-height: 90px; align-items: center; }
.gd-center-empty { margin: 0; font-size: 12.5px; color: var(--gt-ink-dim); }
.gd-center-log { display: flex; flex-direction: column; align-items: center; gap: 1px; }
.gd-center-log span { font-size: 11px; color: rgba(255, 255, 255, .5); }

/* 底部手牌 */
.gd-bottom { display: flex; flex-direction: column; gap: 8px; }
.gd-bottom-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gd-hand {
  display: flex; gap: 3px; overflow-x: auto; overflow-y: visible;
  padding: 14px 4px 8px; min-height: 106px; align-items: flex-end;
  scrollbar-width: thin;
}
.gd-hand .gt-card { margin-right: -12px; }
.gd-hand-empty { margin: 0 auto; font-size: 12px; color: var(--gt-ink-dim); }
.gd-actions { justify-content: center; }

@media (max-width: 900px) {
  .gd { min-width: 860px; }
}
</style>

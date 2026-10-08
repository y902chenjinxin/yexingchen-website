<template>
  <div class="gt-landscape gd-wrap">
    <div
      ref="rootRef"
      class="gt-shell gt-skin-blue gd"
      :class="{ 'is-big': big }"
      :style="{ '--gt-h': rootH + 'px', '--card-w': cardW + 'px', '--card-h': cardH + 'px' }"
    >
      <!-- ===== 顶栏 ===== -->
      <header class="gd-top">
        <span class="gt-title">掼蛋</span>
        <span class="gt-pill gold">主级 {{ G.levelText(roundLevel) }}</span>
        <span class="gd-score" :title="`第 ${roundNo} 局 · 我方 ${G.levelText(myLevel)} / 对方 ${G.levelText(oppLevel)}`">
          <i class="me">我方 {{ G.levelText(myLevel) }}</i>
          <em>·</em>
          <i class="op">对方 {{ G.levelText(oppLevel) }}</i>
        </span>
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
            <!-- 轮到谁出牌：钉在牌区右上角，常驻不消失。
                 旧版把「轮到 X 出牌」放在中央 `.gd-center-empty` 里，而那段只在**还没有人出过牌**
                 时渲染 —— 只要有人出了第一手，轮到谁的提示就永远消失了
                 （夜星：「轮到谁出牌都不展示」）。现改成常驻胶囊，轮到自己时变金底高亮。 -->
            <span class="gd-turnbox" :class="{ 'is-me': turn === oSeat, 'is-done': turn < 0 }">
              <em>轮到</em>
              <b>{{ turn < 0 ? '本局结束' : seatName(turn) }}</b>
              <i>出牌</i>
            </span>
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
                <!-- 开局空态不再写文案：head 的胶囊已经是「本轮先手」，
                     「轮到谁出牌」又常驻右上角；这里再写一遍就是同一句话出现两次。 -->
                <p v-else-if="phase !== 'playing'" class="gd-center-empty">本局结束</p>
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

        <!-- 右侧竖栏：出牌历史小窗（默认展开最近 3 条，窗内滚动回看，可收起） -->
        <aside class="gd-history" :class="{ 'is-collapsed': !histOpen }" aria-label="出牌历史">
          <div class="gd-history-head">
            <span>出牌记录</span>
            <i>{{ history.length }}</i>
            <button
              class="gd-history-toggle"
              :aria-label="histOpen ? '收起出牌记录' : '展开出牌记录'"
              @click="histOpen = !histOpen"
            >{{ histOpen ? '收起' : '展开' }}</button>
          </div>
          <ol v-show="histOpen" class="gd-history-list">
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
              <template v-else-if="h.kind === 'tribute' || h.kind === 'return'">
                <span class="gd-his-seat">{{ seatName(h.seat) }}</span>
                <span class="gd-his-pat gold">{{ h.kind === 'tribute' ? '进贡' : '还贡' }}</span>
                <span class="gd-his-cards">
                  <i :class="{ red: isRed(h.card) }">{{ cardText(h.card) }}{{ cardSuit(h.card) }}</i>
                </span>
                <span class="gd-his-arrow">→ {{ seatName(h.to) }}</span>
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
          <span class="gd-hand-tag">{{ seatName(viewSeat) }} · {{ viewHand.length }} 张</span>
          <!-- 全屏时顶栏被收起，级牌与比分改由这条承载，保证一直可见；非全屏时隐藏以免与顶栏重复 -->
          <span class="gd-scorebar">
            主级 {{ G.levelText(roundLevel) }} · 我方 {{ G.levelText(myLevel) }} / 对方 {{ G.levelText(oppLevel) }}
          </span>
          <span class="gt-spacer"></span>
          <span v-if="viewTing.length" class="gd-mini">可出 {{ viewTing.length }}</span>
          <span v-if="canAct" class="gd-mini" :class="{ on: sel.length }">已选 {{ sel.length }}</span>
          <span class="gt-sub gd-status">{{ statusLine }}</span>
        </div>

        <!-- 划选手势：pointerdown 落在手牌区，pointermove / up 由脚本挂到 window
             —— 手指滑出牌区（往上飘 / 划到牌桌）时仍能收到事件，不会半途断掉 -->
        <div
          class="gd-hand"
          ref="handRef"
          :style="{ '--gd-overlap': overlap + 'px' }"
          @pointerdown="onHandDown"
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

        <!-- 操作区：次要工具（提示/重选/同花顺）收成小号弱按钮，主力只留「不要 / 出牌」两个大按钮 -->
        <div class="gt-actions gd-actions" v-if="!tributePending && !returnPending">
          <button class="gt-btn ghost sm" :disabled="!canAct" @click="doHint">提示</button>
          <button class="gt-btn ghost sm" :disabled="!sel.length" @click="clearSel">重选</button>
          <button
            class="gt-btn ghost sm"
            :disabled="!flushCombos.length"
            :title="flushCombos.length ? '点击循环切换同花顺组合' : '手上没有同花顺'"
            @click="cycleFlush"
          >同花顺<em v-if="flushCombos.length > 1" class="gd-btn-count">{{ flushCombos.length }}</em></button>
          <span class="gd-act-gap"></span>
          <button class="gt-btn gd-pass" :disabled="!canAct || !target" @click="doPass">不要</button>
          <button class="gt-btn gd-play" :disabled="!canAct || !canPlay" @click="doPlay">出牌</button>
        </div>

        <!-- 进贡（在线 · 手动选牌，逢人配不能贡） -->
        <div v-else-if="tributePending" class="gd-return gd-tribute">
          <div class="gd-return-tip">进贡：点一张牌进贡给 {{ seatName(tributeTo) }}（逢人配不能进贡）</div>
          <div class="gd-return-cards">
            <span
              v-for="c in tributeOptions"
              :key="c.id"
              class="gt-card pickable"
              :class="cardCls(c)"
              @click="doTribute(c)"
            >
              <span class="c-tl"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
              <span class="c-mid">{{ cardSuit(c) }}</span>
              <span class="c-br"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
            </span>
            <p v-if="!tributeOptions.length" class="gd-hand-empty">没有可进贡的牌</p>
          </div>
        </div>

        <!-- 还贡（在线 · 仅轮到本人时；服务端要求 ≤10） -->
        <div v-else-if="returnPending" class="gd-return">
          <div class="gd-return-tip">还贡：点一张 ≤10 的牌还给对方（不能还级牌 / 王）</div>
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
            <p v-if="!returnOptions.length" class="gd-hand-empty">手上没有 ≤10 的牌可还</p>
          </div>
        </div>
      </footer>

      <!-- 进贡 / 还贡飞牌动画 -->
      <span
        v-if="flyCard"
        class="gt-card gd-fly"
        :class="cardCls(flyCard.card)"
        :style="flyStyle"
        aria-hidden="true"
      >
        <span class="c-tl"><b>{{ cardText(flyCard.card) }}</b><i>{{ cardSuit(flyCard.card) }}</i></span>
        <span class="c-mid">{{ cardSuit(flyCard.card) }}</span>
        <span class="c-br"><b>{{ cardText(flyCard.card) }}</b><i>{{ cardSuit(flyCard.card) }}</i></span>
      </span>

      <!-- ===== 结算（页内，不弹窗） ===== -->
      <div v-if="phase === 'settled'" class="gt-over">
        <div class="gt-over-card">
          <h3>{{ matchOver ? (iWon ? '我方打过 A，全场获胜！' : '对方打过 A，本场落败') : (iWon ? '我方升级！' : '对方升级') }}</h3>
          <p>
            名次：<b>{{ roundResult.order.map(s => seatName(s)).join(' → ') }}</b><br>
            升级：{{ iWon ? '我方' : '对方' }} +{{ roundResult.up }} 级<br>
            当前级数：我方 {{ G.levelText(myLevel) }} · 对方 {{ G.levelText(oppLevel) }}
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
import { useRootHeight } from '@/composables/useRootHeight'

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
/** 同屏 p4 时各座位的名字后缀（0 号位固定叫「你」，不在此表内） */
const HUMAN_CN = { 1: '二', 2: '三', 3: '四' }
const AI_AVATARS = { 1: '🐯', 2: '🦊', 3: '🐼' }

/* 尺寸基准：牌大小跟着牌桌可用高度走 —— 手机横屏约 49×70，电脑大屏约 88×125。
   旧版固定 62×88 且整张牌桌被等比缩到 0.54，手机上只有 33px 宽，既看不清也点不准。
   系数 0.165 → 0.135：0.165 时手牌高 84px，占掉 360px 画布的四分之一，牌桌只剩 153px，
   中央出牌区（min-height 96）塞不下、向上压住对家座位 —— 这就是「横屏挤在一块」。 */
const { rootRef, rootH } = useRootHeight()
const cardW = computed(() => Math.round(Math.min(88, Math.max(44, (rootH.value || 420) * 0.135))))
const cardH = computed(() => Math.round(cardW.value * 1.42))

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

/**
 * 我方是**哪一队** —— 不能再写死 team 0（V2465-006）。
 *
 * 掼蛋的 TEAM_OF = {0:0, 1:1, 2:0, 3:1}（对家为队友）。单机时真人固定坐 0 号位 → 我方 = team 0；
 * 但在线开房时真人可能落在 **1 或 3 号位**，那时我方其实是 team 1。
 * `seatName()` 会把真人所在座位显示成「你」，而升级计算用的是 `TEAM_OF[ranking[0]]` ——
 * 两边口径不一致，于是「你」拿了第一却显示「对方升级」，级数也整个调了个个儿
 * （夜星的截图：名次「你 → …」+「升级：对方 +1 级」）。
 * 现在统一：所有「我方 / 对方」都由 myTeam / oppTeam 推出。
 */
const myTeam = computed(() => (isOnline.value ? (G.TEAM_OF[oSeat.value] ?? 0) : 0))
const oppTeam = computed(() => 1 - myTeam.value)
const myLevel = computed(() => teamLevel.value[myTeam.value])
const oppLevel = computed(() => teamLevel.value[oppTeam.value])
/** 本局是否我方赢（按我方队伍判定，不按 team 0） */
const iWon = computed(() => roundResult.value.winTeam === myTeam.value)

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
  if (isOnline.value && props.onlineView?.phase === 'tribute') {
    return tributePending.value
      ? `请选择一张牌进贡给 ${seatName(tributeTo.value)}`
      : '等对方进贡…'
  }
  if (isOnline.value && props.onlineView?.phase === 'return') {
    return turn.value === oSeat.value ? '请选择一张 ≤10 的牌还贡' : '等对方还贡…'
  }
  if (!HUMAN_SEATS.value.includes(turn.value)) return `${seatName(turn.value)} 思考中…`
  if (turn.value !== viewSeat.value) return `轮到 ${seatName(turn.value)}`
  return target.value ? '请压过上一手，或选择「不要」' : '本轮由你先出牌'
})
/** 还贡候选项（仅在线 return 阶段、轮到自己时） */
const returnPending = computed(() =>
  isOnline.value && props.onlineView?.phase === 'return' && turn.value === oSeat.value)
const returnOptions = computed(() => props.onlineView?.me?.return_options || [])
/** 进贡候选项（仅在线 tribute 阶段、轮到自己时；服务端手动选牌，无倒计时） */
const tributePending = computed(() =>
  isOnline.value && props.onlineView?.phase === 'tribute' && !!props.onlineView?.me?.tribute_pending)
const tributeOptions = computed(() => props.onlineView?.me?.tribute_options || [])
const tributeTo = computed(() => props.onlineView?.me?.tribute_to ?? null)

/* ---------- 同花顺：一键归集并循环切换 ---------- */
const flushCombos = computed(() => G.findFlushBombs(viewHand.value, roundLevel.value))
const flushIdx = ref(0)
function cycleFlush() {
  const combos = flushCombos.value
  if (!combos.length) { toastMsg('手上没有同花顺'); return }
  if (flushIdx.value >= combos.length) flushIdx.value = 0
  sel.value = combos[flushIdx.value].map(c => c.id)
  toastMsg(`同花顺 ${flushIdx.value + 1}/${combos.length}`)
  flushIdx.value = (flushIdx.value + 1) % combos.length
  sfx.pick()
}

/* ---------- 出牌记录小窗：默认展开最近 3 条，可收起 ---------- */
const histOpen = ref(false)

/* ---------- 进贡 / 还贡飞牌动画 ---------- */
const SEAT_ANCHOR = {
  0: { x: '50%', y: '84%' },
  1: { x: '84%', y: '52%' },
  2: { x: '50%', y: '16%' },
  3: { x: '16%', y: '52%' },
}
const flyCard = ref(null)        // { card, from, to }
const flyStyle = computed(() => {
  const f = flyCard.value
  if (!f) return {}
  const a = SEAT_ANCHOR[f.from] || SEAT_ANCHOR[0]
  const b = SEAT_ANCHOR[f.to] || SEAT_ANCHOR[2]
  return { '--fx0': a.x, '--fy0': a.y, '--fx1': b.x, '--fy1': b.y }
})
let flyTimer = null
let flyPrimed = false
const seenFly = new Set()
function flyKey(h) { return `${h.kind}:${h.seat}:${h.to}:${h.card?.id}` }
function primeFly() {
  flyPrimed = true
  seenFly.clear()
  for (const h of history.value) {
    if (h.kind === 'tribute' || h.kind === 'return') seenFly.add(flyKey(h))
  }
}
watch(history, (list) => {
  if (!flyPrimed) return
  const h = list[0]
  if (!h || (h.kind !== 'tribute' && h.kind !== 'return')) return
  const k = flyKey(h)
  if (seenFly.has(k)) return
  seenFly.add(k)
  flyCard.value = { card: h.card, from: h.seat, to: h.to }
  clearTimeout(flyTimer)
  flyTimer = setTimeout(() => { flyCard.value = null }, 1000)
}, { deep: true })

/* ---------- 手牌自适应重叠（一屏展示全，不滑动） ---------- */
const handRef = ref(null)
const handW = ref(0)
let ro = null
const overlap = computed(() => {
  const n = viewHand.value.length
  const avail = handW.value
  const w = cardW.value
  if (!n || !avail || n < 2) return 0
  const need = n * w
  if (need <= avail) return 0
  const o = (need - avail) / (n - 1)
  // 每张至少露出「点数 + 花色」的一栏（约为牌宽的 30%，且不超过 26px）
  const minShow = Math.max(18, Math.min(26, w * 0.3))
  return Math.min(w - minShow, Math.max(0, o))
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
  // 同屏 p4：0 号位已经叫「你」，其余按座位号排「玩家二 / 三 / 四」。
  // 旧写法 `玩家${s === 2 ? '二' : '三'}` 会让 **1 号与 3 号座位都叫「玩家三」**。
  return HUMAN_SEATS.value.includes(s) ? `玩家${HUMAN_CN[s] || s + 1}` : SEAT_LABEL[s]
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
function doTribute(card) {
  if (!tributePending.value) return
  sel.value = []
  actOnline({ type: 'tribute', card_id: card.id })
}
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
  else if (winTeam === myTeam.value) sfx.win()
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
/**
 * 机器人「思考时间」：旧值 720ms，三家机器人连着出牌，真人根本反应不过来
 * （夜星：「机器人出来时，不管有没有牌，都控制在 2-3s 左右」）。
 * 出牌与过牌走的是同一个 aiTurn，所以这一个延时把两种情况都覆盖了；
 * 2.0~3.0s 随机，避免三家像节拍器。
 */
const AI_THINK_MIN = 2000
const AI_THINK_MAX = 3000
function aiThink() { return AI_THINK_MIN + Math.floor(Math.random() * (AI_THINK_MAX - AI_THINK_MIN)) }

let aiTimer = null
function scheduleAI() {
  clearTimeout(aiTimer)
  if (isOnline.value) return   // 在线由服务端 AI 推进
  if (phase.value !== 'playing') return
  if (HUMAN_SEATS.value.includes(turn.value)) return
  aiTimer = setTimeout(aiTurn, aiThink())
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
 *  牌是线性排布，布局在划选期间不变，故在按下时缓存一次矩形即可。 */
let cardRects = []
function cacheCardRects() {
  cardRects = []
  if (!handRef.value) return
  handRef.value.querySelectorAll('.gt-card').forEach((el, i) => {
    const r = el.getBoundingClientRect()
    cardRects.push({ i, left: r.left, right: r.right, top: r.top, bottom: r.bottom })
  })
}
/** 手牌区的「排列主轴」—— 手机全屏是「逻辑画布 + rotate(90deg)」的横屏视野
 *  （GamesView 的竖屏兜底），此时 `getBoundingClientRect()` 拿到的是**旋转后的轴对齐
 *  包围盒**：牌沿屏幕 y 轴排列，而**所有牌在屏幕 x 轴的区间几乎完全重合**。
 *  旧版固定用 clientX 去撞 rect.left/right，于是「划过整排只选中第一张」。
 *  这里按手牌区 AABB 的长边判断：竖条 → 牌沿 y 排（用 clientY），横条 → 沿 x 排。 */
function handAxis() {
  if (!handRef.value) return 'x'
  const r = handRef.value.getBoundingClientRect()
  return r.height > r.width ? 'y' : 'x'
}
/** ignoreCross=true 用于「划选进行中」：手指难免横向/纵向飘，此时不再校验横轴，
 *  只要还在手牌带附近就持续命中，划回起点也不会因为飘出去而断掉。 */
function cardIndexAt(clientX, clientY, ignoreCross = false) {
  if (!handRef.value || !cardRects.length) return -1
  const axis = handAxis()
  const p = axis === 'y' ? clientY : clientX   // 主轴：牌的排列方向
  if (!ignoreCross) {
    // 横轴：手指是否还在「手牌带」内。容差按牌宽给（旋转后横轴对应牌宽）
    const hr = handRef.value.getBoundingClientRect()
    const pad = Math.max(28, cardW.value * 0.5)
    const q = axis === 'y' ? clientX : clientY
    const lo = axis === 'y' ? hr.left : hr.top
    const hi = axis === 'y' ? hr.right : hr.bottom
    if (q < lo - pad || q > hi + pad) return -1
  }
  // 取「索引最大」的命中 = 视觉最上层那张（DOM 靠后 → 后绘制 → 盖在前一张上；
  // 旋转 90° 后「屏幕坐标增大」的方向恰好也是索引增大，故这条在两种朝向下都成立）
  let hit = -1
  for (const c of cardRects) {
    const a = axis === 'y' ? c.top : c.left
    const b = axis === 'y' ? c.bottom : c.right
    if (p >= a && p <= b) hit = c.i
  }
  return hit
}
function applySwipe(idx) {
  if (idx < 0) return
  /* 快速滑动时 pointermove 会跳点（一次 move 可能跨过好几张牌），只处理「当前命中的那一张」
     会表现为「划过 5 张只选中 2 张、中间漏掉」。这里补全 [上次命中, 本次命中] 之间的全部牌，
     并用 swipeCovered 去重，避免来回划过同一张时反复触发音效。 */
  const from = swipeLast < 0 ? idx : Math.min(swipeLast, idx)
  const to = swipeLast < 0 ? idx : Math.max(swipeLast, idx)
  swipeLast = idx
  let changed = false
  for (let i = from; i <= to; i++) {
    if (swipeCovered.has(i)) continue
    swipeCovered.add(i)
    const id = viewHand.value[i]?.id
    if (id == null) continue
    const has = sel.value.includes(id)
    if (swipeMode && !has) { sel.value.push(id); changed = true }
    else if (!swipeMode && has) { sel.value = sel.value.filter(x => x !== id); changed = true }
  }
  if (changed) sfx.pick()
}
/* 划选走 Pointer Events，但监听挂在 window 上，**不依赖 setPointerCapture**：
 * 部分 WebView 会在元素因选中而重渲染（class / transform 变化）时提前丢失指针捕获，
 * 触发 lostpointercapture → 表现为「划一半就断」。挂 window 则手指滑到手牌区外
 * （往上飘、划到牌桌上）也持续收得到事件，划回起点同样不断。 */
let dragId = null
let swipeCovered = new Set()
function onHandDown(e) {
  if (!canAct.value) return
  if (e.pointerType === 'mouse' && e.button !== 0) return
  cacheCardRects()
  const idx = cardIndexAt(e.clientX, e.clientY)
  if (idx < 0) return
  swipeMode = !sel.value.includes(viewHand.value[idx].id)
  swipeLast = -1
  swipeCovered = new Set()
  suppressClick = true
  dragId = e.pointerId
  window.addEventListener('pointermove', onHandMove, { passive: false })
  window.addEventListener('pointerup', onHandUp)
  window.addEventListener('pointercancel', onHandUp)
  applySwipe(idx)
}
function onHandMove(e) {
  if (swipeMode === null || dragId !== e.pointerId) return
  if (e.cancelable) e.preventDefault()
  applySwipe(cardIndexAt(e.clientX, e.clientY, true))
}
function onHandUp(e) {
  if (e && e.pointerId !== undefined && dragId !== null && e.pointerId !== dragId) return
  dragId = null
  swipeMode = null
  swipeLast = -1
  window.removeEventListener('pointermove', onHandMove)
  window.removeEventListener('pointerup', onHandUp)
  window.removeEventListener('pointercancel', onHandUp)
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
    summary: `第 ${roundNo.value} 局 · 我方 ${G.levelText(myLevel.value)} / 对方 ${G.levelText(oppLevel.value)}`,
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
  if (isOnline.value) {
    syncFromView(props.onlineView)
    primeFly()
    return
  }
  if (props.resume && restoreLocal()) toastMsg('已接着上一局继续')
  newRound()
})
onBeforeUnmount(() => {
  clearTimeout(aiTimer)
  clearTimeout(toastTimer)
  clearTimeout(flyTimer)
  if (ro) ro.disconnect()
  // 划选期间被卸载：window 上的手势监听必须摘掉，否则残留到下一个页面
  window.removeEventListener('pointermove', onHandMove)
  window.removeEventListener('pointerup', onHandUp)
  window.removeEventListener('pointercancel', onHandUp)
})
watch(() => viewHand.value.length, () => {
  flushIdx.value = 0
  requestAnimationFrame(measureHand)
})
</script>

<style scoped>
.gd-wrap { width: 100%; }
.gd {
  display: flex; flex-direction: column; gap: 6px;
  /* 全屏一屏只有 360px 高，外壳留白每一点都要算：旧 10/12 + gap8 → 新 6/8 + gap6，
     省下的 12px 全给牌桌（见 .gd-table / .gd-center 的注释）。 */
  padding: 6px 10px 8px; min-height: 520px;
}
.gd.is-big { min-height: calc(100vh - 140px); }

/* 牌尺寸跟随牌桌高度（JS 写入 --card-w / --card-h）；牌面字号按牌宽等比缩放 */
.gd .gt-card { width: var(--card-w, 62px); height: var(--card-h, 88px); }
/* 牌面改轻投影：旧版「厚纸板」式双层硬阴影在深色绒布上显得笨重，
   减轻后更贴近腾讯棋牌的扁平质感（圆角也放大一档） */
.gd .gt-card {
  border-radius: 8px;
  box-shadow: 0 2px 0 rgba(0, 0, 0, .22), 0 7px 15px -10px rgba(0, 0, 0, .78);
}
.gd .gt-card .c-tl b { font-size: calc(var(--card-w, 62px) * 0.245); }
.gd .gt-card .c-tl i { font-size: calc(var(--card-w, 62px) * 0.2); }
.gd .gt-card .c-mid { font-size: calc(var(--card-w, 62px) * 0.5); }
.gd .gt-card .c-br b { font-size: calc(var(--card-w, 62px) * 0.17); }
.gd .gt-card .c-br i { font-size: calc(var(--card-w, 62px) * 0.155); }
.gd .gt-card .tag { font-size: calc(var(--card-w, 62px) * 0.15); }
.gd .gt-card.is-joker .c-tl b { font-size: calc(var(--card-w, 62px) * 0.21); }

/* 顶栏 */
.gd-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
/* 全屏时顶栏让位给牌桌：收起顶栏，级牌与比分改由底栏 .gd-scorebar 承载（信息不丢） */
.gd.is-big .gd-top { display: none; }
/* 团队比分胶囊：把「我方 / 对方」两枚 pill 合成一枚，顶栏不再被撑成两行 */
.gd-score {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 11px; border-radius: 999px;
  font-size: 11.5px; font-variant-numeric: tabular-nums;
  background: rgba(255, 255, 255, .07); border: 1px solid var(--gt-line);
}
.gd-score .me { color: var(--gt-gold); font-style: normal; font-weight: 600; }
.gd-score .op { color: var(--gt-ink-dim); font-style: normal; }
.gd-score em { font-style: normal; opacity: .4; }

/* 牌桌：主区 + 左下角出牌记录（浮层，默认收起，不占牌桌宽度） */
.gd-table {
  position: relative;
  flex: 1; min-height: 0; display: flex; gap: 10px;
  padding: 8px; border-radius: 16px;
  /* 墨绿绒布（与麻将、大富翁同一色系）：旧版只是一层极淡的白雾叠在深色壳上，
     牌桌与外壳分不出边界，52 张牌像浮在空气里 */
  background:
    radial-gradient(120% 100% at 50% 0%, rgba(255, 255, 255, .09), transparent 58%),
    radial-gradient(100% 92% at 50% 55%, #227154 0%, #17573f 46%, #0d3a2b 100%);
  border: 1px solid rgba(255, 255, 255, .1);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, .06),
    inset 0 0 62px -12px rgba(0, 0, 0, .6);
}
.gd-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.gd-row { display: flex; align-items: center; }
.gd-row-top { justify-content: center; position: relative; }
/* 对家座位压扁到 ~34px：全局 .gt-seat 是 34px 头像 + 7px 上下 padding = 50px 高，
   一屏 360px 的横屏里太奢侈（它和中央出牌区抢的正是同一份高度）。 */
.gd-row-top .gt-seat { padding: 2px 9px 2px 3px; gap: 7px; }
.gd-row-top .gt-seat-av { width: 26px; height: 26px; font-size: 13px; }
.gd-row-top .gt-seat-name { font-size: 11.5px; max-width: 92px; }
.gd-row-top .gt-seat-sub { font-size: 10px; }
.gd-row-mid { flex: 1; min-height: 0; justify-content: space-between; align-items: center; gap: 14px; }
.gd-seat-side { flex-direction: column; text-align: center; max-width: 96px; padding: 8px 6px; }
.gd-seat-side .gt-seat-tx { align-items: center; }
.gd-seat-side .gt-seat-name { max-width: 84px; }

/* 轮到谁出牌：牌区右上角，常驻。轮到自己时金底高亮（一眼看出该我动了） */
.gd-turnbox {
  position: absolute; right: 0; top: 50%; transform: translateY(-50%);
  display: inline-flex; align-items: baseline; gap: 5px;
  padding: 5px 12px; border-radius: 999px;
  background: rgba(0, 0, 0, .42);
  border: 1px solid rgba(233, 200, 119, .45);
  box-shadow: 0 0 18px -7px rgba(233, 200, 119, .55);
  white-space: nowrap;
}
.gd-turnbox em, .gd-turnbox i { font-style: normal; font-size: 11px; color: var(--gt-ink-dim); }
.gd-turnbox b { font-size: 15px; font-weight: 700; color: var(--gt-gold); letter-spacing: .02em; }
.gd-turnbox.is-me {
  background: linear-gradient(180deg, rgba(244, 220, 156, .96), rgba(217, 182, 95, .96));
  border-color: rgba(255, 255, 255, .5);
  box-shadow: 0 0 22px -4px rgba(233, 200, 119, .95);
}
.gd-turnbox.is-me b, .gd-turnbox.is-me em, .gd-turnbox.is-me i { color: #2a1d05; }
.gd-turnbox.is-done { opacity: .55; }

/* 中央出牌区 */
.gd-center {
  flex: 1; min-width: 0; min-height: 84px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 6px;
  padding: 8px; border-radius: 14px;
  background: rgba(0, 0, 0, .13); border: 1px solid rgba(255, 255, 255, .07);
}
.gd-center-head { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.gd-center-cards { display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; min-height: 60px; align-items: center; }
/* 中央已出的牌接近手牌尺寸：出牌区才是牌桌主角，旧版缩到 0.82 倍反而比手牌小一圈，
   「谁出了什么」得凑近才看得清 */
.gd-center .gt-card { width: calc(var(--card-w, 62px) * 0.94); height: calc(var(--card-h, 88px) * 0.94); }
.gd-center-empty { margin: 0; font-size: 12.5px; color: var(--gt-ink-dim); }

/* 出牌记录：牌桌**右侧真正的竖栏**（不再是 absolute 浮层）。
   旧版是 `position:absolute; left:10px; bottom:10px; width:190px` 的浮层 ——
   它正压在左家的座位牌上（截图里 左家的「15 张」被盖掉半截），
   长起来还会压住中央出的牌；三样东西叠在一起，就是「横屏挤在一块」的主因。
   改成 flex 列后彻底不重叠，窗内自己滚动回看。 */
.gd-history {
  flex: 0 0 176px; align-self: stretch; min-height: 0;
  display: flex; flex-direction: column; gap: 6px;
  border-radius: 12px; padding: 7px 6px 7px 8px;
  background: rgba(6, 18, 26, .5); border: 1px solid var(--gt-line);
}
.gd-history.is-collapsed { flex: 0 0 106px; padding: 4px 6px; }
.gd-history.is-collapsed .gd-history-head { padding: 0 2px; gap: 5px; }
.gd-history-head {
  display: flex; align-items: center; gap: 6px;
  font-size: 11.5px; font-weight: 600; color: var(--gt-ink-dim);
  padding: 0 4px 4px; border-bottom: 1px solid var(--gt-line);
}
.gd-history-head > span { flex: 1; }
.gd-history-head i { font-style: normal; font-size: 10.5px; opacity: .7; font-variant-numeric: tabular-nums; }
.gd-history-toggle {
  appearance: none; cursor: pointer; font-family: inherit; font-size: 10.5px; line-height: 1.5;
  padding: 1px 7px; border-radius: 999px; color: var(--gt-ink-dim);
  background: rgba(255, 255, 255, .08); border: 1px solid var(--gt-line);
}
.gd-history-toggle:hover { color: var(--gt-ink); border-color: rgba(233, 200, 119, .5); }
.gd-history-list {
  margin: 0; padding: 2px 4px 2px 0; list-style: none;
  /* 右侧竖栏整条高度都给列表（旧版是 96px 的浮层小窗） */
  flex: 1; min-height: 0; max-height: none; overflow-y: auto;
  display: flex; flex-direction: column; gap: 4px;
  scrollbar-width: thin; overscroll-behavior: contain;
}
.gd-history-list::-webkit-scrollbar { width: 6px; }
.gd-history-list::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, .2); border-radius: 3px; }
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
.gd-his-arrow { font-size: 10.5px; color: var(--gt-ink-dim); flex: none; }

/* 同花顺按钮的组合数角标 */
.gd-btn-count {
  font-style: normal; margin-left: 4px; font-size: 10.5px; line-height: 1.6;
  padding: 0 5px; border-radius: 999px;
  background: rgba(0, 0, 0, .22); color: var(--gt-gold);
}

/* 进贡 / 还贡飞牌：从进贡方席位飞向受贡方席位 */
.gd-fly {
  position: absolute; z-index: 9; pointer-events: none;
  margin-left: -31px; margin-top: -44px;
  animation: gd-fly .95s cubic-bezier(.34, .06, .26, 1) both;
}
@keyframes gd-fly {
  0% { left: var(--fx0, 50%); top: var(--fy0, 84%); opacity: 0; transform: scale(.62) rotate(-10deg); }
  16% { opacity: 1; }
  70% { left: var(--fx1, 50%); top: var(--fy1, 16%); opacity: 1; transform: scale(1.08) rotate(0deg); }
  100% { left: var(--fx1, 50%); top: var(--fy1, 16%); opacity: 0; transform: scale(.94); }
}
@media (prefers-reduced-motion: reduce) {
  .gd-fly { animation-duration: .01ms; }
}

/* 底部手牌 */
.gd-bottom { display: flex; flex-direction: column; gap: 4px; flex: none; }
.gd-bottom-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.gd-hand-tag { font-size: 12.5px; font-weight: 600; color: var(--gt-gold); }
/* 全屏才出现的级牌 / 比分（此时顶栏已收起，靠它兜住信息） */
.gd-scorebar {
  display: none; font-size: 11.5px; color: var(--gt-ink-dim);
  font-variant-numeric: tabular-nums;
}
.gd.is-big .gd-scorebar { display: inline-flex; }
.gd-mini {
  font-size: 11px; padding: 2px 8px; border-radius: 999px;
  background: rgba(255, 255, 255, .07); border: 1px solid var(--gt-line);
  color: var(--gt-ink-dim); font-variant-numeric: tabular-nums;
}
.gd-mini.on { background: rgba(233, 200, 119, .18); border-color: rgba(233, 200, 119, .5); color: var(--gt-gold); }
.gd-hand {
  display: flex; gap: 0; justify-content: center; align-items: flex-end;
  /* 上留白正好是选中上浮的高度，牌不会被裁 */
  padding: calc(var(--card-h, 88px) * 0.2) 4px 4px; min-height: 0;
  overflow: visible;
  touch-action: none;            /* 划选时既不滚动页面也不触发双指缩放 */
  -webkit-user-select: none; user-select: none;
}
.gd-hand .gt-card { margin-right: calc(-1 * var(--gd-overlap, 0px)); }
.gd-hand .gt-card:last-child { margin-right: 0; }
.gd-hand .gt-card:hover, .gd-hand .gt-card.is-sel { z-index: 5; }
.gd-hand-empty { margin: auto; font-size: 12px; color: var(--gt-ink-dim); }

/* 操作区：次要工具收成小号弱按钮，「不要 / 出牌」是大按钮主力（腾讯棋牌同款主次关系） */
.gd-actions { justify-content: center; gap: 8px; }
/* 提示/重选/同花顺/不要/出牌：全局 .gt-btn 是 8px/18px（39px 高），
   一屏 360px 的横屏里偏奢侈，收成 6px/16px（约 33px）。手牌尺寸不动。 */
.gd-actions .gt-btn { padding: 6px 16px; font-size: 12.5px; }
.gd-act-gap { width: 10px; flex: none; }
.gd-play {
  min-width: 96px;
  background: linear-gradient(180deg, #d9483f, #a82f2a);
  border-color: rgba(255, 255, 255, .28);
  box-shadow: 0 6px 16px -8px rgba(217, 72, 63, .95);
}
.gd-play:not(:disabled):hover { background: linear-gradient(180deg, #e2554c, #b8332d); }
.gd-pass { min-width: 80px; }

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

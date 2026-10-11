<template>
  <div class="gt-landscape">
    <div ref="rootRef" class="gt-shell mj" :class="{ 'is-big': big }" :style="{ '--gt-h': rootH + 'px' }">
      <!-- ===== 顶栏 ===== -->
      <header class="mj-top">
        <span class="gt-title">四川麻将</span>
        <span class="gt-pill gold">胡牌即结束 · 第 {{ roundNo }} 局</span>
        <span v-if="dice" class="gt-pill" title="庄家掷骰开门：总和定方位，小点数定墩位">
          骰 {{ dice[0] }}+{{ dice[1] }} · 开{{ openSideName }}第{{ openIdx + 1 }}墩
        </span>
        <span class="gt-pill">余牌 {{ wall.length }}</span>
        <span class="gt-spacer"></span>
        <button class="gt-btn sm ghost" :title="muted ? '取消静音' : '静音'" @click="toggleMute">
          {{ muted ? '🔇' : '🔊' }}
        </button>
        <button class="gt-btn sm ghost" :class="{ 'is-off': !hapticsOn }" :title="hapticsOn ? '关闭震动反馈' : '开启震动反馈'" @click="toggleHaptics">
          📳
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
            </span>
            <!-- 本局积分（V24617-013）：紧跟名字，实时显示 ±分；v2.46.19 起变化时滚动过渡 -->
            <span class="gt-seat-score" :class="dispScores[p.seat] > 0 ? 'is-plus' : dispScores[p.seat] < 0 ? 'is-minus' : ''">
              {{ dispScores[p.seat] > 0 ? '+' : '' }}{{ dispScores[p.seat] }}
            </span>
            <span v-if="isTurn(p.seat) && !out[p.seat]" class="gt-seat-badge">出牌中</span>
            <span v-else-if="out[p.seat]" class="gt-seat-badge">已胡</span>
            <!-- 听牌标识（v2.46.24，夜星：展示哪家听牌了） -->
            <span v-else-if="tingFlags[p.seat]" class="gt-seat-badge is-ting">听牌</span>
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

        <!-- 中央：四方弃牌（上=对家 / 下=自己 / 左=左家 / 右=右家），座位号全部过
             disSeats 投影 —— 在线时以自己的座位为原点，而不是写死的 0 号位视角。
             旧版中央还有个「最近舍牌 + 战报」信息盒，它在 grid 里占 minmax(0,1fr) 整列，
             把左右两家的弃牌挤到桌外、上下两家只剩一行 —— 实测弃牌区只有 403×28px。
             现在信息全部搬到下方信息条（.mj-handbar，本来就有位置），中央整块还给弃牌。 -->
        <div class="mj-center">
          <!-- 四方牌墙（v2.46.42）：4 边 × 15 墩牌背，随摸牌缩短（零头墩半透）；
               开门墩鎏金标记。纯展示不挡交互；屏幕边 → 绝对座位过 povSeat
               投影（V2467-001），墩序按各边物理朝向翻转。 -->
          <div v-if="dice" class="mj-walls" aria-hidden="true">
            <div v-for="side in ['up', 'left', 'right', 'down']" :key="side" class="mj-wall" :class="'mj-wall-' + side">
              <span
                v-for="(wst, s) in wallShape[side]"
                :key="s"
                class="mj-wstack"
                :class="{ 'is-half': wst.n === 1, 'is-gone': wst.n === 0, 'is-open': isOpenStack(side, wst.i) }"
              ></span>
            </div>
          </div>
          <div class="mj-dis mj-dis-up">
            <span
              v-for="t in discards[disSeats.up]"
              :key="t.id"
              class="gt-tile mini"
              :class="[suitCls(t), { 'is-land': t.id === freshDiscardId }]"
              :style="{ '--tilt': discardTilt(t) }"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>

          <div class="mj-dis mj-dis-left">
            <span
              v-for="t in discards[disSeats.left]"
              :key="t.id"
              class="gt-tile mini"
              :class="[suitCls(t), { 'is-land': t.id === freshDiscardId }]"
              :style="{ '--tilt': discardTilt(t) }"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>

          <div class="mj-dis mj-dis-right">
            <span
              v-for="t in discards[disSeats.right]"
              :key="t.id"
              class="gt-tile mini"
              :class="[suitCls(t), { 'is-land': t.id === freshDiscardId }]"
              :style="{ '--tilt': discardTilt(t) }"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>

          <div class="mj-dis mj-dis-down">
            <span
              v-for="t in discards[disSeats.down]"
              :key="t.id"
              class="gt-tile mini"
              :class="[suitCls(t), { 'is-land': t.id === freshDiscardId }]"
              :style="{ '--tilt': discardTilt(t) }"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>

          <!-- 碰/杠大字（v2.46.20）：金底墨字 pop 一闪，动画自身管进出场 -->
          <b v-if="claimFx" class="mj-claim-fx" aria-hidden="true">{{ claimFx }}</b>
        </div>
      </div>

      <!-- ===== 底部：信息条 + 手牌 + 操作 =====
           信息条一行装完「最近舍牌 / 轮到谁 / 手牌 / 余牌 / 副露 / 听牌」——
           旧版听牌另起一整行（.mj-tingbar），在一屏只有 360px 高的横屏里白吃 38px，
           弃牌区因此被压到 28px 高。现在一行到底，高度全让给牌桌。 -->
      <footer class="mj-bottom">
        <div class="mj-handbar">
          <span v-if="lastDiscard" class="mj-lastmini">
            <span class="gt-tile mini" :class="suitCls(lastDiscard.tile)">
              <MahjongTileFace :suit="faceSuit(lastDiscard.tile)" :rank="lastDiscard.tile.rank" />
            </span>
            <em>{{ seatName(lastDiscard.seat) }} 打出</em>
          </span>
          <span v-else class="gt-sub">开局</span>
          <span v-if="phase === 'playing' && !pending" class="gt-pill gold">轮到 {{ seatName(turn) }}</span>
          <span v-if="isTing" class="gt-pill gold">听牌</span>
          <!-- 我的积分（v2.46.24，夜星：电脑端全屏时不展示自己的得分）：
               旧版积分只摆在别家席位卡上，自己的分数没有任何位置 —— 信息条补一枚 -->
          <span class="gt-pill" :class="{ gold: dispScores[viewSeat] > 0 }">
            积分 {{ dispScores[viewSeat] > 0 ? '+' : '' }}{{ dispScores[viewSeat] }}
          </span>
          <span class="gt-pill">{{ seatName(viewSeat) }}手牌 {{ viewHand.length }}</span>
          <span class="gt-pill">余牌 {{ wall.length }}</span>
          <span v-if="melds[viewSeat]?.length" class="gt-pill">副露 {{ melds[viewSeat].length }}</span>
          <span class="gt-spacer"></span>
          <span v-if="phase === 'playing' && viewSeat !== null" class="mj-ting-inline">
            <template v-if="waitingTing.length">
              <!-- v2.46.24：真正的等牌听牌 —— 直接亮听哪些牌（旧版把「打一张可听」
                   当成听牌标，等牌状态反而显示「尚未听牌」，夜星反馈） -->
              <em class="mj-ting-gold">已听 <b>{{ waitingTing.map(tileText).join(' / ') }}</b></em>
            </template>
            <template v-else-if="tingInfo.length">
              <!-- 一向听提示：打哪张就能听（点击听牌项直接选中那张牌，v2.46.19） -->
              <em class="mj-ting-label">一向听</em>
              <button
                v-for="(info, i) in tingInfo.slice(0, 3)"
                :key="i"
                class="mj-ting-item"
                :title="`点击选中 ${tileText(info.tile)}`"
                @click="selectTing(info)"
              >
                打<b>{{ tileText(info.tile) }}</b>听<b>{{ info.waits.map(tileText).join('/') }}</b>
              </button>
            </template>
            <em v-else class="mj-ting-none">尚未听牌</em>
          </span>
        </div>

        <!-- 反应窗口：碰 / 杠 / 胡 / 过（v2.46.14：从手牌右侧移到手牌上方独立一行）
             v2.46.17（V24617-010）：把被碰/杠的那张牌直接亮在按钮前，手上能组成
             该刻子的牌同时描金脉冲（.is-claimhit），一眼看清「碰的是哪张、用哪几张」 -->
        <div v-if="pending" class="gt-actions mj-actions">
          <span class="gt-pill gold">可操作：{{ pending.kinds.map(k => REACT_NAME[k]).join(' / ') }}</span>
          <span v-if="pending.tile" class="mj-claimtile">
            <span class="gt-tile mini" :class="suitCls(pending.tile)">
              <MahjongTileFace :suit="faceSuit(pending.tile)" :rank="pending.tile.rank" />
            </span>
            <em>{{ seatName(pending.from) }} 打出 {{ tileText(pending.tile) }}</em>
          </span>
          <button v-if="pending.kinds.includes('hu')" class="gt-btn is-pulse" @click="onReact('hu')">胡</button>
          <button v-if="pending.kinds.includes('kong')" class="gt-btn is-pulse" @click="onReact('kong')">杠</button>
          <button v-if="pending.kinds.includes('pong')" class="gt-btn is-pulse" @click="onReact('pong')">碰</button>
          <button v-if="pending.kinds.includes('chi')" class="gt-btn is-pulse" @click="onReact('chi')">吃</button>
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
          <em v-if="canDiscard" class="mj-hint">上滑手牌直接打出</em>
        </div>

        <div class="mj-handrow">
        <!-- 自己的碰 / 杠副露：旧版只给个「副露 N」文字计数，牌面不展示 ——
             碰了什么全靠记。现在跟其他三家一样用迷你牌摆在手牌左侧。 -->
        <div v-if="ownMelds.length" class="mj-ownmelds">
          <span v-for="(md, i) in ownMelds" :key="i" class="gt-meld">
            <span
              v-for="(t, k) in meldTiles(md)"
              :key="k"
              class="gt-tile mini"
              :class="suitCls(t)"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </span>
        </div>
        <div class="mj-hand" ref="handRef" :class="{ 'is-deal': dealing }" :style="{ '--ntiles': Math.max(1, handTiles.length) }" @pointerdown="onHandDown">
          <span
            v-for="(t, i) in viewHand"
            :key="t.id"
            class="gt-tile"
            :data-tid="t.id"
            :style="{ '--i': i }"
            :class="[suitCls(t), {
              pickable: canDiscard,
              'is-sel': selId === t.id,
              'is-claimhit': claimHit(t),
              'is-lift': liftId === t.id,
            }]"
            @click="pick(t)"
          >
            <MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" />
          </span>
          <span
            v-if="viewDrawn"
            :key="viewDrawn.id"
            class="gt-tile is-drawn"
            :data-tid="viewDrawn.id"
            :class="[suitCls(viewDrawn), {
              pickable: canDiscard,
              'is-sel': selId === viewDrawn.id,
              'is-claimhit': claimHit(viewDrawn),
              'is-lift': liftId === viewDrawn.id,
            }]"
            @click="pick(viewDrawn)"
          >
            <MahjongTileFace :suit="faceSuit(viewDrawn)" :rank="viewDrawn.rank" />
          </span>
          <p v-if="!handTiles.length" class="mj-hand-empty">— 无手牌 —</p>
        </div>
        </div>
      </footer>

      <!-- ===== 胡牌动画浮层（V24617-011，在线 & 本地共用）=====
           胡牌后先全屏展示赢家 14 张牌 + 番种，牌逐张翻入；点击任意处关闭，
           露出下面的结算卡（再来一局 / 返回）。不再「胡完直接跳积分」。 -->
      <div v-if="showHuShow" class="gt-over mj-hushow" @click="huShow = false">
        <!-- 胡牌时刻的彩带雨（reduced-motion 下 CSS 直接隐藏） -->
        <div class="gt-confetti" aria-hidden="true">
          <i v-for="(st, i) in confetti" :key="i" :style="st"></i>
        </div>
        <div class="mj-hushow-card">
          <p class="mj-hushow-title">{{ huWinner ? seatName(huWinner.seat) : '' }}{{ huWinner?.zimo ? ' 自摸' : ' 胡牌' }}！</p>
          <p v-if="huWinner" class="mj-hushow-fan">{{ huWinner.names.join(' · ') }} · {{ huWinner.fan }} 番</p>
          <div v-if="huWinner?.hand?.length" class="mj-hushow-hand">
            <span
              v-for="(t, i) in huWinner.hand"
              :key="t.id + '-' + i"
              class="gt-tile"
              :class="suitCls(t)"
              :style="{ animationDelay: (i * 60) + 'ms' }"
            ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
          </div>
          <p class="mj-hushow-tip">点击任意处继续</p>
        </div>
      </div>

      <!-- ===== 结算（页内，不弹窗） ===== -->
      <div v-if="phase === 'settled'" class="gt-over">
        <div class="gt-over-card">
          <div v-if="result?.delta > 0" class="gt-confetti" aria-hidden="true">
            <i v-for="(st, i) in confetti" :key="i" :style="st"></i>
          </div>
          <h3>{{ result?.matchOver ? `整场结束 · ${matchChampion !== null ? seatName(matchChampion) + ' 胜' : '平分'}` : result?.title }}</h3>
          <p>
            <template v-if="result?.hus?.length">
              <span v-for="(h, i) in result.hus" :key="i">
                {{ seatName(h.seat) }}：{{ h.names.join(' · ') }} {{ h.fan }} 番
                <em>（{{ h.zimo ? '自摸' : '点炮' }}）</em><br>
                <!-- 胡牌牌面（v2.46.22）：结算卡内嵌 14 张，不用回翻胡牌浮层也能看 -->
                <span v-if="h.hand?.length" class="mj-over-hand">
                  <span
                    v-for="(t, j) in h.hand"
                    :key="j"
                    class="gt-tile mini"
                    :class="suitCls(t)"
                  ><MahjongTileFace :suit="faceSuit(t)" :rank="t.rank" /></span>
                </span>
              </span>
            </template>
            <template v-else>流局：牌墙摸完，无人胡牌。</template>
            <br>
            你的得分：<b>{{ result?.delta > 0 ? '+' : '' }}{{ deltaShown }}</b> 点
            <!-- 整场制（v2.46.22）：本局分只是过程，整场先到 100 分才结束结算 -->
            <em v-if="result?.matchDeltas" class="mj-over-matchline">
              · 整场累计 {{ myMatchDelta > 0 ? '+' : '' }}{{ myMatchDelta }} 分（目标 {{ result?.matchTarget }}）
            </em>
          </p>
          <!-- 四人整场汇总（v2.46.22）：谁赢多少一目了然 -->
          <div v-if="matchSummary" class="mj-over-match">
            <span
              v-for="m in matchSummary"
              :key="m.seat"
              :class="m.delta > 0 ? 'is-plus' : m.delta < 0 ? 'is-minus' : ''"
            >{{ seatName(m.seat) }} {{ m.delta > 0 ? '+' : '' }}{{ m.delta }}<em>（{{ m.total }}/{{ m.target }}）</em></span>
          </div>
          <div class="gt-actions">
            <button v-if="!result?.matchOver" class="gt-btn" @click="nextRound">再来一局</button>
            <button class="gt-btn ghost" @click="doExit">返回列表</button>
          </div>
        </div>
      </div>

      <div v-if="toast" class="gt-toast">{{ toast }}</div>
      <div class="gt-watermark">四 川 麻 将 · 胡 牌 即 结 束</div>
    </div>
  </div>
</template>

<script setup>
/** 四川麻将 · 胡牌即结束 牌桌（v2.46.17）。
 *
 * 纯前端同屏对局：solo = 1 真人 + 3 AI；duo = 2 真人同屏 + 2 AI；quad = 4 真人轮流。
 * 规则核心在 `utils/games/mahjong.js`（和牌判定 / 番种 / 听牌 / 向听 / AI）。
 * 视觉走 `assets/styles/game-table.css` 的独立牌桌皮肤，不污染全站玄黄主题。
 *
 * 简化声明（与引擎注释一致）：
 * 1. **胡牌即结束**（v2.46.10 起，不再是血战到底）：任一家胡牌本局立即收摊，其余人不补打；
 *    点炮只取「一家胡」，按「放炮者下家起逆时针」就近优先，不存在一炮多响。
 * 2. **无定缺**（v2.46.17 起，夜星要求「单纯的胡牌规则」）：开局庄家直接起手，
 *    没有缺门限制；庄家轮换 —— 上一局胡牌者下局坐庄先出。
 * 3. 在线开房（v2.44）：服务端权威发牌，前端只渲染投影、动作 emit('act') 上抛；
 *    本地同屏（solo/duo/quad）逻辑完全不变，在线分支统一走 `isOnline`。
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import * as M from '@/utils/games/mahjong.js'
import { sfx, setMuted, isMuted, panOf } from '@/utils/games/sfx'
import { hapticsEnabled, setHaptics } from '@/utils/games/haptics'
import confettiPieces from '@/utils/games/confetti'
import countUp from '@/utils/games/countUp'
import { speak, tileSpeech } from '@/utils/games/tts'
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
const REACT_NAME = { hu: '胡', kong: '杠', pong: '碰', chi: '吃' }
const STAKE = 100
const BASE = 10
/** 本局胡牌的座位（本地庄家轮换用）：null = 流局 */
const lastWinnerSeat = ref(null)

/* ---------- 状态 ---------- */
const mode = ref(props.initialMode || 'solo')
const phase = ref('playing')       // playing | settled（v2.46.17 起无定缺阶段）
const roundNo = ref(1)
const dealer = ref(0)
const wall = ref([])
const hands = ref([[], [], [], []])
const melds = ref([[], [], [], []])
const discards = ref([[], [], [], []])
const out = ref([false, false, false, false])   // 本局已胡（胡牌即结束 → 一局最多一家为 true）
const turn = ref(0)
const drawn = ref(null)
// 开牌仪式（v2.46.42）：骰子 + 开门信息。null/负 = 旧局态无仪式（前端跳过、不渲染牌墙）
const dice = ref(null)
const openRel = ref(-1)            // 开门边（相对庄：0 本门/1 下家/2 对家/3 上家）
const openIdx = ref(0)             // 开门墩（边内 0 基、自墩主右端数）
/* v2.46.46（夜星：开场动画碍事）：开牌仪式 overlay 已整体移除——
   服务端的骰子/开门信息（dice/open_rel/open_idx）保留，牌墙开门墩鎏金仍靠它们渲染。 */
const lastDiscard = ref(null)
// 注意：牌堆 id 从 0 起，不能用 0 当「未选中」哨兵，否则 id=0 那张牌永远打不出去
const selId = ref(null)
const logs = ref([])
const huResults = ref([])
const result = ref(null)
/** 结算「你的得分 +N 点」逐格上滚（v2.46.20，Balatro 式 tick） */
const deltaShown = countUp(() => result.value?.delta ?? 0)
const pending = ref(null)          // { seat, from, tile, kinds }
const reactQueue = ref([])
const reactFrom = ref(null)
/** 本张弃牌上已经选过「不胡」的座位：顺延给下一家（胡牌即结束，一炮只取一家） */
const huDeclined = ref([])
/** 胡牌动画浮层（V24617-011）：settled 且有胡牌时先展示 14 张牌，点击才进结算卡 */
const huShow = ref(false)
const toast = ref('')
const muted = ref(isMuted())
/** 触感反馈开关（v2.46.19）：与静音并列的小按钮 */
const hapticsOn = ref(hapticsEnabled())
function toggleHaptics() { hapticsOn.value = !hapticsOn.value; setHaptics(hapticsOn.value) }
/** 胡牌 / 胜局彩带参数（确定性伪随机，一次生成复用） */
const confetti = confettiPieces(26)

/* ---------- 派生 ---------- */
const isOnline = computed(() => props.online)
const oSeat = computed(() => Number(props.onlineSeat ?? 0))
const HUMAN_SEATS = computed(() => {
  if (mode.value === 'solo') return [0]
  if (mode.value === 'duo') return [0, 2]
  return [0, 1, 2, 3]
})
function isHuman(s) { return HUMAN_SEATS.value.includes(s) }

/** V24613-004：席位/弃牌一律过 povSeat 投影 —— 本地以 0 号位（你）为原点；
 *  在线以自己的座位为原点（我坐 1 号位，左边就是 0 号位、右边是 2 号位），
 *  不再写死「下=0 号位」的绝对摆位。与掼蛋 povSeat（V2467-001）同一规矩。 */
const povSeat = computed(() => (isOnline.value ? oSeat.value : 0))
const relSeat = (rel) => (povSeat.value + rel) % 4
/** 三家席位面板：对家（rel2）横排在上，上家（rel3）在左、下家（rel1）在右（竖排） */
const PANEL_SEATS = computed(() => [
  { seat: relSeat(2), cls: 'mj-seat-top', dir: 'is-h' },
  { seat: relSeat(3), cls: 'mj-seat-left', dir: 'is-v' },
  { seat: relSeat(1), cls: 'mj-seat-right', dir: 'is-v' },
])
/** 中央四方弃牌的座位投影：下=自己、右=下家、上=对家、左=上家 */
const disSeats = computed(() => ({
  up: relSeat(2), left: relSeat(3), right: relSeat(1), down: povSeat.value,
}))
/** 自己（底部视角）的碰 / 杠副露：手牌左侧摆牌面，替代旧版「副露 N」纯计数 */
const ownMelds = computed(() => melds.value[viewSeat.value] || [])

/* ---------- 四方牌墙（v2.46.42）：屏幕边 → 绝对座位 → 摸墙环内墩序 ----------
 * 每边 15 墩、墩内 i=0 在墩主自己的右手侧。屏显顺序按物理朝向翻转：
 * 自己(down)与左家 i=0 落在屏幕右/下端 → 反序；对家(up)与右家 i=0 落在
 * 屏幕左/上端 → 正序。老局态无骰子信息 → 不渲染（保持旧观感）。 */
const WALL_SCREEN = ['down', 'right', 'up', 'left']
function screenSeat(side) {
  return side === 'down' ? povSeat.value : relSeat(side === 'right' ? 1 : side === 'up' ? 2 : 3)
}
const wallShape = computed(() => {
  const res = { down: [], right: [], up: [], left: [] }
  const left = wall.value.length
  if (!dice.value || left > M.MJ_WALL_AFTER_DEAL) return res
  for (const screen of WALL_SCREEN) {
    const rel = (screenSeat(screen) - dealer.value + 4) % 4
    const rp = M.MJ_RING.indexOf(rel)
    const arr = []
    for (let i = 0; i < M.MJ_STACKS; i++) arr.push({ i, n: M.stackRemain(rp * M.MJ_STACKS + i, left) })
    if (screen === 'down' || screen === 'left') arr.reverse()
    res[screen] = arr
  }
  return res
})
const openAbs = computed(() => (dice.value ? (dealer.value + openRel.value) % 4 : -1))
const openSideName = computed(() => (openRel.value >= 0 ? M.MJ_OPEN_SIDE_NAME[openRel.value] : ''))
function isOpenStack(screen, i) {
  return openAbs.value >= 0 && screenSeat(screen) === openAbs.value && i === openIdx.value
}

const viewSeat = computed(() => {
  if (isOnline.value) return oSeat.value
  if (isHuman(turn.value) && !out.value[turn.value]) return turn.value
  return HUMAN_SEATS.value[0]
})
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

/* ---------- 碰杠提示（V24617-010）----------
 * 反应窗口弹出时：被碰/杠的那张牌亮在按钮前，手上能组成该刻子的牌描金脉冲。
 * 本地/在线同一逻辑：pending.tile 就是那张弃牌。 */
function claimHit(t) {
  const p = pending.value
  return !!(p && p.tile && p.kinds.some(k => k === 'pong' || k === 'kong')
    && t && t.suit === p.tile.suit && t.rank === p.tile.rank)
}

/* ---------- 本局积分（V24617-013）----------
 * 在线读服务端投影的 players[].match_score（v2.46.22 整场累计：历局 + 本局实时）；
 * 本地按 huResults 现算（自摸三家各付、点炮放炮者付两倍）。 */
function seatScore(s) {
  if (isOnline.value) return Number(props.onlineView?.players?.[s]?.match_score || 0)
  let v = 0
  for (const r of huResults.value) {
    const gain = BASE * r.fan
    if (r.zimo) v += (s === r.seat ? 3 : -1) * gain
    else if (s === r.seat) v += 2 * gain
    else if (s === r.from) v -= 2 * gain
  }
  return v
}

/* ---------- 积分滚动（v2.46.19）：分数变化用 0.65s ease-out 滚过去，不再跳变 ---------- */
const dispScores = ref([0, 0, 0, 0])
let scoreRaf = 0
watch(() => [0, 1, 2, 3].map(seatScore), (targets) => {
  const from = dispScores.value.slice()
  const t0 = performance.now()
  cancelAnimationFrame(scoreRaf)
  const step = (now) => {
    const k = Math.min(1, (now - t0) / 650)
    const e = 1 - Math.pow(1 - k, 3)
    dispScores.value = targets.map((t, i) => Math.round(from[i] + (t - from[i]) * e))
    if (k < 1) scoreRaf = requestAnimationFrame(step)
  }
  scoreRaf = requestAnimationFrame(step)
}, { immediate: true })

/** 最新落下的那张弃牌 —— 只有它带「落桌」动效，其余是静态小牌 */
const freshDiscardId = computed(() => lastDiscard.value?.tile?.id ?? -1)

/* ---------- 弃牌物理感（v2.46.19）----------
 * 每张弃牌落桌时带 ±2° 的随机余倾（落在牌对象上，之后一直保持）——
 * 真实麻将牌不会每张都摆得笔直，微小的随机旋转消除「复制粘贴」感。 */
function discardTilt(t) { return `${t._tilt || 0}deg` }

const canZimo = computed(() => {
  if (isOnline.value) {
    if (props.acting) return false
    return (props.onlineView?.me?.options || []).includes('hu')
  }
  if (!canDiscard.value) return false
  return M.canHu(poolOfView.value, melds.value[turn.value].length)
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

/** 听牌提示：打哪张、听哪些（一向听）。仅在自己可出牌（11/14 张）时计算 */
const tingInfo = computed(() => {
  if (phase.value !== 'playing') return []
  if (!canDiscard.value) return []
  const seat = viewSeat.value
  const h = drawn.value ? hands.value[seat].concat([drawn.value]) : hands.value[seat]
  if (h.length % 3 !== 2) return []
  const res = []
  const seen = new Set()
  for (const t of h) {
    const k = `${t.suit}${t.rank}`
    if (seen.has(k)) continue
    seen.add(k)
    const rest = h.filter(x => x.id !== t.id)
    const waits = M.tingTiles(rest, melds.value[seat].length)
    if (waits.length) res.push({ tile: t, waits })
  }
  return res
})
/** 真听牌（v2.46.24 修复，夜星：「已经听牌，还是展示未听牌」）：
 *  旧版把「打一张可听」（一向听）当听牌标，而等牌状态（10/13 张）下真正已经
 *  听牌的手反而显示「尚未听牌」。现在：等牌状态下直接验当前手牌有无听张。 */
const waitingTing = computed(() => {
  if (phase.value !== 'playing') return []
  if (canDiscard.value) return []   // 轮到自己出牌时不存在「等牌」
  const seat = viewSeat.value
  const h = hands.value[seat] || []
  if (h.length % 3 !== 1) return []
  return M.tingTiles(h, melds.value[seat].length)
})
const isTing = computed(() => waitingTing.value.length > 0)
/** 各家听牌标识（v2.46.24，夜星：展示哪家听牌了）：在线读服务端 players[].ting，
 *  本地全知视角现算（等牌直接验；轮到出牌的算「打一张能听」） */
const tingFlags = computed(() => {
  const flags = [false, false, false, false]
  if (phase.value !== 'playing') return flags
  if (isOnline.value) {
    for (const p of props.onlineView?.players || []) flags[p.seat] = !!p.ting
    return flags
  }
  for (let s = 0; s < 4; s++) {
    if (out.value[s]) continue
    const h = (turn.value === s && drawn.value) ? hands.value[s].concat([drawn.value]) : hands.value[s]
    const mc = melds.value[s].length
    if (h.length % 3 === 1) {
      flags[s] = M.tingTiles(h, mc).length > 0
    } else {
      const seen = new Set()
      for (const t of h) {
        const k = `${t.suit}${t.rank}`
        if (seen.has(k)) continue
        seen.add(k)
        if (M.tingTiles(h.filter(x => x.id !== t.id), mc).length) { flags[s] = true; break }
      }
    }
  }
  return flags
})
/** 点听牌项 → 直接选中那张待打的牌（配合金色描边一眼确认） */
function selectTing(info) {
  if (!info?.tile) return
  selId.value = info.tile.id
  sfx.pick()
}

/* ---------- 胡牌动画浮层（V24617-011）---------- */
const huWinner = computed(() => {
  if (!result.value || !result.value.hus?.length) return null
  return result.value.hus[0]
})
const showHuShow = computed(() => phase.value === 'settled' && huShow.value && !!huWinner.value)

/* ---------- 整场制（v2.46.22）：结算卡的四人汇总 / 我方累计 / 整场冠军 ---------- */
const matchSummary = computed(() => {
  const md = result.value?.matchDeltas
  if (!md) return null
  const ms = result.value?.matchScores || {}
  const target = result.value?.matchTarget || 100
  return [0, 1, 2, 3].map((s) => ({
    seat: s,
    delta: Number(md[String(s)] || 0),
    total: Number(ms[String(s)] || 0),
    target,
  }))
})
const myMatchDelta = computed(() =>
  Number(result.value?.matchDeltas?.[String(oSeat.value)] || 0))
const matchChampion = computed(() => {
  const list = matchSummary.value
  if (!list?.length) return null
  const top = list.slice().sort((a, b) => b.delta - a.delta)[0]
  return top.delta > 0 ? top.seat : null
})

/* ---------- 小工具 ---------- */
/** 花色键（m/s/p/z）→ 牌面组件的花纹名 */
function faceSuit(t) {
  if (!t) return 'wan'
  return t.suit === 'm' ? 'wan' : t.suit === 's' ? 'tiao' : t.suit === 'z' ? 'zi' : 'tong'
}
function suitCls(t) {
  if (!t) return ''
  return t.suit === 'm' ? 'is-wan' : t.suit === 's' ? 'is-tiao' : t.suit === 'z' ? 'is-zi' : 'is-tong'
}
function tileText(t) {
  if (!t) return ''
  // 字牌显示 红中/发财/白板，数字牌显示 3万 / 7条 这种
  return t.suit === 'z' ? (M.HONOR_NAME[t.rank] || `${t.rank}字`) : `${t.rank}${M.SUIT_NAME[t.suit]}`
}
function meldTiles(md) {
  if (md.type === 'chi') {
    // v2.46.43：吃副露按点数升序展示 —— 旧版 [手里两张, 吃进那张] 原样拼，
    // 会出现「四萬六萬伍萬」这种乱序（吃进的那张永远排最后）
    return [...(md.combo || []), md.tile]
      .sort((a, b) => M.idxOf(a.suit, a.rank) - M.idxOf(b.suit, b.rank))
  }
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
  const acting = isTurn(s) && !out.value[s]
  return {
    'is-active': acting,
    'is-out': out.value[s],
    // 行动方聚焦（v2.46.19）：别人行动时其余席位压暗降饱和
    'is-idle': phase.value === 'playing' && turn.value >= 0 && !acting && !out.value[s],
  }
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
const PHASE_MAP = { playing: 'playing', finished: 'settled' }
function syncFromView(v) {
  if (!v) return
  const prevPhase = phase.value   // v2.46.26：胡牌语音用（转 finished 瞬间才喊）
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
  // v2.46.26：在线吃碰杠语音/音效 —— 服务端 claim 结算后只更新 melds 投影没有事件，
  // 盯 melds 数量 diff 播报（进房首帧只记基线不补播；自己 4s 内点过的 kind 跳过）
  const KIND_SPK = { pong: '碰', kong: '杠', ankong: '杠', bugang: '杠', chi: '吃' }
  for (let s = 0; s < 4; s++) {
    const cur = v.players?.[s]?.melds || []
    const prevLen = meldsPrevLen[s]
    meldsPrevLen[s] = cur.length
    if (prevLen === null || cur.length <= prevLen) continue
    const md = cur[cur.length - 1]
    const kind = md?.type
    const say = KIND_SPK[kind]
    if (!say) continue
    const act = MELD_ACT[kind]
    if (selfClaimSig.startsWith(`${act}:`) && Date.now() - Number(selfClaimSig.split(':')[1] || 0) < 4000) {
      continue   // 自己刚喊过，别复读
    }
    sfx[act === 'kong' ? 'kong' : 'pong'](panOf(s, povSeat.value))
    showClaimFx(say)
    speak(say, s)
  }
  out.value = [0, 1, 2, 3].map(s => !!v.players?.[s]?.hu)
  turn.value = (v.turn === null || v.turn === undefined) ? -1 : v.turn
  drawn.value = drawnTile
  lastDiscard.value = v.last_discard || null
  wall.value = new Array(v.wall_left || 0)
  phase.value = PHASE_MAP[v.phase] || 'playing'
  roundNo.value = v.round_no || 1
  dealer.value = v.dealer ?? 0
  // 开牌仪式已移除（v2.46.46），但骰子/开门信息保留给牌墙渲染
  dice.value = v.dice || null
  openRel.value = (v.open_rel === undefined || v.open_rel === null) ? -1 : v.open_rel
  openIdx.value = v.open_idx || 0
  logs.value = v.logs || []
  const cl = v.claim
  pending.value = (cl && cl.seat === oSeat.value)
    ? { seat: cl.seat, from: cl.from, tile: cl.tile, kinds: (cl.options || []).slice() }
    : null
  const huInfo = v.result?.hu_info || {}
  const hus = (v.result?.hu || []).map(s => {
    const hi = huInfo[String(s)] || {}
    return { seat: s, fan: hi.fan || 0, names: hi.names || [], zimo: !!hi.zimo, from: hi.from, hand: hi.hand || [] }
  })
  huResults.value = hus
  // v2.46.26：在线胡牌语音 —— 服务端 result 投影没有事件，phase 转 finished 且有人胡时
  // 喊一声（自摸报「自摸」）；自己刚点的胡（onReact 已即时喊）4 秒内不重复。
  if (hus.length && prevPhase !== 'finished' && phase.value === 'finished') {
    if (!(selfClaimSig.startsWith('hu:') && Date.now() - Number(selfClaimSig.split(':')[1] || 0) < 4000)) {
      speak(hus[0].zimo ? '自摸' : '胡', hus[0].seat)
    }
  }
  if (v.result) {
    const delta = Number((v.result.deltas || {})[String(oSeat.value)] || 0)
    result.value = {
      reason: hus.length ? 'hu' : 'liuju',
      hus,
      delta,
      title: !hus.length ? '流局' : delta > 0 ? '本局小赚' : delta < 0 ? '本局小亏' : '本局平局',
      // 整场制字段（v2.46.22）：先到 100 分整场结束才结算豆子
      matchScores: v.result.match_scores || null,
      matchDeltas: v.result.match_deltas || null,
      matchTarget: Number(v.result.match_target || 100),
      matchOver: !!v.result.match_over,
    }
    // 胡牌动画：结算先看 14 张牌，点击任意处才露出结算卡（V24617-011）
    huShow.value = hus.length > 0
  } else {
    result.value = null
    huShow.value = false
  }
  const ids = new Set(hand.map(t => t.id).concat(drawnTile ? [drawnTile.id] : []))
  if (selId.value !== null && !ids.has(selId.value)) selId.value = null
}
watch(() => props.onlineView, (v) => { if (isOnline.value) syncFromView(v) }, { immediate: true, deep: true })

/* ---------- 在线语音报牌（v2.46.24）：盯 last_discard 变化口播牌面 ----------
 * v2.46.26 补砸桌音效：在线时别人的出牌原本只有语音没声音（本地走 doDiscard 的
 * tileDown），这里补 sfx.tileDown；自己的牌 playTile 已即时响过，不重复。 */
let lastSpokenKey = ''
/** 自己刚点过的吃碰杠胡（onReact 记录），服务端 diff 4 秒内同 kind 不重复播 */
let selfClaimSig = ''
/** 在线 melds diff 用的上一帧长度基线（null = 进房首帧，只记不播） */
const meldsPrevLen = [null, null, null, null]
/** meld.type → onReact 的 act kind（selfClaimSig 去重用） */
const MELD_ACT = { pong: 'pong', chi: 'chi', kong: 'kong', ankong: 'kong', bugang: 'kong' }
watch(lastDiscard, (nd, od) => {
  if (!isOnline.value || !nd?.tile) return
  const key = `${nd.seat}:${nd.tile.id}:${discards.value[nd.seat]?.length || 0}`
  if (od === undefined) { lastSpokenKey = key; return }   // 进房首次同步不补播旧牌
  if (key === lastSpokenKey) return
  lastSpokenKey = key
  if (phase.value !== 'playing') return
  if (nd.seat !== viewSeat.value) sfx.tileDown(panOf(nd.seat, povSeat.value))
  speak(tileSpeech(nd.tile), nd.seat)
})

/* ---------- 开局发牌动效（v2.46.24，夜星：一进来就展示全部怪怪的）：
 *  手牌从无到有（或跨局重发）时给每张牌一个自上而下落位的错峰动画 ---------- */
const dealing = ref(false)
let dealTimer = null
function playDealFx() {
  dealing.value = false
  requestAnimationFrame(() => {
    dealing.value = true
    clearTimeout(dealTimer)
    dealTimer = setTimeout(() => { dealing.value = false }, 1500)
  })
}
watch(() => viewHand.value.length, (n, o) => {
  if (n >= 12 && (o ?? 0) < 12) playDealFx()
})

/* ---------- 在线：动作上抛 ---------- */
function actOnline(action) { emit('act', action) }

/* ---------- 开局 ---------- */
function newRound() {
  if (isOnline.value) return   // 在线由服务端发牌，前端不本地开新局
  const deck = M.shuffle(M.buildDeck())
  // 开牌仪式（v2.46.42）：庄家掷两骰 → 总和定开门边、小点数定墩位 →
  // 三轮流牌（每家一次两墩 4 张）→ 庄家跳牌 14 张起手。发牌顺序 = 摸墙
  // 消耗序（与后端 _deal_ritual 镜像）；骰子/开门信息供牌墙渲染与仪式动画。
  const dealerSeat = roundNo.value === 1 ? 0 : (lastWinnerSeat.value ?? 0)
  const d1 = 1 + Math.floor(Math.random() * 6)
  const d2 = 1 + Math.floor(Math.random() * 6)
  const deal = M.dealOpening(deck, dealerSeat, d1, d2)
  wall.value = [...deal.wall].reverse()   // 存反序：drawFor 的 pop() 取摸墙序队头
  hands.value = deal.hands.map(M.sortHand)
  dice.value = [d1, d2]
  openRel.value = deal.openRel
  openIdx.value = deal.openIdx
  melds.value = [[], [], [], []]
  discards.value = [[], [], [], []]
  out.value = [false, false, false, false]
  huResults.value = []
  result.value = null
  pending.value = null
  reactQueue.value = []
  reactFrom.value = null
  huDeclined.value = []
  drawn.value = null
  lastDiscard.value = null
  selId.value = null
  logs.value = []
  huShow.value = false
  phase.value = 'playing'
  // 庄家轮换（V24617-014，本地同规则）：上一局胡牌者坐庄先出；首局 0 号位
  dealer.value = dealerSeat
  turn.value = dealerSeat
  drawn.value = deal.lastDraw          // 庄家跳牌第 14 张，亮为「刚摸」，直接打牌开局
  selId.value = null
  sfx.deal()
  if (!isHuman(dealerSeat)) scheduleAI()
}

function nextRound() {
  if (isOnline.value) { emit('rematch'); return }
  roundNo.value++
  newRound()
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

/** 胡牌即结束：**任一家**胡牌（自摸 / 点炮）本局立刻收摊，不再血战继续。
 *  v2.46.10 之前这里是 `>= 3`（血战到底：打到三家胡或牌墙摸完），一局时间太长、
 *  且真人在手机上常常「胡完还得陪三家打完」。 */
function checkRoundEnd() {
  if (out.value.some(Boolean)) { endRound('hu'); return true }
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
  tile._tilt = +(Math.random() * 4 - 2).toFixed(2)   // 落桌余倾 ±2°
  log(`${seatName(seat)} 打出 ${tileText(tile)}`)
  sfx.tileDown(panOf(seat, povSeat.value))   // v2.46.26：麻将砸桌声（原「干脆一击」偏电子味）
  speak(tileSpeech(tile), seat)   // 语音报牌（v2.46.24）：口播实际打出的牌面；v2.46.28 一人一声
  huDeclined.value = []          // 每张新弃牌的「不胡」名单重新开始
  resolveReactions(seat, tile)
}

/* ---------- 反应（胡 / 杠 / 碰） ---------- */
function resolveReactions(from, tile) {
  if (phase.value !== 'playing') return
  // 1) 胡（点炮）：胡牌即结束 —— 从放炮者**下家起逆时针**找第一家能胡的，只此一家。
  //    旧版把「所有能胡的 AI」都判胡（血战的一炮多响），现在扫到第一个就结束本局。
  for (let off = 1; off <= 3; off++) {
    const s = (from + off) % 4
    if (out.value[s] || huDeclined.value.includes(s)) continue
    if (!M.canHu(hands.value[s].concat([tile]), melds.value[s].length)) continue
    if (isHuman(s)) { pending.value = { seat: s, from, tile, kinds: ['hu'] }; return }
    doHu(s, tile, from, false)
    checkRoundEnd()
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
  nextDraw(rf.from)
}

function takeFromDiscard(from) {
  const pile = discards.value[from]
  if (pile.length) pile.pop()
}

/* ---------- 碰/杠大字（v2.46.20）：碰/杠/暗杠/补杠时中央金底大字 pop 一闪（雀魂式演出） ---------- */
const claimFx = ref(null)
let claimFxTimer = null
function showClaimFx(t) {
  claimFx.value = t
  clearTimeout(claimFxTimer)
  claimFxTimer = setTimeout(() => { claimFx.value = null }, 1000)
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
  sfx.pong(panOf(seat, povSeat.value))
  showClaimFx('碰')
  speak('碰', seat)   // v2.46.26：吃碰杠胡语音（夜星），本地与 AI 同走这里
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
  sfx.kong(panOf(seat, povSeat.value))
  showClaimFx('杠')
  speak('杠', seat)
  turn.value = seat
  drawReplacement(seat)
}

/** 吃（v2.46.24）：上家弃牌 + 手里两张连张成顺子。组合由 chiCombos 给出，
 *  本地模式取第一组；在线模式服务端同样取第一组。 */
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
  log(`${seatName(seat)} 吃 ${tileText(tile)}`)
  sfx.pong(panOf(seat, povSeat.value))
  showClaimFx('吃')
  speak('吃', seat)
  if (isHuman(seat)) return
  scheduleAI()
}

function doAnkong(tileInfo) {
  if (isOnline.value) {
    sfx.kong()
    showClaimFx('暗杠')
    selfClaimSig = `kong:${Date.now()}`
    speak('杠', viewSeat.value)
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
  showClaimFx('暗杠')
  speak('杠')
  drawReplacement(seat)
}

function doBugang(tileInfo) {
  if (isOnline.value) {
    sfx.kong()
    showClaimFx('补杠')
    selfClaimSig = `kong:${Date.now()}`
    speak('杠', viewSeat.value)
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
  showClaimFx('补杠')
  speak('杠')
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
  // hand：胡牌动画浮层要展示赢家全部牌（V24617-011）
  huResults.value.push({ seat, fan: sc.fan, names: sc.names, zimo, from, hand: winning.slice() })
  log(`${seatName(seat)} ${zimo ? '自摸' : '胡'} ${sc.names.join('·')} ${sc.fan}番`)
  sfx.win(panOf(seat, povSeat.value))
  speak(zimo ? '自摸' : '胡', seat)   // v2.46.26：胡牌喊一声（自摸报「自摸」更带感）
  toastMsg(`${seatName(seat)} ${zimo ? '自摸' : '胡牌'}！${sc.names.join(' · ')} ${sc.fan} 番`)
}

function doZimo() {
  if (!canZimo.value) return
  if (isOnline.value) {
    sfx.win()
    selfClaimSig = `hu:${Date.now()}`
    speak('自摸', viewSeat.value)
    actOnline({ type: 'hu' })
    return
  }
  const seat = turn.value
  doHu(seat, null, null, true)
  if (checkRoundEnd()) return
  nextDraw(seat)
}

/* ---------- 人类操作 ---------- */
let suppressClick = false        // 上滑出牌后抑制一次补发的 click（否则会把刚打出的牌又选中）
function pick(t) {
  if (!canDiscard.value || suppressClick) return
  selId.value = selId.value === t.id ? null : t.id
  sfx.pick()
}
/** 直接打出某张牌（点「出牌」按钮与上滑手势共用这一条路径） */
function playTile(t) {
  if (!canDiscard.value || !t) return
  selId.value = t.id
  if (isOnline.value) { sfx.tileDown(); actOnline({ type: 'discard', tile_id: t.id }); return }
  doDiscard(turn.value, t)
}
function discardSel() {
  if (!canDiscard.value || selId.value === null) return
  playTile(poolOfView.value.find(x => x.id === selId.value))
}

/* ---------- 手机手势：手牌上滑 = 直接打出 ----------
 * 旧版手机上必须先点牌选中、再点下方「出牌」按钮（两步，且按钮与手牌离得远）。
 * 现在按下滑到阈值（手机麻将的通用手势）：抬起即出，回到一点一击的老路径也没变。 */
const SWIPE_UP = 30      // 判定「上滑出牌」的位移（px）
const LIFT_AT = 14       // 超过这个位移就先给「抬起」反馈，让玩家知道松手就出
const liftId = ref(null)
const handRef = ref(null)
let gStart = null
function onHandDown(e) {
  if (!canDiscard.value) return
  if (e.pointerType === 'mouse' && e.button !== 0) return
  const el = e.target?.closest ? e.target.closest('.gt-tile') : null
  if (!el) return
  const tid = Number(el.dataset.tid)
  const tile = poolOfView.value.find(x => x.id === tid)
  if (!tile) return
  // 手牌可能被整块 rotate(90deg)（竖屏兜底）：那时手牌的长边是纵向，
  // 「上滑」会和「沿牌排列方向滑动」撞车，故只在手牌横排时启用这个手势。
  const hr = handRef.value ? handRef.value.getBoundingClientRect() : null
  gStart = {
    pid: e.pointerId, x: e.clientX, y: e.clientY, tile,
    horizontal: !hr || hr.width >= hr.height,
  }
  liftId.value = null
  window.addEventListener('pointermove', onHandMove)
  window.addEventListener('pointerup', onHandUp)
  window.addEventListener('pointercancel', onHandUp)
}
function onHandMove(e) {
  if (!gStart || e.pointerId !== gStart.pid) return
  if (!gStart.horizontal) return
  const dy = e.clientY - gStart.y
  const dx = e.clientX - gStart.x
  // 只认「明显向上」的位移：横向划动 / 向下拖不误触发抬起
  liftId.value = (dy <= -LIFT_AT && Math.abs(dy) > Math.abs(dx)) ? gStart.tile.id : null
}
function onHandUp(e) {
  if (!gStart) return
  if (e && e.pointerId !== undefined && e.pointerId !== gStart.pid) return
  const dy = (e && e.clientY != null ? e.clientY : gStart.y) - gStart.y
  const dx = (e && e.clientX != null ? e.clientX : gStart.x) - gStart.x
  const tile = gStart.tile
  const horizontal = gStart.horizontal
  const fired = horizontal && !!(e && e.type !== 'pointercancel')
    && dy <= -SWIPE_UP && Math.abs(dy) > Math.abs(dx) * 0.9
  gStart = null
  liftId.value = null
  window.removeEventListener('pointermove', onHandMove)
  window.removeEventListener('pointerup', onHandUp)
  window.removeEventListener('pointercancel', onHandUp)
  if (fired && canDiscard.value) {
    suppressClick = true
    setTimeout(() => { suppressClick = false }, 320)
    playTile(tile)
  }
}
function doHint() {
  if (!canDiscard.value) return
  if (tingInfo.value.length) {
    const first = tingInfo.value[0]
    selId.value = first.tile.id
    toastMsg(`打 ${tileText(first.tile)} 可听 ${first.waits.map(tileText).join(' / ')}`)
  } else {
    const d = M.aiDiscard(poolOfView.value, melds.value[turn.value].length, { level: 'normal' })
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
    else if (kind === 'chi') sfx.pong()
    // v2.46.26：自己点碰/杠/吃/胡立即喊一声（腾讯棋牌式即时反馈）；
    // melds diff 4 秒内同 kind 不重复播（selfClaimSig 去重）
    if (kind !== 'pass') {
      selfClaimSig = `${kind}:${Date.now()}`
      speak(REACT_NAME[kind] === '胡' ? '胡' : REACT_NAME[kind], p.seat)
    }
    actOnline({ type: kind })
    return
  }
  if (kind === 'pass') {
    const p = pending.value
    pending.value = null
    // 点炮胡被放弃：记下这家后继续往后找（胡牌即结束，一炮只取一家，但不该被放弃者卡死）
    if (p && p.kinds.length === 1 && p.kinds[0] === 'hu') {
      huDeclined.value.push(p.seat)
      resolveReactions(p.from, p.tile)
      return
    }
    reactQueue.value.shift()
    stepReactions()
    return
  }
  if (kind === 'hu') {
    pending.value = null
    doHu(p.seat, p.tile, p.from, false)
    checkRoundEnd()
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
    return
  }
  if (kind === 'chi') {
    pending.value = null
    reactQueue.value.shift()
    doChi(p.seat, p.tile, p.from)
  }
}

/* ---------- AI ---------- */
/**
 * 电脑出牌的「思考时间」。
 * 旧值 640ms：三家机器人连着出，牌刚翻过去下一张就来了，真人根本看不清谁打了什么
 * （夜星：「打麻将时的速度很快，控制在 2-3s」）。
 * v2.46.8 再放慢一档：2.2~3.2s —— 上一版 2.0~3.0 在手机横屏上仍旧「看不清出牌动作」，
 * 除本档位下移外，真正让动作可见的是新加的「弃牌落桌」动效（.gt-tile.is-land）。
 * 固定值会让三家像节拍器，随机更接近真人。
 */
const AI_THINK_MIN = 2200
const AI_THINK_MAX = 3200
function aiThink() { return AI_THINK_MIN + Math.floor(Math.random() * (AI_THINK_MAX - AI_THINK_MIN)) }

let aiTimer = null
function scheduleAI() {
  clearTimeout(aiTimer)
  if (isOnline.value) return   // 在线由服务端 AI 推进
  if (phase.value !== 'playing') return
  if (isHuman(turn.value) || out.value[turn.value]) return
  aiTimer = setTimeout(aiTurn, aiThink())
}
function aiTurn() {
  if (isOnline.value) return
  if (phase.value !== 'playing') return
  const s = turn.value
  if (isHuman(s) || out.value[s]) return
  const full = drawn.value ? hands.value[s].concat([drawn.value]) : hands.value[s].slice()
  const mc = melds.value[s].length
  // 自摸
  if (M.canHu(full, mc)) {
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
  // 出牌（v2.46.31 防守：有对手听牌时算危险牌——现物/可见数/中张）
  const oppTing = [0, 1, 2, 3].some(o => o !== s && !out.value[o]
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
  // 本地庄家轮换：本局胡牌者下局坐庄（V24617-014，与在线引擎一致）
  lastWinnerSeat.value = huResults.value.length ? huResults.value[0].seat : null
  // 胡牌动画：先展示赢家 14 张牌，点击任意处才露出结算卡（V24617-011）
  huShow.value = huResults.value.length > 0
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
    summary: huResults.value.length
      ? `第 ${roundNo.value} 局 · ${seatName(huResults.value[0].seat)}胡`
      : `第 ${roundNo.value} 局 · 流局`,
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
  sfx.preload() // v2.46.41 预热采样，消掉第一次打牌的取包延迟
  if (isOnline.value) { syncFromView(props.onlineView); return }
  if (props.resume && restoreLocal()) toastMsg('已接着上一局继续')
  newRound()
})
onBeforeUnmount(() => {
  clearTimeout(aiTimer)
  clearTimeout(toastTimer)
  clearTimeout(claimFxTimer)
  cancelAnimationFrame(scoreRaf)
  // 上滑出牌期间被卸载：window 上的监听必须摘掉，否则残留到下一个页面
  window.removeEventListener('pointermove', onHandMove)
  window.removeEventListener('pointerup', onHandUp)
  window.removeEventListener('pointercancel', onHandUp)
})
</script>

<style scoped>
.mj {
  display: flex; flex-direction: column; gap: 6px;
  /* 全屏一屏只有 360px 高，外框留白与间距每一点都要算：
     旧 10/12 + gap8 → 新 6/8 + gap6，省下的 12px 全给牌桌（见 .mj-table 注释）。 */
  padding: 6px 10px 8px; min-height: 600px;
  /* --gt-h 由 JS 按实际渲染高度写入（上限 760），迷你牌/手牌尺寸都跟着它走，
     这样同一套 CSS 在手机横屏（约 390 高）与桌面大屏都能自动取到合适的牌面大小。
     系数 0.056：手机横屏 --gt-h≈360 → 迷你牌约 20px 宽（旧值 0.046 只有 16.6px，
     弃牌小到看不清牌面）。 */
  --mini-w: clamp(17px, calc(var(--gt-h, 420px) * 0.056), 28px);
  --mini-h: calc(var(--mini-w) * 1.38);
  /* 弃牌专用尺寸（V24613-003 → v2.46.24 放大一档，夜星：中央牌桌牌少看着空）：
     0.047 → 0.056、上限 23 → 27px，与副露 mini 同档 */
  --dis-w: clamp(15px, calc(var(--gt-h, 420px) * 0.056), 27px);
  --dis-h: calc(var(--dis-w) * 1.38);
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

/* ===== 牌桌：深色框架 + 绒布桌面 + 四方围成矩形 =====
   v2.46.45（夜星：对照腾讯棋牌「有层次框架」）：旧版整块就是一滩绿，
   与桌外背景齐平 —— 真实牌桌（腾讯同款）是「深色桌沿框架包住绒布」两层结构。
   用硬边 spread box-shadow 画外框（不占布局、圆角自动跟随）：
   内圈 9px 深墨绿框架 → 1px 鎏金包线 → 2px 近黑外缘 → 大落影离地。 */
.mj-table {
  flex: 1; min-height: 0;
  display: grid; gap: 6px;
  /* 上（对家）独占一行；左右两家与中央同占中行 —— 四家 + 中央正好围成一个矩形 */
  grid-template-columns: auto minmax(0, 1fr) auto;
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas: "top top top" "left center right";
  padding: 10px 12px; border-radius: 20px;
  /* 绒布：三层 —— 顶部受光 / 中心一圈微亮 / 极淡 45° 交叉布纹（腾讯桌布的哑光纹理），
     外缘压暗与框架衔接 */
  background:
    repeating-linear-gradient(45deg, rgba(255, 255, 255, .016) 0 2px, transparent 2px 5px),
    repeating-linear-gradient(-45deg, rgba(0, 0, 0, .02) 0 2px, transparent 2px 5px),
    radial-gradient(120% 100% at 50% 0%, rgba(255, 255, 255, .09), transparent 55%),
    radial-gradient(100% 80% at 50% 50%, #24785a 0%, #186045 48%, #0c3a2b 100%);
  box-shadow:
    0 0 0 9px #14352b,
    0 0 0 10px rgba(222, 186, 106, .28),
    0 0 0 12px #0a1d17,
    0 30px 54px -20px rgba(0, 0, 0, .85),
    inset 0 0 0 1px rgba(255, 255, 255, .07),
    inset 0 0 60px -10px rgba(0, 0, 0, .6);
}
.mj-seat { display: flex; flex-direction: column; gap: 4px; min-width: 0; min-height: 0;
  /* V24617-012：左右家 3 组副露后内容溢出本格、盖住上下两家的副露/弃牌 ——
     溢出一律裁在本席位内，绝不允许越界遮别人。 */
  overflow: hidden; }
/* 对家：座位牌 + 副露 + 手牌背面**并排一行**。
   旧版是竖排三行，一个「对家」就吃掉桌高的一半（实测 77px／桌高 131px），
   中央弃牌只剩 28px 高 —— 这就是「出牌区间缩小了好多」。
   并排后还要再压：`.gt-seat` 全局是「34px 头像 + 7px 上下 padding + 边框」= 50px 高，
   在一屏 360px 的横屏里太奢侈 → 这里把对家的座位牌压到 34px 左右。 */
.mj-seat-top { grid-area: top; flex-direction: row; align-items: center; justify-content: center; gap: 8px; }
/* V24613-001：座位卡只留「头像 + 名字 + 徽标」——「X 张 · 副露 N」子行删掉，
   张数牌背已经摆着、副露有自己的牌面（自家副露也在手牌左侧摆出来了），
   纯文字重复一遍只是白占宽度。头像/内边距同步再收一档。 */
.mj-seat-top .gt-seat { max-width: 150px; flex: none; padding: 1px 8px 1px 2px; gap: 6px; }
.mj-seat-top .gt-seat-av { width: 24px; height: 24px; font-size: 12px; }
.mj-seat-top .gt-seat-name { font-size: 11.5px; max-width: 88px; }
.mj-seat-top .mj-melds, .mj-seat-top .mj-backs { flex: 0 1 auto; }
.mj-seat-left { grid-area: left; align-items: flex-start; }
.mj-seat-right { grid-area: right; align-items: flex-end; }

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
.mj-melds.is-v { flex: 0 1 52%; max-height: 58%; }
.mj-backs.is-v { flex: 1 1 auto; }
/* 竖排的牌：宽度固定、高度按列等分 —— 牌背是纯色块，压扁不影响辨识；
   有牌面的副露靠 SVG 的 preserveAspectRatio 保比例，同样只会变小不会变形。 */
.mj-backs.is-v .gt-tile { flex: 1 1 0; height: auto; min-height: 5px; max-height: var(--mini-h); }
.mj-melds.is-v .gt-tile { flex: 1 1 0; height: auto; min-height: 7px; max-height: var(--mini-h); }

/* 中央：四方弃牌围成一圈（上=对家 / 下=自己 / 左=左家 / 右=右家）。
   行高分配改成 `auto / 1fr / auto`：上下两条横排只吃一张牌的高度，
   省下的全部给中间那条 —— 左右两家的**竖排**弃牌块需要这份高度（旧版三等分后每条只有 26px）。
   ⚠️ 旧版这里有个隐蔽 bug：`.mj-dis` 用 `grid-template-columns: repeat(auto-fill, var(--mini-w))`
   —— 17 条轨道把整行宽度**全部占满**，于是 `justify-content: center` 完全失效（没有空位可居中），
   四家的牌一律从容器**左边缘**开始铺 → 上下两家与左家的弃牌全叠在中央同一条竖列上，
   看着就是「一堆牌乱堆在中间，不是摆在自己那边」。现在改 flex：内容宽度由牌数决定，
   居中 / 贴边才真正生效。 */
.mj-center {
  grid-area: center; position: relative; min-width: 0; min-height: 0;
  display: grid; gap: 2px 6px;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  /* v2.46.44（夜星：弃牌会拉伸牌桌）：上下两条横排**定高一行**（牌多溢出裁切），
     中行保底「两张侧牌的高度」（左右弃牌纵向码列至少两行）。⚠️ 不能用
     minmax(min, max) 给弃牌行 —— grid 的 maximize-tracks 会把轨道撑到 max、
     把中间 1fr 挤成 0（实测 Chrome 如此），定高才是硬约束。 */
  grid-template-rows:
    calc(var(--dis-h) + 2px)
    minmax(calc(var(--dis-w) * 2 + 4px), 1fr)
    calc(var(--dis-h) + 2px);
  grid-template-areas:
    "up    up"
    "left  right"
    "down  down";
  padding: 18px 28px; border-radius: 14px;   /* v2.46.44：给四方牌墙留边（原 24px，匀 12px 给中行） */
  /* v2.46.46（夜星：还是没有四方桌感）：中央不再是一块「嵌进去的深色面板」——
   * 面板底色与内边线全撤，弃牌直接摆在绒布上，整张桌子就是一块完整的绿绒布；
   * 只保留一圈极淡的内阴影提示「桌面中央」的深度。 */
  background: transparent;
  box-shadow: inset 0 0 44px -8px rgba(0, 0, 0, .28);
  /* v2.46.26（夜星：长方形看着怪）：宽屏下中央弃牌区被 1fr 拉成 3:1 长条，
   * 与真实牌桌「中央近方」的观感差很远。限宽居中后，两侧留出的绿绒布就是
   * 桌面空地，四方弃牌围合成近方阵 —— 这才是麻将桌该有的样子。 */
  width: 100%; max-width: min(100%, 640px);
  justify-self: center;
}
/* 桌心装饰（v2.46.26 / v2.46.46 水印化）：夜星反馈大罗盘太抢戏、中央像「挖了个洞」。
 * 收缩成腾讯中央 logo 那样的水印 —— 半径收一档、金环减淡、凹面撤掉，
 * 像印在绒布上的暗纹而不是嵌进去的罗盘。纯装饰不挡交互 */
.mj-center::before {
  content: ''; position: absolute; left: 50%; top: 50%; z-index: 0;
  width: clamp(64px, 19%, 110px); aspect-ratio: 1;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px solid rgba(222, 186, 106, .26);
  outline: 1px solid rgba(222, 186, 106, .10); outline-offset: 4px;
  background: radial-gradient(circle, rgba(222, 186, 106, .05), transparent 70%);
  box-shadow: 0 0 20px rgba(222, 186, 106, .04);
  pointer-events: none;
}
/* 桌心水印中心：一枚小金点 */
.mj-center::after {
  content: ''; position: absolute; left: 50%; top: 50%; z-index: 0;
  width: 6px; aspect-ratio: 1;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #e8cf92, #b8904a 70%);
  opacity: .75;
  box-shadow: 0 0 8px rgba(222, 186, 106, .3);
  pointer-events: none;
}
/* ---- 四方牌墙（v2.46.42）：贴中央区四边，随摸牌缩短；开门墩鎏金 ---- */
.mj-walls { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.mj-wall { position: absolute; display: flex; gap: 1px; }
.mj-wall-up   { top: 5px; left: 50%; transform: translateX(-50%); }
.mj-wall-down { bottom: 5px; left: 50%; transform: translateX(-50%); }
.mj-wall-left  { left: 5px; top: 50%; transform: translateY(-50%); flex-direction: column; }
.mj-wall-right { right: 5px; top: 50%; transform: translateY(-50%); flex-direction: column; }
.mj-wstack {
  width: 10px; height: 14px; border-radius: 2px;
  /* v2.46.45（夜星：牌墙要有立体感）：立着的牌从玩家视角 = 上半「象牙白顶面」+
   * 下半「翡翠绿背面」，分界线一条暗缝 —— 腾讯牌墙同款构造。 */
  background: linear-gradient(180deg, #fbf7ea 0%, #ece4cd 40%, #ddd2b4 43%, #3f9e78 43%, #236a50 100%);
  box-shadow:
    inset 0 0 0 1px rgba(105, 95, 70, .38),
    0 2px 3px -1px rgba(0, 0, 0, .6);
  transition: opacity .3s ease, transform .3s ease, box-shadow .3s ease;
}
.mj-wall-left .mj-wstack, .mj-wall-right .mj-wstack { width: 14px; height: 10px; }
.mj-wstack.is-half { opacity: .5; }
.mj-wstack.is-gone { opacity: 0; transform: scale(.5); }
.mj-wstack.is-open {
  box-shadow:
    inset 0 0 0 1px rgba(105, 95, 70, .38),
    0 0 0 1.5px rgba(233, 200, 119, .95), 0 0 10px rgba(233, 200, 119, .6),
    0 2px 3px -1px rgba(0, 0, 0, .6);
  transform: scale(1.2);
}
@media (max-height: 430px) {
  /* 矮屏（手机横屏）：弃牌再收一档 —— 中行能多让出 ~12px 给左右弃牌的纵向码列 */
  .mj { --dis-w: clamp(14px, calc(var(--gt-h, 420px) * 0.05), 22px); }
  .mj-wstack { width: 9px; height: 11px; }
  .mj-wall-left .mj-wstack, .mj-wall-right .mj-wstack { width: 11px; height: 9px; }
}
/* 碰/杠大字（v2.46.20）：绝对定位盖在弃牌区中央，金底墨字 pop 一闪；
   进出场都在一条 keyframes 里（0.95s），1s 后 v-if 摘除，无需 transition */
.mj-claim-fx {
  position: absolute; left: 50%; top: 50%; z-index: 20;
  margin: 0; transform: translate(-50%, -50%);
  padding: 10px 26px; border-radius: 14px;
  font-size: clamp(26px, 5vw, 46px); font-weight: 900; letter-spacing: .18em; text-indent: .18em;
  color: #2a1d05;
  background: linear-gradient(180deg, #f4dc9c, #d9b65f);
  border: 1px solid rgba(255, 255, 255, .4);
  box-shadow: 0 10px 30px -10px rgba(0, 0, 0, .9), inset 0 1px 0 rgba(255, 255, 255, .6);
  pointer-events: none;
  animation: mj-claim-pop .95s cubic-bezier(.22, 1.4, .36, 1) both;
}
@keyframes mj-claim-pop {
  0% { transform: translate(-50%, -50%) scale(.4); opacity: 0; }
  18% { transform: translate(-50%, -50%) scale(1.12); opacity: 1; }
  30% { transform: translate(-50%, -50%) scale(1); }
  78% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(1.04); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .mj-claim-fx { animation-duration: .01s; opacity: 0; }
}
/* 弃牌：flex + wrap，牌宽恒定（不随牌数抖动），溢出裁切。
   上下两家横排、各自居中 → 牌堆正对自己；
   左右两家：**grid 纵向码列**（v2.46.44，夜星：手机端弃牌为啥是横着的）——
   旧版 `flex-flow: column wrap` 在中行高度不够时会「每列只剩一张」自动拆成横排，
   整条弃牌带横贯全桌（就是手机上那条横躺的牌带）。现在改 grid
   `grid-auto-flow: column` + 固定行高：行数由容器高度算死，列内从上到下、
   满列才向中缝起新列，**任何高度下都不可能摊成横排**。
   左家 justify-content: start（贴外侧左缘，向右长）、右家 end（贴右缘，向左长）。 */
.mj-dis { display: flex; gap: 2px; min-width: 0; min-height: 0; overflow: hidden; }
.mj-dis > .gt-tile { flex: none; transform: rotate(var(--tilt, 0deg)); }
.mj-dis-up { grid-area: up; flex-flow: row wrap; justify-content: center; align-content: flex-start; }
.mj-dis-down { grid-area: down; flex-flow: row wrap; justify-content: center; align-content: flex-end; }
.mj-dis-left, .mj-dis-right {
  display: grid; gap: 2px; align-content: start;
  grid-template-rows: repeat(auto-fill, var(--dis-w));
  grid-auto-columns: var(--dis-h);
  grid-auto-flow: column;
}
.mj-dis-left { grid-area: left; justify-content: start; }
.mj-dis-right { grid-area: right; justify-content: end; }
/* 左右两家弃牌：牌身横躺 —— 布局盒宽高先互换（长边横向），牌面 SVG 反向转 ±90° 补回来
   （transform 不参与布局，必须换盒子尺寸才能让列内间距正确）。
   旋转方向：牌面朝向桌心 —— 左家牌顶指向右（rotate 90°），右家牌顶指向左（rotate -90°），
   与「打牌时牌顶推向桌心」的真实方位一致。 */
/* 弃牌专用小尺寸（V24613-003）：必须用 .mj 前缀提特异性压过 `.mj .gt-tile.mini`；
   放在左右互换规则**之前**，让横躺规则（同特异性、靠后）赢过它 */
.mj .mj-dis > .gt-tile.mini { width: var(--dis-w); height: var(--dis-h); }
.mj .mj-dis-left > .gt-tile.mini, .mj .mj-dis-right > .gt-tile.mini { width: var(--dis-h); height: var(--dis-w); }
.mj .mj-dis-left > .gt-tile > :deep(svg) {
  right: auto; bottom: auto; left: 50%; top: 50%;
  width: var(--dis-w); height: var(--dis-h);
  transform: translate(-50%, -50%) rotate(90deg);
}
.mj .mj-dis-right > .gt-tile > :deep(svg) {
  right: auto; bottom: auto; left: 50%; top: 50%;
  width: var(--dis-w); height: var(--dis-h);
  transform: translate(-50%, -50%) rotate(-90deg);
}

/* ===== 底部信息条 ===== */
/* 一行到底、不换行：换行会把好不容易让给牌桌的高度又吃回去 */
.mj-handbar { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; overflow: hidden; min-height: 0; }
/* 最近一张舍牌：小牌 + 「谁打出」，替代旧版中央那个大信息盒。
   这张小牌是整条信息条的高度来源（28px），单独收小到 22px —— 一行文字不值得占 28px。
   注意选择器必须写成 `.mj .mj-lastmini .gt-tile.mini`：下面那条 `.mj .gt-tile.mini`
   特异性完全相同，靠后的会赢，只写 `.mj-lastmini .gt-tile.mini` 是不生效的。 */
.mj-lastmini { display: inline-flex; align-items: center; gap: 5px; flex: none; }
.mj .mj-lastmini .gt-tile.mini { width: 16px; height: 22px; }
.mj-lastmini em { font-style: normal; font-size: 11.5px; color: var(--gt-ink-dim); white-space: nowrap; }
.mj-ting-inline { display: inline-flex; align-items: center; gap: 8px; flex: 0 1 auto; overflow: hidden; }
.mj-ting-label { font-style: normal; font-size: 11.5px; font-weight: 700; color: var(--gt-gold); flex: none; }
.mj-ting-item { font-size: 11.5px; color: var(--gt-ink-dim); white-space: nowrap; }
.mj-ting-item b { color: var(--gt-ink); font-weight: 700; }
.mj-ting-none { font-style: normal; font-size: 11.5px; color: var(--gt-ink-dim); white-space: nowrap; }
/* 已听牌（v2.46.24）：鎏金亮字，与「一向听」提示区分 */
.mj-ting-gold { font-style: normal; font-size: 11.5px; color: var(--gt-gold); white-space: nowrap; }
.mj-ting-gold b { color: var(--gt-ink); font-weight: 700; }
/* 席位卡听牌角标：金底更实一点 + 呼吸（v2.46.24） */
.mj .gt-seat-badge.is-ting {
  background: rgba(233, 200, 119, .38);
  animation: mj-ting-breath 2.4s ease-in-out infinite;
}
@keyframes mj-ting-breath { 0%, 100% { opacity: 1; } 50% { opacity: .55; } }
@media (prefers-reduced-motion: reduce) { .mj .gt-seat-badge.is-ting { animation: none; } }

/* 开局发牌动效（v2.46.24）：手牌自上而下错峰落位，1.5s 后自动解除 */
.mj-hand.is-deal .gt-tile {
  animation: mj-deal-in .46s cubic-bezier(.22, 1.2, .36, 1) both;
  animation-delay: calc(var(--i, 0) * 38ms);
}
@keyframes mj-deal-in {
  from { transform: translateY(-42px) rotate(-5deg); opacity: 0; }
  to { transform: none; opacity: 1; }
}
@media (prefers-reduced-motion: reduce) { .mj-hand.is-deal .gt-tile { animation: none; } }

/* ===== 底部 ===== */
.mj-bottom { display: flex; flex-direction: column; gap: 5px; min-height: 0; }
/* v2.46.14：操作按钮从手牌右侧移到手牌**上方**独立一行（夜星：按钮放麻将上方）。
   手牌 flex:1 铺满整行；牌宽公式的百分比以手牌盒实际宽为基准。
   全屏 1280 逻辑宽下手牌仍由 0.12×屏高的上限封顶，不会被压小。 */
.mj-handrow { display: flex; align-items: flex-end; gap: 8px; min-height: 0; }
/* 自己的碰 / 杠副露（V24613-002）：迷你牌横排，flex:none 不参与手牌均分；
   牌宽用 --mini-w（跟别家副露一致），多了往右推手牌、绝不换行溢出 */
.mj-ownmelds {
  display: flex; gap: 4px; align-items: flex-end;
  flex: 0 1 auto; min-width: 0; overflow: hidden; padding-bottom: 3px;
}
.mj-ownmelds .gt-meld { display: inline-flex; gap: 1px; flex: none; }
/* 手牌铺满可用宽度：牌宽 = min(按屏高算的上限, 按张数均分)。
   系数 0.12（0.14 → 0.12）：手机横屏约 43px 宽 / 60px 高，仍比最早的 40px 大，
   但省出的 12px 全给了上方牌桌 —— 一屏只有 360px 高时，每一像素都要算。
   上留白 11px = 选中上浮(-11px) + 落影，不能小于 11，否则选中的牌会顶到信息条上。 */
.mj-hand {
  flex: 1 1 auto;
  display: flex; gap: 3px; align-items: flex-end; justify-content: center;
  padding: 11px 4px 3px; min-height: 0; flex-wrap: nowrap;
  /* 手牌整块接管纵向手势（上滑出牌）—— 否则浏览器会把纵向位移当成滚页面，
     中途发 pointercancel，手势必断。 */
  touch-action: none;
}
.mj-hand .gt-tile {
  width: min(
    calc(var(--gt-h, 420px) * 0.12),
    calc((100% - (var(--ntiles, 14) - 1) * 3px) / var(--ntiles, 14))
  );
  height: auto; aspect-ratio: 5 / 7;
}
/* 牌面 SVG 铺满整张牌（绝对定位，避免百分比高度在 aspect-ratio 盒子里解析不确定） */
.mj .gt-tile > :deep(svg) { position: absolute; inset: 0; }
.mj-hand-empty { margin: 0 auto; font-size: 12px; color: var(--gt-ink-dim); }
/* 出牌 / 自摸 / 提示（V24614-001）：独立一行贴在手牌上方、**右对齐** ——
   原先挤在手牌右侧，横屏 360px 高时 14+ 张牌把按钮压得很窄。
   全局 .gt-btn 是 8px/18px（39px 高）偏奢侈，这里收成 6px/16px（约 32px），
   独立行的整行高度从牌桌里出 —— 牌面尺寸**不动**，那是玩家最常碰的东西。 */
.mj-actions { justify-content: flex-end; margin-bottom: 1px; }
.mj-actions .gt-btn { padding: 6px 16px; font-size: 12.5px; }

/* ===== 牌：象牙白立体牌身（v2.46.44，夜星：对照腾讯棋牌做质感）=====
   旧版「平面色块 + 单层投影」塑料感的再升级 —— 真实麻将牌的五个视觉特征：
   ① 面是暖象牙白，左上受光、右下微沉（radial 高光 + 纵向渐变叠加）；
   ② 牌身有**厚度**：底缘露出受光的象牙侧面 + 一道侧沿暗缝 + 外圈软落影；
   ③ 面缘一圈极细的暖灰包边（不是黑描边）；
   ④ 牌背是「绿面白边」：翠绿背面 + 象牙白侧面包边，与牌身同构；
   ⑤ 体积感全部来自受光方向一致的阴影层，而不是靠对比度硬堆。 */
.mj .gt-tile {
  background:
    radial-gradient(130% 90% at 28% 0%, rgba(255, 255, 255, .92), rgba(255, 255, 255, 0) 52%),
    linear-gradient(175deg, #fffef9 0%, #f8f3e5 46%, #eae1c9 100%);
  border: 1px solid rgba(184, 170, 136, .78);
  border-radius: 7px 7px 6px 6px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .95),
    inset 0 -2px 3px rgba(152, 136, 98, .30),
    0 2px 0 #e9e0c6,
    0 4px 0 #c8bc9c,
    0 5px 1px rgba(88, 78, 52, .32),
    0 13px 20px -10px rgba(0, 0, 0, .8);
}
/* 牌背：翠绿面 + 象牙白侧沿（腾讯式「白边绿背」，与绒布桌同色系） */
.mj .gt-tile.is-back {
  background: linear-gradient(172deg, #4aa87f 0%, #2c7f60 55%, #1c5d46 100%);
  border-color: #efe8d2;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .32),
    inset 0 -2px 3px rgba(10, 60, 44, .45),
    0 2px 0 #e9e0c6,
    0 4px 0 #c8bc9c,
    0 5px 1px rgba(88, 78, 52, .35),
    0 12px 18px -10px rgba(0, 0, 0, .82);
}
/* 迷你牌（背面 / 弃牌 / 副露）尺寸跟随屏高 */
.mj .gt-tile.mini { width: var(--mini-w); height: var(--mini-h); border-radius: 4px; }
/* 迷你牌的厚度收成两小层 —— 大牌那套三层在小尺寸下会糊 */
.mj .gt-tile.mini {
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .85),
    inset 0 -1px 2px rgba(152, 136, 98, .35),
    0 1px 0 #ddd3b6, 0 2px 0 rgba(150, 138, 108, .55),
    0 4px 6px -3px rgba(0, 0, 0, .62);
}
.mj .gt-tile.mini.is-back {
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .28),
    inset 0 -1px 2px rgba(10, 60, 44, .45),
    0 1px 0 #ddd3b6, 0 2px 0 rgba(150, 138, 108, .55),
    0 4px 6px -3px rgba(0, 0, 0, .68);
}

/* 花色着色（牌面由 SVG 绘制，此处仅作兜底与选中描边色） */
.mj .gt-tile.is-wan { --tile-accent: #b3261e; }
.mj .gt-tile.is-tiao { --tile-accent: #1f6b3a; }
.mj .gt-tile.is-tong { --tile-accent: #1b4f8a; }
.mj .gt-tile.is-zi { --tile-accent: #9a7b1e; }
.mj .gt-tile.is-drawn {
  margin-left: 12px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .95),
    0 0 0 2px var(--gt-gold),
    0 2px 0 #e9e0c6, 0 4px 0 #c8bc9c,
    0 14px 20px -10px rgba(0, 0, 0, .85);
}
/* 手牌选中：抬起来 + 金色描边 */
.mj-hand .gt-tile.is-sel {
  transform: translateY(-11px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .95),
    0 0 0 2px var(--gt-gold), 0 0 18px -2px rgba(233, 200, 119, .7),
    0 2px 0 #e9e0c6, 0 4px 0 #c8bc9c,
    0 16px 22px -10px rgba(0, 0, 0, .9);
}

/* ===== 碰杠提示（V24617-010）=====
   反应窗口里亮出被碰/杠的那张牌；能组成刻子的手牌描金脉冲，一眼看清用哪几张碰。 */
.mj-claimtile { display: inline-flex; align-items: center; gap: 6px; flex: none; }
.mj-claimtile em { font-style: normal; font-size: 11.5px; color: var(--gt-ink-dim); white-space: nowrap; }
@keyframes mj-pulse {
  0%, 100% { box-shadow: 0 0 0 2px var(--gt-gold), 0 0 6px -1px rgba(233, 200, 119, .55); }
  50% { box-shadow: 0 0 0 2px var(--gt-gold), 0 0 18px -1px rgba(233, 200, 119, .95); }
}
.mj-hand .gt-tile.is-claimhit { animation: mj-pulse 1.1s ease-in-out infinite; }
.mj-actions .gt-btn.is-pulse { animation: mj-pulse 1.1s ease-in-out infinite; }

/* ===== 本局积分（V24617-013）：座位卡名字旁的小徽标，赢绿亏红 ===== */
.gt-seat-score {
  flex: none; font-size: 10.5px; font-weight: 700; line-height: 1;
  padding: 2px 5px; border-radius: 8px;
  background: rgba(255, 255, 255, .12); color: var(--gt-ink-dim);
  font-variant-numeric: tabular-nums;
}
.gt-seat-score.is-plus { background: rgba(64, 160, 96, .28); color: #9fe0b8; }
.gt-seat-score.is-minus { background: rgba(190, 70, 60, .26); color: #f0b3aa; }

/* ===== 行动方聚焦（v2.46.19）：行动方呼吸光圈（对齐掼蛋），其余席位压暗降饱和 ===== */
.mj .gt-seat { transition: opacity .3s ease, filter .3s ease; }
.mj .gt-seat.is-idle { opacity: .58; filter: saturate(.55); }
.mj .gt-seat.is-active {
  box-shadow: 0 0 0 2px rgba(199, 169, 107, .55), 0 0 22px rgba(199, 169, 107, .35);
  animation: mj-seat-pulse 1.6s ease-in-out infinite;
}
@keyframes mj-seat-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(199, 169, 107, .5), 0 0 16px rgba(199, 169, 107, .28); }
  50% { box-shadow: 0 0 0 3px rgba(199, 169, 107, .8), 0 0 30px rgba(199, 169, 107, .5); }
}

/* 听牌项改成可点按钮：外观仍是文字胶囊，hover 描金提示可点 */
button.mj-ting-item {
  appearance: none; font-family: inherit; cursor: pointer;
  background: rgba(255, 255, 255, .05); border: 1px solid var(--gt-line);
  border-radius: 999px; padding: 1px 8px;
  font-size: 11.5px; color: var(--gt-ink-dim); white-space: nowrap;
}
button.mj-ting-item:hover { border-color: rgba(233, 200, 119, .5); color: var(--gt-gold); }
.gt-btn.is-off { opacity: .45; }

/* ===== 胡牌动画浮层（V24617-011）=====
   胡牌后先全屏展示赢家 14 张牌：牌逐张从下翻入（每张延迟 60ms），点击任意处关闭。 */
.mj-hushow { cursor: pointer; }
.mj-hushow-card {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 22px 30px; border-radius: 18px;
  background: linear-gradient(168deg, rgba(20, 34, 28, .96), rgba(10, 22, 17, .96));
  box-shadow: inset 0 0 0 1px rgba(233, 200, 119, .4), 0 24px 60px -18px rgba(0, 0, 0, .9);
}
@keyframes mj-hushow-pop {
  0% { transform: translateY(26px) scale(.6) rotate(-8deg); opacity: 0; }
  70% { transform: translateY(-3px) scale(1.05) rotate(1deg); opacity: 1; }
  100% { transform: none; opacity: 1; }
}
.mj-hushow-title {
  margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 2px;
  color: var(--gt-gold); text-shadow: 0 0 22px rgba(233, 200, 119, .55);
  animation: mj-hushow-pop .45s cubic-bezier(.2, .85, .3, 1) both;
}
.mj-hushow-fan { margin: 0; font-size: 14px; color: #e8e2d2; animation: mj-hushow-pop .45s .08s cubic-bezier(.2, .85, .3, 1) both; }
.mj-hushow-hand {
  display: flex; gap: 4px; flex-wrap: nowrap; max-width: 92vw;
  padding: 10px 8px 6px; border-radius: 10px;
  background: rgba(0, 0, 0, .28);
}
.mj-hushow-hand .gt-tile {
  width: 34px; aspect-ratio: 5 / 7; flex: none;
  animation: mj-hushow-pop .4s cubic-bezier(.2, .85, .3, 1) both;
}
.mj-hushow-tip { margin: 2px 0 0; font-size: 11.5px; color: rgba(232, 226, 210, .55); }

/* ===== 结算卡整场制增强（v2.46.22）：胡牌牌面 / 四人汇总 / 我方累计 ===== */
/* 胡牌牌面：结算卡内嵌 14 张 mini 牌，不回翻胡牌浮层也能看 */
.mj-over-hand {
  display: inline-flex; gap: 3px; flex-wrap: wrap; justify-content: center;
  margin-top: 5px; padding: 6px 7px 4px; border-radius: 8px;
  background: rgba(0, 0, 0, .28); vertical-align: top;
}
.mj-over-hand .gt-tile { width: 26px; aspect-ratio: 5 / 7; }
/* 整场累计行内备注 */
.mj-over-matchline { font-style: normal; font-size: 12px; color: var(--gt-ink-dim); }
/* 四人整场汇总：一行四枚胶囊，赢金亏红 */
.mj-over-match {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 6px;
  margin-top: 2px;
}
.mj-over-match span {
  padding: 3px 10px; border-radius: 999px;
  font-size: 12px; font-variant-numeric: tabular-nums;
  background: rgba(255, 255, 255, .06); border: 1px solid var(--gt-line);
  color: var(--gt-ink-dim);
}
.mj-over-match span em { font-style: normal; opacity: .55; font-size: 10.5px; }
.mj-over-match span.is-plus { color: var(--gt-gold); border-color: rgba(233, 200, 119, .4); }
.mj-over-match span.is-minus { color: #e07070; }
@media (prefers-reduced-motion: reduce) {
  .mj-over-hand { transition: none; }
}

@media (prefers-reduced-motion: reduce) {
  .mj-hushow-title, .mj-hushow-fan, .mj-hushow-hand .gt-tile,
  .mj-hand .gt-tile.is-claimhit, .mj-actions .gt-btn.is-pulse,
  .mj .gt-tile.is-drawn-glow, .mj .gt-seat.is-active { animation: none !important; }
  .mj .gt-seat.is-idle { opacity: 1; filter: none; }
}

/* 上滑出牌：手指抬起过阈值时把牌「拎起来」，松手即出（给提前反馈，不用猜） */
.mj-hand .gt-tile.is-lift {
  transform: translateY(-30px) scale(1.04);
  z-index: 4;
  filter: none;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .95),
    0 0 0 2px var(--gt-gold), 0 0 24px -2px rgba(233, 200, 119, .9),
    0 2px 0 #e9e0c6, 0 4px 0 #c8bc9c,
    0 20px 26px -10px rgba(0, 0, 0, .92);
}

/* ===== 出牌动效 =====
   ① 摸到的牌：从右侧滑入手牌（.is-drawn 有 key，每摸一张重新挂载 → 每次都放一次）
   ② 打出的牌：落到弃牌区时「抛下 + 金圈一闪」，这是「看得到出牌动作」的关键。
   旧版弃牌是直接出现在位（无过渡），三家人 2~3s 连打，肉眼根本抓不住。 */
@keyframes mj-draw {
  0% { transform: translate(18px, -14px) scale(1.14); opacity: .2; }
  100% { transform: none; opacity: 1; }
}
/* 摸牌区分（v2.46.19）：入列后金色辉光 1.2s 渐隐 —— 不上浮（会与选中/上滑手势打架），
   用一圈柔光标记「这张是刚摸的」，之后自然融入手牌 */
@keyframes mj-drawn-glow {
  0% { filter: drop-shadow(0 0 9px rgba(233, 200, 119, .95)); }
  100% { filter: drop-shadow(0 0 0 rgba(233, 200, 119, 0)); }
}
.mj .gt-tile.is-drawn {
  animation: mj-draw .3s cubic-bezier(.2, .85, .3, 1) both, mj-drawn-glow 1.2s .25s ease-out both;
}
@keyframes mj-land {
  0% {
    transform: translateY(-20px) scale(1.4) rotate(-10deg); opacity: .25;
    box-shadow: 0 0 0 3px var(--gt-gold), 0 0 16px rgba(233, 200, 119, .8);
  }
  55% {
    transform: translateY(1px) scale(.96) rotate(0deg); opacity: 1;
    box-shadow: 0 0 0 2px var(--gt-gold), 0 0 10px rgba(233, 200, 119, .55);
  }
  100% {
    transform: rotate(var(--tilt, 0deg)); opacity: 1;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, .85),
      inset 0 -1px 2px rgba(152, 136, 98, .35),
      0 1px 0 #ddd3b6, 0 2px 0 rgba(150, 138, 108, .55),
      0 4px 6px -3px rgba(0, 0, 0, .62);
  }
}
.mj .gt-tile.is-land { animation: mj-land .38s cubic-bezier(.2, .85, .3, 1) both; z-index: 2; }

/* 手势提示：小号弱化，跟在操作按钮后面 */
.mj-hint {
  font-style: normal; font-size: 11px; color: var(--gt-ink-dim);
  display: inline-flex; align-items: center; gap: 7px;
  padding-left: 2px;
}
.mj-hint b { font-weight: 600; color: var(--gt-gold); }

@media (prefers-reduced-motion: reduce) {
  .mj .gt-tile.is-drawn, .mj .gt-tile.is-land { animation: none !important; }
}
.gt-over-card em { font-style: normal; opacity: .7; }

@media (max-width: 900px) {
  .mj { min-width: 860px; }
}
</style>

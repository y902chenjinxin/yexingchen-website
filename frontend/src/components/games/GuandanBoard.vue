<template>
  <div class="gt-landscape gd-wrap">
    <div
      ref="rootRef"
      class="gt-shell gd"
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
        <!-- 升级进度条（2 → A）：两支细条一眼看出两队离打过 A 还有多远 -->
        <span class="gd-lvbars" title="升级进度：2 → A">
          <span class="gd-lvbar me"><i :style="{ width: lvPct(myLevel) }"></i></span>
          <span class="gd-lvbar op"><i :style="{ width: lvPct(oppLevel) }"></i></span>
        </span>
        <span class="gt-spacer"></span>
        <button class="gt-btn sm ghost" :title="muted ? '取消静音' : '静音'" @click="toggleMute">
          {{ muted ? '🔇' : '🔊' }}
        </button>
        <button class="gt-btn sm ghost" :class="{ 'is-off': !hapticsOn }" :title="hapticsOn ? '关闭震动反馈' : '开启震动反馈'" @click="toggleHaptics">
          📳
        </button>
        <button class="gt-btn sm ghost" @click="doExit">退出对局</button>
      </header>

      <!-- ===== 牌桌：主区 + 右侧出牌历史竖栏 ===== -->
      <div class="gd-table" :class="{ 'is-shake': tableShake, 'is-freeze': freeze }">
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
              <i>{{ isOnline && props.onlineView?.phase === 'return' ? '还贡' : '出牌' }}</i>
            </span>
            <div class="gt-seat" :class="seatCls(topSeat)">
              <span class="gt-seat-av">{{ seatAvatar(topSeat) }}</span>
              <span class="gt-seat-tx">
                <b class="gt-seat-name">{{ seatName(topSeat) }}</b>
                <i class="gt-seat-sub">{{ seatSub(topSeat) }}</i>
              </span>
              <span v-if="isTurn(topSeat)" class="gt-seat-badge">出牌中</span>
              <transition name="gd-pop">
                <span v-if="baoCount(topSeat)" class="gd-bao-badge">报牌 {{ baoCount(topSeat) }}</span>
              </transition>
              <transition name="gd-pop">
                <span v-if="passBubbles[topSeat]" class="gd-pass-bubble">不要</span>
              </transition>
            </div>
          </div>

          <div class="gd-row gd-row-mid">
            <!-- 左家 -->
            <div class="gt-seat gd-seat-side" :class="seatCls(leftSeat)">
              <span class="gt-seat-av">{{ seatAvatar(leftSeat) }}</span>
              <span class="gt-seat-tx">
                <b class="gt-seat-name">{{ seatName(leftSeat) }}</b>
                <i class="gt-seat-sub">{{ seatSub(leftSeat) }}</i>
              </span>
              <span v-if="isTurn(leftSeat)" class="gt-seat-badge">出牌中</span>
              <transition name="gd-pop">
                <span v-if="baoCount(leftSeat)" class="gd-bao-badge">报牌 {{ baoCount(leftSeat) }}</span>
              </transition>
              <transition name="gd-pop">
                <span v-if="passBubbles[leftSeat]" class="gd-pass-bubble">不要</span>
              </transition>
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
                    v-for="(c, i) in lastPlay.cards"
                    :key="c.id"
                    class="gt-card gd-throw"
                    :class="cardCls(c)"
                    :style="{ '--i': i }"
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

              <!-- 炸弹 / 同花顺 / 火箭：中央金圈炸开 + 大字，见 playFxFor -->
              <div v-if="bombFx" class="gd-bomb-fx" aria-hidden="true">
                <span class="gd-bomb-ring"></span>
                <b>炸弹！</b>
              </div>

              <!-- 牌型名称浮现（v2.46.19）：每手牌打出后中央短暂放大牌型名再淡出，
                   普通牌型墨底金字、炸弹/同花顺/火箭金底 —— 比角落小胶囊更醒目 -->
              <transition name="gd-patfade">
                <div v-if="patFx" class="gd-pat-fx" :class="{ gold: patFx.gold }" aria-hidden="true">
                  <b>{{ patFx.name }}</b>
                </div>
              </transition>
            </div>

            <!-- 右家 -->
            <div class="gt-seat gd-seat-side" :class="seatCls(rightSeat)">
              <span class="gt-seat-av">{{ seatAvatar(rightSeat) }}</span>
              <span class="gt-seat-tx">
                <b class="gt-seat-name">{{ seatName(rightSeat) }}</b>
                <i class="gt-seat-sub">{{ seatSub(rightSeat) }}</i>
              </span>
              <span v-if="isTurn(rightSeat)" class="gt-seat-badge">出牌中</span>
              <transition name="gd-pop">
                <span v-if="baoCount(rightSeat)" class="gd-bao-badge">报牌 {{ baoCount(rightSeat) }}</span>
              </transition>
              <transition name="gd-pop">
                <span v-if="passBubbles[rightSeat]" class="gd-pass-bubble">不要</span>
              </transition>
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

      <!-- ===== 底部：信息条 → 操作 → 手牌 =====
           操作区放在**手牌上方**（夜星：「把操作按钮都放在牌的上方，看着顺眼、也好点击操作，
           也不影响出牌的顺滑」）—— 手牌贴底、按钮在其正上方，视线不必在牌堆下方找按钮。 -->
      <footer class="gd-bottom">
        <div class="gd-bottom-bar">
          <span class="gd-hand-tag">{{ seatName(viewSeat) }} · {{ viewHand.length }} 张</span>
            <transition name="gd-pop">
              <span v-if="baoCount(viewSeat)" class="gd-mini gd-bao-me">报牌 {{ baoCount(viewSeat) }}</span>
            </transition>
            <transition name="gd-pop">
              <span v-if="passBubbles[viewSeat]" class="gd-pass-bubble gd-pass-bubble-me">不要</span>
            </transition>
          <!-- 全屏时顶栏被收起，级牌与比分改由这条承载，保证一直可见；非全屏时隐藏以免与顶栏重复 -->
          <span class="gd-scorebar">
            主级 {{ G.levelText(roundLevel) }} · 我方 {{ G.levelText(myLevel) }} / 对方 {{ G.levelText(oppLevel) }}
          </span>
          <span class="gt-spacer"></span>
          <span v-if="showCountdown" class="gd-mini gd-timer" :class="{ urgent: leftSec <= 60 }">
            ⏳ 贡牌剩余 {{ mmss(leftSec) }}
          </span>
          <span v-if="viewTing.length" class="gd-mini">可出 {{ viewTing.length }}</span>
          <span v-if="canAct" class="gd-mini" :class="{ on: sel.length }">已选 {{ sel.length }}</span>
          <span class="gt-sub gd-status">{{ statusLine }}</span>
        </div>

        <!-- 进贡 / 还贡全局横幅：谁贡给谁（贡了哪张）一目了然。
             机器人之间的进贡在服务端瞬间完成，没有这条横幅就完全隐形，
             用户会以为进贡逻辑不存在（V24616-001）。 -->
        <div v-if="tributePhaseVisible" class="gd-tribute-banner" aria-live="polite">
          <span class="gd-tb-title">{{ tributePhaseLabel }}</span>
          <span v-if="tributeResisted" class="gd-tb-item">
            进贡方合计两张大王（大小王不算）· 抗贡成立，由头游 {{ seatName(tributeLeader) }} 直接出牌
          </span>
          <template v-else>
            <span
              v-for="(g, i) in tributePlan"
              :key="i"
              class="gd-tb-item"
              :class="{ done: !!g.card, mine: g.from === oSeat || g.to === oSeat }"
            >
              {{ seatName(g.from) }} → {{ seatName(g.to) }}
              <i v-if="g.card" class="gd-tb-card" :class="{ red: isRed(g.card) }">{{ cardText(g.card) }}{{ cardSuit(g.card) }}</i>
              <em v-else-if="g.done" class="gd-tb-pending">已还</em>
              <em v-else class="gd-tb-pending">待{{ tributePhaseLabel }}</em>
            </span>
          </template>
        </div>

        <!-- 操作区：次要工具（提示/重选/同花顺/顺子）收成小号弱按钮，主力只留「不要 / 出牌」两个大按钮 -->
        <div class="gt-actions gd-actions" v-if="!tributePending && !returnPending">
          <button class="gt-btn ghost sm" :disabled="!canAct" @click="doHint">提示</button>
          <button class="gt-btn ghost sm" :disabled="!sel.length" @click="clearSel">重选</button>
          <button
            class="gt-btn ghost sm"
            :disabled="!flushCombos.length"
            :title="flushCombos.length ? `点击轮换同花顺（共 ${flushCombos.length} 组，从大到小）` : '手上没有同花顺'"
            @click="cycleFlush"
          >同花顺<em v-if="flushCombos.length > 1" class="gd-btn-count">{{ flushCombos.length }}</em></button>
          <button
            class="gt-btn ghost sm"
            :disabled="!seqGroups.length"
            :title="seqGroups.length ? `点击轮换顺子（共 ${seqGroups.length} 组，同花顺优先），弹出对应牌` : '手上没有顺子'"
            @click="cycleSeq"
          >顺子<em v-if="seqGroups.length > 1" class="gd-btn-count">{{ seqGroups.length }}</em></button>
          <button
            class="gt-btn ghost sm"
            :disabled="!seqGroups.length && !sel.length"
            :title="seqGroups.length || sel.length ? '把选中的牌（未选则第一组顺子）钉到最左' : '先点顺子按钮弹出一组，再挪到左侧'"
            @click="pinSeqToLeft"
          >挪左侧</button>
          <button
            class="gt-btn ghost sm"
            :disabled="!sel.length"
            :title="sel.length ? '把选中的牌钉到最右（按牌值升序，攒顺子用）' : '先选牌，再挪到右侧'"
            @click="pinToRight"
          >挪右侧</button>
          <span class="gd-act-gap"></span>
          <button class="gt-btn gd-pass" :disabled="!canAct || !target" @click="doPass">不要</button>
          <button class="gt-btn gd-play" :disabled="!canAct || !canPlay" @click="doPlay">出牌</button>
        </div>

        <!-- 进贡（在线 · 手动选牌，逢人配不能贡；服务端 5 分钟未选则自动代选） -->
        <div v-else-if="tributePending" class="gd-return gd-tribute">
          <div class="gd-return-tip">
            进贡：点一张牌进贡给 {{ seatName(tributeTo) }}（逢人配不能进贡）
            <b v-if="leftSec" class="gd-timer" :class="{ urgent: leftSec <= 60 }">{{ mmss(leftSec) }} 后自动代选</b>
          </div>
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

        <!-- 还贡（在线 · 双方并行，各自选牌确认；服务端要求 ≤10，5 分钟未选则自动代选）
             v2.46.23：选中后不再立刻提交——先高亮预览，点「还贡」按钮才真正给出（夜星） -->
        <div v-else-if="returnPending" class="gd-return">
          <div class="gd-return-tip">
            还贡给 {{ seatName(returnTo) }}：点一张 ≤10 的牌选中（不能还级牌 / 王），再点「还贡」确认
            <b v-if="leftSec" class="gd-timer" :class="{ urgent: leftSec <= 60 }">{{ mmss(leftSec) }} 后自动代选</b>
          </div>
          <div class="gd-return-cards">
            <span
              v-for="c in returnOptions"
              :key="c.id"
              class="gt-card pickable"
              :class="[cardCls(c), { 'is-pick': returnSel === c.id }]"
              @click="returnSel = returnSel === c.id ? null : c.id"
            >
              <span class="c-tl"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
              <span class="c-mid">{{ cardSuit(c) }}</span>
              <span class="c-br"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
            </span>
            <p v-if="!returnOptions.length" class="gd-hand-empty">手上没有 ≤10 的牌可还</p>
          </div>
          <button class="gt-btn gd-play gd-return-ok" :disabled="returnSel == null" @click="confirmReturn">
            还贡{{ returnSelCard ? ` ${cardText(returnSelCard)}${cardSuit(returnSelCard)}` : '' }}
          </button>
        </div>

        <!-- 划选手势：pointerdown 落在手牌区，pointermove / up 由脚本挂到 window
             —— 手指滑出牌区（往上飘 / 划到牌桌）时仍能收到事件，不会半途断掉。
             手机上还支持「上滑出牌」：按住往上带过阈值，松手即打（见 onHandUp）。 -->
        <div
          class="gd-hand"
          ref="handRef"
          :class="{ 'is-up': upHint }"
          :style="{ '--gd-overlap': overlap + 'px' }"
          @pointerdown="onHandDown"
        >
          <template v-for="(c, i) in viewHand" :key="c.id">
            <!-- 分区线（v2.46.24）：左钉区|散牌区、散牌区|右钉区 之间画一道竖线，
                 理好的牌和散牌一眼分开（夜星：「现在都展示在一块，很乱」） -->
            <i
              v-if="(headCount > 0 && i === headCount) || (tailStart > headCount && i === tailStart)"
              class="gd-hand-divider"
              aria-hidden="true"
            ></i>
            <span
              class="gt-card"
              :class="cardCls(c, i)"
              :style="dealWave ? { '--i': i } : null"
              :data-idx="i"
              @click="onPick(c, i, $event)"
            >
              <span class="c-tl"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
              <span class="c-mid">{{ cardSuit(c) }}</span>
              <span class="c-br"><b>{{ cardText(c) }}</b><i>{{ cardSuit(c) }}</i></span>
              <span v-if="isWildCard(c)" class="tag">配</span>
            </span>
          </template>
          <p v-if="!viewHand.length" class="gd-hand-empty">— 无手牌 —</p>
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
          <!-- 我方升级 / 打过 A：彩带雨庆祝（reduced-motion 下 CSS 直接隐藏） -->
          <div v-if="iWon" class="gt-confetti" aria-hidden="true">
            <i v-for="(st, i) in confetti" :key="i" :style="st"></i>
          </div>
          <h3>{{ matchOver ? (iWon ? '我方打过 A，全场获胜！' : '对方打过 A，本场落败') : (iWon ? '我方升级！' : '对方升级') }}</h3>
          <p>
            名次：<b>{{ roundResult.order.map(s => seatName(s)).join(' → ') }}</b><br>
            升级：{{ iWon ? '我方' : '对方' }} +{{ upShown }} 级<br>
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
import { sfx, setMuted, isMuted, panOf } from '@/utils/games/sfx'
import { vibrate, hapticsEnabled, setHaptics } from '@/utils/games/haptics'
import confettiPieces from '@/utils/games/confetti'
import countUp from '@/utils/games/countUp'
import { speak } from '@/utils/games/tts'
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
  /** 服务端给的「操作截止时间」（ISO 本地时间，仅供还贡/进贡倒计时展示） */
  deadlineAt: { type: String, default: '' },
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
/** 触感反馈开关（v2.46.19）：与静音并列的小按钮 */
const hapticsOn = ref(hapticsEnabled())
function toggleHaptics() { hapticsOn.value = !hapticsOn.value; setHaptics(hapticsOn.value) }
/** 胜利彩带参数：一次生成、整个会话复用（确定性伪随机，不会闪变） */
const confetti = confettiPieces(26)
const history = ref([])         // 结构化出牌记录（最新在前）
const roundResult = ref({ up: 0, winTeam: 0, order: [] })
/** 结算「+N 级」逐格上滚（v2.46.20，Balatro 式 tick）：数字从 0 滚到位，不再直接甩出 */
const upShown = countUp(() => roundResult.value.up || 0)
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

/**
 * 牌桌**视角座位**：整张桌按它旋转 90°，让「我」永远坐在牌桌下方（V2467-001）。
 *
 * 旧版把座位写死成「0=下 1=右 2=上 3=左」，只有房主（0 号位）看到的方位是对的；
 * 我坐到 1/3 号位时，自己的牌在下方、人却在牌桌右侧，看着非常别扭
 * （夜星：「方位在哪，视角就转到哪，现在都是房主视角，很怪异」）。
 *
 * 在线 = 我的真实座位；单机 = 第一个真人座位。**同屏 p4 不做逐人翻转**：
 * 那会每换一个人出牌整桌就转 90°，比不转更晕。
 */
const povSeat = computed(() => (isOnline.value ? oSeat.value : (HUMAN_SEATS.value[0] ?? 0)))
const topSeat = computed(() => (povSeat.value + 2) % 4)
const rightSeat = computed(() => (povSeat.value + 1) % 4)
const leftSeat = computed(() => (povSeat.value + 3) % 4)

/** 手牌展示顺序（v2.46.24 三分区）：[左钉区 | 散牌区 | 右钉区]，区间画分隔线。
 *  同花顺：**只有纯天然的（不含逢人配凑的）**自动理到最左——夜星：「4 张同花需要
 *  配牌成同花顺的不在左侧展示」，红桃级牌搭进来的半成品顺不许被拉走。
 *  顺子：v2.46.21 起手动（点「顺子」弹出预览 → 「挪左侧」钉住）；
 *  v2.46.24 加「挪右侧」：选中的牌钉到最右、按牌值升序（新牌总落在比自己小一级的
 *  牌前面，正好把想拼的顺子从右往左攒）。钉住持久：出掉 id 自动失效，新局自然清空。 */
const pinnedSeq = ref(new Set())
const rightPinned = ref(new Set())
const handParts = computed(() => {
  const base = isOnline.value ? (props.onlineView?.me?.hand || []) : (hands.value[viewSeat.value] || [])
  if (phase.value === 'settled' || !base.length) return { head: base, mid: [], tail: [] }
  const naturals = base.filter(c => !G.isWild(c, roundLevel.value))
  const flushes = G.findFlushBombs(naturals, roundLevel.value)
  const left = pinnedSeq.value
  const right = rightPinned.value
  const hasLeft = base.some(c => left.has(c.id))
  const hasRight = base.some(c => right.has(c.id))
  if (!flushes.length && !hasLeft && !hasRight) return { head: [], mid: base, tail: [] }
  const usedL = new Set()
  for (const cs of flushes) for (const c of cs) usedL.add(c.id)
  for (const c of base) if (left.has(c.id)) usedL.add(c.id)
  const usedR = new Set()
  for (const c of base) if (right.has(c.id) && !usedL.has(c.id)) usedR.add(c.id)
  const asc = (a, b) => G.cardValue(a, roundLevel.value) - G.cardValue(b, roundLevel.value)
  return {
    head: base.filter(c => usedL.has(c.id)).sort(asc),
    mid: base.filter(c => !usedL.has(c.id) && !usedR.has(c.id)),
    tail: base.filter(c => usedR.has(c.id)).sort(asc),
  }
})
const viewHand = computed(() => {
  const p = handParts.value
  return p.head.concat(p.mid, p.tail)
})
/** 手牌分隔线位置：headCount>0 时在 head|mid 之间画线；tailStart 在 mid|tail 之间画线 */
const headCount = computed(() => handParts.value.head.length)
const tailStart = computed(() => handParts.value.head.length + handParts.value.mid.length)
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
    if (tributeResisted.value) return '抗贡成立，不进贡'
    if (tributePending.value) return `请选择一张牌进贡给 ${seatName(tributeTo.value)}`
    const waiting = tributePlan.value.filter(g => !g.card)
      .map(g => `${seatName(g.from)} → ${seatName(g.to)}`).join('、')
    return waiting ? `进贡中：${waiting}` : '等对方进贡…'
  }
  if (isOnline.value && props.onlineView?.phase === 'return') {
    // v2.46.23 还贡并行：我还没还 → 选牌确认；我还完了 → 等对方（各自独立、互不排队）
    return returnPending.value ? '选一张 ≤10 的牌，点「还贡」确认' : '等对方还贡…'
  }
  if (!HUMAN_SEATS.value.includes(turn.value)) return `${seatName(turn.value)} 思考中…`
  if (turn.value !== viewSeat.value) return `轮到 ${seatName(turn.value)}`
  return target.value ? '请压过上一手，或选择「不要」' : '本轮由你先出牌'
})
/** 还贡候选项（在线 return 阶段、自己还有未还的贡时；v2.46.23 起双方并行，不再看 turn） */
const returnPending = computed(() =>
  isOnline.value && props.onlineView?.phase === 'return' && !!props.onlineView?.me?.return_pending)
const returnOptions = computed(() => props.onlineView?.me?.return_options || [])
/** 进贡候选项（仅在线 tribute 阶段、轮到自己时；服务端手动选牌，无倒计时） */
const tributePending = computed(() =>
  isOnline.value && props.onlineView?.phase === 'tribute' && !!props.onlineView?.me?.tribute_pending)
const tributeOptions = computed(() => props.onlineView?.me?.tribute_options || [])
const tributeTo = computed(() => props.onlineView?.me?.tribute_to ?? null)

/* ---------- 进贡横幅：从服务端 tribute 计划直接读「谁贡给谁」 ----------
 * givers = 计划（谁→谁）；pairs = 已完成的贡（含牌）；returns = 还贡计划。
 * 抗贡（双方合计两张大王）时服务端不给 givers，只给 resisted + leader。 */
const tributeInfo = computed(() => (isOnline.value ? props.onlineView?.tribute : null) || null)
const tributePhaseVisible = computed(() =>
  ['tribute', 'return'].includes(props.onlineView?.phase) && !!tributeInfo.value)
const tributeResisted = computed(() => !!tributeInfo.value?.resisted)
const tributeLeader = computed(() => tributeInfo.value?.leader ?? null)
const tributePhaseLabel = computed(() => (props.onlineView?.phase === 'return' ? '还贡' : '进贡'))
const tributePlan = computed(() => {
  const tr = tributeInfo.value
  if (!tr || tr.resisted) return []
  if (props.onlineView?.phase === 'return') {
    return (tr.returns || []).map(r => ({
      from: r.from, to: r.to, card: r.card || null, done: !!r.done,
    }))
  }
  const done = new Map((tr.pairs || []).map(p => [p.from, p.card]))
  return (tr.givers || []).map(g => ({
    from: g.from, to: g.to, card: done.get(g.from) || null,
  }))
})
/** 只有「轮到自己选贡牌 + 服务端确实给了截止时间」才显示倒计时 */
const showCountdown = computed(() => (returnPending.value || tributePending.value) && leftSec.value > 0)

/* ---------- 同花顺 / 顺子：一键选中 + 轮换 ----------
 * 夜星定的规则（v2.46.15 起「放到最左」是**自动**的，见 viewHand；按钮只管选中）：
 *  1) 组合按牌型**从大到小**（见 guandan.js 的 seqCombos）—— 第一次点给的是**最大**的一组，
 *     6~9 张同花时也就是「默认选中最大的同花顺」；再点依次换小的，转完一圈回到最大；
 *  2) 「顺子」按钮的候选是 **同花顺优先，其次普通顺子**（优先级 同花顺 > 顺子）；
 *  3) 点按钮同时把这一组写进 sel，直接「出牌」即可。
 */
const flushCombos = computed(() => G.findFlushBombs(viewHand.value, roundLevel.value))
const seqGroups = computed(() => G.findSeqGroups(viewHand.value, roundLevel.value))
const flushIdx = ref(0)
const seqIdx = ref(0)

function gather(combos, idxRef, label) {
  if (!combos.length) { toastMsg(`手上没有${label}`); return }
  if (idxRef.value >= combos.length) idxRef.value = 0
  const cards = combos[idxRef.value]
  sel.value = cards.map(c => c.id)
  toastMsg(`${label} ${idxRef.value + 1}/${combos.length}`)
  idxRef.value = (idxRef.value + 1) % combos.length
  sfx.pick()
}
/** 顺子弹出预览（v2.46.21）：点「顺子」按钮把刚轮换出的那组整排弹跳高亮 1.2s，
 *  不再自动理到最左 —— 先看清是哪五张，再决定要不要点「挪左侧」钉住。 */
const seqPopIds = ref(new Set())
let seqPopTimer = null
function cycleFlush() { gather(flushCombos.value, flushIdx, '同花顺') }
function cycleSeq() {
  gather(seqGroups.value, seqIdx, '顺子')
  const shown = seqGroups.value[(seqIdx.value + seqGroups.value.length - 1) % seqGroups.value.length]
  if (shown) {
    seqPopIds.value = new Set(shown.map(c => c.id))
    clearTimeout(seqPopTimer)
    seqPopTimer = setTimeout(() => { seqPopIds.value = new Set() }, 1200)
  }
}
/** 「挪左侧」（v2.46.21）：把当前选中的牌钉到最左（配合顺子按钮弹出后使用）；
 *  没有选中时退而钉第一组顺子。钉住持久：出掉对应牌 id 自动失效，新局换新牌自然清空。
 *  v2.46.24：与「挪右侧」互斥——挪左先解除右钉。 */
function pinSeqToLeft() {
  let ids = sel.value.slice()
  if (!ids.length) {
    if (!seqGroups.value.length) { toastMsg('手上没有顺子'); return }
    ids = seqGroups.value[0].map(c => c.id)
  }
  pinnedSeq.value = new Set([...pinnedSeq.value, ...ids])
  if (rightPinned.value.size) {
    rightPinned.value = new Set([...rightPinned.value].filter(id => !ids.includes(id)))
  }
  toastMsg('已挪到左侧')
  sfx.pick()
}
/** 「挪右侧」（v2.46.24，夜星）：选中的牌钉到最右、按牌值升序——新加的牌总落在
 *  比自己小一级的牌前面，想把一条顺子从右往左攒时逐张挪即可。与「挪左侧」互斥。 */
function pinToRight() {
  const ids = sel.value.slice()
  if (!ids.length) { toastMsg('先选牌，再点「挪右侧」'); return }
  rightPinned.value = new Set([...rightPinned.value, ...ids])
  if (pinnedSeq.value.size) {
    pinnedSeq.value = new Set([...pinnedSeq.value].filter(id => !ids.includes(id)))
  }
  sel.value = []
  toastMsg(`已挪到右侧 ${ids.length} 张`)
  sfx.pick()
}

/* ---------- 贡牌倒计时（服务端 5 分钟未选则自动代选） ---------- */
const leftSec = ref(0)
let tickTimer = null
function tickLeft() {
  const t = props.deadlineAt ? Date.parse(props.deadlineAt) : NaN
  leftSec.value = Number.isNaN(t) ? 0 : Math.max(0, Math.round((t - Date.now()) / 1000))
}
function mmss(sec) {
  const s = Math.max(0, Math.floor(sec))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/* ---------- 出牌记录小窗：默认展开最近 3 条，可收起 ---------- */
const histOpen = ref(false)

/* ---------- 进贡 / 还贡飞牌动画 ---------- */
/** 屏幕四个方位的锚点：0=下(我) 1=右 2=上 3=左 —— 与牌桌的视角旋转保持一致 */
const SCREEN_ANCHOR = {
  0: { x: '50%', y: '84%' },
  1: { x: '84%', y: '52%' },
  2: { x: '50%', y: '16%' },
  3: { x: '16%', y: '52%' },
}
/** 座位号 → 屏幕方位：视角座位永远落在下方（3 号位在我左手边，以此类推） */
function screenPos(s) { return ((Number(s) - povSeat.value) % 4 + 4) % 4 }
const flyCard = ref(null)        // { card, from, to }
const flyStyle = computed(() => {
  const f = flyCard.value
  if (!f) return {}
  const a = SCREEN_ANCHOR[screenPos(f.from)]
  const b = SCREEN_ANCHOR[screenPos(f.to)]
  return { '--fx0': a.x, '--fy0': a.y, '--fx1': b.x, '--fy1': b.y }
})
let flyTimer = null
const seenFly = new Set()
function flyKey(h) { return `${h.kind}:${h.seat}:${h.to}:${h.card?.id}` }
/* 进贡 / 还贡动画走**队列**逐个播：一局最多 4 笔（双下进 2 还 2），首屏补放也不乱。
 * 🔴 旧版 onMounted 里 primeFly() 把首屏 history 里已有的贡牌记录全部标记「已看过」——
 * 而换局时 GameTableView 用 :key="roomId-roundNo" 整组件重挂载，机器人间的进贡在
 * 服务端瞬间完成后组件才挂载 → 动画永远不播、toast 也不出，用户完全看不到进贡
 * 发生过（V24616-001「人机不进贡」的实际观感）。现在反过来：history 里的贡牌条目
 * 一律视为未播过，入队逐个飞 + toast；seenFly 只防同一条目重复播放。 */
const flyQueue = []
let flyBusy = false
function enqueueFly(h) {
  flyQueue.push(h)
  drainFly()
}
function drainFly() {
  if (flyBusy) return
  const h = flyQueue.shift()
  if (!h) return
  flyBusy = true
  flyCard.value = { card: h.card, from: h.seat, to: h.to }
  toastMsg(
    `${seatName(h.seat)} 向 ${seatName(h.to)} ${h.kind === 'tribute' ? '进贡' : '还贡'} ${cardText(h.card)}${cardSuit(h.card)}`,
    2600,
  )
  clearTimeout(flyTimer)
  flyTimer = setTimeout(() => { flyCard.value = null; flyBusy = false; drainFly() }, 1150)
}
watch(history, (list) => {
  // history 最新在前；补放时按发生顺序（旧→新）播
  const items = list.filter(h => h.kind === 'tribute' || h.kind === 'return').reverse()
  for (const h of items) {
    const k = flyKey(h)
    if (seenFly.has(k)) continue
    seenFly.add(k)
    enqueueFly(h)
  }
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
/* ---------- 发牌错峰动画（v2.46.19）----------
 * 新一局发牌时手牌逐张（每张 35ms）从上方带角度落进手牌，而不是整排一起出现。
 * dealWave 只在开局后 ~1.2s 内为真，之后的选牌/出牌不再触发。 */
const dealWave = ref(false)
let dealTimer = null
function startDealWave() {
  dealWave.value = true
  clearTimeout(dealTimer)
  dealTimer = setTimeout(() => { dealWave.value = false }, 1300)
}
function cardCls(c, i) {
  const cls = {
    'is-red': isRed(c),
    'is-joker': !!c.joker,
    'is-level': !c.joker && c.rank === roundLevel.value,
    'is-wild': isWildCard(c),
    'is-sel': sel.value.includes(c.id),
    'is-seqpop': seqPopIds.value.has(c.id),
  }
  if (i !== undefined) {
    cls.pickable = canAct.value
    if (dealWave.value) cls['gd-deal-in'] = true
  }
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
  const acting = isTurn(s)
  return {
    'is-active': acting,
    'is-out': finished.value.includes(s),
    'is-me': isOnline.value && s === oSeat.value,
    // 队友标识（v2.46.19）：青蓝描环 + 名字旁「友」角标，一眼分清敌我
    'is-mate': s !== povSeat.value && G.TEAM_OF[s] === myTeam.value,
    // 行动方聚焦（v2.46.19）：轮到别人时其余席位降饱和压暗，视线聚焦到行动方
    'is-idle': phase.value === 'playing' && turn.value >= 0 && !acting && !finished.value.includes(s),
  }
}
/** 报牌阈值（夜星 2026-10-09 定的）：剩 ≤7 张就报牌 */
const BAO_LIMIT = 7
/** 报牌张数：对局中、未出完、剩 1~BAO_LIMIT 张时返回张数，否则 0（v-if 用） */
function baoCount(s) {
  if (phase.value !== 'playing' || finished.value.includes(s)) return 0
  const n = handCount(s)
  return n >= 1 && n <= BAO_LIMIT ? n : 0
}
/** 报牌名单变化 → 新进入报牌的座位响一声提醒（每座位每局只响一次；
 *  张数回升 = 新一局重新发牌，自动从名单里移除、下局可再次提醒） */
const baoSeats = computed(() => [0, 1, 2, 3].filter(s => baoCount(s) > 0))
const seenBao = new Set()
watch(baoSeats, (list) => {
  const now = new Set(list)
  for (const s of now) {
    if (!seenBao.has(s)) {
      seenBao.add(s)
      sfx.alert(panOf(s, povSeat.value))
    }
  }
  for (const s of [...seenBao]) if (!now.has(s)) seenBao.delete(s)
})
/** 升级进度：级数 2~A(14) 映射成 0~100%，打过 A 显示满格 */
function lvPct(l) {
  const p = Math.max(0, Math.min(1, (l - G.MIN_LEVEL) / (G.MAX_LEVEL - G.MIN_LEVEL)))
  return `${Math.round(p * 100)}%`
}
function toggleMute() { muted.value = !muted.value; setMuted(muted.value) }
let toastTimer = null
function toastMsg(t, ms = 1800) {
  toast.value = t
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, ms)
}

/* ---------- 「不要」气泡（夜星：点不要后头像处弹小气泡，参考主流棋牌） ----------
 * 本地：applyPass 直接触发；在线：syncFromView 按 history 增量触发（服务端 history 只追加，
 * 长度变大且最后一条是 pass → 该座位弹「不要」，长度变小 = 新一局，重置计数）。 */
const passBubbles = ref({})
const passBubbleTimers = {}
function showPassBubble(seat) {
  if (seat === null || seat === undefined || seat < 0) return
  passBubbles.value = { ...passBubbles.value, [seat]: true }
  clearTimeout(passBubbleTimers[seat])
  passBubbleTimers[seat] = setTimeout(() => {
    const next = { ...passBubbles.value }
    delete next[seat]
    passBubbles.value = next
  }, 2000)
}

/* ---------- 炸弹特效（夜星：出牌动效和炸弹特效，参考网上的设计） ----------
 * 普通出牌的入场动画早就有（.gd-throw，从下方浮入）；这里补**炸弹 / 同花顺 / 火箭**：
 * 中央金圈炸开 + 「炸弹！」大字 + 全桌 0.55s 震动。在线轮询每 1.6s 全量重建 lastPlay，
 * 必须按内容 key 判重，否则特效每 1.6s 重放一遍。 */
const bombFx = ref(false)
const tableShake = ref(false)
/** 牌型名称浮现（v2.46.19）：每一手牌都短暂放大显示牌型名 */
const patFx = ref(null)
let bombTimer1 = null
let bombTimer2 = null
let patFxTimer = null
/** hit-stop 定帧（v2.46.20）：炸弹落地前全桌冻结一小段时间 */
const freeze = ref(false)
let freezeTimer = null
let lastPlayKey = ''
/** 出牌口播文本（v2.46.24，夜星：「报实际出的牌的内容，如三个二带一对五、四个六」）：
 *  按点数分组生成口语描述；逢人配（百搭）按它补进的数量并入「几个 X」。 */
const TTS_CN = { 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: 'J', 12: 'Q', 13: 'K', 14: 'A' }
const TTS_COUNT = { 1: '', 2: '一对', 3: '三个', 4: '四个', 5: '五个', 6: '六个' }
function ttsRank(c) { return c.joker ? (c.joker === 'big' ? '大王' : '小王') : (TTS_CN[c.rank] || c.rank) }
function describePlay(cards, pat) {
  const t = pat?.type
  if (!t) return ''
  // 按点数分组（大小王各自一组；逢人配不单列，数量并入主组）
  const groups = new Map()
  let wildN = 0
  for (const c of cards) {
    if (G.isWild(c, roundLevel.value)) { wildN += 1; continue }
    const k = c.joker ? `j${c.joker}` : c.rank
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k).push(c)
  }
  const gs = [...groups.values()].sort((a, b) => b.length - a.length)
  const main = gs[0] || []
  const mainN = main.length + (gs.length ? 0 : wildN)   // 全百搭时并给主组
  const mainTxt = `${TTS_COUNT[Math.min(mainN, 6)] || ''}${ttsRank(main[0] || cards[0])}`
  if (t === 'single') return mainTxt || '单张'
  if (t === 'pair') return `一对${ttsRank(main[0] || cards[0])}`
  if (t === 'triple') return `三个${ttsRank(main[0] || cards[0])}`
  if (t === 'triple2') {
    const kick = gs[1]
    return `三个${ttsRank(main[0] || cards[0])}带一对${kick ? ttsRank(kick[0]) : ''}`
  }
  if (t === 'bomb') return `${TTS_COUNT[Math.min(cards.length, 6)] || ''}${ttsRank(main[0] || cards[0])}`
  return G.PATTERN_NAME[t] || ''   // 顺子 / 三连对 / 钢板 / 同花顺 / 火箭：报牌型名
}
function playFxFor(p) {
  if (!p || !p.cards || !p.cards.length) return
  const key = `${p.seat}:${p.cards.length}:${p.cards[0]?.id}:${p.cards[p.cards.length - 1]?.id}`
  if (key === lastPlayKey) return
  lastPlayKey = key
  const pat = p.pattern || {}
  // 语音报牌（v2.46.24）：口播实际出的牌面内容（本地与在线同走这里，lastPlay 全量投影）
  const say = describePlay(p.cards, pat)
  if (say) speak(say)
  // 牌型名浮现：普通牌型墨底，炸弹 / 同花顺 / 火箭金底
  const name = G.PATTERN_NAME[pat.type] || ''
  if (name) {
    patFx.value = {
      name,
      gold: (pat.bombLevel || 0) > 0 || pat.type === 'flushbomb' || pat.type === 'rocket',
    }
    clearTimeout(patFxTimer)
    patFxTimer = setTimeout(() => { patFx.value = null }, 1000)
  }
  if ((pat.bombLevel || 0) > 0 || pat.type === 'rocket') {
    // hit-stop（v2.46.20）：先全桌定帧 90ms 再爆——格斗游戏「卡帧→爆发」的重击节奏。
    // 定帧期间金圈、大字、震动都不出现，解冻瞬间一起上，冲击感更强。
    freeze.value = true
    clearTimeout(bombTimer1)
    clearTimeout(bombTimer2)
    clearTimeout(freezeTimer)
    freezeTimer = setTimeout(() => {
      freeze.value = false
      bombFx.value = true
      tableShake.value = true
      vibrate([30, 40, 30])
      bombTimer1 = setTimeout(() => { bombFx.value = false }, 1100)
      bombTimer2 = setTimeout(() => { tableShake.value = false }, 600)
    }, 90)
  }
}
watch(lastPlay, (p) => playFxFor(p))

/* ---------- 出牌历史 ---------- */
function pushHistory(item) {
  history.value.unshift(item)
  if (history.value.length > 60) history.value.length = 60
}

/* ---------- 在线：服务端投影 → 展示态 ---------- */
const PHASE_MAP = { playing: 'playing', tribute: 'playing', return: 'playing', finished: 'settled' }
const onlineHistLen = ref(0)
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
  // 服务端 history 按时间正序，取最新在前；增量部分里最后一条是 pass → 弹「不要」气泡
  const hist = v.history || []
  if (hist.length !== onlineHistLen.value) {
    if (hist.length < onlineHistLen.value) startDealWave()   // 历史变短 = 新一局发牌
    if (hist.length > onlineHistLen.value) {
      const lastEv = hist[hist.length - 1]
      if (lastEv && lastEv.kind === 'pass') showPassBubble(lastEv.seat)
    }
    onlineHistLen.value = hist.length
  }
  history.value = hist.slice().reverse()
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
/* ---------- 还贡：先选中预览、点按钮才确认（v2.46.23 夜星：「选中后不是立马给」） ---------- */
const returnSel = ref(null)
const returnSelCard = computed(() =>
  returnOptions.value.find(c => c.id === returnSel.value) || null)
const returnTo = computed(() => {
  const r = (tributeInfo.value?.returns || []).find(x => x.from === oSeat.value)
  return r ? r.to : null
})
watch(returnPending, (on) => { if (!on) returnSel.value = null })
function confirmReturn() {
  if (!returnPending.value || returnSel.value == null) return
  actOnline({ type: 'return', card_id: returnSel.value })
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
  startDealWave()
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
  showPassBubble(seat)
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
/* 上滑出牌（手机手势）：按下后**垂直于手牌排列方向**带过阈值 → 松手即打。
   阈值 34px：足够区别于划选时手指的纵向抖动，又不至于要甩很大幅度。
   手牌被整块 rotate(90deg)（竖屏兜底）时排列轴变成纵向，此时关掉这个手势，避免与划选打架。 */
const UP_SWIPE = 34
const upHint = ref(false)
let swipeStart = null
let swipeStartIdx = -1
let swipeUpOn = false

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
  swipeStart = { x: e.clientX, y: e.clientY }
  swipeStartIdx = idx
  swipeUpOn = false
  upHint.value = false
  window.addEventListener('pointermove', onHandMove, { passive: false })
  window.addEventListener('pointerup', onHandUp)
  window.addEventListener('pointercancel', onHandUp)
  applySwipe(idx)
}
function onHandMove(e) {
  if (swipeMode === null || dragId !== e.pointerId) return
  if (e.cancelable) e.preventDefault()
  // 上滑出牌：只在手牌横排时启用（排列轴为 x），纵向位移显著大于横向才算
  if (swipeStart && handAxis() === 'x') {
    const dy = e.clientY - swipeStart.y
    const dx = e.clientX - swipeStart.x
    const up = dy <= -UP_SWIPE && Math.abs(dy) > Math.abs(dx) * 1.1
    if (up !== swipeUpOn) { swipeUpOn = up; upHint.value = up }
    if (up) return                       // 进入上滑态后不再动划选
  }
  applySwipe(cardIndexAt(e.clientX, e.clientY, true))
}
function onHandUp(e) {
  if (e && e.pointerId !== undefined && dragId !== null && e.pointerId !== dragId) return
  const wasUp = swipeUpOn
  const idx = swipeStartIdx
  dragId = null
  swipeMode = null
  swipeLast = -1
  swipeStart = null
  swipeUpOn = false
  upHint.value = false
  window.removeEventListener('pointermove', onHandMove)
  window.removeEventListener('pointerup', onHandUp)
  window.removeEventListener('pointercancel', onHandUp)
  // 触控结束后浏览器还会补发一次 click，留足窗口抑制它，避免把最后一张又点掉
  setTimeout(() => { suppressClick = false }, 350)
  if (wasUp && e && e.type !== 'pointercancel') swipeUpPlay(idx)
}
/** 上滑松手：有选中就按选中出，没选中就把手指划过的那一张当选中（单张）。
 *  合法性交给 doPlay 统一校验（牌型 / 是否压得过）—— 不合法会 toast 说明原因，
 *  并把这一次的选中留在手上，方便玩家直接改选。 */
function swipeUpPlay(idx) {
  if (!canAct.value) return
  if (!sel.value.length && idx >= 0) {
    const c = viewHand.value[idx]
    if (c) { sel.value = [c.id]; anchorIdx.value = idx; sfx.pick() }
  }
  if (!sel.value.length) return
  doPlay()
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
  // 贡牌倒计时：本地每秒自算剩余时间，不额外请求（死亡时间来自服务端 deadline_at）
  tickLeft()
  clearInterval(tickTimer)
  tickTimer = setInterval(tickLeft, 1000)
  if (isOnline.value) {
    syncFromView(props.onlineView)
    return
  }
  if (props.resume && restoreLocal()) toastMsg('已接着上一局继续')
  newRound()
})
onBeforeUnmount(() => {
  clearTimeout(aiTimer)
  clearTimeout(toastTimer)
  clearTimeout(flyTimer)
  clearTimeout(dealTimer)
  clearTimeout(patFxTimer)
  clearTimeout(bombTimer1)
  clearTimeout(bombTimer2)
  clearTimeout(freezeTimer)
  clearTimeout(seqPopTimer)
  clearInterval(tickTimer)
  if (ro) ro.disconnect()
  // 划选期间被卸载：window 上的手势监听必须摘掉，否则残留到下一个页面
  window.removeEventListener('pointermove', onHandMove)
  window.removeEventListener('pointerup', onHandUp)
  window.removeEventListener('pointercancel', onHandUp)
})
watch(() => props.deadlineAt, tickLeft)
// 手牌张数一变（发牌 / 出牌 / 换局）→ 轮换指针复位；顺子「挪左侧」是手动钉住，不清
watch(() => viewHand.value.length, () => {
  flushIdx.value = 0
  seqIdx.value = 0
  requestAnimationFrame(measureHand)
})
// 新一局（settled → playing）清掉上一局钉住的顺子与右钉牌；同局内钉住的牌打出后 id 自动失效
watch(phase, (p, old) => {
  if (p === 'playing' && old === 'settled') {
    pinnedSeq.value = new Set()
    rightPinned.value = new Set()
  }
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

/* 牌桌：主区 + 左下角出牌记录（浮层，默认收起，不占牌桌宽度）
   v2.46.23 背景重做（夜星：「背景不兼容」）——参考真实赌桌 / WPT 类客户端的设计语言：
   ① 绒布降饱和压暗（旧版 #227154 太艳，与墨蓝外壳打架），中央亮四周暗的聚光感；
   ② 叠 45°/135° 两层极淡织纹（crosshatch，模拟绒布的布纹走向，透明度 <3% 不抢牌）；
   ③ 内圈一条鎏金细线（::before，inset 7px）当「桌沿镶边」，呼应全站鎏金 accent；
   ④ 暗角加深（inset 大半径黑晕），四角沉下去、视线聚焦中央出牌区。 */
.gd-table {
  position: relative;
  flex: 1; min-height: 0; display: flex; gap: 10px;
  padding: 8px; border-radius: 16px;
  background:
    repeating-linear-gradient(45deg, rgba(255, 255, 255, .022) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(135deg, rgba(255, 255, 255, .022) 0 1px, transparent 1px 5px),
    radial-gradient(120% 105% at 50% 38%, #1f5c45 0%, #164534 46%, #0c3125 78%, #082419 100%);
  border: 1px solid rgba(0, 0, 0, .45);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, .05),
    inset 0 0 90px -18px rgba(0, 0, 0, .72),
    0 10px 30px -18px rgba(0, 0, 0, .8);
}
/* 鎏金桌沿镶线：一条细线就够，宁可克制不要花哨（Apple HIG 式留白） */
.gd-table::before {
  content: ''; position: absolute; inset: 7px; border-radius: 11px;
  border: 1px solid rgba(233, 200, 119, .2);
  box-shadow: 0 0 14px -6px rgba(233, 200, 119, .35);
  pointer-events: none;
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
  position: relative;

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
  .gd-hand.is-up { transform: none; }
  .gd-center-cards > .gt-card { animation: none !important; }
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
/* 分区线（v2.46.24）：左钉区|散牌区、散牌区|右钉区 之间的鎏金竖线 */
.gd-hand-divider {
  flex: none; width: 2px; align-self: stretch; margin: 4px 5px;
  border-radius: 2px; background: rgba(233, 200, 119, .5);
  box-shadow: 0 0 8px rgba(233, 200, 119, .3);
}
/* 上滑出牌：手牌整体抬起 + 头顶弹出「松手出牌」胶囊（提前告知松手会发生什么） */
.gd-hand.is-up { position: relative; transform: translateY(-8px); }
.gd-hand.is-up::after {
  content: '松手出牌';
  position: absolute; left: 50%; top: 2px; transform: translate(-50%, -110%);
  padding: 3px 13px; border-radius: 999px; font-size: 12px; font-weight: 600;
  color: #2a1d05; white-space: nowrap; pointer-events: none; z-index: 6;
  background: linear-gradient(180deg, #f4dc9c, #d9b65f);
  border: 1px solid rgba(255, 255, 255, .5);
  box-shadow: 0 8px 18px -8px rgba(0, 0, 0, .92), inset 0 1px 0 rgba(255, 255, 255, .6);
  animation: gt-pop .16s ease-out both;
}

/* ===== 出牌动效 =====
   打出的牌不再「凭空出现」：从上方带角度甩进中央、逐张 30ms 错峰落下，
   落定时轻微回弹。旧版只有一个 0.34s 的原地 pop（`gt-anim-play`），
   牌是「先在位、再抖一下」，看不出是谁打过来的。 */
@keyframes gd-throw {
  0% { transform: translateY(-52px) rotate(-15deg) scale(1.26); opacity: 0; }
  62% { transform: translateY(3px) rotate(2deg) scale(.985); opacity: 1; }
  100% { transform: none; opacity: 1; }
}
.gd-center-cards > .gt-card {
  animation: gd-throw .36s cubic-bezier(.2, .85, .3, 1) both;
  animation-delay: calc(var(--i, 0) * 32ms);
}
.gd-hand .gt-card:hover, .gd-hand .gt-card.is-sel { z-index: 5; }
/* 顺子弹出预览（v2.46.21）：点「顺子」按钮后整组弹起 + 金描边呼吸 1.2s，
   与选中态（is-sel 常驻上浮）区分：弹出是短暂的「看这一组」，钉住靠「挪左侧」按钮 */
.gd-hand .gt-card.is-seqpop {
  z-index: 6;
  animation: gd-seqpop 1.2s ease-out both;
}
@keyframes gd-seqpop {
  0% { transform: translateY(0); box-shadow: 0 2px 0 rgba(0, 0, 0, .22); }
  12% { transform: translateY(-18px) scale(1.06); }
  22% { transform: translateY(-14px) scale(1.03); }
  30%, 82% { transform: translateY(-14px); }
  100% { transform: translateY(0); }
}
.gd-hand .gt-card.is-seqpop::after {
  content: ''; position: absolute; inset: -3px; border-radius: 10px;
  border: 2px solid rgba(233, 200, 119, .95);
  box-shadow: 0 0 12px rgba(233, 200, 119, .5);
  animation: gd-seqpop-ring 1.2s ease-out both;
  pointer-events: none;
}
@keyframes gd-seqpop-ring {
  0% { opacity: 0; }
  15%, 82% { opacity: 1; }
  100% { opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .gd-hand .gt-card.is-seqpop { animation: none; transform: translateY(-14px); }
  .gd-hand .gt-card.is-seqpop::after { animation: none; }
}
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
/* v2.46.23 还贡选中态：金描边 + 轻微上浮，与「已选要出的牌」区分开（这里是待确认） */
.gd-return .gt-card.is-pick {
  transform: translateY(-10px);
  box-shadow: 0 0 0 2px var(--gt-gold, #e9c877), 0 10px 18px -8px rgba(0, 0, 0, .6);
  z-index: 5;
}
.gd-return-ok {
  margin-top: 8px; align-self: center; min-width: 148px;
}
.gd-return-ok:disabled { opacity: .45; }
.gd-return { display: flex; flex-direction: column; gap: 6px; padding: 6px 2px; }
.gd-return-tip { font-size: 12.5px; color: var(--gt-ink-dim, #b9b3a6); text-align: center; }
.gd-return-cards { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
/* 贡牌倒计时：服务端 5 分钟未选会自动代选一张，剩最后 1 分钟变红提醒 */
.gd-timer { color: var(--gt-gold); font-variant-numeric: tabular-nums; }
.gd-timer.urgent { color: #ff8f7d; }
.gd-return-tip .gd-timer { margin-left: 8px; font-weight: 700; }
/* 进贡/还贡横幅：跟在信息条下方，金框墨底，谁→谁（含贡牌）一眼可读 */
.gd-tribute-banner {
  display: flex; align-items: center; justify-content: center;
  flex-wrap: wrap; gap: 4px 14px;
  padding: 4px 12px; border-radius: 10px;
  background: color-mix(in srgb, var(--gt-gold, #c9a227) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--gt-gold, #c9a227) 38%, transparent);
  font-size: 12.5px; color: var(--gt-ink, #efe9db);
}
.gd-tb-title {
  font-weight: 800; color: var(--gt-gold, #c9a227);
  padding-right: 10px; border-right: 1px solid color-mix(in srgb, var(--gt-gold, #c9a227) 35%, transparent);
}
.gd-tb-item { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
.gd-tb-item.done { opacity: 0.62; }
.gd-tb-item.mine { color: var(--gt-gold, #c9a227); font-weight: 700; }
.gd-tb-card { font-style: normal; font-weight: 700; }
.gd-tb-card.red { color: #ff8f7d; }
.gd-tb-pending {
  font-style: normal; font-size: 11px; opacity: 0.75;
  border: 1px solid currentColor; border-radius: 999px; padding: 0 6px;
}
.gd-wait-host { margin: 8px 0 0; font-size: 12.5px; color: var(--gt-ink-dim, #b9b3a6); }

@media (max-width: 900px) {
  .gd { min-width: 860px; }
}

/* ===== 「不要」气泡（夜星：点不要后头像处弹小气泡，参考主流棋牌） ===== */
.gd-pass-bubble {
  position: absolute; left: 50%; top: -24px; transform: translateX(-50%);
  padding: 3px 10px; border-radius: 999px;
  background: rgba(28, 30, 34, .92); color: #f3efe4;
  font-size: 11.5px; font-weight: 700; letter-spacing: .08em;
  border: 1px solid rgba(233, 200, 119, .45);
  box-shadow: 0 4px 10px -4px rgba(0, 0, 0, .8);
  white-space: nowrap; pointer-events: none; z-index: 20;
}
.gd-pass-bubble::after {
  content: ''; position: absolute; left: 50%; bottom: -4px;
  width: 8px; height: 8px; transform: translateX(-50%) rotate(45deg);
  background: rgba(28, 30, 34, .92);
  border-right: 1px solid rgba(233, 200, 119, .45);
  border-bottom: 1px solid rgba(233, 200, 119, .45);
}
/* 我方的气泡挂在底部信息条上方（那一条没有 .gt-seat 的圆角胶囊壳，位置微调） */
.gd-bottom-bar { position: relative; }
.gd-pass-bubble-me { top: -30px; }
.gd-pop-enter-active, .gd-pop-leave-active { transition: opacity .18s ease, transform .18s ease; }
.gd-pop-enter-from, .gd-pop-leave-to {
  opacity: 0; transform: translateX(-50%) translateY(6px) scale(.82);
}

/* ===== 炸弹 / 同花顺 / 火箭特效（中央金圈炸开 + 全桌震动） ===== */
/* hit-stop（v2.46.20）：炸弹落地前 90ms 全桌定帧——微缩 + 压暗营造「吸气」，解冻瞬间爆开。
   动画冻结用 animation-play-state，金圈/大字本来就没启动，靠 JS 延迟 90ms 再挂。 */
.gd-table.is-freeze { transform: scale(.994); filter: brightness(.85); }
.gd-table.is-freeze * { animation-play-state: paused !important; }
.gd-table.is-shake { animation: gd-shake .55s cubic-bezier(.36, .07, .19, .97) both; }
@keyframes gd-shake {
  10%, 90% { transform: translate(-2px, 1px); }
  20%, 80% { transform: translate(3px, -2px); }
  30%, 50%, 70% { transform: translate(-5px, 2px); }
  40%, 60% { transform: translate(5px, -1px); }
}
.gd-bomb-fx {
  position: absolute; inset: 0; z-index: 40;
  display: grid; place-items: center; pointer-events: none;
}
.gd-bomb-fx b {
  font-size: clamp(28px, 6vw, 56px); font-weight: 900; letter-spacing: .12em;
  color: #ffd875;
  text-shadow: 0 0 24px rgba(255, 120, 40, .9), 0 2px 0 #7a2b00;
  animation: gd-bomb-pop .5s cubic-bezier(.2, 1.4, .4, 1) both;
}
.gd-bomb-ring {
  position: absolute; width: 170px; height: 170px; border-radius: 50%;
  border: 6px solid rgba(255, 190, 90, .9);
  box-shadow: 0 0 40px rgba(255, 140, 40, .55), inset 0 0 30px rgba(255, 140, 40, .35);
  animation: gd-bomb-ring .7s ease-out both;
}
@keyframes gd-bomb-ring {
  from { transform: scale(.2); opacity: 1; }
  to { transform: scale(2.6); opacity: 0; }
}
@keyframes gd-bomb-pop {
  0% { transform: scale(.3); opacity: 0; }
  55% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .gd-table.is-shake { animation: none; }
  .gd-table.is-freeze { transform: none; filter: none; }
  .gd-bomb-fx b, .gd-bomb-ring { animation-duration: .01s; }
}

/* ===== v2.46.19 体验增强 ===== */
/* 触感开关：关闭时按钮压暗 */
.gt-btn.is-off { opacity: .45; }

/* 升级进度条：两支细条（上=我方金、下=对方灰蓝），顶栏比分旁一眼看进度 */
.gd-lvbars {
  display: inline-flex; flex-direction: column; gap: 3px;
  padding: 4px 8px; border-radius: 8px;
  background: rgba(255, 255, 255, .05); border: 1px solid var(--gt-line);
}
.gd-lvbar {
  display: block; width: 52px; height: 4px; border-radius: 2px;
  background: rgba(255, 255, 255, .1); overflow: hidden;
}
.gd-lvbar i {
  display: block; height: 100%; border-radius: 2px;
  background: linear-gradient(90deg, rgba(233, 200, 119, .55), #e9c877);
  transition: width .6s cubic-bezier(.25, .6, .3, 1);
}
.gd-lvbar.op i { background: linear-gradient(90deg, rgba(140, 170, 200, .4), rgba(140, 170, 200, .85)); }

/* 报牌徽标（≤7 张）：席位上红底白字小胶囊，轮到自己时底部信息条也有 */
.gd-bao-badge {
  padding: 1px 7px; border-radius: 999px;
  font-size: 10.5px; font-weight: 700; line-height: 1.6;
  background: rgba(190, 60, 50, .88); color: #ffe9e2;
  border: 1px solid rgba(255, 190, 170, .5);
  white-space: nowrap;
}
.gd-bao-me {
  background: rgba(190, 60, 50, .88);
  border-color: rgba(255, 190, 170, .5);
  color: #ffe9e2; font-weight: 700;
}

/* 牌型名称浮现：中央放大字号再淡出；金底 = 炸弹 / 同花顺 / 火箭 */
.gd-pat-fx {
  position: absolute; left: 50%; top: 46%; transform: translate(-50%, -50%);
  z-index: 30; pointer-events: none;
  padding: 4px 20px; border-radius: 12px;
  background: rgba(0, 0, 0, .55); border: 1px solid rgba(233, 200, 119, .5);
  animation: gd-pat-pop .95s cubic-bezier(.2, .85, .3, 1) both;
}
.gd-pat-fx b {
  font-size: clamp(20px, 3.4vw, 34px); font-weight: 900; letter-spacing: .14em;
  color: var(--gt-gold); text-shadow: 0 2px 10px rgba(0, 0, 0, .8);
}
.gd-pat-fx.gold {
  background: linear-gradient(180deg, rgba(244, 220, 156, .96), rgba(217, 182, 95, .96));
  border-color: rgba(255, 255, 255, .5);
  box-shadow: 0 0 26px -4px rgba(233, 200, 119, .95);
}
.gd-pat-fx.gold b { color: #2a1d05; text-shadow: none; }
@keyframes gd-pat-pop {
  0% { opacity: 0; transform: translate(-50%, -30%) scale(.7); }
  22% { opacity: 1; transform: translate(-50%, -50%) scale(1.04); }
  32% { transform: translate(-50%, -50%) scale(1); }
  78% { opacity: 1; }
  100% { opacity: 0; transform: translate(-50%, -62%) scale(1); }
}
.gd-patfade-enter-active, .gd-patfade-leave-active { transition: opacity .15s ease; }
.gd-patfade-enter-from, .gd-patfade-leave-to { opacity: 0; }

/* 行动方聚焦：轮到别人时其余席位压暗降饱和；切换有 0.3s 过渡不生硬 */
.gd .gt-seat.is-idle {
  opacity: .58; filter: saturate(.55);
  transition: opacity .3s ease, filter .3s ease;
}
.gd .gt-seat { transition: opacity .3s ease, filter .3s ease; }

/* 队友标识：青蓝描环 + 右上角「友」小角标（对家/左右家都适用） */
.gd .gt-seat.is-mate { box-shadow: inset 0 0 0 1.5px rgba(96, 190, 255, .45); }
.gd .gt-seat.is-mate::after {
  content: '友';
  position: absolute; right: -6px; top: -7px;
  width: 16px; height: 16px; border-radius: 50%;
  display: grid; place-items: center;
  font-size: 9.5px; font-weight: 700; font-style: normal;
  background: rgba(70, 160, 235, .92); color: #eaf5ff;
  border: 1px solid rgba(255, 255, 255, .4);
}
/* gt-seat 需要 relative 才能挂角标（全局可能有定位，这里兜底声明） */
.gd .gt-seat { position: relative; }

/* 发牌错峰：新局手牌逐张从上方带角度落进（每张延迟 35ms） */
@keyframes gd-deal-in {
  0% { opacity: 0; transform: translateY(-34px) rotate(-7deg) scale(.92); }
  70% { opacity: 1; transform: translateY(2px) rotate(1deg) scale(1.01); }
  100% { opacity: 1; transform: none; }
}
.gd-hand .gt-card.gd-deal-in {
  animation: gd-deal-in .34s cubic-bezier(.2, .85, .3, 1) both;
  animation-delay: calc(var(--i, 0) * 35ms);
}
@media (prefers-reduced-motion: reduce) {
  .gd-pat-fx, .gd-hand .gt-card.gd-deal-in { animation: none !important; }
  .gd .gt-seat.is-idle { opacity: 1; filter: none; }
}
</style>

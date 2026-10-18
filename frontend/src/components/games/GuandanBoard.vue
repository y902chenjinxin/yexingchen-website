<template>
  <div class="gt-landscape gd-wrap">
    <div
      ref="rootRef"
      class="gt-shell gd"
      :class="{ 'is-big': big }"
      :style="{ '--gt-h': rootH + 'px', '--card-w': cardW + 'px', '--card-h': cardH + 'px' }"
    >
      <!-- ===== 顶栏（v2.46.72 横屏改版后只留标题与全局开关：
           级牌/比分/升级进度常驻左区，不再与顶栏重复） ===== -->
      <header class="gd-top">
        <span class="gt-title">掼蛋</span>
        <span class="gt-pill gold">主级 {{ G.levelText(roundLevel) }}</span>
        <span class="gt-spacer"></span>
        <button class="gt-btn sm ghost" :title="muted ? '取消静音' : '静音'" @click="toggleMute">
          {{ muted ? '🔇' : '🔊' }}
        </button>
        <button class="gt-btn sm ghost" :class="{ 'is-off': !hapticsOn }" :title="hapticsOn ? '关闭震动反馈' : '开启震动反馈'" @click="toggleHaptics">
          📳
        </button>
        <button class="gt-btn sm ghost" @click="doExit">退出对局</button>
      </header>

      <!-- ===== 牌桌：左区（左家+比分） / 顶部（对家+轮次条） / 中央四座位出牌区 / 右区（右家+记录入口）
           v2.46.72 横屏改版（夜星清单）：左右各 ~13% 玩家信息，中部大面积留白；
           出牌区按座位投影摆四家最近一手（povSeat 投影，座位号≠屏幕位置）；
           出牌记录收成右区入口按钮，打开时浮层盖在右区上，不占牌桌宽度。 ===== -->
      <div class="gd-table" ref="tableRef" :class="{ 'is-shake': tableShake, 'is-freeze': freeze }">
        <!-- 顶部：对家 + 全局「轮到谁出牌」提示条（先手提示从右家头上移到顶部中央，夜星） -->
        <div class="gd-zone gd-zone-top">
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
          <!-- v2.46.75：轮次条缩小（夜星）；级牌/局数信息已挪左区左上角 -->
          <span class="gd-turnbox" :class="{ 'is-me': turn === oSeat, 'is-done': turn < 0 }">
            <em>轮到</em>
            <b>{{ turn < 0 ? '本局结束' : seatName(turn) }}</b>
            <i>{{ isOnline && props.onlineView?.phase === 'return' ? '还贡' : '出牌' }}</i>
          </span>
        </div>

        <!-- 左区：比分+局数贴左上角（v2.46.75：主级胶囊删——与比分重复；局数从轮次条
             下挪来左上角，夜星）+ 左家席位贴桌底 -->
        <div class="gd-zone gd-zone-left">
          <span class="gd-score">
            <i class="me">我方 {{ G.levelText(myLevel) }}</i>
            <em>·</em>
            <i class="op">对方 {{ G.levelText(oppLevel) }}</i>
          </span>
          <span class="gd-round-info">第 {{ roundNo }} 局</span>
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
        </div>

        <!-- v2.46.76：记录按钮移左上角（比分/局数组之下，夜星） -->
        <button class="gt-btn ghost sm gd-hist-btn" @click="histOpen = !histOpen">
          记录<em v-if="history.length" class="gd-btn-count">{{ history.length }}</em>
        </button>

        <!-- 中央：四座位出牌区 —— 每家只显示最近一手（小尺寸+who 胶囊），大面积留白
             v2.46.90：矮桌（手机 rotate90 逻辑高 ~180）保持菱形摆位（上=对家 下=我
             左=左家 右=右家），仅牌缩 0.62 + 胶囊压扁；v2.46.89 的 2×2 错行
             在转屏后会叠成一条线（夜星截图），已废弃 -->
        <div class="gd-center" :class="{ 'is-low': lowTable }">
          <div v-for="pos in [0, 1, 2, 3]" :key="pos" class="gd-thz" :class="'gd-thz-' + pos">
            <template v-if="throwByPos[pos]">
              <span class="gd-thz-who">{{ seatName(throwByPos[pos].seat) }} · {{ G.PATTERN_NAME[throwByPos[pos].pattern?.type] || '出牌' }}</span>
              <div class="gd-thz-cards" :style="{ '--thz-scale': throwScale(throwByPos[pos].cards.length) }">
                <span
                  v-for="(c, i) in throwByPos[pos].cards"
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
              </div>
            </template>
          </div>

          <!-- 炸弹 / 同花顺 / 火箭：中央金圈炸开 + 大字，见 playFxFor -->
          <div v-if="bombFx" class="gd-bomb-fx" aria-hidden="true">
            <span class="gd-bomb-ring"></span>
            <b>炸弹！</b>
          </div>

          <!-- 牌型名称浮现（v2.46.19）：每手牌打出后中央短暂放大牌型名再淡出 -->
          <transition name="gd-patfade">
            <div v-if="patFx" class="gd-pat-fx" :class="{ gold: patFx.gold }" aria-hidden="true">
              <b>{{ patFx.name }}</b>
            </div>
          </transition>
        </div>

        <!-- 右区：右家（v2.46.76：记录入口已移左上角） -->
        <div class="gd-zone gd-zone-right">
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

        <!-- 出牌记录浮层：默认收起，打开时盖在右区上方，窗内滚动回看 -->
        <aside v-show="histOpen" class="gd-history" aria-label="出牌历史">
          <div class="gd-history-head">
            <span>出牌记录</span>
            <i>{{ history.length }}</i>
            <button
              class="gd-history-toggle"
              :aria-label="histOpen ? '收起出牌记录' : '展开出牌记录'"
              @click="histOpen = !histOpen"
            >{{ histOpen ? '收起' : '展开' }}</button>
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
              <template v-else-if="h.kind === 'tribute' || h.kind === 'return'">
                <span class="gd-his-seat">{{ seatName(h.seat) }}</span>
                <span class="gd-his-pat gold">{{ h.kind === 'tribute' ? '进贡' : '还贡' }}</span>
                <span class="gd-his-cards">
                  <i :class="{ red: isRed(h.card) }">{{ cardText(h.card) }}{{ cardSuit(h.card) }}</i>
                </span>
                <span class="gd-his-arrow">→ {{ seatName(h.to) }}</span>
              </template>
              <template v-else-if="h.kind === 'resist'">
                <span class="gd-his-pat gold">抗贡</span>
                <span class="gd-his-cards">头游 {{ seatName(h.leader) }} 直接出牌</span>
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
          <!-- v2.46.76：「你 · N 张」标签删（夜星：自己手牌自己可见，其余三家席位已有张数） -->
          <span class="gt-spacer"></span>
            <transition name="gd-pop">
              <span v-if="baoCount(viewSeat)" class="gd-mini gd-bao-me">报牌 {{ baoCount(viewSeat) }}</span>
            </transition>
            <transition name="gd-pop">
              <span v-if="passBubbles[viewSeat]" class="gd-pass-bubble gd-pass-bubble-me">不要</span>
            </transition>
            <!-- v2.46.72：级牌/比分移到左区常驻，这里不再重复（全屏顶栏收起也不丢信息） -->
          <span class="gt-spacer"></span>
          <span v-if="showCountdown" class="gd-mini gd-timer" :class="{ urgent: leftSec <= 60 }">
            ⏳ 贡牌剩余 {{ mmss(leftSec) }}
          </span>
          <!-- v2.46.76：「可出 N」删（夜星：与选牌识别/轮次条重合）；statusLine 为空时不占位 -->
          <span v-if="sel.length" class="gd-mini" :class="{ on: sel.length }">已选 {{ sel.length }}</span>
          <span v-if="statusLine" class="gt-sub gd-status">{{ statusLine }}</span>
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

        <!-- v2.46.114：抗贡横幅——后端 new_game 抗贡时写 kind='resist' 的 history 条目才可见。
             此前后端只写 log：tribute 横幅要 phase∈[tribute,return]、抗贡时 phase='playing'，
             状态栏/记录同样查不到 → 用户看到「赢了但对面没进贡」以为逻辑丢了（夜星报障）。
             与上方进贡横幅同款样式，独立显隐 6s。 -->
        <div v-if="resistBanner" class="gd-tribute-banner" aria-live="polite">
          <span class="gd-tb-title">抗贡</span>
          <span class="gd-tb-item">
            进贡方合计两张大王（大小王不算）· 抗贡成立，由头游 {{ seatName(resistLeader) }} 直接出牌
          </span>
        </div>

        <!-- 手牌上方工具条（v2.46.72）：提示（左）· 挪左 · 选牌自动识别牌型（中） · 挪右 · 重选（右）。
             同花顺/顺子不再单独占按钮——选完牌中央标签直接报牌型（识别优先级见 detectPattern）；
             挪左/挪右收成手牌上方边缘小按钮，不占核心操作区（夜星清单）。 -->
        <div class="gd-hand-tools" v-if="!tributePending && !returnPending">
          <button class="gt-btn ghost sm" :disabled="!canAct" @click="doHint">提示</button>
          <button
            class="gt-btn ghost sm gd-pin"
            :disabled="!seqGroups.length && !sel.length"
            :title="seqGroups.length || sel.length ? '把选中的牌（未选则第一组顺子）钉到最左' : '先选牌，再挪到左侧'"
            @click="pinSeqToLeft"
          >挪左</button>
          <span class="gd-pat-label" :class="{ ok: selPattern && canPlay, bad: selPattern && !canPlay }" aria-live="polite">
            <template v-if="selPattern">{{ G.PATTERN_NAME[selPattern.type] }}<i v-if="!canPlay && canAct"> · 压不过</i></template>
          </span>
          <button
            class="gt-btn ghost sm gd-pin"
            :disabled="!sel.length"
            :title="sel.length ? '把选中的牌插回散牌区，落在第一张比它小的牌左边（成组不拆）' : '先选牌，再挪到右侧'"
            @click="pinToRight"
          >挪右</button>
          <button class="gt-btn ghost sm" :disabled="!sel.length" @click="clearSel">重选</button>
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
          <button class="gt-btn gd-return-ok" :disabled="returnSel == null" @click="confirmReturn">
            还贡{{ returnSelCard ? ` ${cardText(returnSelCard)}${cardSuit(returnSelCard)}` : '' }}
          </button>
        </div>

        <!-- 手牌区（v2.46.72）：占宽 80% 靠底居中、弧形叠放（只露左上角花色数字）、
             去底部多余横线；「不要 / 出牌」做成左下/右下浮动大按钮（毛玻璃/鎏金），
             不单独占一行——省下的高度全给手牌。 -->
        <div class="gd-hand-zone">
          <div
            class="gd-hand"
            ref="handRef"
            :class="{ 'is-up': upHint }"
            :style="{ '--gd-overlap': overlap + 'px' }"
            @pointerdown="onHandDown"
          >
            <template v-for="(c, i) in viewHand" :key="c.id">
              <!-- 分区线（v2.46.24）：左钉区|散牌区 之间画一道竖线，
                   理好的牌和散牌一眼分开（夜星：「现在都展示在一块，很乱」） -->
              <i
                v-if="headCount > 0 && i === headCount"
                class="gd-hand-divider"
                aria-hidden="true"
              ></i>
              <span
                class="gt-card"
                :class="cardCls(c, i)"
                :style="{ '--i': i, ...(fanStyle(i) || {}) }"
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
        </div>
        <!-- 大按钮挂在 footer 两角（手牌 80% 区之外），不压两端手牌的热区 -->
        <template v-if="!tributePending && !returnPending">
          <button class="gt-btn gd-big gd-pass-big" :disabled="!canAct || !target" @click="doPass">不要</button>
          <button class="gt-btn gd-big gd-play-big" :disabled="!canAct || !canPlay" @click="doPlay">出牌</button>
        </template>
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
import { speak, speakPass } from '@/utils/games/tts'
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
/** 四座位出牌区（v2.46.72 横屏改版）：按座位投影摆到对家上/左家左/右家右/自己下
 *  （screenPos 走 povSeat，座位号≠屏幕位置）。
 *  v2.46.114（夜星）：**只展示最新一家出牌**——下一人出牌后上一人的牌收起，
 *  四家同显在一圈里互相压牌（尤其横屏矮桌上下两家必叠）。新一圈开始
 *  （领出者再次领出 / target 清空 / 新一局）即 clearThrows 整体清空留白。 */
const seatThrows = ref({})
function setThrow(seat, h) { seatThrows.value = { [seat]: h } }
function clearThrows() { seatThrows.value = {} }
const throwByPos = computed(() => {
  const m = {}
  for (const [s, h] of Object.entries(seatThrows.value)) {
    const pos = screenPos(Number(s))
    if (!(pos in m)) m[pos] = h
  }
  return m
})
/** v2.46.114：出牌张数越多、牌越小——一行排爆出牌区会横向溢出中央区
 *  （横屏 852 逻辑宽尚可，竖屏 rotate90 逻辑宽仅 ~390，12 张连对/顺子必超）。
 *  缩放经 CSS 变量 --thz-scale 乘到 .gd-thz 的 gt-card 宽高上。 */
function throwScale(n) {
  if (n >= 12) return 0.5
  if (n >= 10) return 0.6
  if (n >= 8) return 0.7
  if (n >= 6) return 0.8
  if (n >= 5) return 0.9
  return 1
}
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

/** 手牌展示顺序：[左区（钉组/同花顺组）| 散牌区]，区间画分隔线。
 *  v2.46.67（夜星四点）左区规则重写：
 *  1) **手动优先**——「挪右侧」过的牌绝不被自动同花顺拉回左区，直到再点「挪左侧」；
 *  2) 左区**按组展示不混排**——钉的组保持独立、天然同花顺一组一张，组内升序、
 *     组间按组内最大牌从大到小排，只排序不加分隔（不再把相同牌汇总到一起）；
 *  3) 天然同花顺（不含逢人配凑的）从大到小**贪心取互不重叠的 5 张组**：同花 6~9 张
 *     只取最大的 5 张进左区、剩余回散牌区；同花 10 张能拆两组就自动拆成两组。
 *  顺子仍手动（点「顺子」弹出预览 → 「挪左侧」钉住）。
 *  「挪右侧」v2.46.39 重定义（夜星）：把选中的这组牌**插回散牌区**；v2.46.85 起
 *  组内从大到小逐张归位；v2.46.86 起——只要存在挪右的牌，整手按牌值降序排成一条
 *  continuum，组合（顺子/三张）逐张拆开并入全局排序（夜星：顺子向右挪移需要拆开）。
 *  每组记 id，出掉自动失效，新局自然清空。 */
const pinnedGroups = ref([]) // 每项 = 一次「挪左侧」钉住的 ids 数组，按操作顺序
const rightDocks = ref([]) // 每项 { ids: [...] }，按操作顺序依次插入
const handParts = computed(() => {
  const base = isOnline.value ? (props.onlineView?.me?.hand || []) : (hands.value[viewSeat.value] || [])
  if (phase.value === 'settled' || !base.length) return { head: base, mid: [], tail: [] }
  const inBase = new Set(base.map(c => c.id))
  const val = c => G.cardValue(c, roundLevel.value)
  const asc = (a, b) => val(a) - val(b)
  /* ① 手动挪右最优先：dock 组的牌不进左区（旧版 dock 撞上同花顺会让位给头区——
     这就是「同花顺不支持手动向右移动」的根源） */
  const docks = rightDocks.value
    .map(d => ({ ids: d.ids.filter(id => inBase.has(id)) }))
    .filter(d => d.ids.length)
  const dockIds = new Set()
  for (const d of docks) for (const id of d.ids) dockIds.add(id)
  /* ② 手动钉的左区组（按钉的顺序；与 dock 撞牌的让位——挪右是更新的操作） */
  const pinGroups = pinnedGroups.value
    .map(g => g.filter(id => inBase.has(id) && !dockIds.has(id)))
    .filter(g => g.length)
  const pinnedIds = new Set(pinGroups.flat())
  /* ③ 天然同花顺：从大到小贪心取互不重叠的 5 张组。旧版把所有滑窗组合取并集——
     6 张同花 6 张全进左区还跟别的组交叉混排；现在只取最大 5 张，剩余回散牌区 */
  const naturals = base.filter(c => !G.isWild(c, roundLevel.value) && !pinnedIds.has(c.id) && !dockIds.has(c.id))
  const flushGroups = []
  const usedF = new Set()
  for (const cs of G.findFlushBombs(naturals, roundLevel.value)) {
    if (cs.some(c => usedF.has(c.id))) continue
    flushGroups.push(cs)
    for (const c of cs) usedF.add(c.id)
  }
  if (!pinGroups.length && !flushGroups.length && !docks.length) return { head: [], mid: base, tail: [] }
  // v2.46.86：只要存在「挪右」的牌，就进入"按大小全排序"模式——整手按牌值降序排成
  // 一条 continuum，挪右的牌逐张落到各自牌值位置。顺子/三张等组合在此被拆开、并入全局
  // 排序（夜星：顺子向右挪移时需要拆开），不再保留左区分组，彻底解决"小牌靠前、大牌靠右"。
  // v2.46.89：挪左钉组优先级最高——旧版这里直接 return { head: [] }，只要这手牌
  // 之前用过一次「挪右」（rightDocks 整手常驻），之后点「挪左」钉的组就被整个丢弃，
  // 只弹「已挪到左侧」提示、牌面纹丝不动（夜星截图复现）。现在钉组照常进左区，
  // 其余牌（含同花顺）按 continuum 归位，挪右语义不变。
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
    return { head, mid: seq, tail: [] }
  }
  /* ④ 左区 = 钉组 + 同花顺组：组内升序、组间按组内最大牌降序，整组拼接不互混 */
  const groups = [
    ...pinGroups.map(ids => base.filter(c => ids.includes(c.id)).sort(asc)),
    ...flushGroups.map(cs => cs.slice().sort(asc)),
  ].sort((a, b) => Math.max(...b.map(val)) - Math.max(...a.map(val)))
  const head = groups.flat()
  const usedL = new Set(head.map(c => c.id))
  let mid = base
    .filter(c => !usedL.has(c.id) && !dockIds.has(c.id))
    .sort((a, b) => val(b) - val(a))
  return { head, mid, tail: [] }
})
const viewHand = computed(() => {
  const p = handParts.value
  return p.head.concat(p.mid, p.tail)
})
/** 手牌分隔线位置：headCount>0 时在 head|mid 之间画线（v2.46.67 起 tail 恒空，不再有第二道线） */
const headCount = computed(() => handParts.value.head.length)
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
  // v2.46.76：「本轮由你先出牌」删（与顶部轮次条重合，夜星）
  return target.value ? '请压过上一手，或选择「不要」' : ''
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

/* ---------- 顺子组：供「挪左」在未选中时兜底钉第一组（v2.46.72 起同花顺/顺子
 *  不再单独占按钮——选牌后中央标签自动报牌型，归集动作只剩挪左/挪右两个小按钮） ---------- */
const seqGroups = computed(() => G.findSeqGroups(viewHand.value, roundLevel.value))
/** 「挪左侧」（v2.46.21）：把当前选中的牌钉到最左（配合顺子按钮弹出后使用）；
 *  没有选中时退而钉第一组顺子。钉住持久：出掉对应牌 id 自动失效，新局换新牌自然清空。
 *  v2.46.39：与「挪右侧」仍然互斥——挪左先解除该组的右侧归位 dock。 */
/** 「挪左侧」（v2.46.21）：把当前选中的牌钉到最左（配合顺子按钮弹出后使用）；
 *  没有选中时退而钉第一组顺子。钉住持久：出掉对应牌 id 自动失效，新局换新牌自然清空。
 *  v2.46.67：改为**按组**记录（保持钉的顺序，左区整组展示不与别的牌混排）；
 *  与「挪右侧」仍然互斥——挪左先解除该组的右侧归位 dock。 */
function pinSeqToLeft() {
  let ids = sel.value.slice()
  if (!ids.length) {
    if (!seqGroups.value.length) { toastMsg('手上没有顺子'); return }
    ids = seqGroups.value[0].map(c => c.id)
  }
  const rest = pinnedGroups.value
    .map(g => g.filter(id => !ids.includes(id)))
    .filter(g => g.length)
  pinnedGroups.value = [...rest, ids]
  if (rightDocks.value.length) {
    rightDocks.value = rightDocks.value
      .map(d => ({ ids: d.ids.filter(id => !ids.includes(id)) }))
      .filter(d => d.ids.length)
  }
  toastMsg('已挪到左侧')
  sfx.pick()
}
/** 「挪右侧」（v2.46.39 重定义，夜星）：把选中的牌**按牌值归位**到整手降序序列——
 *  v2.46.86 起，只要存在挪右的牌，整手即按大小排成一条 continuum（顺子等组合被拆开）。
 *  已在位的组再点一次位置不变。与「挪左侧」互斥：挪右先解除左钉。 */
function pinToRight() {
  const ids = sel.value.slice()
  if (!ids.length) { toastMsg('先选牌，再点「挪右侧」'); return }
  // 先从旧 dock 组里摘掉（重复挪 = 重新计算插入点）
  const rest = rightDocks.value
    .map(d => ({ ids: d.ids.filter(id => !ids.includes(id)) }))
    .filter(d => d.ids.length)
  rightDocks.value = [...rest, { ids }]
  // v2.46.67：挪右解除左钉（按组过滤）——dock 优先于自动同花顺与左钉
  if (pinnedGroups.value.length) {
    pinnedGroups.value = pinnedGroups.value
      .map(g => g.filter(id => !ids.includes(id)))
      .filter(g => g.length)
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
  // v2.46.114：抗贡可见化——后端 new_game 抗贡时写 kind='resist' 的 history 条目
  // （此前只写 log，横幅/状态栏/记录三通道全瞎，用户看到「赢了但对面没进贡」
  // 以为逻辑丢了，夜星报障）。无飞牌（没人递牌），横幅 6s + toast + 抽屉记录。
  for (let i = 0; i < list.length; i++) {
    const h = list[i]
    if (h.kind !== 'resist') continue
    const k = `resist:${h.leader}:${i}`
    if (seenResist.has(k)) continue
    seenResist.add(k)
    showResist(h.leader)
  }
}, { deep: true })

/* v2.46.114：抗贡横幅（与 gd-tribute-banner 同款样式，独立显隐） */
const resistBanner = ref(false)
const resistLeader = ref(null)
const seenResist = new Set()
let resistTimer = null
function showResist(leader) {
  resistLeader.value = leader
  resistBanner.value = true
  toastMsg(`抗贡成立：进贡方合计两张大王，不进不还，由头游 ${seatName(leader)} 直接出牌`, 4200)
  clearTimeout(resistTimer)
  resistTimer = setTimeout(() => { resistBanner.value = false }, 6000)
}

/* ---------- 手牌自适应重叠（一屏展示全，不滑动） ---------- */
const handRef = ref(null)
const handW = ref(0)
let ro = null
/* v2.46.89：矮桌检测——牌桌高度不足时中央出牌区切 2×2 对角摆位（防上下两家压牌）。
   手机 rotate90 兜底下壳逻辑高只有 ~390，牌桌被手牌/工具条挤到 ~140-190px，
   上下两家出牌区（各 ~85px 高）必然重叠；桌面（≥720 高）不受影响 */
const tableRef = ref(null)
const lowTable = ref(false)
function measureTable() {
  if (tableRef.value) lowTable.value = tableRef.value.clientHeight < 230
}
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
  // clientWidth 含左右内边距，扣掉才是真正可摆牌的内容宽
  // v2.46.73 左右内边距 4px→80px（夜星确认的外部 UI 方案），故 -160-8
  if (handRef.value) handW.value = handRef.value.clientWidth - 168
}

/* ---------- 手牌弧形叠放（v2.46.72，v2.46.73 弧度收敛）----------
 * 每张牌按索引算扇形角 --fa（度）与抬升 --fy（px）：中间高、两端低、微外旋。
 * v2.46.73 按外部 UI 评审把总弧度压到 14° 内（27 张满手单牌 ±7°）、
 * 抬升收到 10px——牌身更正、角标数字更可读，仍保留一点持牌感。
 * 选中上浮走全局 .is-sel（在 --fy 基础上再抬），两者都是独立 transform 属性，可叠加。 */
function fanStyle(i) {
  const n = viewHand.value.length
  if (n < 3) return null
  const half = (n - 1) / 2
  const t = (i - half) / half          // -1（最左）… 1（最右）
  const maxDeg = Math.min(7, 1.6 + n * 0.2)
  const arcH = Math.min(10, 2 + n * 0.3)
  return {
    '--fa': (t * maxDeg).toFixed(2),
    '--fy': (-(1 - t * t) * arcH).toFixed(2),
  }
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
  if (t === 'pair') return `对${ttsRank(main[0] || cards[0])}`
  if (t === 'triple') return `三个${ttsRank(main[0] || cards[0])}`
  if (t === 'triple2') {
    const kick = gs[1]
    return `三个${ttsRank(main[0] || cards[0])}，带对${kick ? ttsRank(kick[0]) : ''}`
  }
  if (t === 'bomb') return `炸！${TTS_COUNT[Math.min(cards.length, 6)] || ''}${ttsRank(main[0] || cards[0])}`
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
  if (say) speak(say, p.seat)   // v2.46.28：按座位分声，一人一声
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
/* v2.46.114：上限 60 → 200（夜星：超过 60 次不再记录、牌桌也不展示）。
 * 后端 view() 同步放宽到最近 200 条、引擎 _history 上限 200。 */
function pushHistory(item) {
  history.value.unshift(item)
  if (history.value.length > 200) history.value.length = 200
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
  let prevTargetSeat = target.value?.seat
  target.value = normPlay(v.target)
  lastPlay.value = normPlay(v.last_play)
  // 一圈结束（target 清空）或开局 → 四座位出牌区整体清空留白（V24672）
  if (!v.target) clearThrows()
  // 服务端 history 按时间正序，取最新在前；增量部分里最后一条是 pass → 弹「不要」气泡
  const hist = v.history || []
  if (hist.length !== onlineHistLen.value) {
    if (hist.length < onlineHistLen.value) startDealWave()   // 历史变短 = 新一局发牌
    if (hist.length > onlineHistLen.value) {
      const lastEv = hist[hist.length - 1]
      if (lastEv && lastEv.kind === 'pass') {
        showPassBubble(lastEv.seat)
        speakPass(lastEv.seat)   // v2.46.26：在线「不要」补语音（夜星：没有合成音）
      }
      // 四座位出牌区：把本轮增量里的出牌逐条落位（轮询批量到达也不漏）
      for (const ev of hist.slice(onlineHistLen.value)) {
        if (ev.kind !== 'play') continue
        if (ev.seat === prevTargetSeat) clearThrows()   // 领出者再次领出 = 新一圈
        prevTargetSeat = ev.seat
        setThrow(ev.seat, normPlay(ev))
      }
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
  clearThrows()
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
      clearThrows()   // 一圈结束，中央出牌区清空留白（V24672）
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
  // 四座位出牌区：领出者再次领出 = 新一圈，先清掉上一圈的牌（V24672）
  if (target.value?.seat === seat) clearThrows()
  setThrow(seat, { seat, cards, pattern: pat })
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
  speakPass(seat)   // v2.46.26：本地「不要」补语音（随机台词池）
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
const AI_THINK_MIN = 3000
const AI_THINK_MAX = 3500
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
  // v2.46.31：pressure=对手最少剩牌（封堵用）+ 记牌（全场最大剩余单张优先甩）
  const oppMin = Math.min(...[0, 1, 2, 3].filter(o => G.TEAM_OF[o] !== G.TEAM_OF[s] && hands.value[o].length).map(o => hands.value[o].length), 99)
  const hiSingle = G.highestRemainingSingle(hands.value[s], roundLevel.value, history.value)
  const pick = G.aiChoose(hands.value[s], tgt?.pattern ?? null, roundLevel.value, { lastIsTeammate, pressure: oppMin, highestSingle: hiSingle })
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
  /* v2.46.36：理牌选牌不再限自己回合——攒顺子/挪牌随时可做（夜星）。
     出牌入口仍有 canAct 把守（按钮 disabled + swipeUpPlay/doPlay 校验），不会误出。 */
  if (tributePending.value || returnPending.value) return
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
  /* v2.46.36：划选理牌同样不限回合（与 onPick 同 gate）；上滑出牌由 swipeUpPlay 的 canAct 校验兜底 */
  if (tributePending.value || returnPending.value) return
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
  sfx.preload() // v2.46.41 预热采样，消掉第一次出牌的取包延迟
  if (typeof ResizeObserver !== 'undefined' && handRef.value) {
    ro = new ResizeObserver(() => { measureHand(); measureTable() })
    ro.observe(handRef.value)
    if (tableRef.value) ro.observe(tableRef.value)
  }
  measureHand()
  measureTable()
  // 壳高度就位后再测一次（首帧 --gt-h 可能尚未写入，牌桌真实高度晚一拍）
  requestAnimationFrame(measureTable)
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
  clearInterval(tickTimer)
  if (ro) ro.disconnect()
  // 划选期间被卸载：window 上的手势监听必须摘掉，否则残留到下一个页面
  window.removeEventListener('pointermove', onHandMove)
  window.removeEventListener('pointerup', onHandUp)
  window.removeEventListener('pointercancel', onHandUp)
})
watch(() => props.deadlineAt, tickLeft)
// v2.46.36 本地双人：视角座位随回合在两位玩家间切换，切走时清掉上一个视角的选牌，
// 防止 A 攒的选中串到 B 的手牌上（在线模式 viewSeat 恒为自己，不受影响）
watch(viewSeat, () => { sel.value = []; anchorIdx.value = null })
// 手牌张数一变（发牌 / 出牌 / 换局）→ 重测手牌宽度（重叠度自适应）；顺子「挪左」是手动钉住，不清
watch(() => viewHand.value.length, () => {
  requestAnimationFrame(measureHand)
})
// 新一局（settled → playing）清掉上一局钉住的顺子与右侧归位组；同局内打出后 id 自动失效
watch(phase, (p, old) => {
  if (p === 'playing' && old === 'settled') {
    pinnedGroups.value = []
    rightDocks.value = []
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
/* 全屏时顶栏让位给牌桌：收起顶栏（级牌/比分常驻左区，信息不丢） */
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
/* ===== v2.46.72 横屏布局（夜星清单）：grid 四区 =====
   左右各 ~13% 放玩家信息，顶部对家+轮次条，中央大面积留白给出牌区。
   旧版 flex 三列把左右家挤在中央两侧、记录占掉一整条竖栏 —— 中部没有留白。 */
.gd-table {
  position: relative;
  flex: 1; min-height: 0;
  display: grid;
  grid-template-columns: minmax(92px, 13%) 1fr minmax(92px, 13%);
  grid-template-rows: auto minmax(0, 1fr);
  gap: 6px;
  padding: 8px;
  /* v2.46.89：桌面全出血——旧版在壳内再画一层更暗的圆角矩形绒布，牌桌被
     「限制在一个矩形框里」（夜星截图）。壳 .gt-shell 本身已有全幅绒布+织物纹理
     +暗角（game-table.css），这里全部透出即可，出牌面积即整个牌屏 */
  background: none;
  box-shadow: none;
  border-radius: 0;
}
/* v2.46.75：桌沿鎏金镶线矩形已删（夜星：矩形框框住对家/左家/右家很怪）——
   桌面质感由绒布渐变 + 内圈暗角承担，不再画框 */
/* 四个信息区：贴边固定，中间留白（夜星：所有头像/牌数对齐屏幕边缘固定位置） */
.gd-zone { display: flex; min-width: 0; min-height: 0; }
.gd-zone-top {
  grid-column: 2; grid-row: 1;
  align-items: center; justify-content: center; gap: 10px;
}
.gd-zone-left, .gd-zone-right {
  flex-direction: column; align-items: center; justify-content: center; gap: 6px;
}
.gd-zone-left { grid-column: 1; grid-row: 2; justify-content: flex-end; padding-bottom: 2px; }
.gd-zone-right { grid-column: 3; grid-row: 2; }
/* v2.46.74：比分改绝对定位**左上角组**（夜星：比分放左上角）——
   全屏 720×360 时牌桌只剩 ~100px 高，纵排三件套必然溢出桌沿；
   拆成「左上角信息组 + 席位贴桌底」两段后互不相撞
   v2.46.75：主级胶囊删，组内只剩比分 + 「第 N 局」（.gd-round-info） */
.gd-zone-left .gd-score { position: absolute; left: 12px; top: 8px; z-index: 4; }
/* v2.46.76：记录按钮移左上角（比分 top8 / 第N局 top34 之下），不再占右区 */
.gd-hist-btn {
  position: absolute; left: 12px; top: 58px; z-index: 4;
  opacity: .85;
}

/* 左区比分/进度条纵向排布，尺寸压紧（左区只有 ~92px，字号/内边距都要收） */
.gd-zone-left .gd-score { font-size: 10.5px; padding: 2px 6px; gap: 4px; white-space: nowrap; }

/* 轮到谁出牌：顶部中央全局提示条，常驻。轮到自己时金底高亮（一眼看出该我动了）
   v2.46.75：整体缩小一档（夜星：小一点），不再压顶部视野 */
.gd-turnbox {
  display: inline-flex; align-items: baseline; gap: 4px;
  padding: 2px 9px; border-radius: 999px;
  background: rgba(0, 0, 0, .42);
  border: 1px solid rgba(233, 200, 119, .45);
  box-shadow: 0 0 18px -7px rgba(233, 200, 119, .55);
  white-space: nowrap;
}
.gd-turnbox em, .gd-turnbox i { font-style: normal; font-size: 10px; color: var(--gt-ink-dim); }
.gd-turnbox b { font-size: 12.5px; font-weight: 700; color: var(--gt-gold); letter-spacing: .02em; }
.gd-turnbox.is-me {
  background: linear-gradient(180deg, rgba(244, 220, 156, .96), rgba(217, 182, 95, .96));
  border-color: rgba(255, 255, 255, .5);
  box-shadow: 0 0 22px -4px rgba(233, 200, 119, .95);
}
.gd-turnbox.is-me b, .gd-turnbox.is-me em, .gd-turnbox.is-me i { color: #2a1d05; }
.gd-turnbox.is-done { opacity: .55; }
/* v2.46.75：「第 N 局」从轮次条下挪到左区左上角（比分下方，绝对定位同组） */
.gd-round-info {
  position: absolute; left: 12px; top: 34px; z-index: 4;
  font-size: 11px; letter-spacing: .04em; white-space: nowrap;
  color: var(--gt-ink-dim); text-shadow: 0 1px 2px rgba(0, 0, 0, .45);
}

/* 中央出牌区：四座位方位浮层（v2.46.72）—— 不再是一个盒子，直接在牌桌留白上摆。
   每家只显示本圈最近一手：who 胶囊（谁 · 牌型）+ 小尺寸牌行；
   位置按 screenPos（povSeat 投影）固定：0=下(我) 1=右 2=上 3=左。 */
.gd-center { position: relative; grid-column: 2; grid-row: 2; min-width: 0; min-height: 0; }
.gd-thz {
  position: absolute; display: flex; flex-direction: column; align-items: center; gap: 3px;
  max-width: 100%; pointer-events: none;
}
/* v2.46.73：改固定像素定位（外部 UI 方案）——百分比在窄板上贴得太近，
   固定 12px 保证四家牌行永远离桌沿/信息面板一拳远，互不重叠
   v2.46.89：我方（pos0）pill 移到牌行下方（贴手牌一侧）、对家（pos2）贴顶——
   中轴上两家的牌行各让出 ~21px，矮桌里不易相撞 */
.gd-thz-0 { bottom: 2px; left: 50%; transform: translateX(-50%); flex-direction: column-reverse; }   /* 我：贴底（夜星：别跟对家挤，往手牌侧压） */
.gd-thz-1 { right: 12px; top: 50%; transform: translateY(-50%); }     /* 右家 */
.gd-thz-2 { top: 6px; left: 50%; transform: translateX(-50%); }       /* 对家 */
.gd-thz-3 { left: 12px; top: 50%; transform: translateY(-50%); }      /* 左家 */
.gd-thz-who {
  font-size: 10.5px; line-height: 1.7; white-space: nowrap;
  padding: 0 9px; border-radius: 999px;
  color: var(--gt-ink-dim); background: rgba(0, 0, 0, .38);
  border: none;
}
.gd-thz-cards { display: flex; gap: 3px; justify-content: center; min-width: 0; }
/* 出牌区的牌缩到 0.78 倍：四家同屏不互相顶，牌型仍可辨（who 胶囊兜底语义）
   v2.46.114：再乘 --thz-scale（张数越多越小，防一行排爆出牌区，见 throwScale） */
.gd-thz .gt-card { width: calc(var(--card-w, 62px) * 0.78 * var(--thz-scale, 1)); height: calc(var(--card-h, 88px) * 0.78 * var(--thz-scale, 1)); }
.gd-thz .gt-card .c-mid { font-size: calc(var(--card-w, 62px) * 0.4 * var(--thz-scale, 1)); }
/* 左右家的牌行靠桌沿一侧对齐，避免挤进中央 */
.gd-thz-1 { align-items: flex-end; }
.gd-thz-3 { align-items: flex-start; }

/* ===== v2.46.90 矮桌摆位：保持菱形（v2.46.89 的 2×2 错行已废弃）=====
   v2.46.89 把左家/我方/右家全钉逻辑 bottom——但 CSS top/bottom 是逻辑坐标，
   rotate90 竖屏兜底后三家在屏幕上叠成一条线（夜星：出牌像展示一排）。
   现在四家各钉自己的方位（上=对家 下=我 左=左家 右=右家），转屏前后都是菱形；
   矮桌只把牌缩到 0.62、who 胶囊压扁，保证 ~120px 的中央区竖向放得下两行。 */
.gd-center.is-low .gd-thz-0 { bottom: 2px; left: 50%; transform: translateX(-50%); }
.gd-center.is-low .gd-thz-1 { right: 6px; top: 50%; transform: translateY(-50%); }
.gd-center.is-low .gd-thz-2 { top: 2px; left: 50%; transform: translateX(-50%); }
.gd-center.is-low .gd-thz-3 { left: 6px; top: 50%; transform: translateY(-50%); }
.gd-center.is-low .gd-thz { gap: 2px; }
.gd-center.is-low .gd-thz-who { font-size: 10px; line-height: 1.4; padding: 0 8px; }
.gd-center.is-low .gd-thz .gt-card { width: calc(var(--card-w, 62px) * 0.62 * var(--thz-scale, 1)); height: calc(var(--card-h, 88px) * 0.62 * var(--thz-scale, 1)); }
.gd-center.is-low .gd-thz .gt-card .c-mid { font-size: calc(var(--card-w, 62px) * 0.32 * var(--thz-scale, 1)); }

/* ===== v2.46.114 撤销 v2.46.92 横屏悬垂（出牌压牌根因）=====
   旧方案：我方出牌 bottom:-48px 悬垂到工具条上方 + .gd-hand-tools margin-top:48px 让位。
   实测两个 bug 叠加导致「出牌区压在工具条与手牌之间」（夜星截图）：
   ① .gd-hand-tools 基础规则（margin: 0 auto）写在媒体查询**之后**，同特异性后者胜出，
     margin-top:48px 从未生效（探针实测 computed 0px）；
   ② v2.46.114 起牌桌只展示最新一家出牌（setThrow 只留最新一手），上下两家不再同显，
     贴底 bottom:2px 足矣，无需悬垂——悬垂反而挤占工具条与手牌之间仅有的空间。
   探针实测（852×393）：贴底后出牌区 y117-177、工具条 y210、手牌 y245，间隙 33px。 */

/* ===== v2.46.93/95 手机竖屏 rotate90 兜底：我方出牌垂到挪左/挪右按钮行正中间 =====
   竖屏 rotate90 下中央区逻辑高仅 ~116px，对家（贴顶下垂 ~65px）+ 我方（贴底）
   两行出牌必叠（v2.46.92 的 landscape 媒体查询在竖屏设备上根本不命中，夜星截图
   复现）。按夜星拍板的兜底方案：我方出牌整组悬垂出中央区底边，牌行落在挪左/
   挪右按钮行的竖直中点。注意 rotate90 下 local bottom 偏移映射到屏幕 **横向**：
   -76px 时牌行 x145 与手牌列（右缘 ~149）碰触（v2.46.94 收到 -62 留 10px）；
   v2.46.95 按夜星要求空隙加到 20px → -48px，牌行 x169-173 起（探针双跑均值），
   y 中点 426 仍与按钮行中点严格对齐；胶囊翻回正常顺序贴桌沿。横屏走上面的
   v2.46.92 规则，桌面大屏不受影响。 */
@media (orientation: portrait) {
  .gd-center.is-low .gd-thz-0 {
    bottom: -48px;
    flex-direction: column; /* 覆盖基法的 column-reverse：胶囊贴桌沿、牌行落按钮中点 */
    z-index: 3;             /* 悬垂部分压过 .gd-bottom 的透明容器，防止被后绘制的底区盖住 */
  }
}

/* 出牌记录：浮层（v2.46.72 收进右区入口，打开时盖在右区上方，不占牌桌宽度）
   旧版是右侧真竖栏（更早以前是 absolute 浮层压左家）—— 改版后中央要留白，
   记录是低频回看，收成按钮 + 按需浮层最合适。 */
.gd-history {
  position: absolute; right: 10px; top: 10px; z-index: 30;
  width: 216px; max-height: calc(100% - 20px); min-height: 0;
  display: flex; flex-direction: column; gap: 6px;
  border-radius: 12px; padding: 7px 6px 7px 8px;
  background: rgba(6, 18, 26, .88); border: 1px solid var(--gt-line);
  box-shadow: 0 14px 34px -14px rgba(0, 0, 0, .9);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
}
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
  .gd-thz-cards > .gt-card { animation: none !important; }
}

/* 底部手牌 */
.gd-bottom { position: relative; display: flex; flex-direction: column; gap: 4px; flex: none; }
.gd-bottom-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.gd-mini {
  font-size: 11px; padding: 2px 8px; border-radius: 999px;
  background: rgba(255, 255, 255, .07); border: none;
  color: var(--gt-ink-dim); font-variant-numeric: tabular-nums;
}
.gd-mini.on { background: rgba(233, 200, 119, .18); border-color: rgba(233, 200, 119, .5); color: var(--gt-gold); }
/* ===== 手牌区（v2.46.72）：占宽 80% 靠底居中、弧形叠放、悬浮卡片感 =====
   v2.46.73：高度固定 180px、左右内边距 80px（外部 UI 方案；牌尺寸经拍板保持
   随板高缩放不缩到 44×64——手机缩放后数字可读性优先） */
.gd-hand-zone {
  position: relative;
  width: 80%; margin: 0 auto; min-height: 0;
  /* v2.46.74：定高 180px 在手机 rotate90（逻辑高 ~390）下会把牌桌挤到 ~84px，
     改 clamp 弹性——矮板收缩保牌桌，桌面高板仍 180px */
  height: clamp(140px, 42%, 180px);
}
.gd-hand {
  display: flex; gap: 0; justify-content: center; align-items: flex-end;
  height: 100%;
  /* 上留白 = 选中上浮 + 弧形抬升；下留白 = 让出 footer 两角大按钮的高度带，
     手牌与按钮垂直错开、互不遮挡（大按钮挂在 footer 级，见 .gd-big） */
  padding: calc(var(--card-h, 88px) * 0.26) 80px 46px; min-height: 0;
  overflow: visible;
  touch-action: none;            /* 划选时既不滚动页面也不触发双指缩放 */
  -webkit-user-select: none; user-select: none;
}
.gd-hand .gt-card {
  margin-right: calc(-1 * var(--gd-overlap, 0px));
  /* 弧形叠放（夜星清单）：rotate / translate 用独立 transform 属性，
     与 .is-sel 的 transform 上浮互不覆盖（WebView Chromium 104+ 支持） */
  rotate: calc(var(--fa, 0) * 1deg);
  translate: 0 calc(var(--fy, 0) * 1px);
  transform-origin: 50% 120%;
}
.gd-hand .gt-card:last-child { margin-right: 0; }
/* 选中牌：在弧形抬升基础上再上浮（沿用全局 .is-sel transform，z-index 抬层） */
.gd-hand .gt-card.is-sel { translate: 0 calc(var(--fy, 0) * 1px - 16px); }
/* 分区线（v2.46.24）：左钉区|散牌区 之间的鎏金竖线 */
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
/* 出牌动效：四座位出牌区的牌行沿用逐张甩入（gd-throw），选择器随结构改名 */
@keyframes gd-throw {
  0% { transform: translateY(-52px) rotate(-15deg) scale(1.26); opacity: 0; }
  62% { transform: translateY(3px) rotate(2deg) scale(.985); opacity: 1; }
  100% { transform: none; opacity: 1; }
}
.gd-thz-cards > .gt-card {
  animation: gd-throw .36s cubic-bezier(.2, .85, .3, 1) both;
  animation-delay: calc(var(--i, 0) * 32ms);
}
.gd-hand .gt-card:hover, .gd-hand .gt-card.is-sel { z-index: 5; }
.gd-hand-empty { margin: auto; font-size: 12px; color: var(--gt-ink-dim); }

/* ===== 操作区（v2.46.72 精简）：工具行 + 左下/右下浮动大按钮 ===== */
/* 工具行：提示（左）· 挪左 · 牌型识别标签（中） · 挪右 · 重选（右）
   v2.46.73：统一深色胶囊 + 金边（外部 UI 方案），间距 12px；
   禁用态去掉底与边（降噪：只留可用的按钮壳），字保留 45% 提示功能存在 */
.gd-hand-tools {
  display: flex; align-items: center; gap: 12px;
  width: 80%; padding: 0 2px;
  /* v2.46.114：拆 longhand——shorthand margin 写在媒体查询之后会覆盖前者的
     margin-top 让位（同特异性后者胜），历史踩坑两次 */
  margin-left: auto; margin-right: auto;
}
.gd-hand-tools .gt-btn {
  padding: 4px 14px; font-size: 12px; border-radius: 999px;
  background: rgba(10, 20, 16, .38);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(233, 200, 119, .32);
}
.gd-hand-tools .gt-btn:disabled {
  background: transparent; border-color: transparent; opacity: .45;
}
/* 选牌自动识别牌型（夜星清单：同花顺/顺子不单独做按钮，选完自动报牌型） */
.gd-pat-label {
  flex: 1; text-align: center; font-size: 13px; font-weight: 700;
  letter-spacing: .06em; color: var(--gt-ink-dim); white-space: nowrap;
  min-width: 0; overflow: hidden; text-overflow: ellipsis;
}
.gd-pat-label.ok { color: var(--gt-gold); text-shadow: 0 0 12px rgba(233, 200, 119, .4); }
.gd-pat-label.bad { color: #ff8f7d; }
.gd-pat-label i { font-style: normal; font-size: 11px; font-weight: 400; opacity: .85; }
/* 主力大按钮：左下「不要」墨灰毛玻璃、右下「出牌」鎏金（夜星拍板：不用亮绿，
   与全站宣纸+鎏金体系一致；深绿桌面上鎏金对比度最高） */
.gd-big {
  position: absolute; bottom: 6px; z-index: 8;
  min-width: 108px; padding: 11px 0;
  font-size: 16.5px; font-weight: 800; letter-spacing: .1em;
  border-radius: 999px;
}
.gd-big:disabled { opacity: .38; }
.gd-pass-big {
  left: 6px;
  background: rgba(22, 28, 32, .66); color: #cfc9bb;
  border: 1px solid rgba(233, 200, 119, .38);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 8px 20px -10px rgba(0, 0, 0, .9);
}
.gd-pass-big:not(:disabled):hover { background: rgba(40, 48, 54, .78); }
.gd-play-big {
  right: 6px;
  background: linear-gradient(180deg, #f4dc9c, #d9b65f);
  color: #2a1d05;
  border: 1px solid rgba(255, 255, 255, .55);
  box-shadow: 0 8px 22px -8px rgba(233, 200, 119, .85), inset 0 1px 0 rgba(255, 255, 255, .65);
}
.gd-play-big:not(:disabled):hover { background: linear-gradient(180deg, #f9e6b4, #e2c06c); }

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
  background: linear-gradient(180deg, #f4dc9c, #d9b65f);
  color: #2a1d05; font-weight: 700;
  border: 1px solid rgba(255, 255, 255, .5);
  box-shadow: 0 6px 18px -8px rgba(233, 200, 119, .85);
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
/* v2.46.74 玩家席位压缩（夜星：头像/姓名占位大了）——只覆盖掼蛋 scoped，
   不动共享 game-table.css（麻将等不受影响）：头像 34→26、内边距收半、文字回落 */
.gd .gt-seat { position: relative; padding: 3px 9px 3px 3px; gap: 6px; }
.gd .gt-seat-av { width: 26px; height: 26px; font-size: 13px; }
.gd .gt-seat-tx { display: flex; flex-direction: column; gap: 0; min-width: 0; }
.gd .gt-seat-name { font-size: 12px; max-width: 76px; }
.gd .gt-seat-sub { font-size: 10.5px; opacity: .82; }
/* v2.46.90「出牌中」徽标改浮层（夜星：轮到左右家时席位被撑大、里面文本错位）——
   徽标从 flex 流里拔出来悬在席位胶囊下缘，胶囊尺寸恒定不再跳动；
   轮到谁的高亮继续由 is-active 金色脉动光承担（不放大，只留选中特效） */
.gd .gt-seat-badge {
  position: absolute; left: 50%; bottom: -9px; transform: translateX(-50%);
  font-size: 10px; white-space: nowrap; z-index: 3; pointer-events: none;
}

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

<template>
  <div class="gt-landscape">
    <div ref="shellRef" class="gt-shell mp" :class="{ 'is-tilt': tilt }">
      <!-- ===== 棋盘 ===== -->
      <div ref="boardWrapRef" class="mp-boardwrap" :style="boardWrapStyle">
        <div class="mp-board" :style="{ '--n': BOARD_N }">
          <!-- 52 格 -->
          <div
            v-for="c in cells"
            :key="c.idx"
            class="mp-cell"
            :class="[`t-${c.type}`, c.owner != null ? 'owned' : '', { hl: c.hl }]"
            :style="cellStyle(c)"
          >
            <div class="mp-cell-top" :style="c.owner != null ? { background: COLORS[c.owner] } : {}">
              <span v-if="c.level > 0" class="mp-houses">{{ '🏠'.repeat(c.level) }}</span>
            </div>
            <div class="mp-cell-body">
              <b class="mp-cname">{{ c.name }}</b>
              <i v-if="c.price" class="mp-cprice">{{ fmt(c.price) }}</i>
              <i v-else-if="c.type === 'start'" class="mp-cprice">起点</i>
            </div>
            <div class="mp-tokens">
              <span
                v-for="p in tokensAt(c.idx)"
                :key="p.id"
                class="mp-tok"
                :class="{ 'is-now': p.id === cur.id && !game.over }"
                :style="{ background: COLORS[p.id] }"
                :title="p.name"
              >{{ p.avatar }}</span>
            </div>
            <!-- 落点反馈气泡：谁在这块地上花了 / 赚了多少，落在棋盘上直接可见 -->
            <span
              v-for="f in floatersAt(c.idx)"
              :key="f.id"
              class="mp-float"
              :class="'k-' + f.kind"
            >{{ f.text }}</span>
          </div>

          <!-- 中央信息区：当前行动者 + 玩家一排 + 骰子 + 行动流水 -->
          <div class="mp-center">
            <div class="mp-center-head">
              <span class="gt-pill gold">第 {{ game.round }} 轮<template v-if="roundLimit"> / {{ roundLimit }}</template></span>
              <span class="gt-pill">{{ phaseText }}</span>
            </div>
            <!-- 当前行动者：谁在动、什么颜色，一眼可见 -->
            <div v-if="!game.over" class="mp-turn">
              <span class="mp-turn-av" :style="{ background: COLORS[cur.id] }">{{ cur.avatar }}</span>
              <b class="mp-turn-name">{{ cur.name }}</b>
            </div>

            <!-- 玩家 2×2 紧凑卡（原在右栏，占掉一半宽度还看不全）：
                 头像 / 名字 / 现金·地产·道具都摊在棋盘中央，轮到谁就地发光 -->
            <div class="mp-players">
              <div
                v-for="p in game.players"
                :key="p.id"
                class="mp-pcard"
                :class="{ on: p.id === cur.id && !game.over, out: !p.alive }"
                :title="`${p.name} · 现金 ${fmt(p.cash)} · 地产 ${ownedCount(p)} · 道具 ${p.items.length}`"
              >
                <span class="mp-pav" :style="{ background: COLORS[p.id] }">{{ p.avatar }}</span>
                <span class="mp-ptx">
                  <b>{{ p.name }}<em v-if="p.skill"> · {{ SKILLS[p.skill].name }}</em></b>
                  <i :class="cashDir[p.id]">{{ fmt(cashShown[p.id] ?? p.cash) }} · 地{{ ownedCount(p) }} · 具{{ p.items.length }}</i>
                </span>
                <span v-if="!p.alive" class="gt-seat-badge">破产</span>
              </div>
            </div>

            <div class="mp-dice">
              <MonopolyDice
                v-for="(d, i) in game.dice"
                :key="i"
                :value="d"
                :rolling="game.rolling"
              />
            </div>

            <div class="mp-log">
              <div v-for="(l, i) in game.log.slice(-4)" :key="i" class="mp-log-row">{{ l }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== 右侧面板 ===== -->
      <aside class="mp-side">
        <div class="gt-bar mp-side-bar">
          <span class="gt-title">大富翁</span>
          <span class="gt-pill">底注 {{ fmt(stake) }} 豆</span>
          <span class="gt-spacer"></span>
          <button class="gt-btn ghost sm" @click="tilt = !tilt">{{ tilt ? '平面' : '3D' }}</button>
          <button class="gt-btn ghost sm" @click="$emit('exit')">退出</button>
        </div>

        <!-- 当前地块 + 欢乐豆：合成一块两行（旧版「当前所在」标题占一行、豆子又单独一块，
             右栏堆了 8 个盒子，手机横屏下比棋盘还抢眼）。操作按钮就在下面，指向这里的地块。 -->
        <div class="mp-here">
          <div class="mp-here-row">
            <b>{{ hereCell.name }}</b>
            <span class="gt-beans">🪙 {{ fmt(wallet.beans) }}</span>
          </div>
          <i v-if="hereCell.price">地价 {{ fmt(hereCell.price) }} · 租金 {{ fmt(rentOf(hereCell)) }}</i>
          <i v-else>{{ hereHint }}</i>
        </div>

        <!-- 操作区 -->
        <div class="gt-actions mp-ops">
          <template v-if="!game.over">
            <button
              class="gt-btn"
              :disabled="rollDisabled"
              @click="rollAndMove"
            >🎲 掷骰前进</button>
            <button
              v-if="canBuy"
              class="gt-btn"
              :disabled="isOnline ? acting : busy"
              @click="buyHere"
            >购地 {{ fmt(hereCell.price) }}</button>
            <button
              v-if="canBuild"
              class="gt-btn ghost"
              :disabled="isOnline ? acting : busy"
              @click="buildHere"
            >盖房 {{ fmt(buildCost(hereCell)) }} → Lv{{ hereCell.level + 1 }}</button>
            <button
              v-if="cur.skill && !cur.skillUsed && SKILLS[cur.skill].target === 'self' && (!isOnline || oIsMyTurn)"
              class="gt-btn ghost"
              :disabled="isOnline ? acting : (busy || cur.isAI)"
              @click="useSkill"
            >✨ {{ SKILLS[cur.skill].name }}</button>
            <button
              v-for="g in itemGroups"
              :key="g.key"
              class="gt-btn ghost sm mp-item"
              :disabled="itemDisabled"
              :title="ITEMS[g.key].desc"
              @click="useItem(g.key)"
            >{{ ITEMS[g.key].icon }} {{ ITEMS[g.key].name }}<em v-if="g.n > 1" class="mp-item-n">×{{ g.n }}</em></button>
            <!-- 在线专属：服务端驱动回合的补充操作 -->
            <template v-if="isOnline">
              <button v-if="oOpts.buy" class="gt-btn ghost" :disabled="acting" @click="skipBuy">放弃 · 拍卖</button>
              <button v-if="oOpts.end_turn" class="gt-btn" :disabled="acting" @click="endTurnAct">结束回合</button>
              <button v-if="oOpts.pay_jail" class="gt-btn" :disabled="acting" @click="payJail">缴纳罚金出狱</button>
              <button v-if="oOpts.roll_jail" class="gt-btn ghost" :disabled="acting" @click="rollJail">掷骰出狱</button>
            </template>
          </template>
          <template v-else>
            <button class="gt-btn" @click="restart">🔁 再来一局</button>
          </template>
        </div>

        <!-- 在线：地块经营（升级 / 抵押 / 赎回） -->
        <div
          v-if="isOnline && oIsMyTurn && (oOpts.upgrade.length || oOpts.mortgage.length || oOpts.redeem.length)"
          class="mp-manage"
        >
          <template v-if="oOpts.upgrade.length">
            <div class="mp-here-h">可盖房</div>
            <div class="gt-actions">
              <button v-for="t in oOpts.upgrade" :key="'u' + t" class="gt-btn ghost sm" :disabled="acting" @click="upgradeTile(t)">{{ boardName(t) }}</button>
            </div>
          </template>
          <template v-if="oOpts.mortgage.length">
            <div class="mp-here-h">可抵押</div>
            <div class="gt-actions">
              <button v-for="t in oOpts.mortgage" :key="'m' + t" class="gt-btn ghost sm" :disabled="acting" @click="mortgageTile(t)">{{ boardName(t) }}</button>
            </div>
          </template>
          <template v-if="oOpts.redeem.length">
            <div class="mp-here-h">可赎回</div>
            <div class="gt-actions">
              <button v-for="t in oOpts.redeem" :key="'r' + t" class="gt-btn ghost sm" :disabled="acting" @click="redeemTile(t)">{{ boardName(t) }}</button>
            </div>
          </template>
        </div>

        <!-- 在线：拍卖（页内，不弹窗） -->
        <div v-if="isOnline && oAuction" class="mp-auction">
          <div class="mp-here-h">拍卖 · {{ boardName(oAuction.tile) }}</div>
          <div class="mp-here-b">
            <b>最高 {{ fmt(oAuction.high) }} 豆</b>
            <i>{{ oAuction.high_seat >= 0 ? seatLabel(oAuction.high_seat) + ' 领先' : '尚无人出价' }}</i>
          </div>
          <div v-if="oAuction.turn === oSeat" class="gt-actions">
            <input v-model.number="bidAmount" class="mp-bid" type="number" :min="oAuction.high + 1" />
            <button class="gt-btn sm" :disabled="acting" @click="doBid">出价</button>
            <button class="gt-btn ghost sm" :disabled="acting" @click="passBid">放弃</button>
          </div>
          <i v-else>等待 {{ seatLabel(oAuction.turn) }} 出价…</i>
        </div>

        <!-- 在线：收到的交易（页内，不弹窗） -->
        <div v-if="isOnline && oTrades.length" class="mp-trades">
          <div class="mp-here-h">收到交易</div>
          <div v-for="tr in oTrades" :key="tr.id" class="mp-trade-row">
            <i>{{ seatLabel(tr.from) }}：{{ bundleText(tr.give) }} 换 {{ bundleText(tr.want) }}</i>
            <div class="gt-actions">
              <button class="gt-btn sm" :disabled="acting" @click="acceptTrade(tr.id)">接受</button>
              <button class="gt-btn ghost sm" :disabled="acting" @click="rejectTrade(tr.id)">拒绝</button>
            </div>
          </div>
        </div>

        <!-- 家庭豆子：已并入「当前地块」那块，不再单占一个盒子 -->
      </aside>

      <!-- 结算（页内，不弹窗） -->
      <div v-if="game.over" class="gt-over">
        <div class="gt-over-card">
          <h3>{{ game.over.win ? '🏆 你赢了！' : '本局结束' }}</h3>
          <p>
            {{ game.over.title }}<br />
            本局豆子：<b :style="{ color: game.over.delta >= 0 ? '#8fe3a8' : '#ff9b9b' }">
              {{ game.over.delta >= 0 ? '+' : '' }}{{ fmt(game.over.delta) }}
            </b>
          </p>
          <div class="gt-actions">
            <button class="gt-btn" @click="restart">再来一局</button>
            <button class="gt-btn ghost" @click="$emit('exit')">返回</button>
          </div>
        </div>
      </div>

      <div v-if="toast" class="gt-toast">{{ toast }}</div>
    </div>
  </div>
</template>

<script setup>
/** 大富翁（v2.43）—— 52 格等距 3D 中国城市棋盘，1~8 人（不足自动补 AI）。
 *
 * 规则要点：买地 / 盖房升级 / 收租 / 机会命运 / 监狱 / 税收 / 道具格 / 破产淘汰 / 最后存活者胜。
 * 8 角色各带 1 个主动技能，8 张道具卡踩「道具格」随机抽。
 * 信息全公开 → 规则全部前端计算（与既有棋类一致），结算走 /api/game/settle 记战绩与豆子。
 */
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { reportSettle, gameEconomyApi } from '@/api/gameEconomy'
import { sfx } from '@/utils/games/sfx'
import MonopolyDice from '@/components/games/MonopolyDice.vue'

const props = defineProps({
  gameKey: { type: String, default: 'monopoly' },
  initialMode: { type: String, default: 'p4' },
  bare: { type: Boolean, default: false },
  big: { type: Boolean, default: false },
  // v2.44 在线：服务端投影渲染，动作 emit 给等待房页转 /act
  online: { type: Boolean, default: false },
  onlineView: { type: Object, default: null },
  onlineSeat: { type: Number, default: 0 },
  seatNames: { type: Array, default: () => [] },
  acting: { type: Boolean, default: false },
  isHost: { type: Boolean, default: false },
})
const emit = defineEmits(['exit', 'room-lock', 'room-unlock', 'act', 'rematch'])

/* ---------------- 静态数据 ---------------- */
const BOARD_N = 14          // 14×14 环，共 52 格
const START_CASH = 50000

const COLORS = ['#e05a5a', '#4a90d9', '#3fae7a', '#e0a83f', '#9b6bd6', '#39bcc4', '#d6709b', '#7d8fa8']

const SKILLS = {
  reroll:  { name: '掷骰加成', desc: '本回合可重掷一次骰子', target: 'self' },
  freerent:{ name: '免租一次', desc: '本回合免付一次租金', target: 'self' },
  forcebuy:{ name: '强买邻地', desc: '七折强买当前所在的无主地块', target: 'self' },
  demolish:{ name: '拆迁令', desc: '拆掉当前地块上的一级建筑', target: 'self' },
  doublerent:{ name: '双倍收租', desc: '本回合收租翻倍', target: 'self' },
  blink:   { name: '闪现', desc: '立即前进 6 格', target: 'self' },
  equalize:{ name: '均富', desc: '与最富者现金拉平（取其一半）', target: 'self' },
  bargain: { name: '抄底', desc: '七折买下当前地块的对手地产', target: 'self' },
}

const ITEMS = {
  barrier:  { name: '路障', icon: '🚧', desc: '在自己脚下放置，下一位经过者停一回合' },
  teleport: { name: '传送', icon: '🌀', desc: '立即传送到下一个自己的地块' },
  freecard: { name: '免费卡', icon: '🎫', desc: '立即获得一次免租' },
  equalcard:{ name: '均富卡', icon: '⚖️', desc: '立即与最富者现金拉平' },
  buycard:  { name: '购地卡', icon: '📜', desc: '立即七折买下当前无主地块' },
  turncard: { name: '转向卡', icon: '🔄', desc: '强制下一位玩家后退 3 格' },
  monster:  { name: '怪兽卡', icon: '👾', desc: '拆掉场上任意一处最高等级建筑' },
  angel:    { name: '天使卡', icon: '😇', desc: '本回合免疫一切扣款' },
}

// 8 个颜色组 × 30 块地
const GROUPS = [
  { key: 'hb', name: '华北', color: '#d9734a' },
  { key: 'hd', name: '华东', color: '#4a90d9' },
  { key: 'hn', name: '华南', color: '#3fae7a' },
  { key: 'xn', name: '西南', color: '#e0a83f' },
  { key: 'hz', name: '华中', color: '#9b6bd6' },
  { key: 'xb', name: '西北', color: '#39bcc4' },
  { key: 'db', name: '东北', color: '#d6709b' },
  { key: 'gj', name: '港澳台', color: '#7d8fa8' },
]

// [名称, 地价, 组]
const CITY_DEFS = [
  ['北京', 2600, 'hb'], ['天津', 1800, 'hb'], ['石家庄', 1400, 'hb'], ['太原', 1200, 'hb'],
  ['上海', 2800, 'hd'], ['南京', 1900, 'hd'], ['杭州', 2000, 'hd'], ['苏州', 1700, 'hd'],
  ['广州', 2400, 'hn'], ['深圳', 2500, 'hn'], ['珠海', 1300, 'hn'], ['佛山', 1400, 'hn'],
  ['成都', 1800, 'xn'], ['重庆', 1700, 'xn'], ['昆明', 1200, 'xn'], ['贵阳', 1000, 'xn'],
  ['武汉', 1900, 'hz'], ['长沙', 1500, 'hz'], ['郑州', 1500, 'hz'], ['南昌', 1200, 'hz'],
  ['西安', 1600, 'xb'], ['兰州', 1000, 'xb'], ['乌鲁木齐', 900, 'xb'],
  ['沈阳', 1400, 'db'], ['大连', 1500, 'db'], ['哈尔滨', 1200, 'db'],
  ['香港', 3000, 'gj'], ['澳门', 2200, 'gj'], ['台北', 2300, 'gj'], ['三亚', 1800, 'gj'],
]

// 52 格布局（与 CITY_DEFS 顺序一一对应）
const LAYOUT = [
  { type: 'start' }, { city: 0 }, { type: 'chance' }, { city: 1 }, { type: 'tax' },
  { city: 2 }, { city: 3 }, { type: 'item' }, { city: 4 }, { city: 5 },
  { type: 'fate' }, { city: 6 }, { city: 7 }, { type: 'jail' }, { city: 8 },
  { type: 'chance' }, { city: 9 }, { type: 'item' }, { city: 10 }, { city: 11 },
  { type: 'tax' }, { city: 12 }, { type: 'fate' }, { city: 13 }, { city: 14 },
  { city: 15 }, { type: 'park' }, { city: 16 }, { type: 'chance' }, { city: 17 },
  { type: 'item' }, { city: 18 }, { city: 19 }, { type: 'fate' }, { city: 20 },
  { city: 21 }, { type: 'item' }, { city: 22 }, { type: 'chance' }, { type: 'gotojail' },
  { city: 23 }, { type: 'fate' }, { city: 24 }, { city: 25 }, { type: 'item' },
  { city: 26 }, { type: 'chance' }, { city: 27 }, { city: 28 }, { type: 'fate' },
  { city: 29 }, { type: 'item' },
]

const CHANCE = [
  { text: '银行派息，领取 2000 豆', fn: (p) => { p.cash += 2000 } },
  { text: '路边拾遗，领取 800 豆', fn: (p) => { p.cash += 800 } },
  { text: '投资获利，领取 3000 豆', fn: (p) => { p.cash += 3000 } },
  { text: '违章罚款，支付 1200 豆', fn: (p) => { pay(p, 1200) } },
  { text: '慈善捐款，支付 600 豆', fn: (p) => { pay(p, 600) } },
  { text: '免费旅游，直接前进 3 格', fn: (p) => { moveBy(p, 3) } },
]

const FATE = [
  { text: '房产升值，每处地产 +400 豆', fn: (p) => { p.cash += 400 * Object.keys(p.props).length } },
  { text: '维修费，每处地产 -300 豆', fn: (p) => { pay(p, 300 * Object.keys(p.props).length) } },
  { text: '中了小奖，领取 1500 豆', fn: (p) => { p.cash += 1500 } },
  { text: '医疗支出，支付 1000 豆', fn: (p) => { pay(p, 1000) } },
  { text: '被查税，支付现金 10%', fn: (p) => { pay(p, Math.round(p.cash * 0.1)) } },
  { text: '顺风车，直接前进 2 格', fn: (p) => { moveBy(p, 2) } },
]

const AI_NAMES = ['阿豆', '小满', '铁蛋', '阿福', '小柔', '老周', '阿珍']
const AI_AVATARS = ['🐼', '🦊', '🐯', '🐨', '🐰', '🐵', '🐸']

/* ---------------- 状态 ---------------- */
const game = reactive({
  players: [],
  cells: [],
  curIdx: 0,
  round: 1,
  dice: [1, 1],
  rolling: false,
  log: [],
  over: null,
})
const busy = ref(false)
/* 3D 倾斜默认关：`rotateX(15deg)` 叠在 `perspective` 上会把棋盘近端放大、远端缩小，
   在手机横屏这种「宽 780 高 390」的窄高容器里，放大出来的下缘直接被舞台 overflow 裁掉 ——
   这就是夜星反复反馈的「地图被盖住」。改为平面渲染，需要视角时再手动切 3D。 */
const tilt = ref(false)
const toast = ref('')
const wallet = reactive({ beans: 0 })

/* ---------------- 棋盘尺寸（由容器算出来） ----------------
 * 为什么必须用 JS 量：`.mp-board` 是 14×14 的 grid。
 *   ① `aspect-ratio: 1` + `width: auto` + `height: 100%` 在 flex 容器里，Chrome 会先按
 *      「内容宽度」定 flex base size，再套 height:100% —— 结果棋盘被拉成 514×336 的
 *      长方形（实测），格子变 20×48，名字与价格互相压字、环也不成方。
 *   ② 高度不是确定值时 `grid-template-rows: repeat(14, 1fr)` 退化成 content 尺寸，
 *      14 行加起来 630px 直接溢出 336px 的棋盘（实测 scrollHeight=630），下边的格子被裁。
 * → 由 JS 量容器可用宽高，写进 `--mp-w` / `--mp-h`（两个方向都是确定 px）。
 *
 * 【v2.46.8 两个改动】
 *   · **不再强制正方形**：手机横屏时横向空间大量闲置（实测棋盘只用到容器宽度的 41%），
 *     而高度是硬约束 —— 方棋盘只能取「高度」那一档，格子自然小（夜星：「还有很大的空间
 *     可以用，可以放大格子」）。现在按可用盒子铺满，宽高比封顶 1.45，格子面积约 +45%。
 *   · **高度改用「可视高度」兜底**：非全屏（手机自带浏览器走桌面版 viewport 1280）时
 *     `.mp` 没有确定高度，行高是由内容（棋盘自己）撑出来的 —— 只读容器高度会自锁，
 *     而且整块外壳会高于视口（夜星：「横屏展示时底部会被遮挡」）。
 *     这里同时量「容器高度」和「视口剩余高度」，取更小的那个，两种情况都不会溢出。
 */
const boardWrapRef = ref(null)
const shellRef = ref(null)
const boardSize = ref({ w: 0, h: 0 })
let boardRO = null
let onWinResize = null
const BOARD_MAX_H = 760          // 桌面端上限（不让棋盘无限长高）
const BOARD_ASPECT = 1.45        // 宽高比封顶：再宽格子会扁得不像牌桌
const boardWrapStyle = computed(() => (boardSize.value.w
  ? { '--mp-w': boardSize.value.w + 'px', '--mp-h': boardSize.value.h + 'px' }
  : {}))
function measureBoard() {
  const el = boardWrapRef.value
  if (!el) return
  const w = Math.floor(el.clientWidth || 0)
  if (!w) return
  /* 全屏链路里 `--mp-w/h` 写在**逻辑画布坐标**上（画布整体等比缩放），
     而 getBoundingClientRect() 给的是缩放后的屏幕坐标 —— 必须除以缩放比换回逻辑值，
     否则会把棋盘算小一倍（缩放 0.5 时尤为明显）。 */
  const rect = el.getBoundingClientRect()
  const scale = rect.width ? rect.width / el.clientWidth : 1
  const visH = Math.max(240, (window.innerHeight - rect.top) / (scale || 1) - 14)
  let bh = Math.floor(Math.min(el.clientHeight || visH, visH, BOARD_MAX_H))
  let bw = Math.floor(Math.min(w, bh * BOARD_ASPECT, BOARD_MAX_H * BOARD_ASPECT))
  if (bw < bh) bh = bw             // 盒子比高更窄（竖屏）→ 退回正方形，别拉成长条
  if (bw <= 0 || bh <= 0) return
  /* 把「可视高度」也写回外壳：矮屏时右栏靠它封顶（否则右栏自己就能把外壳顶出屏幕，
     底部按钮还是会被裁 —— 棋盘量准了也没用）。 */
  if (shellRef.value) shellRef.value.style.setProperty('--mp-vis-h', Math.round(visH) + 'px')
  const prev = boardSize.value
  if (Math.abs(bw - prev.w) > 1 || Math.abs(bh - prev.h) > 1) boardSize.value = { w: bw, h: bh }
}

let toastTimer = null
let onlineRollTimer = null
function say(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1800)
}
function log(msg) { game.log.push(msg); if (game.log.length > 120) game.log.splice(0, 40) }

/* ---------------- 在线：派生（服务端投影） ---------------- */
const isOnline = computed(() => props.online)
const oSeat = computed(() => Number(props.onlineSeat ?? 0))
const oView = computed(() => props.onlineView || {})
const oTable = computed(() => oView.value.table || {})
const oOpts = computed(() => {
  const o = oView.value.me?.options || {}
  return {
    roll: false, buy: false, end_turn: false,
    upgrade: [], mortgage: [], redeem: [],
    pay_jail: false, roll_jail: false, ...o,
  }
})
const oAuction = computed(() => oTable.value.auction || null)
/** 轮数上限（在线引擎下发；本地固定 200） */
const roundLimit = computed(() => (isOnline.value ? (oTable.value.round_limit || 0) : 200))
/** 待我处理的交易（服务端只保留 pending） */
const oTrades = computed(() =>
  (oTable.value.trades || []).filter((t) => t.status === 'pending' && t.to === oSeat.value))
const oIsMyTurn = computed(() => isOnline.value && oView.value.turn === oSeat.value)
const rollDisabled = computed(() => (isOnline.value
  ? (props.acting || !oOpts.value.roll)
  : (busy.value || cur.value.isAI || game.rolling)))
const bidAmount = ref(0)

/** 座位标签：在线用 seatNames，本地用玩家名 */
function seatLabel(s) {
  if (isOnline.value) return s === oSeat.value ? '你' : (props.seatNames?.[s] || `座位${s + 1}`)
  return game.players[s]?.name || `玩家${s + 1}`
}
/** 交易礼包文案 */
function bundleText(b) {
  if (!b) return '—'
  const parts = []
  if (b.cash) parts.push(`${fmt(b.cash)}豆`)
  if (b.tiles?.length) parts.push(`${b.tiles.length}块地`)
  if (b.items?.length) parts.push(`${b.items.length}张卡`)
  return parts.join('+') || '—'
}
/** 地块名（拍卖/交易展示用） */
function boardName(idx) { return game.cells[idx]?.name || `#${idx}` }

const cur = computed(() => game.players[game.curIdx] || { items: [], props: {}, cash: 0, id: 0, avatar: '?' })
const cells = computed(() => game.cells)
const hereCell = computed(() => game.cells[cur.value.pos] || { name: '—' })
const hereHint = computed(() => {
  const t = hereCell.value.type
  return ({
    start: '起点 · 每经过一次领 2000 豆',
    chance: '机会 · 抽一张随机事件卡',
    fate: '命运 · 抽一张随机事件卡',
    tax: '税收 · 按现金比例缴税',
    item: '道具格 · 随机获得一张道具卡',
    jail: '监狱（路过）',
    park: '免费停车 · 安全区',
    gotojail: '进监狱 · 下一回合停走',
  })[t] || ''
})
const phaseText = computed(() => {
  if (isOnline.value) {
    const v = oView.value
    if (v.finished || v.phase === 'finished') return '对局结束'
    if (v.phase === 'auction') return '拍卖中'
    if (v.turn === oSeat.value) return props.acting ? '提交中' : '轮到你了'
    return `${seatLabel(v.turn)} 行动中`
  }
  if (game.over) return '对局结束'
  if (game.rolling) return '掷骰中'
  return cur.value.isAI ? `${cur.value.name} 思考中` : '轮到你了'
})
const canBuy = computed(() => {
  if (isOnline.value) return !!oOpts.value.buy
  const c = hereCell.value
  return !cur.value.isAI && c.price && c.owner == null && cur.value.cash >= c.price && !game.over
})
const canBuild = computed(() => {
  if (isOnline.value) return oOpts.value.upgrade.includes(hereCell.value.idx)
  const c = hereCell.value
  return !cur.value.isAI && c.price && c.owner === cur.value.id && c.level < 4 && cur.value.cash >= buildCost(c) && !game.over
})

/* ---- 道具卡分组（v2.46.25，夜星：「卡太多了点不了还找地方」）----
 * 旧版一张卡渲染一个全宽按钮：摸了一手 8 张卡右栏就堆 8 个大按钮，塞满还看不全。
 * 现在按种类合并成紧凑小徽章（×N 角标），一行多个自动换行；非我回合禁用但**仍可见**
 * （旧版在线时干脆整排隐藏，玩家根本不知道自己手里有牌）。 */
const itemGroups = computed(() => {
  const cnt = {}
  for (const it of (cur.value.items || [])) cnt[it] = (cnt[it] || 0) + 1
  return Object.keys(cnt).map((k) => ({ key: k, n: cnt[k] }))
})
const itemDisabled = computed(() => (isOnline.value ? (props.acting || !oIsMyTurn.value) : (busy.value || cur.value.isAI)))

function fmt(n) {
  const v = Math.round(Number(n) || 0)
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(v % 10000 === 0 ? 0 : 1) + '万'
  return String(v)
}
function buildCost(c) { return c.build != null ? c.build : Math.round((c.price || 0) * 0.6) }
function rentOf(c) {
  if (!c || !c.price || c.owner == null) return 0
  if (Array.isArray(c.rents)) return c.rents[Math.min(c.level || 0, c.rents.length - 1)] || 0
  const base = Math.round(c.price * 0.12)
  return Math.round(base * (1 + c.level * 0.9))
}
function ownedCount(p) { return Object.keys(p.props || {}).length }
function tokensAt(idx) { return game.players.filter((p) => p.alive && p.pos === idx) }

/* ---------------- 棋盘几何：14×14 环 ---------------- */
function cellStyle(c) {
  const i = c.idx
  let col, row
  if (i <= 13) { col = 14 - i; row = 14 }
  else if (i <= 26) { col = 1; row = 14 - (i - 13) }
  else if (i <= 39) { col = 1 + (i - 26); row = 1 }
  else { col = 14; row = 1 + (i - 39) }
  return { gridColumn: col, gridRow: row }
}

function buildCells() {
  const cityById = {}
  CITY_DEFS.forEach((d, i) => {
    cityById[i] = { name: d[0], price: d[1], group: d[2], groupColor: GROUPS.find((g) => g.key === d[2]).color }
  })
  game.cells = LAYOUT.map((l, idx) => {
    if (l.city != null) {
      const c = cityById[l.city]
      return { idx, type: 'city', name: c.name, price: c.price, group: c.group, groupColor: c.groupColor, owner: null, level: 0, hl: false }
    }
    const names = { start: '起点', jail: '监狱', park: '免费停车', gotojail: '进监狱', chance: '机会', fate: '命运', tax: '税收', item: '道具' }
    return { idx, type: l.type, name: names[l.type] || '', price: 0, owner: null, level: 0, hl: false }
  })
}

/* ---------------- 开局 ---------------- */
function playerCount() {
  const m = String(props.initialMode || 'p4')
  const n = Number(m.replace('p', ''))
  return Number.isFinite(n) ? Math.min(8, Math.max(2, n)) : 4
}

function newGame() {
  buildCells()
  const n = playerCount()
  const humans = 1                         // v2.44：同屏多人下线，本地练习固定 1 真人 + N AI
  const skillKeys = Object.keys(SKILLS)
  game.players = []
  for (let i = 0; i < n; i++) {
    const isAI = i >= humans
    game.players.push({
      id: i,
      name: isAI ? AI_NAMES[(i - humans) % AI_NAMES.length] : (i === 0 ? '你' : '玩家2'),
      avatar: isAI ? AI_AVATARS[(i - humans) % AI_AVATARS.length] : (i === 0 ? '🙂' : '😎'),
      isAI,
      cash: START_CASH,
      pos: 0,
      props: {},
      items: [],
      alive: true,
      jailTurns: 0,
      skill: skillKeys[i % skillKeys.length],
      skillUsed: false,
      freeRent: false,
      doubleRent: false,
      immune: false,
    })
  }
  game.curIdx = 0
  game.round = 1
  game.dice = [1, 1]
  game.over = null
  game.log = ['开局：每人 ' + fmt(START_CASH) + ' 豆，最后存活者获胜']
  busy.value = false
}

function restart() {
  if (isOnline.value) { emit('rematch'); return }
  newGame(); say('新的一局开始了')
}

/* ---------------- 金钱 ---------------- */
function pay(p, amount) {
  if (p.immune) { log(`${p.name} 的天使卡抵挡了 ${fmt(amount)} 豆支出`); return }
  p.cash -= amount
  if (p.cash < 0) {
    // 自动变卖地产抵债
    for (const k of Object.keys(p.props)) {
      if (p.cash >= 0) break
      const c = game.cells[Number(k)]
      p.cash += Math.round((c.price || 0) * 0.7) + c.level * Math.round((c.price || 0) * 0.4)
      c.owner = null; c.level = 0
      delete p.props[k]
      log(`${p.name} 变卖 ${c.name} 抵债`)
    }
  }
  if (p.cash < 0) { p.cash = 0; bankrupt(p) }
}

function bankrupt(p) {
  p.alive = false
  for (const k of Object.keys(p.props)) {
    const c = game.cells[Number(k)]
    c.owner = null; c.level = 0
    delete p.props[k]
  }
  log(`💀 ${p.name} 破产出局`)
}

function grantCell(p, idx) {
  const c = game.cells[idx]
  c.owner = p.id
  p.props[idx] = true
}

/** 同色组是否集齐（v2.46.31：AI 只在集齐组上加盖，与后端同口径） */
function groupComplete(g, ownerId) {
  const cells = game.cells.filter((x) => x.type === 'city' && x.group === g)
  return cells.length > 0 && cells.every((x) => x.owner === ownerId)
}

/* ---------------- 移动 ---------------- */
function moveBy(p, steps) {
  const before = p.pos
  p.pos = (p.pos + steps) % 52
  if (steps > 0 && p.pos < before) { p.cash += 2000; log(`${p.name} 经过起点，领取 2000 豆`) }
  return p.pos
}

function tokensRefresh() { /* 触发 tokensAt 重算 */ game.cells = [...game.cells] }

/* ---------------- 落点气泡：把「这块地上发生了什么」直接画在棋盘上 ----------------
 * 旧版所有反馈只进中央那行小字 log，玩家根本不知道刚扣的钱是因为什么。 */
const floaters = ref([])
let floatSeq = 0
const FLOAT_MS = 1500
function floatAt(idx, text, kind = 'info') {
  const id = ++floatSeq
  floaters.value.push({ id, idx, text, kind })
  setTimeout(() => { floaters.value = floaters.value.filter((f) => f.id !== id) }, FLOAT_MS)
}
function floatersAt(idx) { return floaters.value.filter((f) => f.idx === idx) }

/* ---------------- 现金 count-up（v2.46.20，Balatro 式滚动）----------------
 *  旧版现金直接跳变：-8000 一闪而过，玩家感知不到盈亏幅度。
 *  改成 rAF 逐帧逼近目标值：收钱向上滚、付钱向下滚，行内闪色提示方向。
 *  遵循 prefers-reduced-motion：系统要求减弱动效时直接同步。 */
const cashShown = reactive({})
const cashDir = reactive({})
const cashDirT = {}
let cashRaf = 0
const cashReduce = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
function cashTick() {
  for (const p of game.players) {
    const target = p.cash
    let shown = cashShown[p.id]
    if (shown == null) { cashShown[p.id] = target; continue }
    if (shown === target) continue
    const dir = target > shown ? 'up' : 'down'
    cashDir[p.id] = dir
    clearTimeout(cashDirT[p.id])
    cashDirT[p.id] = setTimeout(() => { cashDir[p.id] = '' }, 900)
    const diff = target - shown
    shown = Math.abs(diff) <= 1 ? target : Math.round(shown + diff * 0.16)
    cashShown[p.id] = shown
  }
  const moving = game.players.some((p) => cashShown[p.id] !== p.cash)
  cashRaf = moving ? requestAnimationFrame(cashTick) : 0
}
function kickCash() {
  if (cashReduce) {
    for (const p of game.players) cashShown[p.id] = p.cash
    return
  }
  if (!cashRaf) cashRaf = requestAnimationFrame(cashTick)
}
watch(() => game.players.map((p) => p.cash).join(','), kickCash)

/** 逐格推进：让「走到哪、路上经过什么」在棋盘上看得见。
 *  旧版 moveBy 是一次性瞬移，玩家只能从中央 log 里的一行字猜发生了什么。 */
/** 机器人「想一下」的时长（行动前）与每走一格的间隔。
 *  旧值 480/520/600ms + STEP_MS 105：掷骰到走位全程不到 1 秒，玩家只看到棋盘突然变了
 *  （夜星：「机器人行动的速度也慢一点，现在都看不到出的动作」）。
 *  现在给足观察时间：行动前 1.5~2.3s，每格 130ms，落点后再停 240ms 才结算。 */
const STEP_MS = 130
const AI_DELAY_MIN = 1500
const AI_DELAY_MAX = 2300
function aiDelay() { return AI_DELAY_MIN + Math.floor(Math.random() * (AI_DELAY_MAX - AI_DELAY_MIN)) }
async function animateMove(p, steps, stepMs = STEP_MS) {
  for (let i = 0; i < steps; i++) {
    const before = p.pos
    p.pos = (p.pos + 1) % 52
    if (p.pos < before) {
      p.cash += 2000
      log(`${p.name} 经过起点，领取 2000 豆`)
      floatAt(p.pos, '+2000', 'gain')
      sfx.coin()
    }
    tokensRefresh()
    await sleep(stepMs)
  }
  return p.pos
}

/* ---------------- 掷骰与落点结算 ---------------- */
async function rollAndMove() {
  if (isOnline.value) { emit('act', { type: 'roll' }); return }
  if (busy.value || game.over) return
  const p = cur.value
  if (!p.alive) return nextTurn()
  busy.value = true
  game.rolling = true
  const barrier = game.cells[p.pos].barrier
  if (barrier) {
    game.cells[p.pos].barrier = false
    game.rolling = false
    log(`🚧 ${p.name} 撞上路障，本回合停走`)
    busy.value = false
    return endTurn()
  }
  if (p.jailTurns > 0) {
    p.jailTurns -= 1
    game.rolling = false
    log(`🔒 ${p.name} 在监狱中，停走一回合（剩 ${p.jailTurns}）`)
    busy.value = false
    return endTurn()
  }

  const d1 = 1 + Math.floor(Math.random() * 6)
  const d2 = 1 + Math.floor(Math.random() * 6)
  const steps = d1 + d2
  game.dice = [d1, d2]
  sfx.dice()
  // Monopoly Go 式节奏（v2.46.20）：点数与时长反直觉挂钩——
  // 小点数（≤4）骰子多晃、棋子慢走，弥补「白等一回合」的失落感；
  // 大点数（≥9）提前出发，棋子在数字落定前就在动，制造「期待先行」。
  // 旧版恒定 620ms：掷 2 和掷 12 观感一样，小点数刚看清骰子棋子已经停了。
  await sleep(steps <= 4 ? 920 : steps >= 9 ? 430 : 620)
  game.rolling = false
  log(`🎲 ${p.name} 掷出 ${d1}+${d2}=${steps}`)
  await animateMove(p, steps, steps <= 4 ? 210 : STEP_MS)
  await sleep(240)
  await resolveLanding(p)
  busy.value = false
  endTurn()
}

function endTurn() {
  if (isOnline.value) return   // 在线由服务端推进回合
  if (game.over) return
  const p = cur.value
  p.freeRent = false
  p.doubleRent = false
  p.immune = false
  const alive = game.players.filter((x) => x.alive)
  if (alive.length <= 1) return finish(alive[0])
  // v2.46.25 终局口径（与在线引擎一致）：4 人及以上局剩最后 3 人即按资产排名结算；
  // 200 整轮封顶（2 人局的主要出口，防拖局）
  if (game.players.length >= 4 && alive.length <= 3) return finishRanked()
  if (game.round > 200) return finishRanked()
  let guard = 0
  do {
    game.curIdx = (game.curIdx + 1) % game.players.length
    if (game.curIdx === 0) game.round += 1
    guard += 1
  } while (!game.players[game.curIdx].alive && guard < 40)
  // AI 自动行动
  if (game.players[game.curIdx]?.isAI) setTimeout(() => aiTurn(), aiDelay())
}

function nextTurn() { endTurn() }

async function resolveLanding(p) {
  const c = game.cells[p.pos]
  if (c.type === 'city') {
    if (c.owner == null) {
      // 无主：AI 自动判断是否购买（v2.46.31 期望值：凑组关键张/低价组放宽到 1.25 倍现金）
      if (p.isAI) {
        const ownedInGroup = game.cells.filter((x) => x.type === 'city' && x.group === c.group && x.owner === p.id).length
        const hot = ownedInGroup >= 1 || c.group <= 1     // 已持同组或最低价组
        if (p.cash > c.price * (hot ? 1.25 : 1.6)) {
          p.cash -= c.price; grantCell(p, c.idx)
          log(`🏙 ${p.name} 买下 ${c.name}（${fmt(c.price)}）`)
          floatAt(c.idx, `-${fmt(c.price)} 购地`, 'buy')
          sfx.coinPay()
        } else log(`${p.name} 放弃购买 ${c.name}`)
      }
    } else if (c.owner !== p.id) {
      const owner = game.players[c.owner]
      if (!owner?.alive) { c.owner = null; c.level = 0; return }
      if (p.freeRent) {
        log(`${p.name} 使用免租，跳过 ${c.name} 租金`)
        floatAt(c.idx, '免租', 'info')
        return
      }
      if (p.immune) {
        log(`${p.name} 的天使卡免除了 ${c.name} 租金`)
        floatAt(c.idx, '😇 免疫', 'info')
        return
      }
      let rent = rentOf(c)
      if (p.doubleRent) rent *= 2
      log(`💸 ${p.name} 向 ${owner.name} 支付 ${c.name} 租金 ${fmt(rent)} 豆`)
      p.cash -= rent
      owner.cash += rent
      floatAt(c.idx, `-${fmt(rent)} 租`, 'pay')
      sfx.coinPay()
      if (p.cash < 0) pay(p, 0)
    } else if (p.isAI && c.level < 4 && p.cash > buildCost(c) * 2.2 && groupComplete(c.group, p.id)) {
      p.cash -= buildCost(c); c.level += 1
      log(`🏠 ${p.name} 把 ${c.name} 升到 Lv${c.level}`)
      floatAt(c.idx, `Lv${c.level} 加盖`, 'buy')
      sfx.coinPay()
    }
  } else if (c.type === 'chance') {
    const card = CHANCE[Math.floor(Math.random() * CHANCE.length)]
    log(`🃏 机会：${card.text}`)
    floatAt(c.idx, card.text, 'info')
    const cashBefore = p.cash
    card.fn(p, game)
    if (p.cash > cashBefore) sfx.coin()
    else if (p.cash < cashBefore) sfx.coinPay()
  } else if (c.type === 'fate') {
    const card = FATE[Math.floor(Math.random() * FATE.length)]
    log(`🎴 命运：${card.text}`)
    floatAt(c.idx, card.text, 'info')
    const cashBefore = p.cash
    card.fn(p, game)
    if (p.cash > cashBefore) sfx.coin()
    else if (p.cash < cashBefore) sfx.coinPay()
  } else if (c.type === 'tax') {
    const t = Math.round(p.cash * 0.08)
    log(`🧾 ${p.name} 缴税 ${fmt(t)} 豆`)
    floatAt(c.idx, `-${fmt(t)} 税`, 'pay')
    sfx.coinPay()
    pay(p, t)
  } else if (c.type === 'item') {
    const keys = Object.keys(ITEMS)
    const it = keys[Math.floor(Math.random() * keys.length)]
    p.items.push(it)
    log(`🎁 ${p.name} 获得道具「${ITEMS[it].name}」`)
    floatAt(c.idx, `${ITEMS[it].icon} ${ITEMS[it].name}`, 'item')
  } else if (c.type === 'gotojail') {
    p.pos = 13
    p.jailTurns = 1
    log(`🚔 ${p.name} 被送进监狱`)
    floatAt(13, '🚔 入狱', 'info')
  }
  tokensRefresh()
}

/* ---------------- 玩家操作 ---------------- */
function buyHere() {
  if (isOnline.value) { emit('act', { type: 'buy' }); return }
  const p = cur.value, c = hereCell.value
  if (c.owner != null || p.cash < c.price) return
  p.cash -= c.price
  grantCell(p, c.idx)
  log(`🏙 ${p.name} 买下 ${c.name}（${fmt(c.price)}）`)
  floatAt(c.idx, `-${fmt(c.price)} 购地`, 'buy')
  sfx.coinPay()
  tokensRefresh()
}

function buildHere() {
  if (isOnline.value) { emit('act', { type: 'upgrade', tile: hereCell.value.idx }); return }
  const p = cur.value, c = hereCell.value
  if (c.owner !== p.id || c.level >= 4) return
  const cost = buildCost(c)
  if (p.cash < cost) return
  p.cash -= cost
  c.level += 1
  log(`🏠 ${p.name} 把 ${c.name} 升到 Lv${c.level}（租金 ${fmt(rentOf(c))}）`)
  floatAt(c.idx, `-${fmt(cost)} 加盖 Lv${c.level}`, 'buy')
  sfx.coinPay()
}

function useSkill() {
  if (isOnline.value) {
    // 服务端技能需要 tile/pos 参数：tile 取当前格（强买/拆迁/抄底），pos 取前进 6 格（忍者）
    emit('act', { type: 'skill', tile: hereCell.value.idx, pos: (cur.value.pos + 6) % 52 })
    return
  }
  const p = cur.value
  if (!p.skill || p.skillUsed) return
  const s = p.skill
  const c = hereCell.value
  p.skillUsed = true
  if (s === 'reroll') {
    const d1 = 1 + Math.floor(Math.random() * 6), d2 = 1 + Math.floor(Math.random() * 6)
    game.dice = [d1, d2]
    log(`✨ ${p.name} 重掷：${d1}+${d2}`)
    moveBy(p, d1 + d2); resolveLanding(p)
  } else if (s === 'freerent') {
    p.freeRent = true; log(`✨ ${p.name} 获得本回合免租`)
  } else if (s === 'forcebuy') {
    if (c.type === 'city' && c.owner == null) {
      const cost = Math.round(c.price * 0.7)
      if (p.cash >= cost) { p.cash -= cost; grantCell(p, c.idx); log(`✨ 强买 ${c.name}（${fmt(cost)}）`) }
    } else say('当前地块无法强买')
  } else if (s === 'demolish') {
    if (c.type === 'city' && c.level > 0) { c.level -= 1; log(`✨ 拆迁令：${c.name} 降为 Lv${c.level}`) }
    else say('当前地块没有可拆建筑')
  } else if (s === 'doublerent') {
    p.doubleRent = true; log(`✨ ${p.name} 本回合双倍收租`)
  } else if (s === 'blink') {
    moveBy(p, 6); resolveLanding(p); log('✨ 闪现前进 6 格')
  } else if (s === 'equalize') {
    const richest = game.players.filter((x) => x.alive).sort((a, b) => b.cash - a.cash)[0]
    if (richest && richest.id !== p.id) {
      const target = Math.round(richest.cash / 2)
      if (target > p.cash) { log(`✨ 均富：从 ${fmt(p.cash)} 拉平到 ${fmt(target)}`); p.cash = target }
    }
  } else if (s === 'bargain') {
    if (c.type === 'city' && c.owner != null && c.owner !== p.id) {
      const owner = game.players[c.owner]
      const cost = Math.round(c.price * 0.7)
      if (p.cash >= cost) {
        p.cash -= cost; owner.cash += cost
        delete owner.props[c.idx]; grantCell(p, c.idx)
        log(`✨ 抄底买下 ${c.name}（付 ${owner.name} ${fmt(cost)}）`)
      }
    } else say('当前地块无法抄底')
  }
  tokensRefresh()
}

function useItem(it) {
  if (isOnline.value) {
    const idx = ITEM_KEYS.indexOf(it)
    if (idx < 0) return
    // 服务端道具：怪兽卡需 tile；路障卡需 target_seat（取首个存活对手）
    // 传送卡需选择目标格，本期无选格 UI，暂不携带 pos（服务端会提示目标不合法）
    const action = { type: 'use_item', item: idx }
    if (it === 'monster') action.tile = hereCell.value.idx
    if (it === 'barrier') {
      const other = game.players.find((p) => p.id !== oSeat.value && p.alive)
      if (other) action.target_seat = other.id
    }
    emit('act', action)
    return
  }
  const p = cur.value
  const i = p.items.indexOf(it)
  if (i < 0) return
  p.items.splice(i, 1)
  const c = hereCell.value
  if (it === 'barrier') { c.barrier = true; log(`🚧 ${p.name} 放置路障`) }
  else if (it === 'teleport') {
    const mine = Object.keys(p.props).map(Number)
    if (mine.length) {
      const next = mine.find((x) => x > p.pos) ?? mine[0]
      p.pos = next; resolveLanding(p); log(`🌀 传送到 ${game.cells[next].name}`)
    } else say('你还没有地产可传送')
  } else if (it === 'freecard') { p.freeRent = true; log('🎫 获得一次免租') }
  else if (it === 'equalcard') {
    const richest = game.players.filter((x) => x.alive).sort((a, b) => b.cash - a.cash)[0]
    if (richest && richest.id !== p.id && richest.cash > p.cash) { p.cash = Math.round(richest.cash / 2); log('⚖️ 均富卡生效') }
    else say('你已是最富，无需均富')
  } else if (it === 'buycard') {
    if (c.type === 'city' && c.owner == null) {
      const cost = Math.round(c.price * 0.7)
      if (p.cash >= cost) { p.cash -= cost; grantCell(p, c.idx); log(`📜 购地卡买下 ${c.name}`) }
      else say('现金不足')
    } else say('当前地块不可购')
  } else if (it === 'turncard') {
    const nxt = game.players[(game.curIdx + 1) % game.players.length]
    if (nxt?.alive) { nxt.pos = (nxt.pos + 49) % 52; log(`🔄 ${nxt.name} 被转向后退 3 格`) }
  } else if (it === 'monster') {
    let best = null
    for (const cc of game.cells) if (cc.level > 0 && (!best || cc.level > best.level)) best = cc
    if (best) { best.level -= 1; log(`👾 怪兽卡拆掉 ${best.name} 一级建筑`) }
    else say('场上还没有建筑')
  } else if (it === 'angel') { p.immune = true; log('😇 天使卡：本回合免疫扣款') }
  tokensRefresh()
}

/* ---------------- AI ---------------- */
async function aiTurn() {
  if (isOnline.value) return   // 在线 AI 由服务端驱动
  if (game.over) return
  const p = cur.value
  if (!p?.isAI || !p.alive) return
  // 偶尔使用道具
  if (p.items.length && Math.random() < 0.35) {
    const it = p.items[0]
    if (['freecard', 'angel', 'equalcard'].includes(it)) { useItem(it); await sleep(320) }
  }
  await sleep(220)
  await rollAndMove()
}

/* ---------------- 结算 ---------------- */
/** 净资产：现金 + 地价 + 加盖投入（排名 / 提前结算口径，与在线引擎 _net_worth 对齐） */
function netWorth(p) {
  let w = p.cash
  for (const k of Object.keys(p.props || {})) {
    const c = game.cells[Number(k)]
    if (!c) continue
    w += (c.price || 0) + (c.level || 0) * buildCost(c)
  }
  return w
}

/** 按资产排名提前结算（剩 3 人 / 200 轮封顶）：第一名胜，其余按名次展示 */
function finishRanked() {
  if (game.over) return
  const rank = [...game.players].sort((a, b) => netWorth(b) - netWorth(a))
  const me = game.players.find((p) => p.id === 0) || rank[0]
  const myRank = rank.indexOf(me) + 1
  const win = rank[0]?.id === 0
  const delta = win ? stake.value * (game.players.length - 1) : -stake.value
  game.over = {
    win,
    title: `按资产排名：${rank.map((p, i) => `${i + 1}.${p.name}`).join(' ')}（共 ${game.round} 轮）· 你第 ${myRank} 名`,
    delta,
  }
  log(`🏁 ${game.round} 轮排名结算：${rank[0]?.name || '无人'} 资产第一`)
  reportSettle('monopoly', win ? 'win' : (myRank === game.players.length ? 'lose' : 'draw'), delta, stake.value)
    .then((res) => { if (res?.beans != null) wallet.beans = res.beans })
    .catch(() => {})
}

async function finish(winner) {
  if (game.over) return
  const win = !!winner && winner.id === 0
  const delta = win ? stake.value * (game.players.length - 1) : -stake.value
  game.over = {
    win,
    title: winner ? `${winner.avatar} ${winner.name} 成为最后的大富翁（共 ${game.round} 轮）` : '平局',
    delta,
  }
  log(win ? '🏆 你赢了！' : `🏆 ${winner?.name || '无人'} 获胜`)
  const res = await reportSettle('monopoly', win ? 'win' : 'lose', delta, stake.value)
  if (res?.beans != null) wallet.beans = res.beans
}

const stake = ref(100)

/* ---------------- 在线：服务端投影 → 本地展示态 ---------------- */
const CHAR_KEYS = ['reroll', 'freerent', 'forcebuy', 'demolish', 'doublerent', 'blink', 'equalize', 'bargain']
const ITEM_KEYS = ['barrier', 'teleport', 'freecard', 'equalcard', 'buycard', 'turncard', 'monster', 'angel']
const KIND_TYPE = { property: 'city', start: 'start', chance: 'chance', item: 'item', tax: 'tax', jail: 'jail', goto_jail: 'gotojail', parking: 'park' }

/** 把服务端 view(state, seat) 投影映射到既有展示 ref，模板无需改字段名 */
function syncFromView(v) {
  if (!v) return
  const t = v.table || {}
  const owner = t.owner || []
  game.cells = (t.board || []).map((bt) => ({
    idx: bt.idx,
    type: KIND_TYPE[bt.kind] || bt.kind,
    name: bt.name,
    price: bt.price || 0,
    group: bt.group,
    groupColor: bt.kind === 'property' ? (GROUPS[bt.group]?.color || '#8a8a8a') : undefined,
    build: bt.build,
    rents: bt.rents,
    owner: owner[bt.idx] == null || owner[bt.idx] < 0 ? null : owner[bt.idx],
    level: t.level?.[bt.idx] || 0,
    hl: false,
  }))
  const propsOf = (s) => {
    const o = {}
    owner.forEach((ow, i) => { if (ow === s) o[i] = true })
    return o
  }
  game.players = (v.players || []).map((sp) => ({
    id: sp.seat,
    name: sp.seat === oSeat.value ? '你' : (props.seatNames?.[sp.seat] || `座位${sp.seat + 1}`),
    avatar: sp.seat === oSeat.value ? '🙂' : '🤖',
    isAI: sp.seat !== oSeat.value,
    cash: sp.cash,
    pos: sp.pos,
    props: propsOf(sp.seat),
    items: (sp.items || []).map((i) => ITEM_KEYS[i]).filter(Boolean),
    alive: sp.alive,
    jailTurns: sp.in_jail || 0,
    skill: CHAR_KEYS[sp.character] || null,
    skillUsed: sp.seat === oSeat.value ? ((v.me?.skill_left ?? 0) <= 0) : false,
    freeRent: false,
    doubleRent: false,
    immune: false,
  }))
  game.curIdx = (v.turn == null) ? 0 : v.turn
  // v2.46.25：真实轮数（服务端按整圈折算），「第 X 轮」不再恒显示 1
  game.round = t.rounds || game.round || 1
  // 在线：服务端掷出新点数时本地补播一次翻滚，否则玩家只看到数字「跳变」，
  // 完全没有「在掷骰」的感觉（单机走 rollAndMove，那边自己驱动动画）
  const nd = t.last_dice || [1, 1]
  if (nd[0] !== game.dice[0] || nd[1] !== game.dice[1]) {
    game.rolling = true
    clearTimeout(onlineRollTimer)
    onlineRollTimer = setTimeout(() => { game.rolling = false }, 620)
  }
  game.dice = nd
  game.over = null
  if (v.result) {
    const win = v.result.winner === oSeat.value
    const delta = v.result.deltas?.[oSeat.value] ?? 0
    game.over = { win, title: `${seatLabel(v.result.winner)} 获胜`, delta }
  }
}
watch(() => props.onlineView, (v) => { if (isOnline.value) syncFromView(v) }, { immediate: true, deep: true })
watch(oAuction, (a) => { if (a) bidAmount.value = (a.high || 0) + 500 })

/* ---------------- 在线：动作上抛 ---------------- */
function skipBuy() { if (isOnline.value) emit('act', { type: 'skip_buy' }) }
function endTurnAct() { if (isOnline.value) emit('act', { type: 'end_turn' }) }
function payJail() { if (isOnline.value) emit('act', { type: 'pay_jail' }) }
function rollJail() { if (isOnline.value) emit('act', { type: 'roll_jail' }) }
function upgradeTile(idx) { if (isOnline.value) emit('act', { type: 'upgrade', tile: idx }) }
function mortgageTile(idx) { if (isOnline.value) emit('act', { type: 'mortgage', tile: idx }) }
function redeemTile(idx) { if (isOnline.value) emit('act', { type: 'redeem', tile: idx }) }
function doBid() { if (isOnline.value) emit('act', { type: 'bid', amount: Number(bidAmount.value) || 0 }) }
function passBid() { if (isOnline.value) emit('act', { type: 'pass_bid' }) }
function acceptTrade(id) { if (isOnline.value) emit('act', { type: 'trade_accept', id }) }
function rejectTrade(id) { if (isOnline.value) emit('act', { type: 'trade_reject', id }) }

/* ---------------- 生命周期 ---------------- */
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)) }

onMounted(async () => {
  measureBoard()
  if (typeof ResizeObserver !== 'undefined' && boardWrapRef.value) {
    boardRO = new ResizeObserver(measureBoard)
    boardRO.observe(boardWrapRef.value)
  }
  // 棋盘高度同时受「视口剩余高度」约束（见 measureBoard），旋转 / 地址栏收放都要重量一次
  onWinResize = () => measureBoard()
  window.addEventListener('resize', onWinResize)
  window.addEventListener('orientationchange', onWinResize)
  if (isOnline.value) { syncFromView(props.onlineView); return }
  newGame()
  emit('room-lock')
  try {
    const res = await gameEconomyApi.wallet()
    const d = res?.data || {}
    if (d.beans != null) wallet.beans = d.beans
  } catch { /* 未登录或接口不可用时静默 */ }
  setTimeout(() => { if (cur.value?.isAI) aiTurn() }, aiDelay())
})

watch(() => game.curIdx, () => {
  if (isOnline.value) return   // 在线由服务端推进
  const p = cur.value
  if (p?.isAI && !game.over && !busy.value) setTimeout(() => aiTurn(), aiDelay())
})

onBeforeUnmount(() => {
  clearTimeout(toastTimer)
  clearTimeout(onlineRollTimer)
  if (cashRaf) cancelAnimationFrame(cashRaf)
  if (onWinResize) {
    window.removeEventListener('resize', onWinResize)
    window.removeEventListener('orientationchange', onWinResize)
    onWinResize = null
  }
  boardRO?.disconnect()
  boardRO = null
})
</script>

<style scoped>
.mp {
  /* 右栏收窄：玩家列表搬去棋盘中央后，这里只剩「当前地块 / 操作 / 钱包」，
     306px 的宽度是在浪费棋盘的地盘；留白也一并收紧，省下的都给棋盘 */
  display: grid; grid-template-columns: minmax(0, 1fr) 248px; gap: 10px;
  padding: 10px; min-height: 640px;
}
@media (max-width: 1100px) { .mp { grid-template-columns: minmax(0, 1fr); } }
/* 矮屏（手机横屏 / 窗口高度不足）：不再写死 640 —— 外壳比视口还高时，
   棋盘下半截与右栏下面的按钮都会被裁掉（夜星：「横屏展示时底部会被遮挡」）。
   棋盘高度由 JS 按「视口剩余高度」量（见 measureBoard），右栏也用同一个值封顶
   （内部本来就 overflow-y: auto，所以只是加个上限，不会丢内容）。 */
@media (max-height: 820px) {
  .mp { min-height: 0; }
  .mp-side { max-height: var(--mp-vis-h, calc(100vh - 20px)); }
}

/* ---- 棋盘 ---- */
.mp-boardwrap { perspective: 1500px; display: grid; place-items: center; min-width: 0; min-height: 0; }
.mp-board {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--n), 1fr);
  grid-template-rows: repeat(var(--n), 1fr);
  /* 宽高都取 JS 量出来的 `--mp-w` / `--mp-h`（见 script 里的说明）：两个方向都是确定 px，
     `repeat(14, 1fr)` 才不会退化成内容高度、把棋盘撑爆。
     未测量到之前退回旧写法（正方形），保证首帧不塌。 */
  width: var(--mp-w, min(100%, 760px));
  height: var(--mp-h, auto);
  aspect-ratio: 1;
  gap: 2px;
  transform-style: preserve-3d;
  /* 棋盘底：与麻将同色系的墨绿绒布。旧版棋盘没有底色，52 个彩色格子直接浮在
     深色背景上，视觉上「很碎、很吵」—— 加一层绒布把格子收进一个整体里。 */
  padding: 7px; border-radius: 16px; box-sizing: border-box;
  background: linear-gradient(158deg, #1d6049 0%, #134230 58%, #0b2a1f 100%);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, .09),
    inset 0 0 56px -14px rgba(0, 0, 0, .65);
}
.mp.is-tilt .mp-board { transform: rotateX(15deg) scale(.985); }

/* 单格尺寸 = (棋盘 − padding 14 − 13 道间隙 26) / 14。
 * 横屏时棋盘不再正方形（宽 > 高），所以横竖两档分别算：
 * 字号 / 令牌 / 色条一律取**较小的那一档**（`--mp-cell`），保证任何比例下都落在格内；
 * `--mp-cw` 单独留给需要「横向铺满」的东西。 */
.mp-board {
  --mp-cw: calc((var(--mp-w, 760px) - 40px) / 14);
  --mp-ch: calc((var(--mp-h, 760px) - 40px) / 14);
  --mp-cell: min(var(--mp-cw), var(--mp-ch));
}

.mp-cell {
  position: relative; border-radius: 4px;
  /* 气泡要上浮出格子，故不能裁切；圆角靠自身 background 保证 */
  overflow: visible;
  /* 统一象牙底：类型靠顶部色条区分，底色一律低饱和 —— 旧版 7 种高饱和渐变同时出现时很吵 */
  background: linear-gradient(170deg, #fdfbf6, #f0eadd);
  border: 1px solid rgba(122, 106, 74, .26);
  box-shadow: 0 2px 0 rgba(96, 80, 50, .36), 0 6px 10px -8px rgba(0, 0, 0, .7);
  display: flex; flex-direction: column;
  color: #2b2413; min-width: 0; padding: 0;
  transition: box-shadow .2s, filter .2s;
}
.mp-cell.hl { box-shadow: 0 0 0 2px var(--gt-gold), 0 2px 0 rgba(96, 80, 50, .36); }
/* 顶部色条：min-height 而非 height —— 格子放不下时房子图标要能把它撑开
   （.mp-cell 现在是 overflow:visible，写死 5px 会让房子跑到格子外） */
.mp-cell-top {
  min-height: 3px; height: calc(var(--mp-cell) * 0.15);
  background: rgba(120, 100, 60, .26); border-radius: 3px 3px 0 0;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
}
.mp-houses { display: block; font-size: 5.5px; line-height: 1; text-align: center; }
.mp-cell-body {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0; padding: 0 1px;
  overflow: hidden;
}
.mp-cname {
  /* 上限 11 → 12.5、系数 .34 → .38：横屏格子变宽变扁后（实测 32×21），
     字号只被「短边」这一档约束，还有余量再大一点；名字仍不会压到价格。 */
  font-size: clamp(7px, calc(var(--mp-cell) * 0.38), 12.5px);
  font-weight: 700; line-height: 1.02; text-align: center;
  max-width: 100%; overflow: hidden; white-space: nowrap;
}
.mp-cprice { font-style: normal; font-size: clamp(6px, calc(var(--mp-cell) * 0.28), 9.5px); opacity: .72; line-height: 1; }
/* 类型底：低饱和版（旧版 #ffe9a8 / #f0d7d0 / #dceaf7 … 太艳） */
.mp-cell.t-start { background: linear-gradient(170deg, #fdf6e2, #f5e8c2); }
.mp-cell.t-jail, .mp-cell.t-gotojail { background: linear-gradient(170deg, #f9efeb, #eedad2); }
.mp-cell.t-park { background: linear-gradient(170deg, #eef6f0, #dbeade); }
.mp-cell.t-chance { background: linear-gradient(170deg, #f0f5fb, #dde8f4); }
.mp-cell.t-fate { background: linear-gradient(170deg, #f6f1fb, #e6ddf2); }
.mp-cell.t-tax { background: linear-gradient(170deg, #fcf3e8, #f2e3cd); }
.mp-cell.t-item { background: linear-gradient(170deg, #fdf3f7, #f2e0e9); }
/* 顶部色条按类型着色（有主时被行内的业主色覆盖，优先级正确） */
.mp-cell.t-start .mp-cell-top { background: #d8ab38; }
.mp-cell.t-jail .mp-cell-top, .mp-cell.t-gotojail .mp-cell-top { background: #b98577; }
.mp-cell.t-park .mp-cell-top { background: #6faa84; }
.mp-cell.t-chance .mp-cell-top { background: #6d9ad4; }
.mp-cell.t-fate .mp-cell-top { background: #9a7fd0; }
.mp-cell.t-tax .mp-cell-top { background: #c79a5c; }
.mp-cell.t-item .mp-cell-top { background: #c98bb0; }

.mp-tokens {
  position: absolute; inset: auto 1px 1px 1px; display: flex; flex-wrap: wrap;
  gap: 1px; justify-content: center;
}
.mp-tok {
  width: clamp(9px, calc(var(--mp-cell) * 0.48), 21px);
  height: clamp(9px, calc(var(--mp-cell) * 0.48), 21px);
  border-radius: 50%; font-size: clamp(6px, calc(var(--mp-cell) * 0.3), 11px);
  display: grid; place-items: center; color: #fff;
  border: 1px solid rgba(255, 255, 255, .85);
  box-shadow: 0 1px 3px rgba(0, 0, 0, .55);
  transition: box-shadow .18s ease;
  /* 落到新格子时弹一下：棋子每走一格都是新挂载的元素，动画自然重放。
     这是「看得到机器人走位」的关键 —— 旧版棋子是瞬移，只能看到一个颜色块换了位置。 */
  animation: mp-hop .26s cubic-bezier(.2, .85, .3, 1) both;
}
@keyframes mp-hop {
  0% { transform: translateY(-11px) scale(1.26); }
  62% { transform: translateY(1px) scale(.97); }
  100% { transform: none; }
}
/* 轮到谁动，谁的令牌亮一圈金边 + 略大一圈（用尺寸放大而不是 transform，
   否则会和上面的 mp-hop 动画抢同一个属性、落定时跳一下） */
.mp-tok.is-now {
  width: clamp(10px, calc(var(--mp-cell) * 0.56), 24px);
  height: clamp(10px, calc(var(--mp-cell) * 0.56), 24px);
  border-color: var(--gt-gold);
  box-shadow: 0 0 0 2px rgba(233, 200, 119, .8), 0 1px 3px rgba(0, 0, 0, .6);
}

/* ---- 落点气泡：谁在这块地上花了 / 赚了多少 ---- */
.mp-float {
  position: absolute; left: 50%; top: 40%; z-index: 9;
  max-width: 96px; padding: 2px 7px; border-radius: 999px;
  font-size: 10px; font-weight: 700; line-height: 1.25; text-align: center;
  pointer-events: none; white-space: normal;
  transform: translate(-50%, -50%);
  box-shadow: 0 5px 14px -5px rgba(0, 0, 0, .85);
  animation: mp-float-up 1.5s cubic-bezier(.2, .8, .3, 1) both;
}
@keyframes mp-float-up {
  0% { opacity: 0; transform: translate(-50%, -20%) scale(.7); }
  16% { opacity: 1; transform: translate(-50%, -60%) scale(1.06); }
  72% { opacity: 1; transform: translate(-50%, -125%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -190%) scale(.94); }
}
.mp-float.k-buy { background: #2f8f5b; color: #fff; }
.mp-float.k-pay { background: #c0453c; color: #fff; }
.mp-float.k-gain { background: #d8a12a; color: #2b2410; }
.mp-float.k-item { background: #6b4fbf; color: #fff; }
.mp-float.k-info { background: rgba(22, 32, 28, .94); color: #f2eee0; }

/* ---- 中央区 ----
   棋盘中央只有 ~283px 见方，必须当「定高容器」排版。
   旧版 .mp-players 用 flex-wrap：4 张卡各 ~250px 宽 → 换行成 4 行（实测 166px），
   中央内容被顶到 319px（容器 283px）→ 首行溢出到棋盘上沿、日志溢出到下沿。
   现在玩家卡改 2×2 网格 + 整体 overflow 裁切，内容总高 ~223px，稳落在 259px 内容盒内。 */
.mp-center {
  grid-column: 2 / 14; grid-row: 2 / 14;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  padding: 10px; border-radius: 12px; overflow: hidden;
  background: radial-gradient(120% 100% at 50% 0%, rgba(255, 255, 255, .1), rgba(0, 0, 0, .22));
  border: 1px solid var(--gt-line);
}
.mp-center-head { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }

/* 当前行动者：谁在动、什么颜色，一眼可见（旧版只在右栏玩家列表里高亮，容易被忽略） */
.mp-turn { display: flex; align-items: center; gap: 7px; }
.mp-turn-av {
  width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center;
  font-size: 13px; border: 2px solid rgba(255, 255, 255, .5);
  box-shadow: 0 4px 12px -4px rgba(0, 0, 0, .8);
}
.mp-turn-name { font-size: 14px; font-weight: 700; letter-spacing: .02em; }

/* 骰子：尺寸用固定值 —— 牌桌全屏是「逻辑画布 + 整体缩放」，vw/vh 拿到的是真实视口，
   在缩放画布里会算错（桌面放大后骰子会大得离谱）。 */
.mp-dice { display: flex; gap: 12px; --mdy-size: 42px; flex: none; }

.mp-log {
  width: 100%; max-width: min(100%, 620px); margin-inline: auto;
  display: flex; flex-direction: column; gap: 2px;
  font-size: 11px; color: var(--gt-ink-dim); text-align: center;
}
.mp-log-row {
  animation: gt-pop .2s ease-out both;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
@media (prefers-reduced-motion: reduce) {
  .mp-float { animation-duration: .01ms; }
  .mp-tok { animation: none !important; }
}

/* ---- 右侧（只剩「棋局信息 + 操作」，玩家列表已挪进棋盘中央） ---- */
.mp-side { display: flex; flex-direction: column; gap: 10px; min-width: 0; min-height: 0; overflow-y: auto; scrollbar-width: thin; }

/* 玩家 2×2：一张紧凑卡 = 头像 + 名字(技能) + 现金·地产·道具。
   中央区在横屏时变宽（棋盘不再正方形，中央跟着变成 12/14 的宽矩形），
   所以给玩家卡与日志各封一个上限并居中 —— 不封的话一张卡会被拉成 400px 宽，
   头像和名字之间空一大片，比窄屏还难看。 */
.mp-players {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px 6px;
  width: 100%; min-width: 0;
  max-width: min(100%, 460px); margin-inline: auto;
}
.mp-players > :only-child { grid-column: 1 / -1; }
.mp-pcard {
  display: flex; align-items: center; gap: 5px; padding: 3px 7px 3px 3px; border-radius: 10px;
  background: rgba(0, 0, 0, .3); border: 1px solid var(--gt-line);
  min-width: 0;
}
.mp-pcard.on { border-color: var(--gt-gold); box-shadow: 0 0 14px -3px rgba(233, 200, 119, .75); }
.mp-pcard.out { opacity: .45; }
.mp-pav {
  width: 19px; height: 19px; border-radius: 50%; flex: none; display: grid; place-items: center;
  font-size: 10px; border: 1px solid rgba(255, 255, 255, .45);
}
.mp-ptx { min-width: 0; display: flex; flex-direction: column; gap: 0; }
.mp-ptx b { font-size: 10.5px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mp-ptx b em { font-style: normal; font-weight: 400; color: var(--gt-gold); font-size: 9px; }
.mp-ptx i { font-style: normal; font-size: 9.5px; color: var(--gt-ink-dim); font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
/* 现金 count-up 闪色（v2.46.20）：收钱鎏金、付钱砖红，900ms 后回落 */
.mp-ptx i.up { color: var(--gt-gold, #d4a24a); transition: color .5s; }
.mp-ptx i.down { color: #e05a5a; transition: color .5s; }
@media (prefers-reduced-motion: reduce) {
  .mp-ptx i.up, .mp-ptx i.down { transition: none; }
}

.mp-here { padding: 8px 10px; border-radius: 12px; background: rgba(0, 0, 0, .26); border: 1px solid var(--gt-line); display: flex; flex-direction: column; gap: 2px; }
.mp-here-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.mp-here-row b { font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mp-here-row .gt-beans { font-size: 12px; flex: none; }
.mp-here > i { font-style: normal; font-size: 11px; color: var(--gt-ink-dim); }
.mp-here-h { font-size: 10.5px; color: var(--gt-ink-dim); margin-bottom: 3px; }
.mp-here-b { display: flex; flex-direction: column; gap: 2px; }
.mp-here-b b { font-size: 14px; }
.mp-here-b i { font-style: normal; font-size: 11px; color: var(--gt-ink-dim); }

/* 操作区吸底常驻：右栏再长也不会把「掷骰 / 购地 / 盖房」挤出屏幕（全屏时右栏内部滚动） */
.mp-ops {
  justify-content: flex-start; position: sticky; bottom: -2px; z-index: 2;
  padding: 8px 0 2px;
  background: linear-gradient(180deg, rgba(6, 22, 18, 0), rgba(6, 22, 18, .94) 38%);
}
/* 道具卡徽章（v2.46.25）：紧凑小号、自动换行，×N 角标标数量 —— 一手 8 张卡也只占两三行 */
.mp-ops .mp-item { padding: 4px 10px; font-size: 12px; }
.mp-item-n {
  font-style: normal; font-weight: 700; margin-left: 3px; padding: 0 5px;
  border-radius: 999px; font-size: 10px; line-height: 1.5;
  background: rgba(233, 200, 119, .2); color: var(--gt-gold, #e9c877);
}
/* 在线：经营 / 拍卖 / 交易（页内块，非弹窗） */
.mp-manage, .mp-auction, .mp-trades {
  display: flex; flex-direction: column; gap: 5px;
  padding: 9px 11px; border-radius: 12px;
  background: rgba(0, 0, 0, .26); border: 1px solid var(--gt-line);
}
.mp-manage .gt-actions, .mp-auction .gt-actions, .mp-trade-row .gt-actions { flex-wrap: wrap; gap: 6px; }
.mp-trade-row { display: flex; flex-direction: column; gap: 4px; }
.mp-trade-row i { font-style: normal; font-size: 11px; color: var(--gt-ink-dim); }
.mp-auction .mp-here-b i { font-style: normal; font-size: 11px; color: var(--gt-ink-dim); }
.mp-bid {
  width: 88px; padding: 4px 8px; border-radius: 8px;
  background: rgba(0, 0, 0, .3); color: var(--gt-ink, #eee);
  border: 1px solid var(--gt-line); font-size: 12px;
}


@media (max-width: 900px) {
  .mp { min-height: 0; }
  /* 这里旧版写死 `.mp-cname { font-size: 8px }`：格子大字却很小，名字反而更看不清。
     现在字号一律由 `--mp-cell` 决定（见 .mp-cname），全尺寸区间都落在格内，
     不再需要这条窄屏兜底。 */
}
</style>

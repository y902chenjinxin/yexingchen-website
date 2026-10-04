<template>
  <div class="gt-landscape">
    <div class="gt-shell mp" :class="{ 'is-tilt': tilt }">
      <!-- ===== 棋盘 ===== -->
      <div class="mp-boardwrap">
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
                :style="{ background: COLORS[p.id] }"
                :title="p.name"
              >{{ p.avatar }}</span>
            </div>
          </div>

          <!-- 中央信息区 -->
          <div class="mp-center">
            <div class="mp-center-head">
              <span class="gt-pill gold">第 {{ game.round }} 轮</span>
              <span class="gt-pill">{{ phaseText }}</span>
            </div>
            <div class="mp-dice" :class="{ rolling: game.rolling }">
              <span v-for="(d, i) in game.dice" :key="i" class="mp-die">{{ DICE_FACE[d] }}</span>
            </div>
            <div class="mp-log">
              <div v-for="(l, i) in game.log.slice(-6)" :key="i" class="mp-log-row">{{ l }}</div>
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

        <!-- 玩家列表 -->
        <div class="mp-players">
          <div
            v-for="p in game.players"
            :key="p.id"
            class="mp-pcard"
            :class="{ on: p.id === cur.id && !game.over, out: !p.alive }"
          >
            <span class="mp-pav" :style="{ background: COLORS[p.id] }">{{ p.avatar }}</span>
            <div class="mp-ptx">
              <b>{{ p.name }}<em v-if="p.skill"> · {{ SKILLS[p.skill].name }}</em></b>
              <i>💰 {{ fmt(p.cash) }} · 地产 {{ ownedCount(p) }} · 道具 {{ p.items.length }}</i>
            </div>
            <span v-if="!p.alive" class="gt-seat-badge">已破产</span>
          </div>
        </div>

        <!-- 当前地块 -->
        <div class="mp-here">
          <div class="mp-here-h">当前所在</div>
          <div class="mp-here-b">
            <b>{{ hereCell.name }}</b>
            <i v-if="hereCell.price">地价 {{ fmt(hereCell.price) }} · 租金 {{ fmt(rentOf(hereCell)) }}</i>
            <i v-else>{{ hereHint }}</i>
          </div>
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
              v-for="it in (isOnline && !oIsMyTurn ? [] : cur.items)"
              :key="it"
              class="gt-btn ghost"
              :disabled="isOnline ? acting : (busy || cur.isAI)"
              :title="ITEMS[it].desc"
              @click="useItem(it)"
            >{{ ITEMS[it].icon }} {{ ITEMS[it].name }}</button>
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

        <!-- 家庭豆子 -->
        <div class="mp-wallet">
          <span class="gt-sub">我的欢乐豆</span>
          <span class="gt-beans">🪙 {{ fmt(wallet.beans) }}</span>
        </div>
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { reportSettle, gameEconomyApi } from '@/api/gameEconomy'

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

const DICE_FACE = ['', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅']

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
const tilt = ref(true)
const toast = ref('')
const wallet = reactive({ beans: 0 })

let toastTimer = null
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

/* ---------------- 移动 ---------------- */
function moveBy(p, steps) {
  const before = p.pos
  p.pos = (p.pos + steps) % 52
  if (steps > 0 && p.pos < before) { p.cash += 2000; log(`${p.name} 经过起点，领取 2000 豆`) }
  return p.pos
}

function tokensRefresh() { /* 触发 tokensAt 重算 */ game.cells = [...game.cells] }

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
  game.dice = [d1, d2]
  await sleep(360)
  game.rolling = false
  const steps = d1 + d2
  log(`🎲 ${p.name} 掷出 ${d1}+${d2}=${steps}`)
  moveBy(p, steps)
  tokensRefresh()
  await sleep(160)
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
  let guard = 0
  do {
    game.curIdx = (game.curIdx + 1) % game.players.length
    if (game.curIdx === 0) game.round += 1
    guard += 1
  } while (!game.players[game.curIdx].alive && guard < 40)
  // AI 自动行动
  if (game.players[game.curIdx]?.isAI) setTimeout(() => aiTurn(), 520)
}

function nextTurn() { endTurn() }

async function resolveLanding(p) {
  const c = game.cells[p.pos]
  if (c.type === 'city') {
    if (c.owner == null) {
      // 无主：AI 自动判断是否购买
      if (p.isAI) {
        if (p.cash > c.price * 1.6) { p.cash -= c.price; grantCell(p, c.idx); log(`🏙 ${p.name} 买下 ${c.name}（${fmt(c.price)}）`) }
        else log(`${p.name} 放弃购买 ${c.name}`)
      }
    } else if (c.owner !== p.id) {
      const owner = game.players[c.owner]
      if (!owner?.alive) { c.owner = null; c.level = 0; return }
      if (p.freeRent) { log(`${p.name} 使用免租，跳过 ${c.name} 租金`); return }
      if (p.immune) { log(`${p.name} 的天使卡免除了 ${c.name} 租金`); return }
      let rent = rentOf(c)
      if (p.doubleRent) rent *= 2
      log(`💸 ${p.name} 向 ${owner.name} 支付 ${c.name} 租金 ${fmt(rent)} 豆`)
      p.cash -= rent
      owner.cash += rent
      if (p.cash < 0) pay(p, 0)
    } else if (p.isAI && c.level < 4 && p.cash > buildCost(c) * 2.2) {
      p.cash -= buildCost(c); c.level += 1
      log(`🏠 ${p.name} 把 ${c.name} 升到 Lv${c.level}`)
    }
  } else if (c.type === 'chance') {
    const card = CHANCE[Math.floor(Math.random() * CHANCE.length)]
    log(`🃏 机会：${card.text}`)
    card.fn(p, game)
  } else if (c.type === 'fate') {
    const card = FATE[Math.floor(Math.random() * FATE.length)]
    log(`🎴 命运：${card.text}`)
    card.fn(p, game)
  } else if (c.type === 'tax') {
    const t = Math.round(p.cash * 0.08)
    log(`🧾 ${p.name} 缴税 ${fmt(t)} 豆`)
    pay(p, t)
  } else if (c.type === 'item') {
    const keys = Object.keys(ITEMS)
    const it = keys[Math.floor(Math.random() * keys.length)]
    p.items.push(it)
    log(`🎁 ${p.name} 获得道具「${ITEMS[it].name}」`)
  } else if (c.type === 'gotojail') {
    p.pos = 13
    p.jailTurns = 1
    log(`🚔 ${p.name} 被送进监狱`)
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
  game.dice = t.last_dice || [1, 1]
  game.rolling = false
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
  if (isOnline.value) { syncFromView(props.onlineView); return }
  newGame()
  emit('room-lock')
  try {
    const res = await gameEconomyApi.wallet()
    const d = res?.data || {}
    if (d.beans != null) wallet.beans = d.beans
  } catch { /* 未登录或接口不可用时静默 */ }
  setTimeout(() => { if (cur.value?.isAI) aiTurn() }, 600)
})

watch(() => game.curIdx, () => {
  if (isOnline.value) return   // 在线由服务端推进
  const p = cur.value
  if (p?.isAI && !game.over && !busy.value) setTimeout(() => aiTurn(), 480)
})
</script>

<style scoped>
.mp {
  display: grid; grid-template-columns: minmax(0, 1fr) 306px; gap: 14px;
  padding: 14px; min-height: 640px;
}
@media (max-width: 1100px) { .mp { grid-template-columns: minmax(0, 1fr); } }

/* ---- 棋盘 ---- */
.mp-boardwrap { perspective: 1500px; display: flex; align-items: center; justify-content: center; }
.mp-board {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--n), 1fr);
  grid-template-rows: repeat(var(--n), 1fr);
  width: min(100%, 760px); aspect-ratio: 1;
  gap: 3px;
  transform-style: preserve-3d;
}
.mp.is-tilt .mp-board { transform: rotateX(15deg) scale(.985); }

.mp-cell {
  position: relative; border-radius: 5px; overflow: hidden;
  background: linear-gradient(170deg, #f6f1e4, #e7dfcc);
  border: 1px solid rgba(120, 100, 60, .35);
  box-shadow: 0 4px 0 rgba(90, 74, 44, .45), 0 8px 12px -8px rgba(0, 0, 0, .8);
  display: flex; flex-direction: column;
  color: #2b2413; min-width: 0;
  transition: box-shadow .2s, filter .2s;
}
.mp-cell.hl { box-shadow: 0 0 0 2px var(--gt-gold), 0 4px 0 rgba(90, 74, 44, .45); }
.mp-cell-top { height: 5px; background: rgba(120, 100, 60, .3); }
.mp-houses { display: block; font-size: 6px; line-height: 5px; text-align: center; }
.mp-cell-body {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 1px; padding: 1px;
}
.mp-cname {
  font-size: 9px; font-weight: 700; line-height: 1.05; text-align: center;
  word-break: break-all; max-width: 100%;
}
.mp-cprice { font-style: normal; font-size: 7.5px; opacity: .72; }
.mp-cell.t-start { background: linear-gradient(170deg, #ffe9a8, #f3cf72); }
.mp-cell.t-jail, .mp-cell.t-gotojail { background: linear-gradient(170deg, #f0d7d0, #dfb4a8); }
.mp-cell.t-park { background: linear-gradient(170deg, #d7ecdc, #b6d8c0); }
.mp-cell.t-chance { background: linear-gradient(170deg, #dceaf7, #bcd6ee); }
.mp-cell.t-fate { background: linear-gradient(170deg, #ecdcf5, #d5bceb); }
.mp-cell.t-tax { background: linear-gradient(170deg, #f6e2c8, #e9c79a); }
.mp-cell.t-item { background: linear-gradient(170deg, #fbe6ef, #f0c6d9); }

.mp-tokens {
  position: absolute; inset: auto 1px 1px 1px; display: flex; flex-wrap: wrap;
  gap: 1px; justify-content: center;
}
.mp-tok {
  width: 13px; height: 13px; border-radius: 50%; font-size: 8px;
  display: grid; place-items: center; color: #fff;
  border: 1px solid rgba(255, 255, 255, .85);
  box-shadow: 0 1px 3px rgba(0, 0, 0, .55);
}

/* ---- 中央区 ---- */
.mp-center {
  grid-column: 2 / 14; grid-row: 2 / 14;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px;
  padding: 16px; border-radius: 12px;
  background: radial-gradient(120% 100% at 50% 0%, rgba(255, 255, 255, .1), rgba(0, 0, 0, .22));
  border: 1px solid var(--gt-line);
}
.mp-center-head { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.mp-dice { display: flex; gap: 10px; font-size: 44px; line-height: 1; color: var(--gt-gold); }
.mp-dice.rolling { animation: mp-shake .32s linear infinite; }
@keyframes mp-shake {
  0%, 100% { transform: translateY(0) rotate(0); }
  25% { transform: translateY(-4px) rotate(-8deg); }
  75% { transform: translateY(4px) rotate(8deg); }
}
.mp-log {
  width: 100%; max-width: 460px; display: flex; flex-direction: column; gap: 3px;
  font-size: 11.5px; color: var(--gt-ink-dim); text-align: center;
}
.mp-log-row { animation: gt-pop .2s ease-out both; }

/* ---- 右侧 ---- */
.mp-side { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.mp-players { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow-y: auto; }
.mp-pcard {
  display: flex; align-items: center; gap: 8px; padding: 6px 9px; border-radius: 12px;
  background: rgba(0, 0, 0, .24); border: 1px solid var(--gt-line);
}
.mp-pcard.on { border-color: var(--gt-gold); box-shadow: 0 0 14px -3px rgba(233, 200, 119, .6); }
.mp-pcard.out { opacity: .45; }
.mp-pav {
  width: 28px; height: 28px; border-radius: 50%; flex: none; display: grid; place-items: center;
  font-size: 14px; border: 1px solid rgba(255, 255, 255, .4);
}
.mp-ptx { min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.mp-ptx b { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mp-ptx b em { font-style: normal; font-weight: 400; color: var(--gt-gold); font-size: 10.5px; }
.mp-ptx i { font-style: normal; font-size: 10.5px; color: var(--gt-ink-dim); }

.mp-here { padding: 9px 11px; border-radius: 12px; background: rgba(0, 0, 0, .26); border: 1px solid var(--gt-line); }
.mp-here-h { font-size: 10.5px; color: var(--gt-ink-dim); margin-bottom: 3px; }
.mp-here-b { display: flex; flex-direction: column; gap: 2px; }
.mp-here-b b { font-size: 14px; }
.mp-here-b i { font-style: normal; font-size: 11px; color: var(--gt-ink-dim); }

.mp-ops { justify-content: flex-start; }
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
.mp-wallet { display: flex; align-items: center; justify-content: space-between; padding-top: 4px; }

@media (max-width: 900px) {
  .mp { min-height: 0; }
  .mp-cname { font-size: 8px; }
}
</style>

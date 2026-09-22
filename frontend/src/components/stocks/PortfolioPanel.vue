<template>
  <section class="pp">
    <!-- 资产配置：按个股持仓市值占比 -->
    <div class="pp-card glass">
      <div class="pp-head">
        <span class="pp-title">资产配置</span>
        <span class="pp-sub">按个股市值占比</span>
      </div>
      <div v-if="alloc.length" class="pp-alloc">
        <DonutChart :data="alloc" unit="只" aria-label="持仓资产配置占比" />
        <ul class="pp-legend">
          <li v-for="a in alloc" :key="a.category" class="pp-leg">
            <i class="pp-dot" :style="{ background: a.color }"></i>
            <span class="pp-leg-name">{{ a.category }}</span>
            <span class="pp-leg-pct">{{ a.pct.toFixed(1) }}%</span>
          </li>
        </ul>
      </div>
      <p v-else class="pp-empty">给自选股补上「数量」和「成本价」后，这里显示各股市值占比</p>
    </div>

    <!-- 每日盈亏走势：按每日收盘快照环比 -->
    <div class="pp-card glass">
      <div class="pp-head">
        <span class="pp-title">每日盈亏走势</span>
        <span class="pp-sub">快照环比 · 红盈绿亏</span>
        <button class="pp-btn" :disabled="recording" @click="$emit('record')">
          {{ recording ? '记录中…' : '记今日快照' }}
        </button>
      </div>
      <template v-if="pnlSeries.length">
        <svg class="pp-trend" :viewBox="`0 0 ${TW} ${TH}`" preserveAspectRatio="none" role="img"
          aria-label="每日盈亏柱状图">
          <line class="pp-zero" :x1="8" :x2="TW - 8" :y1="zeroY" :y2="zeroY" />
          <rect
            v-for="(d, i) in pnlSeries"
            :key="d.date"
            class="pp-bar"
            :class="d.pnl >= 0 ? 'is-up' : 'is-down'"
            :x="barX(i)"
            :y="Math.min(zeroY, barY(d.pnl))"
            :width="barW"
            :height="Math.max(1.5, Math.abs(barY(d.pnl) - zeroY))"
            rx="2"
          />
        </svg>
        <div class="pp-xrow">
          <span v-for="(d, i) in pnlSeries" :key="'x' + d.date" class="pp-x">
            {{ i % xStep === 0 ? shortDate(d.date) : '' }}
          </span>
        </div>
        <div class="pp-range">
          <span class="pp-range-i">区间合计 <b :class="pnlCls(rangeSum)">{{ sign(rangeSum) }}¥{{ fmt(Math.abs(rangeSum)) }}</b></span>
          <span class="pp-range-i">最大单日 <b :class="pnlCls(maxUp)">{{ sign(maxUp) }}¥{{ fmt(Math.abs(maxUp)) }}</b></span>
          <span class="pp-range-i">最大回撤 <b :class="pnlCls(maxDown)">{{ sign(maxDown) }}¥{{ fmt(Math.abs(maxDown)) }}</b></span>
        </div>
      </template>
      <p v-else class="pp-empty">
        需至少 2 天收盘快照才能算出环比盈亏（当前已记录 {{ snapshotDays }} 天）。
        交易日 15:35 后自动记录，明天起走势会自己长出来。
      </p>
    </div>

    <!-- 每日盈亏日历 -->
    <div class="pp-card glass pp-cal-card">
      <div class="pp-head">
        <span class="pp-title">每日盈亏日历</span>
        <span class="pp-sub">{{ calMonthLabel }}</span>
      </div>
      <div class="pp-cal-week">
        <span v-for="w in WEEK" :key="w">{{ w }}</span>
      </div>
      <div class="pp-cal">
        <div
          v-for="c in calCells"
          :key="c.key"
          class="pp-cell"
          :class="cellCls(c)"
        >
          <template v-if="!c.blank">
            <span class="pp-cell-d">{{ c.day }}<i v-if="c.estimated" class="pp-cell-est" aria-label="估算值">~</i></span>
            <span v-if="c.pnl !== null" class="pp-cell-v">{{ sign(c.pnl) }}{{ fmt(Math.abs(c.pnl), 0) }}</span>
          </template>
        </div>
      </div>
      <p class="pp-cal-tip">
        有数据的日期按「红涨绿跌」染色：红色为当日盈利，绿色为当日亏损。
        今天的数值取自实时行情，历史数值来自每日收盘快照。
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import DonutChart from '@/components/finance/DonutChart.vue'

const props = defineProps({
  holdings: { type: Array, default: () => [] },   // summary.holdings
  snapshots: { type: Array, default: () => [] },  // GET /stocks/snapshots
  todayPnl: { type: Number, default: 0 },
  recording: { type: Boolean, default: false },
})
defineEmits(['record'])

/* 配色全部取设计 token，避免硬编码 hex（项目 CSS 门控要求） */
const PALETTE = [
  'var(--lj-seal)', 'var(--lj-dai)', 'var(--lj-ochre)', 'var(--yq-rain)',
  'var(--yq-gold)', 'var(--ls-jade)', 'var(--lj-vermilion)', 'var(--lj-mist)',
]

const WEEK = ['日', '一', '二', '三', '四', '五', '六']
const TW = 600
const TH = 110
const zeroY = TH / 2

function sign(v) { return v > 0 ? '+' : '' }
function fmt(v, n = 2) { return Number(v || 0).toFixed(n) }
function pnlCls(v) { return v > 0 ? 'up' : v < 0 ? 'down' : 'flat' }
function shortDate(d) { return (d || '').slice(5).replace('-', '/') }
function localDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/* ---------- 资产配置 ---------- */
const alloc = computed(() => {
  const rows = props.holdings
    .filter(h => h.quantity && h.price)
    .map(h => ({ name: h.name || h.code, amount: Number(h.price) * Number(h.quantity) }))
    .filter(r => r.amount > 0)
    .sort((a, b) => b.amount - a.amount)
  const total = rows.reduce((s, r) => s + r.amount, 0)
  return rows.map((r, i) => ({
    category: r.name,
    amount: r.amount,
    color: PALETTE[i % PALETTE.length],
    pct: total ? (r.amount / total) * 100 : 0,
  }))
})

/* ---------- 每日盈亏序列（快照环比，首日无环比故从第 2 天起） ---------- */
const snapshotDays = computed(() => (props.snapshots || []).length)

const pnlSeries = computed(() => {
  const s = props.snapshots || []
  const out = []
  for (let i = 1; i < s.length; i++) {
    const cur = Number(s[i].hold_pnl) || 0
    const prev = Number(s[i - 1].hold_pnl) || 0
    out.push({ date: s[i].date, pnl: cur - prev })
  }
  return out
})

const maxAbs = computed(() => Math.max(...pnlSeries.value.map(d => Math.abs(d.pnl)), 1))
const barW = computed(() => {
  const n = Math.max(pnlSeries.value.length, 1)
  const step = (TW - 20) / n
  return Math.max(3, Math.min(30, step - 6))
})
const xStep = computed(() => Math.max(1, Math.ceil(pnlSeries.value.length / 7)))

function barX(i) {
  const n = Math.max(pnlSeries.value.length, 1)
  const step = (TW - 20) / n
  return 10 + i * step + (step - barW.value) / 2
}
function barY(v) {
  const h = (TH / 2 - 8) * (Math.abs(v) / maxAbs.value)
  return v >= 0 ? zeroY - h : zeroY + h
}

const rangeSum = computed(() => pnlSeries.value.reduce((s, d) => s + d.pnl, 0))
const maxUp = computed(() => Math.max(0, ...pnlSeries.value.map(d => d.pnl)))
const maxDown = computed(() => Math.min(0, ...pnlSeries.value.map(d => d.pnl)))

/* ---------- 日历 ---------- */
const todayStr = localDate(new Date())
const calMonthLabel = computed(() => {
  const now = new Date()
  return `${now.getFullYear()} 年 ${now.getMonth() + 1} 月`
})

const calCells = computed(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = now.getMonth()
  const startPad = new Date(y, m, 1).getDay()
  const daysInMonth = new Date(y, m + 1, 0).getDate()

  // 历史日盈亏取自快照环比（s[i-1] → s[i] 的差归到 s[i] 这一天）
  const byDate = new Map()
  const s = props.snapshots || []
  for (let i = 1; i < s.length; i++) {
    byDate.set(s[i].date, (Number(s[i].hold_pnl) || 0) - (Number(s[i - 1].hold_pnl) || 0))
  }

  // 昨天的估值：取最近一个快照的 hold_pnl（当作「截至昨日的累计盈亏」）作为锚，
  // 之后几天用「今日实时累计 - 昨日累计」折算填充。
  // 这样日历在「今天 / 昨天 / 周末 / 节假日」都能看到数字，而不是大片空白。
  // 算法：
  //   - 若今天实时累计 = T，最近一个快照累计 = P（snapshots 里最后一条）
  //     则「今天实时盈亏 = T - P」应当归到 today
  //     但中间（最近快照日 + 1 → 昨天）若有空白，可按 "日均补差" 或 "归零" 处理
  //   - 简化做法：直接把 P 与 T 之间的差值按 1 天归到「昨天」（最近一次会话跨越的天数按 1 天算）
  //     实际更合理的方案：把 T-P 全归到昨天，让昨天显示完整增量
  const lastSnap = s.length ? s[s.length - 1] : null
  const lastSnapPnl = lastSnap ? Number(lastSnap.hold_pnl) || 0 : null
  const lastSnapDate = lastSnap ? lastSnap.date : null
  const todayLivePnl = Number(props.todayPnl) || 0
  // today 实时累计 ≈ lastSnapPnl + todayLivePnl
  const todayCum = lastSnapPnl == null ? todayLivePnl : (lastSnapPnl + todayLivePnl)
  // 「昨天」那一格：若日历格昨天没有快照值，则用 (今天累计 - 最近快照累计)
  // 但此差值的语义是「从最近一次落库到现在的所有变化」，全归到昨天更直观
  const yesterdayStr = (() => {
    const d = new Date(now)
    d.setDate(d.getDate() - 1)
    return localDate(d)
  })()

  // 用一个 Map 缓存每一天的 pnl 计算结果
  const cells = []
  for (let i = 0; i < startPad; i++) cells.push({ blank: true, key: `pad-${i}` })
  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    let pnl = byDate.has(ds) ? byDate.get(ds) : null
    let estimated = false
    if (pnl === null) {
      // 兜底：若这一天能落在「最近快照日」与「今天」之间，且 lastSnapDate 早于今天，
      //      视为「最近落库到现在的全量变化」，统一归到「昨天」一格（最直观、最不易让用户困惑）
      if (lastSnapDate && ds > lastSnapDate && ds < todayStr) {
        // 中间空白日（最近快照之后到今天之前）的差值全部归给「昨天」
        if (ds === yesterdayStr && lastSnapPnl != null) {
          pnl = todayCum - lastSnapPnl
          estimated = true
        }
      }
    }
    cells.push({
      blank: false,
      key: ds,
      day: d,
      date: ds,
      pnl,
      isToday: ds === todayStr,
      future: ds > todayStr,
      estimated,
    })
  }

  // 今天用实时估值覆盖（保证当天就有数）
  // 注意：覆盖必须在 estimated 填充之后，否则会覆盖掉昨日的估算
  for (const c of cells) {
    if (!c.blank && c.isToday) {
      c.pnl = todayLivePnl
      c.estimated = false
    }
  }
  return cells
})

function cellCls(c) {
  if (c.blank) return 'is-blank'
  const cls = []
  if (c.isToday) cls.push('is-today')
  if (c.future && c.pnl === null) cls.push('is-future')
  if (c.pnl !== null && c.pnl > 0) cls.push('is-up')
  else if (c.pnl !== null && c.pnl < 0) cls.push('is-down')
  return cls
}
</script>

<style scoped>
.pp { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
.pp-cal-card { grid-column: 1 / -1; }
.pp-card { border-radius: 16px; padding: 16px 20px; }

.pp-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.pp-title { font-size: 15px; letter-spacing: .08em; color: var(--lj-text); }
.pp-sub { font-size: 12px; color: var(--lj-text-3); }
.pp-head .pp-btn { margin-left: auto; }
.pp-btn {
  border-radius: 8px; padding: 4px 10px; font-size: 12px; cursor: pointer;
  background: transparent; color: var(--lj-text); border: 1px solid var(--lj-line);
  transition: all .2s;
}
.pp-btn:hover:not(:disabled) { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.pp-btn:disabled { opacity: .5; cursor: not-allowed; }

.pp-empty { margin: 0; padding: 18px 4px; font-size: 12px; line-height: 1.8; color: var(--lj-text-3); }

/* 资产配置 */
.pp-alloc { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.pp-legend { list-style: none; margin: 0; padding: 0; flex: 1; min-width: 140px; }
.pp-leg { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12px; }
.pp-dot { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.pp-leg-name { flex: 1; color: var(--lj-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pp-leg-pct { color: var(--lj-text-2); font-variant-numeric: tabular-nums; }

/* 每日盈亏走势 */
.pp-trend { width: 100%; height: 110px; display: block; }
.pp-zero { stroke: var(--lj-line-strong); stroke-width: 1; stroke-dasharray: 4 4; }
.pp-bar.is-up { fill: var(--pnl-up); }
.pp-bar.is-down { fill: var(--pnl-down); }
.pp-xrow { display: flex; margin-top: 4px; }
.pp-x { flex: 1; text-align: center; font-size: 10px; color: var(--lj-text-3); }
.pp-range { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 10px; font-size: 12px; color: var(--lj-text-3); }
.pp-range-i b { font-weight: 600; font-variant-numeric: tabular-nums; }

/* 日历 */
.pp-cal-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-bottom: 6px; }
.pp-cal-week span { text-align: center; font-size: 11px; color: var(--lj-text-3); }
.pp-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
.pp-cell {
  min-height: 46px; border-radius: 8px; padding: 5px 7px; box-sizing: border-box;
  display: flex; flex-direction: column; justify-content: space-between;
  border: 1px solid transparent; background: rgba(74, 95, 99, .06);
}
.pp-cell.is-blank { background: transparent; }
.pp-cell.is-future { background: transparent; border-style: dashed; border-color: var(--lj-line); }
.pp-cell.is-up { background: var(--pnl-up-soft); border-color: var(--pnl-up-line); }
.pp-cell.is-down { background: var(--pnl-down-soft); border-color: var(--pnl-down-line); }
.pp-cell.is-today { box-shadow: 0 0 0 1px var(--lj-seal) inset; }
.pp-cell-d { font-size: 11px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.pp-cell-est { font-style: normal; margin-left: 2px; opacity: .55; font-size: 9px; }
.pp-cell-v { font-size: 11px; color: var(--lj-text); font-variant-numeric: tabular-nums; align-self: flex-end; }
.pp-cal-tip { margin: 12px 0 0; font-size: 11px; line-height: 1.7; color: var(--lj-text-3); }

.up { color: var(--pnl-up); }
.down { color: var(--pnl-down); }
.flat { color: var(--lj-text); }

@media (max-width: 860px) {
  .pp { grid-template-columns: 1fr; }
  .pp-cell { min-height: 40px; padding: 4px 5px; }
}
</style>

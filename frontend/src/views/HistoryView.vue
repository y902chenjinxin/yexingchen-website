<!--
  HistoryView.vue
  玄黄・历史上的今天 独立岛页（v2.44）
  - 时光藤蔓：整幅装饰性藤蔓，不展示任何事件卡片。
  - 上方藤蔓区可【左滑】回望昨天/前天/…，【右滑】展望明天/后天/…，逐日切换日期。
  - 中央"此刻节点"显示所选日期 + 相对标签（今天/昨天/明天/…天前/…天后）。
  - 下方铺列所选日期发生的具体历史事件（按年份倒序的简单列表）。
-->
<template>
  <IslandInnerBase
    type="history"
    title="历史上的今天"
    subtitle="每一天，都藏着未来的线索"
  >
    <template #toolbar>
      <button class="ht-btn ghost" :disabled="isToday" @click="goToday">回到今天</button>
      <button class="ht-btn ghost" :disabled="loading" @click="load(true)">
        {{ loading ? '加载中…' : '⟳ 刷新' }}
      </button>
    </template>

    <!-- ============ 藤蔓（装饰 + 左滑右滑换日） ============ -->
    <section class="ht-vine glass">
      <div class="ht-vine-head">
        <span class="ht-tl-title">时光藤蔓</span>
        <span class="ht-tl-tip">左滑回望昨天 ┆ 右滑展望明天</span>
      </div>

      <div
        ref="stageEl"
        class="ht-vine-stage"
        :class="{ 'is-scrubbing': scrubbing }"
        @pointerdown="onScrubStart"
        @pointermove="onScrubMove"
        @pointerup="onScrubEnd"
        @pointercancel="onScrubEnd"
      >
        <svg
          class="ht-vine-svg"
          viewBox="0 0 1000 300"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="vineGradMain" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stop-color="#5f8a6a" />
              <stop offset=".5" stop-color="#3c7d63" />
              <stop offset="1" stop-color="#2e6e52" />
            </linearGradient>
            <linearGradient id="berryGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#f6c35e" />
              <stop offset="1" stop-color="#c4652f" />
            </linearGradient>
            <linearGradient id="leafA" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#8fbf6e" />
              <stop offset="1" stop-color="#4c8a4f" />
            </linearGradient>
            <radialGradient id="leafB" cx=".35" cy=".3" r=".9">
              <stop offset="0" stop-color="#a9cf7f" />
              <stop offset="1" stop-color="#5a9a52" />
            </radialGradient>
          </defs>

          <!-- 远景藤蔓：弱、模糊，制造纵深 -->
          <path :d="pathFar" class="ht-strand strand-far" />
          <!-- 主藤蔓 -->
          <path :d="pathMain" class="ht-strand strand-main" />
          <!-- 叶片点缀 -->
          <g v-for="lf in leaves" :key="lf.k" :transform="`translate(${lf.x} ${lf.y}) rotate(${lf.rot})`">
            <ellipse class="ht-leaf" :rx="lf.rx" :ry="lf.ry" :fill="lf.fill">
              <animate
                v-if="!prefersReduced"
                attributeName="ry" :values="`${lf.ry};${lf.ry * 0.62};${lf.ry}`"
                dur="3.8s" repeatCount="indefinite" :begin="`${lf.delay}s`"
              />
            </ellipse>
          </g>
          <g v-for="b in berries" :key="b.k" :transform="`translate(${b.x} ${b.y})`">
            <circle r="5.5" class="ht-berry" />
            <circle r="2.3" class="ht-berry-core" />
          </g>
        </svg>

        <!-- 此刻节点：中央游标线 + 日期读数 -->
        <div class="ht-cursor-zone">
          <span class="ht-cursor-line"></span>
          <div class="ht-datebox">
            <span class="ht-date-main">{{ dateLabel }}</span>
            <span class="ht-date-tag" :class="{ on: isToday }">{{ rel.tag }} · {{ rel.text }}</span>
          </div>
        </div>

        <!-- 拖拽遮罩：捕获指针，避免点到别处误触 -->
        <div class="ht-scrub" aria-hidden="true"></div>
      </div>

      <!-- 逐日导航（精确微调） -->
      <div class="ht-datebar">
        <button class="ht-btn ghost ht-day" @click="nudge(-1)" aria-label="前一天">‹ 前一天</button>
        <span class="ht-datebar-hint">左滑 / 右滑 换日 · 按位置拖动可连续回望或展望</span>
        <button class="ht-btn ghost ht-day" @click="nudge(1)" aria-label="后一天">后一天 ›</button>
      </div>
    </section>

    <!-- ============ 事件列表（所选日期 · 铺列展示） ============ -->
    <section class="ht-events glass">
      <div class="ht-events-head">
        <span class="ht-events-title">{{ dateLabel }} 事件</span>
        <span class="ht-events-sub">共 {{ items.length }} 条 · 按年份倒序</span>
      </div>

      <div v-if="loading && !items.length" class="ht-loading">
        <span class="ht-dot"></span><span class="ht-dot"></span><span class="ht-dot"></span>
      </div>
      <template v-else>
        <div v-if="!items.length" class="ht-empty">该日暂无内置记录，试试左滑回望或右滑展望</div>
        <ol v-else class="ht-list">
          <li v-for="(it, idx) in items" :key="`${it.year}-${idx}`" class="ht-row">
            <span class="ht-y">{{ it.year || '—' }}</span>
            <div class="ht-body">
              <span class="ht-t">{{ it.title }}</span>
              <span v-if="it.desc" class="ht-d">{{ it.desc }}</span>
            </div>
          </li>
        </ol>
      </template>
    </section>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { workbenchApi } from '@/api/workbench'

const today = new Date()
const pad = (n) => String(n).padStart(2, '0')

// 相对今天的偏移：0=今天，-1=昨天，+1=明天……
const offset = ref(0)
const MAX_OFFSET = 3650

const items = ref([])
const loading = ref(false)
const scrubbing = ref(false)
const prefersReduced = typeof window !== 'undefined'
  ? (window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false)
  : false

const stageEl = ref(null)

/* ---------- 日期换算 ---------- */
function shiftDate(base, days) {
  return new Date(base.getFullYear(), base.getMonth(), base.getDate() + days)
}
const selected = computed(() => shiftDate(today, offset.value))
const dateLabel = computed(() =>
  `${selected.value.getFullYear()} 年 ${selected.value.getMonth() + 1} 月 ${selected.value.getDate()} 日`
)
const isToday = computed(() => offset.value === 0)
const rel = computed(() => {
  const o = offset.value
  if (o === 0) return { tag: '此刻', text: '今天' }
  if (o === -1) return { tag: '回顾', text: '昨天' }
  if (o === -2) return { tag: '回顾', text: '前天' }
  if (o < 0) return { tag: '回顾', text: `${Math.abs(o)} 天前` }
  if (o === 1) return { tag: '展望', text: '明天' }
  if (o === 2) return { tag: '展望', text: '后天' }
  return { tag: '展望', text: `${o} 天后` }
})
function dayQuery() {
  const d = selected.value
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/* ---------- 藤蔓几何：横向蜿蜒（纯装饰） ---------- */
const VW = 1000
const VH = 300
const baseY = 158
const amp = 72
function vineY(t) {
  return baseY + amp * Math.sin(t * 2 * Math.PI - Math.PI / 1.7)
}
function samplePath(ampMul = 1) {
  const N = 90
  const pts = []
  for (let i = 0; i <= N; i++) {
    const t = i / N
    pts.push([t * VW, baseY + amp * ampMul * Math.sin(t * 2 * Math.PI - Math.PI / 1.7)])
  }
  let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`
  for (let i = 1; i < pts.length - 1; i++) {
    const mx = (pts[i][0] + pts[i + 1][0]) / 2
    const my = (pts[i][1] + pts[i + 1][1]) / 2
    d += ` Q ${pts[i][0].toFixed(1)} ${pts[i][1].toFixed(1)} ${mx.toFixed(1)} ${my.toFixed(1)}`
  }
  const last = pts[pts.length - 1]
  d += ` L ${last[0].toFixed(1)} ${last[1].toFixed(1)}`
  return d
}
const pathMain = samplePath(1)
const pathFar = samplePath(0.66)

const leaves = computed(() =>
  [0.12, 0.26, 0.4, 0.56, 0.7, 0.84].map((t, i) => {
    const side = i % 2 === 0 ? 1 : -1
    const rx = 15 + (i % 3) * 5
    return {
      k: i, x: t * VW + side * (18 + (i % 2) * 8), y: vineY(t) - side * 13,
      rot: side > 0 ? 20 + i * 8 : -24 - i * 6,
      rx, ry: rx * 0.45, delay: i * 0.55,
      fill: `url(#leaf${i % 2 ? 'B' : 'A'})`,
    }
  })
)
const berries = computed(() =>
  [0.2, 0.47, 0.72, 0.9].map((t, k) => ({ k, x: t * VW, y: vineY(t) + 5 }))
)

/* ---------- 左滑右滑换日 ---------- */
// 每拖 ~88px 视为 1 天；左拖(负数增量)→ offset 变小(昨天/前天…)，右拖→ 明天/后天…
const PX_PER_DAY = 88
let scrubbingActive = false
let scrubStartX = 0
let scrubStartOffset = 0
let liveOffset = 0

function pointerDelta(clientX) {
  return clientX - scrubStartX
}
function onScrubStart(e) {
  const el = stageEl.value
  if (!el) return
  scrubbingActive = true
  scrubbing.value = true
  scrubStartX = e.clientX
  scrubStartOffset = offset.value
  liveOffset = offset.value
  try { el.setPointerCapture(e.pointerId) } catch { /* 忽略 */ }
  updateFromDelta(e.clientX)
}
function onScrubMove(e) {
  if (!scrubbingActive) return
  updateFromDelta(e.clientX)
}
function updateFromDelta(clientX) {
  const delta = pointerDelta(clientX)
  // 左拖 → 负偏移（回顾昨天/前天…）
  const d = Math.round(delta / PX_PER_DAY)
  const nd = Math.max(-MAX_OFFSET, Math.min(MAX_OFFSET, scrubStartOffset + d))
  if (nd !== liveOffset) {
    liveOffset = nd
    offset.value = nd
    scheduleLoad()
  }
}
function onScrubEnd() {
  scrubbingActive = false
  scrubbing.value = false
}
function nudge(dir) {
  offset.value = Math.max(-MAX_OFFSET, Math.min(MAX_OFFSET, offset.value + dir))
  scheduleLoad()
}
function goToday() {
  offset.value = 0
  scheduleLoad()
}

/* 切换日期：延时聚合连续拖动，减少请求 */
let loadTimer = null
function scheduleLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(() => load(false), 130)
}

async function load(refresh = false) {
  loading.value = true
  try {
    const res = await workbenchApi.todayInHistory(
      refresh ? { date: dayQuery(), refresh: true } : { date: dayQuery() }
    )
    const data = (res && typeof res === 'object' && 'data' in res) ? res.data : (res || {})
    items.value = Array.isArray(data.items) ? data.items : []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<style scoped>
/* ============ 通用按钮 ============ */
.ht-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: var(--tx-strong, #e8eef6);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.ht-btn:hover:not(:disabled) { background: rgba(255, 255, 255, 0.14); }
.ht-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.ht-btn.ghost.ht-day { padding: 6px 12px; }

/* ============ 藤蔓区 ============ */
.ht-vine { margin-bottom: 18px; }
.ht-vine-head {
  display: flex; align-items: baseline; justify-content: space-between;
  padding: 4px 4px 10px;
}
.ht-tl-title { font-family: var(--font-serif, serif); font-size: 15px; letter-spacing: .06em; }
.ht-tl-tip { font-size: 12px; color: var(--tx-weak, rgba(210,220,232,.6)); }

.ht-vine-stage {
  position: relative;
  height: 300px;
  border-radius: 16px;
  overflow: hidden;
  cursor: grab;
  touch-action: pan-y;   /* 允许横向拖拽，竖向仍可滚动页面 */
  user-select: none;
}
.ht-vine-stage.is-scrubbing { cursor: grabbing; }

.ht-vine-svg {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
}
.ht-strand { fill: none; }
.strand-far {
  stroke: rgba(90, 130, 100, 0.35);
  stroke-width: 8; stroke-linecap: round;
  filter: blur(1.5px);
}
.strand-main {
  stroke: url(#vineGradMain);
  stroke-width: 14; stroke-linecap: round;
}
.ht-leaf { stroke: rgba(255, 255, 255, 0.08); stroke-width: 1; }
.ht-berry { fill: url(#berryGrad); filter: drop-shadow(0 1px 2px rgba(0,0,0,.25)); }
.ht-berry-core { fill: rgba(255, 244, 200, 0.85); }

/* 中央游标区 */
.ht-cursor-zone {
  position: absolute; top: 0; bottom: 0; left: 50%;
  transform: translateX(-50%);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  pointer-events: none;
  width: 300px;
}
.ht-cursor-line {
  position: absolute; top: 0; bottom: 0; left: 50%;
  width: 2px; transform: translateX(-50%);
  background: linear-gradient(180deg, transparent, rgba(255, 214, 130, 0.7), transparent);
  box-shadow: 0 0 10px rgba(255, 214, 130, 0.5);
}
.ht-datebox {
  margin-top: 8px;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 14px 26px;
  border-radius: 18px;
  background: linear-gradient(160deg, rgba(22, 30, 42, 0.72), rgba(14, 20, 30, 0.66));
  border: 1px solid rgba(255, 255, 255, 0.1);
  -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
  box-shadow: 0 8px 26px rgba(0, 0, 0, 0.35);
}
.ht-date-main {
  font-family: var(--font-serif, serif);
  font-size: 20px; letter-spacing: .04em; color: #f2f6fb;
}
.ht-date-tag {
  font-size: 11px; letter-spacing: .1em; color: rgba(214, 224, 236, 0.7);
  padding: 2px 9px; border-radius: 999px; background: rgba(255, 255, 255, 0.08);
}
.ht-date-tag.on { color: #ffd682; background: rgba(255, 214, 130, 0.14); }

/* 拖拽遮罩 */
.ht-scrub { position: absolute; inset: 0; cursor: inherit; }

/* 逐日导航条 */
.ht-datebar {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  padding: 12px 4px 2px; flex-wrap: wrap;
}
.ht-datebar-hint { font-size: 12px; color: var(--tx-weak, rgba(210,220,232,.55)); }

/* ============ 事件列表（铺列展示） ============ */
.ht-events { }
.ht-events-head {
  display: flex; align-items: baseline; justify-content: space-between;
  padding: 4px 4px 12px; flex-wrap: wrap; gap: 6px;
}
.ht-events-title { font-family: var(--font-serif, serif); font-size: 15px; letter-spacing: .06em; }
.ht-events-sub { font-size: 12px; color: var(--tx-weak, rgba(210,220,232,.6)); }

.ht-loading { display: flex; gap: 8px; padding: 26px 0; justify-content: center; }
.ht-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #4c8a5f; animation: ht-blink 1.2s ease-in-out infinite;
}
.ht-dot:nth-child(2) { animation-delay: .18s; }
.ht-dot:nth-child(3) { animation-delay: .36s; }
@keyframes ht-blink { 0%,100%{opacity:.25;transform:scale(.8)} 50%{opacity:1;transform:scale(1)} }

.ht-empty { padding: 30px 8px; text-align: center; color: var(--tx-weak, rgba(210,220,232,.6)); font-size: 13px; }

.ht-list {
  margin: 0; padding: 0; list-style: none;
  display: flex; flex-direction: column; gap: 10px;
}
.ht-row {
  display: flex; align-items: baseline; gap: 16px;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: background 0.2s ease;
}
.ht-row:hover { background: rgba(255, 255, 255, 0.08); }
.ht-y {
  flex-shrink: 0; min-width: 64px; text-align: right;
  font-family: var(--font-serif, serif);
  font-size: 15px; color: #ffd682; letter-spacing: .03em;
}
.ht-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ht-t { font-size: 14px; color: var(--tx-strong, #e9eef5); }
.ht-d { font-size: 12px; color: var(--tx-weak, rgba(210,220,232,.62)); line-height: 1.6; }

@media (max-width: 768px) {
  .ht-vine-stage { height: 260px; }
  .ht-date-main { font-size: 17px; }
  .ht-datebox { padding: 12px 18px; }
  .ht-row { gap: 12px; padding: 10px 12px; }
  .ht-y { min-width: 52px; font-size: 14px; }
}
</style>
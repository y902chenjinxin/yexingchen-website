<template>
  <IslandInnerBase type="tool" title="人生 4000 周" subtitle="一生 ≈ 90 年 × 52 周 · 每周一格">
    <div class="lg-tool">
      <div v-if="!birth" class="lg-setup glass-card">
        <p class="lg-ask">你的出生日期？（只存在本机浏览器，不上传）</p>
        <input v-model="birthInput" type="date" class="lg-date">
        <button class="lg-btn primary" @click="saveBirth">生成我的人生格子</button>
      </div>

      <template v-else>
        <div class="lg-head glass-card">
          <div class="lg-stat">
            <div class="lg-stat-num">{{ livedWeeks.toLocaleString() }}</div>
            <div class="lg-stat-label">已生活的周数</div>
          </div>
          <div class="lg-stat">
            <div class="lg-stat-num">{{ percent }}%</div>
            <div class="lg-stat-label">人生进度（按 90 年）</div>
          </div>
          <div class="lg-stat">
            <div class="lg-stat-num">{{ remainingWeeks.toLocaleString() }}</div>
            <div class="lg-stat-label">剩余格子（乐观估计）</div>
          </div>
          <div class="lg-head-actions">
            <button class="lg-btn" @click="exportImage">存成图片</button>
            <button class="lg-btn" @click="resetBirth">改生日</button>
          </div>
        </div>

        <div class="lg-legend">
          <span><i class="dot lived"></i>已度过</span>
          <span><i class="dot current"></i>本周</span>
          <span><i class="dot future"></i>未来</span>
          <span class="lg-decade">每行 = 1 年 · 共 90 行</span>
        </div>

        <!-- 手机端格子自动缩小到一屏放得下（52 列），桌面端保持 13px -->
        <div class="lg-grid-wrap" ref="wrapEl">
          <div class="lg-grid" :style="{ '--lg-cell': cellPx + 'px', '--lg-gap': gapPx + 'px' }">
            <div
              v-for="w in TOTAL"
              :key="w"
              class="lg-cell"
              :class="{ lived: w < livedWeeks, current: w === livedWeeks }"
              :title="`第 ${w} 周 · ${weekLabel(w)}`"
            ></div>
          </div>
        </div>
      </template>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'

const TOTAL = 90 * 52
const COLS = 52
const birth = ref('')
const birthInput = ref('')
const wrapEl = ref(null)

/* ---------- 日期：一律按**本地时区**处理 ----------
 * 以前用 `toISOString().slice(0, 10)` 取日期，而 toISOString 是 UTC —— 中国时区 +8
 * 会让每个格子显示的日期整体偏早一天（见 docs/ai/TOOL_POLISH_AUDIT_20260927.md A1）。
 * `new Date('YYYY-MM-DD')` 也按 UTC 解析，同样要拆开手动构造。
 */
function parseLocalDate(s) {
  const [y, m, d] = String(s).split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}
function formatLocalDate(d) {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/** 今天：用 ref 而不是模块级常量，页面挂过夜/跨周时还能刷新（A2） */
const today = ref(new Date())
function refreshToday() { today.value = new Date() }

const livedWeeks = computed(() => {
  if (!birth.value) return 0
  const b = parseLocalDate(birth.value)
  const days = Math.max(0, Math.floor((today.value - b) / 86400000))
  return Math.min(TOTAL, Math.floor(days / 7))
})
const percent = computed(() => ((livedWeeks.value / TOTAL) * 100).toFixed(1))
const remainingWeeks = computed(() => Math.max(0, TOTAL - livedWeeks.value))

/** 第 w 周对应的日期（本地时区） */
function weekDate(w) {
  const b = parseLocalDate(birth.value)
  const d = new Date(b.getTime() + (w - 1) * 7 * 86400000)
  return d
}
function weekLabel(w) {
  if (!birth.value) return ''
  return formatLocalDate(weekDate(w))
}

/* ---------- 自适应格子：52 列尽量一屏放下（A3） ---------- */
const MAX_CELL = 13
const MIN_CELL = 4
const cellPx = ref(MAX_CELL)
const gapPx = ref(3)

function fitGrid() {
  const w = wrapEl.value?.clientWidth
  if (!w) return
  // gap 随格子大小缩放，先按 3px 估，再回算能塞下的格子尺寸
  let cell = Math.floor((w - 6 - COLS * 3) / COLS)
  cell = Math.max(MIN_CELL, Math.min(MAX_CELL, cell))
  gapPx.value = cell >= 10 ? 3 : 2
  // 用实际 gap 再校一次，保证总宽不超过容器
  cell = Math.floor((w - 6 - (COLS - 1) * gapPx.value) / COLS)
  cellPx.value = Math.max(MIN_CELL, Math.min(MAX_CELL, cell))
}

let ro = null
onMounted(() => {
  birth.value = localStorage.getItem('lg_birth') || ''
  document.addEventListener('visibilitychange', onVisible)
  window.addEventListener('resize', fitGrid)
  if (window.ResizeObserver && wrapEl.value) {
    ro = new ResizeObserver(fitGrid)
    ro.observe(wrapEl.value)
  }
  fitGrid()
})
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisible)
  window.removeEventListener('resize', fitGrid)
  ro?.disconnect()
})
/** 从后台切回来必须重算「今天」，否则跨天后进度是旧的 */
function onVisible() {
  if (document.visibilityState === 'visible') { refreshToday(); fitGrid() }
}

function saveBirth() {
  if (!birthInput.value) { ElMessage.warning('请先选择出生日期'); return }
  birth.value = birthInput.value
  localStorage.setItem('lg_birth', birth.value)
  refreshToday()
  requestAnimationFrame(fitGrid)
}
function resetBirth() {
  birth.value = ''
  localStorage.removeItem('lg_birth')
}

/* ---------- 存成图片（C1）：1080×1350，横向社交图尺寸 ---------- */
const INK = '#18202A'
const GOLD = '#C7A96B'
const LIVED = '#4A5A4A'

function exportImage() {
  const W = 1080, H = 1350
  const cv = document.createElement('canvas')
  cv.width = W; cv.height = H
  const ctx = cv.getContext('2d')
  // 宣纸底
  ctx.fillStyle = '#FAF7F0'
  ctx.fillRect(0, 0, W, H)

  ctx.textAlign = 'center'
  ctx.fillStyle = INK
  ctx.font = '700 52px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText('人生 4000 周', W / 2, 104)
  ctx.fillStyle = GOLD
  ctx.font = '400 26px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText(`${birth.value} 出生 · 一格 = 一周`, W / 2, 148)

  // 三个统计
  const stats = [
    [livedWeeks.value.toLocaleString(), '已生活的周数'],
    [`${percent.value}%`, '人生进度'],
    [remainingWeeks.value.toLocaleString(), '剩余格子'],
  ]
  stats.forEach(([num, label], i) => {
    const cx = W / 2 + (i - 1) * 300
    ctx.fillStyle = GOLD
    ctx.font = '800 52px "PingFang SC", "Microsoft YaHei", sans-serif'
    ctx.fillText(String(num), cx, 244)
    ctx.fillStyle = '#8A8F98'
    ctx.font = '400 20px "PingFang SC", "Microsoft YaHei", sans-serif'
    ctx.fillText(label, cx, 276)
  })

  // 格子：52 列 × 90 行，缩放填满可用区
  const cell = 10, gap = 2
  const gw = COLS * cell + (COLS - 1) * gap
  const gh = 90 * cell + 89 * gap
  const x0 = (W - gw) / 2
  const y0 = 320
  const lived = livedWeeks.value
  for (let w = 1; w <= TOTAL; w++) {
    const col = Math.floor((w - 1) / 90)
    const row = (w - 1) % 90
    ctx.fillStyle = w === lived ? GOLD : (w < lived ? LIVED : 'rgba(0,0,0,.08)')
    ctx.fillRect(x0 + col * (cell + gap), y0 + row * (cell + gap), cell, cell)
  }

  ctx.fillStyle = '#8A8F98'
  ctx.font = '400 20px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText('玄黄 · 人生 4000 周', W / 2, y0 + gh + 56)

  cv.toBlob((blob) => {
    if (!blob) { ElMessage.warning('导出失败，请重试'); return }
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `人生4000周-${formatLocalDate(new Date())}.png`
    a.click()
    setTimeout(() => URL.revokeObjectURL(a.href), 5000)
  }, 'image/png')
}

/** 给父组件或其他地方复用的日期（避免再有人踩 UTC 的坑） */
defineExpose({ formatLocalDate })
</script>

<style scoped>
.lg-setup { padding: 26px; display: flex; flex-direction: column; gap: 14px; align-items: flex-start; }
.lg-ask { font-size: 14px; color: var(--dp-text2, #45505b); }
.lg-date { padding: 9px 12px; border-radius: 10px; border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-size: 14px; }
.lg-btn {
  padding: 9px 20px; border-radius: 10px; font-size: 13.5px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a);
}
.lg-btn:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.lg-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.lg-head { display: flex; align-items: center; gap: 26px; padding: 16px 20px; flex-wrap: wrap; }
.lg-stat-num { font-size: 24px; font-weight: 800; color: var(--yq-gold, #c7a96b); font-variant-numeric: tabular-nums; }
.lg-stat-label { font-size: 11.5px; color: var(--dp-text3, #8a8f98); margin-top: 2px; }
.lg-head-actions { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
.lg-legend { display: flex; gap: 16px; align-items: center; margin: 14px 0 10px; font-size: 12px; color: var(--dp-text3, #8a8f98); flex-wrap: wrap; }
.lg-legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 4px; vertical-align: -1px; }
.dot.lived { background: #4a5a4a; }
.dot.current { background: var(--yq-gold, #c7a96b); }
.dot.future { background: var(--dp-bg2, rgba(0,0,0,.07)); }
.lg-decade { margin-left: auto; }
.lg-grid-wrap { overflow-x: auto; padding-bottom: 8px; }
.lg-grid {
  display: grid;
  grid-template-rows: repeat(90, var(--lg-cell, 13px));
  grid-auto-flow: column;
  grid-template-columns: repeat(52, var(--lg-cell, 13px));
  gap: var(--lg-gap, 3px);
  width: max-content;
  margin: 0 auto;
}
.lg-cell { width: var(--lg-cell, 13px); height: var(--lg-cell, 13px); border-radius: 2px; background: var(--dp-bg2, rgba(0,0,0,.07)); }
.lg-cell.lived { background: #4a5a4a; }
.lg-cell.current { background: var(--yq-gold, #c7a96b); box-shadow: 0 0 0 2px rgba(199,169,107,.35); }

/* ---------- 窄屏（B 类响应式）：格子已经自适应，这里只收间距与字号 ---------- */
@media (max-width: 768px) {
  .lg-head { gap: 16px; padding: 14px 16px; }
  .lg-stat-num { font-size: 21px; }
  .lg-head-actions { margin-left: 0; width: 100%; }
  .lg-head-actions .lg-btn { flex: 1; }
  .lg-decade { margin-left: 0; width: 100%; }
}
@media (max-width: 480px) {
  .lg-setup { padding: 18px; }
  .lg-stat { min-width: 30%; }
  .lg-legend { gap: 10px; font-size: 11.5px; }
}
</style>

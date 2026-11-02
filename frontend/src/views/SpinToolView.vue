<template>
  <IslandInnerBase type="tool" title="自定义抽签" subtitle="转盘决定 · 吃什么 / 做什么 / 谁去">
    <!-- ===== 主界面：转盘 ===== -->
    <div v-if="mode === 'play'" class="sp-play">
      <div class="sp-top">
        <span class="sp-top-lab">我的签组</span>
        <button class="sp-icon-btn" aria-label="编辑当前配置" title="编辑当前配置" @click="mode = 'edit'"><AppIcon icon="✏️" :size="16" /></button>
      </div>

      <!-- 配置卡片条：多套签组并列常驻（v2.46.78 夜星：多个任务一起存在，切换不丢数据），
           点卡片切换、末位 ＋ 新建 -->
      <div ref="cfgStrip" class="sp-cfg-strip">
        <button
          v-for="(c, ci) in configs"
          :key="c.id"
          class="sp-cfg-card"
          :class="{ on: c.id === activeId, 'is-center': cfgCenter === ci }"
          @click="pickCfg(c.id)"
        >
          <b class="sp-cfg-card-name">{{ c.name }}</b>
          <span class="sp-cfg-card-chips">
            <i v-for="(o, i) in c.options.slice(0, 3)" :key="i">{{ o.label }}</i>
            <em v-if="c.options.length > 3">+{{ c.options.length - 3 }}</em>
          </span>
          <span class="sp-cfg-card-num">{{ c.options.length }} 项</span>
        </button>
        <button class="sp-cfg-card sp-cfg-add" aria-label="新建签组" title="新建签组" @click="createCfg"><AppIcon icon="＋" :size="20" /></button>
      </div>

      <!-- 转盘：conic-gradient 依权重分段，标签沿径向排布。
           v2.46.330 起支持手指拖着转：按住盘面绕圆心划，松手带惯性滑行，
           速度衰减后吸附到指针所指扇区的正中。粒子画在下面的 canvas 上。 -->
      <div class="sp-wheel-wrap">
        <i class="sp-bezel" aria-hidden="true"></i>
        <canvas ref="fxCanvas" class="sp-fx" aria-hidden="true"></canvas>
        <i class="sp-pointer" aria-hidden="true"></i>
        <div
          ref="wheelEl"
          class="sp-wheel"
          :class="{ spinning, dragging, 'is-fast': fast }"
          :style="wheelStyle"
          role="button"
          tabindex="0"
          :aria-label="spinning ? '转盘旋转中' : '按住盘面拖动旋转，松手出结果'"
          @keydown.enter.prevent="spin"
          @keydown.space.prevent="spin"
        >
          <span
            v-for="(seg, i) in segs" :key="i"
            class="sp-seg-label"
            :style="seg.style"
          >{{ seg.label }}</span>
          <!-- 中心 GO：只负责"随机一甩"，拖拽交给盘面。pointerdown.stop 保证
               按在中心时不会被当成拖拽起点 -->
          <button
            class="sp-hub"
            :disabled="spinning"
            aria-label="随机抽一次"
            @pointerdown.stop
            @click.stop="spin"
          >GO</button>
        </div>
      </div>

      <div class="sp-result" aria-live="polite">
        <Transition name="sp-pop" mode="out-in">
          <span v-if="result" :key="'r' + result" class="sp-result-text">{{ result }}</span>
          <span v-else-if="hint" :key="'h' + hint" class="sp-result-hint">{{ hint }}</span>
          <span v-else :key="'d'" class="sp-result-dim">
            {{ spinning ? '转动中…' : '按住盘面转一圈，松手看结果' }}
          </span>
        </Transition>
      </div>

      <button class="sp-reset" :disabled="!result" @click="resetRound">
        <AppIcon icon="↻" :size="14" /> 重置
      </button>
    </div>

    <!-- ===== 编辑配置 ===== -->
    <div v-else class="sp-edit">
      <div class="sp-field">
        <label class="sp-label" for="sp-name">配置名称</label>
        <input id="sp-name" v-model="draft.name" class="sp-input" type="text" maxlength="20" placeholder="例如：早上吃什么?" />
      </div>

      <div class="sp-opts">
        <div v-for="(o, i) in draft.options" :key="i" class="sp-opt">
          <span class="sp-opt-idx">选项 {{ i + 1 }}</span>
          <div class="sp-opt-row">
            <input v-model="o.label" class="sp-input sp-opt-label" type="text" maxlength="12" :placeholder="`选项 ${i + 1}`" />
            <button class="sp-opt-del" aria-label="删除选项" @click="draft.options.splice(i, 1)"><AppIcon icon="×" :size="14" /></button>
          </div>
          <div class="sp-opt-weight">
            <span class="sp-weight-ico" aria-hidden="true"><AppIcon icon="◑" :size="14" /></span>
            <input v-model.number="o.weight" class="sp-weight-num" type="number" min="1" max="10" aria-label="权重" />
            <input v-model.number="o.weight" class="sp-weight-range" type="range" min="1" max="10" step="1" aria-label="权重滑杆" />
            <i class="sp-opt-stat" v-if="activeStats[o.label]">{{ activeStats[o.label] }} 次</i>
          </div>
        </div>
        <div v-if="draft.options.length < 2" class="sp-err">至少保留 2 个选项</div>
      </div>

      <div class="sp-edit-actions">
        <button class="sp-btn ghost" :disabled="draft.options.length >= 12" @click="draft.options.push({ label: '', weight: 1 })"><AppIcon icon="＋" :size="14" /> 添加选项</button>
        <button class="sp-btn primary" :disabled="!canSave" @click="saveDraft">保存</button>
        <button class="sp-btn ghost" @click="cancelEdit">返回</button>
      </div>
      <button class="sp-cfg-del" @click="removeCfg">删除此配置</button>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import confetti from 'canvas-confetti'
import { haptic, tick } from '@/utils/haptic'
import { useSnapTicks } from '@/composables/useSnapTicks'
import { useFlickWheel } from '@/composables/useFlickWheel'
import AppIcon from '@/components/common/AppIcon.vue'

/* ---------- 数据模型（localStorage，多套配置 + 抽中统计） ---------- */
const KEY = 'xuanhuang-spin-v1'
const SEED = {
  activeId: 'c1',
  configs: [{
    id: 'c1', name: '早上吃什么?',
    options: [
      { label: '小笼包', weight: 1 }, { label: '豆浆油条', weight: 1 },
      { label: '胡辣汤', weight: 1 }, { label: '米粥', weight: 1 },
      { label: '帕尼尼', weight: 1 }, { label: '手抓饼', weight: 1 },
    ],
    stats: {},
  }],
}
let saved = {}
try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') } catch { /* 忽略坏档 */ }
/* v2.46.324：签组卡片条改成吸附 + 刻度反馈（滑到哪张哪张抬起来） */
const cfgStrip = ref(null)
const { activeIndex: cfgCenter } = useSnapTicks(() => cfgStrip.value)

const configs = ref(Array.isArray(saved.configs) && saved.configs.length ? saved.configs : JSON.parse(JSON.stringify(SEED.configs)))
const activeId = ref(saved.activeId && configs.value.some(c => c.id === saved.activeId) ? saved.activeId : configs.value[0].id)

function persist() {
  try { localStorage.setItem(KEY, JSON.stringify({ activeId: activeId.value, configs: configs.value })) } catch { /* 静默 */ }
}

const activeCfg = computed(() => configs.value.find(c => c.id === activeId.value))
const activeStats = computed(() => activeCfg.value?.stats || {})

/* ---------- 模式与编辑草稿 ---------- */
const mode = ref('play')            // play | edit
const draft = ref(null)
watch(mode, (m) => { if (m === 'edit') {
  draft.value = JSON.parse(JSON.stringify(activeCfg.value || { name: '', options: [{ label: '', weight: 1 }] }))
} })
const canSave = computed(() =>
  draft.value && draft.value.name.trim() && draft.value.options.filter(o => o.label.trim()).length >= 2
)

function saveDraft() {
  const clean = {
    ...activeCfg.value,
    id: activeCfg.value?.id || 'c' + Date.now(),
    name: draft.value.name.trim(),
    options: draft.value.options.filter(o => o.label.trim()).map(o => ({ label: o.label.trim(), weight: Math.min(10, Math.max(1, o.weight || 1)) })),
    stats: activeCfg.value?.stats || {},
  }
  const idx = configs.value.findIndex(c => c.id === clean.id)
  if (idx >= 0) configs.value[idx] = clean; else configs.value.push(clean)
  activeId.value = clean.id
  persist()
  cancelWheel()
  rot.value = 0
  result.value = ''
  mode.value = 'play'
}
function cancelEdit() { mode.value = 'play' }
function createCfg() {
  const c = { id: 'c' + Date.now(), name: '新配置', options: [{ label: '选项 1', weight: 1 }, { label: '选项 2', weight: 1 }], stats: {} }
  configs.value.push(c)
  activeId.value = c.id
  persist()
  mode.value = 'edit'
}
function removeCfg() {
  if (configs.value.length <= 1) return
  configs.value = configs.value.filter(c => c.id !== activeId.value)
  activeId.value = configs.value[0].id
  persist()
  mode.value = 'play'
}
function pickCfg(id) {
  if (id === activeId.value) return
  cancelWheel()          // 换签组：段数/权重都变了，正在转的动画必须停
  rot.value = 0
  result.value = ''
  hint.value = ''
  activeId.value = id
  persist()
}

/* ---------- 转盘几何 ---------- */
/* v2.46.78 配色淡化（夜星：格子颜色太深）：宣纸/鎏金体系浅马卡龙底 + 深墨字，
   替代原来的深绿/深金段，旋转时整体轻盈、标签可读。
   v2.46.315：这套浅色是**写死的**，暗夜主题下整块转盘就是一张白饼（夜星：「黑天展示
   一块白色怪怪的」）。改成只给索引，颜色交给 CSS 变量 --sp-seg-N / --sp-seg-N-fg，
   由 .sp-play 按主题给两套盘面（白天仍是原来那套马卡龙，夜间换成深色段 + 亮字）。 */
const SEG_COUNT = 6
const segVar = (i, suffix = '') => `var(--sp-seg-${(i % SEG_COUNT) + 1}${suffix})`
const segs = computed(() => {
  const opts = activeCfg.value?.options || []
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight), 0) || 1
  let acc = 0
  return opts.map((o, i) => {
    const span = (Math.max(1, o.weight) / total) * 360
    const mid = acc + span / 2
    const style = {
      // 居中修复（v2.46.80 夜星：标签偏右）：锚点原在径向线上、文字向右展开 → 偏右；
      // translate(-50%,-50%) 把元素自身中心摆到半径 86px 的段中点，径向/切向都居中
      transform: `rotate(${mid}deg) translateY(-86px) translate(-50%, -50%)`,
      color: segVar(i, '-fg'),
    }
    acc += span
    return { label: o.label, style }
  })
})
/* ⚠️ 这里**不要**带 transform（v2.46.330）：旋转由 useFlickWheel 命令式写在
   el.style.transform 上，60fps 逐帧写。若同时保留 style 绑定，Vue 每次重渲染
   都会把 transform 覆盖回旧值 —— 表现为"转起来一顿一顿"。
   背景只跟配置有关，单独提出来，逐帧不受影响。 */
const wheelStyle = computed(() => {
  const opts = activeCfg.value?.options || []
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight), 0) || 1
  const stops = []
  let acc = 0
  opts.forEach((o, i) => {
    const span = (Math.max(1, o.weight) / total) * 360
    stops.push(`${segVar(i)} ${acc}deg ${acc + span}deg`)
    acc += span
  })
  return { background: `conic-gradient(${stops.join(', ')})` }
})

/* ---------- 抽签（v2.46.330：物理惯性转盘） ---------- */
const wheelEl = ref(null)
const fxCanvas = ref(null)
const result = ref('')
const hint = ref('')
let hintTimer = 0

/** 各扇区跨度（度，合计 360），抽签与转盘几何共用同一份权重口径。 */
function spansForWheel() {
  const opts = activeCfg.value?.options || []
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight), 0) || 1
  return opts.map((o) => (Math.max(1, o.weight) / total) * 360)
}

const {
  rot, spinning, dragging, fast,
  launchTo, cancel: cancelWheel,
} = useFlickWheel({
  wheelRef: wheelEl,
  canvasRef: fxCanvas,
  getSpans: spansForWheel,
  /* 跨扇区「哒」一声 —— 跟阅读设置滑杆、模块条带同一套刻度反馈。
     但转得飞快时不能响：6 段盘 × 1000°/s ≈ 每秒 17 次，连成一片像电钻。
     只在慢下来（<720°/s）时响，收尾那几秒"一格一格"的机械感刚好。 */
  onCross: (_i, v) => { if (v < 720) tick(0.8) },
  onHint: showHint,
  onSettle: onWheelSettle,
})

/** 轻点一下没滑 → 提示，不转（防误触） */
function showHint() {
  hint.value = '请滑动手势转动命运'
  clearTimeout(hintTimer)
  hintTimer = setTimeout(() => { hint.value = '' }, 1800)
  haptic.light()
}

/**
 * 落定的一小把金色礼花（v2.46.332）。
 * 用 canvas-confetti（github.com/catdad/canvas-confetti，MIT，3KB gzip）——
 * 比自己画纸屑省事太多，而且它自带重力/阻力/形状抖动，落感比手写好。
 * `disableForReducedMotion` 会在系统开了"减弱动态效果"时自动不撒。
 */
function fireConfetti() {
  try {
    confetti({
      particleCount: 34,
      spread: 66,
      startVelocity: 30,
      gravity: 0.85,
      ticks: 140,
      scalar: 0.82,
      zIndex: 2000,
      origin: { x: 0.5, y: 0.46 },
      colors: ['#fff8e6', '#ffe9a8', '#ffd274', '#e3b664', '#ffb04a'],
      disableForReducedMotion: true,
    })
  } catch {
    /* 老内核缺 OffscreenCanvas / 2d 上下文时静默降级，不影响结果展示 */
  }
}

/** 落定：结果来自"指针压着哪块"，不是预先随机出来的 */
function onWheelSettle(idx) {
  const opt = activeCfg.value?.options?.[idx]
  if (!opt) return
  result.value = opt.label
  haptic.medium()
  tick(1)
  fireConfetti()
  const cfg = activeCfg.value
  cfg.stats = { ...(cfg.stats || {}) }
  cfg.stats[opt.label] = (cfg.stats[opt.label] || 0) + 1
  persist()
}

/** 中心 GO：按权重随机挑一块，强推 5 圈落到正中 */
function spin() {
  if (spinning.value) return
  const opts = activeCfg.value?.options || []
  if (opts.length < 2) return
  haptic.light()
  result.value = ''
  hint.value = ''
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight), 0)
  let r = Math.random() * total
  let idx = 0
  for (let i = 0; i < opts.length; i++) {
    r -= Math.max(1, opts[i].weight)
    if (r < 0) { idx = i; break }
  }
  launchTo(idx)
}

function resetRound() {
  result.value = ''
  hint.value = ''
  haptic.light()
}
</script>

<style scoped>
/* v2.46.314：与弹幕页同一处病根 —— --ls-card / --color-ink(--dim) 全站从未定义，
   fallback 写死白底深字，暗夜玻璃下就是白卡。改复用棋类大厅那张玻璃卡的全站 token。 */
.sp-play, .sp-edit {
  --sp-card: var(--color-bg-glass, rgba(255, 255, 255, .06));
  --sp-line: var(--glass-border, color-mix(in srgb, var(--ls-text) 16%, transparent));
  --sp-surface: color-mix(in srgb, var(--ls-text) 7%, transparent);
  --sp-surface-2: color-mix(in srgb, var(--ls-text) 11%, transparent);
  --sp-ink: var(--ls-text);
  --sp-ink-dim: var(--ls-text-3);
  --sp-blur: var(--glass-blur, blur(16px) saturate(160%));
}
.sp-play { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 16px; padding-bottom: 24px; position: relative; }
/* 盘面配色（v2.46.315）：默认走深色一套（夜间主题），白天主题整组覆盖成原来的马卡龙。
   之前这六个色是写死在 JS 里的浅色，暗夜主题下整块转盘就是一张白饼。 */
.sp-play {
  --sp-seg-1: #3a2f63; --sp-seg-1-fg: #ded4ff;
  --sp-seg-2: #14414c; --sp-seg-2-fg: #a8e8f4;
  --sp-seg-3: #4a3123; --sp-seg-3-fg: #f3d6b3;
  --sp-seg-4: #22314f; --sp-seg-4-fg: #c6d6f8;
  --sp-seg-5: #1d3a30; --sp-seg-5-fg: #b8e8d0;
  --sp-seg-6: #3d2740; --sp-seg-6-fg: #f0cde8;
}
/* 白天：保留 v2.46.78 那套「宣纸/鎏金浅马卡龙 + 深墨字」（夜星当时要求的淡化配色） */
html[data-theme="day"] .sp-play {
  --sp-seg-1: #f3e6c8; --sp-seg-1-fg: #6d4f16;
  --sp-seg-2: #e9f2ea; --sp-seg-2-fg: #2f5d46;
  --sp-seg-3: #f7e8e0; --sp-seg-3-fg: #8a4a34;
  --sp-seg-4: #e9edf6; --sp-seg-4-fg: #3c4a6b;
  --sp-seg-5: #f2ebf6; --sp-seg-5-fg: #5e4472;
  --sp-seg-6: #fbf3dc; --sp-seg-6-fg: #7a5c1e;
}
.sp-top { display: flex; align-items: center; gap: 12px; width: 100%; justify-content: space-between; padding: 0 2px; }
.sp-top-lab { font-size: 13px; font-weight: 700; letter-spacing: .04em; color: var(--sp-ink-dim); }
.sp-icon-btn {
  width: 36px; height: 36px; border-radius: 10px; border: none; cursor: pointer; font-size: 16px;
  background: transparent; color: var(--color-accent);
}
/* 配置卡片条：横向滚动，多签组并列常驻；选中态鎏金描边 */
.sp-cfg-strip {
  display: flex; gap: 10px; width: 100%; overflow-x: auto; padding: 2px 2px 6px;
  scrollbar-width: none;
  /* v2.46.324：吸附 + 刻度反馈，滑到哪张哪张抬起 */
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
}
.sp-cfg-strip::-webkit-scrollbar { display: none; }
.sp-cfg-card {
  flex: none; width: 132px; display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px; border-radius: 14px; cursor: pointer; text-align: left;
  background: var(--sp-card);
  border: 1.5px solid var(--sp-line);
  -webkit-backdrop-filter: var(--sp-blur); backdrop-filter: var(--sp-blur);
  transition: border-color .2s, box-shadow .2s, transform .15s, background-color .2s;
}
.sp-cfg-card:active { transform: scale(.97); }
/* 刻度吸附的视觉联动（v2.46.324）：居中那张抬起来，配跨格「哒」声 */
.sp-cfg-card { scroll-snap-align: start; }
.sp-cfg-card.is-center {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 10px 22px -14px rgba(0, 0, 0, .6);
}
.sp-cfg-card.on {
  border-color: color-mix(in srgb, var(--color-accent) 62%, transparent);
  box-shadow: 0 6px 18px -12px color-mix(in srgb, var(--color-accent) 90%, transparent),
    inset 0 1px 0 color-mix(in srgb, var(--ls-text) 8%, transparent);
  background: color-mix(in srgb, var(--color-accent) 14%, transparent);
}
.sp-cfg-card-name {
  font-size: 13px; font-weight: 700; color: var(--sp-ink);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sp-cfg-card.on .sp-cfg-card-name { color: var(--color-accent); }
.sp-cfg-card-chips { display: flex; flex-wrap: wrap; gap: 4px; min-height: 18px; }
.sp-cfg-card-chips i {
  font-style: normal; font-size: 10px; line-height: 1; padding: 3px 6px; border-radius: 999px;
  color: var(--sp-ink-dim); background: color-mix(in srgb, var(--ls-text) 10%, transparent);
  max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sp-cfg-card-chips em { font-style: normal; font-size: 10px; color: var(--sp-ink-dim); }
.sp-cfg-card-num { font-size: 10.5px; color: var(--sp-ink-dim); font-variant-numeric: tabular-nums; }
.sp-cfg-add {
  width: 52px; align-items: center; justify-content: center;
  font-size: 20px; color: var(--color-accent);
  border-style: dashed; background: transparent;
}

.sp-wheel-wrap { position: relative; width: min(320px, 82vw); aspect-ratio: 1; margin-top: 6px; }
/* 粒子画布：比转盘大一圈，火星才有地方往外飞。
   pointer-events:none —— 它盖在盘面上，不能挡住手指拖拽。 */
.sp-fx {
  /* 尺寸与位置由 useFlickWheel 按轮径写 px（不用百分比）。
     🔴 必须 max-width:none：tool-mobile.css 在 ≤768px 有一条
     `.island-inner-tool canvas { max-width:100% }`，百分比宽度会被它砍回 100%
     而高度仍是 152% —— 画布变竖条，圆心跑偏，"光圈歪了"就是这么来的。 */
  position: absolute; left: 0; top: 0;
  max-width: none; max-height: none;
  pointer-events: none; z-index: 3;
}
/* 机加工质感外圈：一点点金属渐变高光 + 内阴影，代替原来那圈糊光 */
.sp-bezel {
  position: absolute; inset: -9px; border-radius: 50%; z-index: 2; pointer-events: none;
  background: conic-gradient(from 210deg,
    rgba(255, 255, 255, 0) 0deg,
    rgba(255, 238, 196, .55) 38deg,
    rgba(255, 255, 255, .10) 88deg,
    rgba(255, 255, 255, 0) 176deg,
    rgba(255, 238, 196, .30) 246deg,
    rgba(255, 255, 255, 0) 320deg);
  -webkit-mask: radial-gradient(closest-side, transparent calc(100% - 2px), #000 calc(100% - 1.2px));
  mask: radial-gradient(closest-side, transparent calc(100% - 2px), #000 calc(100% - 1.2px));
}
@media (prefers-reduced-motion: no-preference) {
  .sp-bezel { transition: opacity .3s ease, filter .3s ease; }
}
/* 注：高速时的发光交给 .sp-wheel.is-fast 的 box-shadow（金色），
   这里不用 :has() —— 鸿蒙 4 的 WebView 内核可能不支持，会变成死规则。 */
.sp-pointer {
  position: absolute; left: 50%; top: -4px; transform: translateX(-50%); z-index: 4;
  border-left: 9px solid transparent; border-right: 9px solid transparent;
  border-top: 16px solid var(--color-accent);
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, .25));
}
.sp-wheel {
  width: 100%; height: 100%; border-radius: 50%; position: relative;
  /* v2.46.314：外圈原来是写死的白环 + 白色环缝，暗夜主题下转盘像贴了一张白卡。
     改成页面底色（--ls-paper）：夜间是深环、白天仍是白环，两种主题都收得住。 */
  box-shadow: 0 14px 34px -14px rgba(0, 0, 0, .45), inset 0 0 0 6px var(--ls-paper, #fff);
  /* 🔴 v2.46.330：这里原来是 `transition: transform 4.2s`（CSS 自动旋转）。
     手指拖拽要求"拖到哪盘到哪"，有 transition 就会拖出 4.2s 的尾巴完全跟不上。
     现在整套动画由 useFlickWheel 的 rAF 逐帧驱动，transition 必须去掉。 */
  transition: none;
  /* 触摸设备上必须禁掉浏览器的滚动/缩放手势，否则竖向拖动会滚页面而不是转盘 */
  touch-action: none;
  -webkit-user-select: none; user-select: none;
  cursor: grab;
  will-change: transform;
}
.sp-wheel.dragging { cursor: grabbing; }
.sp-wheel.spinning { cursor: default; }
/* 高速态：外缘泛一层**暖金**光（原来用 --color-accent，夜间是紫色，
   跟鎏金盘面撞在一起很脏）。这里写死暖色，两套主题都成立。 */
.sp-wheel.is-fast {
  box-shadow:
    0 14px 34px -14px rgba(0, 0, 0, .45),
    inset 0 0 0 6px var(--ls-paper, #fff),
    0 0 34px -4px rgba(255, 208, 120, .5);
  transition: box-shadow .35s ease;
}
.sp-seg-label {
  position: absolute; left: 50%; top: 50%; z-index: 1;
  font-size: 12px; font-weight: 600; white-space: nowrap;
  transform-origin: 0 0; pointer-events: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, .18);
}
.sp-hub {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 2;
  width: 64px; height: 64px; border-radius: 50%; border: 6px solid var(--ls-paper, #fff); cursor: pointer;
  background: linear-gradient(180deg, #f4dc9c, #d9b65f); color: #2a1d05;
  font-size: 15px; font-weight: 800; letter-spacing: .04em;
  box-shadow: 0 6px 16px -6px rgba(0, 0, 0, .5);
}
.sp-hub:disabled { cursor: default; opacity: .8; }
.sp-result { min-height: 58px; display: grid; place-items: center; text-align: center; padding: 0 8px; }
.sp-result-text {
  font-size: clamp(26px, 8vw, 34px); font-weight: 800; color: var(--sp-ink);
  letter-spacing: .04em;
  text-shadow: 0 0 26px color-mix(in srgb, var(--color-accent) 45%, transparent);
}
/* 轻点一下没滑：用鎏金小字提示，不做弹窗（全站无弹窗约定） */
.sp-result-hint {
  font-size: 13.5px; font-weight: 700; color: var(--color-accent);
  animation: sp-nudge .46s cubic-bezier(.36, .07, .19, .97);
}
.sp-result-dim { font-size: 13.5px; color: var(--sp-ink-dim); }
@keyframes sp-nudge {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  55% { transform: translateX(4px); }
  80% { transform: translateX(-2px); }
}
/* 结果切场的弹入（v2.46.330）：数字/文字从下方顶上来，配"咔"一下的落定感 */
.sp-pop-enter-active { transition: opacity .2s ease, transform .34s cubic-bezier(.2, 1.4, .35, 1); }
.sp-pop-leave-active { transition: opacity .14s ease, transform .14s ease; }
.sp-pop-enter-from { opacity: 0; transform: translateY(8px) scale(.9); }
.sp-pop-leave-to { opacity: 0; transform: translateY(-4px) scale(.98); }
.sp-reset {
  display: inline-flex; align-items: center; gap: 7px; cursor: pointer;
  padding: 11px 26px; border-radius: 999px; border: none; font-size: 14px; font-weight: 700;
  color: var(--tc-btn-fg, #04121c);
  background: var(--tc-btn-grad, linear-gradient(135deg, #8b5cff, #2de2ff));
  box-shadow: 0 8px 20px -12px color-mix(in srgb, var(--color-accent) 90%, transparent);
  transition: filter .18s ease;
}
.sp-reset:not(:disabled):hover { filter: brightness(1.08); }
.sp-reset:disabled { opacity: .4; cursor: not-allowed; }

/* ===== 编辑配置 ===== */
.sp-edit { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; padding-bottom: 24px; }
.sp-field { display: flex; flex-direction: column; gap: 8px; }
.sp-label { font-size: 13px; font-weight: 600; color: var(--sp-ink-dim); }
.sp-input {
  width: 100%; box-sizing: border-box; padding: 11px 14px; font-size: 15px;
  color: var(--sp-ink); background: var(--sp-surface);
  border: 1px solid var(--sp-line); border-radius: 12px;
  outline: none; transition: border-color .2s, background-color .2s;
  -webkit-backdrop-filter: var(--sp-blur); backdrop-filter: var(--sp-blur);
}
.sp-input::placeholder { color: color-mix(in srgb, var(--ls-text) 34%, transparent); }
.sp-input:focus { border-color: var(--color-accent); }
.sp-opts { display: flex; flex-direction: column; gap: 14px; }
.sp-opt { display: flex; flex-direction: column; gap: 5px; }
.sp-opt-idx { font-size: 12px; color: var(--sp-ink-dim); }
.sp-opt-row { display: flex; align-items: center; gap: 8px; }
.sp-opt-label { flex: 1; font-weight: 600; }
.sp-opt-del {
  width: 30px; height: 30px; flex: none; border-radius: 50%; border: none; cursor: pointer;
  background: color-mix(in srgb, var(--ls-text) 10%, transparent); color: var(--sp-ink-dim);
  font-size: 15px; transition: background-color .18s ease, color .18s ease;
}
.sp-opt-del:hover { background: color-mix(in srgb, var(--ls-text) 18%, transparent); color: var(--sp-ink); }
.sp-opt-weight { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.sp-weight-ico { color: var(--sp-ink-dim); }
.sp-weight-num {
  width: 44px; text-align: center; font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums;
  color: var(--color-accent); background: none; border: none;
  border-bottom: 2px solid currentColor; outline: none;
}
.sp-weight-range { flex: 1; accent-color: var(--color-accent); height: 4px; }
.sp-opt-stat { margin-left: auto; font-style: normal; font-size: 12px; color: var(--sp-ink-dim); }
.sp-err { font-size: 12px; color: #ff6a63; }
.sp-edit-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.sp-btn {
  padding: 10px 22px; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 600; border: none;
}
.sp-btn.primary { background: var(--tc-btn-grad, linear-gradient(135deg, #8b5cff, #2de2ff)); color: var(--tc-btn-fg, #04121c); }
.sp-btn.ghost {
  background: var(--sp-surface); border: 1px solid var(--sp-line); color: var(--sp-ink);
}
.sp-btn:disabled { opacity: .4; cursor: not-allowed; }
.sp-cfg-del {
  align-self: center; border: none; background: none; cursor: pointer;
  font-size: 13px; color: #e5484d; opacity: .85; text-decoration: underline;
}
@media (max-width: 700px) {
  .sp-wheel-wrap { width: min(300px, 88vw); }
  .sp-seg-label { font-size: 11px; }
}
</style>

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
      <div class="sp-cfg-strip">
        <button
          v-for="c in configs"
          :key="c.id"
          class="sp-cfg-card"
          :class="{ on: c.id === activeId }"
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

      <!-- 转盘：conic-gradient 依权重分段，标签沿径向排布 -->
      <div class="sp-wheel-wrap">
        <i class="sp-pointer" aria-hidden="true"></i>
        <div
          class="sp-wheel"
          :class="{ spinning }"
          :style="wheelStyle"
          role="button"
          :aria-label="spinning ? '转盘旋转中' : '开始抽签'"
          @click="spin"
          @transitionend="onSpinEnd"
        >
          <span
            v-for="(seg, i) in segs" :key="i"
            class="sp-seg-label"
            :style="seg.style"
          >{{ seg.label }}</span>
          <button class="sp-hub" :disabled="spinning" aria-label="开始抽签" @click.stop="spin">GO</button>
        </div>
      </div>

      <div class="sp-result" aria-live="polite">
        <span v-if="result" class="sp-result-text">{{ result }}</span>
        <span v-else class="sp-result-dim">{{ spinning ? '转动中…' : '点转盘开始' }}</span>
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
import { haptic } from '@/utils/haptic'
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
function pickCfg(id) { activeId.value = id; result.value = ''; rot.value = 0; persist() }

/* ---------- 转盘几何 ---------- */
/* v2.46.78 配色淡化（夜星：格子颜色太深）：宣纸/鎏金体系浅马卡龙底 + 深墨字，
   替代原来的深绿/深金段，旋转时整体轻盈、标签可读 */
const COLORS = [
  { bg: '#f3e6c8', fg: '#6d4f16' },  // 米金
  { bg: '#e9f2ea', fg: '#2f5d46' },  // 淡竹青
  { bg: '#f7e8e0', fg: '#8a4a34' },  // 赭石
  { bg: '#e9edf6', fg: '#3c4a6b' },  // 黛蓝
  { bg: '#f2ebf6', fg: '#5e4472' },  // 藕紫
  { bg: '#fbf3dc', fg: '#7a5c1e' },  // 宣纸金
]
const segs = computed(() => {
  const opts = activeCfg.value?.options || []
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight), 0) || 1
  let acc = 0
  return opts.map((o, i) => {
    const span = (Math.max(1, o.weight) / total) * 360
    const mid = acc + span / 2
    const col = COLORS[i % COLORS.length]
    const style = {
      // 居中修复（v2.46.80 夜星：标签偏右）：锚点原在径向线上、文字向右展开 → 偏右；
      // translate(-50%,-50%) 把元素自身中心摆到半径 86px 的段中点，径向/切向都居中
      transform: `rotate(${mid}deg) translateY(-86px) translate(-50%, -50%)`,
      color: col.fg,
    }
    acc += span
    return { label: o.label, style }
  })
})
const wheelStyle = computed(() => {
  const opts = activeCfg.value?.options || []
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight), 0) || 1
  const stops = []
  let acc = 0
  opts.forEach((o, i) => {
    const span = (Math.max(1, o.weight) / total) * 360
    const col = COLORS[i % COLORS.length].bg
    stops.push(`${col} ${acc}deg ${acc + span}deg`)
    acc += span
  })
  return { background: `conic-gradient(${stops.join(', ')})`, transform: `rotate(${rot.value}deg)` }
})

/* ---------- 抽签 ---------- */
const spinning = ref(false)
const result = ref('')
const rot = ref(0)
let pendingIdx = -1

function spin() {
  if (spinning.value) return
  const opts = activeCfg.value?.options || []
  if (opts.length < 2) return
  haptic.light()
  // 按权重随机选中段，再让该段中点转到顶部指针处（额外 5 整圈保证观感）
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight), 0)
  let r = Math.random() * total
  pendingIdx = 0
  for (let i = 0; i < opts.length; i++) {
    r -= Math.max(1, opts[i].weight)
    if (r < 0) { pendingIdx = i; break }
  }
  const span = (Math.max(1, opts[pendingIdx].weight) / total) * 360
  const segStart = opts.slice(0, pendingIdx).reduce((s, o) => s + (Math.max(1, o.weight) / total) * 360, 0)
  const jitter = (Math.random() - 0.5) * span * 0.6
  const target = (360 - (segStart + span / 2 + jitter)) % 360
  spinning.value = true
  result.value = ''
  rot.value = rot.value + 5 * 360 + ((target - (rot.value % 360)) + 360) % 360
}

function onSpinEnd() {
  if (!spinning.value) return
  spinning.value = false
  const opt = activeCfg.value?.options[pendingIdx]
  if (!opt) return
  result.value = opt.label
  haptic.medium?.()
  const cfg = activeCfg.value
  cfg.stats = { ...(cfg.stats || {}) }
  cfg.stats[opt.label] = (cfg.stats[opt.label] || 0) + 1
  persist()
}

function resetRound() { result.value = ''; haptic.light() }
</script>

<style scoped>
.sp-play { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 16px; padding-bottom: 24px; position: relative; }
.sp-top { display: flex; align-items: center; gap: 12px; width: 100%; justify-content: space-between; padding: 0 2px; }
.sp-top-lab { font-size: 13px; font-weight: 700; letter-spacing: .04em; color: var(--color-ink-dim, #7a8087); }
.sp-icon-btn {
  width: 36px; height: 36px; border-radius: 10px; border: none; cursor: pointer; font-size: 16px;
  background: transparent; color: var(--color-accent);
}
/* 配置卡片条：横向滚动，多签组并列常驻；选中态鎏金描边 */
.sp-cfg-strip {
  display: flex; gap: 10px; width: 100%; overflow-x: auto; padding: 2px 2px 6px;
  scrollbar-width: none;
}
.sp-cfg-strip::-webkit-scrollbar { display: none; }
.sp-cfg-card {
  flex: none; width: 132px; display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px; border-radius: 14px; cursor: pointer; text-align: left;
  background: var(--ls-card, #fff);
  border: 1.5px solid var(--ls-line, rgba(0,0,0,.08));
  transition: border-color .2s, box-shadow .2s, transform .15s;
}
.sp-cfg-card:active { transform: scale(.97); }
.sp-cfg-card.on {
  border-color: var(--color-accent);
  box-shadow: 0 6px 16px -10px color-mix(in srgb, var(--color-accent) 80%, transparent);
  background: color-mix(in srgb, var(--color-accent) 7%, var(--ls-card, #fff));
}
.sp-cfg-card-name {
  font-size: 13px; font-weight: 700; color: var(--color-ink, #3a3f45);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sp-cfg-card.on .sp-cfg-card-name { color: var(--color-accent); }
.sp-cfg-card-chips { display: flex; flex-wrap: wrap; gap: 4px; min-height: 18px; }
.sp-cfg-card-chips i {
  font-style: normal; font-size: 10px; line-height: 1; padding: 3px 6px; border-radius: 999px;
  color: var(--color-ink-dim, #7a8087); background: rgba(0, 0, 0, .05);
  max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sp-cfg-card-chips em { font-style: normal; font-size: 10px; color: var(--color-ink-dim, #7a8087); }
.sp-cfg-card-num { font-size: 10.5px; color: var(--color-ink-dim, #7a8087); font-variant-numeric: tabular-nums; }
.sp-cfg-add {
  width: 52px; align-items: center; justify-content: center;
  font-size: 20px; color: var(--color-accent);
  border-style: dashed; background: transparent;
}

.sp-wheel-wrap { position: relative; width: min(320px, 82vw); aspect-ratio: 1; margin-top: 6px; }
.sp-pointer {
  position: absolute; left: 50%; top: -4px; transform: translateX(-50%); z-index: 3;
  border-left: 9px solid transparent; border-right: 9px solid transparent;
  border-top: 16px solid var(--color-accent);
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, .25));
}
.sp-wheel {
  width: 100%; height: 100%; border-radius: 50%; position: relative; cursor: pointer;
  box-shadow: 0 14px 34px -14px rgba(0, 0, 0, .45), inset 0 0 0 6px rgba(255, 255, 255, .85);
  transition: transform 4.2s cubic-bezier(.15, .85, .25, 1);
}
.sp-seg-label {
  position: absolute; left: 50%; top: 50%; z-index: 1;
  font-size: 12px; font-weight: 600; white-space: nowrap;
  transform-origin: 0 0; pointer-events: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, .18);
}
.sp-hub {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 2;
  width: 64px; height: 64px; border-radius: 50%; border: 6px solid #fff; cursor: pointer;
  background: linear-gradient(180deg, #f4dc9c, #d9b65f); color: #2a1d05;
  font-size: 15px; font-weight: 800; letter-spacing: .04em;
  box-shadow: 0 6px 16px -6px rgba(0, 0, 0, .5);
}
.sp-hub:disabled { cursor: default; opacity: .8; }
.sp-result { min-height: 48px; display: grid; place-items: center; }
.sp-result-text { font-size: 30px; font-weight: 800; color: var(--color-ink, #3a3f45); letter-spacing: .04em; }
.sp-result-dim { font-size: 14px; color: var(--color-ink-dim, #7a8087); }
.sp-reset {
  display: inline-flex; align-items: center; gap: 7px; cursor: pointer;
  padding: 11px 26px; border-radius: 999px; border: none; font-size: 14px; font-weight: 700;
  color: #fff; background: linear-gradient(180deg, #6fae90, #4d8f70);
  box-shadow: 0 8px 18px -8px rgba(77, 143, 112, .8);
}
.sp-reset:disabled { opacity: .4; cursor: not-allowed; }

/* ===== 编辑配置 ===== */
.sp-edit { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; padding-bottom: 24px; }
.sp-field { display: flex; flex-direction: column; gap: 8px; }
.sp-label { font-size: 13px; font-weight: 600; color: var(--color-ink-dim, #7a8087); }
.sp-input {
  width: 100%; box-sizing: border-box; padding: 11px 14px; font-size: 15px;
  color: var(--color-ink, #3a3f45); background: var(--ls-card, #fff);
  border: none; border-bottom: 1.5px solid var(--ls-line, rgba(0,0,0,.12));
  outline: none; transition: border-color .2s;
}
.sp-input:focus { border-bottom-color: var(--color-accent); }
.sp-opts { display: flex; flex-direction: column; gap: 14px; }
.sp-opt { display: flex; flex-direction: column; gap: 5px; }
.sp-opt-idx { font-size: 12px; color: var(--color-ink-dim, #7a8087); }
.sp-opt-row { display: flex; align-items: center; gap: 8px; }
.sp-opt-label { flex: 1; font-weight: 600; }
.sp-opt-del {
  width: 30px; height: 30px; flex: none; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(0, 0, 0, .1); color: inherit; font-size: 15px;
}
.sp-opt-weight { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.sp-weight-ico { color: var(--color-ink-dim, #7a8087); }
.sp-weight-num {
  width: 44px; text-align: center; font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums;
  color: var(--color-accent); background: none; border: none;
  border-bottom: 2px solid currentColor; outline: none;
}
.sp-weight-range { flex: 1; accent-color: var(--color-accent); height: 4px; }
.sp-opt-stat { margin-left: auto; font-style: normal; font-size: 12px; color: var(--color-ink-dim, #7a8087); }
.sp-err { font-size: 12px; color: #e5484d; }
.sp-edit-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.sp-btn {
  padding: 10px 22px; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 600; border: none;
}
.sp-btn.primary { background: linear-gradient(180deg, #6fae90, #4d8f70); color: #fff; }
.sp-btn.ghost {
  background: transparent; border: 1px solid var(--ls-line, rgba(0,0,0,.12)); color: var(--color-ink, #3a3f45);
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

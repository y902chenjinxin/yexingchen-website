<template>
  <IslandInnerBase type="tool" title="电子木鱼" subtitle="赛博功德 · 敲一下 +0.1">
    <div class="muyu-tool">
      <div class="my-counter">
        <span class="my-num">{{ countText }}</span>
        <span class="my-unit">功德</span>
      </div>

      <!-- 今日目标（C3）：达成后换色，给个「今天圆满了」的收尾感 -->
      <div class="my-goal">
        <div class="my-goal-bar"><i :style="{ width: goalPercent + '%' }" :class="{ done: goalDone }"></i></div>
        <div class="my-goal-text">
          <template v-if="goalDone">今日 {{ goal }} 目标已达成 · 随喜</template>
          <template v-else>今日 {{ todayCount.toFixed(1) }} / {{ goal }}</template>
          <button class="my-goal-set" @click="editGoal">目标</button>
        </div>
      </div>

      <button
        class="my-drum"
        :class="{ hit: hitting }"
        aria-label="敲木鱼（空格键也可）"
        @click="knock"
        @touchstart.passive="knock"
      >
        <svg viewBox="0 0 200 160" class="my-svg">
          <!-- 木鱼主体 -->
          <ellipse cx="100" cy="105" rx="78" ry="46" fill="#8a5a34" />
          <ellipse cx="100" cy="98" rx="78" ry="46" fill="#a97142" />
          <ellipse cx="100" cy="94" rx="62" ry="34" fill="#b9854f" />
          <ellipse cx="100" cy="92" rx="20" ry="9" fill="#5a3a20" />
          <!-- 木鱼槌 -->
          <g :style="{ transform: hitting ? 'rotate(18deg)' : 'rotate(-8deg)', transformOrigin: '160px 30px', transition: 'transform .07s' }">
            <rect x="156" y="30" width="9" height="66" rx="4" fill="#6b4423" transform="rotate(24 160 30)" />
            <circle cx="128" cy="62" r="15" fill="#7a4e2a" />
            <circle cx="128" cy="62" r="10" fill="#8f5c33" />
          </g>
        </svg>
      </button>

      <div class="my-floating-layer">
        <span v-for="f in floats" :key="f.id" class="my-float" :style="{ left: f.x + '%', top: f.y + 'px' }">+{{ f.inc }} 功德</span>
      </div>

      <div class="my-foot">
        <button class="my-reset" @click="reset">清零重修</button>
        <label class="my-sound">
          <input v-model="soundOn" type="checkbox" @change="saveSound"> 音效
        </label>
        <span class="my-note">计数存在本机浏览器，换设备不同步——功德是自己的。<br>空格键也能敲。</span>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'

const K = 'muyu_merit'
const KD = 'muyu_daily'      // { date: 'YYYY-MM-DD', count: number }
const KG = 'muyu_goal'
const KS = 'muyu_sound'

/* 内部一律用**整数**计数（单位 0.1 功德）：
 * 以前 `count += 0.1` 会把 0.30000000000000004 写进 localStorage，
 * 显示层 toFixed(1) 遮住了，但数据在累积误差（审计 A4）。 */
const ticks = ref(0)
const todayTicks = ref(0)
const goalTicks = ref(50)        // 目标 5.0 功德
const soundOn = ref(true)

const hitting = ref(false)
const floats = ref([])
let fid = 0
let audioCtx = null

const countText = computed(() => (ticks.value / 10).toFixed(1))
const todayCount = computed(() => todayTicks.value / 10)
const goal = computed(() => goalTicks.value / 10)
const goalPercent = computed(() => Math.min(100, (todayTicks.value / Math.max(1, goalTicks.value)) * 100))
const goalDone = computed(() => todayTicks.value >= goalTicks.value)

function todayKey() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/** 敲一下：命中区域是整块木鱼；同时挂 click 与 touchstart 会重复触发，用时间窗去重 */
let lastHit = 0
function knock() {
  const now = Date.now()
  if (now - lastHit < 60) return
  lastHit = now

  ticks.value += 1
  todayTicks.value += 1
  persist()
  if (goalDone.value && todayTicks.value === goalTicks.value) ElMessage.success('今日目标达成，随喜 🙏')

  hitting.value = true
  setTimeout(() => { hitting.value = false }, 70)

  const id = ++fid
  floats.value.push({ id, x: 40 + Math.random() * 20, y: 0, inc: '0.1' })
  setTimeout(() => { floats.value = floats.value.filter(f => f.id !== id) }, 900)
  if (soundOn.value) playDuk()
}

function persist() {
  localStorage.setItem(K, String(ticks.value))
  localStorage.setItem(KD, JSON.stringify({ date: todayKey(), count: todayTicks.value }))
}

function playDuk() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
    const o = audioCtx.createOscillator()
    const g = audioCtx.createGain()
    o.type = 'sine'
    o.frequency.setValueAtTime(660, audioCtx.currentTime)
    o.frequency.exponentialRampToValueAtTime(180, audioCtx.currentTime + 0.08)
    g.gain.setValueAtTime(0.4, audioCtx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.12)
    o.connect(g); g.connect(audioCtx.destination)
    o.start(); o.stop(audioCtx.currentTime + 0.13)
  } catch { /* 静音环境忽略 */ }
}

function saveSound() { localStorage.setItem(KS, soundOn.value ? '1' : '0') }

async function editGoal() {
  try {
    const { value } = await ElMessageBox.prompt('每日功德目标（单位：功德）', '设定目标', {
      inputValue: String(goal.value),
      inputPattern: /^\d+(\.\d)?$/,
      inputErrorMessage: '请输入数字，如 5 或 8.8',
    })
    const v = Math.max(0.1, Math.min(999, Number(value)))
    goalTicks.value = Math.round(v * 10)
    localStorage.setItem(KG, String(goalTicks.value))
  } catch { /* 取消 */ }
}

/** 清零是**不可逆**的，必须确认（审计 A5）；其他页面的破坏性操作都走了 ElMessageBox */
async function reset() {
  if (ticks.value === 0) return
  try {
    await ElMessageBox.confirm(
      `将清零全部功德（当前 ${countText.value}）与今日进度，无法恢复。`,
      '确认清零重修？',
      { type: 'warning', confirmButtonText: '清零', cancelButtonText: '算了' },
    )
  } catch { return }
  ticks.value = 0
  todayTicks.value = 0
  persist()
  ElMessage.success('已清零，从头再来')
}

function onKey(e) {
  const t = e.target
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  if (e.code === 'Space' || e.key === ' ') { e.preventDefault(); knock() }
}

onMounted(() => {
  ticks.value = Math.round(parseFloat(localStorage.getItem(K) || '0') * 10) || 0
  const daily = (() => { try { return JSON.parse(localStorage.getItem(KD) || 'null') } catch { return null } })()
  todayTicks.value = daily && daily.date === todayKey() ? Number(daily.count) || 0 : 0
  const g = Number(localStorage.getItem(KG) || '0')
  if (g > 0) goalTicks.value = Math.round(g)
  soundOn.value = localStorage.getItem(KS) !== '0'
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.muyu-tool { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 10px 0 20px; }
.my-counter { display: flex; align-items: baseline; gap: 8px; }
.my-num { font-size: 40px; font-weight: 800; color: var(--yq-gold, #c7a96b); font-variant-numeric: tabular-nums; }
.my-unit { font-size: 14px; color: var(--dp-text3, #8a8f98); }
/* 今日目标 */
.my-goal { width: min(320px, 82vw); }
.my-goal-bar { height: 8px; border-radius: 999px; background: var(--dp-bg2, rgba(0,0,0,.06)); overflow: hidden; }
.my-goal-bar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--yq-gold, #c7a96b), var(--yq-gold-bright, #f59e0b)); transition: width .18s; }
.my-goal-bar i.done { background: linear-gradient(90deg, #7fa8a3, #1aa86a); }
.my-goal-text { margin-top: 6px; font-size: 12px; color: var(--dp-text3, #8a8f98); display: flex; align-items: center; justify-content: center; gap: 8px; }
.my-goal-set {
  padding: 1px 8px; border-radius: 6px; font-size: 11px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text3, #8a8f98);
}
.my-drum { width: 210px; background: transparent; border: none; cursor: pointer; padding: 0; user-select: none; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
.my-drum:active .my-svg { transform: scale(.97); }
.my-svg { width: 100%; display: block; filter: drop-shadow(0 6px 14px rgba(0,0,0,.18)); }
.my-floating-layer { position: relative; width: 210px; height: 0; }
.my-float {
  position: absolute; font-size: 13px; color: var(--yq-gold, #c7a96b); font-weight: 700;
  animation: floatUp .9s ease-out forwards; white-space: nowrap;
}
@keyframes floatUp { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-46px); } }
@media (prefers-reduced-motion: reduce) { .my-float { animation: none; opacity: 0; } }
.my-foot { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; justify-content: center; }
.my-reset {
  padding: 6px 16px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text3, #8a8f98);
}
.my-sound { font-size: 12px; color: var(--dp-text3, #8a8f98); display: inline-flex; align-items: center; gap: 4px; cursor: pointer; }
.my-note { font-size: 11.5px; color: var(--dp-text3, #8a8f98); line-height: 1.7; text-align: center; }

/* ---------- 窄屏（B 类响应式） ---------- */
@media (max-width: 480px) {
  .my-num { font-size: 34px; }
  .my-drum { width: 176px; }
  .my-floating-layer { width: 176px; }
  .my-foot { gap: 10px; }
}
</style>

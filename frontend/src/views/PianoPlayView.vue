<template>
  <div class="pp">
    <!-- 顶栏：曲名 + 进度 + 退出 -->
    <header class="pp-top">
      <button class="pp-back" type="button" aria-label="退出" @click="exit">←</button>
      <div class="pp-title">
        <b>{{ song?.title || '加载中…' }}</b>
        <span v-if="song">{{ song.bpm }} BPM · {{ song.notes.length }} 个音</span>
      </div>
      <div class="pp-modes">
        <button
          type="button" class="pp-mode" :class="{ on: mode === 'chord' }"
          :disabled="phase !== 'playing'" @click="switchMode('chord')"
        >和弦伴奏</button>
        <button
          type="button" class="pp-mode" :class="{ on: mode === 'score' }"
          :disabled="phase !== 'playing'" @click="switchMode('score')"
        >看谱弹</button>
        <button
          type="button" class="pp-mode" :class="{ on: mode === 'fall' }"
          :disabled="phase !== 'playing'" @click="switchMode('fall')"
        >跟着落</button>
      </div>
      <div class="pp-progress"><i :style="{ width: progressPct + '%' }" /></div>
    </header>

    <!-- 舞台：曲谱模式（默认）/ 下落模式 -->
    <main ref="stageEl" class="pp-stage" :class="{ 'is-score': mode !== 'fall' }">
      <!-- 和弦伴奏（默认）：一个格子一个和弦，按一下三个音一起响 -->
      <template v-if="mode === 'chord'">
        <div class="pp-scorehd">
          <span class="pp-hint">
            按格子上的字母 —— 一次响一整个和弦。按错只是不往下走，照着按就行
          </span>
          <span v-if="cursor >= chords.length" class="pp-done-chip">
            弹完了 · 点行号重来
          </span>
          <span class="pp-count-badge">
            {{ Math.min(cursor, chords.length) }} / {{ chords.length }}
            <template v-if="chordKinds"> · {{ chordKinds }} 个和弦</template>
          </span>
        </div>
        <PianoChordScore :chords="chords" :active="cursor" @pick="pick" />
      </template>

      <!-- 看谱弹：不赶时间，看着简谱一个一个按；按错也出声 -->
      <template v-else-if="mode === 'score'">
        <div class="pp-scorehd">
          <span class="pp-hint">
            看着谱子慢慢弹，按错也没关系（按对会往下走，想从哪句开始就点那句的编号）
          </span>
          <span v-if="cursor >= (song?.notes?.length || 0)" class="pp-done-chip">
            弹完了 · 点句子编号重来
          </span>
          <span class="pp-count-badge">{{ Math.min(cursor, song?.notes?.length || 0) }} / {{ song?.notes?.length || 0 }}</span>
        </div>
        <PianoScore :notes="song?.notes || []" :active="cursor" @pick="pick" />
      </template>

      <!-- 跟着落：原来的节奏版 -->
      <template v-else>
      <div class="pp-fade pp-fade--top" aria-hidden="true" />

      <!-- lane：左右边距与下方键盘完全一致，音符落点才能对上琴键 -->
      <div class="pp-lane" :style="{ width: laneW + 'px' }">
      <div ref="rollEl" class="pp-roll">
        <div
          v-for="n in visibleNotes"
          :key="n.id"
          class="pp-note"
          :class="[n.black ? 'is-black' : 'is-white', { hit: hitSet.has(n.id) }]"
          :style="n.style"
        >
          <span>{{ n.key }}</span>
        </div>
      </div>

      <!-- 判定线 -->
      <div class="pp-judge" aria-hidden="true" />

      <!-- 击中光圈：只在判定线附近按下时冒一下，不打分 -->
      <div
        v-for="f in flashes"
        :key="f.id"
        class="pp-flash"
        :style="{ left: f.x + 'px', width: f.w + 'px' }"
        aria-hidden="true"
      />
      </div>

      </template>

      <!-- 开场 / 倒计时 / 结束 -->
      <div v-if="phase !== 'playing'" class="pp-overlay">
        <div v-if="phase === 'loading'" class="pp-ov-box">正在加载曲谱…</div>

        <div v-else-if="phase === 'error'" class="pp-ov-box">
          <p class="pp-ov-err">{{ errMsg || '曲谱加载失败，请重试' }}</p>
          <div class="pp-ov-acts">
            <button class="pp-btn" type="button" @click="exit">返回大厅</button>
            <button class="pp-btn primary" type="button" @click="load">重试</button>
          </div>
        </div>

        <div v-else-if="phase === 'ready'" class="pp-ov-box">
          <p class="pp-ov-lead">{{ song?.title }}</p>
          <p class="pp-ov-sub">
            <b>和弦伴奏</b>：按一个键响一整个和弦，最简单也最好听<br />
            <b>看谱弹</b>：简谱摊开，一个音一个音慢慢按<br />
            <b>跟着落</b>：音符掉到底线时按对应字母（节奏版）<br />
            白键 <kbd>A S D F G H J K L</kbd> / <kbd>Q W E R T Y U I O</kbd><br />黑键 <kbd>1</kbd> ~ <kbd>0</kbd>
          </p>
          <div class="pp-ov-acts">
            <button class="pp-btn primary" type="button" :disabled="starting" @click="start('chord')">
              {{ starting ? '正在准备音频…' : '和弦伴奏' }}
            </button>
            <button class="pp-btn" type="button" :disabled="starting" @click="start('score')">看谱弹</button>
            <button class="pp-btn" type="button" :disabled="starting" @click="start('fall')">跟着落</button>
            <button class="pp-btn" type="button" @click="exit">返回</button>
          </div>
          <p v-if="pianoError" class="pp-ov-err">{{ pianoError }}</p>
        </div>

        <div v-else-if="phase === 'countdown'" class="pp-count">{{ countdown }}</div>

        <div v-else-if="phase === 'done'" class="pp-ov-box">
          <p class="pp-ov-lead">弹完了</p>
          <p class="pp-ov-sub">{{ song?.title }} · 按错也没关系，这本来就只是玩</p>
          <div class="pp-ov-acts">
            <button class="pp-btn primary" type="button" @click="restart">再弹一次</button>
            <button class="pp-btn" type="button" @click="exit">返回大厅</button>
          </div>
        </div>
      </div>
    </main>

    <!-- 键盘 -->
    <footer class="pp-keys">
      <PianoKeyboard ref="kbEl" :active="activeSet" @down="onKeyDown" @up="onKeyUp" />
    </footer>
  </div>
</template>

<script setup>
/**
 * 演奏页（v2.46.334）—— 全屏路由 /piano/:id
 *
 * 三条设计决定：
 * 1. **不打分、不评级、不统计**（夜星：「我自己演奏不需要观众，娱乐自己的」）。
 *    只有按键发光 + 判定线光圈，漏按没有任何惩罚。
 * 2. 音符用**一个容器整体位移**（`transform: translate3d`）来下落，而不是逐个改 top。
 *    800 个音符逐个改样式 = 每帧 800 次 style 写入，帧率会掉到 30 以下；
 *    整体位移只有一个合成层，60fps 稳定。
 * 3. 音频必须在"开始演奏"的点击里初始化（浏览器自动播放策略），
 *    所以先给一个 ready 覆盖层，用户点了才进倒计时。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import PianoKeyboard from '@/components/piano/PianoKeyboard.vue'
import PianoScore from '@/components/piano/PianoScore.vue'
import PianoChordScore from '@/components/piano/PianoChordScore.vue'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import { usePiano } from '@/composables/usePiano'
import { getSong } from '@/api/songs'
import { keyLayout, KEY_TO_MIDI } from '@/utils/pianoKeys'
import { deriveChords } from '@/utils/chords'

const route = useRoute()
const { exit: exitFullscreen } = useFullscreenPage()

const { ready: audioReady, init: initAudio, noteOn, noteOff, allOff, dispose: disposeAudio, error: pianoError } = usePiano()

const song = ref(null)
const phase = ref('loading')     // loading | ready | countdown | playing | done | error
/** 演奏形态：chord = 和弦伴奏（默认）｜score = 看谱慢慢弹｜fall = 节奏版 */
const mode = ref('chord')
/** 曲谱/和弦模式下「建议你现在按」的序号（按对才前进，按错不动，也不惩罚） */
const cursor = ref(0)
const errMsg = ref('')
const starting = ref(false)
const countdown = ref(3)

const stageEl = ref(null)
const rollEl = ref(null)
const kbEl = ref(null)

const stageH = ref(0)
const laneW = ref(0)          // 与键盘同宽
const layout = shallowRef(keyLayout(1))

/* ---------- 和弦伴奏（v2.46.338）----------
 * 从当前曲谱实时推导：任何上传的谱子都有和弦模式，不需要人工标和弦。
 * 1108 个音推 78 个和弦约 16ms，所以直接 computed，不做缓存也不卡界面。
 * 推导口径见 utils/chords.js 顶部注释。 */
const chordData = computed(() => deriveChords(song.value?.notes || []))
const chords = computed(() => chordData.value.chords)
const chordKeyMap = computed(() => chordData.value.keyMap)
const chordKinds = computed(() => chordData.value.chordCount || 0)
/** 当前按住的键 → 它响的和弦音（keyup 要逐个释放，不能只 allOff） */
const heldChords = new Map()

const activeKeys = ref([])
const activeSet = computed(() => new Set(activeKeys.value))
const flashes = ref([])
const hitSet = ref(new Set())
const progress = ref(0)

const LEAD = 3.2                  // 音符从舞台顶部落到底线所用秒数
const JUDGE_WINDOW = 0.2          // 判定线前后 200ms 内按下 → 冒光圈
const MAX_ANIM_NOTES = 1400       // 超过这个数就不再按时间窗口裁剪（直接全渲染会更卡）

const pps = computed(() => (stageH.value > 0 ? stageH.value / LEAD : 140))

/**
 * 位移量：让 t 秒的音在 elapsed==t 时**正好压在判定线上**。
 *
 * 推导（别凭感觉改符号）：
 *   音符 top = -(time*pps + h)，容器位移 = stageH + t*pps
 *   → 屏幕 y = stageH + (t - time)*pps - h
 *   当 t = time 时 y = stageH - h，即音符**底边**正好贴在判定线；
 *   当 t = time - LEAD 时 y = -h，正好在舞台顶部之外。
 * 反过来写（直接 time*pps、位移用减法）会让音符从**下方**升上来 —— 
 * 第一次做下落轨道必踩的一脚，这里已经踩过了。
 */
function offsetY(t) {
  return stageH.value + t * pps.value
}

/** 每个音符的静态样式（只在曲谱或窗口尺寸变化时算一次） */
const notes = computed(() => {
  const list = song.value?.notes || []
  const L = layout.value
  return list.map((n, i) => {
    const p = L.pos.get(n.key)
    if (!p) return { ...n, id: i, style: { display: 'none' } }
    const w = p.w * (p.black ? 0.9 : 0.86)
    const h = Math.max(14, Math.min(150, (n.dur || 0.2) * pps.value))
    return {
      ...n,
      id: i,
      black: p.black,
      left: p.x + (p.w - w) / 2,
      w,
      top: -(n.time * pps.value + h),
      h,
      style: {
        left: (p.x + (p.w - w) / 2) + 'px',
        width: w + 'px',
        top: -(n.time * pps.value + h) + 'px',
        height: h + 'px',
      },
    }
  })
})

/** 只渲染当前时间窗附近的音符（长曲子 1000+ 个，全塞进 DOM 会拖慢首帧） */
const visibleNotes = computed(() => {
  const list = notes.value
  if (list.length <= MAX_ANIM_NOTES) return list
  const base = offsetY(now.value)
  return list.filter((n) => {
    const y = n.top + base
    return y > -400 && y < stageH.value + 200
  })
})

/* ---------------- 时间轴 ---------------- */
let startAt = 0            // performance.now() 起点
const now = ref(0)         // 当前秒数（只在 rAF 里写，节流更新）
let rafId = 0

function tickFrame() {
  rafId = 0
  if (phase.value !== 'playing') return
  const t = (performance.now() - startAt) / 1000
  now.value = t
  const roll = rollEl.value
  if (roll) roll.style.transform = `translate3d(0, ${offsetY(t)}px, 0)`
  // 进度条只在整数百分比变化时写，避免每帧触发一次组件重渲染
  const pct = Math.max(0, Math.min(100, Math.round((t / (duration.value || 1)) * 100)))
  if (pct !== progress.value) progress.value = pct
  if (t > duration.value + 1.6) {
    finish()
    return
  }
  rafId = requestAnimationFrame(tickFrame)
}

const progressPct = computed(() => {
  if (mode.value === 'chord') {
    const len = chords.value.length || 1
    return Math.min(100, Math.round((cursor.value / len) * 100))
  }
  if (mode.value === 'score') {
    const len = song.value?.notes?.length || 1
    return Math.min(100, Math.round((cursor.value / len) * 100))
  }
  return progress.value
})

const duration = computed(() => {
  const l = song.value?.notes || []
  return l.length ? Math.max(...l.map((n) => n.time + (n.dur || 0))) : 0
})

function finish() {
  phase.value = 'done'
  allOff()
  heldChords.clear()
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
}

/* ---------------- 按键 ---------------- */
function onKeyDown(key) {
  if (activeKeys.value.includes(key)) return
  activeKeys.value = [...activeKeys.value, key]

  // 和弦伴奏：一个键 = 一个和弦，三四个音同时响（这就是"吉他感"的来源）
  if (mode.value === 'chord') {
    const info = chordKeyMap.value[key]
    if (info) {
      if (audioReady.value) for (const m of info.midis) noteOn(m.midi, m.vel)
      heldChords.set(key, info.midis.map((m) => m.midi))
    } else {
      // 不在和弦表里的键（黑键等）：响单音，保持"随便乱按也有声"
      const mm = KEY_TO_MIDI.get(key)
      if (mm != null && audioReady.value) noteOn(mm, 0.75)
    }
    if (phase.value === 'playing') {
      const target = chords.value[cursor.value]
      if (target && target.key === key) cursor.value += 1
    }
    return
  }

  const midi = KEY_TO_MIDI.get(key)
  if (midi != null && audioReady.value) noteOn(midi, 0.9)

  if (phase.value !== 'playing') return
  if (mode.value === 'score') {
    // 只判断"是不是谱子上这个音"：按对了往下走一格，按错什么都不发生（不扣分、不响提示音）
    const target = song.value?.notes?.[cursor.value]
    if (target && target.key === key) cursor.value += 1
    return
  }
  judge(key)
}

function onKeyUp(key) {
  if (!activeKeys.value.includes(key)) return
  activeKeys.value = activeKeys.value.filter((k) => k !== key)

  // 和弦音和单音混着按的时候要分开释放，否则会和弦音一直挂着（听着像卡住）
  const ms = heldChords.get(key)
  if (ms) {
    for (const m of ms) noteOff(m)
    heldChords.delete(key)
    return
  }
  const midi = KEY_TO_MIDI.get(key)
  if (midi != null) noteOff(midi)
}

/** 判定线附近有音就冒个光圈（不计分、不扣分） */
function judge(key) {
  const t = now.value
  const near = notes.value.find((n) => n.key === key && Math.abs(n.time - t) <= JUDGE_WINDOW && !hitSet.value.has(n.id))
  if (!near) return
  const next = new Set(hitSet.value)
  next.add(near.id)
  hitSet.value = next
  fireFlash(near)
}

let flashSeq = 0
function fireFlash(n) {
  const id = ++flashSeq
  flashes.value = [...flashes.value, { id, x: n.left + n.w / 2 - 30, w: 60 }]
  setTimeout(() => {
    flashes.value = flashes.value.filter((f) => f.id !== id)
  }, 460)
}

/* ---------------- 物理键盘 ---------------- */
function onWinKeyDown(e) {
  if (e.repeat) return                       // 长按不松手只响一次
  const tag = (e.target?.tagName || '').toLowerCase()
  if (tag === 'input' || tag === 'textarea' || e.target?.isContentEditable) return
  if ([' ', 'Enter', 'Escape', 'Tab'].includes(e.key) || e.key === 'Meta') return
  const key = codeToKey(e.code)
  if (!key) return
  e.preventDefault()
  onKeyDown(key)
}
function onWinKeyUp(e) {
  const key = codeToKey(e.code)
  if (key) onKeyUp(key)
}
/** 切出窗口时把所有亮着的键清掉，否则回来会"卡住发光" */
function clearAll() {
  activeKeys.value = []
  allOff()
}

function codeToKey(code) {
  if (!code) return ''
  if (code.startsWith('Key')) return code.slice(3)
  if (code.startsWith('Digit')) return code.slice(5)
  return ''
}

/* ---------------- 加载 ---------------- */
async function load() {
  phase.value = 'loading'
  errMsg.value = ''
  try {
    const res = await getSong(route.params.id)
    const data = res?.data || res
    if (!data?.notes?.length) throw new Error('empty')
    song.value = data
    await nextTick()
    measure()
    phase.value = 'ready'
  } catch (e) {
    errMsg.value = e?.response?.data?.msg || '曲谱加载失败，请重试'
    phase.value = 'error'
  }
}

function measure() {
  const el = stageEl.value
  if (!el) return
  stageH.value = el.clientHeight
  // 宽度必须取**键盘**的，不是舞台的：舞台右侧没有内边距、键盘有 16px，
  // 用舞台宽度会让整条轨道比琴键宽 32px，音符落到键的右边，按下去"明明按对了"。
  const kb = kbEl.value?.$el
  const w = kb?.clientWidth || (el.clientWidth - 32)
  laneW.value = w
  layout.value = keyLayout(w)
  // 尺寸变了要重算一遍静态样式
  const roll = rollEl.value
  if (roll) roll.style.transform = `translate3d(0, ${offsetY(now.value)}px, 0)`
}

async function start(m = 'score') {
  starting.value = true
  try {
    await initAudio()            // 必须在这次点击的调用栈里
  } catch {
    starting.value = false
    return
  }
  starting.value = false
  mode.value = m
  if (m !== 'fall') {
    // 看谱弹 / 和弦伴奏：不要倒计时、不要时间轴，直接把谱子摊开
    cursor.value = 0
    phase.value = 'playing'
    return
  }
  phase.value = 'countdown'
  countdown.value = 3
  const timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(timer)
      beginPlay()
    }
  }, 700)
}

/** 演奏中切换形态（和弦伴奏 / 看谱弹 / 跟着落） */
function switchMode(m) {
  if (m === mode.value) return
  if (m !== 'fall') {
    if (rafId) cancelAnimationFrame(rafId)
    rafId = 0
    allOff()
    heldChords.clear()
    mode.value = m
    cursor.value = 0
  } else {
    allOff()
    heldChords.clear()
    mode.value = 'fall'
    beginPlay()
  }
}

/** 点某一句 / 某个和弦就从那里开始（两种谱面共用，靠 mode 决定长度） */
function pick(i) {
  const len = mode.value === 'chord' ? chords.value.length : (song.value?.notes?.length || 0)
  cursor.value = Math.max(0, Math.min(Math.max(1, len) - 1, i))
  allOff()
  heldChords.clear()
}

function beginPlay() {
  now.value = 0
  // 起点提前 LEAD 秒：第一颗音从舞台顶部开始落，玩家有 3.2 秒预读时间
  startAt = performance.now() + LEAD * 1000
  hitSet.value = new Set()
  phase.value = 'playing'
  rafId = requestAnimationFrame(tickFrame)
}

function restart() {
  allOff()
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
  activeKeys.value = []
  heldChords.clear()
  if (mode.value !== 'fall') {
    cursor.value = 0
    phase.value = 'playing'
    return
  }
  beginPlay()
}

function exit() {
  allOff()
  if (rafId) cancelAnimationFrame(rafId)
  exitFullscreen()
}

let ro = null
onMounted(async () => {
  window.addEventListener('keydown', onWinKeyDown)
  window.addEventListener('keyup', onWinKeyUp)
  window.addEventListener('blur', clearAll)
  if (typeof ResizeObserver !== 'undefined' && stageEl.value) {
    ro = new ResizeObserver(measure)
    ro.observe(stageEl.value)
  }
  await load()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onWinKeyDown)
  window.removeEventListener('keyup', onWinKeyUp)
  window.removeEventListener('blur', clearAll)
  ro?.disconnect()
  if (rafId) cancelAnimationFrame(rafId)
  allOff()
  disposeAudio()
})
</script>

<style scoped>
.pp {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(120% 70% at 50% -10%, rgba(255, 214, 140, .10), transparent 60%),
    radial-gradient(90% 60% at 50% 110%, rgba(120, 170, 255, .10), transparent 62%),
    #07080c;
  color: #f2ede4;
  overflow: hidden;
}

/* ---------- 顶栏 ---------- */
.pp-top {
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 20px 10px;
}
.pp-back {
  width: 34px; height: 34px; flex: none;
  border-radius: 10px; border: 1px solid rgba(255, 255, 255, .14);
  background: rgba(255, 255, 255, .06); color: #e7dfd2;
  font-size: 16px; line-height: 1; cursor: pointer;
}
.pp-back:hover { background: rgba(255, 255, 255, .12); }
.pp-title { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pp-title b { font-size: 15px; font-weight: 700; letter-spacing: .02em; }
.pp-title span { font-size: 11.5px; color: rgba(242, 237, 228, .5); font-variant-numeric: tabular-nums; }
.pp-progress {
  flex: 1; height: 3px; max-width: 320px;
  background: rgba(255, 255, 255, .1); border-radius: 999px; overflow: hidden;
}
.pp-progress i {
  display: block; height: 100%; width: 0;
  background: linear-gradient(90deg, #ffd274, #ffe9b8);
  box-shadow: 0 0 10px rgba(255, 210, 116, .7);
  transition: width .12s linear;
}

/* ---------- 舞台 ---------- */
.pp-stage { position: relative; flex: 1 1 auto; min-height: 0; overflow: hidden; }
/* 曲谱模式：上下两段——提示行固定、简谱自己滚 */
.pp-stage.is-score { display: flex; flex-direction: column; padding: 0 16px; }
.pp-scorehd {
  flex: none; display: flex; align-items: center; gap: 12px;
  padding: 2px 4px 8px; border-bottom: 1px solid rgba(255, 255, 255, .07);
}
.pp-hint { font-size: 12px; color: rgba(242, 237, 228, .5); line-height: 1.6; }
.pp-done-chip {
  margin-left: auto; flex: none; font-size: 12px; font-weight: 700;
  color: #ffe1a0; padding: 3px 10px; border-radius: 999px;
  background: rgba(255, 225, 160, .14);
  border: 1px solid rgba(255, 225, 160, .4);
}
.pp-count-badge {
  margin-left: auto; flex: none; font-size: 11.5px; font-variant-numeric: tabular-nums;
  color: rgba(255, 225, 160, .9); letter-spacing: .04em;
}
.pp-stage.is-score .ps,
.pp-stage.is-score .cs { flex: 1 1 auto; min-height: 0; }

/* 顶栏模式切换 */
.pp-modes { display: flex; gap: 6px; margin-left: auto; }
.pp-mode {
  height: 26px; padding: 0 10px; border-radius: 8px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, .14);
  background: transparent; color: rgba(242, 237, 228, .6);
  font-size: 12px; font-weight: 600;
}
.pp-mode.on { background: rgba(255, 225, 160, .16); border-color: rgba(255, 225, 160, .55); color: #ffe1a0; }
.pp-mode:disabled { opacity: .4; cursor: default; }
.pp-fade--top {
  position: absolute; inset: 0 0 auto 0; height: 26%; z-index: 3; pointer-events: none;
  background: linear-gradient(180deg, #07080c 0%, rgba(7, 8, 12, .85) 40%, transparent 100%);
}
.pp-lane {
  position: absolute; top: 0; bottom: 0; left: 16px;
  overflow: hidden;
}
.pp-roll {
  position: absolute; left: 0; right: 0; top: 0; height: 0;
  will-change: transform;
  /* 🔴 千万别加 `contain: paint`：容器高度是 0，paint 包含会把所有绝对定位的
     音符裁在这个 0 高盒子里 —— 表现是"音符全都不见了"，但 DOM 数量是对的，
     排查时特别容易以为是渲染没跑。 */
}
.pp-note {
  position: absolute;
  display: flex; align-items: center; justify-content: center;
  border-radius: 7px;
  font-size: 12px; font-weight: 700;
  letter-spacing: .04em;
  box-shadow: 0 2px 10px -3px rgba(0, 0, 0, .6);
  transition: opacity .18s ease, transform .18s ease;
}
.pp-note.is-white {
  background: linear-gradient(180deg, #ffe9b8 0%, #f2c96f 100%);
  color: #4a3208;
  border: 1px solid rgba(255, 246, 214, .8);
}
.pp-note.is-black {
  background: linear-gradient(180deg, #cf9a3c 0%, #9d6f21 100%);
  color: #2a1c02;
  border: 1px solid rgba(255, 220, 150, .55);
}
/* 打中/漏掉的音符都淡出，不做区分 —— 这里不打分，只是别挡住视线 */
.pp-note.hit { opacity: .18; transform: scale(.94); }

.pp-judge {
  position: absolute; left: 0; right: 0; bottom: 0; height: 3px; z-index: 2;
  background: linear-gradient(90deg, transparent, rgba(255, 226, 168, .9) 20%, rgba(255, 240, 200, 1) 50%, rgba(255, 226, 168, .9) 80%, transparent);
  box-shadow: 0 0 22px rgba(255, 214, 140, .55);
}
.pp-flash {
  position: absolute; bottom: -18px; height: 54px; z-index: 2; pointer-events: none;
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(255, 244, 214, .85), rgba(255, 200, 110, .35) 55%, transparent 72%);
  animation: pp-ring .44s ease-out forwards;
}
@keyframes pp-ring {
  0% { transform: scale(.35); opacity: .95; }
  100% { transform: scale(1.5); opacity: 0; }
}

/* ---------- 覆盖层 ---------- */
.pp-overlay {
  position: absolute; inset: 0; z-index: 5;
  display: grid; place-items: center;
  background: rgba(6, 7, 11, .72);
  -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
}
.pp-ov-box { text-align: center; padding: 24px; max-width: 520px; }
.pp-ov-lead { margin: 0 0 10px; font-size: 26px; font-weight: 800; letter-spacing: .04em; }
.pp-ov-sub { margin: 0 0 20px; font-size: 13px; line-height: 1.9; color: rgba(242, 237, 228, .62); }
.pp-ov-sub kbd {
  display: inline-block; padding: 1px 6px; margin: 0 1px;
  border-radius: 5px; border: 1px solid rgba(255, 255, 255, .2);
  background: rgba(255, 255, 255, .08);
  font-family: inherit; font-size: 12px;
}
.pp-ov-err { margin: 14px 0 0; font-size: 12.5px; color: #ff9d8a; }
.pp-ov-acts { display: flex; gap: 12px; justify-content: center; }
.pp-btn {
  padding: 11px 26px; border-radius: 12px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, .16);
  background: rgba(255, 255, 255, .07); color: #f2ede4;
  font-size: 14px; font-weight: 600;
}
.pp-btn:hover { background: rgba(255, 255, 255, .13); }
.pp-btn.primary {
  border-color: transparent;
  background: linear-gradient(135deg, #ffe1a0, #e8b558);
  color: #2c1d04;
  box-shadow: 0 10px 26px -12px rgba(255, 200, 110, .9);
}
.pp-btn:disabled { opacity: .6; cursor: default; }

.pp-count {
  font-size: 96px; font-weight: 800; color: #ffe1a0;
  text-shadow: 0 0 40px rgba(255, 200, 110, .5);
  animation: pp-count .68s ease-out;
}
@keyframes pp-count {
  0% { transform: scale(1.5); opacity: 0; }
  35% { transform: scale(1); opacity: 1; }
  100% { transform: scale(.92); opacity: .9; }
}

/* ---------- 键盘 ---------- */
.pp-keys {
  flex: none;
  padding: 10px 16px calc(14px + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(180deg, rgba(255, 255, 255, .04), rgba(255, 255, 255, .01));
  border-top: 1px solid rgba(255, 255, 255, .08);
}
</style>

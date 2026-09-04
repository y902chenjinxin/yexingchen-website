<template>
  <div class="whale-stage" ref="stageEl">
    <div
      ref="frameEl"
      class="whale-frame"
      :class="{ dragging: dragging, flip: flipped }"
    >
      <video :ref="el => vEls[0].value = el" class="whale-video" muted loop playsinline autoplay></video>
      <video :ref="el => vEls[1].value = el" class="whale-video" muted loop playsinline autoplay></video>
    </div>

    <!-- 唯一可交互命中区：小"抓手"角标（鲸鱼本体 pointer-events:none 完全点击穿透，不再遮挡下层入口）
         按住拖动移动桌宠，单击打开设置面板 -->
    <div
      ref="handleEl"
      class="whale-handle"
      title="拖动桌宠 · 单击设置"
      @pointerdown="onHandlePointerDown"
    >
      <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
        <g fill="currentColor">
          <rect x="3" y="3" width="3" height="3" rx="1"/>
          <rect x="8" y="3" width="3" height="3" rx="1"/>
          <rect x="13" y="3" width="3" height="3" rx="1"/>
          <rect x="3" y="8" width="3" height="3" rx="1"/>
          <rect x="8" y="8" width="3" height="3" rx="1"/>
          <rect x="13" y="8" width="3" height="3" rx="1"/>
        </g>
      </svg>
    </div>

    <Transition name="panel">
      <div v-if="showPanel" class="whale-panel" @pointerdown.stop>
        <button class="panel-close" @click="showPanel = false" aria-label="关闭">✕</button>
        <div class="panel-title">桌宠设置</div>

        <div class="panel-label">动作方式</div>
        <label class="opt" :class="{ on: mode === 'auto' }">
          <input type="radio" name="whale-mode" value="auto" :checked="mode === 'auto'" @change="setMode('auto')" />
          <span class="opt-radio"></span>
          <span class="opt-body"><b>固定编排</b><small>待机为主，按预设节奏穿插动作</small></span>
        </label>
        <label class="opt" :class="{ on: mode === 'random' }">
          <input type="radio" name="whale-mode" value="random" :checked="mode === 'random'" @change="setMode('random')" />
          <span class="opt-radio"></span>
          <span class="opt-body"><b>随机动作</b><small>每次都换一个不同动作</small></span>
        </label>

        <label class="opt walk-opt" :class="{ on: walkRunning }">
          <input type="checkbox" :checked="walkRunning" @change="onWalkToggle" />
          <span class="opt-radio"></span>
          <span class="opt-body"><b>散步模式</b><small>在页面底部来回走动</small></span>
        </label>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { VIDBOX } from '@/pet/vidbox'

const VW = 640
const VH = 360

const stageEl = ref(null)
const frameEl = ref(null)
const handleEl = ref(null)
const vEls = [ref(null), ref(null)]
function activeVideo() { return vEls[activeIdx]?.value }

// 自动动作池（待机为主，穿插慢游/跑步/扭头/日常/轻音乐……多样但都静音安全），让桌宠"自己刷新动作"
const AUTO_POOL = [
  ['idle', 'breathing'],
  ['idle', 'breathing'],
  ['idle', 'breathing'],
  ['turn', 'looking_around'],
  ['turn', 'looking_around'],
  ['moves', 'floating_steps'],
  ['moves', 'floating_steps'],
  ['moves', 'running_trip'],
  ['moves', 'target_point_run'],
  ['moves', 'crab_walk'],
  ['daily', 'big_stretch'],
  ['daily', 'gentle_spin'],
  ['daily', 'sleepy_yawn'],
  ['daily', 'mirror_check'],
  ['daily', 'quick_nap'],
  ['daily', 'maid_curtsy'],
  ['music', 'light_sway_dance'],
  ['music', 'carefree_humming'],
  ['fun', 'desk_tap'],
  ['fun', 'petting_a_cat'],
  ['fun', 'gravity_squash'],
  ['games', 'spinning_a_top'],
  ['food', 'melting_ice_cream'],
  ['seasonal', 'cooling_with_a_hand_fan'],
]
// 跑步类动作：素材原始朝向为「面朝左」，位移时按运动方向决定是否镜像
const RUN_KEYS = ['running_trip', 'target_point_run', 'crab_walk']
const RUN_SET = new Set(RUN_KEYS)
// 随机模式：从全部动作（排除拖拽类）随机
const RANDOM_POOL = Object.keys(VIDBOX).filter((k) => !k.startsWith('drag/'))
function pickRnd() {
  const k = RANDOM_POOL[Math.floor(Math.random() * RANDOM_POOL.length)]
  return [k.split('/')[0], k.split('/')[1]]
}
const DRAG_POOL = [['drag', 'dragged_in_midair'], ['drag', 'turn_into_ball']]
const WALK_POOL = [['moves', 'floating_steps'], ['moves', 'running_trip'], ['moves', 'crab_walk']]

const dragging = ref(false)
const flipped = ref(false)
// 模式：auto=固定编排，random=随机动作；walkRunning 供面板散步开关回显
const mode = ref('auto')
const showPanel = ref(false)
const walkRunning = ref(false)

let current = null
let autoTimer = null
let draggingState = false
let moved = false
let offX = 0
let offY = 0
let walk = null
let hintTimer = null
let activeIdx = 0
let fadeToken = 0

const MODE_KEY = 'whale-pet-mode'
const FADE_MS = 380

function keyOf(pair) { return pair[0] + '/' + pair[1] }

function applyTo(video, pair) {
  const key = keyOf(pair)
  const box = VIDBOX[key]
  if (!box) return null
  const frame = frameEl.value
  frame.style.width = box.bw + 'px'
  frame.style.height = box.bh + 'px'
  video.style.width = VW + 'px'
  video.style.height = VH + 'px'
  video.style.left = (-box.bx) + 'px'
  video.style.top = (-box.by) + 'px'
  video.src = `/whale-pet/videos/${pair[0]}/${pair[1]}.webm`
  video.load()
  video.play().catch(() => {})
  return box
}

// 直接换动作（拖拽/初始）：立即切换，不做淡入淡出
function setAction(pair, force = false) {
  const cur = keyOf(pair)
  if (!force && cur === current) return
  current = cur
  fadeToken++                        // 取消进行中的交叉淡入淡出
  const active = activeVideo()
  if (!applyTo(active, pair)) return
  active.style.opacity = '1'
  vEls[1 - activeIdx].value.style.opacity = '0'
}

// 双层交叉淡入淡出：旧片渐隐、新片(已开播)渐入，没有"消失空洞"或首帧空白
function crossSwitch(pair) {
  const newIdx = 1 - activeIdx
  const oldEl = activeVideo()
  const newEl = vEls[newIdx].value
  if (!applyTo(newEl, pair)) return
  current = keyOf(pair)
  newEl.style.opacity = '0'
  const token = ++fadeToken
  const t0 = performance.now()
  const fade = (now) => {
    if (token !== fadeToken) return
    let p = (now - t0) / FADE_MS
    if (p >= 1) p = 1
    oldEl.style.opacity = String(1 - p)
    newEl.style.opacity = String(p)
    if (p < 1) requestAnimationFrame(fade)
    else activeIdx = newIdx
  }
  requestAnimationFrame(fade)
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)]
}

function pickAuto() {
  if (mode.value === 'random') return pickRnd()
  return pick(AUTO_POOL)
}

function scheduleAuto() {
  autoTimer = setTimeout(() => {
    if (walk || draggingState) { scheduleAuto(); return }
    playAuto(pickAuto())
    scheduleAuto()
  }, 8000 + Math.random() * 5000)
}

function playAuto(pair) {
  crossSwitch(pair)
  // 跑步类动作触发横向位移穿越，跑完自动回待机
  if (pair[0] === 'moves' && RUN_SET.has(pair[1]) && !walk && !draggingState) {
    runAcross()
  }
}

// 可见尺寸（含 transform scale(0.75) 后的实际占位），用于边界计算
function visibleSize() {
  const f = frameEl.value
  return { w: (f ? f.offsetWidth : VW) * 0.75, h: (f ? f.offsetHeight : VH) * 0.75 }
}
function clampX(x) {
  const { w } = visibleSize()
  const max = Math.max(0, window.innerWidth - w)
  return Math.max(0, Math.min(x, max))
}
function clampY(y) {
  const { h } = visibleSize()
  const max = Math.max(0, window.innerHeight - h)
  return Math.max(0, Math.min(y, max))
}
function currentX() {
  return stageEl.value.getBoundingClientRect().left
}

// 统一横向移动：从当前位置出发，左右边界内来回，到边界镜像调头（正脸朝前，非倒退）
// mode='autoRun' 自动跑步限时后自然停下；mode='manual' 散步持续直到手动停
function startWalk(dir, speed, mode) {
  crossSwitch(pick(WALK_POOL), true)
  walk = {
    x: clampX(currentX()),
    dir,
    speed,
    stopAt: mode === 'autoRun' ? performance.now() + (9000 + Math.random() * 7000) : null
  }
  flipped.value = dir > 0   // 素材面朝左：向右跑镜像成面右
  walkRunning.value = true
  tick()
}

// 自动跑步穿越：改为边界内来回，不再穿屏跑出屏外
function runAcross() {
  const maxX = Math.max(0, window.innerWidth - visibleSize().w)
  const dir = currentX() >= maxX - 10 ? -1 : 1
  startWalk(dir, 3.4, 'autoRun')
}

function endAutoWalk() {
  walk = null
  walkRunning.value = false
  if (autoTimer) clearTimeout(autoTimer)
  crossSwitch(pickAuto())
  scheduleAuto()
}

// 只有抓手区可交互：按住抓手拖动桌宠（鲸鱼本体 pointer-events:none，点击穿透给下层内容）
function onHandlePointerDown(e) {
  e.preventDefault()
  if (e.button !== 0) return
  draggingState = true
  moved = false
  const r = stageEl.value.getBoundingClientRect()
  offX = e.clientX - r.left
  offY = e.clientY - r.top
  dragging.value = true
  stopWalk()
  setAction(pick(DRAG_POOL), true)
  document.addEventListener('pointermove', onPointerMove)
  document.addEventListener('pointerup', onHandlePointerUp, { once: true })
}

function onPointerMove(e) {
  const dx = e.movementX, dy = e.movementY
  if (dx || dy) moved = true
  // 素材面朝左：向右拖镜像成面右，向左拖保持
  flipped.value = dx > 0
  const stage = stageEl.value
  stage.style.right = 'auto'
  stage.style.bottom = 'auto'
  stage.style.left = clampX(e.clientX - offX) + 'px'
  stage.style.top = clampY(e.clientY - offY) + 'px'
}

function onHandlePointerUp() {
  document.removeEventListener('pointermove', onPointerMove)
  draggingState = false
  dragging.value = false
  if (!moved) { togglePanel(); return }
  stopWalk()
  crossSwitch(pickAuto())
}

function togglePanel() {
  showPanel.value = !showPanel.value
}

function setMode(m) {
  mode.value = m
  try { localStorage.setItem(MODE_KEY, m) } catch (e) {}
}

function onWalkToggle() {
  toggleWalk()
}

function toggleWalk() {
  if (walk) {
    stopWalk()
    crossSwitch(pickAuto())
    return
  }
  const maxX = Math.max(0, window.innerWidth - visibleSize().w)
  const dir = currentX() >= maxX - 10 ? -1 : 1
  startWalk(dir, 1.4, 'manual')
}

function tick() {
  if (!walk) return
  const maxX = Math.max(0, window.innerWidth - visibleSize().w)
  walk.x += walk.speed * walk.dir
  // 到边界立即钳位并镜像调头（正脸朝前，非倒退）
  if (walk.x <= 0) { walk.x = 0; walk.dir = 1; flipped.value = true }
  else if (walk.x >= maxX) { walk.x = maxX; walk.dir = -1; flipped.value = false }
  const stage = stageEl.value
  stage.style.right = 'auto'
  stage.style.bottom = '40px'
  stage.style.left = walk.x + 'px'
  stage.style.top = 'auto'
  if (walk.stopAt && performance.now() >= walk.stopAt) { endAutoWalk(); return }
  requestAnimationFrame(tick)
}

function stopWalk() {
  if (!walk) return
  walk = null
  walkRunning.value = false
  // 停在当前位置，不再归位右下角
}

function showHint() {
  const el = frameEl.value
  if (!el) return
  el.classList.add('hint')
  clearTimeout(hintTimer)
  hintTimer = setTimeout(() => el.classList.remove('hint'), 2600)
}

onMounted(() => {
  try {
    const saved = localStorage.getItem(MODE_KEY)
    if (saved === 'auto' || saved === 'random') mode.value = saved
  } catch (e) {}
  setAction(pick(AUTO_POOL), true)
  scheduleAuto()
  const hintId = setInterval(() => { if (!draggingState) showHint() }, 12000)
  const firstHint = setTimeout(showHint, 1500)
  onBeforeUnmount(() => {
    fadeToken++
    clearInterval(hintId)
    clearTimeout(firstHint)
    if (autoTimer) clearTimeout(autoTimer)
    if (hintTimer) clearTimeout(hintTimer)
    document.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('pointerup', onHandlePointerUp)
  })
})
</script>

<style scoped>
.whale-stage {
  position: fixed;
  right: 30px;
  bottom: 40px;
  z-index: 1800;
  pointer-events: none;
}
.whale-frame {
  position: relative;
  overflow: hidden;
  transform: scale(0.75);
  transform-origin: bottom right;
  filter: drop-shadow(0 12px 20px rgba(0, 0, 0, 0.45));
  /* 鲸鱼本体完全点击穿透：透明留白区域不再拦截下方入口（玉简/按钮/链接）的点击 */
  pointer-events: none;
  transition: filter 0.4s ease;
}
/* 唯一可交互命中区：小“抓手”角标，用于按住拖动桌宠 / 单击打开设置面板 */
.whale-handle {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
  cursor: grab;
  touch-action: none;
  color: var(--ls-text-3, #7f8d94);
  background: var(--ls-glass, rgba(32,42,51,.55));
  border: 1px solid var(--ls-line, rgba(206,220,226,.12));
  box-shadow: 0 2px 8px rgba(0,0,0,.25);
  opacity: .75;
  transition: opacity .2s ease, background .2s ease;
}
.whale-handle:hover { opacity: 1; background: rgba(95,148,153,.35); color: #c9dde0; }
.whale-handle:active { cursor: grabbing; }
.whale-frame.dragging { cursor: grabbing; }
.whale-frame.flip .whale-video { transform: scaleX(-1); }
.whale-video {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  opacity: 1;
}
.whale-frame.hint::after {
  content: '按住“抓手”可拖动 · 单击抓手设置';
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  transform: translateX(-50%);
  white-space: nowrap;
  padding: 4px 10px;
  font-family: var(--font-serif, 'Noto Serif SC', serif);
  font-size: 12px;
  color: var(--ls-text, #ecf1f4);
  background: var(--ls-glass, rgba(32,42,51,.62));
  border: 1px solid var(--ls-line, rgba(206,220,226,.10));
  border-radius: 10px;
  box-shadow: inset 0 1px 0 var(--ls-highlight, rgba(255,255,255,.08)), var(--ls-shadow, 0 18px 46px rgba(0,0,0,.35));
  backdrop-filter: saturate(160%) blur(14px);
  pointer-events: none;
}

.whale-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  width: 232px;
  max-height: calc(100dvh - 220px);
  overflow-y: auto;
  padding: 14px 14px 12px;
  pointer-events: auto;
  font-family: var(--font-serif, 'Noto Serif SC', serif);
  color: var(--ls-text, #ecf1f4);
  background: linear-gradient(165deg, rgba(255,255,255,.06), rgba(255,255,255,0) 48%), var(--ls-glass, rgba(32,42,51,.62));
  border: 1px solid var(--ls-line, rgba(206,220,226,.10));
  border-radius: 14px;
  box-shadow: inset 0 1px 0 var(--ls-highlight, rgba(255,255,255,.08)), var(--ls-shadow, 0 18px 46px rgba(0,0,0,.35));
  backdrop-filter: saturate(160%) blur(16px);
  user-select: none;
}
.panel-enter-active, .panel-leave-active { transition: opacity .2s ease, transform .2s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(6px); }
.panel-close {
  position: absolute;
  top: 8px;
  right: 8px;
  border: none;
  background: transparent;
  color: var(--ls-text-3, #7f8d94);
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  padding: 4px;
}
.panel-close:hover { color: var(--ls-ochre, #c2a26b); }
.panel-title {
  font-size: 14px;
  letter-spacing: 2px;
  color: var(--ls-ochre, #c2a26b);
  margin: 0 0 8px;
}
.panel-label {
  font-size: 11px;
  color: var(--ls-text-2, #abb7be);
  margin: 6px 0 4px;
  letter-spacing: 1px;
}
.opt {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 7px 8px;
  margin-bottom: 5px;
  border: 1px solid var(--ls-line, rgba(206,220,226,.10));
  border-radius: 8px;
  cursor: pointer;
  transition: border-color .2s ease, background .2s ease;
}
.opt.on { border-color: var(--ls-dai, #5f9499); background: rgba(95,148,153,.10); }
.opt input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}
.opt-radio {
  flex: 0 0 auto;
  margin-top: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid var(--ls-text-3, #7f8d94);
  box-sizing: border-box;
  position: relative;
}
.opt.on .opt-radio { border-color: var(--ls-dai, #5f9499); }
.opt.on .opt-radio::after {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: 50%;
  background: var(--ls-dai, #5f9499);
}
.opt-body { display: flex; flex-direction: column; gap: 1px; }
.opt-body b { font-size: 13px; font-weight: 600; color: var(--ls-text, #ecf1f4); }
.opt.on .opt-body b { color: var(--ls-dai, #5f9499); }
.opt-body small { font-size: 11px; color: var(--ls-text-3, #7f8d94); line-height: 1.35; }
.walk-opt { margin-top: 4px; }
</style>
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
let lastTap = 0
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

// 跑步横向穿越：从右下角常驻位出发向左平滑越过全屏，不回屏外冒入、不倒着跑
function runAcross() {
  const stage = stageEl.value
  const w = frameEl.value.offsetWidth
  walk = { x: window.innerWidth - w - 30, dir: -1, speed: 3.4, endX: 40 }
  flipped.value = false  // 素材面朝左，向左跑不镜像
  stage.style.right = 'auto'
  stage.style.bottom = '40px'
  stage.style.left = walk.x + 'px'
  stage.style.top = 'auto'
  tick()
}

function endAutoWalk() {
  const stage = stageEl.value
  if (stage) { stage.style.right = '30px'; stage.style.bottom = '40px'; stage.style.left = 'auto'; stage.style.top = 'auto' }
  walk = null
  flipped.value = false
  if (autoTimer) clearTimeout(autoTimer)
  crossSwitch(pickAuto())
  scheduleAuto()
}

function onPointerDown(e) {
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
  document.addEventListener('pointerup', onPointerUp, { once: true })
}

function onPointerMove(e) {
  const dx = e.movementX, dy = e.movementY
  if (dx || dy) moved = true
  // 素材面朝左：向右拖镜像成面右，向左拖保持
  flipped.value = dx > 0
  const stage = stageEl.value
  stage.style.right = 'auto'
  stage.style.bottom = 'auto'
  stage.style.left = (e.clientX - offX) + 'px'
  stage.style.top = (e.clientY - offY) + 'px'
}

function onPointerUp() {
  draggingState = false
  dragging.value = false
  document.removeEventListener('pointermove', onPointerMove)
  if (!moved) {
    // 没拖动 -> 单击开/关设置面板；双击走/停散步
    const now = Date.now()
    if (now - lastTap < 350) {
      lastTap = 0
      toggleWalk()
    } else {
      lastTap = now
      togglePanel()
    }
    return
  }
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
  crossSwitch(pick(WALK_POOL), true)
  const r = stageEl.value.getBoundingClientRect()
  walk = { x: window.innerWidth - r.width - 60, dir: -1, speed: 1.4 }
  flipped.value = false
  walkRunning.value = true
  tick()
}

function tick() {
  if (!walk) return
  walk.x += walk.speed * walk.dir
  if (walk.endX != null) {
    // 横向穿越：跑到终点或出屏即停下回待机
    if ((walk.dir < 0 && walk.x <= walk.endX) || (walk.dir < 0 && walk.x < -100) ||
        (walk.dir > 0 && walk.x >= walk.endX) || (walk.dir > 0 && walk.x > window.innerWidth + 100)) {
      endAutoWalk(); return
    }
  } else {
    // 素材面朝左：向左跑不镜像(dir=-1)，向右跑镜像成面右(dir=+1)
    if (walk.x > window.innerWidth - 60) { walk.dir = -1; flipped.value = false }
    if (walk.x < 0) { walk.dir = 1; flipped.value = true }
  }
  const stage = stageEl.value
  stage.style.right = 'auto'
  stage.style.bottom = '40px'
  stage.style.left = walk.x + 'px'
  stage.style.top = 'auto'
  requestAnimationFrame(tick)
}

function stopWalk() {
  if (!walk) return
  walk = null
  walkRunning.value = false
  const stage = stageEl.value
  stage.style.bottom = '40px'
  stage.style.right = '30px'
  stage.style.left = 'auto'
  stage.style.top = 'auto'
  flipped.value = false
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
  frameEl.value.addEventListener('pointerdown', onPointerDown)
  const hintId = setInterval(() => { if (!draggingState) showHint() }, 12000)
  const firstHint = setTimeout(showHint, 1500)
  onBeforeUnmount(() => {
    fadeToken++
    clearInterval(hintId)
    clearTimeout(firstHint)
    if (autoTimer) clearTimeout(autoTimer)
    if (hintTimer) clearTimeout(hintTimer)
    frameEl.value?.removeEventListener('pointerdown', onPointerDown)
    document.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('pointerup', onPointerUp)
  })
})
</script>

<style scoped>
.whale-stage {
  position: fixed;
  right: 30px;
  bottom: 40px;
  z-index: 10001;
  pointer-events: none;
}
.whale-frame {
  position: relative;
  overflow: hidden;
  transform: scale(0.75);
  transform-origin: bottom right;
  cursor: grab;
  filter: drop-shadow(0 12px 20px rgba(0, 0, 0, 0.45));
  pointer-events: auto;
  touch-action: none;
  transition: filter 0.4s ease;
}
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
  content: '单击 设置 · 双击 散步 · 可拖拽';
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
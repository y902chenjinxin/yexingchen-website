<template>
  <div class="whale-stage" ref="stageEl" :class="{ recede }">
    <div
      ref="frameEl"
      class="whale-frame"
      :class="{ dragging: dragging, flip: flipped }"
    >
      <video :ref="el => vEls[0].value = el" class="whale-video" muted loop playsinline autoplay></video>
      <video :ref="el => vEls[1].value = el" class="whale-video" muted loop playsinline autoplay></video>
    </div>

    <!-- 唯一可交互命中区：小"抓手"角标（鲸鱼本体 pointer-events:none 完全点击穿透，不再遮挡下层入口）按住即可拖动桌宠 -->
    <div
      ref="handleEl"
      class="whale-handle"
      title="拖动桌宠"
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

// 跑步类动作：素材原始朝向为「面朝左」，位移时按运动方向决定是否镜像
const RUN_KEYS = ['running_trip', 'target_point_run', 'crab_walk']
const RUN_SET = new Set(RUN_KEYS)
// 随机动作（唯一模式）：从全部动作（排除拖拽类）随机挑一个
const RANDOM_POOL = Object.keys(VIDBOX).filter((k) => !k.startsWith('drag/'))
function pickRnd() {
  const k = RANDOM_POOL[Math.floor(Math.random() * RANDOM_POOL.length)]
  return [k.split('/')[0], k.split('/')[1]]
}
const DRAG_POOL = [['drag', 'dragged_in_midair'], ['drag', 'turn_into_ball']]
const WALK_POOL = [['moves', 'floating_steps'], ['moves', 'running_trip'], ['moves', 'crab_walk']]

const dragging = ref(false)
const flipped = ref(false)
const recede = ref(false)

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
let recedeTimer = null

const FADE_MS = 380

// 滚动时让位：桌宠短暂淡出/缩小，停止滚动后恢复，避免压在内容上
function onScrollRecede() {
  recede.value = true
  clearTimeout(recedeTimer)
  recedeTimer = setTimeout(() => { recede.value = false }, 500)
}

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

function scheduleAuto() {
  autoTimer = setTimeout(() => {
    if (walk || draggingState) { scheduleAuto(); return }
    playAuto(pickRnd())
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

// 横向移动：从当前位置出发，左右边界内来回，到边界镜像调头（正脸朝前，非倒退）
// 自动跑步限时后自然停下；手动拖拽到任意位置则停在该处
function startWalk(dir, speed) {
  crossSwitch(pick(WALK_POOL), true)
  walk = {
    x: clampX(currentX()),
    dir,
    speed,
    stopAt: performance.now() + (9000 + Math.random() * 7000)
  }
  flipped.value = dir > 0   // 素材面朝左：向右跑镜像成面右
  tick()
}

// 自动跑步穿越：改为边界内来回，不再穿屏跑出屏外
function runAcross() {
  const maxX = Math.max(0, window.innerWidth - visibleSize().w)
  const dir = currentX() >= maxX - 10 ? -1 : 1
  startWalk(dir, 3.4)
}

function endAutoWalk() {
  walk = null
  if (autoTimer) clearTimeout(autoTimer)
  crossSwitch(pickRnd())
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
  if (!moved) return
  stopWalk()
  crossSwitch(pickRnd())
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
  walk = null
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
  setAction(pickRnd(), true)
  scheduleAuto()
  const hintId = setInterval(() => { if (!draggingState) showHint() }, 12000)
  const firstHint = setTimeout(showHint, 1500)
  window.addEventListener('scroll', onScrollRecede, { passive: true })
  onBeforeUnmount(() => {
    fadeToken++
    clearInterval(hintId)
    clearTimeout(firstHint)
    if (autoTimer) clearTimeout(autoTimer)
    if (hintTimer) clearTimeout(hintTimer)
    if (recedeTimer) clearTimeout(recedeTimer)
    document.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('pointerup', onHandlePointerUp)
    window.removeEventListener('scroll', onScrollRecede)
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
/* 唯一可交互命中区：小"抓手"角标，用于按住拖动桌宠 */
.whale-handle {
  position: absolute;
  top: 50%;
  right: 6px;
  transform: translateY(-50%);
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
  content: '按住抓手可拖动';
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

/* 滚动让位：淡出缩小 */
.whale-stage.recede { opacity: .35; }
.whale-frame { transition: filter .4s ease, opacity .25s ease, transform .25s ease; }
.whale-stage.recede .whale-frame { transform: scale(.6); }
</style>
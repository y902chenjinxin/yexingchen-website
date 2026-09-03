<template>
  <div
    class="jade-carousel"
    ref="carouselRef"
    tabindex="0"
    @keydown="onKeydown"
    @mousedown="onMouseDown"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >
    <div class="carousel-track" :style="carouselStyle">
      <div
        v-for="(card, index) in cards"
        :key="card.key"
        class="jade-card"
        :class="{ 'is-active': index === currentIndex }"
        :data-type="card.key"
        :style="getCardStyle(index)"
        @click="onCardClick(index)"
        @mouseenter="onMouseEnter(card)"
        @mouseleave="onMouseLeave"
      >
        <div class="card-inner">
          <div class="card-texture"></div>
          <!-- 专属 SVG 篆符 -->
          <svg class="card-sigil" viewBox="0 0 64 64" aria-hidden="true">
            <path
              :d="sigilPath(card.key)"
              :fill="card.color"
              opacity="0.78"
            />
            <circle
              v-for="i in 3"
              :key="i"
              :cx="seeded(i, card.key) * 64"
              :cy="seeded(i + 7, card.key) * 64"
              r="1.6"
              :fill="card.color"
              opacity="0.3"
            />
          </svg>
          <div class="card-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- 当前位小圆点指示 -->
    <div class="carousel-dots">
      <span
        v-for="(c, i) in cards"
        :key="c.key"
        class="dot"
        :class="{ active: i === currentIndex }"
        @click="currentIndex = i"
      ></span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useIslandSound } from '@/composables/useIslandSound'

const props = defineProps({
  cards: {
    type: Array,
    default: () => [
      { key: 'music',  rune: '音', label: '宫商流转', path: '/music',  color: '#4a5f63' },
      { key: 'novel',  rune: '書', label: '卷帙浩繁', path: '/novel',  color: '#b0805a' },
      { key: 'video',  rune: '影', label: '光影交织', path: '/video',  color: '#5b6b7a' },
      { key: 'log',    rune: '墨', label: '翰墨丹青', path: '/log',    color: '#4a6a56' },
      { key: 'tool',   rune: '器', label: '机关百变', path: '/tool',   color: '#6a7a6a' },
      { key: 'notes',  rune: '記', label: '笔记云台', path: '/notes',               color: '#55706b' },
      { key: 'assets', rune: '藏', label: '内容资产', path: '/assets',              color: '#6b6a7a' },
      { key: 'tasks',  rune: '約', label: '任务镜台', path: '/tasks',               color: '#7a5a5a' }
    ]
  },
  initialIndex: { type: Number, default: 0 },
  autoReturn: { type: Boolean, default: true },
  autoReturnMs: { type: Number, default: 6000 }
})

const router = useRouter()
const { playHoverSound, stopHoverSound } = useIslandSound()

const carouselRef = ref(null)
const currentIndex = ref(props.initialIndex)
let dragStartX = 0
let isDragging = false
let returnTimer = null

const carouselStyle = computed(() => ({
  transform: `translateX(${-currentIndex.value * 178}px)`
}))

/** 3D 透视位姿：中间最大最前，两侧扇形收缩（沿用 HomeView 逻辑） */
function getCardStyle(index) {
  const offset = index - currentIndex.value
  const absOffset = Math.abs(offset)
  const scale = absOffset === 0 ? 1.12 : Math.max(0.72, 1 - absOffset * 0.16)
  const translateZ = absOffset === 0 ? 70 : -absOffset * 42
  const translateY = absOffset === 0 ? -26 : (offset > 0 ? absOffset * 16 : -absOffset * 11)
  const translateX = offset * 82
  const rotateZ = offset * 5
  const opacity = absOffset === 0 ? 1 : Math.max(0.5, 1 - absOffset * 0.22)
  const zIndex = 8 - absOffset
  return {
    transform: `translateX(${translateX}px) translateY(${translateY}px) translateZ(${translateZ}px) scale(${scale}) rotateZ(${rotateZ}deg)`,
    opacity,
    zIndex
  }
}

function go(delta) {
  const n = props.cards.length
  currentIndex.value = (currentIndex.value + delta + n) % n
  scheduleReturn()
}

function onCardClick(index) {
  const card = props.cards[index]
  if (card) {
    const delta = index - currentIndex.value
    const wrap = Math.abs(delta) > props.cards.length / 2
    if (index !== currentIndex.value) {
      currentIndex.value = index
      scheduleReturn()
      return
    }
    router.push(card.path)
  }
}

function onMouseEnter(card) {
  playHoverSound(card.key)
}

function onMouseLeave() {
  stopHoverSound()
}

/* ---- 拖动 / 触摸 ---- */
function onMouseDown(e) {
  dragStartX = e.clientX
  isDragging = true
  window.addEventListener('mouseup', onMouseUp)
}
function onMouseUp(e) {
  window.removeEventListener('mouseup', onMouseUp)
  if (!isDragging) return
  isDragging = false
  const diff = e.clientX - dragStartX
  if (Math.abs(diff) > 50) go(diff < 0 ? 1 : -1)
}
function onTouchStart(e) {
  dragStartX = e.touches[0].clientX
  isDragging = true
}
function onTouchEnd(e) {
  if (!isDragging) return
  isDragging = false
  const diff = (e.changedTouches[0]?.clientX || dragStartX) - dragStartX
  if (Math.abs(diff) > 50) go(diff < 0 ? 1 : -1)
}

/* ---- 键盘 ---- */
function onKeydown(e) {
  if (e.key === 'ArrowLeft') go(-1)
  else if (e.key === 'ArrowRight') go(1)
  else if (e.key === 'Escape') stopHoverSound()
}

/* ---- 空闲自动回位 ---- */
function scheduleReturn() {
  if (!props.autoReturn) return
  clearTimer()
  returnTimer = setTimeout(() => {
    currentIndex.value = props.initialIndex
  }, props.autoReturnMs)
}
function clearTimer() {
  if (returnTimer) {
    clearTimeout(returnTimer)
    returnTimer = null
  }
}

/* ---- 专属篆符路径（简笔文字意象，每岛一条） ---- */
function sigilPath(key) {
  switch (key) {
    case 'music':
      return 'M16 44 L40 20 Q44 16 48 20 L42 28 Q38 24 34 28 L34 44'
    case 'novel':
      return 'M20 16 L44 16 L44 48 L20 44 Z M28 26 L42 26 M28 34 L42 34 M24 18 L24 40'
    case 'video':
      return 'M16 24 L48 24 L48 44 L16 44 Z M24 30 L38 34 L24 40 Z'
    case 'log':
      return 'M18 20 Q30 14 42 20 L42 36 Q30 30 18 36 Z M18 20 L18 36 M30 18 L30 30'
    case 'tool':
      return 'M22 18 Q34 8 44 20 L32 30 L42 40 L30 42 L20 32 Q24 24 22 18 Z'
    case 'notes':
      return 'M24 14 L44 14 L44 50 L20 44 L20 20 Z M28 24 L40 24 M28 32 L40 32 M28 40 L36 40'
    case 'assets':
      return 'M20 22 L32 14 L44 22 L44 46 L20 46 Z M28 22 L36 22 M28 30 L36 30 M16 30 L48 30'
    default: // tasks
      return 'M20 18 L40 18 L44 24 L40 46 L24 46 L20 24 Z M20 24 L44 24 M24 18 L26 12 L38 12 L40 18'
  }
}

/* 确定性伪随机（避免抖动） */
function seeded(i, key) {
  const s = [...key].reduce((a, c) => a + c.charCodeAt(0), 0)
  const x = Math.sin(s * i * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

onUnmounted(() => {
  clearTimer()
  stopHoverSound()
  window.removeEventListener('mouseup', onMouseUp)
})
</script>

<style scoped>
.jade-carousel {
  position: relative;
  width: 100%;
  height: 340px;
  perspective: 1500px;
  perspective-origin: 50% 34%;
  overflow: hidden;
  outline: none;
  user-select: none;
  cursor: default;
}

.carousel-track {
  position: absolute;
  top: 27%;
  left: 50%;
  transform-style: preserve-3d;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  transition: transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  pointer-events: none;
}

/* 玉简：竖条简 + 毛玻璃羊脂青玉釉 */
.jade-card {
  position: relative;
  width: 132px;
  height: 176px;
  cursor: pointer;
  transition: all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
  transform-style: preserve-3d;
  border-radius: 14px;
  z-index: 1;
  pointer-events: auto;
  background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line-strong);
  box-shadow:
    0 8px 22px rgba(58, 67, 80, 0.1),
    0 2px 6px rgba(58, 67, 80, 0.06),
    inset 0 1px 2px rgba(255, 255, 255, 0.8);
}

/* 内侧淡墨细线（呼应玉简篆纹） */
.jade-card::after {
  content: '';
  position: absolute;
  inset: 5px;
  border: 1px solid var(--lj-line);
  border-radius: 9px;
  opacity: 0.45;
  transition: all 0.4s;
  pointer-events: none;
}

.jade-card:hover::after,
.jade-card.is-active::after {
  opacity: 1;
  border-color: var(--lj-dai);
  box-shadow: inset 0 0 12px rgba(74, 95, 99, 0.08);
}

/* 玉体内层：羊脂玉釉晕光 */
.card-inner {
  position: absolute;
  inset: 0;
  border-radius: 13px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background:
    radial-gradient(circle at 30% 18%, rgba(255, 255, 255, 0.55) 0%, rgba(255, 255, 255, 0) 42%),
    linear-gradient(165deg, rgba(255, 255, 255, 0.5) 0%, rgba(255, 255, 255, 0.08) 55%, rgba(74, 95, 99, 0.05) 100%);
}

/* 冰裂纹纹理 */
.card-texture {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, rgba(74, 95, 99, 0.05) 0%, transparent 30%),
    repeating-linear-gradient(45deg, rgba(74, 95, 99, 0.025) 0 1px, transparent 1px 7px),
    repeating-linear-gradient(-45deg, rgba(74, 95, 99, 0.02) 0 1px, transparent 1px 11px);
  pointer-events: none;
  opacity: 0.6;
}

/* 专属篆符 */
.card-sigil {
  width: 52px;
  height: 52px;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 1px 3px rgba(58, 67, 80, 0.15));
  transition: all 0.4s;
}

.card-label {
  font-family: var(--font-serif);
  font-size: 12px;
  color: var(--lj-text-2);
  letter-spacing: 0.22em;
  position: relative;
  z-index: 1;
}

.jade-card:hover .card-sigil,
.jade-card.is-active .card-sigil {
  transform: scale(1.08);
}

.jade-card.is-active {
  box-shadow:
    0 14px 30px rgba(58, 67, 80, 0.14),
    0 0 0 1px var(--lj-line-strong) inset,
    inset 0 1px 2px rgba(255, 255, 255, 0.9);
}

/* 小圆点指示 */
.carousel-dots {
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(251, 250, 246, 0.7);
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border-radius: 999px;
  box-shadow: 0 2px 8px rgba(58, 67, 80, 0.08);
  cursor: default;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lj-line-strong);
  cursor: pointer;
  transition: all 0.3s;
}

.dot:hover { background: var(--lj-mist); }

.dot.active {
  background: var(--lj-dai);
  transform: scale(1.3);
}

@media (prefers-reduced-motion: reduce) {
  .jade-card, .carousel-track, .carousel-dots, .dot { transition: none !important; }
}
</style>
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
        v-for="(card, index) in displayCards"
        :key="card.key"
        class="jade-card"
        :class="{ 'is-active': index === currentIndex }"
        :data-type="card.key"
        :style="getCardStyle(index)"
        @click="onCardClick(index)"
        @pointermove="onCardPointerMove($event)"
        @pointerleave="onCardPointerLeave($event)"
      >
        <!-- 3D 舞台：四层按不同 Z 深度堆叠，形成真实景深 -->
        <div class="card-inner">
          <!-- 层 1｜玉体：羊脂玉釉晕光 + 冰裂纹（z=0，唯一承载裁切的层） -->
          <div class="card-face">
            <div class="card-texture"></div>
          </div>

          <!-- 层 2｜专属 SVG 篆符（z=22） -->
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

          <!-- 层 3｜镭射箔面 + 指针高光（z=38，压在篆符之上呈「覆膜」感） -->
          <div class="card-foil" aria-hidden="true"></div>

          <!-- 层 4｜标签托片（z=54，最前，保证箔面不会糊掉文字） -->
          <div class="card-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- 当前位小圆点指示 -->
    <div class="carousel-dots">
      <span
        v-for="(c, i) in displayCards"
        :key="c.key"
        class="dot"
        :class="{ active: i === currentIndex }"
        @click="currentIndex = i"
      ></span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMenusStore } from '@/stores/menus'

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
      // 家庭助理三件套：通讯录 / 待办 / 订阅（共用生日与续费提醒引擎）
      { key: 'contacts', rune: '家', label: '骨肉亲缘', path: '/contacts',      color: '#a06a4a' },
      { key: 'tasks',    rune: '待', label: '诸事待理', path: '/tasks',         color: '#5a6f5f' },
      { key: 'subs',     rune: '费', label: '细水长流', path: '/subscriptions', color: '#6a6a8a' }
    ]
  },
  initialIndex: { type: Number, default: 0 },
  autoReturn: { type: Boolean, default: true },
  autoReturnMs: { type: Number, default: 3000 }
})

const router = useRouter()
const menus = useMenusStore()

const carouselRef = ref(null)
const currentIndex = ref(props.initialIndex)
let dragStartX = 0
let isDragging = false
let returnTimer = null

// 按角色过滤：被角色限制掉的模块不该在玉简上留卡片（点了也进不去）。
// 菜单尚未加载成功时 isPathAllowed 一律放行，避免接口抖动把主视觉导航清空。
const displayCards = computed(() => props.cards.filter(c => menus.isPathAllowed(c.path)))

// 卡片数量变化后（角色过滤生效）把索引夹回合法范围，否则高亮会落在不存在的卡上
watch(() => displayCards.value.length, (n) => {
  if (!n) { currentIndex.value = 0; return }
  if (currentIndex.value < 0 || currentIndex.value >= n) currentIndex.value = 0
})

const carouselStyle = computed(() => ({
  transform: `translateX(${-currentIndex.value * 178}px)`
}))

/**
 * 3D 透视位姿：中间最大最前，两侧扇形收缩（沿用 HomeView 逻辑）。
 * 末尾追加 rotateX/rotateY，由指针变量 --tl-x/--tl-y 驱动卡片微倾；
 * 因写在同一条 transform 里，倾斜与轮播位移互不覆盖。
 */
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
    transform: `translateX(${translateX}px) translateY(${translateY}px) translateZ(${translateZ}px) scale(${scale}) rotateZ(${rotateZ}deg) rotateX(var(--tl-x, 0deg)) rotateY(var(--tl-y, 0deg))`,
    opacity,
    zIndex
  }
}

/* ---- 指针驱动：箔面扫光 + 卡片微倾（直接写 CSS 变量，避免逐帧触发重渲染） ---- */
const NEUTRAL_POINTER = { '--px': '0.5', '--py': '0.5', '--tl-x': '0deg', '--tl-y': '0deg' }

function onCardPointerMove(e) {
  // 触摸端不做指针跟随（避免拖动轮播时卡片被「甩歪」）
  if (e.pointerType && e.pointerType !== 'mouse') return
  const el = e.currentTarget
  if (!el) return
  const r = el.getBoundingClientRect()
  if (!r.width || !r.height) return
  const px = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width))
  const py = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))
  el.style.setProperty('--px', px.toFixed(3))
  el.style.setProperty('--py', py.toFixed(3))
  // 倾角封顶 ±13°：超过后文字可读性与「反光可信度」都会崩（业界经验值）
  el.style.setProperty('--tl-x', ((0.5 - py) * 12).toFixed(2) + 'deg')
  el.style.setProperty('--tl-y', ((px - 0.5) * 14).toFixed(2) + 'deg')
}

function onCardPointerLeave(e) {
  const el = e.currentTarget
  if (!el) return
  Object.entries(NEUTRAL_POINTER).forEach(([k, v]) => el.style.setProperty(k, v))
}

function go(delta) {
  const n = displayCards.value.length
  if (!n) return
  currentIndex.value = (currentIndex.value + delta + n) % n
  scheduleReturn()
}

function onCardClick(index) {
  const card = displayCards.value[index]
  if (card) {
    if (index !== currentIndex.value) {
      currentIndex.value = index
      scheduleReturn()
      return
    }
    router.push(card.path)
  }
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
}

/* ---- 循环自动轮播（从右往左，每 autoReturnMs 切一张，到底回环） ---- */
function scheduleReturn() {
  if (!props.autoReturn) return
  clearTimer()
  returnTimer = setTimeout(() => {
    const n = displayCards.value.length
    if (!n) return
    currentIndex.value = (currentIndex.value + 1) % n
    scheduleReturn()
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
    case 'contacts':
      // 一人形：头 + 肩
      return 'M32 16 Q39 16 39 24 Q39 32 32 32 Q25 32 25 24 Q25 16 32 16 Z M20 50 Q20 37 32 37 Q44 37 44 50'
    case 'tasks':
      // 简 + 勾
      return 'M22 16 L42 16 L42 48 L22 48 Z M27 26 L37 26 M27 33 L37 33 M26 41 L29 44 L37 36'
    case 'subs':
      // 钱币：外圆 + 十字
      return 'M32 15 Q46 15 46 32 Q46 49 32 49 Q18 49 18 32 Q18 15 32 15 Z M25 32 L39 32 M32 25 L32 39'
    default:
      return 'M20 32 L28 24 L36 32 L28 40 Z'
  }
}

/* 确定性伪随机（避免抖动） */
function seeded(i, key) {
  const s = [...key].reduce((a, c) => a + c.charCodeAt(0), 0)
  const x = Math.sin(s * i * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

onMounted(() => {
  scheduleReturn()
})

onUnmounted(() => {
  clearTimer()
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

/* 玉简：竖条简 + 毛玻璃羊脂青玉釉（向晚·雨青） */
.jade-card {
  position: relative;
  width: 132px;
  height: 176px;
  cursor: pointer;
  transition: all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
  transform-style: preserve-3d;
  border-radius: 16px;
  z-index: 1;
  pointer-events: auto;
  background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.01)), var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line-strong);
  box-shadow:
    0 8px 22px rgba(0, 0, 0, 0.20),
    0 2px 6px rgba(0, 0, 0, 0.10),
    inset 0 1px 0 rgba(255, 255, 255, 0.16),
    0 0 22px rgba(127, 168, 163, 0.08);
}

/* 内侧淡墨细线（呼应玉简篆纹） */
.jade-card::after {
  content: '';
  position: absolute;
  inset: 5px;
  border: 1px solid var(--lj-line);
  border-radius: 11px;
  opacity: 0.45;
  transition: all 0.4s;
  pointer-events: none;
}

.jade-card:hover::after,
.jade-card.is-active::after {
  opacity: 1;
  border-color: var(--lj-seal);
  box-shadow: inset 0 0 14px rgba(217, 138, 118, 0.10);
}

/* 3D 舞台：preserve-3d 让四层在 Z 轴上真正错开；不设 overflow 以免压平子层景深 */
.card-inner {
  position: absolute;
  inset: 0;
  border-radius: 15px;
  transform-style: preserve-3d;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

/* 层 1｜玉体：羊脂玉釉晕光（z=0） */
.card-face {
  position: absolute;
  inset: 0;
  border-radius: 15px;
  overflow: hidden;
  transform: translateZ(0px);
  background:
    radial-gradient(circle at 30% 16%, rgba(255, 255, 255, 0.55) 0%, rgba(255, 255, 255, 0) 44%),
    radial-gradient(ellipse 120% 55% at 110% 105%, rgba(127, 168, 163, 0.16), transparent 60%),
    linear-gradient(170deg, rgba(255, 255, 255, 0.42) 0%, rgba(255, 255, 255, 0.05) 52%, rgba(74, 95, 99, 0.08) 100%);
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

/* 层 2｜专属篆符（z=22，浮出玉体） */
.card-sigil {
  width: 52px;
  height: 52px;
  position: relative;
  z-index: 1;
  transform: translateZ(22px);
  filter: drop-shadow(0 1px 3px rgba(58, 67, 80, 0.15));
  transition: all 0.4s;
}
/* 篆符对比度：整体提笔，激活/悬停卡最清晰 */
.card-sigil path { opacity: 0.92; }
.card-sigil circle { opacity: 0.42; }
.jade-card:hover .card-sigil path,
.jade-card.is-active .card-sigil path { opacity: 1; }

/* 层 3｜镭射箔面：多层渐变叠 mix-blend-mode，随指针扫过（z=38） */
.card-foil {
  position: absolute;
  inset: 0;
  border-radius: 15px;
  overflow: hidden;
  pointer-events: none;
  transform: translateZ(38px);
  opacity: 0;
  mix-blend-mode: var(--jade-foil-blend, color-dodge);
  background-image:
    radial-gradient(circle at calc(var(--px, 0.5) * 100%) calc(var(--py, 0.5) * 100%), var(--jade-glare) 0%, transparent 40%),
    linear-gradient(
      115deg,
      transparent 12%,
      var(--jade-foil-1) 34%,
      var(--jade-foil-2) 46%,
      transparent 54%,
      var(--jade-foil-3) 68%,
      var(--jade-foil-4) 78%,
      transparent 90%
    ),
    repeating-linear-gradient(0deg, transparent 0 3px, var(--jade-foil-grain) 3px 4px);
  background-size: 100% 100%, 300% 300%, 100% 100%;
  background-position: 0 0, calc(var(--px, 0.5) * 100%) calc(var(--py, 0.5) * 100%), 0 0;
  background-repeat: no-repeat, no-repeat, repeat;
  transition: opacity 0.45s ease, background-position 0.18s ease-out;
}
.jade-card:hover .card-foil { opacity: var(--jade-foil-opacity, 0.58); }
.jade-card.is-active .card-foil { opacity: var(--jade-foil-opacity-active, 0.46); }

/* 静止态环境流光：激活卡在未悬停时缓慢自扫，触摸端也能看到质感 */
@media (prefers-reduced-motion: no-preference) {
  .jade-card.is-active:not(:hover) .card-foil {
    animation: jadeFoilSweep 6.5s ease-in-out infinite;
  }
}
@keyframes jadeFoilSweep {
  0%, 100% { background-position: 0 0, 14% 86%, 0 0; }
  50%      { background-position: 0 0, 86% 14%, 0 0; }
}

/* 层 4｜标签托片：微凹玻璃片（简头/简身意象），hover/active 转朱砂（z=54） */
.card-label {
  font-family: var(--font-serif);
  font-size: 12px;
  color: var(--lj-text-2);
  letter-spacing: 0.22em;
  position: relative;
  z-index: 1;
  transform: translateZ(54px);
  padding: 5px 11px 4px;
  border-radius: 999px;
  background: rgba(26, 34, 44, 0.45);
  border: 1px solid var(--lj-line);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
  transition: all 0.35s;
}
.jade-card:hover .card-label,
.jade-card.is-active .card-label {
  color: var(--lj-seal-hover);
  border-color: var(--lj-seal);
  background: var(--lj-seal-soft);
}

.jade-card:hover .card-sigil,
.jade-card.is-active .card-sigil {
  transform: translateZ(22px) scale(1.08);
}

/* 激活卡：柔朱砂光环（克制，非铺满） */
.jade-card.is-active {
  box-shadow:
    0 14px 30px rgba(0, 0, 0, 0.24),
    0 0 0 1px var(--lj-seal) inset,
    inset 0 1px 0 rgba(255, 255, 255, 0.18),
    0 0 26px rgba(217, 138, 118, 0.18);
}

/* 主次层次：激活卡色纯，两侧侧卡轻微退后（不改变卡片几何/尺寸） */
.jade-card:not(.is-active):not(:hover) { filter: saturate(0.9) brightness(0.985); }
.jade-card:not(.is-active):hover { filter: saturate(1) brightness(1.05); }

/* 激活卡篆符：极淡朱砂光晕（材质生动，克制） */
.jade-card.is-active .card-sigil {
  filter: drop-shadow(0 0 6px rgba(217, 138, 118, 0.30)) drop-shadow(0 1px 3px rgba(58, 67, 80, 0.15));
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
  background: rgba(26, 34, 44, 0.65);
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border-radius: 999px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  cursor: default;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--lj-line-strong);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.3, 0.6, 0.3, 1);
}

.dot:hover { background: var(--lj-seal); transform: scale(1.25); }

.dot.active {
  width: 18px;
  background: linear-gradient(90deg, var(--lj-seal), var(--lj-seal-hover));
  box-shadow: 0 0 8px rgba(217, 138, 118, 0.4);
}

@media (prefers-reduced-motion: reduce) {
  .jade-card, .carousel-track, .carousel-dots, .dot,
  .card-inner, .card-foil, .card-sigil, .card-label { transition: none !important; }
  .card-foil { animation: none !important; }
}
</style>

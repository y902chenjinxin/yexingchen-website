<template>
  <div
    class="mj-card"
    :class="{ 'is-fan': fanOpen, 'is-dragging': dragging }"
    @touchstart.passive="onTouchStart"
    @touchmove.passive="onTouchMove"
    @touchend="onTouchEnd"
    @touchcancel="onTouchEnd"
  >
    <!-- 主卡：全幅凹陷层次全息玉片 -->
    <div class="mj-hero">
      <div
        v-for="(c, i) in cards"
        :key="c.key"
        class="mj-face"
        :class="{ active: i === index }"
        :style="faceStyle(i)"
        @transitionstart="onFaceStart(i)"
      >
        <!-- 凹陷层次：内缩台阶 + 顶高光 + 底暗刻 -->
        <div class="mj-face__well">
          <div class="mj-face__jade"></div>
          <div class="mj-face__rift"></div>
          <!-- 专属水墨符 -->
          <svg class="mj-face__sigil" viewBox="0 0 64 64" aria-hidden="true">
            <path :d="sigilPath(c.key)" :fill="c.color" opacity="0.82" />
            <circle v-for="k in 3" :key="k" :cx="seed(k,c.key)*64" :cy="seed(k+7,c.key)*64" r="1.6" :fill="c.color" opacity="0.34"/>
          </svg>
        </div>
        <!-- 全息箔面（原位点亮） -->
        <div class="mj-face__foil"></div>
        <!-- 标签托片 -->
        <div class="mj-face__tag">{{ c.rune }}</div>
        <!-- 底部标签名 -->
        <div class="mj-face__name">{{ c.label }}</div>
      </div>
      <!-- 页码指示 -->
      <div class="mj-dots">
        <span v-for="(c,i) in cards" :key="c.key" class="mj-dot" :class="{active:i===index}" @click="index=i"></span>
      </div>
    </div>

    <!-- 氛围引用（主卡启用态文案） -->
    <p class="mj-quote">{{ cards[index]?.quote || '' }}</p>

    <!-- 长按扇形展开：横向排布全部模块 -->
    <Transition name="mj-fan">
      <div v-if="fanOpen" class="mj-fan">
        <div class="mj-fan__title">一念通万般</div>
        <div class="mj-fan__row">
          <button
            v-for="(c,i) in cards"
            :key="c.key"
            class="mj-fan__chip"
            :style="{ '--chip-d': (i*40)+'deg' }"
            @click="go(c)"
          >
            <span class="mj-fan__chip-ico">{{ c.rune }}</span>
            <span class="mj-fan__chip-lab">{{ c.label }}</span>
          </button>
        </div>
        <p class="mj-fan__hint">轻点前往 · 上滑收起</p>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMenusStore } from '@/stores/menus'

const props = defineProps({
  cards: {
    type: Array,
    default: () => [
      { key:'music', rune:'音', label:'宫商流转', path:'/music', color:'#4a5f63', quote:'一曲清商，万般心绪皆化入弦。' },
      { key:'novel', rune:'書', label:'卷帙浩繁', path:'/novel', color:'#b0805a', quote:'一盏灯，一卷书，一段不眠的长夜。' },
      { key:'video', rune:'影', label:'光影交织', path:'/video', color:'#5b6b7a', quote:'光影之间，藏了百态人生。' },
      { key:'log',   rune:'墨', label:'翰墨丹青', path:'/log', color:'#4a6a56', quote:'把今日，留一盏墨香。' },
      { key:'tool',  rune:'器', label:'机关百变', path:'/tool', color:'#6a7a6a', quote:'七十二般兵器，皆备于匣。' },
      { key:'notes', rune:'記', label:'笔记云台', path:'/notes', color:'#55706b', quote:'所思所记，皆有归处。' },
      { key:'contacts', rune:'家', label:'骨肉亲缘', path:'/contacts', color:'#a06a4a', quote:'念念不忘，四时有回响。' },
      { key:'tasks',  rune:'待', label:'诸事待理', path:'/tasks',  color:'#5a6f5f', quote:'一日之计，在晨昏之间。' },
      { key:'subs',   rune:'费', label:'细水长流', path:'/subscriptions', color:'#6a6a8a', quote:'涓滴成流，常在常新。' },
    ],
  },
})

const router = useRouter()
const menus = useMenusStore()
const displayCards = computed(() => props.cards.filter(c => menus.isPathAllowed(c.path)))

const index = ref(0)
const fanOpen = ref(false)
const dragging = ref(false)
let startX = 0, startY = 0, dx = 0, dy = 0, tracking = false, panT = null, fanT = null
let cardAnim = false

function faceStyle(i) {
  const off = i - index.value
  return {
    transform: `translateX(${off * 62}px) scale(${off===0?1:0.9}) rotateY(${-off*6}deg)`,
    opacity: off === 0 ? 1 : 0.55,
    zIndex: 20 - Math.abs(off),
    pointerEvents: off === 0 ? 'auto' : 'none',
  }
}

function onFaceStart(i) {
  cardAnim = i === index.value
}

/* 滑动横切 + 区分纵向滚动 */
function onTouchStart(e) {
  const t = e.touches[0]
  startX = t.clientX; startY = t.clientY; dx = 0; dy = 0
  tracking = true; cardAnim = false
  clearTimeout(panT); clearTimeout(fanT)
  panT = setTimeout(() => {
    if (tracking && Math.abs(dx) < 6 && Math.abs(dy) < 8) {
      fanOpen.value = true
    }
  }, 560)
}
function onTouchMove(e) {
  if (!tracking) return
  const t = e.touches[0]
  const cx = t.clientX, cy = t.clientY
  dx = cx - startX; dy = cy - startY
  if (Math.abs(dx) > 8 || Math.abs(dy) > 10) {
    clearTimeout(panT)
    fanOpen.value = false
  }
  if (Math.abs(dy) > Math.abs(dx)) { dragging.value = true }
}
function onTouchEnd(e) {
  tracking = false; dragging.value = false
  clearTimeout(panT)
  clearTimeout(fanT)
  const n = displayCards.value.length
  if (dy && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 70) {
    fanOpen.value = false
  } else if (Math.abs(dx) > 46) {
    if (!cardAnim) {
      const delta = dx < 0 ? 1 : -1
      index.value = (index.value + delta + n) % n
    }
  }
}

function go(c) { if (c) { fanOpen.value = false; router.push(c.path) } }

function buzz() { try { if (navigator && navigator.vibrate) navigator.vibrate(6) } catch {} }

function sigilPath(key) {
  switch (key) {
    case 'music': return 'M16 44 L40 20 Q44 16 48 20 L42 28 Q38 24 34 28 L34 44'
    case 'novel': return 'M20 16 L44 16 L44 48 L20 44 Z M28 26 L42 26 M28 34 L42 34 M24 18 L24 40'
    case 'video': return 'M16 24 L48 24 L48 44 L16 44 Z M24 30 L38 34 L24 40 Z'
    case 'log': return 'M18 20 Q30 14 42 20 L42 36 Q30 30 18 36 Z M18 20 L18 36 M30 18 L30 30'
    case 'tool': return 'M22 18 Q34 8 44 20 L32 30 L42 40 L30 42 L20 32 Q24 24 22 18 Z'
    case 'notes': return 'M24 14 L44 14 L44 50 L20 44 L20 20 Z M28 24 L40 24 M28 32 L40 32 M28 40 L36 40'
    case 'contacts': return 'M32 16 Q39 16 39 24 Q39 32 32 32 Q25 32 25 24 Q25 16 32 16 Z M20 50 Q20 37 32 37 Q44 37 44 50'
    case 'tasks': return 'M22 16 L42 16 L42 48 L22 48 Z M27 26 L37 26 M27 33 L37 33 M26 41 L29 44 L37 36'
    case 'subs': return 'M32 15 Q46 15 46 32 Q46 49 32 49 Q18 49 18 32 Q18 15 32 15 Z M25 32 L39 32 M32 25 L32 39'
    default: return 'M20 32 L28 24 L36 32 L28 40 Z'
  }
}
function seed(i, key) {
  const s = [...key].reduce((a, c) => a + c.charCodeAt(0), 0)
  const x = Math.sin(s * i * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

onUnmounted(() => { clearTimeout(panT); clearTimeout(fanT) })
</script>

<style scoped>
.mj-card {
  position: relative;
  width: 100%;
  user-select: none;
  -webkit-user-select: none;
  touch-action: pan-y;
  -webkit-tap-highlight-color: transparent;
}

/* ===== 主卡舞台：近全幅、深景深舞台 ===== */
.mj-hero {
  position: relative;
  height: 240px;
  perspective: 1100px;
  perspective-origin: 50% 42%;
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
}
.mj-face {
  position: absolute;
  left: 50%; top: 50%;
  width: 250px; height: 176px;
  margin-left: -125px; margin-top: -88px;
  transform-style: preserve-3d;
  transition: transform .5s cubic-bezier(.25,.46,.45,.94), opacity .5s ease;
  border-radius: 24px;
  pointer-events: none;
}
.mj-face.active { pointer-events: auto; }

/* 凹陷层次井：外框 + 内缩台阶，模拟按下/内凹 */
.mj-face__well {
  position: absolute; inset: 0;
  border-radius: 24px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(0,0,0,.18), rgba(255,255,255,.03) 30%, rgba(0,0,0,.22)),
    var(--lj-glass, rgba(30,42,50,.66));
  -webkit-backdrop-filter: var(--lj-glass-blur, blur(20px));
  backdrop-filter: var(--lj-glass-blur, blur(20px));
  border: 1px solid var(--lj-line-strong, rgba(127,168,163,.34));
  box-shadow:
    0 24px 46px rgba(0,0,0,.34),
    0 8px 18px rgba(0,0,0,.22),
    inset 0 2px 0 rgba(255,255,255,.2),
    inset 0 -18px 30px rgba(0,0,0,.28),
    inset 0 0 0 7px rgba(0,0,0,.06); /* 内凹台阶 */
}
/* 玉面 */
.mj-face__jade {
  position: absolute; inset: 6px;
  border-radius: 19px;
  background:
    radial-gradient(circle at 32% 18%, rgba(255,255,255,.34), transparent 46%),
    radial-gradient(ellipse 120% 56% at 108% 106%, rgba(127,168,163,.22), transparent 60%),
    linear-gradient(168deg, rgba(255,255,255,.14), rgba(74,95,99,.06) 60%);
}
.mj-face__rift {
  position: absolute; inset: 10px;
  border-radius: 16px;
  border: 1px solid var(--lj-line, rgba(127,168,163,.2));
  opacity: .5;
  background:
    repeating-linear-gradient(45deg, rgba(74,95,99,.03) 0 1px, transparent 1px 6px),
    repeating-linear-gradient(-45deg, rgba(74,95,99,.02) 0 1px, transparent 1px 9px);
}
.mj-face__sigil {
  position: absolute; left: 50%; top: 38%; width: 56px; height: 56px;
  transform: translate(-50%,-50%);
  filter: drop-shadow(0 2px 5px rgba(0,0,0,.28));
}
/* 标签托片 */
.mj-face__tag {
  position: absolute; left: 50%; bottom: 22px; transform: translateX(-50%);
  font-family: var(--font-serif, serif);
  font-size: 12px; letter-spacing: .4em; text-indent: .4em;
  padding: 4px 13px 3px; border-radius: 999px;
  color: var(--lj-text-2, rgba(190,205,200,.78));
  background: rgba(12,20,16,.5);
  border: 1px solid var(--lj-line, rgba(127,168,163,.3));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08);
}
.mj-face__name {
  position: absolute; left: 0; right: 0; bottom: -30px;
  text-align: center; font-size: 14px; font-weight: 600;
  color: var(--lj-text, #dfebe5); letter-spacing: .14em;
  opacity: 0; transform: translateY(4px);
  transition: opacity .4s ease, transform .4s ease;
}
.mj-face.active .mj-face__name { opacity: 1; transform: translateY(0); }

/* 全息箔面：琥珀金斜条 + 扫光 */
.mj-face__foil {
  position: absolute; inset: 6px; border-radius: 19px;
  mix-blend-mode: color-dodge;
  opacity: 0;
  background-image:
    linear-gradient(115deg, transparent 12%, rgba(230,195,135,.5) 34%, rgba(201,163,95,.6) 46%, transparent 56%, rgba(230,195,135,.38) 72%, transparent 86%);
  background-size: 320% 320%;
  background-position: 0 0;
  transition: background-position .3s ease-out;
  pointer-events: none;
}
.mj-face.active .mj-face__foil { animation: mjSweep 7s ease-in-out infinite; }

@media (prefers-reduced-motion: reduce) {
  .mj-face { transition: none; }
  .mj-face__foil { animation: none !important; }
}
@keyframes mjSweep {
  0%,100% { opacity: 0; background-position: 60% 40%; }
  18%      { opacity: .4; }
  42%      { opacity: 0; background-position: 20% 70%; }
}

/* 页码指示 */
.mj-dots {
  position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 6px; padding: 5px 10px; border-radius: 999px;
  background: rgba(12,20,16,.5);
  -webkit-backdrop-filter: var(--lj-glass-blur, blur(14px));
  backdrop-filter: var(--lj-glass-blur, blur(14px));
  pointer-events: auto; z-index: 30;
}
.mj-dot { width: 5px; height: 5px; border-radius: 999px; background: var(--lj-line-strong, rgba(127,168,163,.5)); transition: all .3s; }
.mj-dot.active { width: 16px; background: linear-gradient(90deg, var(--lj-seal,#c96b58), #e0a26b); box-shadow: 0 0 8px rgba(217,138,118,.5); }

/* 氛围引用 */
.mj-quote {
  margin: 34px auto 0; max-width: 78%;
  text-align: center; font-size: 12.5px; letter-spacing: .16em; line-height: 1.6;
  color: var(--lj-text-3, rgba(200,215,220,.55));
  min-height: 20px;
}
@media (prefers-reduced-motion: no-preference) {
  .mj-quote { animation: mjRise .5s ease both; }
}
@keyframes mjRise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

/* ===== 长按扇形展开 ===== */
.mj-fan {
  position: absolute; left: 0; right: 0; top: 0; bottom: 0;
  z-index: 200;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 18px;
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(12,20,16,.55), rgba(12,20,16,.82));
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  backdrop-filter: blur(20px) saturate(140%);
  overflow: hidden;
}
.mj-fan__title { font-family: var(--font-serif, serif); font-size: 15px; letter-spacing: .5em; text-indent: .5em; color: var(--lj-amber, #caa466); }
.mj-fan__row {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 12px;
  max-width: 86%; padding: 6px 0;
}
.mj-fan__chip {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 10px 6px 8px; width: 62px;
  border-radius: 18px;
  background: var(--lj-glass, rgba(30,42,50,.6));
  -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px);
  border: 1px solid var(--lj-line, rgba(127,168,163,.22));
  color: var(--lj-text, #dfebe5);
  box-shadow: 0 10px 22px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.08);
  animation: chipIn .45s cubic-bezier(.2,.8,.2,1) backwards;
  animation-delay: calc(var(--chip-d) * .004s);
  transition: transform .2s, border-color .2s;
}
.mj-fan__chip:active { transform: scale(.93); border-color: var(--lj-amber,#caa466); }
.mj-fan__chip-ico {
  font-family: var(--font-serif, serif); font-size: 20px; color: var(--lj-amber, #caa466);
  width: 34px; height: 34px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  background: rgba(201,163,95,.14);
}
.mj-fan__chip-lab { font-size: 11px; letter-spacing: .08em; opacity: .9; }
.mj-fan__hint { font-size: 11px; letter-spacing: .12em; opacity: .5; }
@keyframes chipIn { from { opacity: 0; transform: translateY(14px) scale(.92); } to { opacity: 1; transform: none; } }

/* 过渡 */
.mj-fan-enter-active, .mj-fan-leave-active { transition: opacity .3s ease, transform .3s ease; }
.mj-fan-enter-from, .mj-fan-leave-to { opacity: 0; transform: scale(.96); }
</style>
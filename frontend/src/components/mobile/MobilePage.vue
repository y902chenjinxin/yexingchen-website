<template>
  <section class="mpage" :class="{ pinned }">
    <div class="mpage-scroll" ref="scrollEl" @scroll="onScroll"
         @touchstart.passive="onStart" @touchmove.passive="onMove" @touchend="onEnd">
      <!-- 固定导航：返回 + 小标题（滚动后浮现） -->
      <header class="mpage-nav">
        <button v-if="showBack" class="mpage-back" @click="goBack" aria-label="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>
        </button>
        <span class="mpage-navtitle">{{ title }}</span>
        <span v-if="$slots['nav-action']" class="mpage-navaction"><slot name="nav-action" /></span>
      </header>

      <!-- iOS 大标题 -->
      <div class="mpage-head">
        <h1 class="mpage-big" v-if="title">{{ title }}</h1>
        <div v-if="$slots.tools" class="mpage-tools"><slot name="tools" /></div>
      </div>

      <div class="mpage-body"><slot /></div>
    </div>
  </section>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  title: { type: String, default: '' },
  showBack: { type: Boolean, default: true },
  // 无历史时回退的路径
  fallback: { type: String, default: '/workbench' },
})

const emit = defineEmits(['back'])
const router = useRouter()

const scrollEl = ref(null)
const pinned = ref(false)
function onScroll() {
  const el = scrollEl.value
  pinned.value = el ? el.scrollTop > 4 : false
}

function buzz() { try { if (navigator && navigator.vibrate) navigator.vibrate(8) } catch { /* noop */ } }

function goBack() {
  buzz()
  emit('back')
  if (window.history.length > 1) { try { window.history.back(); return } catch { /* ignore */ } }
  router.push(props.fallback)
}

/* 左缘侧滑返回（iOS 手势）：从屏幕左缘横向拖动超 90px 触发 */
let sx = 0, sy = 0, dragX = 0, tracking = false
function onStart(e) {
  const t = e.touches && e.touches[0]
  if (!t) return
  sx = t.clientX; sy = t.clientY; dragX = 0
  tracking = sx < 34
}
function onMove(e) {
  if (!tracking) return
  const t = e.touches && e.touches[0]
  if (!t) return
  dragX = t.clientX - sx
  if (Math.abs(t.clientY - sy) > 40) tracking = false
}
function onEnd() {
  if (tracking && dragX > 90) goBack()
  tracking = false
}

// 轻量借用（不走 useRouter 循环）：history 有栈时直接 back
function useRouterBorrow() {
  return null
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.showBack) goBack()
}
window.addEventListener('keydown', onKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.mpage {
  height: 100dvh;
  min-height: 100svh;
  display: flex;
  flex-direction: column;
  background: var(--ls-bg, #0d1a15);
  color: var(--ls-text, #dfebe5);
}
.mpage-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch; }

.mpage-nav {
  position: sticky; top: 0; z-index: 20;
  display: flex; align-items: center; gap: 8px;
  height: 56px;
  padding: calc(env(safe-area-inset-top, 0px)) 14px 0;
  transition: background .3s ease, box-shadow .3s ease, border-color .3s ease;
  border-bottom: 1px solid transparent;
  border-radius: 0 0 22px 22px;
}
.mpage.pinned .mpage-nav {
  background: linear-gradient(180deg, rgba(20,30,28,.82), rgba(20,30,28,.6));
  -webkit-backdrop-filter: saturate(150%) blur(14px);
  backdrop-filter: saturate(150%) blur(14px);
  border-bottom-color: rgba(127,168,163,.16);
  box-shadow: 0 8px 24px rgba(0,0,0,.22);
}
.mpage-back {
  width: 40px; height: 40px; flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--ls-line, rgba(127,168,163,.2));
  border-radius: 12px; background: rgba(255,255,255,.04);
  color: var(--ls-text); cursor: pointer; transition: all .2s;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
.mpage-back:active { transform: scale(.94); color: var(--ls-amber, #caa466); }
.mpage-back svg { width: 20px; height: 20px; }
.mpage-navtitle {
  font-size: 17px; font-weight: 600; letter-spacing: .02em;
  opacity: 0; transform: translateY(2px);
  transition: opacity .28s ease, transform .28s ease;
}
.mpage.pinned .mpage-navtitle { opacity: 1; transform: translateY(0); }
.mpage-navaction { margin-left: auto; }

.mpage-head {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 12px;
  padding: 6px 20px 14px;
}
.mpage-big {
  margin: 0; font-size: clamp(24px, 6vw, 30px); font-weight: 700;
  letter-spacing: .02em; line-height: 1.15;
  transition: font-size .3s ease, opacity .3s ease;
}
.mpage.pinned .mpage-big { font-size: clamp(21px, 5vw, 25px); opacity: .85; }
.mpage-tools { display: flex; align-items: center; gap: 8px; flex: none; padding-bottom: 2px; }

.mpage-body { padding: 0 16px calc(28px + env(safe-area-inset-bottom, 0px)); }
</style>
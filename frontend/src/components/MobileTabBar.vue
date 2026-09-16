<template>
  <nav class="mt-tabbar" aria-label="移动端主导航">
    <button
      v-for="t in tabs"
      :key="t.path"
      class="mt-tab"
      :class="{ active: isActive(t) }"
      @click="go(t)"
      :aria-label="t.label"
    >
      <span class="mt-ico" aria-hidden="true" v-html="t.icon"></span>
      <span class="mt-lab">{{ t.label }}</span>
    </button>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const tabs = [
  {
    path: '/tool',
    label: '工具',
    active: (p) => p === '/tool' || p.startsWith('/tool/'),
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4.5 4.5 0 1 0-5.1 6.8l-5.3 5.3a1 1 0 0 0 1.4 1.4l5.3-5.3a4.5 4.5 0 0 0 6.8-5.1l-2.6 2.6-2.1-.3-.3-2.1 2.6-2.6z"/></svg>',
  },
  {
    path: '/workbench',
    label: '工作台',
    active: (p) => p === '/workbench',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 9.5 12 3.5l8.5 6"/><path d="M5.5 8.5V20h13V8.5"/><rect x="9" y="12" width="6" height="3.2" rx="1"/></svg>',
  },
  {
    path: '/profile',
    label: '我的',
    active: (p) => p === '/profile',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.6"/><path d="M4.8 19.5a7.6 7.6 0 0 1 14.4 0"/></svg>',
  },
]

const isActive = (t) => t.active(route.path)

function buzz() {
  // iOS 质感触感反馈：轻震动，无音效；iOS 自动忽略 vibrate
  try { if (navigator && navigator.vibrate) navigator.vibrate(8) } catch { /* noop */ }
}

function go(t) {
  buzz()
  if (route.path !== t.path) router.push(t.path)
}
</script>

<style scoped>
.mt-tabbar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  z-index: 1500;
  display: flex;
  padding: 6px 12px calc(6px + var(--safe-bottom, env(safe-area-inset-bottom, 0px)));
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0) 40%), var(--lj-glass, rgba(30,42,50,.68));
  -webkit-backdrop-filter: var(--lj-glass-blur, blur(18px));
  backdrop-filter: var(--lj-glass-blur, blur(18px));
  border-top: 1px solid var(--lj-line, rgba(127,168,163,.18));
  box-shadow: 0 -10px 30px rgba(0,0,0,.20), inset 0 1px 0 rgba(255,255,255,.06);
}

.mt-tab {
  flex: 1;
  min-height: 54px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--lj-text-2, rgba(200,215,220,.66));
  transition: color .25s ease, transform .15s ease;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  position: relative;
}
.mt-tab:active { color: var(--lj-ochre, #caa466); transform: translateY(1px) scale(.98); }

.mt-tab::after {
  content: '';
  position: absolute;
  top: -7px;
  width: 40px; height: 2px; border-radius: 2px;
  background: radial-gradient(circle, rgba(202,164,102,.9), transparent 70%);
  opacity: 0;
  transition: opacity .25s ease;
}
.mt-tab.active::after { opacity: 1; }

.mt-ico { width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; }
.mt-ico svg { width: 100%; height: 100%; }

.mt-tab.active { color: var(--lj-ochre, #caa466); }
.mt-tab.active .mt-ico { filter: drop-shadow(0 0 6px rgba(202,164,102,.45)); }

.mt-lab { font-size: 11px; letter-spacing: .04em; }
</style>
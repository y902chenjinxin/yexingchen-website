<template>
  <nav class="mt-tabbar" aria-label="移动端主导航">
    <button
      v-for="t in tabs"
      :key="t.path"
      class="mt-tab"
      :class="{ active: isActive(t) }"
      @click="go(t)"
      :aria-label="t.label"
      :aria-current="isActive(t) ? 'page' : undefined"
    >
      <span class="mt-ico" aria-hidden="true" v-html="t.icon"></span>
      <span class="mt-lab">{{ t.label }}</span>
    </button>
  </nav>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

/* 两 Tab：主页 / 我的（工具经主页快捷入口直达，不再占用主导航） */
const tabs = [
  {
    path: '/workbench',
    label: '主页',
    active: (p) => p === '/workbench',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 10.2 12 4l8.5 6.2"/><path d="M5.5 8.8V20h13V8.8"/><rect x="9.6" y="12.5" width="4.8" height="3" rx="1.2"/></svg>',
  },
  {
    path: '/profile',
    label: '我的',
    active: (p) => p === '/profile',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.4"/><path d="M5 19.5a7.3 7.3 0 0 1 14 0"/></svg>',
  },
]

const isActive = (t) => t.active(route.path)

function buzz() {
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
  padding: 6px 20px calc(6px + var(--safe-bottom, env(safe-area-inset-bottom, 0px)));
  justify-content: space-around;
  background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0) 45%), var(--lj-glass, rgba(22,30,39,.62));
  -webkit-backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  border-top: 1px solid var(--lj-line, rgba(15,40,70,.14));
  box-shadow: 0 -10px 30px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.06);
}

.mt-tab {
  flex: 1;
  max-width: 200px;
  min-height: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--lj-text-3, #8a8f98);
  transition: color .25s ease, transform .15s ease;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}
.mt-tab:active { transform: translateY(1px) scale(.98); }

.mt-ico { width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center; transition: transform .2s ease; }
.mt-ico svg { width: 100%; height: 100%; }

.mt-tab.active { color: var(--lj-dai, #5b6ae0); }
.mt-tab.active .mt-ico svg { stroke-width: 2; }
.mt-tab.active .mt-ico { transform: translateY(-1px); }

.mt-lab { font-size: 11px; letter-spacing: .04em; }
.mt-tab.active .mt-lab { font-weight: 600; }
</style>
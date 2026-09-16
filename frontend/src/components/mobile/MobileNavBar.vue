<template>
  <header class="mn-nav" :class="{ 'has-line': bordered }">
    <button v-if="showBack" class="mn-back" @click="goBack" aria-label="返回">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>
    </button>
    <span v-else class="mn-spacer" aria-hidden="true"></span>
    <h1 class="mn-title">
      <span v-if="icon" class="mn-ico" aria-hidden="true" v-html="icon"></span>{{ title }}
    </h1>
    <span class="mn-action"><slot name="action" /></span>
  </header>
</template>

<script setup>
import { onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  title: { type: String, default: '' },
  icon: { type: String, default: '' },
  showBack: { type: Boolean, default: true },
  // 无历史时回退的路径
  fallback: { type: String, default: '/workbench' },
  bordered: { type: Boolean, default: true },
})

const emit = defineEmits(['back'])
const router = useRouter()

function buzz() { try { if (navigator && navigator.vibrate) navigator.vibrate(8) } catch { /* noop */ } }

function goBack() {
  buzz()
  emit('back')
  if (window.history.length > 1) { try { window.history.back(); return } catch { /* ignore */ } }
  router.push(props.fallback)
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.showBack) goBack()
}
window.addEventListener('keydown', onKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.mn-nav {
  position: relative;
  z-index: 20;
  display: grid;
  grid-template-columns: 48px 1fr 48px;
  align-items: center;
  height: 52px;
  padding: calc(env(safe-area-inset-top, 0px)) 8px 0;
  border-bottom: 1px solid transparent;
  transition: border-color .3s ease;
}
.mn-nav.has-line {
  border-bottom-color: var(--ls-line, rgba(127,168,163,.14));
}
.mn-back {
  width: 38px; height: 38px; justify-self: start;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--ls-line, rgba(127,168,163,.2));
  border-radius: 12px; background: rgba(255,255,255,.04);
  color: var(--ls-text); cursor: pointer; transition: transform .2s;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
.mn-back:active { transform: scale(.92); color: var(--ls-amber, #caa466); }
.mn-back svg { width: 20px; height: 20px; }
.mn-spacer { width: 38px; justify-self: start; }

.mn-title {
  margin: 0; font-size: 17px; font-weight: 600; letter-spacing: .02em;
  text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.mn-ico { display: inline-flex; color: var(--ls-amber, #caa466); }
.mn-ico svg { width: 18px; height: 18px; }
.mn-action { justify-self: end; display: inline-flex; align-items: center; }
</style>
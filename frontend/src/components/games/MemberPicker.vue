<template>
  <div ref="wrapEl" class="mp-wrap">
    <button
      type="button"
      class="mp-trigger"
      :class="{ open, empty: !selected }"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="toggle"
      @keydown.down.prevent="openList(0)"
      @keydown.enter.prevent="toggle"
      @keydown.esc="open = false"
    >
      <template v-if="selected">
        <span class="mp-ava">{{ selected.avatar || '🌿' }}</span>
        <span class="mp-name">{{ selected.display_name || '家人' }}</span>
      </template>
      <span v-else class="mp-ph">{{ placeholder }}</span>
      <span class="mp-caret" aria-hidden="true">▾</span>
    </button>

    <!-- 弹层 Teleport 到 body：辅栏在放大模式下可滚动，留在原地会被裁切 -->
    <Teleport to="body">
      <div v-if="open" class="mp-layer" @click.self="open = false">
        <ul
          ref="listEl"
          class="mp-list"
          role="listbox"
          :style="panelStyle"
          @keydown.esc="open = false"
        >
          <li
            v-for="(m, i) in members"
            :key="m.user_id"
            class="mp-item"
            :class="{ on: m.user_id === modelValue, hi: i === hi }"
            role="option"
            :aria-selected="m.user_id === modelValue"
            @click="pick(m)"
            @mousemove="hi = i"
          >
            <span class="mp-ava">{{ m.avatar || '🌿' }}</span>
            <span class="mp-name">{{ m.display_name || '家人' }}</span>
            <span v-if="m.user_id === modelValue" class="mp-check" aria-hidden="true">✓</span>
          </li>
          <li v-if="!members.length" class="mp-empty">家庭里还没有其他账号可以邀请</li>
        </ul>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
/** 家人选择器（棋类在线邀请用）。
 *
 * 替代原生 `<select>`：原生下拉在玻璃质感的棋局面板里是一块白底系统控件，突兀且无法加头像。
 * 这里做成「头像 + 昵称」的玻璃弹层，弹层 Teleport 到 body —— 放大模式下辅栏是
 * overflow-y:auto 的滚动容器，留在原地会被裁掉下半截。
 */
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  members: { type: Array, default: () => [] },
  placeholder: { type: String, default: '选择一位家人…' },
})
const emit = defineEmits(['update:modelValue'])

const wrapEl = ref(null)
const listEl = ref(null)
const open = ref(false)
const hi = ref(0)
const pos = ref({ top: 0, left: 0, width: 0 })

const selected = computed(() => props.members.find((m) => m.user_id === props.modelValue) || null)
const panelStyle = computed(() => ({
  top: pos.value.top + 'px',
  left: pos.value.left + 'px',
  width: pos.value.width + 'px',
}))

function place() {
  const r = wrapEl.value?.getBoundingClientRect()
  if (!r) return
  const H = 260
  const below = window.innerHeight - r.bottom - 8
  // 下方放不下且上方更宽裕 → 向上展开（贴住触发器上沿）
  const up = below < Math.min(H, 160) && r.top > below
  pos.value = {
    top: up ? Math.max(8, r.top - 8 - Math.min(H, r.top - 8)) : r.bottom + 6,
    left: r.left,
    width: r.width,
  }
}

function openList(startHi = null) {
  if (!props.members.length) { open.value = true; place(); return }
  hi.value = startHi ?? Math.max(0, props.members.findIndex((m) => m.user_id === props.modelValue))
  open.value = true
  place()
  nextTick(() => listEl.value?.focus?.())
}
function toggle() { open.value ? (open.value = false) : openList() }
function pick(m) { emit('update:modelValue', m.user_id); open.value = false }

function onDocDown(e) {
  if (!open.value) return
  if (wrapEl.value?.contains(e.target)) return
  if (listEl.value?.contains(e.target)) return
  open.value = false
}
function onReflow() { if (open.value) place() }
function onKey(e) {
  if (!open.value) return
  if (e.key === 'ArrowDown') { e.preventDefault(); hi.value = Math.min(props.members.length - 1, hi.value + 1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); hi.value = Math.max(0, hi.value - 1) }
  else if (e.key === 'Enter') { e.preventDefault(); const m = props.members[hi.value]; if (m) pick(m) }
  else if (e.key === 'Escape') { open.value = false }
}

watch(open, (v) => {
  if (v) {
    document.addEventListener('mousedown', onDocDown)
    window.addEventListener('scroll', onReflow, true)
    window.addEventListener('resize', onReflow)
    document.addEventListener('keydown', onKey)
  } else {
    document.removeEventListener('mousedown', onDocDown)
    window.removeEventListener('scroll', onReflow, true)
    window.removeEventListener('resize', onReflow)
    document.removeEventListener('keydown', onKey)
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocDown)
  window.removeEventListener('scroll', onReflow, true)
  window.removeEventListener('resize', onReflow)
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.mp-wrap { position: relative; width: 100%; }
.mp-trigger {
  display: flex; align-items: center; gap: 9px; width: 100%;
  padding: 9px 12px; border-radius: 12px; cursor: pointer; font-family: inherit;
  font-size: 13.5px; text-align: left;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14));
  background: linear-gradient(160deg, rgba(255,255,255,.9), rgba(255,255,255,.62));
  color: var(--dp-text, #18202a);
  transition: border-color .2s, box-shadow .2s, background .2s;
}
.mp-trigger:hover { border-color: rgba(199,169,107,.6); box-shadow: 0 2px 10px rgba(199,169,107,.16); }
.mp-trigger.open { border-color: var(--yq-gold, #c7a96b); box-shadow: 0 0 0 3px rgba(199,169,107,.18); }
.mp-trigger.empty .mp-ph { color: var(--dp-text3, #8a8f98); }
.mp-ava {
  width: 24px; height: 24px; flex: none; border-radius: 50%; display: grid; place-items: center;
  font-size: 14px; line-height: 1;
  background: rgba(127,168,163,.16); border: 1px solid rgba(127,168,163,.3);
}
.mp-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mp-ph { flex: 1; min-width: 0; }
.mp-caret { flex: none; font-size: 11px; color: var(--dp-text3, #8a8f98); transition: transform .2s; }
.mp-trigger.open .mp-caret { transform: rotate(180deg); }

/* ===== 弹层 ===== */
.mp-layer { position: fixed; inset: 0; z-index: 3200; }
.mp-list {
  position: fixed; margin: 0; padding: 6px; list-style: none; outline: none;
  max-height: 260px; overflow-y: auto;
  border-radius: 14px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  background: linear-gradient(160deg, rgba(255,255,255,.97), rgba(250,248,243,.95));
  box-shadow: 0 18px 42px rgba(20,30,40,.18), inset 0 1px 0 rgba(255,255,255,.7);
  backdrop-filter: blur(14px);
  animation: mpin .16s cubic-bezier(.4,.1,.2,1);
}
@keyframes mpin { from { opacity: 0; transform: translateY(-4px) } }
.mp-item {
  display: flex; align-items: center; gap: 9px; padding: 8px 10px; border-radius: 10px;
  font-size: 13.5px; color: var(--dp-text, #18202a); cursor: pointer;
  border: 1px solid transparent; transition: background .15s, border-color .15s;
}
.mp-item.hi { background: rgba(199,169,107,.12); }
.mp-item.on { background: rgba(199,169,107,.18); border-color: rgba(199,169,107,.55); font-weight: 600; }
.mp-check { flex: none; font-size: 12px; color: var(--yq-gold, #c7a96b); }
.mp-empty { padding: 10px; font-size: 12.5px; color: var(--dp-text3, #8a8f98); text-align: center; }

/* ===== 夜间主题 ===== */
:root[data-theme="night"] .mp-trigger {
  background: linear-gradient(160deg, rgba(255,255,255,.1), rgba(255,255,255,.05));
  border-color: rgba(255,255,255,.2); color: #f2eee4;
}
:root[data-theme="night"] .mp-trigger.empty .mp-ph { color: #b9b3cc; }
:root[data-theme="night"] .mp-caret { color: #b9b3cc; }
:root[data-theme="night"] .mp-list {
  background: linear-gradient(160deg, rgba(38,44,58,.98), rgba(22,26,36,.97));
  border-color: rgba(199,169,107,.3);
  box-shadow: 0 18px 42px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.07);
}
:root[data-theme="night"] .mp-item { color: #f2eee4; }
:root[data-theme="night"] .mp-item.hi { background: rgba(199,169,107,.16); }
:root[data-theme="night"] .mp-item.on { background: rgba(199,169,107,.24); border-color: rgba(199,169,107,.6); }
:root[data-theme="night"] .mp-empty { color: #b9b3cc; }
</style>
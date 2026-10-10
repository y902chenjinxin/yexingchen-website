<template>
  <!-- 提交按钮状态机（APP_design.md #3 · v2.46.33）：
       同一按钮位置依次呈现 空闲→加载→成功/失败 四态，不替换组件。
       四态文案用 grid 叠放在同一格 —— 宽度取最长态，尺寸与位置全程稳定。 -->
  <button
    class="xz-sbtn"
    :class="[`is-${state}`, $attrs.class]"
    :disabled="state === 'loading'"
    @click="onClick"
  >
    <span class="xz-sbtn-layer" :class="{ on: state === 'idle' }">{{ label }}</span>
    <span class="xz-sbtn-layer" :class="{ on: state === 'loading' }"><i class="xz-sbtn-dot"></i>{{ loadingLabel }}<em v-if="elapsed" class="xz-sbtn-eta">{{ elapsed }}s</em></span>
    <span class="xz-sbtn-layer" :class="{ on: state === 'success' }">✓ {{ doneLabel }}</span>
    <span class="xz-sbtn-layer" :class="{ on: state === 'error' }">{{ errorLabel }}</span>
  </button>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { haptic } from '@/utils/haptic'

const props = defineProps({
  /** async 动作：resolve → 成功态；reject → 失败态 */
  action: { type: Function, required: true },
  label: { type: String, required: true },
  loadingLabel: { type: String, default: '保存中…' },
  doneLabel: { type: String, default: '已完成' },
  errorLabel: { type: String, default: '未成功，重试' },
  /** 成功/失败态停留时长（ms），之后自动回到 idle */
  hold: { type: Number, default: 900 },
})

const state = ref('idle')
/* 进度 ETA（#27）：loading 期间显示已用秒数——移动端网络抖动时「没卡死」的体感来源 */
const elapsed = ref(0)
let tickTimer = null
function startTick() {
  elapsed.value = 0
  stopTick()
  tickTimer = setInterval(() => { elapsed.value += 1 }, 1000)
}
function stopTick() {
  if (tickTimer) { clearInterval(tickTimer); tickTimer = null }
}
let timer = null
function schedule(back) {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => { state.value = 'idle' }, back)
}
async function onClick() {
  if (state.value === 'loading') return
  state.value = 'loading'
  startTick()
  try {
    await props.action()
    state.value = 'success'
    haptic.medium()
    schedule(props.hold)
  } catch (e) {
    state.value = 'error'
    haptic.heavy()
    schedule(Math.max(props.hold, 1200))
    throw e  // 保留给调用方/全局拦截器（与原直接调用行为一致）
  } finally {
    stopTick()
  }
}
onBeforeUnmount(() => { if (timer) clearTimeout(timer); stopTick() })
</script>

<style scoped>
.xz-sbtn { display: grid; place-items: center; }
.xz-sbtn-layer {
  grid-area: 1 / 1;
  display: inline-flex; align-items: center; gap: 7px;
  opacity: 0; pointer-events: none; white-space: nowrap;
  transition: opacity var(--m-dur-out, 180ms) ease;
}
.xz-sbtn-layer.on { opacity: 1; }
.xz-sbtn-eta {
  font-style: normal; font-size: .78em; opacity: .65;
  font-variant-numeric: tabular-nums;
}
.xz-sbtn-dot {
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid currentColor; border-top-color: transparent;
  animation: xz-sbtn-spin .7s linear infinite;
}
@keyframes xz-sbtn-spin { to { transform: rotate(360deg) } }
.xz-sbtn.is-success { filter: none; }
@media (prefers-reduced-motion: reduce) {
  .xz-sbtn-dot { animation-duration: .001ms; }
  .xz-sbtn-layer { transition: none; }
}
</style>

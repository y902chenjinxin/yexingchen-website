<template>
  <div ref="host" class="pk" :class="{ 'pk--compact': compact }">
    <div
      v-for="k in keys"
      :key="k.key"
      class="pk-key"
      :class="[k.black ? 'pk-key--black' : 'pk-key--white', { on: active.has(k.key) }]"
      :style="{ left: k.x + 'px', width: k.w + 'px' }"
      :data-key="k.key"
      @pointerdown.prevent="press(k.key)"
      @pointerup.passive="release(k.key)"
      @pointerleave.passive="release(k.key)"
    >
      <span class="pk-label">{{ k.key }}</span>
      <span v-if="!compact" class="pk-note">{{ k.note }}</span>
    </div>
  </div>
</template>

<script setup>
/**
 * 虚拟钢琴键盘（v2.46.334）
 *
 * 白键 18 + 黑键 10，位置全部来自 utils/pianoKeys.js 的 keyLayout(width)，
 * 演奏页的下落轨道用同一份几何 —— 音符落点与按键中心严格对齐。
 *
 * 键盘本身**不发声音**，只上报按下/松开事件：声音由 usePiano 管，
 * 这样同一个键盘可以同时用在「演奏页」（快速发声）和「大厅预览」（试听）里。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { BLACK_KEYS, WHITE_KEYS, keyLayout, midiName, WHITE_INDEX } from '@/utils/pianoKeys'

defineProps({
  active: { type: Object, default: () => new Set() },
  compact: { type: Boolean, default: false },
})
const emit = defineEmits(['down', 'up'])

const host = ref(null)
const width = ref(0)
let ro = null

const keys = computed(() => {
  const { pos } = keyLayout(width.value || 1)
  const out = []
  for (const [k, m] of [...WHITE_KEYS, ...BLACK_KEYS]) {
    const p = pos.get(k)
    if (!p) continue
    out.push({ key: k, x: p.x, w: p.w, black: p.black, note: midiName(m) })
  }
  // 黑键后渲染（压在白键上面），靠 DOM 顺序而不是 z-index
  return out.sort((a, b) => Number(a.black) - Number(b.black))
})

function measure() {
  const el = host.value
  if (el) width.value = el.clientWidth
}

function press(k) { emit('down', k) }
function release(k) { emit('up', k) }

onMounted(() => {
  measure()
  if (typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(measure)
    ro.observe(host.value)
  }
})
onBeforeUnmount(() => ro?.disconnect())

defineExpose({ layout: () => keyLayout(width.value || 1), whiteIndex: WHITE_INDEX })
</script>

<style scoped>
.pk {
  position: relative;
  width: 100%;
  height: var(--pk-h, 168px);
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
}
.pk--compact { --pk-h: 76px; }

.pk-key {
  position: absolute;
  top: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 3px;
  padding-bottom: 8px;
  cursor: pointer;
  transition: transform .06s ease, box-shadow .12s ease, background-color .12s ease;
}
.pk-key--white {
  height: 100%;
  border-radius: 0 0 7px 7px;
  background: linear-gradient(180deg, #fdfcf9 0%, #f3efe6 78%, #e6dfd1 100%);
  border: 1px solid rgba(24, 22, 18, .16);
  border-top: none;
  box-shadow: inset 0 -6px 10px -8px rgba(0, 0, 0, .45);
  color: #6b6154;
}
.pk-key--black {
  height: 62%;
  z-index: 2;
  border-radius: 0 0 5px 5px;
  background: linear-gradient(180deg, #3a3733 0%, #1d1b19 62%, #0d0c0b 100%);
  border: 1px solid rgba(0, 0, 0, .55);
  border-top: none;
  box-shadow: 0 3px 6px -2px rgba(0, 0, 0, .6);
  color: #cfc7ba;
}
.pk-key--white.on {
  background: linear-gradient(180deg, #fff6da 0%, #ffe6a8 70%, #f6cf78 100%);
  color: #6a4a12;
  transform: translateY(2px);
  box-shadow: inset 0 -3px 8px -4px rgba(0, 0, 0, .35), 0 0 18px -2px rgba(255, 208, 120, .75);
}
.pk-key--black.on {
  background: linear-gradient(180deg, #6a5320 0%, #8a6a24 60%, #a98330 100%);
  color: #fff3d4;
  transform: translateY(2px);
  box-shadow: 0 0 16px -2px rgba(255, 200, 90, .8);
}
.pk-label {
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  opacity: .78;
  font-variant-numeric: tabular-nums;
}
.pk-note {
  font-size: 9px;
  line-height: 1;
  opacity: .45;
}
.pk--compact .pk-label { font-size: 10px; }
</style>

<template>
  <!-- 步进器（APP_design.md #6 · v2.46.33）：
       数量微调 1~max，长按连发；每次变更 light 触觉。手账描边皮肤。 -->
  <div class="xz-step" role="group" :aria-label="label">
    <button
      type="button" class="xz-step-btn" :disabled="modelValue <= min"
      aria-label="减少"
      @pointerdown="holdStart(-1)" @pointerup="holdStop" @pointerleave="holdStop" @pointercancel="holdStop"
      @click="bump(-1)"
    >−</button>
    <span class="xz-step-val" aria-live="polite">{{ modelValue }}</span>
    <button
      type="button" class="xz-step-btn" :disabled="modelValue >= max"
      aria-label="增加"
      @pointerdown="holdStart(1)" @pointerup="holdStop" @pointerleave="holdStop" @pointercancel="holdStop"
      @click="bump(1)"
    >＋</button>
  </div>
</template>

<script setup>
import { onBeforeUnmount } from 'vue'
import { haptic } from '@/utils/haptic'

const props = defineProps({
  modelValue: { type: Number, required: true },
  min: { type: Number, default: 1 },
  max: { type: Number, default: 9 },
  label: { type: String, default: '数量' },
  step: { type: Number, default: 1 },
})
const emit = defineEmits(['update:modelValue'])

let repeatTimer = null
let repeatDelay = null

function bump(dir) {
  const next = Math.min(props.max, Math.max(props.min, props.modelValue + dir * props.step))
  if (next === props.modelValue) return
  emit('update:modelValue', next)
  haptic.light()
}

/* 长按连发：400ms 后以 140ms 间隔重复 bump */
function holdStart(dir) {
  holdStop()
  repeatDelay = setTimeout(() => {
    repeatTimer = setInterval(() => bump(dir), 140)
  }, 400)
}
function holdStop() {
  if (repeatDelay) { clearTimeout(repeatDelay); repeatDelay = null }
  if (repeatTimer) { clearInterval(repeatTimer); repeatTimer = null }
}
onBeforeUnmount(holdStop)
</script>

<style scoped>
.xz-step {
  display: inline-flex; align-items: center; gap: 10px;
  border: 1.5px solid var(--m-line-strong);
  border-radius: 12px;
  padding: 4px 6px;
  background: var(--xz-card-2, transparent);
}
.xz-step-btn {
  width: 30px; height: 30px;
  border: none; border-radius: 9px;
  background: transparent; color: var(--m-text);
  font-size: 16px; line-height: 1;
  cursor: pointer;
}
.xz-step-btn:disabled { opacity: .35; cursor: default; }
.xz-step-btn:not(:disabled):active { background: rgba(0, 0, 0, .06); }
.xz-step-val {
  min-width: 20px; text-align: center;
  font-size: 15px; font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--m-text);
}
</style>

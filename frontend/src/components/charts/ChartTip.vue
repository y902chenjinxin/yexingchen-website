<template>
  <div v-if="show" class="ctip" :style="style" role="status" aria-live="off">
    <div v-if="title" class="ctip-title">{{ title }}</div>
    <div v-for="r in rows" :key="r.label" class="ctip-row">
      <i v-if="r.color" class="ctip-dot" :style="{ background: r.color }"></i>
      <span class="ctip-label">{{ r.label }}</span>
      <b class="ctip-val" :style="r.color ? { color: r.color } : null">{{ r.value }}</b>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  x: { type: Number, default: 0 },   // 当前列在 viewBox 内的 x
  vw: { type: Number, required: true }, // viewBox 宽度
  title: { type: String, default: '' },
  rows: { type: Array, default: () => [] }, // [{ label, value, color }]
})

const style = computed(() => {
  const pct = props.vw ? Math.min(100, Math.max(0, (props.x / props.vw) * 100)) : 0
  const flip = pct > 68
  return { left: `${pct}%`, transform: `translateX(${flip ? -110 : 10}%)` }
})
</script>

<style scoped>
.ctip {
  position: absolute;
  top: 6px;
  min-width: 92px;
  padding: 7px 10px;
  border-radius: 10px;
  font-family: var(--font-serif);
  font-size: 12px;
  color: var(--lj-text, var(--dp-text));
  background: var(--lj-glass, var(--color-bg-glass));
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line, var(--dp-line));
  box-shadow: 0 8px 22px rgba(0, 0, 0, .22);
  pointer-events: none;
  line-height: 1.5;
  z-index: 3;
}
.ctip-title {
  font-size: 11px;
  color: var(--lj-text-2, var(--dp-text3));
  letter-spacing: .05em;
  margin-bottom: 2px;
}
.ctip-row { display: flex; align-items: center; gap: 6px; }
.ctip-label { color: var(--lj-text-2, var(--dp-text3)); }
.ctip-val { margin-left: auto; font-variant-numeric: tabular-nums; font-weight: 600; }
.ctip-dot { width: 7px; height: 7px; border-radius: 50%; flex: none; }
</style>
<!--
  StepIndicator.vue
  玄黄 · 步骤指示器
  - 用于工具页（Watermark / Pdf / Compress / Idphoto / Cover / Voice）的步骤引导
  - 当前步骤高亮（鎏金），已完成步骤打勾，未到达步骤灰色
  - 主题感知：昼夜双套配色
-->
<template>
  <ol class="stp" :class="{ 'stp-compact': compact }">
    <li
      v-for="(s, i) in steps"
      :key="s.key"
      class="stp-item"
      :class="{
        'stp-done': i < currentIndex,
        'stp-current': i === currentIndex,
        'stp-future': i > currentIndex,
      }"
    >
      <span class="stp-circle" aria-hidden="true">
        <svg v-if="i < currentIndex" class="stp-check" viewBox="0 0 16 16">
          <path d="M3 8 L7 12 L13 4" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span v-else>{{ i + 1 }}</span>
      </span>
      <span class="stp-label">{{ s.label }}</span>
      <span v-if="i < steps.length - 1" class="stp-line" aria-hidden="true"></span>
    </li>
  </ol>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  steps: { type: Array, required: true }, // [{ key, label }]
  current: { type: [String, Number], required: true }, // 当前 step 的 key 或 0-based index
  compact: { type: Boolean, default: false },
})

const currentIndex = computed(() => {
  if (typeof props.current === 'number') return props.current
  const idx = props.steps.findIndex((s) => s.key === props.current)
  return idx >= 0 ? idx : 0
})
</script>

<style scoped>
.stp {
  display: flex;
  align-items: center;
  list-style: none;
  margin: 0; padding: 0;
  gap: 4px;
}

.stp-item {
  flex: 1;
  display: flex; align-items: center;
  min-width: 0;
}

/* 圆圈 */
.stp-circle {
  flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  font-size: 13px; font-weight: 600;
  border: 1.5px solid var(--dp-line, rgba(127, 127, 127, 0.32));
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.04));
  color: var(--lj-text-3);
  transition: all .25s ease;
  font-variant-numeric: tabular-nums;
}
.stp-check { width: 14px; height: 14px; }

.stp-label {
  font-size: 12.5px; color: var(--lj-text-3);
  letter-spacing: .04em;
  margin: 0 10px;
  white-space: nowrap;
  transition: color .25s ease;
}

/* 连接线 */
.stp-line {
  flex: 1;
  height: 1.5px;
  background: var(--dp-line, rgba(127, 127, 127, 0.25));
  transition: background .3s ease;
  border-radius: 2px;
}

/* 完成态 */
.stp-done .stp-circle {
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  border-color: transparent;
  box-shadow: 0 2px 8px var(--yq-gold-glow, rgba(199, 169, 107, 0.3));
}
.stp-done .stp-label { color: var(--lj-text-2); }
.stp-done .stp-line {
  background: linear-gradient(90deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  opacity: 0.65;
}

/* 当前态：鎏金 + 脉冲 */
.stp-current .stp-circle {
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.06));
  border-color: var(--yq-gold, #c7a96b);
  color: var(--yq-gold, #c7a96b);
  box-shadow:
    0 0 0 3px var(--yq-gold-faint, rgba(199, 169, 107, 0.18)),
    0 0 18px var(--yq-gold-glow, rgba(199, 169, 107, 0.35));
  position: relative;
}
.stp-current .stp-circle::after {
  content: "";
  position: absolute; inset: -3px;
  border-radius: 50%;
  border: 1.5px solid var(--yq-gold-glow, rgba(199, 169, 107, 0.5));
  animation: stp-pulse 1.8s ease-out infinite;
}
@keyframes stp-pulse {
  0%   { transform: scale(1); opacity: 0.9; }
  100% { transform: scale(1.6); opacity: 0; }
}
.stp-current .stp-label { color: var(--yq-gold, #c7a96b); font-weight: 600; }

/* 紧凑型 */
.stp-compact .stp-circle { width: 22px; height: 22px; font-size: 11px; }
.stp-compact .stp-label { font-size: 11.5px; margin: 0 8px; }

@media (prefers-reduced-motion: reduce) {
  .stp-current .stp-circle::after { animation: none; }
}
</style>
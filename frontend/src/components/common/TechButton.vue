<template>
  <button
    class="tech-btn"
    :class="[`tech-btn--${variant}`, { 'is-block': block, 'is-disabled': disabled || loading }]"
    :disabled="disabled || loading"
    :type="nativeType"
    @click="$emit('click', $event)"
  >
    <span class="tech-btn__sweep" aria-hidden="true"></span>
    <span v-if="loading" class="tech-btn__spinner" aria-hidden="true"></span>
    <span class="tech-btn__label"><slot /></span>
  </button>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'primary' }, // primary | ghost | danger
  block: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  nativeType: { type: String, default: 'button' },
})
defineEmits(['click'])
</script>

<style scoped>
.tech-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 22px;
  font-family: var(--font-sans);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: .04em;
  border-radius: 12px;
  cursor: pointer;
  overflow: hidden;
  isolation: isolate;
  transition: transform .12s ease, box-shadow .25s ease, filter .2s ease;
  user-select: none;
}
.tech-btn.is-block { display: flex; width: 100%; }

/* 主：青→紫渐变填充 + 霓虹描边 */
.tech-btn--primary {
  color: #04121f;
  background:
    linear-gradient(135deg, var(--tc-cyan), var(--tc-blue)) padding-box,
    linear-gradient(135deg, var(--tc-cyan-bright), var(--tc-violet)) border-box;
  border: 1px solid transparent;
  box-shadow: 0 0 0 1px rgba(45, 226, 255, .4), 0 8px 24px rgba(45, 226, 255, .35);
}
.tech-btn--primary:hover {
  filter: brightness(1.08);
  box-shadow: 0 0 0 1px rgba(45, 226, 255, .6), 0 10px 30px rgba(45, 226, 255, .55);
}

/* 幽灵：透明玻璃 + 霓虹描边 */
.tech-btn--ghost {
  color: #cfe6ff;
  background: rgba(15, 23, 38, .55);
  border: 1px solid var(--tc-line-strong);
  backdrop-filter: blur(8px);
  box-shadow: inset 0 0 0 1px rgba(120, 180, 255, .05);
}
.tech-btn--ghost:hover {
  color: #fff;
  border-color: var(--tc-cyan);
  box-shadow: 0 0 18px rgba(45, 226, 255, .3), inset 0 0 0 1px rgba(45, 226, 255, .25);
}

/* 危险：朱红霓虹（v2.46.148 从品红拆出，与全站 --tc-danger 同源） */
.tech-btn--danger {
  color: #1a0605;
  background:
    linear-gradient(135deg, #ff7a5c, #ff3d2e) padding-box,
    linear-gradient(135deg, #ffa48f, #ff5347) border-box;
  border: 1px solid transparent;
  box-shadow: 0 0 0 1px rgba(255, 83, 71, .4), 0 8px 24px rgba(255, 83, 71, .35);
}
.tech-btn--danger:hover { filter: brightness(1.08); }

.tech-btn:active { transform: translateY(1px) scale(.985); }
.tech-btn.is-disabled { opacity: .5; cursor: not-allowed; filter: grayscale(.3); }

/* 扫光 */
.tech-btn__sweep {
  position: absolute;
  top: 0;
  left: 0;
  width: 40%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .55), transparent);
  transform: translateX(-120%) skewX(-20deg);
  opacity: 0;
  pointer-events: none;
  z-index: -1;
}
.tech-btn:hover .tech-btn__sweep {
  opacity: 1;
  animation: tech-sweep .7s ease forwards;
}
.tech-btn__label { position: relative; z-index: 1; }
.tech-btn__spinner {
  position: relative;
  z-index: 1;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(4, 18, 31, .35);
  border-top-color: #04121f;
  border-radius: 50%;
  animation: tech-spin .7s linear infinite;
}
.tech-btn--ghost .tech-btn__spinner { border-color: rgba(255, 255, 255, .35); border-top-color: #fff; }
.tech-btn--danger .tech-btn__spinner { border-color: rgba(26, 6, 5, .35); border-top-color: #1a0605; }
@keyframes tech-spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .tech-btn { transition: none; }
  .tech-btn:hover .tech-btn__sweep { animation: none; opacity: 0; }
}
</style>

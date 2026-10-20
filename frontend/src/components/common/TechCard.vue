<template>
  <component :is="tag" class="tech-card" :class="{ 'tech-card--hover': hover, 'tech-card--glow': glow }">
    <!-- 四角霓虹角标 -->
    <span class="tech-card__corner tech-card__corner--tl" aria-hidden="true"></span>
    <span class="tech-card__corner tech-card__corner--tr" aria-hidden="true"></span>
    <span class="tech-card__corner tech-card__corner--bl" aria-hidden="true"></span>
    <span class="tech-card__corner tech-card__corner--br" aria-hidden="true"></span>
    <div class="tech-card__body"><slot /></div>
  </component>
</template>

<script setup>
defineProps({
  tag: { type: String, default: 'div' },
  hover: { type: Boolean, default: true },
  glow: { type: Boolean, default: false },
})
</script>

<style scoped>
.tech-card {
  position: relative;
  background: linear-gradient(160deg, rgba(20, 30, 48, .72), rgba(10, 16, 28, .86));
  border: 1px solid var(--tc-line);
  border-radius: var(--radius-lg);
  -webkit-backdrop-filter: var(--glass-blur);
  backdrop-filter: var(--glass-blur);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
  transition: border-color .25s, box-shadow .25s, transform .25s;
}
/* 渐变描边 */
.tech-card::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(135deg, rgba(45, 226, 255, .6), rgba(185, 139, 255, .5), rgba(45, 226, 255, .12));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  opacity: .85;
  transition: opacity .25s;
}
.tech-card__body { position: relative; z-index: 1; }

/* 四角霓虹 */
.tech-card__corner {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 2px solid var(--tc-cyan);
  opacity: .8;
  z-index: 2;
  pointer-events: none;
}
.tech-card__corner--tl { top: 8px; left: 8px; border-right: 0; border-bottom: 0; border-top-left-radius: 6px; }
.tech-card__corner--tr { top: 8px; right: 8px; border-left: 0; border-bottom: 0; border-top-right-radius: 6px; }
.tech-card__corner--bl { bottom: 8px; left: 8px; border-right: 0; border-top: 0; border-bottom-left-radius: 6px; }
.tech-card__corner--br { bottom: 8px; right: 8px; border-left: 0; border-top: 0; border-bottom-right-radius: 6px; }

.tech-card--hover:hover {
  transform: translateY(-4px);
  border-color: var(--tc-line-strong);
  box-shadow: var(--glass-shadow), 0 0 32px rgba(45, 226, 255, .18);
}
.tech-card--hover:hover::before { opacity: 1; }
.tech-card--glow { animation: tech-glow-pulse 3.2s ease-in-out infinite; }

@media (prefers-reduced-motion: reduce) {
  .tech-card, .tech-card--hover:hover { transition: none; }
  .tech-card--glow { animation: none; }
}
</style>

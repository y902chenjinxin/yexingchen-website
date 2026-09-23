<!--
  EmptyState.vue
  玄黄 · 通用空态组件（v194 升级）
  - 6 种主题插画（data / search / net / deny / time / generic）
  - 鎏金图标 + 玄灰文字 + 主按钮 + 跟随光斑
  - 主题感知：昼夜两套配色
-->
<template>
  <div class="ls-empty" :class="['ls-empty--' + size, 'ls-empty--' + (tone || 'data')]" role="status" :aria-label="title">
    <!-- 插画（鎏金 SVGs） -->
    <div class="ls-empty-art" aria-hidden="true">
      <component :is="iconComponent" />
      <div class="ls-empty-glow" />
    </div>
    <p class="ls-empty-title">{{ title }}</p>
    <p v-if="description" class="ls-empty-desc">{{ description }}</p>
    <div v-if="actionLabel" class="ls-empty-actions">
      <button type="button" class="ls-empty-btn ls-empty-btn--primary" @click="onAction">
        <slot name="icon"></slot>
        <span>{{ actionLabel }}</span>
      </button>
      <slot name="extra"></slot>
    </div>
    <slot />
  </div>
</template>

<script setup>
import { computed, h } from 'vue'

const props = defineProps({
  title: { type: String, default: '这里还什么都没有' },
  description: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
  size: { type: String, default: 'md' }, // sm / md / lg
  tone: { type: String, default: 'data' }, // data / search / net / deny / time / generic
})
const emit = defineEmits(['action'])
function onAction() { emit('action') }

/* 6 种鎏金插画 */
const patterns = {
  // 数据空：空盒子 + 虚线 + 箭头
  data: [
    h('rect', { x: 60, y: 50, width: 80, height: 56, rx: 10, fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 2.5, 'stroke-dasharray': '5 4' }),
    h('path', { d: 'M 75 70 L 100 95 L 125 70', fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: 0.85 }),
    h('circle', { cx: 100, cy: 58, r: 4.5, fill: 'var(--yq-gold, #c7a96b)' }),
  ],
  // 搜索空：放大镜
  search: [
    h('circle', { cx: 88, cy: 64, r: 22, fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 3 }),
    h('line', { x1: 105, y1: 81, x2: 128, y2: 104, stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 3.5, 'stroke-linecap': 'round' }),
    h('circle', { cx: 88, cy: 64, r: 10, fill: 'var(--yq-gold, #c7a96b)', opacity: 0.25 }),
  ],
  // 网络空：云 + 断线
  net: [
    h('path', { d: 'M 50 80 Q 50 50 80 50 Q 90 35 110 45 Q 140 40 150 70 Q 160 95 130 100 L 70 100 Q 45 95 50 80 Z', fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 2.5, 'stroke-linejoin': 'round' }),
    h('line', { x1: 70, y1: 75, x2: 130, y2: 75, stroke: 'var(--dp-danger, #fb7185)', 'stroke-width': 3, 'stroke-linecap': 'round' }),
  ],
  // 权限空：锁
  deny: [
    h('rect', { x: 75, y: 75, width: 50, height: 40, rx: 6, fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 3 }),
    h('path', { d: 'M 84 75 L 84 60 Q 84 48 100 48 Q 116 48 116 60 L 116 75', fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 3, 'stroke-linecap': 'round' }),
    h('circle', { cx: 100, cy: 95, r: 3.5, fill: 'var(--yq-gold, #c7a96b)' }),
  ],
  // 时间空：沙漏
  time: [
    h('rect', { x: 78, y: 40, width: 44, height: 60, rx: 4, fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 2.5 }),
    h('path', { d: 'M 80 45 L 120 45 L 100 70 Z M 80 95 L 120 95 L 100 70 Z', fill: 'none', stroke: 'var(--yq-gold, #c7a96b)', 'stroke-width': 2.5, 'stroke-linejoin': 'round' }),
    h('circle', { cx: 92, cy: 92, r: 2, fill: 'var(--yq-gold, #c7a96b)' }),
    h('circle', { cx: 106, cy: 95, r: 2, fill: 'var(--yq-gold, #c7a96b)' }),
    h('circle', { cx: 100, cy: 88, r: 2, fill: 'var(--yq-gold, #c7a96b)' }),
  ],
  // 通用：圆点
  generic: [
    h('circle', { cx: 70, cy: 70, r: 6, fill: 'var(--yq-gold, #c7a96b)', opacity: 0.6 }),
    h('circle', { cx: 100, cy: 70, r: 6, fill: 'var(--yq-gold, #c7a96b)', opacity: 0.85 }),
    h('circle', { cx: 130, cy: 70, r: 6, fill: 'var(--yq-gold, #c7a96b)', opacity: 0.6 }),
  ],
}

const iconComponent = computed(() => () => {
  const t = props.tone || 'data'
  return h('svg', { viewBox: '0 0 200 140', xmlns: 'http://www.w3.org/2000/svg' }, [
    // 底圆（鎏金晕染）
    h('circle', { cx: 100, cy: 70, r: 56, fill: 'url(#ls-empty-bg)', opacity: 0.45 }),
    // 主题图案
    ...(patterns[t] || patterns.generic),
    // 渐变定义
    h('defs', {}, [
      h('radialGradient', { id: 'ls-empty-bg', cx: '50%', cy: '50%', r: '50%' }, [
        h('stop', { offset: '0%', 'stop-color': 'var(--yq-gold, #c7a96b)', 'stop-opacity': 0.32 }),
        h('stop', { offset: '100%', 'stop-color': 'var(--yq-gold, #c7a96b)', 'stop-opacity': 0 }),
      ]),
    ]),
  ])
})
</script>

<style scoped>
.ls-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 28px 20px;
  gap: 6px;
  color: var(--lj-text-2);
  /* 主题感知玻璃底 */
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.04));
  border-radius: 18px;
  border: 1px dashed var(--dp-line, rgba(127, 127, 127, 0.2));
  /* 鎏金微动效 */
  transition: border-color .2s, box-shadow .2s;
}
.ls-empty:hover {
  border-color: var(--yq-gold-glow, rgba(199, 169, 107, 0.35));
  box-shadow: 0 12px 28px rgba(0, 0, 0, .15);
}

.ls-empty-art {
  position: relative;
  width: 140px;
  height: 110px;
  margin-bottom: 6px;
  display: flex; align-items: center; justify-content: center;
}
.ls-empty-art svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 6px 16px var(--yq-gold-glow, rgba(199, 169, 107, 0.3)));
  animation: ls-empty-float 5s ease-in-out infinite;
}
.ls-empty-glow {
  position: absolute;
  inset: 10%;
  background: radial-gradient(closest-side, var(--yq-gold-glow, rgba(199, 169, 107, 0.28)), transparent 70%);
  filter: blur(14px);
  z-index: -1;
  animation: ls-empty-pulse 4s ease-in-out infinite;
}

@keyframes ls-empty-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
@keyframes ls-empty-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.9; }
}

.ls-empty-title { font-size: 15px; font-weight: 600; color: var(--lj-text); margin: 0; letter-spacing: .04em; }
.ls-empty-desc { font-size: 12.5px; color: var(--lj-text-2); margin: 0; max-width: 380px; line-height: 1.6; }
.ls-empty-actions { margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }

.ls-empty-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
  letter-spacing: .04em;
  transition: all .18s ease;
  font-family: inherit;
}
.ls-empty-btn--primary {
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  font-weight: 600;
  box-shadow: 0 4px 14px var(--yq-gold-glow, rgba(199, 169, 107, 0.28));
}
.ls-empty-btn--primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px var(--yq-gold-glow-strong, rgba(199, 169, 107, 0.42));
}

/* 尺寸 */
.ls-empty--sm { padding: 18px 14px; }
.ls-empty--sm .ls-empty-art { width: 88px; height: 70px; }
.ls-empty--sm .ls-empty-title { font-size: 13px; }
.ls-empty--sm .ls-empty-desc { font-size: 11.5px; }

.ls-empty--md .ls-empty-art { width: 140px; height: 110px; }

.ls-empty--lg { padding: 36px 28px; }
.ls-empty--lg .ls-empty-art { width: 180px; height: 140px; }
.ls-empty--lg .ls-empty-title { font-size: 17px; }
.ls-empty--lg .ls-empty-desc { font-size: 13.5px; }

@media (prefers-reduced-motion: reduce) {
  .ls-empty-art svg,
  .ls-empty-glow { animation: none; }
}
</style>
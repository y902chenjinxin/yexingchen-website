<!--
  EmptyState.vue
  玄黄・通用空状态（#5）
  - 统一「暂无数据」的视觉：柔和插画（内联 SVG）+ 主文案 + 副文案 + 可选 CTA
  - 替代各页面零散的「暂无」文字，形成体验闭环
  - 尺寸可调，深色/浅色自动适配
-->
<template>
  <div class="ls-empty" :class="'ls-empty--' + size">
    <div class="ls-empty-art" aria-hidden="true">
      <!-- 柔和插画：山 + 月 + 飘叶，贴合水墨/玻璃风 -->
      <svg viewBox="0 0 200 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="lsEmptyGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--dp-accent)" stop-opacity=".5" />
            <stop offset="100%" stop-color="var(--dp-accent)" stop-opacity="0" />
          </linearGradient>
        </defs>
        <!-- 山 -->
        <path d="M20 100 L70 55 L95 82 L120 62 L150 92 L175 78 L190 100 Z"
              fill="url(#lsEmptyGrad)" stroke="var(--dp-line-strong)" stroke-width="1.5" stroke-linejoin="round" />
        <!-- 月 -->
        <circle cx="150" cy="38" r="14" fill="none" stroke="var(--dp-warning)" stroke-width="1.5" opacity=".9" />
        <circle cx="150" cy="38" r="14" fill="var(--dp-warning)" opacity=".18" />
        <!-- 飘叶 -->
        <path d="M60 30 q8 -10 18 -4 q6 8 -6 14 Z" fill="var(--dp-accent)" opacity=".4" transform="rotate(-15 66 33)" />
        <path d="M95 50 q6 -8 14 -3 q4 6 -5 11 Z" fill="var(--dp-danger)" opacity=".35" transform="rotate(12 100 52)" />
        <!-- 下方弥散光 -->
        <ellipse cx="100" cy="108" rx="70" ry="6" fill="var(--dp-accent)" opacity=".12" />
      </svg>
    </div>
    <p class="ls-empty-title">{{ title }}</p>
    <p v-if="description" class="ls-empty-desc">{{ description }}</p>
    <div v-if="actionLabel" class="ls-empty-actions">
      <button type="button" class="ls-empty-btn" @click="onAction">
        <slot name="icon"></slot>
        <span>{{ actionLabel }}</span>
      </button>
      <slot name="extra"></slot>
    </div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '这里还什么都没有' },
  description: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
  size: { type: String, default: 'md' }, // sm / md / lg
})
const emit = defineEmits(['action'])
function onAction() { emit('action') }
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
  color: var(--dp-text2);
}
.ls-empty-art { width: 120px; height: 90px; margin-bottom: 6px; }
.ls-empty-art svg { width: 100%; height: 100%; }
.ls-empty-title { font-size: 15px; font-weight: 600; color: var(--dp-text); margin: 0; }
.ls-empty-desc { font-size: 12.5px; color: var(--dp-text3); margin: 0; max-width: 320px; line-height: 1.6; }
.ls-empty-actions { margin-top: 10px; }
.ls-empty-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: var(--dp-radius-sm, 8px);
  border: 1px solid var(--dp-line-strong);
  background: var(--dp-accent-faint, rgba(167, 139, 250, .18));
  color: var(--dp-text);
  font-size: 13px;
  cursor: pointer;
  transition: background .18s ease, border-color .18s ease;
}
.ls-empty-btn:hover { background: var(--dp-accent-faint, rgba(167, 139, 250, .28)); border-color: var(--dp-accent); }

/* 尺寸 */
.ls-empty--sm { padding: 18px 14px; }
.ls-empty--sm .ls-empty-art { width: 80px; height: 60px; }
.ls-empty--sm .ls-empty-title { font-size: 13px; }
.ls-empty--sm .ls-empty-desc { font-size: 11.5px; }
.ls-empty--lg .ls-empty-art { width: 160px; height: 120px; }
.ls-empty--lg .ls-empty-title { font-size: 17px; }
.ls-empty--lg .ls-empty-desc { font-size: 13.5px; }
</style>
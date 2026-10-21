<template>
  <button
    class="ibtn"
    :class="[`ibtn--${variant}`, `ibtn--${size}`, { 'is-icon-only': iconOnly, 'is-round': round }]"
    :type="nativeType"
    :disabled="disabled"
    :title="label"
    :aria-label="label"
    @click="$emit('click', $event)"
  >
    <svg
      v-if="body"
      class="ibtn__ico"
      :width="icoSize"
      :height="icoSize"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
      v-html="body"
    ></svg>
    <span class="ibtn__label">{{ label }}</span>
  </button>
</template>

<script setup>
/**
 * 统一「图标按钮」（v2.46.135）
 *
 * 设计目标（夜星：手机端很多按钮是文字样式，需要改成图标样式）：
 *   · **一套代码两种形态** —— 桌面上「图标 + 文字」，手机（#app.is-mobile）上只留图标；
 *     文字用 .ibtn__label 包着，移动端 CSS 隐藏，不会在 DOM 里丢标签、aria 不残。
 *   · **尺寸即触控** —— sm=32 / md=40，都 ≥32，配合 padding 达到 40+ 的点击区。
 *   · **颜色继承** —— 图标 stroke 走 currentColor，主题换肤自动跟随，不需要单独配色。
 *   · **可访问性** —— title + aria-label 都取 label，图标 only 时读屏仍知道是什么动作。
 *
 * 用法：
 *   <IconButton icon="plus" label="新增" variant="primary" @click="openCreate" />
 *   <IconButton icon="trash" label="删除" variant="danger" size="sm" @click="remove(c)" />
 */
import { computed } from 'vue'
import { uiIconBody } from '@/utils/icons/uiIcons'

const props = defineProps({
  /** 语义图标名，见 utils/icons/uiIcons.js（plus / edit / trash / refresh ...） */
  icon: { type: String, required: true },
  /** 中文动作名：桌面显示为文字，移动端作为 title / aria-label */
  label: { type: String, required: true },
  /** default | primary | ghost | danger */
  variant: { type: String, default: 'ghost' },
  /** sm | md */
  size: { type: String, default: 'md' },
  /** 强制只显示图标（桌面也隐藏文字，用于行内密集操作） */
  iconOnly: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  nativeType: { type: String, default: 'button' },
})

defineEmits(['click'])

const body = computed(() => uiIconBody(props.icon))
const icoSize = computed(() => (props.size === 'sm' ? 15 : 17))
</script>

<style scoped>
.ibtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid var(--tc-line-strong, rgba(120, 180, 255, .3));
  background: transparent;
  color: var(--tc-text-2, #a6bcd6);
  border-radius: 10px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  white-space: nowrap;
  transition: color .16s, border-color .16s, background-color .16s, transform .1s;
  -webkit-tap-highlight-color: transparent;
}
.ibtn--md { height: 36px; padding: 0 12px; }
.ibtn--sm { height: 30px; padding: 0 9px; font-size: 12px; border-radius: 8px; }
.ibtn.is-round { border-radius: 999px; }

.ibtn:hover {
  color: var(--tc-cyan, #2de2ff);
  border-color: var(--tc-cyan, #2de2ff);
  background: rgba(45, 226, 255, .08);
}
.ibtn:active { transform: translateY(1px); }
.ibtn:disabled { opacity: .45; cursor: not-allowed; }

.ibtn__ico { flex: none; display: block; }

/* 主操作：实色渐变（与全站主按钮同一套令牌） */
.ibtn--primary {
  border-color: transparent;
  background: var(--tc-btn-grad, linear-gradient(135deg, #8b5cff, #2de2ff));
  color: var(--tc-btn-fg, #04121c);
}
.ibtn--primary:hover {
  background: var(--tc-btn-grad-hover, linear-gradient(135deg, #a279ff, #5ae9ff));
  color: var(--tc-btn-fg, #04121c);
  border-color: transparent;
}
/* 危险：只在 hover/长按才红，平时保持中性，避免列表里一片红
 * v2.46.148：边框不再写死品红 rgba，跟随 --color-danger（朱红）；hover 底色偏亮，
 * 文字改深墨（白字在 #ff5347 上对比度只有 ~2.6:1） */
.ibtn--danger { color: var(--color-danger, #ff5347); border-color: rgba(255, 83, 71, .38); }
.ibtn--danger:hover { color: #1a0605; background: var(--color-danger, #ff5347); border-color: var(--color-danger, #ff5347); }

/* —— 手机端：只留图标 ——
 * 🔴 必须把**整条选择器**包进 :global()，不能写成 `:global(#app.is-mobile) .ibtn {}`。
 * Vue 的 scoped 编译遇到「:global() 在前 + 后代」时会把后代丢掉，产出裸的
 * `#app.is-mobile { display:none; width:38px }` —— 后果是**手机端整个 App 被隐藏**
 * （v2.46.135 引入，表现为整页空白，CDP 查匹配规则才定位到）。 */
:global(#app.is-mobile .ibtn__label) { display: none; }
:global(#app.is-mobile .ibtn) { width: 38px; height: 38px; padding: 0; border-radius: 12px; }
:global(#app.is-mobile .ibtn--sm) { width: 32px; height: 32px; border-radius: 10px; }
/* 桌面强制图标模式 */
.ibtn.is-icon-only { width: 36px; padding: 0; }
.ibtn.is-icon-only .ibtn__label { display: none; }
</style>

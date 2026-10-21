<template>
  <!--
    统一搜索框（v2.46.157）

    为什么要有它：全站 15 处「搜索输入 + 查询按钮」各写一遍
    （`<input class="xx-input" @keyup.enter>` + 一个 `<IconButton icon="search">`），
    宽度、高度、按钮文案、清空行为全不统一；还有几处一度只有回车、没有按钮。
    以后搜索框的样式/行为只改这个文件。

    用法：
      <SearchField v-model="filters.q" placeholder="搜物品 / 地点 / 经过" width="220px" @search="reload" />
    行为：Enter 与点按钮走同一个 @search；clearable 时右侧出现清除（清空即触发 search）。
  -->
  <div class="sf" :style="{ width }">
    <input
      v-model="inner"
      class="sf__input"
      type="search"
      :placeholder="placeholder"
      :disabled="disabled"
      spellcheck="false"
      autocomplete="off"
      @keyup.enter="emitSearch"
    />
    <button
      v-if="clearable && inner"
      class="sf__clear"
      type="button"
      title="清空"
      aria-label="清空"
      @click="clear"
    >
      ×
    </button>
    <button
      class="sf__go"
      type="button"
      title="查询"
      aria-label="查询"
      :disabled="disabled"
      @click="emitSearch"
    >
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="6.5" />
        <line x1="15.4" y1="15.4" x2="20" y2="20" />
      </svg>
      <span v-if="showLabel" class="sf__label">查询</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '搜索' },
  /** 整体宽度；传 '100%' 自适应父容器 */
  width: { type: String, default: '220px' },
  /** 有内容时显示清除按钮，清空会立即触发一次 search */
  clearable: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  /** 按钮上是否显示「查询」两个字（窄位置可关掉只留图标） */
  showLabel: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'search'])

const inner = computed({
  get: () => props.modelValue ?? '',
  set: (v) => emit('update:modelValue', v ?? ''),
})

function emitSearch() {
  if (props.disabled) return
  emit('search', inner.value)
}

function clear() {
  emit('update:modelValue', '')
  emit('search', '')
}
</script>

<style scoped>
.sf {
  display: inline-flex;
  align-items: stretch;
  height: 32px;
  border-radius: 9px;
  overflow: hidden;
  background: var(--tc-bg-2, rgba(255, 255, 255, .04));
  box-shadow: inset 0 0 0 1px var(--tc-line, rgba(15, 60, 110, .18));
  transition: box-shadow .18s;
}
.sf:focus-within {
  box-shadow: inset 0 0 0 1px var(--tc-cyan, #2de2ff);
}
.sf__input {
  flex: 1 1 auto;
  min-width: 0;
  padding: 0 10px;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--tc-text, inherit);
  font: inherit;
  font-size: 13px;
}
.sf__input::placeholder { color: var(--tc-text-3, #7c8ea6); }
/* type=search 的原生叉号与自绘的重复，去掉 */
.sf__input::-webkit-search-cancel-button { display: none; }

.sf__clear {
  flex: none;
  width: 24px;
  border: 0;
  background: transparent;
  color: var(--tc-text-3, #7c8ea6);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.sf__clear:hover { color: var(--tc-text-2, #46586e); }

.sf__go {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 11px;
  border: 0;
  border-left: 1px solid var(--tc-line, rgba(15, 60, 110, .16));
  background: rgba(45, 226, 255, .08);
  color: var(--tc-cyan-deep, #0a708c);
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background .18s;
}
.sf__go:hover { background: rgba(45, 226, 255, .16); }
.sf__go:disabled { opacity: .5; cursor: default; }
.sf__label { white-space: nowrap; }

/* 窄容器（手机）：只留图标，省宽度 */
@media (max-width: 560px) {
  .sf__label { display: none; }
  .sf__go { padding: 0 9px; }
}
</style>

<template>
  <!--
    统一下拉（v2.46.148）

    为什么要有它：
      1) 全站还有一批**原生 `<select>`**（筛选/参数），弹层由浏览器渲染，主题管不到，
         不同页面宽度、字体、边框还各写一套 class；
      2) 夜星要「统一换下拉组件，抽象成一个方法，后续改动方便」—— 以后调样式只改这一个文件。
    用法两种，随便挑：
      · 传数组：<FilterSelect v-model="x" :options="[{value:'',label:'全部'}, ...]" />
      · 传插槽：<FilterSelect v-model="x"><el-option v-for="c in list" :key="c" :value="c" :label="c" /></FilterSelect>
    事件：@change 直接把选中的值抛出来（省得写 e.target.value）。
  -->
  <el-select
    class="fs"
    :model-value="modelValue"
    :placeholder="placeholder"
    :clearable="clearable"
    :disabled="disabled"
    :size="size === 'sm' ? 'small' : 'default'"
    :teleported="teleported"
    :style="{ width }"
    @update:model-value="onUpdate"
    @change="onChange"
  >
    <template v-if="options && options.length">
      <el-option
        v-for="o in normalized"
        :key="String(o.value)"
        :value="o.value"
        :label="o.label"
      />
    </template>
    <slot v-else />
  </el-select>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean, Array], default: '' },
  /** [{value,label}] 或 ['a','b']（字符串数组会自动当 label=value） */
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择' },
  clearable: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  /** 'sm' 用于表格行内 / 紧凑工具栏 */
  size: { type: String, default: 'default' },
  width: { type: String, default: '150px' },
  /** 表格里用 false 可避免滚动时弹层错位 */
  teleported: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'change'])

const normalized = computed(() =>
  (props.options || []).map((o) =>
    typeof o === 'object' && o !== null ? { value: o.value, label: o.label ?? String(o.value) } : { value: o, label: String(o) }
  )
)

function onUpdate(v) {
  emit('update:modelValue', v ?? '')
}
function onChange(v) {
  emit('change', v ?? '')
}
</script>

<style scoped>
/* 统一外观：高度、圆角、边框、聚焦色都对齐项目 token。
   各页面不要再写 :deep(.el-select__wrapper) 覆盖，需要特殊宽度用 width prop。 */
.fs :deep(.el-select__wrapper) {
  min-height: 32px;
  border-radius: 9px;
  font-size: 13px;
  box-shadow: inset 0 0 0 1px var(--tc-line, rgba(15, 60, 110, .18));
  background: var(--tc-bg-2, rgba(255, 255, 255, .04));
}
.fs :deep(.el-select__wrapper.is-hovering:not(.is-focused)) {
  box-shadow: inset 0 0 0 1px var(--tc-line-strong, rgba(15, 60, 110, .3));
}
.fs :deep(.el-select__wrapper.is-focused) {
  box-shadow: inset 0 0 0 1px var(--tc-cyan, #2de2ff) !important;
}
.fs :deep(.el-select__placeholder),
.fs :deep(.el-select__selected-item) {
  color: var(--tc-text, inherit);
  font-size: 13px;
}
.fs :deep(.el-select__placeholder.is-transparent) {
  color: var(--tc-text-3, rgba(127, 140, 160, .9));
}
/* 手机端：高度略加，避免误触 */
:global(#app.is-mobile .fs .el-select__wrapper) {
  min-height: 36px;
}
</style>

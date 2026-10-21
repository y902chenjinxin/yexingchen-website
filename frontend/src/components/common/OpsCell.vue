<template>
  <!--
    表格行内操作区（v2.46.157）

    为什么要有它：6 个管理页各自写 `<div class="row-ops"><IconButton .../></div>`，
    且一度有人写了文字按钮、有人忘了 title、danger 变体各写一遍。
    这个组件把「一组行内动作」收敛成一处：图标化、可禁用、危险色、自定义插槽。

    用法（刻意只封装单元格内容，不封装 el-table-column —— 列宽/固定列各页不同，包进去反而难调）：
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <OpsCell :row="row" :actions="[
            { icon: 'play', label: '使用', onClick: go },
            { icon: 'edit', label: '编辑', onClick: openDialog },
            { icon: 'trash', label: '删除', danger: true,
              disabled: r => r.kind === 'builtin', onClick: handleDelete },
          ]">
            <template #extra="{ row }"><el-tag v-if="row.x">…</el-tag></template>
          </OpsCell>
        </template>
      </el-table-column>
  -->
  <div class="ops">
    <slot name="extra" :row="row" />
    <IconButton
      v-for="a in visible"
      :key="a.key || a.label"
      :icon="a.icon"
      :label="a.label"
      size="sm"
      icon-only
      :variant="a.danger ? 'danger' : (a.variant || 'ghost')"
      :disabled="typeof a.disabled === 'function' ? !!a.disabled(row) : !!a.disabled"
      @click="a.onClick && a.onClick(row)"
    />
    <slot :row="row" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import IconButton from '@/components/common/IconButton.vue'

const props = defineProps({
  /** 当前行数据（用于 disabled / show 判定与 onClick 回调） */
  row: { type: Object, default: () => ({}) },
  /**
   * 动作清单：
   *   { icon, label, onClick(row), danger?, variant?, disabled?: bool|(row)=>bool, show?: (row)=>bool }
   */
  actions: { type: Array, default: () => [] },
})

const visible = computed(() =>
  (props.actions || []).filter((a) => (typeof a.show === 'function' ? a.show(props.row) : a.show !== false))
)
</script>

<style scoped>
/* 行内动作统一间距与不换行；原来是每个页面各写一份 .row-ops */
.ops {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
</style>

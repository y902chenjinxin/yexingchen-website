<template>
  <!--
    页面工具栏（v2.46.157）

    为什么要有它：管理页/列表页的工具栏有 6 套写法（.manage-toolbar / .li-toolbar / .va-toolbar …），
    间距 12/14/18px 不一、换行行为不一、主操作一会儿在标题下一会儿在右侧。
    这个组件统一：**左边筛选、右边主操作、间距一致、窄屏自动换行、主操作永远贴右**。

    用法：
      <PageToolbar>
        <template #filters>
          <FilterSelect … /><SearchField … />
        </template>
        <template #actions>
          <IconButton icon="plus" label="添加" variant="primary" />
        </template>
      </PageToolbar>
    actions 会靠右（中间用弹性占位），不加 actions 时就是普通一行筛选。
  -->
  <div class="pt">
    <div class="pt__main">
      <slot name="filters" />
      <slot />
    </div>
    <div v-if="$slots.actions" class="pt__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({})
</script>

<style scoped>
.pt {
  display: flex;
  align-items: center;
  gap: 10px 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.pt__main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1 1 auto;
  min-width: 0;
  flex-wrap: wrap;
}
.pt__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  margin-left: auto;   /* 主操作永远贴右，用掉中间的空白 */
}

/* 手机：一行放不下就整体换行，主操作跟着走 */
@media (max-width: 560px) {
  .pt { gap: 8px; margin-bottom: 12px; }
  .pt__main { gap: 8px; }
  .pt__actions { margin-left: 0; }
}
</style>

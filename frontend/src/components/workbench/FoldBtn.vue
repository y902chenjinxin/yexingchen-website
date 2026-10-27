<template>
  <button class="fbtn" :class="{ on: open }" :aria-expanded="open" @click="$emit('toggle')">
    <span class="fbtn-text">{{ open ? closeText : openText }}</span>
    <i class="fbtn-arrow">⌄</i>
  </button>
</template>

<script setup>
/**
 * 卡片折叠按钮（v2.46.252）
 *
 * 夜星：「卡片的展开按钮不在一个位置，优化下。」
 *
 * 之前三张卡各写各的：英语卡在右栏里、知识卡在标题行右侧、场景卡在「难在哪」下面，
 * 竖着一排卡片看下来，按钮位置一路往下掉，眼睛没法形成肌肉记忆。
 *
 * 现在统一：**所有卡的折叠按钮都放在卡片右上角、日期导航的右边**，
 * 字号/颜色/箭头完全一致。内容差异靠 openText 表达（「长句 63 词」「展开看怎么办」）。
 */
defineProps({
  open: { type: Boolean, default: false },
  openText: { type: String, default: '展开' },
  closeText: { type: String, default: '收起' },
})
defineEmits(['toggle'])
</script>

<style scoped>
.fbtn {
  display: inline-flex; align-items: center; gap: 3px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .16));
  border-radius: 999px; background: transparent; cursor: pointer;
  padding: 3px 9px 3px 10px;
  font: inherit; font-size: 11.5px; line-height: 1.5; white-space: nowrap;
  color: var(--tc-text-2, #46586e);
  transition: border-color .15s, color .15s, background-color .15s;
}
.fbtn:hover {
  border-color: var(--tc-cyan, #0e93b8);
  color: var(--tc-cyan-deep, #0a708c);
  background: rgba(14, 147, 184, .07);
}
/* 展开中：边框和字变青，一眼看出「现在能看到全部内容」 */
.fbtn.on {
  border-color: var(--tc-cyan, #0e93b8);
  color: var(--tc-cyan-deep, #0a708c);
  background: rgba(14, 147, 184, .07);
}
.fbtn-text { letter-spacing: .01em; }
.fbtn-arrow {
  display: inline-block; font-style: normal; font-size: 12px; line-height: 1;
  transition: transform .18s ease;
}
.fbtn.on .fbtn-arrow { transform: rotate(180deg); }
</style>

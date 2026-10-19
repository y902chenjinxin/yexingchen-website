<template>
  <!-- v2.46.116 翻页时钟工具页（夜星：时分秒收为工具，快捷入口进，首页不展示） -->
  <IslandInnerBase type="tool" title="翻页时钟" subtitle="时分秒 · 经典翻页动画">
    <div class="fc-tool">
      <FlipClock size="lg" />
      <p class="fc-tip">实时走时 · 每秒自动翻页，支持减少动态效果偏好</p>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import FlipClock from '@/components/mobile/FlipClock.vue'
</script>

<style scoped>
.fc-tool {
  display: flex; flex-direction: column; align-items: center; gap: 18px;
  padding: 26px 0 8px;
}
.fc-tip {
  margin: 0; font-size: 12px; letter-spacing: .06em;
  color: var(--ls-text-3, #8a8f98);
}
</style>

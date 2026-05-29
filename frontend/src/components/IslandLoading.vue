<!-- 岛屿内容加载状态 -->
<template>
  <div class="island-loading" :aria-label="`${islandName}加载中`" role="status">
    <div class="loading-ring"></div>
    <span class="sr-only">{{ islandName }}内容加载中...</span>
  </div>
</template>

<script setup>
defineProps({
  islandName: {
    type: String,
    default: '岛屿'
  }
})
</script>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.island-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.loading-ring {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-gold-light);
  border-top-color: var(--color-gold);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
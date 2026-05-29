<template>
  <div class="skeleton-container" aria-label="加载中" role="status">
    <div class="skeleton-header"></div>
    <div class="skeleton-content">
      <div class="skeleton-line" v-for="i in 5" :key="i"></div>
    </div>
    <span class="sr-only">内容加载中，请稍候...</span>
  </div>
</template>

<script setup>
defineProps({
  lines: {
    type: Number,
    default: 5
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

.skeleton-container {
  padding: var(--space-md);
}

.skeleton-header {
  height: 200px;
  background: linear-gradient(90deg, var(--color-bg-glass) 25%, rgba(255,255,255,0.1) 50%, var(--color-bg-glass) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius);
  margin-bottom: var(--space-lg);
}

.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.skeleton-line {
  height: 20px;
  background: linear-gradient(90deg, var(--color-bg-glass) 25%, rgba(255,255,255,0.1) 50%, var(--color-bg-glass) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

.skeleton-line:nth-child(2) { width: 85%; }
.skeleton-line:nth-child(3) { width: 70%; }
.skeleton-line:nth-child(4) { width: 90%; }
.skeleton-line:nth-child(5) { width: 65%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
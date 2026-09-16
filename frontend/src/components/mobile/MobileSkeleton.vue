<template>
  <div class="msk" :class="[$attrs.class]" role="status" aria-label="加载中">
    <!-- 头部大标题占位 -->
    <div class="msk-title"></div>
    <!-- 卡片块 -->
    <div v-for="i in rows" :key="i" class="msk-card">
      <div class="msk-line w70"></div>
      <div class="msk-line w100"></div>
      <div class="msk-line w85"></div>
    </div>
    <!-- 网格占位（2 列） -->
    <div v-if="grid" class="msk-grid">
      <div v-for="i in (grid||6)" :key="'g'+i" class="msk-tile"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  rows: { type: Number, default: 3 },
  grid: { type: Number, default: 0 },
})
</script>

<style scoped>
.msk { padding: 8px 2px; }
.msk-title {
  width: 42%; height: 30px; border-radius: 10px; margin: 10px 0 20px;
  background: var(--lj-line, rgba(127,168,163,.16));
  position: relative; overflow: hidden;
}
.msk-card {
  border-radius: 16px; margin-bottom: 12px; padding: 18px 16px;
  background: var(--lj-glass, rgba(255,255,255,.05));
  border: 1px solid var(--lj-line, rgba(127,168,163,.14));
  backdrop-filter: var(--lj-glass-blur, blur(16px));
}
.msk-line {
  height: 13px; border-radius: 7px; margin-bottom: 10px;
  background: linear-gradient(90deg, transparent, var(--lj-dai, rgba(127,168,163,.20)), transparent);
  background-size: 220% 100%;
  animation: msk-shine 1.4s ease-in-out infinite;
}
.w100 { width: 100%; } .w85 { width: 85%; } .w70 { width: 70%; }
.msk-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 12px; }
.msk-tile {
  height: 96px; border-radius: 16px;
  background: linear-gradient(#d8e7ee, #c3d8e2), var(--lj-line, rgba(127,168,163,.16));
  background-blend-mode: multiply;
}
@keyframes msk-shine {
  0% { background-position: 200% 0; }
  100% { background-position: -20% 0; }
}
</style>
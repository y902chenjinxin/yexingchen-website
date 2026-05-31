<template>
  <div class="mist-layer" aria-hidden="true">
    <div class="mist mist-1"></div>
    <div class="mist mist-2"></div>
    <div class="mist mist-3"></div>
  </div>
</template>

<script setup>
// MistLayer.vue - 薄雾漂移组件
// 提供底部云雾漂移效果，增强首页背景层次感
</script>

<style scoped>
.mist-layer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 200px;
  pointer-events: none;
  z-index: 2;
  overflow: hidden;
}

.mist {
  position: absolute;
  bottom: 0;
  width: 300%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(200, 200, 210, 0.08) 20%,
    rgba(200, 200, 210, 0.12) 50%,
    rgba(200, 200, 210, 0.08) 80%,
    transparent 100%
  );
  filter: blur(30px);
  opacity: 0.6;
}

.mist-1 {
  animation: mist-drift-1 80s linear infinite;
}

.mist-2 {
  animation: mist-drift-2 120s linear infinite;
  opacity: 0.4;
  filter: blur(50px);
}

.mist-3 {
  animation: mist-drift-3 100s linear infinite;
  opacity: 0.3;
  filter: blur(40px);
}

@keyframes mist-drift-1 {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

@keyframes mist-drift-2 {
  0% {
    transform: translateX(100%);
  }
  100% {
    transform: translateX(-100%);
  }
}

@keyframes mist-drift-3 {
  0% {
    transform: translateX(-50%);
  }
  50% {
    transform: translateX(50%);
  }
  100% {
    transform: translateX(-50%);
  }
}

/* 移动端降级 */
@media (max-width: 768px) {
  .mist-layer {
    height: 120px;
  }

  .mist {
    opacity: 0.3;
  }

  .mist-1 {
    animation-duration: 120s;
  }

  .mist-2 {
    animation-duration: 180s;
  }

  .mist-3 {
    display: none;
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .mist {
    animation: none;
    opacity: 0.15;
  }
}
</style>
<template>
  <div class="island-inner" :class="`island-inner-${type}`">
    <!-- 背景层 -->
    <div class="inner-background">
      <div class="inner-stars"></div>
      <div class="inner-qi"></div>
    </div>

    <!-- 内容区 -->
    <div class="inner-content">
      <header class="inner-header">
        <button class="back-btn" @click="$emit('back')">
          <span class="back-icon">←</span>
          <span class="back-text">返回仙府</span>
        </button>
        <h1 class="island-title">{{ title }}</h1>
        <p class="island-subtitle">{{ subtitle }}</p>
      </header>

      <main class="inner-main">
        <slot></slot>
      </main>
    </div>

    <!-- 装饰层 -->
    <div class="inner-decorations">
      <div class="floating-element" v-for="i in 5" :key="i" :class="`element-${i}`"></div>
    </div>

    <!-- 灵气粒子 -->
    <canvas ref="particleCanvas" class="inner-particles"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useParticleSystem } from '@/composables/useParticleSystem'

const props = defineProps({
  type: {
    type: String,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    required: true
  }
})

defineEmits(['back'])

const particleCanvas = ref(null)
let particleSystem = null

onMounted(() => {
  const accentColor = {
    music: 'rgba(155, 141, 201, 0.5)',
    novel: 'rgba(212, 196, 168, 0.5)',
    video: 'rgba(168, 124, 156, 0.5)',
    log: 'rgba(122, 155, 124, 0.5)',
    tool: 'rgba(196, 154, 108, 0.5)'
  }

  particleSystem = useParticleSystem(particleCanvas, {
    particleCount: 20,
    colors: [accentColor[props.type] || 'rgba(201, 169, 98, 0.5)'],
    lifetime: 2000,
    speed: 0.5,
    size: 2,
    maxParticles: 30
  })
})

onUnmounted(() => {
  if (particleSystem) {
    particleSystem.pause()
  }
})
</script>

<style scoped>
.island-inner {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: var(--color-bg);
  overflow: hidden;
}

/* 各岛屿专属色调 */
.island-inner-music {
  --island-accent: var(--island-music, #9B8DC9);
}

.island-inner-novel {
  --island-accent: var(--island-novel, #D4C4A8);
}

.island-inner-video {
  --island-accent: var(--island-video, #A87C9C);
}

.island-inner-log {
  --island-accent: var(--island-log, #7A9B7C);
}

.island-inner-tool {
  --island-accent: var(--island-tool, #C49A6C);
}

.inner-background {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.inner-stars {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    circle at 20% 30%,
    rgba(201, 169, 98, 0.05) 0%,
    transparent 50%
  );
}

.inner-qi {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at 80% 70%,
    var(--island-accent) 0%,
    transparent 60%
  );
  opacity: 0.1;
  animation: qi-pulse 8s ease-in-out infinite;
}

@keyframes qi-pulse {
  0%, 100% { opacity: 0.1; transform: scale(1); }
  50% { opacity: 0.2; transform: scale(1.1); }
}

.inner-content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.inner-header {
  padding: 30px 40px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(201, 169, 98, 0.1);
  border: 1px solid rgba(201, 169, 98, 0.3);
  border-radius: 20px;
  color: var(--color-gold);
  cursor: pointer;
  transition: all 0.3s ease;
  width: fit-content;
}

.back-btn:hover {
  background: rgba(201, 169, 98, 0.2);
  border-color: rgba(201, 169, 98, 0.5);
}

.back-icon {
  font-size: 16px;
}

.back-text {
  font-size: 14px;
}

.island-title {
  font-family: var(--font-serif);
  font-size: 36px;
  color: var(--color-gold);
  margin: 20px 0 5px;
}

.island-subtitle {
  font-size: 16px;
  color: var(--color-text-secondary);
}

.inner-main {
  flex: 1;
  padding: 20px 40px;
  overflow-y: auto;
}

.inner-decorations {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 2;
}

.floating-element {
  position: absolute;
  background: var(--island-accent);
  border-radius: 50%;
  opacity: 0.3;
  filter: blur(20px);
  animation: float-element 15s ease-in-out infinite;
}

.element-1 { width: 100px; height: 100px; top: 20%; left: 10%; animation-delay: 0s; }
.element-2 { width: 150px; height: 150px; top: 60%; left: 70%; animation-delay: 3s; }
.element-3 { width: 80px; height: 80px; top: 40%; left: 80%; animation-delay: 6s; }
.element-4 { width: 120px; height: 120px; top: 70%; left: 20%; animation-delay: 9s; }
.element-5 { width: 60px; height: 60px; top: 30%; left: 50%; animation-delay: 12s; }

@keyframes float-element {
  0%, 100% { transform: translateY(0) scale(1); opacity: 0.3; }
  50% { transform: translateY(-30px) scale(1.1); opacity: 0.5; }
}

.inner-particles {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}
</style>
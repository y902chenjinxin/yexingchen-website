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
        <button class="back-btn" @click="goBack">
          <span class="back-icon">←</span>
          <span class="back-text">返回工作台</span>
        </button>
        <h1 class="island-title">{{ title }}</h1>
        <p class="island-subtitle">{{ subtitle }}</p>
        <div v-if="$slots.toolbar" class="inner-toolbar"><slot name="toolbar" /></div>
      </header>

      <main class="inner-main">
        <slot></slot>
      </main>

      <!-- 底部网安/备案标识 -->
      <SiteFooter variant="dark" class="inner-footer" />
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
import { useRouter } from 'vue-router'
import { useParticleSystem } from '@/composables/useParticleSystem'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()

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

function goBack() {
  router.push('/workbench')
}

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
  /* 岛屿内容为普通全屏容器：z-index 需低于 Element 弹层（约 2000）与桌宠配置面板，
     否则会盖住挂到 body 的上传/编辑/删除等弹窗，表现为"点击按钮没反应" */
  z-index: 1;
  background: var(--ls-bg1);
  overflow: hidden;
}

/* 墨青夜色背景：双层渐变 + 纸纹噪点 + 慢晕光斑（去平涂廉价感） */
.island-inner::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 70% 45% at 18% 12%, var(--ls-bg-glow), transparent 62%),
    radial-gradient(ellipse 55% 40% at 88% 78%, rgba(194, 162, 107, 0.05), transparent 60%),
    linear-gradient(168deg, #1b262f 0%, #131b22 55%, #10161c 100%);
}
.island-inner::after {
  content: '';
  position: absolute;
  inset: 0;
  opacity: .5;
  background:
    repeating-linear-gradient(0deg, rgba(206,220,226,.012) 0 1px, transparent 1px 4px),
    repeating-linear-gradient(90deg, rgba(206,220,226,.008) 0 1px, transparent 1px 6px);
  pointer-events: none;
}

/* 各岛屿专属低饱和 accent（玄素琉璃同源，克制非鲜艳） */
.island-inner-music {
  --island-accent: var(--ls-dai, #5f9499);
}
.island-inner-novel {
  --island-accent: var(--ls-ochre, #c2a26b);
}
.island-inner-video {
  --island-accent: #8a6a86;
}
.island-inner-log {
  --island-accent: var(--ls-jade, #6aa98f);
}
.island-inner-tool {
  --island-accent: #a5825a;
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
  box-sizing: border-box;
}

.inner-header {
  padding: 26px 40px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(165deg, rgba(255,255,255,.05), rgba(255,255,255,0) 55%), var(--ls-glass);
  border: 1px solid var(--ls-line);
  border-radius: 20px;
  color: var(--ls-text-2);
  cursor: pointer;
  transition: all 0.3s ease;
  width: fit-content;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
  backdrop-filter: saturate(160%) blur(12px);
}

.back-btn:hover {
  border-color: var(--ls-line-strong);
  color: var(--ls-text);
  transform: translateY(-1px);
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
  font-weight: 600;
  letter-spacing: .08em;
  background: linear-gradient(180deg, #f2f6f8 20%, var(--ls-ochre) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin: 18px 0 4px;
}

.island-subtitle {
  font-size: 15px;
  color: var(--ls-text-2);
  letter-spacing: .06em;
}

.inner-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
  flex-wrap: wrap;
}

.inner-main {
  flex: 1;
  /* 底部留出播放条空间（npbar：bottom16+高62），并把页脚顶到画面真实底部，避免页脚悬浮 */
  padding: 16px 40px 88px;
  overflow-y: auto;
}

.inner-footer {
  flex: none;
  position: relative;
  z-index: 3;
  padding: 8px 20px 10px;
  border-top: 1px solid var(--ls-line);
  background: rgba(16, 22, 28, 0.5);
  backdrop-filter: saturate(140%) blur(8px);
  -webkit-backdrop-filter: saturate(140%) blur(8px);
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

/* 桌面缩放(>100%)或较窄视口时收敛留白与字号，避免破版/横向溢出 */
@media (max-width: 1100px) {
  .inner-header { padding: 22px 26px 12px; }
  .inner-main { padding: 14px 26px 80px; }
  .island-title { font-size: 30px; }
}
@media (max-width: 760px) {
  .inner-header { padding: 18px 16px 10px; }
  .inner-main { padding: 12px 16px 72px; }
  .island-title { font-size: 24px; }
  .island-subtitle { font-size: 13px; }
}
</style>
<template>
  <div class="entrance-overlay" v-if="!isComplete">
    <!-- 墨染层 - 重力流淌效果 -->
    <svg class="ink-flow-layer" :class="{ active: currentPhase >= 0 }" viewBox="0 0 100 100" preserveAspectRatio="none">
      <defs>
        <!-- 毛笔质感滤镜 -->
        <filter id="ink-edge" x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" result="noise"/>
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
        </filter>
        <!-- 墨迹渐变 -->
        <linearGradient id="ink-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="var(--color-ink-deep)" stop-opacity="0.9"/>
          <stop offset="50%" stop-color="var(--color-ink-deep)" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="var(--color-ink-deep)" stop-opacity="0.4"/>
        </linearGradient>
      </defs>
      <!-- 墨迹流淌路径 -->
      <g filter="url(#ink-edge)">
        <path
          class="ink-stream ink-stream-1"
          d="M0,0 Q20,30 10,50 T30,100 L0,100 Z"
          fill="url(#ink-gradient)"
        />
        <path
          class="ink-stream ink-stream-2"
          d="M30,0 Q50,25 40,55 T50,100 L30,100 Z"
          fill="url(#ink-gradient)"
        />
        <path
          class="ink-stream ink-stream-3"
          d="M60,0 Q75,35 65,60 T75,100 L55,100 Z"
          fill="url(#ink-gradient)"
        />
        <path
          class="ink-stream ink-stream-4"
          d="M85,0 Q95,20 90,45 T95,100 L80,100 Z"
          fill="url(#ink-gradient)"
        />
      </g>
    </svg>

    <!-- 灵气涌动层 -->
    <div class="qi-surge" :class="{ active: currentPhase >= 1 }">
      <div class="qi-orb"></div>
    </div>

    <!-- 阵法符文层 -->
    <div class="symbol-layer" :class="{ active: currentPhase >= 2 }">
      <div class="symbol-ring symbol-ring-1"></div>
      <div class="symbol-ring symbol-ring-2"></div>
      <div class="symbol-ring symbol-ring-3"></div>
    </div>

    <!-- 岛屿凝聚层 -->
    <div class="island-materialize" :class="{ active: currentPhase >= 3 }">
      <div class="island-placeholder" v-for="i in 5" :key="i"></div>
    </div>

    <!-- 顶栏淡入层 -->
    <div class="topbar-layer" :class="{ active: currentPhase >= 4 }"></div>

    <!-- 跳过提示 -->
    <div class="skip-hint" :class="{ visible: showSkipHint }">
      点击任意处跳过
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useEntranceAnimation } from '@/composables/useEntranceAnimation'

const props = defineProps({
  onComplete: {
    type: Function,
    default: null
  }
})

const { isComplete, currentPhase, runEntrance } = useEntranceAnimation()

const showSkipHint = ref(false)

// 监听动画完成，触发回调
watch(isComplete, (complete) => {
  if (complete && props.onComplete) {
    props.onComplete()
  }
})

// 2秒后显示跳过提示
onMounted(() => {
  runEntrance()

  setTimeout(() => {
    showSkipHint.value = true
  }, 2000)
})
</script>

<style scoped>
.entrance-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
  pointer-events: all;
}

/* 墨染层 */
.ink-flow-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.ink-flow-layer.active {
  opacity: 1;
}

/* 墨迹流淌动画 */
.ink-stream {
  opacity: 0;
}

.ink-flow-layer.active .ink-stream {
  animation: ink-flow 3s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}

.ink-stream-1 {
  animation-delay: 0s !important;
}

.ink-stream-2 {
  animation-delay: 0.15s !important;
}

.ink-stream-3 {
  animation-delay: 0.3s !important;
}

.ink-stream-4 {
  animation-delay: 0.45s !important;
}

@keyframes ink-flow {
  0% {
    opacity: 0;
    transform: translateY(-100%);
  }
  20% {
    opacity: 0.9;
  }
  50% {
    opacity: 0.85;
  }
  70% {
    opacity: 0.7;
  }
  100% {
    opacity: 0;
    transform: translateY(0%);
  }
}

/* 灵气涌动 */
.qi-surge {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 1.5s ease;
}

.qi-surge.active {
  opacity: 1;
}

.qi-orb {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    var(--color-gold-light) 0%,
    transparent 70%
  );
  animation: qi-pulse 2s ease-in-out infinite;
}

@keyframes qi-pulse {
  0%, 100% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 0.8; }
}

/* 阵法符文 */
.symbol-layer {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 1s ease;
}

.symbol-layer.active {
  opacity: 1;
}

.symbol-ring {
  position: absolute;
  border: 1px solid var(--color-gold);
  border-radius: 50%;
  opacity: 0.3;
}

.symbol-ring-1 {
  width: 600px;
  height: 600px;
  animation: symbol-rotate 240s linear infinite;
}

.symbol-ring-2 {
  width: 400px;
  height: 400px;
  animation: symbol-rotate 180s linear infinite reverse;
}

.symbol-ring-3 {
  width: 800px;
  height: 800px;
  animation: symbol-rotate 300s linear infinite;
}

@keyframes symbol-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 岛屿凝聚 */
.island-materialize {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 2s ease;
}

.island-materialize.active {
  opacity: 1;
}

.island-placeholder {
  position: absolute;
  width: 100px;
  height: 100px;
  background: var(--color-gold);
  border-radius: 50%;
  opacity: 0;
  animation: materialize 1s ease forwards;
}

.island-placeholder:nth-child(1) { animation-delay: 0s; }
.island-placeholder:nth-child(2) { animation-delay: 0.3s; }
.island-placeholder:nth-child(3) { animation-delay: 0.6s; }
.island-placeholder:nth-child(4) { animation-delay: 0.9s; }
.island-placeholder:nth-child(5) { animation-delay: 1.2s; }

@keyframes materialize {
  0% {
    opacity: 0;
    transform: scale(0) translateY(50px);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2) translateY(-20px);
  }
  100% {
    opacity: 0;
    transform: scale(1) translateY(0);
  }
}

/* 顶栏淡入 */
.topbar-layer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: linear-gradient(
    to bottom,
    var(--color-ink-deep) 0%,
    transparent 100%
  );
  opacity: 0;
  transition: opacity 1s ease;
}

.topbar-layer.active {
  opacity: 1;
}

/* 跳过提示 */
.skip-hint {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--color-text-muted);
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.5s ease;
  pointer-events: none;
}

.skip-hint.visible {
  opacity: 0.5;
}
</style>
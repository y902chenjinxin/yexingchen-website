<template>
  <div class="random-events-layer">
    <!-- 流星雨 -->
    <div v-if="activeEvent === 'meteor_shower'" class="meteor-shower">
      <div
        v-for="i in meteorCount"
        :key="`meteor-${i}`"
        class="meteor"
        :style="getMeteorStyle(i)"
      ></div>
    </div>

    <!-- 灵气爆发 -->
    <div v-if="activeEvent === 'qi_burst'" class="qi-burst">
      <div class="burst-flash"></div>
      <div class="burst-ring"></div>
    </div>

    <!-- 仙鹤群飞 -->
    <div v-if="activeEvent === 'crane_swarm'" class="crane-swarm">
      <div
        v-for="i in craneCount"
        :key="`swarm-crane-${i}`"
        class="crane"
        :style="getSwarmCraneStyle(i)"
      >
        <svg viewBox="0 0 60 40" class="crane-svg">
          <path d="M5 25 Q15 15 30 20 Q45 15 55 25" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M30 20 L30 10 L35 15" stroke="currentColor" stroke-width="1" fill="none"/>
          <circle cx="30" cy="8" r="2" fill="currentColor"/>
        </svg>
      </div>
    </div>

    <!-- 祥云降临 -->
    <div v-if="activeEvent === 'auspicious_clouds'" class="auspicious-clouds">
      <div
        v-for="i in cloudCount"
        :key="`cloud-${i}`"
        class="auspicious-cloud"
        :style="getCloudStyle(i)"
      ></div>
    </div>

    <!-- 天雷隐现 -->
    <div v-if="activeEvent === 'distant_thunder'" class="distant-thunder">
      <div
        v-for="i in lightningCount"
        :key="`lightning-${i}`"
        class="lightning"
        :style="getLightningStyle(i)"
      >
        <svg viewBox="0 0 30 80" class="lightning-svg">
          <path d="M15 0 L10 25 L18 25 L8 50 L16 50 L6 80 L20 45 L12 45 L22 20 L14 20 Z"
                fill="currentColor" opacity="0.8"/>
        </svg>
      </div>
      <div class="thunder-flash"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  activeEvent: {
    type: String,
    default: null
  }
})

// seeded random
function seededRandom(seed) {
  const x = Math.abs(Math.sin(seed * 12.9898) * 43758.5453) % 1
  return x
}

// 流星数量（3-5颗）
const meteorCount = computed(() => {
  const seed = Date.now() % 1000
  return 3 + Math.floor(seededRandom(seed) * 3)
})

// 仙鹤数量（3-5只）
const craneCount = computed(() => {
  const seed = (Date.now() % 1000) + 100
  return 3 + Math.floor(seededRandom(seed) * 3)
})

// 祥云数量
const cloudCount = computed(() => {
  const seed = (Date.now() % 1000) + 200
  return 4 + Math.floor(seededRandom(seed) * 3)
})

// 闪电数量
const lightningCount = computed(() => {
  const seed = (Date.now() % 1000) + 300
  return 2 + Math.floor(seededRandom(seed) * 3)
})

// 获取流星样式
function getMeteorStyle(index) {
  const seed = Date.now() + index * 100
  const startX = seededRandom(seed) * 60 + 20 // 20% - 80%
  const startY = seededRandom(seed + 1) * 30 // 0% - 30%
  const endX = seededRandom(seed + 2) * 40 + 50 // 50% - 90%
  const endY = seededRandom(seed + 3) * 40 + 60 // 60% - 100%
  const delay = seededRandom(seed + 4) * 0.5
  const duration = 1 + seededRandom(seed + 5) * 0.5

  return {
    '--start-x': `${startX}%`,
    '--start-y': `${startY}%`,
    '--end-x': `${endX}%`,
    '--end-y': `${endY}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

// 获取群飞仙鹤样式
function getSwarmCraneStyle(index) {
  const seed = Date.now() + index * 200
  const y = seededRandom(seed) * 50 + 10
  const delay = seededRandom(seed + 1) * 2
  const duration = 8 + seededRandom(seed + 2) * 4
  const scale = 0.6 + seededRandom(seed + 3) * 0.6

  return {
    top: `${y}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
    transform: `scale(${scale})`,
    opacity: 0.4 + seededRandom(seed + 4) * 0.4
  }
}

// 获取祥云样式
function getCloudStyle(index) {
  const seed = Date.now() + index * 150
  const x = seededRandom(seed) * 80 + 10
  const startY = 100 + seededRandom(seed + 1) * 20
  const endY = seededRandom(seed + 2) * 50
  const delay = seededRandom(seed + 3) * 2
  const duration = 5 + seededRandom(seed + 4) * 3
  const scale = 0.8 + seededRandom(seed + 5) * 1.2

  return {
    '--start-x': `${x}%`,
    '--start-y': `${startY}%`,
    '--end-y': `${endY}%`,
    '--scale': scale,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

// 获取闪电样式
function getLightningStyle(index) {
  const seed = Date.now() + index * 300
  const x = seededRandom(seed) * 70 + 15
  const y = seededRandom(seed + 1) * 30
  const delay = seededRandom(seed + 2) * 2
  const duration = 0.2 + seededRandom(seed + 3) * 0.3

  return {
    left: `${x}%`,
    top: `${y}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}
</script>

<style scoped>
.random-events-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 4;
  overflow: hidden;
}

/* 流星雨 */
.meteor-shower {
  position: absolute;
  inset: 0;
}

.meteor {
  position: absolute;
  width: 2px;
  height: 2px;
  background: linear-gradient(45deg, transparent, var(--color-gold), transparent);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--color-gold), 0 0 20px var(--color-gold);
  animation: meteor-fall linear forwards;
  will-change: transform;
}

@keyframes meteor-fall {
  0% {
    transform: translateX(var(--start-x)) translateY(var(--start-y));
    opacity: 1;
  }
  70% {
    opacity: 1;
  }
  100% {
    transform: translateX(var(--end-x)) translateY(var(--end-y));
    opacity: 0;
  }
}

/* 灵气爆发 */
.qi-burst {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.burst-flash {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, rgba(201, 169, 98, 0.6) 0%, rgba(201, 169, 98, 0.2) 50%, transparent 70%);
  animation: flash-pulse 0.5s ease-out forwards;
  will-change: opacity;
}

.burst-ring {
  position: absolute;
  width: 100px;
  height: 100px;
  border: 2px solid var(--color-gold);
  border-radius: 50%;
  animation: ring-expand 1s ease-out forwards;
  will-change: transform, opacity;
}

@keyframes flash-pulse {
  0% { opacity: 0; }
  20% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes ring-expand {
  0% { transform: scale(0); opacity: 1; }
  100% { transform: scale(20); opacity: 0; }
}

/* 仙鹤群飞 */
.crane-swarm {
  position: absolute;
  inset: 0;
}

.crane-swarm .crane {
  position: absolute;
  width: 60px;
  height: 40px;
  color: rgba(201, 169, 98, 0.7);
  animation: swarm-crane-fly linear forwards;
  will-change: transform;
}

.crane-swarm .crane-svg {
  width: 100%;
  height: 100%;
}

@keyframes swarm-crane-fly {
  0% { transform: translateX(-100px) scale(var(--scale, 1)); }
  50% { transform: translateX(50vw) translateY(-20px) scale(var(--scale, 1)); }
  100% { transform: translateX(calc(100vw + 100px)) scale(var(--scale, 1)); }
}

/* 祥云降临 */
.auspicious-clouds {
  position: absolute;
  inset: 0;
}

.auspicious-cloud {
  position: absolute;
  left: var(--start-x);
  top: var(--start-y);
  width: 200px;
  height: 100px;
  background: radial-gradient(ellipse at center, rgba(201, 169, 98, 0.3) 0%, rgba(201, 169, 98, 0.1) 50%, transparent 70%);
  border-radius: 50%;
  filter: blur(10px);
  animation: cloud-rise ease-out forwards;
  will-change: transform, opacity;
  transform: scale(var(--scale, 1));
}

@keyframes cloud-rise {
  0% {
    transform: translateY(0) scale(var(--scale, 1));
    opacity: 0;
  }
  20% {
    opacity: 0.8;
  }
  100% {
    transform: translateY(calc(var(--start-y) - var(--end-y) - 100px)) scale(var(--scale, 1));
    opacity: 0;
  }
}

/* 天雷隐现 */
.distant-thunder {
  position: absolute;
  inset: 0;
}

.lightning {
  position: absolute;
  width: 30px;
  height: 80px;
  color: rgba(201, 169, 98, 0.6);
  animation: lightning-flash 0.3s ease-in-out forwards;
  will-change: opacity;
  filter: blur(1px);
}

.lightning-svg {
  width: 100%;
  height: 100%;
}

.thunder-flash {
  position: absolute;
  inset: 0;
  background: rgba(201, 169, 98, 0.1);
  animation: thunder-flash 0.5s ease-out forwards;
}

@keyframes lightning-flash {
  0%, 100% { opacity: 0; }
  10%, 30%, 50% { opacity: 1; }
  20%, 40% { opacity: 0.3; }
}

@keyframes thunder-flash {
  0% { opacity: 0; }
  10% { opacity: 1; }
  20% { opacity: 0.2; }
  30% { opacity: 0.8; }
  100% { opacity: 0; }
}

/* 响应式 */
@media (max-width: 768px) {
  .crane-swarm .crane {
    width: 40px;
    height: 26px;
  }

  .auspicious-cloud {
    width: 120px;
    height: 60px;
  }

  .lightning {
    width: 20px;
    height: 50px;
  }
}
</style>
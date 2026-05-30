<template>
  <div class="decorations-layer">
    <!-- 灯笼 -->
    <div
      v-for="lantern in lanterns"
      :key="lantern.id"
      class="lantern"
      :style="lantern.style"
    >
      <div class="lantern-body">
        <div class="lantern-glow"></div>
      </div>
    </div>

    <!-- 丹炉 -->
    <div
      v-if="showAlchemyFurnace"
      class="alchemy-furnace"
      :style="alchemyFurnaceStyle"
    >
      <div class="furnace-body"></div>
      <div class="furnace-smoke">
        <span v-for="i in 5" :key="i" class="smoke-particle" :style="{ animationDelay: `${i * 0.3}s` }"></span>
      </div>
    </div>

    <!-- 仙鹤 -->
    <div
      v-for="crane in cranes"
      :key="crane.id"
      class="crane"
      :style="crane.style"
    >
      <svg viewBox="0 0 60 40" class="crane-svg">
        <path d="M5 25 Q15 15 30 20 Q45 15 55 25" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M30 20 L30 10 L35 15" stroke="currentColor" stroke-width="1" fill="none"/>
        <circle cx="30" cy="8" r="2" fill="currentColor"/>
      </svg>
    </div>

    <!-- 符文碎片 -->
    <div
      v-for="rune in runes"
      :key="rune.id"
      class="rune-fragment"
      :style="rune.style"
    ></div>

    <!-- 天机提示 -->
    <div
      v-if="showHint"
      class="tianji-hint"
      @mouseenter="showHintText = true"
      @mouseleave="showHintText = false"
    >
      <span class="hint-icon">☯</span>
      <span v-if="showHintText" class="hint-text">{{ hintText }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  shichen: {
    type: String,
    default: '子时'
  }
})

// seeded random
function seededRandom(seed) {
  const x = Math.abs(Math.sin(seed * 12.9898) * 43758.5453) % 1
  return x
}

// 获取日期种子
function getDaySeed() {
  const date = new Date()
  return date.getFullYear() * 10000 + (date.getMonth() + 1) * 100 + date.getDate()
}

// 显示状态
const showHint = ref(true)
const showHintText = ref(false)
const hintText = '天机：可遇不可求'

// 灯笼数据
const lanterns = ref([])
const LANTERN_COUNT = 3

// 丹炉数据
const showAlchemyFurnace = ref(false)
const alchemyFurnaceStyle = ref({})

// 仙鹤数据
const cranes = ref([])
const CRANE_COUNT = 1

// 符文碎片数据
const runes = ref([])
const RUNE_COUNT = 6

// 初始化装饰物件
function initDecorations() {
  const daySeed = getDaySeed()
  const hourSeed = daySeed + new Date().getHours()

  // 生成灯笼
  lanterns.value = []
  for (let i = 0; i < LANTERN_COUNT; i++) {
    const seed = hourSeed + i * 100
    const random = seededRandom(seed)
    if (random < 0.2) { // 20%概率
      const x = seededRandom(seed + 1) * 80 + 5 // 5% - 85%
      const y = seededRandom(seed + 2) * 60 + 10 // 10% - 70%
      const delay = seededRandom(seed + 3) * 5
      const duration = 4 + seededRandom(seed + 4) * 3
      lanterns.value.push({
        id: `lantern-${i}`,
        style: {
          left: `${x}%`,
          top: `${y}%`,
          animationDelay: `${delay}s`,
          animationDuration: `${duration}s`
        }
      })
    }
  }

  // 生成丹炉（极低概率）
  const furnaceSeed = hourSeed + 999
  const furnaceRandom = seededRandom(furnaceSeed)
  showAlchemyFurnace.value = furnaceRandom < 0.05
  if (showAlchemyFurnace.value) {
    const x = seededRandom(furnaceSeed + 1) * 70 + 15
    const y = seededRandom(furnaceSeed + 2) * 50 + 30
    alchemyFurnaceStyle.value = {
      left: `${x}%`,
      top: `${y}%`,
      animationDelay: `${seededRandom(furnaceSeed + 3) * 3}s`
    }
  }

  // 生成仙鹤
  cranes.value = []
  const craneSeed = hourSeed + 888
  const craneRandom = seededRandom(craneSeed)
  if (craneRandom < 0.03) { // 极低概率（每5分钟一次，简化处理）
    for (let i = 0; i < CRANE_COUNT; i++) {
      const seed = craneSeed + i * 50
      const y = seededRandom(seed) * 40 + 10
      const delay = seededRandom(seed + 1) * 5
      const duration = 15 + seededRandom(seed + 2) * 10
      cranes.value.push({
        id: `crane-${i}`,
        style: {
          top: `${y}%`,
          animationDelay: `${delay}s`,
          animationDuration: `${duration}s`
        }
      })
    }
  }

  // 生成符文碎片
  runes.value = []
  for (let i = 0; i < RUNE_COUNT; i++) {
    const seed = hourSeed + i * 77
    const random = seededRandom(seed)
    if (random < 0.4) { // 中等概率
      const x = seededRandom(seed + 1) * 90 + 5
      const y = seededRandom(seed + 2) * 80 + 10
      const delay = seededRandom(seed + 3) * 8
      const duration = 8 + seededRandom(seed + 4) * 6
      const size = 4 + seededRandom(seed + 5) * 6
      runes.value.push({
        id: `rune-${i}`,
        style: {
          left: `${x}%`,
          top: `${y}%`,
          width: `${size}px`,
          height: `${size}px`,
          animationDelay: `${delay}s`,
          animationDuration: `${duration}s`
        }
      })
    }
  }
}

let intervalId = null

onMounted(() => {
  initDecorations()
  // 每分钟重新计算装饰物件显示
  intervalId = setInterval(initDecorations, 60000)
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
  }
})
</script>

<style scoped>
.decorations-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 3;
  overflow: hidden;
}

/* 灯笼 */
.lantern {
  position: absolute;
  width: 30px;
  height: 45px;
  animation: lantern-float 5s ease-in-out infinite;
  will-change: transform;
}

.lantern-body {
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse at center, rgba(201, 169, 98, 0.6) 0%, rgba(201, 169, 98, 0.2) 50%, transparent 70%);
  border-radius: 50% 50% 45% 45%;
  position: relative;
}

.lantern-glow {
  position: absolute;
  inset: -10px;
  background: radial-gradient(ellipse at center, rgba(201, 169, 98, 0.4) 0%, transparent 60%);
  border-radius: 50%;
  animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes lantern-float {
  0%, 100% { transform: translateY(0) rotate(-2deg); }
  50% { transform: translateY(-15px) rotate(2deg); }
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* 丹炉 */
.alchemy-furnace {
  position: absolute;
  width: 80px;
  height: 100px;
  opacity: 0.3;
  animation: furnace-appear 3s ease-out forwards;
  will-change: transform, opacity;
}

.furnace-body {
  width: 100%;
  height: 70%;
  background: linear-gradient(180deg, rgba(139, 115, 85, 0.8) 0%, rgba(100, 80, 60, 0.6) 100%);
  border-radius: 10% 10% 40% 40%;
  position: relative;
}

.furnace-body::before {
  content: '';
  position: absolute;
  top: 20%;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 25px;
  background: radial-gradient(ellipse at center, rgba(201, 169, 98, 0.5) 0%, transparent 70%);
  border-radius: 50%;
}

.furnace-smoke {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 40px;
}

.smoke-particle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: radial-gradient(ellipse at center, rgba(201, 169, 98, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  animation: smoke-rise 3s ease-out infinite;
  will-change: transform, opacity;
}

@keyframes furnace-appear {
  0% { opacity: 0; transform: scale(0.8); }
  30% { opacity: 0.4; }
  100% { opacity: 0.3; transform: scale(1); }
}

@keyframes smoke-rise {
  0% { transform: translateY(0) scale(1); opacity: 0.5; }
  100% { transform: translateY(-40px) scale(2); opacity: 0; }
}

/* 仙鹤 */
.crane {
  position: absolute;
  width: 60px;
  height: 40px;
  color: rgba(201, 169, 98, 0.6);
  animation: crane-fly 20s linear infinite;
  will-change: transform;
}

.crane-svg {
  width: 100%;
  height: 100%;
}

@keyframes crane-fly {
  0% { transform: translateX(-100px) translateY(0); }
  25% { transform: translateX(25vw) translateY(-10px); }
  50% { transform: translateX(50vw) translateY(5px); }
  75% { transform: translateX(75vw) translateY(-5px); }
  100% { transform: translateX(calc(100vw + 100px)) translateY(0); }
}

/* 符文碎片 */
.rune-fragment {
  position: absolute;
  background: linear-gradient(135deg, var(--color-gold) 0%, var(--color-gold-light) 50%, var(--color-gold) 100%);
  opacity: 0.4;
  border-radius: 2px;
  animation: rune-float 10s ease-in-out infinite;
  will-change: transform;
  box-shadow: 0 0 10px rgba(201, 169, 98, 0.3);
}

@keyframes rune-float {
  0%, 100% {
    transform: translateY(0) translateX(0) rotate(0deg);
    opacity: 0.4;
  }
  25% {
    transform: translateY(-20px) translateX(10px) rotate(90deg);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-10px) translateX(-5px) rotate(180deg);
    opacity: 0.3;
  }
  75% {
    transform: translateY(-25px) translateX(15px) rotate(270deg);
    opacity: 0.5;
  }
}

/* 天机提示 */
.tianji-hint {
  position: fixed;
  bottom: 80px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-bg-glass);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(201, 169, 98, 0.2);
  border-radius: 8px;
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.3s;
  z-index: 100;
}

.tianji-hint:hover {
  border-color: rgba(201, 169, 98, 0.5);
  background: var(--color-bg-elevated);
}

.hint-icon {
  font-size: 16px;
  color: var(--color-gold);
  animation: hint-pulse 3s ease-in-out infinite;
}

.hint-text {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  animation: fade-in 0.3s ease;
}

@keyframes hint-pulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}

@keyframes fade-in {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 响应式 */
@media (max-width: 768px) {
  .lantern {
    width: 20px;
    height: 30px;
  }

  .alchemy-furnace {
    width: 50px;
    height: 60px;
  }

  .crane {
    width: 40px;
    height: 26px;
  }

  .tianji-hint {
    bottom: 70px;
    right: 10px;
    padding: 6px 10px;
  }
}
</style>
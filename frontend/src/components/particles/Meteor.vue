<template>
  <div class="meteor-container" v-if="isEnabled" ref="containerRef">
    <div
      v-for="meteor in meteors"
      :key="meteor.id"
      class="meteor"
      :class="{ active: meteor.active }"
      :style="meteor.style"
      @animationend="onMeteorEnd(meteor.id)"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useGracefulDegrade } from '@/composables/useGracefulDegrade'

const { isFeatureEnabled } = useGracefulDegrade()
const isEnabled = ref(true)
const containerRef = ref(null)
const meteors = ref([])
let meteorId = 0
let spawnInterval = null

const spawnMeteor = () => {
  // 随机概率触发
  if (Math.random() > 0.02) return // 2%概率

  const id = meteorId++
  const startX = Math.random() * 100 // 0-100%
  const duration = 1 + Math.random() * 2 // 1-3秒

  meteors.value.push({
    id,
    active: true,
    style: {
      left: `${startX}%`,
      animationDuration: `${duration}s`,
      '--end-x': `${(Math.random() - 0.5) * 200}px`,
      '--end-y': `${300 + Math.random() * 200}px`
    }
  })
}

const onMeteorEnd = (id) => {
  meteors.value = meteors.value.filter(m => m.id !== id)
}

onMounted(() => {
  isEnabled.value = isFeatureEnabled('randomEvents')

  // 每30秒检查一次是否生成流星
  spawnInterval = setInterval(() => {
    if (isEnabled.value) {
      spawnMeteor()
    }
  }, 30000)
})

onUnmounted(() => {
  if (spawnInterval) {
    clearInterval(spawnInterval)
  }
})
</script>

<style scoped>
.meteor-container {
  position: fixed;
  inset: 0;
  z-index: 50;
  pointer-events: none;
  overflow: hidden;
}

.meteor {
  position: absolute;
  top: -10%;
  width: 2px;
  height: 80px;
  background: linear-gradient(
    to bottom,
    transparent 0%,
    var(--color-gold) 50%,
    transparent 100%
  );
  opacity: 0;
  transform: rotate(20deg);
}

.meteor.active {
  animation: meteor-fall var(--duration, 2s) ease-out forwards;
}

@keyframes meteor-fall {
  0% {
    opacity: 0;
    transform: translateY(0) translateX(0) rotate(20deg);
  }
  10% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: translateY(calc(100vh + 100px)) translateX(var(--end-x)) rotate(20deg);
  }
}
</style>
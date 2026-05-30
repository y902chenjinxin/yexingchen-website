/**
 * CultivationProgress.vue
 * 修为进度可视化 - 小篆印章风格显示"今日修为+X"
 */
<template>
  <div class="cultivation-seal" :class="{ 'cultivation-animate': showAnimation }">
    <div class="seal-border">
      <div class="seal-inner">
        <div class="seal-text">今日修为</div>
        <div class="seal-value">+{{ cultivationPoints }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const STORAGE_KEY = 'cultivation_data'
const POINTS_STAY = 1      // 停留10分钟
const POINTS_CLICK = 1     // 点击5次
const POINTS_SCROLL = 1    // 滚动到底

const cultivationPoints = ref(0)
const showAnimation = ref(false)
let stayTimer = null
let clickCount = 0
let clickTimer = null
let hasScrolledToBottom = false

// 从localStorage加载数据
function loadCultivationData() {
  try {
    const today = new Date().toDateString()
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const data = JSON.parse(stored)
      if (data.date === today) {
        cultivationPoints.value = data.points
        hasScrolledToBottom = data.scrolled || false
      }
    }
  } catch (e) {
    console.warn('Failed to load cultivation data:', e)
  }
}

// 保存到localStorage
function saveCultivationData() {
  try {
    const today = new Date().toDateString()
    const data = {
      date: today,
      points: cultivationPoints.value,
      scrolled: hasScrolledToBottom
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (e) {
    console.warn('Failed to save cultivation data:', e)
  }
}

// 增加修为点
function addCultivationPoint(source) {
  cultivationPoints.value++
  showAnimation.value = true
  setTimeout(() => {
    showAnimation.value = false
  }, 600)
  saveCultivationData()
}

// 停留计时 - 每10分钟+1修为
function startStayTimer() {
  let elapsed = 0
  stayTimer = setInterval(() => {
    elapsed += 60 // 每分钟
    if (elapsed >= 600) { // 10分钟
      addCultivationPoint('stay')
      elapsed = 0
    }
  }, 60000)
}

// 点击计数 - 每点击5次+1修为
function handleClick() {
  clickCount++
  if (clickTimer) clearTimeout(clickTimer)
  clickTimer = setTimeout(() => {
    if (clickCount >= 5) {
      addCultivationPoint('click')
      clickCount = 0
    }
  }, 5000) // 5秒内点击5次
}

// 滚动到底检测
function handleScroll() {
  const scrollTop = window.scrollY
  const docHeight = document.documentElement.scrollHeight
  const windowHeight = window.innerHeight
  if (scrollTop + windowHeight >= docHeight - 50) {
    if (!hasScrolledToBottom) {
      hasScrolledToBottom = true
      addCultivationPoint('scroll')
      saveCultivationData()
    }
  }
}

onMounted(() => {
  loadCultivationData()
  startStayTimer()
  window.addEventListener('click', handleClick)
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  if (stayTimer) clearInterval(stayTimer)
  if (clickTimer) clearTimeout(clickTimer)
  window.removeEventListener('click', handleClick)
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.cultivation-seal {
  position: fixed;
  bottom: 80px;
  right: 30px;
  z-index: 100;
  cursor: default;
  transition: transform 0.3s ease;
}

.cultivation-seal:hover {
  transform: scale(1.05);
}

.seal-border {
  border: 2px solid var(--color-gold);
  border-radius: 4px;
  padding: 4px;
  background: var(--color-bg-glass);
  backdrop-filter: blur(8px);
}

.seal-inner {
  border: 1px solid var(--color-gold);
  border-radius: 2px;
  padding: 8px 12px;
  text-align: center;
  background: linear-gradient(135deg, rgba(201, 168, 108, 0.1) 0%, rgba(201, 168, 108, 0.05) 100%);
}

.seal-text {
  font-family: var(--font-serif);
  font-size: 12px;
  color: var(--color-gold);
  letter-spacing: 0.1em;
  margin-bottom: 2px;
}

.seal-value {
  font-family: var(--font-serif);
  font-size: 18px;
  color: var(--color-danger);
  letter-spacing: 0.05em;
  font-weight: 600;
}

/* 动画效果 */
.cultivation-animate .seal-value {
  animation: cultivation-pulse 0.6s ease-out;
}

@keyframes cultivation-pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .cultivation-seal {
    bottom: 100px;
    right: 15px;
  }

  .seal-border {
    padding: 3px;
  }

  .seal-inner {
    padding: 6px 10px;
  }

  .seal-text {
    font-size: 10px;
  }

  .seal-value {
    font-size: 16px;
  }
}
</style>
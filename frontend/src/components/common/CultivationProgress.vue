<template>
  <div class="cultivation-progress" v-if="show" :title="progressText">
    <div class="progress-seal">
      <span class="progress-value">{{ cultivationPoints }}</span>
      <span class="progress-label">修为</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const show = ref(false)
const cultivationPoints = ref(0)
const visitCount = ref(0)
const lastVisit = ref(null)

const progressText = computed(() => {
  return `今日修为+${cultivationPoints.value} · 第${visitCount.value}次访问`
})

let updateInterval = null

const loadProgress = () => {
  const stored = localStorage.getItem('cultivation_points')
  if (stored) {
    cultivationPoints.value = parseInt(stored)
  }

  const visits = localStorage.getItem('visit_count')
  if (visits) {
    visitCount.value = parseInt(visits)
  }

  // 更新访问次数
  const today = new Date().toDateString()
  const lastVisitDate = localStorage.getItem('last_visit_date')

  if (lastVisitDate !== today) {
    // 新的一天，增加访问次数
    const count = parseInt(localStorage.getItem('visit_count') || '0')
    localStorage.setItem('visit_count', (count + 1).toString())
    localStorage.setItem('last_visit_date', today)
    visitCount.value = count + 1

    // 每天首次访问增加修为
    const points = parseInt(localStorage.getItem('cultivation_points') || '0')
    localStorage.setItem('cultivation_points', (points + 1).toString())
    cultivationPoints.value = points + 1
  }

  show.value = true
}

const addPoints = (amount) => {
  cultivationPoints.value += amount
  localStorage.setItem('cultivation_points', cultivationPoints.value.toString())
}

const trackAction = () => {
  // 每5个动作增加1修为
  const actions = parseInt(localStorage.getItem('action_count') || '0') + 1
  localStorage.setItem('action_count', actions.toString())

  if (actions >= 5) {
    addPoints(1)
    localStorage.setItem('action_count', '0')
  }
}

onMounted(() => {
  loadProgress()

  // 监听用户行为
  document.addEventListener('click', trackAction)
  document.addEventListener('scroll', trackScroll, { passive: true })
})

onUnmounted(() => {
  document.removeEventListener('click', trackAction)
  document.removeEventListener('scroll', trackScroll)
})

const trackScroll = () => {
  // 滚动到底增加修为
  const scrollHeight = document.documentElement.scrollHeight
  const scrollTop = document.documentElement.scrollTop
  const clientHeight = window.innerHeight

  if (scrollTop + clientHeight >= scrollHeight - 50) {
    const scrolled = localStorage.getItem('has_scrolled')
    if (!scrolled) {
      addPoints(1)
      localStorage.setItem('has_scrolled', 'true')
    }
  }
}
</script>

<style scoped>
.cultivation-progress {
  position: fixed;
  bottom: 80px;
  right: 20px;
  z-index: 100;
  cursor: pointer;
}

.progress-seal {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  background: var(--color-bg-elevated);
  border: 2px solid var(--color-gold);
  border-radius: 50%;
  box-shadow: var(--shadow-gold);
  transition: all 0.3s ease;
}

.progress-seal:hover {
  transform: scale(1.1);
  box-shadow: var(--shadow-glow);
}

.progress-value {
  font-family: var(--font-serif);
  font-size: 18px;
  color: var(--color-gold);
  font-weight: 600;
}

.progress-label {
  font-size: 10px;
  color: var(--color-text-secondary);
  letter-spacing: 1px;
}
</style>
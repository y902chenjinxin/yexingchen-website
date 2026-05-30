<template>
  <IslandInnerBase
    type="log"
    title="日志岛 · 墨迹心路"
    subtitle="笔耕不辍，心迹可寻"
    @back="$emit('back')"
  >
    <div class="log-content">
      <!-- 砚台虚影 -->
      <div class="inkstone-bg">
        <svg viewBox="0 0 200 100" class="inkstone-svg">
          <ellipse cx="100" cy="70" rx="80" ry="25" fill="var(--island-log)" opacity="0.1"/>
          <ellipse cx="100" cy="65" rx="60" ry="18" fill="var(--island-log)" opacity="0.15"/>
          <ellipse cx="100" cy="60" rx="40" ry="12" fill="rgba(74, 124, 89, 0.3)"/>
        </svg>
      </div>

      <!-- 墨滴晕染装饰 -->
      <div class="ink-drops">
        <div v-for="i in 5" :key="i" class="ink-spread" :style="getSpreadStyle(i)"></div>
      </div>

      <!-- 日志列表 -->
      <div class="log-list-area">
        <div v-if="logStore.loading" class="loading-state">
          <span class="loading-text">洞天正在铺开竹简...</span>
        </div>
        <div v-else-if="!logStore.items || logStore.items.length === 0" class="empty-state">
          <span class="empty-icon">📝</span>
          <span class="empty-text">暂无墨迹记录，静待心路成文</span>
        </div>
        <div v-else class="log-items">
          <div
            v-for="(item, index) in logStore.items"
            :key="item.id"
            class="log-item"
            :style="getItemStyle(index)"
          >
            <div class="log-date">
              <span class="date-day">{{ formatDay(item.created_at) }}</span>
              <span class="date-month">{{ formatMonth(item.created_at) }}</span>
            </div>
            <div class="log-info">
              <span class="log-title">{{ item.title || '无题' }}</span>
              <span class="log-excerpt">{{ item.content ? item.content.substring(0, 50) + '...' : '暂无内容' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 纸页飘落效果 -->
      <div class="floating-papers">
        <div v-for="i in 6" :key="i" class="paper" :style="getPaperStyle(i)"></div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted } from 'vue'
import IslandInnerBase from './IslandInnerBase.vue'
import { useLogStore } from '@/stores/log'

defineEmits(['back'])

const logStore = useLogStore()

onMounted(async () => {
  await logStore.fetchList()
})

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getSpreadStyle = (i) => {
  const seed = i * 5678.901
  const random = seededRandom(seed)

  return {
    left: `${20 + random * 60}%`,
    top: `${30 + random * 40}%`,
    animationDelay: `${random * 3}s`,
    opacity: 0.1 + random * 0.15
  }
}

const getPaperStyle = (i) => {
  const seed = i * 4567.89
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `-${20 + random * 30}px`,
    width: `${20 + random * 20}px`,
    height: `${30 + random * 30}px`,
    animationDelay: `${random * 10}s`,
    opacity: 0.3 + random * 0.3,
    transform: `rotate(${random * 30 - 15}deg)`
  }
}

const getItemStyle = (index) => {
  const seed = index * 6789.012
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`
  }
}

const formatDay = (dateStr) => {
  if (!dateStr) return '--'
  const date = new Date(dateStr)
  return date.getDate()
}

const formatMonth = (dateStr) => {
  if (!dateStr) return '----'
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}
</script>

<style scoped>
.log-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.inkstone-bg {
  position: absolute;
  bottom: 10%;
  left: 10%;
  width: 200px;
  height: 100px;
  opacity: 0.6;
  pointer-events: none;
}

.inkstone-svg {
  width: 100%;
  height: 100%;
}

.ink-drops {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.ink-spread {
  position: absolute;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(74, 124, 89, 0.3) 0%,
    rgba(122, 155, 124, 0.1) 50%,
    transparent 70%
  );
  animation: ink-expand 6s ease-out infinite;
}

@keyframes ink-expand {
  0% {
    transform: scale(0.5);
    opacity: 0.4;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

.log-list-area {
  background: var(--color-bg-elevated);
  border: 1px solid rgba(122, 155, 124, 0.2);
  border-radius: var(--radius);
  padding: 30px;
  min-height: 300px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
}

.loading-text,
.empty-text {
  color: var(--color-text-muted);
  font-size: 14px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

.log-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.log-item {
  display: flex;
  gap: 24px;
  padding: 20px;
  background: rgba(122, 155, 124, 0.05);
  border: 1px solid rgba(122, 155, 124, 0.15);
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  animation: slide-in 0.5s ease-out backwards;
  cursor: pointer;
}

.log-item:hover {
  background: rgba(122, 155, 124, 0.1);
  border-color: rgba(122, 155, 124, 0.3);
  transform: translateX(8px);
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.log-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  padding: 10px;
  background: rgba(122, 155, 124, 0.1);
  border-radius: var(--radius-sm);
}

.date-day {
  font-family: var(--font-serif);
  font-size: 24px;
  color: var(--island-log);
  line-height: 1;
}

.date-month {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.log-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.log-title {
  font-family: var(--font-serif);
  color: var(--color-text);
  font-size: 16px;
}

.log-excerpt {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.floating-papers {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.paper {
  position: absolute;
  background: rgba(232, 228, 220, 0.9);
  border-radius: 2px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  animation: fall-paper 15s linear infinite;
  will-change: transform, opacity;
}

@keyframes fall-paper {
  0% {
    transform: translateY(0) rotate(var(--rotate, 0deg));
    opacity: 0;
  }
  10% {
    opacity: 0.5;
  }
  90% {
    opacity: 0.5;
  }
  100% {
    transform: translateY(calc(100vh + 100px)) rotate(var(--rotate, 0deg));
    opacity: 0;
  }
}
</style>
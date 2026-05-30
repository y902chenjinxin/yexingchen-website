<template>
  <IslandInnerBase
    type="novel"
    title="小说岛 · 书卷悠长"
    subtitle="卷卷在手，洞悉天机"
    @back="$emit('back')"
  >
    <div class="novel-content">
      <!-- 书页翻飞装饰 -->
      <div class="page-flying">
        <div v-for="i in 4" :key="i" class="flying-page" :style="getPageStyle(i)"></div>
      </div>

      <!-- 墨迹粒子装饰 -->
      <div class="ink-particles">
        <span v-for="i in 10" :key="i" class="ink-particle" :style="getInkStyle(i)">·</span>
      </div>

      <!-- 小说列表 -->
      <div class="novel-list-area">
        <div v-if="novelStore.loading" class="loading-state">
          <span class="loading-text">洞天正在打开书卷...</span>
        </div>
        <div v-else-if="!novelStore.items || novelStore.items.length === 0" class="empty-state">
          <span class="empty-icon">📖</span>
          <span class="empty-text">暂无典籍收录，静待书卷成册</span>
        </div>
        <div v-else class="novel-items">
          <div
            v-for="(item, index) in novelStore.items"
            :key="item.id"
            class="novel-item"
            :style="getItemStyle(index)"
          >
            <div class="novel-cover">
              <span class="cover-icon">📜</span>
            </div>
            <div class="novel-info">
              <span class="novel-title">{{ item.title || '无题' }}</span>
              <span class="novel-author">{{ item.author || '佚名' }}</span>
              <span class="novel-chapter">第{{ item.chapter || 1 }}章</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 墨迹飘散效果 -->
      <div class="floating-ink">
        <span v-for="i in 8" :key="i" class="ink-drop" :style="getInkDropStyle(i)">●</span>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted } from 'vue'
import IslandInnerBase from './IslandInnerBase.vue'
import { useNovelStore } from '@/stores/novel'

defineEmits(['back'])

const novelStore = useNovelStore()

onMounted(async () => {
  await novelStore.fetchList()
})

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getPageStyle = (i) => {
  const seed = i * 2345.6789
  const random = seededRandom(seed)

  return {
    left: `${10 + random * 60}%`,
    top: `${10 + random * 40}%`,
    animationDelay: `${random * 3}s`,
    transform: `rotate(${random * 60 - 30}deg)`,
    opacity: 0.1 + random * 0.15
  }
}

const getInkStyle = (i) => {
  const seed = i * 3456.789
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${random * 100}%`,
    animationDelay: `${random * 4}s`,
    fontSize: `${8 + random * 16}px`,
    color: `var(--island-novel)`
  }
}

const getInkDropStyle = (i) => {
  const seed = i * 4567.89
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${10 + seededRandom(seed * 2) * 60}%`,
    animationDelay: `${random * 8}s`,
    opacity: 0.2 + random * 0.3,
    fontSize: `${8 + random * 12}px`,
    color: `var(--island-novel)`
  }
}

const getItemStyle = (index) => {
  const seed = index * 5678.901
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`
  }
}
</script>

<style scoped>
.novel-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.page-flying {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.flying-page {
  position: absolute;
  width: 40px;
  height: 50px;
  background: linear-gradient(
    135deg,
    var(--island-novel) 0%,
    rgba(232, 228, 220, 0.3) 100%
  );
  border-radius: 2px;
  animation: page-fly 15s linear infinite;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

@keyframes page-fly {
  0% {
    transform: translateY(-100px) rotate(0deg);
    opacity: 0;
  }
  10% {
    opacity: 0.6;
  }
  90% {
    opacity: 0.6;
  }
  100% {
    transform: translateY(calc(100vh + 100px)) rotate(360deg);
    opacity: 0;
  }
}

.ink-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.ink-particle {
  position: absolute;
  animation: float-particle 8s ease-in-out infinite;
}

@keyframes float-particle {
  0%, 100% {
    transform: translateY(0) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translateY(-20px) scale(1.2);
    opacity: 0.6;
  }
}

.novel-list-area {
  background: var(--color-bg-elevated);
  border: 1px solid rgba(212, 196, 168, 0.2);
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

.novel-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.novel-item {
  display: flex;
  gap: 20px;
  padding: 20px;
  background: rgba(212, 196, 168, 0.05);
  border: 1px solid rgba(212, 196, 168, 0.15);
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  animation: slide-in 0.5s ease-out backwards;
}

.novel-item:hover {
  background: rgba(212, 196, 168, 0.1);
  border-color: rgba(212, 196, 168, 0.3);
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

.novel-cover {
  width: 60px;
  height: 80px;
  background: linear-gradient(
    135deg,
    var(--island-novel) 0%,
    rgba(212, 196, 168, 0.5) 100%
  );
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cover-icon {
  font-size: 28px;
  opacity: 0.7;
}

.novel-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.novel-title {
  font-family: var(--font-serif);
  color: var(--color-text);
  font-size: 16px;
}

.novel-author,
.novel-chapter {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.floating-ink {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.ink-drop {
  position: absolute;
  animation: float-ink 12s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes float-ink {
  0%, 100% {
    transform: translateY(0) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translateY(-30px) scale(1.2);
    opacity: 0.6;
  }
}
</style>
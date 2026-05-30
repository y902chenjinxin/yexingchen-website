<template>
  <IslandInnerBase
    type="music"
    title="音乐岛 · 音律飘渺"
    subtitle="天籁之音，洗涤尘心"
    @back="$emit('back')"
  >
    <div class="music-content">
      <!-- 古琴虚影背景 -->
      <div class="guqin-bg">
        <svg viewBox="0 0 400 100" class="guqin-svg">
          <ellipse cx="200" cy="80" rx="180" ry="20" fill="none" stroke="var(--island-music)" stroke-width="1" opacity="0.2"/>
          <ellipse cx="200" cy="80" rx="150" ry="15" fill="none" stroke="var(--island-music)" stroke-width="0.5" opacity="0.15"/>
          <line v-for="i in 7" :key="i" :x1="100 + i * 28" y1="30" :x2="100 + i * 28" y2="130" stroke="var(--island-music)" stroke-width="0.5" opacity="0.3"/>
        </svg>
      </div>

      <!-- 音符飘带装饰 -->
      <div class="music-ribbon">
        <svg viewBox="0 0 200 300" class="ribbon-svg">
          <path d="M20 0 Q60 80 100 150 T180 300" fill="none" stroke="var(--island-music)" stroke-width="2" opacity="0.2" stroke-dasharray="5,5">
            <animate attributeName="stroke-dashoffset" from="0" to="30" dur="3s" repeatCount="indefinite"/>
          </path>
          <circle v-for="i in 5" :key="i" r="4" fill="var(--island-music)" :cx="20 + i * 35" :cy="i * 60" opacity="0.3">
            <animate attributeName="cy" values="0;280;0" :dur="`${4 + i * 0.5}s`" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>

      <!-- 音乐列表 -->
      <div class="music-list-area">
        <div v-if="musicStore.loading" class="loading-state">
          <span class="loading-text">洞天正在加载天籁之音...</span>
        </div>
        <div v-else-if="!musicStore.items || musicStore.items.length === 0" class="empty-state">
          <span class="empty-icon">🎵</span>
          <span class="empty-text">暂无音乐收录，静待仙音降临</span>
        </div>
        <div v-else class="music-items">
          <div
            v-for="(item, index) in musicStore.items"
            :key="item.id"
            class="music-item"
            :style="getItemStyle(index)"
          >
            <div class="music-info">
              <span class="music-name">{{ item.name || '未知曲目' }}</span>
              <span class="music-artist">{{ item.artist || '佚名' }}</span>
            </div>
            <div class="music-actions">
              <button class="play-btn" @click="handlePlay(item)">▶</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 音符飘舞效果 -->
      <div class="floating-notes">
        <span v-for="i in 12" :key="i" class="note" :style="getNoteStyle(i)">♪</span>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted } from 'vue'
import IslandInnerBase from './IslandInnerBase.vue'
import { useMusicStore } from '@/stores/music'

defineEmits(['back'])

const musicStore = useMusicStore()

onMounted(async () => {
  await musicStore.fetchList()
})

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getNoteStyle = (i) => {
  const seed = i * 1234.5678
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${10 + seededRandom(seed * 2) * 60}%`,
    animationDelay: `${random * 5}s`,
    opacity: 0.3 + random * 0.4,
    fontSize: `${16 + random * 16}px`
  }
}

const getItemStyle = (index) => {
  const seed = index * 9876.5432
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`,
    '--item-hue': `${random * 30}deg`
  }
}

const handlePlay = (item) => {
  console.log('Playing:', item.name)
}
</script>

<style scoped>
.music-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.guqin-bg {
  position: absolute;
  top: 20%;
  left: 5%;
  width: 300px;
  height: 150px;
  opacity: 0.6;
  pointer-events: none;
}

.guqin-svg {
  width: 100%;
  height: 100%;
}

.music-ribbon {
  position: absolute;
  top: 0;
  right: 10%;
  width: 150px;
  height: 250px;
  opacity: 0.5;
  pointer-events: none;
}

.ribbon-svg {
  width: 100%;
  height: 100%;
}

.music-list-area {
  background: var(--color-bg-elevated);
  border: 1px solid rgba(155, 141, 201, 0.2);
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

.music-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.music-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(155, 141, 201, 0.05);
  border: 1px solid rgba(155, 141, 201, 0.15);
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  animation: slide-in 0.5s ease-out backwards;
}

.music-item:hover {
  background: rgba(155, 141, 201, 0.1);
  border-color: rgba(155, 141, 201, 0.3);
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

.music-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.music-name {
  font-family: var(--font-serif);
  color: var(--color-text);
  font-size: 16px;
}

.music-artist {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.music-actions {
  display: flex;
  gap: 12px;
}

.play-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--island-music);
  border: none;
  color: var(--color-bg);
  cursor: pointer;
  transition: all var(--transition);
  font-size: 14px;
}

.play-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 0 15px var(--island-music);
}

.floating-notes {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.note {
  position: absolute;
  color: var(--island-music);
  animation: float-note 10s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes float-note {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
    opacity: 0.3;
  }
  50% {
    transform: translateY(-50px) rotate(15deg);
    opacity: 0.7;
  }
}
</style>
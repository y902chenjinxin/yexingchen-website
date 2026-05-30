<template>
  <IslandInnerBase
    type="video"
    title="视频岛 · 光影流转"
    subtitle="洞见万象，影像千秋"
    @back="$emit('back')"
  >
    <div class="video-content">
      <!-- 镜头光圈装饰 -->
      <div class="lens-aperture">
        <div class="aperture-ring" v-for="i in 4" :key="i"></div>
      </div>

      <!-- 胶片飘带 -->
      <div class="film-ribbon">
        <div v-for="i in 6" :key="i" class="film-frame" :style="getFrameStyle(i)"></div>
      </div>

      <!-- 视频列表 -->
      <div class="video-list-area">
        <div v-if="videoStore.loading" class="loading-state">
          <span class="loading-text">洞天正在加载光影...</span>
        </div>
        <div v-else-if="!videoStore.items || videoStore.items.length === 0" class="empty-state">
          <span class="empty-icon">🎬</span>
          <span class="empty-text">暂无影像收录，静待光影凝固</span>
        </div>
        <div v-else class="video-items">
          <div
            v-for="(item, index) in videoStore.items"
            :key="item.id"
            class="video-item"
            :style="getItemStyle(index)"
          >
            <div class="video-thumbnail">
              <span class="play-icon">▶</span>
            </div>
            <div class="video-info">
              <span class="video-title">{{ item.title || '无题' }}</span>
              <span class="video-duration">{{ item.duration || '00:00' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 光圈飘动效果 -->
      <div class="floating-apertures">
        <div v-for="i in 6" :key="i" class="aperture" :style="getApertureStyle(i)"></div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted } from 'vue'
import IslandInnerBase from './IslandInnerBase.vue'
import { useVideoStore } from '@/stores/video'

defineEmits(['back'])

const videoStore = useVideoStore()

onMounted(async () => {
  await videoStore.fetchList()
})

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getFrameStyle = (i) => {
  const seed = i * 7890.1234
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 2}s`,
    opacity: 0.2 + random * 0.3
  }
}

const getApertureStyle = (i) => {
  const seed = i * 3456.789
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${10 + seededRandom(seed * 2) * 60}%`,
    width: `${40 + random * 60}px`,
    height: `${40 + random * 60}px`,
    animationDelay: `${random * 6}s`,
    opacity: 0.1 + random * 0.2,
    borderRadius: '50%',
    border: `2px solid var(--island-video)`,
    boxShadow: `0 0 ${10 + random * 20}px var(--island-video)`
  }
}

const getItemStyle = (index) => {
  const seed = index * 8901.234
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`
  }
}
</script>

<style scoped>
.video-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.lens-aperture {
  position: absolute;
  top: 15%;
  right: 10%;
  width: 150px;
  height: 150px;
  pointer-events: none;
}

.aperture-ring {
  position: absolute;
  inset: 0;
  border: 2px solid var(--island-video);
  border-radius: 50%;
  opacity: 0.15;
  animation: aperture-pulse 4s ease-in-out infinite;
}

.aperture-ring:nth-child(1) { inset: 0; animation-delay: 0s; }
.aperture-ring:nth-child(2) { inset: 20px; animation-delay: 0.5s; }
.aperture-ring:nth-child(3) { inset: 40px; animation-delay: 1s; }
.aperture-ring:nth-child(4) { inset: 60px; animation-delay: 1.5s; }

@keyframes aperture-pulse {
  0%, 100% { opacity: 0.1; transform: scale(1); }
  50% { opacity: 0.25; transform: scale(1.05); }
}

.film-ribbon {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  gap: 20px;
  padding: 20px 40px;
  pointer-events: none;
  overflow: hidden;
}

.film-frame {
  width: 60px;
  height: 80px;
  background: linear-gradient(
    135deg,
    var(--island-video) 0%,
    rgba(168, 124, 156, 0.3) 100%
  );
  border-radius: 4px;
  animation: ribbon-drift 20s linear infinite;
  flex-shrink: 0;
}

@keyframes ribbon-drift {
  from { transform: translateX(-100px); opacity: 0; }
  10% { opacity: 0.5; }
  90% { opacity: 0.5; }
  to { transform: translateX(calc(100vw + 100px)); opacity: 0; }
}

.video-list-area {
  background: var(--color-bg-elevated);
  border: 1px solid rgba(168, 124, 156, 0.2);
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

.video-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.video-item {
  display: flex;
  gap: 20px;
  padding: 16px;
  background: rgba(168, 124, 156, 0.05);
  border: 1px solid rgba(168, 124, 156, 0.15);
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  animation: slide-in 0.5s ease-out backwards;
  cursor: pointer;
}

.video-item:hover {
  background: rgba(168, 124, 156, 0.1);
  border-color: rgba(168, 124, 156, 0.3);
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

.video-thumbnail {
  width: 100px;
  height: 70px;
  background: linear-gradient(
    135deg,
    var(--island-video) 0%,
    rgba(168, 124, 156, 0.3) 100%
  );
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.play-icon {
  font-size: 24px;
  color: var(--color-bg);
  opacity: 0.8;
}

.video-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}

.video-title {
  font-family: var(--font-serif);
  color: var(--color-text);
  font-size: 16px;
}

.video-duration {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.floating-apertures {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.aperture {
  position: absolute;
  animation: float-aperture 10s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes float-aperture {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
    opacity: 0.2;
  }
  50% {
    transform: translateY(-40px) rotate(180deg);
    opacity: 0.5;
  }
}
</style>
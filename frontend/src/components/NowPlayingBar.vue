<template>
  <transition name="npbar">
    <div v-if="player.shows && player.curItem" class="npbar" ref="barRef">
      <!-- 曲目信息 -->
      <div class="np-info">
        <div class="np-cover">
          <span class="np-note">♪</span>
          <span class="np-badge" :class="{ live: player.isPlaying }"></span>
        </div>
        <div class="np-meta">
          <span class="np-title">{{ player.curItem.title || '未知曲目' }}</span>
          <span class="np-artist">{{ player.curItem.artist || '佚名' }}</span>
        </div>
      </div>

      <!-- 播放/暂停 -->
      <button class="np-btn np-toggle" @click="player.togglePlay()" :title="player.isPlaying ? '暂停' : '播放'" aria-label="播放切换">
        <el-icon><VideoPause v-if="player.isPlaying" /><VideoPlay v-else /></el-icon>
      </button>

      <!-- 进度条 -->
      <div class="np-progress">
        <span class="np-time">{{ fmt(player.progress) }}</span>
        <input
          type="range"
          class="np-range"
          :value="ratio"
          min="0" max="1" step="0.001"
          :disabled="!player.duration"
          @input="onSeek"
          aria-label="播放进度"
        />
        <span class="np-time">{{ fmt(player.duration) }}</span>
      </div>

      <!-- 音量 -->
      <div class="np-volume">
        <button class="np-btn" @click="player.toggleMute()" :title="player.volume > 0 ? '静音' : '恢复音量'" aria-label="静音">
          <svg v-if="player.volume > 0" viewBox="0 0 24 24" class="np-vol-ic" aria-hidden="true"><path d="M3 10v4h4l5 5V5l-5 5H3z"/><path d="M16 8a5 5 0 0 1 0 8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          <svg v-else viewBox="0 0 24 24" class="np-vol-ic" aria-hidden="true"><path d="M3 10v4h4l5 5V5l-5 5H3z"/><path d="M16 9l5 6M21 9l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <input
          type="range"
          class="np-range np-vol"
          v-model.number="volProxy"
          min="0" max="1" step="0.01"
          @input="onVolume"
          aria-label="音量"
        />
      </div>

      <!-- 关闭 -->
      <button class="np-btn np-close" @click="player.stopAndHide()" title="关闭播放" aria-label="关闭">
        <svg viewBox="0 0 24 24" class="np-vol-ic" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import { VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { usePlayerStore } from '@/stores/player'

const player = usePlayerStore()
const barRef = ref(null)

const ratio = computed(() => (player.duration ? player.progress / player.duration : 0))
const volProxy = ref(player.volume)

function onSeek(e) {
  player.seekByRatio(Number(e.target.value))
}

function onVolume() {
  player.setVolume(volProxy.value)
}

function fmt(sec) {
  if (!Number.isFinite(sec) || sec <= 0) return '00:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
.npbar {
  position: fixed;
  bottom: 16px;
  left: 16px;
  width: calc(100% - 320px);
  max-width: 1080px;
  height: 62px;
  z-index: 980;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 18px 0 14px;
  border-radius: 18px;
  background: linear-gradient(160deg, rgba(28, 36, 48, 0.92), rgba(20, 26, 38, 0.9));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  -webkit-backdrop-filter: saturate(150%) blur(14px);
  backdrop-filter: saturate(150%) blur(14px);
  box-sizing: border-box;
}

/* 进入/退出过渡 */
.npbar-enter-active, .npbar-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.npbar-enter-from, .npbar-leave-to { opacity: 0; transform: translateY(24px); }

.np-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 0 1 auto;
}

.np-cover {
  position: relative;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(140deg, rgba(122, 172, 210, 0.5), rgba(76, 110, 160, 0.4));
  color: rgba(224, 238, 255, 0.9);
}

.np-note { font-size: 22px; }

.np-badge {
  position: absolute;
  top: -3px; right: -3px;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: #6b7280;
  border: 2px solid #141a26;
}
.np-badge.live {
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.7);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

.np-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  max-width: 200px;
}
.np-title {
  font-family: var(--font-serif, serif);
  font-size: 14px;
  color: #e9eef5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.np-artist {
  font-size: 12px;
  color: rgba(200, 210, 224, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.np-btn {
  width: 36px; height: 36px;
  flex-shrink: 0;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  color: #dbe3ee;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.np-btn:hover { background: rgba(255, 255, 255, 0.14); color: #fff; transform: scale(1.05); }
.np-toggle { background: linear-gradient(140deg, #3d7fd6, #2a5fa8); color: #fff; }
.np-toggle:hover { background: linear-gradient(140deg, #4b8ce0, #326ab8); }
.np-close { background: transparent; }
.np-close:hover { background: rgba(239, 68, 68, 0.18); color: #f87171; }

.np-progress {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 120px;
}

.np-time {
  font-size: 12px;
  color: rgba(190, 200, 214, 0.65);
  font-variant-numeric: tabular-nums;
  min-width: 38px;
  text-align: center;
}
.np-time:first-child { text-align: right; }

.np-range {
  -webkit-appearance: none;
  appearance: none;
  flex: 1;
  height: 4px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.16);
  outline: none;
  cursor: pointer;
}
.np-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: #dfe8f4;
  border: none;
  box-shadow: 0 1px 4px rgba(0,0,0,.4);
  transition: transform .15s;
}
.np-range::-webkit-slider-thumb:hover { transform: scale(1.25); }
.np-range::-moz-range-thumb {
  width: 12px; height: 12px;
  border-radius: 50%;
  background: #dfe8f4;
  border: none;
}
.np-range:disabled { opacity: 0.4; cursor: default; }

.np-vol-ic { width: 18px; height: 18px; fill: currentColor; }

.np-volume {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.np-vol { width: 80px; }

@media (max-width: 768px) {
  .npbar {
    width: calc(100% - 20px);
    left: 10px;
  }
  .np-volume { display: none; }
  .np-meta { max-width: 110px; }
}
</style>
<template>
  <transition name="npbar">
    <div v-if="player.shows && player.curItem" class="npbar" ref="barRef">
      <!-- 曲目信息（点击展开全屏播放器，仅移动端生效） -->
      <div class="np-info" @click="onInfoClick">
        <div class="np-cover">
          <span class="np-note">♪</span>
          <span class="np-badge" :class="{ live: player.isPlaying }"></span>
        </div>
        <div class="np-meta">
          <span class="np-title">{{ player.curItem.title || '未知曲目' }}</span>
          <span class="np-artist">
            {{ player.curItem.artist || '佚名' }}
            <span v-if="player.queue.length > 1" class="np-qmeta">{{ player.queueIndex + 1 }}/{{ player.queue.length }}</span>
          </span>
        </div>
      </div>

      <!-- 上一首 -->
      <button class="np-btn np-step" :disabled="player.queue.length < 2" @click="player.prev()" title="上一首" aria-label="上一首">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h2v14H6zM20 5v14L9 12z" fill="currentColor"/></svg>
      </button>
      <!-- 播放/暂停 -->
      <button class="np-btn np-toggle" @click="player.togglePlay()" :title="player.isPlaying ? '暂停' : '播放'" aria-label="播放切换">
        <el-icon><VideoPause v-if="player.isPlaying" /><VideoPlay v-else /></el-icon>
      </button>
      <!-- 下一首 -->
      <button class="np-btn np-step" :disabled="player.queue.length < 2" @click="player.next()" title="下一首" aria-label="下一首">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 5h2v14h-2zM4 5v14l11-7z" fill="currentColor"/></svg>
      </button>
      <!-- 播放模式切换 -->
      <button class="np-btn np-mode" @click="player.cyclePlayMode()" :title="modeTitle" :aria-label="`播放模式：${modeTitle}`">
        <svg v-if="player.playMode === 'list'" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 7h10M7 12h10M7 17h10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M17.5 7l2.2-2.2M19.7 4.8v2.2M17.5 17l2.2 2.2M19.7 19.2v-2.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
        <svg v-else-if="player.playMode === 'single'" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 7h10M7 12h7M7 17h7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          <circle cx="17.5" cy="12.5" r="2.6" fill="none" stroke="currentColor" stroke-width="1.6"/>
          <path d="M5 5l14 7-14 7z" fill="currentColor" opacity=".55"/>
        </svg>
        <svg v-else-if="player.playMode === 'shuffle'" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M16 4h4v4M20 4l-7 7M16 20h4v-4M20 20l-7-7M4 4l16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 5v14l11-7z" fill="currentColor"/>
          <path d="M5 5h2v14H5z" fill="currentColor"/>
        </svg>
        <span class="np-mode-label">{{ modeShort }}</span>
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
const emit = defineEmits(['open-full'])

const isTouchDevice = typeof window !== 'undefined' &&
  window.matchMedia('(pointer: coarse)').matches

function onInfoClick() {
  if (!isTouchDevice) return
  emit('open-full')
}

const ratio = computed(() => (player.duration ? player.progress / player.duration : 0))
const volProxy = ref(player.volume)

const MODE_LABEL = {
  list: { short: '列表', title: '列表循环（点击切换模式）' },
  single: { short: '单曲', title: '单曲循环（点击切换模式）' },
  shuffle: { short: '随机', title: '随机播放（点击切换模式）' },
  once: { short: '一次', title: '单曲一次（点击切换模式）' },
}
const modeShort = computed(() => MODE_LABEL[player.playMode]?.short || '列表')
const modeTitle = computed(() => MODE_LABEL[player.playMode]?.title || '列表循环')

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
.np-btn:disabled { opacity: 0.32; cursor: not-allowed; transform: none; }
.np-toggle { background: linear-gradient(140deg, #3d7fd6, #2a5fa8); color: #fff; }
.np-toggle:hover { background: linear-gradient(140deg, #4b8ce0, #326ab8); }
.np-step { background: rgba(255, 255, 255, 0.05); width: 32px; height: 32px; }
.np-step svg { width: 16px; height: 16px; }
.np-mode {
  display: inline-flex; align-items: center; gap: 4px;
  width: auto; height: 32px; padding: 0 10px; border-radius: 16px;
  background: rgba(255, 255, 255, 0.05); font-size: 12px;
}
.np-mode svg { width: 16px; height: 16px; }
.np-mode-label { line-height: 1; letter-spacing: .04em; }
.np-mode:hover { background: rgba(255, 255, 255, 0.12); }
.np-close { background: transparent; }
.np-close:hover { background: rgba(239, 68, 68, 0.18); color: #f87171; }
.np-qmeta {
  margin-left: 8px;
  font-size: 11px;
  color: rgba(200, 215, 230, 0.55);
  font-variant-numeric: tabular-nums;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
}

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
    bottom: calc(16px + var(--safe-bottom));
  }
  .np-volume { display: none; }
  .np-meta { max-width: 110px; }
}
</style>
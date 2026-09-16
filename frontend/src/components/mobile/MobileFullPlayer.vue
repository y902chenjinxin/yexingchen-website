<template>
  <transition name="mfp">
    <div v-if="visible" class="mfp" @click.self="close">
      <div class="mfp-sheet" role="dialog" aria-modal="true" aria-label="全屏播放器">
        <!-- 顶部：下拉关闭 + 标题 -->
        <div class="mfp-handle"></div>
        <header class="mfp-nav">
          <span class="mfp-title">{{ modeLabel }}</span>
          <button class="mfp-close" @click="close" aria-label="关闭播放器">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </header>

        <!-- 封面旋钮 -->
        <div class="mfp-art" :class="{ spin: player.isPlaying }">
          <div class="mfp-art-inner">
            <span class="mfp-note" aria-hidden="true">♪</span>
            <div class="mfp-art-glint"></div>
          </div>
        </div>
        <!-- 加载态（无曲目） -->
        <div v-if="!player.curItem" class="mfp-empty">暂无播放内容</div>

        <!-- 曲目信息 -->
        <div class="mfp-meta">
          <h2 class="mfp-track">{{ player.curItem?.title || '未知曲目' }}</h2>
          <p class="mfp-artist">{{ player.curItem?.artist || '佚名' }}</p>
        </div>

        <!-- 进度 -->
        <div class="mfp-progress">
          <input
            v-if="player.duration"
            type="range" class="mfp-range"
            :value="ratio" min="0" max="1" step="0.001"
            :style="{ '--fill': (ratio * 100) + '%' }"
            @input="onSeek"
            aria-label="播放进度"
          />
          <div class="mfp-times">
            <span>{{ fmt(player.progress) }}</span>
            <span>{{ fmt(player.duration) }}</span>
          </div>
        </div>

        <!-- 控制组 -->
        <div class="mfp-controls">
          <button class="mfp-btn" @click="player.toggleMute()" :aria-label="player.volume > 0 ? '静音' : '恢复音量'">
            <svg v-if="player.volume > 0" viewBox="0 0 24 24" class="mfp-ic" aria-hidden="true"><path d="M3 10v4h4l5 5V5l-5 5H3z"/></svg>
            <svg v-else viewBox="0 0 24 24" class="mfp-ic" aria-hidden="true"><path d="M3 10v4h4l5 5V5l-5 5H3z"/><path d="M16 9l5 6M21 9l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
          <button class="mfp-btn mfp-main" @click="player.togglePlay()" :aria-label="player.isPlaying ? '暂停' : '播放'">
            <svg v-if="!player.isPlaying" viewBox="0 0 24 24" class="mfp-ic mfp-react" aria-hidden="true"><path d="M7 5v14l12-7z"/></svg>
            <svg v-else viewBox="0 0 24 24" class="mfp-pause" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1.2"/><rect x="14" y="5" width="4" height="14" rx="1.2"/></svg>
          </button>
          <button class="mfp-btn" @click="player.stopAndHide()" aria-label="停止并关闭">
            <svg viewBox="0 0 24 24" class="mfp-stop" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="1.5"/></svg>
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import { usePlayerStore } from '@/stores/player'

const player = usePlayerStore()

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const modeLabel = computed(() => {
  if (player.mode === 'bgm') return '背景 · 天籁'
  return '点播 · 宫商'
})

function close() {
  emit('update:modelValue', false)
}

const ratio = computed(() => (player.duration ? player.progress / player.duration : 0))
function onSeek(e) { player.seekByRatio(Number(e.target.value)) }

function fmt(sec) {
  if (!Number.isFinite(sec) || sec <= 0) return '00:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
.mfp {
  position: fixed; inset: 0;
  z-index: 2000;
  background: linear-gradient(180deg, rgba(10,16,14,.55), rgba(6,10,9,.85));
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  display: flex; align-items: flex-end; justify-content: center;
}
.mfp-sheet {
  width: 100%;
  height: 88vh;
  border-radius: 26px 26px 0 0;
  background: linear-gradient(180deg, rgba(26,36,44,.96), rgba(16,24,32,.98));
  -webkit-backdrop-filter: saturate(160%) blur(24px);
  backdrop-filter: saturate(160%) blur(24px);
  border-top: 1px solid rgba(255,255,255,.1);
  box-shadow: 0 -30px 70px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.07);
  padding: 10px 26px calc(40px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
  display: flex; flex-direction: column;
  align-items: center;
}
.mfp-handle {
  width: 44px; height: 5px; border-radius: 999px;
  background: rgba(255,255,255,.22); margin: 2px auto 10px; flex: none;
}
.mfp-nav {
  width: 100%; display: flex; align-items: center; justify-content: center; position: relative;
  flex: none;
  margin-bottom: 12px;
}
.mfp-title { font-size: 13px; letter-spacing: .18em; color: rgba(210,225,235,.6); }
.mfp-close {
  position: absolute; right: 0; top: 50%; transform: translateY(-50%);
  width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; background: rgba(255,255,255,.07); color: #dbe3ee; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.mfp-close svg { width: 18px; height: 18px; }
.mfp-close:active { transform: translateY(-50%) scale(.9); }

/* 封面旋钮 */
.mfp-art {
  position: relative;
  width: min(62vw, 260px); height: min(62vw, 260px);
  margin: 6vh 0 24px; flex: none;
  border-radius: 50%;
  background: radial-gradient(circle at 32% 26%, rgba(255,255,255,.2), transparent 46%),
    conic-gradient(from 20deg, #3a5b6e, #2c4a5c, #3d6a7a, #2f4f62, #3a5b6e);
  border: 1px solid rgba(255,255,255,.14);
  box-shadow: 0 30px 60px rgba(0,0,0,.4), inset 0 0 40px rgba(0,0,0,.3), inset 0 2px 0 rgba(255,255,255,.2);
  display: flex; align-items: center; justify-content: center;
}
.mfp-art.spin { animation: mfpSpin 14s linear infinite; }
@keyframes mfpSpin { from { transform: rotate(0) } to { transform: rotate(360deg) } }
.mfp-art-inner {
  position: relative; width: 46%; height: 46%; border-radius: 50%;
  background: linear-gradient(160deg, #101a1c, #0a1214);
  border: 2px solid rgba(255,255,255,.18);
  display: flex; align-items: center; justify-content: center;
}
.mfp-note { font-size: 30px; color: rgba(224,238,255,.85); }
.mfp-art-glint {
  position: absolute; inset: 0; border-radius: 50%; pointer-events: none;
  background: linear-gradient(135deg, transparent 42%, rgba(255,255,255,.14) 50%, transparent 58%);
}

.mfp-empty { flex: none; margin: -8px 0 16px; font-size: 13px; color: rgba(200,215,220,.5); }

.mfp-meta { text-align: center; flex: none; }
.mfp-track {
  margin: 0; font-size: 22px; font-weight: 700; color: #eef3f8;
  max-width: 86vw; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.mfp-artist { margin: 6px 0 0; font-size: 14px; color: rgba(200,215,220,.6); }

.mfp-progress { width: 100%; flex: none; margin-top: 26px; }
.mfp-range {
  -webkit-appearance: none; appearance: none;
  width: 100%; height: 5px; border-radius: 5px;
  background: rgba(255,255,255,.16); outline: none; cursor: pointer;
  background-image: linear-gradient(90deg, #e0a26b var(--fill,0%), transparent var(--fill,0%));
}
.mfp-range::-webkit-slider-thumb {
  -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
  background: #ffd9a8; border: none; box-shadow: 0 1px 5px rgba(0,0,0,.4);
}
.mfp-times {
  display: flex; justify-content: space-between; margin-top: 8px;
  font-size: 12px; color: rgba(200,215,220,.55); font-variant-numeric: tabular-nums;
}

.mfp-controls {
  display: flex; align-items: center; gap: 36px; margin-top: auto; flex: none;
  padding-bottom: 18px;
}
.mfp-btn {
  width: 56px; height: 56px; border: none; border-radius: 50%;
  background: rgba(255,255,255,.08); color: #dbe3ee;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  -webkit-tap-highlight-color: transparent; transition: transform .18s, background .2s;
}
.mfp-btn:active { transform: scale(.9); background: rgba(255,255,255,.14); }
.mfp-main {
  width: 76px; height: 76px;
  background: linear-gradient(140deg, #e0a26b, #c96b58);
  box-shadow: 0 14px 30px rgba(201,107,88,.4), inset 0 2px 0 rgba(255,255,255,.28);
}
.mfp-main:active { transform: scale(.92); }
.mfp-ic { width: 24px; height: 24px; fill: currentColor; }
.mfp-react { width: 28px; height: 28px; margin-left: 3px; fill: #fff; }
.mfp-pause { width: 28px; height: 28px; fill: #fff; }
.mfp-stop { width: 26px; height: 26px; fill: currentColor; }

@media (prefers-reduced-motion: reduce) {
  .mfp-art.spin { animation: none; }
  .mfp * { transition: none !important; }
}

.mfp-enter-active, .mfp-leave-active { transition: opacity .32s ease; }
.mfp-enter-from, .mfp-leave-to { opacity: 0; }
</style>
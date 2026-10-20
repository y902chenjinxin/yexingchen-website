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

        <!-- 中段：封面 / 曲目信息 / 进度。空间不足时只滚动这一段，
             底部控制键永远钉在屏幕内，避免上一首/下一首被挤出可视区 -->
        <div class="mfp-body">
          <!-- 封面旋钮 -->
          <div class="mfp-art" :class="{ spin: player.isPlaying }">
            <div class="mfp-art-inner">
              <span class="mfp-note" aria-hidden="true"><AppIcon icon="♪" :size="30" /></span>
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
        </div>

        <!-- 控制组 -->
        <div class="mfp-controls">
          <button class="mfp-btn mfp-step" :disabled="player.queue.length < 2" @click="player.prev()" aria-label="上一首">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h2v14H6zM20 5v14L9 12z" fill="currentColor"/></svg>
          </button>
          <button class="mfp-btn mfp-main" @click="player.togglePlay()" :aria-label="player.isPlaying ? '暂停' : '播放'">
            <svg v-if="!player.isPlaying" viewBox="0 0 24 24" class="mfp-ic mfp-react" aria-hidden="true"><path d="M7 5v14l12-7z"/></svg>
            <svg v-else viewBox="0 0 24 24" class="mfp-pause" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1.2"/><rect x="14" y="5" width="4" height="14" rx="1.2"/></svg>
          </button>
          <button class="mfp-btn mfp-step" :disabled="player.queue.length < 2" @click="player.next()" aria-label="下一首">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 5h2v14h-2zM4 5v14l11-7z" fill="currentColor"/></svg>
          </button>
        </div>

        <!-- 第二排：模式（下拉）/ 静音 / 关闭 -->
        <div class="mfp-controls-2">
          <div class="mfp-mode-wrap" v-click-outside="closeModeMenu">
            <button
              class="mfp-mode"
              @click="toggleModeMenu"
              :title="modeTitle"
              :aria-label="`播放模式：${modeTitle}，点击选择`"
              aria-haspopup="listbox"
              :aria-expanded="modeMenuOpen"
            >
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
              <span class="mfp-mode-label">{{ modeShort }}</span>
            </button>
            <transition name="mfpmenu">
              <ul v-if="modeMenuOpen" class="mfp-mode-menu" role="listbox" aria-label="选择播放模式">
                <li
                  v-for="m in player.PLAY_MODES"
                  :key="m"
                  role="option"
                  :aria-selected="player.playMode === m"
                  :class="{ active: player.playMode === m }"
                  @click="pickMode(m)"
                >
                  <span class="mfpmenu-ic">
                    <svg v-if="m === 'list'" viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M7 7h10M7 12h10M7 17h10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                      <path d="M17.5 7l2.2-2.2M19.7 4.8v2.2M17.5 17l2.2 2.2M19.7 19.2v-2.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                    </svg>
                    <svg v-else-if="m === 'single'" viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M7 7h10M7 12h7M7 17h7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                      <circle cx="17.5" cy="12.5" r="2.6" fill="none" stroke="currentColor" stroke-width="1.6"/>
                      <path d="M5 5l14 7-14 7z" fill="currentColor" opacity=".55"/>
                    </svg>
                    <svg v-else-if="m === 'shuffle'" viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M16 4h4v4M20 4l-7 7M16 20h4v-4M20 20l-7-7M4 4l16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M7 5v14l11-7z" fill="currentColor"/>
                      <path d="M5 5h2v14H5z" fill="currentColor"/>
                    </svg>
                  </span>
                  <span class="mfpmenu-text">{{ MODE_LABEL[m].title }}</span>
                  <svg v-if="player.playMode === m" class="mfpmenu-check" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M5 12l4 4 10-10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </li>
              </ul>
            </transition>
          </div>
          <button class="mfp-btn mfp-side" @click="player.toggleMute()" :aria-label="player.volume > 0 ? '静音' : '恢复音量'">
            <svg v-if="player.volume > 0" viewBox="0 0 24 24" class="mfp-ic" aria-hidden="true"><path d="M3 10v4h4l5 5V5l-5 5H3z"/></svg>
            <svg v-else viewBox="0 0 24 24" class="mfp-ic" aria-hidden="true"><path d="M3 10v4h4l5 5V5l-5 5H3z"/><path d="M16 9l5 6M21 9l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
          <button class="mfp-btn mfp-side" @click="player.stopAndHide()" aria-label="停止并关闭">
            <svg viewBox="0 0 24 24" class="mfp-stop" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="1.5"/></svg>
          </button>
        </div>

        <!-- 队列提示 -->
        <div v-if="player.queue.length > 1" class="mfp-qmeta">
          {{ player.queueIndex + 1 }} / {{ player.queue.length }} · {{ modeShort }}
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import { usePlayerStore } from '@/stores/player'
import AppIcon from '@/components/common/AppIcon.vue'

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

const MODE_LABEL = {
  list: { short: '列表循环', title: '列表循环' },
  single: { short: '单曲循环', title: '单曲循环' },
  shuffle: { short: '随机播放', title: '随机播放' },
  once: { short: '单曲一次', title: '单曲一次' },
}
const modeShort = computed(() => MODE_LABEL[player.playMode]?.short || '列表循环')
const modeTitle = computed(() => MODE_LABEL[player.playMode]?.title || '列表循环')

/* ---------- 播放模式下拉菜单 ---------- */
const modeMenuOpen = ref(false)
function toggleModeMenu() { modeMenuOpen.value = !modeMenuOpen.value }
function closeModeMenu() { modeMenuOpen.value = false }
function pickMode(m) {
  player.setPlayMode(m)
  modeMenuOpen.value = false
}

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
  /* svh = 最小视口高度：地址栏收起/展开都不会把底部控制键顶出屏幕 */
  height: 88vh;
  height: 88svh;
  max-height: 88svh;
  border-radius: 26px 26px 0 0;
  background: linear-gradient(180deg, rgba(26,36,44,.96), rgba(16,24,32,.98));
  -webkit-backdrop-filter: saturate(160%) blur(24px);
  backdrop-filter: saturate(160%) blur(24px);
  border-top: 1px solid rgba(255,255,255,.1);
  box-shadow: 0 -30px 70px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.07);
  padding: 10px 22px calc(20px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
  display: flex; flex-direction: column;
  align-items: center;
  overflow: hidden;              /* 由 .mfp-body 承担滚动，外壳自身不外溢 */
}
/* 中段（封面/信息/进度）：唯一可滚动区，flex 收缩后不会把控制键挤出屏幕。
   首尾用 margin:auto 让内容在富余空间里居中，溢出时自动退化为可滚动、不裁切顶部。 */
.mfp-body {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  display: flex; flex-direction: column;
  align-items: center;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
.mfp-body > .mfp-art { margin-top: auto; }
.mfp-body > .mfp-progress { margin-bottom: auto; }
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
  width: min(62vw, 240px); height: min(62vw, 240px);
  margin: 18px 0 22px; flex: none;
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

.mfp-progress { width: 100%; flex: none; margin-top: 20px; }
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
  display: flex; align-items: center; justify-content: center; gap: 30px;
  margin-top: 16px; flex: none;
  padding-bottom: 4px;
}
.mfp-controls-2 {
  display: flex; align-items: center; justify-content: center; gap: 24px;
  flex: none; margin-top: 14px;
}
.mfp-step { width: 52px; height: 52px; }
.mfp-step svg { width: 22px; height: 22px; fill: currentColor; }
.mfp-step:disabled { opacity: 0.32; }
.mfp-side { width: 48px; height: 48px; }
.mfp-mode-wrap { position: relative; }
.mfp-mode {
  display: inline-flex; align-items: center; gap: 6px;
  height: 40px; padding: 0 14px; border-radius: 20px;
  border: none; background: rgba(255, 255, 255, 0.08); color: #dbe3ee;
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  font-size: 13px; letter-spacing: .04em;
}
.mfp-mode svg { width: 18px; height: 18px; }
.mfp-mode:active { background: rgba(255, 255, 255, 0.14); }
.mfp-mode[aria-expanded="true"] { background: rgba(255, 255, 255, 0.2); color: #fff; }
.mfp-mode-label { line-height: 1; }

/* 模式下拉菜单（移动端从按钮上方展开） */
.mfp-mode-menu {
  position: absolute;
  left: 50%; bottom: calc(100% + 10px);
  transform: translateX(-50%);
  margin: 0; padding: 6px;
  min-width: 200px;
  list-style: none;
  background: linear-gradient(160deg, rgba(26, 36, 44, 0.98), rgba(16, 24, 32, 0.98));
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
  z-index: 5;
}
.mfp-mode-menu li {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  font-size: 14px;
  color: rgba(220, 230, 240, 0.85);
  border-radius: 10px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.mfp-mode-menu li:active { background: rgba(255, 255, 255, 0.08); color: #fff; }
.mfp-mode-menu li.active { background: rgba(61, 127, 214, 0.22); color: #fff; }
.mfpmenu-ic { display: inline-flex; width: 18px; height: 18px; flex-shrink: 0; color: currentColor; }
.mfpmenu-text { flex: 1; min-width: 0; white-space: nowrap; }
.mfpmenu-check { width: 16px; height: 16px; color: #4ade80; flex-shrink: 0; }
.mfpmenu-enter-active, .mfpmenu-leave-active { transition: opacity .14s ease, transform .14s ease; }
.mfpmenu-enter-from, .mfpmenu-leave-to { opacity: 0; transform: translate(-50%, 6px); }
.mfp-qmeta {
  margin-top: 14px;
  font-size: 12px;
  color: rgba(200, 215, 225, 0.55);
  font-variant-numeric: tabular-nums;
  text-align: center;
  letter-spacing: .05em;
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

/* ---------- 小屏 / 矮屏自适应 ----------
   目标：无论机型多矮，上一首 / 播放 / 下一首都留在屏幕内，绝不被挤出可视区 */
@media (max-width: 380px) {
  .mfp-sheet { padding-left: 16px; padding-right: 16px; }
  .mfp-track { font-size: 20px; }
  .mfp-controls { gap: 22px; }
  .mfp-controls-2 { gap: 16px; }
  .mfp-step { width: 48px; height: 48px; }
  .mfp-main { width: 68px; height: 68px; }
  .mfp-side { width: 44px; height: 44px; }
}

/* 矮屏（iPhone SE / 横屏）：压缩封面与间距，一屏放下全部控件 */
@media (max-height: 720px) {
  .mfp-art { width: min(46vw, 168px); height: min(46vw, 168px); }
  .mfp-note { font-size: 24px; }
  .mfp-progress { margin-top: 14px; }
  .mfp-controls { margin-top: 10px; }
  .mfp-controls-2 { margin-top: 10px; }
  .mfp-qmeta { margin-top: 8px; }
  .mfp-nav { margin-bottom: 6px; }
}
@media (max-height: 600px) {
  .mfp-art { width: min(34vw, 120px); height: min(34vw, 120px); }
  .mfp-nav { margin-bottom: 2px; }
}

/* ---------- 横屏：左封面 / 右控制 两栏，一屏放下 ----------
   手机横屏只有 350~430 高，竖排（封面 + 信息 + 进度 + 两排控制）必然被挤爆
   —— 上一首/下一首会掉出可视区。横屏改为左右两栏：左边封面占满高度，
   右边自上而下「标题 → 进度 → 控制 → 模式排 → 队列」。
   .mfp-body 用 display:contents 打散，让它的子元素直接参与 sheet 的网格。 */
@media (orientation: landscape) and (max-height: 600px) {
  .mfp-sheet {
    height: 100svh;
    max-height: 100svh;
    border-radius: 0;
    padding: 6px 24px calc(8px + env(safe-area-inset-bottom, 0px));
    box-sizing: border-box;
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    grid-template-rows: auto auto 1fr auto auto auto auto;
    grid-template-areas:
      "hd    hd"
      "nav   nav"
      "art   meta"
      "art   prog"
      "art   ctrl"
      "art   ctrl2"
      "art   qmeta";
    column-gap: 26px;
    overflow: hidden;
  }
  .mfp-handle { grid-area: hd; }
  .mfp-nav { grid-area: nav; margin-bottom: 4px; }
  /* 打散中段容器：mfp-art / mfp-meta / mfp-progress 变成 sheet 的直接网格项 */
  .mfp-body { display: contents; }
  /* 覆盖 .mfp-body > .mfp-art 的 margin:auto（在网格里会被推歪） */
  .mfp-body > .mfp-art { grid-area: art; margin: 0; align-self: center; justify-self: center; }
  .mfp-meta { grid-area: meta; align-self: end; text-align: left; }
  .mfp-track { font-size: 19px; }
  .mfp-artist { font-size: 12.5px; }
  .mfp-progress { grid-area: prog; margin: 10px 0 0; align-self: start; }
  .mfp-body > .mfp-progress { margin-bottom: 0; }
  .mfp-controls { grid-area: ctrl; margin-top: 10px; gap: 26px; padding-bottom: 0; }
  .mfp-main { width: 60px; height: 60px; }
  .mfp-step { width: 44px; height: 44px; }
  .mfp-controls-2 { grid-area: ctrl2; margin-top: 8px; gap: 18px; }
  .mfp-qmeta { grid-area: qmeta; margin-top: 6px; }
  .mfp-empty { grid-area: meta; align-self: end; }
  /* 横屏高度本来就紧，封面按高度而不是宽度收敛，避免顶破两栏 */
  .mfp-art { width: min(38vh, 220px); height: min(38vh, 220px); }
}

@media (prefers-reduced-motion: reduce) {
  .mfp-art.spin { animation: none; }
  .mfp * { transition: none !important; }
}

.mfp-enter-active, .mfp-leave-active { transition: opacity .32s ease; }
.mfp-enter-from, .mfp-leave-to { opacity: 0; }
</style>
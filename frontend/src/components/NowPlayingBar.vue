<template>
  <transition name="npbar">
    <!--
      显示条件：真正在播放或处于点播模式
      - 之前用 player.shows || bgmItem：只要 BGM 库加载完就显示，会出现"没在播也占位"的空 bar
      - 现在用 player.isPlaying || player.curItem：仅当有声时显示，避免空占位 + 与表格内容视觉重叠
      - BGM 模式下若 autoplay 被拦，bar 会隐藏；用户主动点"设为默认"再点播放后会重新出现
    -->
    <div v-if="shouldShow && !minimized" class="npbar" ref="barRef">
      <!-- 曲目信息（点击展开全屏播放器，仅移动端生效） -->
      <div class="np-info" @click="onInfoClick">
        <div class="np-cover">
          <span class="np-note">♪</span>
          <span class="np-badge" :class="{ live: player.isPlaying }"></span>
        </div>
        <div class="np-meta">
          <span class="np-title" :title="displayItem?.title || ''">{{ displayItem?.title || '未知曲目' }}</span>
          <span class="np-artist">
            {{ displayItem?.artist || '佚名' }}
            <span v-if="player.mode === 'playlist' && player.queue.length > 1" class="np-qmeta">{{ player.queueIndex + 1 }}/{{ player.queue.length }}</span>
          </span>
        </div>
      </div>

      <!-- 上一首 -->
      <button class="np-btn np-step" :disabled="player.queue.length < 2 || player.mode !== 'playlist'" @click="player.prev()" title="上一首" aria-label="上一首">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h2v14H6zM20 5v14L9 12z" fill="currentColor"/></svg>
      </button>
      <!-- 播放/暂停 -->
      <button class="np-btn np-toggle" @click="player.togglePlay()" :title="player.isPlaying ? '暂停' : '播放'" aria-label="播放切换">
        <el-icon><VideoPause v-if="player.isPlaying" /><VideoPlay v-else /></el-icon>
      </button>
      <!-- 下一首 -->
      <button class="np-btn np-step" :disabled="player.queue.length < 2 || player.mode !== 'playlist'" @click="player.next()" title="下一首" aria-label="下一首">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 5h2v14h-2zM4 5v14l11-7z" fill="currentColor"/></svg>
      </button>
      <!-- 播放模式：点击展开下拉菜单直接选 -->
      <div class="np-mode-wrap" v-click-outside="closeModeMenu">
        <button
          class="np-btn np-mode"
          @click="toggleModeMenu"
          :title="modeTitle"
          :aria-label="`播放模式：${modeTitle}，点击选择`"
          aria-haspopup="listbox"
          :aria-expanded="modeMenuOpen"
          :disabled="player.mode !== 'playlist'"
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
          <span class="np-mode-label">{{ modeShort }}</span>
        </button>
        <transition name="npmenu">
          <ul v-if="modeMenuOpen" class="np-mode-menu" role="listbox" aria-label="选择播放模式">
            <li
              v-for="m in player.PLAY_MODES"
              :key="m"
              role="option"
              :aria-selected="player.playMode === m"
              :class="{ active: player.playMode === m }"
              @click="pickMode(m)"
            >
              <span class="npmenu-ic">
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
              <span class="npmenu-text">{{ MODE_LABEL[m].title }}</span>
              <svg v-if="player.playMode === m" class="npmenu-check" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12l4 4 10-10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </li>
          </ul>
        </transition>
      </div>

      <!-- 进度条（横向拉长主力：flex:1 占满剩余宽度） -->
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
        <button class="np-btn np-vol-btn" @click="player.toggleMute()" :title="player.volume > 0 ? '静音' : '恢复音量'" aria-label="静音">
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

      <!-- 最小化：收起成浮动小图标（播放条不再占位），点图标再展开 -->
      <button class="np-btn np-min" @click="minimize" title="最小化成小图标（不挡内容，可拖动）" aria-label="最小化播放框">
        <svg viewBox="0 0 24 24" class="np-vol-ic" aria-hidden="true"><path d="M5 12h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>

      <!-- 关闭：任何模式都可叉掉播放框，停止后自动恢复默认背景音乐 -->
      <button class="np-btn np-close" @click="player.stopAndHide()" title="关闭播放（回到背景音乐）" aria-label="关闭播放">
        <svg viewBox="0 0 24 24" class="np-vol-ic" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
    </div>
  </transition>

  <!-- 最小化后的浮动图标：可拖动；位移很小则视为点击 → 展开播放条 -->
  <div
    v-if="shouldShow && minimized"
    class="np-mini"
    :class="{ playing: player.isPlaying, dragging }"
    :style="{ left: miniPos.x + 'px', top: miniPos.y + 'px' }"
    role="button"
    tabindex="0"
    :title="miniTitle"
    aria-label="展开播放框（可拖动改变位置）"
    @pointerdown="onMiniDown"
    @pointermove="onMiniMove"
    @pointerup="onMiniUp"
    @pointercancel="onMiniUp"
    @keydown.enter.prevent="expand"
    @keydown.space.prevent="expand"
  >
    <span class="np-mini-note" aria-hidden="true">♪</span>
    <span class="np-mini-dot" aria-hidden="true"></span>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { usePlayerStore } from '@/stores/player'
import { useBgmLibraryStore } from '@/stores/bgmLibrary'

const player = usePlayerStore()
const bgm = useBgmLibraryStore()
const barRef = ref(null)
const emit = defineEmits(['open-full'])

const isTouchDevice = typeof window !== 'undefined' &&
  window.matchMedia('(pointer: coarse)').matches

function onInfoClick() {
  if (!isTouchDevice) return
  emit('open-full')
}

/* ---------- 当前显示项（解决 BGM 模式下播放栏与听觉不一致） ----------
 *  playlist 模式 → 用 curItem
 *  bgm 模式     → 用当前 BGM 项（来自 bgmLibrary）
 *  idle 模式    → 仍然优先 BGM（即便未播放也告诉用户「当前背景音乐」）
 */
const bgmItem = computed(() => {
  if (player.mode === 'playlist') return null
  return bgm.musicLibrary.find(it => String(it.id) === String(bgm.bgmChoiceId)) || null
})
const displayItem = computed(() => {
  if (player.mode === 'playlist') return player.curItem
  return bgmItem.value
})

/* 是否显示 npbar：
 *  - 点播模式（playlist）：有 curItem 就显示
 *  - BGM 模式（bgm）：真正在播放或 BGM 已就绪且是用户的播放意图（bgmEnabled + bgmItem）
 *  关键修复：之前用 "shows || bgmItem"，会出现 BGM 库加载完就显示一个空 bar 的情况
 *  现在改为：用户明确表达了"在播"意图（isPlaying 或 playlist.curItem）才显示
 */
const shouldShow = computed(() => {
  if (player.dismissed) return false     // 用户已 ✕ 关闭播放框
  if (player.mode === 'playlist' && player.curItem) return true
  // BGM 模式下：用户在播 或 BGM 已就绪（自动播放被拦时也算意图）
  if (player.mode === 'bgm' && player.bgmEnabled && bgmItem.value) return true
  return false
})

const ratio = computed(() => (player.duration ? player.progress / player.duration : 0))
const volProxy = ref(player.volume)

/* ---------- 最小化：把播放条收成一个可拖动的浮动图标 ----------
 * 动机：播放条是 position:fixed 且宽 min(100% - 32px, 1200px)、固定在底部居中，
 * 在别的页面上操作时会压住内容，而且不可移动 —— 想看被遮住的部分只能关掉播放。
 * 现在可以收成一个小圆标，位置随便拖，并且记住。 */
const MINI_SIZE = 46
const MINI_MARGIN = 8
const DRAG_THRESHOLD = 6      // 位移小于它就算「点击」，大于就算「拖动」

function clampNum(v, lo, hi) { return Math.min(Math.max(v, lo), hi) }

function defaultMiniPos() {
  const vw = window.innerWidth || 1024
  const vh = window.innerHeight || 768
  // 默认落在右下角、原播放条上方一点（用户希望「页面右边浮现」）
  return { x: vw - MINI_SIZE - 20, y: vh - MINI_SIZE - 96 }
}

function loadMiniPos() {
  try {
    const raw = localStorage.getItem('np_mini_pos')
    if (!raw) return null
    const p = JSON.parse(raw)
    if (typeof p?.x === 'number' && typeof p?.y === 'number') return p
  } catch { /* 数据坏了就退回默认位置 */ }
  return null
}

function saveMiniPos() {
  try { localStorage.setItem('np_mini_pos', JSON.stringify(miniPos.value)) } catch { /* 忽略 */ }
}

const minimized = ref(localStorage.getItem('np_minimized') === '1')
const miniPos = ref(loadMiniPos() || defaultMiniPos())
const dragging = ref(false)

function minimize() {
  minimized.value = true
  try { localStorage.setItem('np_minimized', '1') } catch { /* 忽略 */ }
}
function expand() {
  minimized.value = false
  try { localStorage.setItem('np_minimized', '0') } catch { /* 忽略 */ }
}

const miniTitle = computed(() => {
  const t = displayItem.value?.title || '背景音乐'
  return `${player.isPlaying ? '正在播放' : '已暂停'}：${t}（单击展开，拖动可移动）`
})

/* 拖动：pointer 事件 + 边界钳制；松手时若几乎没动，就当作点击 → 展开 */
let dragOrigin = null
let movedDist = 0

function onMiniDown(e) {
  if (e.button) return                       // 只响应主指针（左键/触摸）
  const rect = e.currentTarget.getBoundingClientRect()
  dragOrigin = { px: e.clientX, py: e.clientY, left: rect.left, top: rect.top }
  movedDist = 0
  dragging.value = true
  try { e.currentTarget.setPointerCapture(e.pointerId) } catch { /* 忽略 */ }
}

function onMiniMove(e) {
  if (!dragOrigin) return
  const dx = e.clientX - dragOrigin.px
  const dy = e.clientY - dragOrigin.py
  movedDist = Math.max(movedDist, Math.hypot(dx, dy))
  miniPos.value = {
    x: clampNum(dragOrigin.left + dx, MINI_MARGIN, window.innerWidth - MINI_SIZE - MINI_MARGIN),
    y: clampNum(dragOrigin.top + dy, MINI_MARGIN, window.innerHeight - MINI_SIZE - MINI_MARGIN),
  }
}

function onMiniUp(e) {
  if (!dragOrigin) return
  const wasDrag = movedDist > DRAG_THRESHOLD
  dragOrigin = null
  dragging.value = false
  try { e.currentTarget.releasePointerCapture(e.pointerId) } catch { /* 忽略 */ }
  if (wasDrag) saveMiniPos()
  else expand()
}

/* 窗口尺寸变化时把图标拉回可视区，
 * 否则「拖到右下角后把窗口缩小」会让图标留在屏幕外找不回来 */
function onWinResize() {
  miniPos.value = {
    x: clampNum(miniPos.value.x, MINI_MARGIN, window.innerWidth - MINI_SIZE - MINI_MARGIN),
    y: clampNum(miniPos.value.y, MINI_MARGIN, window.innerHeight - MINI_SIZE - MINI_MARGIN),
  }
}
onMounted(() => window.addEventListener('resize', onWinResize))
onBeforeUnmount(() => window.removeEventListener('resize', onWinResize))

const MODE_LABEL = {
  list: { short: '列表', title: '列表循环' },
  single: { short: '单曲', title: '单曲循环' },
  shuffle: { short: '随机', title: '随机播放' },
  once: { short: '一次', title: '单曲一次' },
}
const modeShort = computed(() => MODE_LABEL[player.playMode]?.short || '列表')
const modeTitle = computed(() => MODE_LABEL[player.playMode]?.title || '列表循环')

/* ---------- 播放模式下拉菜单 ---------- */
const modeMenuOpen = ref(false)
function toggleModeMenu() { if (player.mode === 'playlist') modeMenuOpen.value = !modeMenuOpen.value }
function closeModeMenu() { modeMenuOpen.value = false }
function pickMode(m) {
  player.setPlayMode(m)
  modeMenuOpen.value = false
}

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
/* ============================================================
   播放框横向拉长布局 v2.40.2
   - 高度压回 60px（不再"升高"）
   - 横向尽量铺开：进度条 flex:1 占满剩余宽度，标题/作者区给 280px
   - 按钮缩小一档：np-btn 32，np-toggle 40，np-step 32，np-mode 32
   ============================================================ */
.npbar {
  position: fixed;
  bottom: 14px;
  /* 居中布局：不依赖任何侧栏宽度
   * - 普通带侧栏的桌面页面：剩余宽度充足，居中靠下很自然
   * - MusicView 等全屏 island 页面：没有侧栏，原本 calc(100% - 320px) 会溢出；现在用 min + 居中解决
   */
  left: 50%;
  transform: translateX(-50%);
  width: min(calc(100% - 32px), 1200px);
  height: 60px;
  z-index: 980;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px 0 14px;
  border-radius: 16px;
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
  gap: 10px;
  min-width: 0;
  flex: 0 0 auto;
  width: 280px;          /* 标题/作者区给足横向空间 */
}

.np-cover {
  position: relative;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(140deg, rgba(122, 172, 210, 0.5), rgba(76, 110, 160, 0.4));
  color: rgba(224, 238, 255, 0.9);
}

.np-note { font-size: 18px; }

.np-badge {
  position: absolute;
  top: -2px; right: -2px;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #6b7280;
  border: 2px solid #141a26;
}
.np-badge.live {
  background: #4ade80;
  box-shadow: 0 0 6px rgba(74, 222, 128, 0.7);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

.np-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  flex: 1;
}
.np-title {
  font-family: var(--font-serif, serif);
  font-size: 13px;
  color: #e9eef5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.np-artist {
  font-size: 11px;
  color: rgba(200, 210, 224, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---------- 按钮统一 32px，主播 40px ---------- */
.np-btn {
  width: 32px; height: 32px;
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
.np-btn:hover { background: rgba(255, 255, 255, 0.14); color: #fff; }
.np-btn:disabled { opacity: 0.32; cursor: not-allowed; }
.np-btn :deep(svg), .np-btn svg { width: 16px; height: 16px; }

.np-toggle {
  width: 40px; height: 40px;
  background: linear-gradient(140deg, #3d7fd6, #2a5fa8); color: #fff;
  box-shadow: 0 4px 12px rgba(61, 127, 214, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.18);
}
.np-toggle:hover { background: linear-gradient(140deg, #4b8ce0, #326ab8); }
.np-toggle svg { width: 18px; height: 18px; }

.np-step { background: rgba(255, 255, 255, 0.05); }
.np-mode-wrap { position: relative; flex-shrink: 0; }
.np-mode {
  display: inline-flex; align-items: center; gap: 4px;
  width: auto; height: 32px; padding: 0 10px; border-radius: 16px;
  background: rgba(255, 255, 255, 0.05); font-size: 12px;
}
.np-mode svg { width: 14px; height: 14px; }
.np-mode[aria-expanded="true"] { background: rgba(255, 255, 255, 0.16); color: #fff; }
.np-mode-label { line-height: 1; letter-spacing: .04em; }
.np-mode:hover { background: rgba(255, 255, 255, 0.12); }
.np-close { background: transparent; }
.np-close:hover { background: rgba(239, 68, 68, 0.18); color: #f87171; }
.np-min { background: transparent; }
.np-min:hover { background: rgba(255, 255, 255, 0.14); }

/* ---- 最小化后的浮动图标 ----
   固定在屏幕上（fixed），位置由内联 left/top 控制，可拖动并记忆；
   touch-action:none 让触摸拖动不会误触发页面滚动。 */
.np-mini {
  position: fixed;
  width: 46px; height: 46px;
  z-index: 981;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: grab;
  touch-action: none;
  user-select: none;
  color: rgba(224, 238, 255, 0.92);
  background: linear-gradient(160deg, rgba(38, 48, 64, 0.94), rgba(24, 31, 44, 0.92));
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 26px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.07);
  -webkit-backdrop-filter: saturate(150%) blur(12px);
  backdrop-filter: saturate(150%) blur(12px);
  transition: border-color .2s ease, box-shadow .2s ease;
}
.np-mini:hover { border-color: rgba(255, 255, 255, 0.24); }
.np-mini:focus-visible { outline: 2px solid var(--yq-gold, #fbbf24); outline-offset: 2px; }
.np-mini.dragging { cursor: grabbing; box-shadow: 0 14px 34px rgba(0, 0, 0, 0.55); }
.np-mini-note { font-size: 19px; line-height: 1; }

/* 右上角状态点：播放中鎏金呼吸，暂停时静态 */
.np-mini-dot {
  position: absolute; top: 7px; right: 7px;
  width: 8px; height: 8px; border-radius: 50%;
  background: rgba(200, 215, 230, 0.38);
}
.np-mini.playing .np-mini-dot {
  background: var(--yq-gold, #fbbf24);
  animation: npMiniPulse 1.9s ease-out infinite;
}
@keyframes npMiniPulse {
  0%   { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.5); }
  70%  { box-shadow: 0 0 0 7px rgba(251, 191, 36, 0); }
  100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0); }
}
@media (prefers-reduced-motion: reduce) {
  .np-mini.playing .np-mini-dot { animation: none; }
}

.np-qmeta {
  margin-left: 6px;
  font-size: 10px;
  color: rgba(200, 215, 230, 0.55);
  font-variant-numeric: tabular-nums;
  padding: 1px 5px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
}

/* ---------- 进度条（主力拉长区） ---------- */
.np-progress {
  flex: 1 1 auto;       /* 占满剩余横向空间 */
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.np-time {
  font-size: 12px;
  color: rgba(190, 200, 214, 0.65);
  font-variant-numeric: tabular-nums;
  min-width: 42px;
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

/* ---------- 音量 ---------- */
.np-vol-ic { width: 16px; height: 16px; fill: currentColor; }
.np-volume {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.np-vol { width: 88px; }

/* ---------- 模式菜单 ---------- */
.np-mode-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 8px);
  margin: 0;
  padding: 6px;
  min-width: 168px;
  list-style: none;
  background: linear-gradient(160deg, rgba(28, 36, 48, 0.96), rgba(20, 26, 38, 0.96));
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  -webkit-backdrop-filter: saturate(150%) blur(14px);
  backdrop-filter: saturate(150%) blur(14px);
  z-index: 5;
}
.np-mode-menu li {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  font-size: 13px;
  color: rgba(220, 230, 240, 0.85);
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
}
.np-mode-menu li:hover { background: rgba(255, 255, 255, 0.08); color: #fff; }
.np-mode-menu li.active { background: rgba(61, 127, 214, 0.22); color: #fff; }
.npmenu-ic { display: inline-flex; width: 18px; height: 18px; flex-shrink: 0; color: currentColor; }
.npmenu-text { flex: 1; min-width: 0; white-space: nowrap; }
.npmenu-check { width: 16px; height: 16px; color: #4ade80; flex-shrink: 0; }
.npmenu-enter-active, .npmenu-leave-active { transition: opacity .14s ease, transform .14s ease; }
.npmenu-enter-from, .npmenu-leave-to { opacity: 0; transform: translateY(6px); }

/* ---------- 移动端：保持横向铺开，缩小各部分 ---------- */
@media (max-width: 768px) {
  .npbar {
    width: calc(100% - 20px);
    left: 10px;
    bottom: calc(14px + var(--safe-bottom));
    height: 56px;
    gap: 10px;
    padding: 0 10px 0 8px;
  }
  .np-volume { display: none; }
  .np-info { width: 140px; gap: 8px; }
  .np-cover { width: 32px; height: 32px; }
  .np-note { font-size: 16px; }
  .np-progress { min-width: 100px; }
  .np-mode { height: 30px; padding: 0 8px; font-size: 11px; }
  .np-mode svg { width: 12px; height: 12px; }
  .np-step, .np-btn { width: 30px; height: 30px; }
  .np-toggle { width: 36px; height: 36px; }
  .np-close { display: none; }
}
</style>

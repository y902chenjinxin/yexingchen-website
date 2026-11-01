<template>
  <transition name="mfp">
    <div v-if="visible" class="fp" :class="{ 'is-page': page }" :style="themeStyle" @click.self="close">
      <!-- ===== 背景层：由曲目名派生的色相（每首歌一种氛围）+ 两团缓慢漂移的光 + 极淡几何装饰 ===== -->
      <div class="fp-bg" aria-hidden="true">
        <span class="fp-orb fp-orb--a"></span>
        <span class="fp-orb fp-orb--b"></span>
        <span class="fp-deco fp-deco--ring"></span>
        <span class="fp-deco fp-deco--tri"></span>
        <span class="fp-deco fp-deco--cross"></span>
        <span class="fp-veil"></span>
      </div>

      <div class="fp-inner">
        <!-- 顶栏：只有返回与模式标记，其余全部让给画面 -->
        <header class="fp-top">
          <button class="fp-ghost-btn" aria-label="关闭播放器" @click="close">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="1.9"
                stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <span class="fp-tag">{{ modeLabel }}</span>
          <span class="fp-top-spacer"></span>
        </header>

        <!-- ===== 主视觉：歌名当歌词（Folia 是全屏歌词，我们没有歌词数据，就用曲目名占这个位） ===== -->
        <main class="fp-stage">
          <h1 :key="'t' + (player.curItem?.id || '')" class="fp-title" :class="{ 'is-playing': player.isPlaying }">
            <span v-for="(c, i) in titleChars" :key="i" class="fp-ch" :style="{ '--i': i }">{{ c }}</span>
          </h1>
          <p class="fp-sub">
            <span class="fp-sub-artist">{{ player.curItem?.artist || '佚名' }}</span>
            <template v-if="queueText"><span class="fp-dot">·</span>{{ queueText }}</template>
          </p>
          <p v-if="!player.curItem" class="fp-empty">暂无播放内容</p>
        </main>

        <!-- ===== 底部控制条：Folia 的「一条胶囊打天下」 ===== -->
        <footer class="fp-bar">
          <div class="fp-card">
            <div class="fp-row fp-row--main">
              <button class="fp-step" :disabled="player.queue.length < 2" aria-label="上一首" @click="player.prev()">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M7 5v14M19 5.6v12.8L9.4 12z" fill="none" stroke="currentColor" stroke-width="1.8"
                    stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
              <button class="fp-play" :aria-label="player.isPlaying ? '暂停' : '播放'" @click="player.togglePlay()">
                <svg v-if="player.isPlaying" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="8" y="6" width="3" height="12" rx="1.1" fill="currentColor" />
                  <rect x="13.6" y="6" width="3" height="12" rx="1.1" fill="currentColor" />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 6.2l9.2 5.8L9 17.8z" fill="currentColor" />
                </svg>
              </button>
              <button class="fp-step" :disabled="player.queue.length < 2" aria-label="下一首" @click="player.next()">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M17 5v14M5 5.6v12.8L14.6 12z" fill="none" stroke="currentColor" stroke-width="1.8"
                    stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>

              <div class="fp-info">
                <span class="fp-info-title">{{ player.curItem?.title || '未知曲目' }}</span>
                <span class="fp-info-sub">{{ player.curItem?.artist || '佚名' }}</span>
              </div>

              <button class="fp-ghost-btn fp-more" :class="{ on: panelOpen }" aria-label="更多控制"
                :aria-expanded="panelOpen" @click.stop="panelOpen = !panelOpen">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="6" cy="12" r="1.5" fill="currentColor" />
                  <circle cx="12" cy="12" r="1.5" fill="currentColor" />
                  <circle cx="18" cy="12" r="1.5" fill="currentColor" />
                </svg>
              </button>
            </div>

            <div class="fp-row fp-row--progress">
              <span class="fp-time">{{ fmt(player.progress) }}</span>
              <input
                v-if="player.duration"
                type="range" class="fp-range"
                :value="ratio" min="0" max="1" step="0.001"
                :style="{ '--fill': (ratio * 100) + '%' }"
                aria-label="播放进度"
                @input="onSeek"
              />
              <span v-else class="fp-range fp-range--idle"></span>
              <span class="fp-time">{{ fmt(player.duration) }}</span>
            </div>
          </div>

          <!-- 更多控制：播放模式 / 静音 / 停止（Folia 也是把这类东西收进一个面板） -->
          <transition name="fpmenu">
            <div v-if="panelOpen" class="fp-panel" @click.stop>
              <span class="fp-panel-lab">播放模式</span>
              <div class="fp-modes">
                <button
                  v-for="m in player.PLAY_MODES" :key="m"
                  class="fp-mode" :class="{ on: player.playMode === m }"
                  @click="pickMode(m)"
                >{{ MODE_LABEL[m].short }}</button>
              </div>
              <div class="fp-panel-acts">
                <button class="fp-act" @click="player.toggleMute()">
                  {{ player.volume > 0 ? '静音' : '恢复音量' }}
                </button>
                <button class="fp-act fp-act--danger" @click="player.stopAndHide()">停止并关闭</button>
              </div>
            </div>
          </transition>
        </footer>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { fmtClock } from '@/utils/format'
import { usePlayerStore } from '@/stores/player'

const player = usePlayerStore()

const props = defineProps({
  modelValue: Boolean,
  /* v2.46.217：作为独立路由页渲染（真全屏），而不是 App.vue 里的覆盖层 */
  page: Boolean,
})
const emit = defineEmits(['update:modelValue'])
const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

function close() {
  emit('update:modelValue', false)
}

const modeLabel = computed(() => (player.mode === 'bgm' ? '背景 · 天籁' : '点播 · 宫商'))

const MODE_LABEL = {
  list: { short: '列表循环' },
  single: { short: '单曲循环' },
  shuffle: { short: '随机播放' },
  once: { short: '单曲一次' },
}

const panelOpen = ref(false)
function pickMode(m) {
  player.setPlayMode(m)
  panelOpen.value = false
}
/* 换歌or关闭时收起面板，避免残留 */
watch(() => player.curItem?.id, () => { panelOpen.value = false })
watch(visible, (v) => { if (!v) panelOpen.value = false })

const queueText = computed(() => {
  const n = player.queue.length
  if (n < 2 || player.queueIndex < 0) return ''
  return `${player.queueIndex + 1} / ${n}`
})

/* ---------- 主视觉文案 ---------- */
/* 按 code point 拆字，逐字入场（emoji / 中文都不会被拆坏） */
const titleChars = computed(() => Array.from(player.curItem?.title || '未在播放'))

/* 色相由曲目派生：同一首歌永远是同一个氛围，换歌换一套光。
   不是随机 —— 随机每次进页面都变，反而让人以为换了首歌。 */
function hashCode(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 360000
  return h
}
const themeStyle = computed(() => {
  const it = player.curItem
  const seed = hashCode(`${it?.title || ''}|${it?.artist || ''}`)
  return {
    '--fp-hue': seed % 360,
    '--fp-hue2': (seed % 360 + 44) % 360,
  }
})

const ratio = computed(() => (player.duration ? player.progress / player.duration : 0))
function onSeek(e) { player.seekByRatio(Number(e.target.value)) }

function fmt(sec) {
  return fmtClock(sec)
}
</script>

<style scoped>
/* ============================================================
 * 全屏播放页（v2.46.316 按 Folia 的语言重做）
 * 参考点：全屏当主视觉、不放专辑封面、中央巨大文字、底部一条胶囊
 * 控制条，其余控件收进一个小面板。颜色由曲目派生（--fp-hue）。
 * ============================================================ */
.fp {
  position: fixed; inset: 0; z-index: 2000;
  background: hsl(var(--fp-hue, 240), 32%, 6%);
  display: flex; align-items: stretch; justify-content: center;
  color: #f2eee6;
  -webkit-tap-highlight-color: transparent;
}
.fp.is-page {
  position: relative; inset: auto; z-index: auto;
  height: 100vh; height: 100dvh;
}

/* ---------- 背景 ---------- */
.fp-bg { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.fp-orb {
  position: absolute; border-radius: 50%;
  filter: blur(72px);
  will-change: transform;
}
.fp-orb--a {
  width: 74vmax; height: 74vmax; left: -26vmax; top: -34vmax;
  background: radial-gradient(circle, hsl(var(--fp-hue, 240), 70%, 44%, .55), transparent 66%);
  animation: fpDriftA 28s ease-in-out infinite alternate;
}
.fp-orb--b {
  width: 62vmax; height: 62vmax; right: -24vmax; bottom: -30vmax;
  background: radial-gradient(circle, hsl(var(--fp-hue2, 280), 62%, 38%, .42), transparent 68%);
  animation: fpDriftB 36s ease-in-out infinite alternate;
}
@keyframes fpDriftA { from { transform: translate3d(0, 0, 0) scale(1) } to { transform: translate3d(6vmax, 4vmax, 0) scale(1.08) } }
@keyframes fpDriftB { from { transform: translate3d(0, 0, 0) scale(1.05) } to { transform: translate3d(-5vmax, -3vmax, 0) scale(1) } }

/* 极淡几何装饰：只负责"不是纯色块"，绝不抢戏 */
.fp-deco { position: absolute; opacity: .07; border-color: rgba(255, 255, 255, .9); }
.fp-deco--ring {
  width: 40vmin; height: 40vmin; left: 12%; top: 16%;
  border: 1px solid; border-radius: 50%;
}
.fp-deco--tri {
  width: 26vmin; height: 26vmin; right: 14%; top: 24%;
  background: currentColor; opacity: .05;
  clip-path: polygon(50% 0, 100% 100%, 0 100%);
  transform: rotate(18deg);
}
.fp-deco--cross {
  width: 16vmin; height: 16vmin; left: 22%; bottom: 26%; opacity: .05;
  background:
    linear-gradient(currentColor, currentColor) center / 1px 100% no-repeat,
    linear-gradient(currentColor, currentColor) center / 100% 1px no-repeat;
}
/* 底部压暗：保证控制条与文字永远压得住背景 */
.fp-veil {
  position: absolute; inset: 0;
  background:
    radial-gradient(120% 80% at 50% 30%, transparent 30%, rgba(0, 0, 0, .55) 100%),
    linear-gradient(180deg, rgba(0, 0, 0, .35), transparent 26%, transparent 56%, rgba(0, 0, 0, .72));
}

/* ---------- 骨架 ---------- */
.fp-inner {
  position: relative; z-index: 2;
  width: 100%; max-width: 1120px;
  display: flex; flex-direction: column;
  padding: 0;
}

/* ---------- 顶栏 ---------- */
.fp-top {
  flex: none;
  display: flex; align-items: center; gap: 10px;
  padding: 14px 16px 6px;
  padding-top: calc(12px + env(safe-area-inset-top, 0px));
}
.fp-tag {
  margin: 0 auto;
  font-size: 11px; letter-spacing: .22em;
  color: rgba(242, 238, 230, .38);
}
.fp-top-spacer { width: 38px; flex: none; }
.fp-ghost-btn {
  width: 38px; height: 38px; flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%; border: 1px solid rgba(255, 255, 255, .1);
  background: rgba(255, 255, 255, .06);
  color: rgba(242, 238, 230, .8);
  cursor: pointer; transition: background .18s ease, color .18s ease, border-color .18s ease;
}
.fp-ghost-btn svg { width: 19px; height: 19px; }
.fp-ghost-btn:hover { background: rgba(255, 255, 255, .13); color: #fff; }
.fp-ghost-btn.on { background: rgba(255, 255, 255, .16); color: #fff; border-color: rgba(255, 255, 255, .22); }
.fp-ghost-btn:active { transform: scale(.94); }

/* ---------- 主视觉（Folia 的歌词位） ---------- */
.fp-stage {
  position: relative;
  flex: 1 1 auto; min-height: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 20px; padding: 8px 26px 46px;
  overflow: hidden;
}
.fp-title {
  margin: 0; text-align: center;
  font-family: var(--font-serif);
  font-weight: 700;
  font-size: clamp(32px, 8.6vw, 92px);
  line-height: 1.12;
  letter-spacing: .015em;
  text-wrap: balance;
  color: #f7f3ea;
}
/* 🔴 别用 background-clip:text 做大字标题：逐字 span 带 transform 时会自建绘制层，
   父级被裁到文字的渐变根本画不出来（实测整行透明，只剩下面的歌手行）。
   现在颜色给到每个字自己：静止是暖白，播放时按字错开变成暖金 + 微光晕，
   暂停即回落 —— 观感接近 Folia 的「正在唱那几字发亮」，且不依赖任何裁剪技巧。 */
.fp-ch {
  display: inline-block;
  opacity: 0;
  transform: translateY(.22em) scale(.985);
  animation: fpChar .46s cubic-bezier(.2, .8, .2, 1) forwards;
  animation-delay: calc(var(--i, 0) * 24ms);
  color: #f7f3ea;
  text-shadow: 0 10px 30px rgba(0, 0, 0, .5);
  transition: color 1.1s ease, text-shadow 1.1s ease;
  transition-delay: calc(var(--i, 0) * 55ms);
}
.fp-title.is-playing .fp-ch {
  color: #ffe3b0;
  text-shadow:
    0 0 22px rgba(255, 190, 110, .38),
    0 10px 30px rgba(0, 0, 0, .5);
}
@keyframes fpChar { to { opacity: 1; transform: none; } }

/* 副行贴到控制条上方（Folia 的翻译行就这么放）：
   大字居中、小字压底，中间留白才不显得空。 */
.fp-sub {
  position: absolute; left: 0; right: 0; bottom: 14px;
  margin: 0; text-align: center;
  font-size: 13px; letter-spacing: .12em;
  color: rgba(242, 238, 230, .52);
}
.fp-sub-artist { color: rgba(242, 238, 230, .62); }
.fp-dot { margin: 0 8px; opacity: .6; }
.fp-empty { margin: 0; font-size: 13px; color: rgba(242, 238, 230, .4); }

/* ---------- 底部控制条 ---------- */
.fp-bar {
  position: relative; flex: none;
  width: 100%; max-width: 760px; margin: 0 auto;
  padding: 0 14px calc(14px + env(safe-area-inset-bottom, 0px));
}
.fp-card {
  padding: 12px 14px 10px;
  border-radius: 22px;
  background: rgba(16, 18, 24, .58);
  border: 1px solid rgba(255, 255, 255, .1);
  box-shadow: 0 22px 54px -24px rgba(0, 0, 0, .9), inset 0 1px 0 rgba(255, 255, 255, .07);
  -webkit-backdrop-filter: blur(26px) saturate(170%);
  backdrop-filter: blur(26px) saturate(170%);
}
.fp-row { display: flex; align-items: center; }
.fp-row--main { gap: 10px; }
.fp-row--progress { gap: 10px; margin-top: 10px; }

.fp-play {
  width: 50px; height: 50px; flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; cursor: pointer;
  background: #f7f4ef; color: #14161b;
  box-shadow: 0 8px 22px -10px rgba(0, 0, 0, .9), inset 0 -1px 0 rgba(0, 0, 0, .12);
  transition: transform .16s ease, filter .16s ease;
}
.fp-play svg { width: 22px; height: 22px; }
.fp-play:hover { filter: brightness(1.06); }
.fp-play:active { transform: scale(.93); }

.fp-step {
  width: 36px; height: 36px; flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; cursor: pointer;
  background: transparent; color: rgba(242, 238, 230, .7);
  transition: color .16s ease, background .16s ease;
}
.fp-step svg { width: 21px; height: 21px; }
.fp-step:hover:not(:disabled) { color: #fff; background: rgba(255, 255, 255, .09); }
.fp-step:disabled { opacity: .28; cursor: default; }

.fp-info {
  flex: 1 1 auto; min-width: 0;
  display: flex; flex-direction: column; gap: 2px;
  padding: 0 4px 0 6px;
}
.fp-info-title {
  font-size: 14px; font-weight: 600; color: #f6f2ea;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fp-info-sub {
  font-size: 11.5px; color: rgba(242, 238, 230, .45);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fp-more { width: 34px; height: 34px; }
.fp-more svg { width: 20px; height: 20px; }

/* 进度：Folia 是一条极细的线，拖到才出现圆点 */
.fp-time {
  flex: none; min-width: 38px; text-align: center;
  font-size: 11px; font-variant-numeric: tabular-nums;
  color: rgba(242, 238, 230, .42);
}
.fp-range {
  flex: 1 1 auto; min-width: 0;
  -webkit-appearance: none; appearance: none;
  height: 16px; background: transparent; cursor: pointer; outline: none;
  --fill: 0%;
}
.fp-range--idle { height: 16px; }
.fp-range::-webkit-slider-runnable-track {
  height: 3px; border-radius: 3px;
  background-image: linear-gradient(90deg,
    rgba(255, 224, 163, .95) var(--fill, 0%),
    rgba(255, 255, 255, .16) var(--fill, 0%));
}
.fp-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 11px; height: 11px; margin-top: -4px;
  border-radius: 50%; background: #fff; border: none;
  box-shadow: 0 0 0 4px rgba(255, 224, 163, .18), 0 2px 6px rgba(0, 0, 0, .55);
  transition: transform .15s ease;
}
.fp-range:active::-webkit-slider-thumb { transform: scale(1.15); }
.fp-range::-moz-range-track {
  height: 3px; border-radius: 3px; background: rgba(255, 255, 255, .16);
}
.fp-range::-moz-range-progress { height: 3px; border-radius: 3px; background: rgba(255, 224, 163, .95); }
.fp-range::-moz-range-thumb {
  width: 11px; height: 11px; border: none; border-radius: 50%; background: #fff;
}

/* ---------- 更多控制面板 ---------- */
.fp-panel {
  position: absolute; left: 14px; right: 14px; bottom: calc(100% - 4px);
  margin-bottom: 10px;
  padding: 14px;
  border-radius: 20px;
  background: rgba(20, 22, 28, .92);
  border: 1px solid rgba(255, 255, 255, .1);
  box-shadow: 0 22px 54px -20px rgba(0, 0, 0, .9), inset 0 1px 0 rgba(255, 255, 255, .06);
  -webkit-backdrop-filter: blur(26px) saturate(170%);
  backdrop-filter: blur(26px) saturate(170%);
}
.fp-panel-lab {
  display: block; margin-bottom: 8px;
  font-size: 11px; letter-spacing: .18em; color: rgba(242, 238, 230, .38);
}
.fp-modes { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.fp-mode {
  padding: 10px 0; border-radius: 12px; cursor: pointer;
  font-size: 13px;
  border: 1px solid rgba(255, 255, 255, .1);
  background: rgba(255, 255, 255, .05);
  color: rgba(242, 238, 230, .74);
  transition: background .16s ease, color .16s ease, border-color .16s ease;
}
.fp-mode:hover { background: rgba(255, 255, 255, .1); color: #fff; }
.fp-mode.on {
  border-color: rgba(255, 224, 163, .5);
  background: rgba(255, 224, 163, .14);
  color: #ffe0a3;
}
.fp-panel-acts { display: flex; gap: 8px; margin-top: 10px; }
.fp-act {
  flex: 1; padding: 10px 0; border-radius: 12px; cursor: pointer;
  font-size: 13px;
  border: 1px solid rgba(255, 255, 255, .1);
  background: transparent;
  color: rgba(242, 238, 230, .7);
  transition: background .16s ease, color .16s ease;
}
.fp-act:hover { background: rgba(255, 255, 255, .08); color: #fff; }
.fp-act--danger { color: #ff9b90; border-color: rgba(255, 120, 100, .28); }
.fp-act--danger:hover { background: rgba(255, 100, 80, .14); color: #ffb7ae; }

.fpmenu-enter-active, .fpmenu-leave-active { transition: opacity .16s ease, transform .16s ease; }
.fpmenu-enter-from, .fpmenu-leave-to { opacity: 0; transform: translateY(8px); }

.mfp-enter-active, .mfp-leave-active { transition: opacity .3s ease; }
.mfp-enter-from, .mfp-leave-to { opacity: 0; }

/* ---------- 矮屏 / 小屏 ---------- */
@media (max-height: 620px) {
  .fp-title { font-size: clamp(24px, 5.2vw, 46px); }
  .fp-stage { gap: 12px; }
  .fp-play { width: 44px; height: 44px; }
  .fp-play svg { width: 20px; height: 20px; }
  .fp-row--progress { margin-top: 6px; }
  .fp-card { padding: 9px 12px 8px; }
}
/* 手机横屏：宽度富裕高度紧张，主视觉让位，控制条贴底即可 */
@media (orientation: landscape) and (max-height: 480px) {
  .fp-top { padding-top: 6px; padding-bottom: 0; }
  .fp-title { font-size: clamp(22px, 4.4vh, 38px); }
  .fp-sub { display: none; }
  .fp-bar { max-width: 620px; }
}
@media (max-width: 400px) {
  .fp-row--main { gap: 6px; }
  .fp-play { width: 46px; height: 46px; }
  .fp-step { width: 32px; height: 32px; }
  .fp-step svg { width: 19px; height: 19px; }
  .fp-info-title { font-size: 13px; }
  .fp-time { min-width: 34px; font-size: 10.5px; }
}

@media (prefers-reduced-motion: reduce) {
  .fp-orb { animation: none; }
  .fp-ch { animation: none; opacity: 1; transform: none; transition: none; }
  .fp * { transition: none !important; }
}
</style>

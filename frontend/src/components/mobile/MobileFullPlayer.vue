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

        <!-- ===== 主视觉：有歌词就滚动歌词，没有就留空（v2.46.327）=====
             夜星：「没有歌词在播放页面时就空着，有就展示」「播放到对应位置歌词需要放大展示」。
             没有歌词时保留歌名当主视觉（这是原本的设计身份），只是不再伪造歌词行。 -->
        <main class="fp-stage">
          <div
            v-if="lyricLines.length"
            ref="lyricBox"
            class="fp-lyric"
            :class="{ 'no-sync': !lyricSynced }"
            @scroll.passive="onLyricScroll"
          >
            <p
              v-for="(l, i) in lyricLines"
              :key="i"
              class="fp-lyric-line"
              :class="{ on: lyricSynced && i === lineIdx, past: lyricSynced && i < lineIdx }"
              @click="lyricSynced && seekToTime(l.t)"
            ><span>{{ l.text }}</span></p>
          </div>

          <template v-else>
            <h1 :key="'t' + (player.curItem?.id || '')" class="fp-title" :class="{ 'is-playing': player.isPlaying }">
              <span v-for="(c, i) in titleChars" :key="i" class="fp-ch" :style="{ '--i': i }">{{ c }}</span>
            </h1>
          </template>

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
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { fmtClock } from '@/utils/format'
import { parseLrc, plainLines, findLine } from '@/utils/lrc'
import { getLyric } from '@/api/music'
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

/* ================= 歌词（v2.46.327） =================
 * 抓取策略：进播放页时按当前曲目 id 拉一次 GET /api/music/{id}/lyric，
 * 结果进 Map 缓存（同一首来回切不重复请求）。歌词是「有就展示、没有就空着」，
 * 所以这里**不做**任何在线抓取的兜底 —— 抓取是用户动作（管理页/去水印工具），
 * 播放时偷偷打外网接口会让进页面变慢，也会抓到不匹配的歌词。
 */
const lyricText = ref('')
const lyricSynced = ref(false)
const lineIdx = ref(-1)
const lyricBox = ref(null)
const lyricCache = new Map()

const lyricLines = computed(() => {
  if (!lyricText.value) return []
  const synced = parseLrc(lyricText.value)
  if (synced.length) return synced
  // 没有时间轴的纯文本：照样展示，但不跟随、不高亮
  return plainLines(lyricText.value)
})

async function loadLyric(id) {
  lyricText.value = ''
  lineIdx.value = -1
  lyricSynced.value = false
  if (!id) return
  if (lyricCache.has(id)) {
    applyLyric(lyricCache.get(id))
    return
  }
  try {
    const res = await getLyric(id)
    const data = res?.data || res || {}
    const content = data.content || ''
    lyricCache.set(id, content)
    // 请求期间可能又换歌了，别把上一首的歌词贴到这一首上
    if (player.curItem?.id === id) applyLyric(content)
  } catch {
    /* 没歌词/接口失败：保持空着 */
  }
}

function applyLyric(content) {
  lyricText.value = content || ''
  lyricSynced.value = parseLrc(content || '').length > 0
  lineIdx.value = -1
  nextTick(() => { if (lyricBox.value) lyricBox.value.scrollTop = 0 })
}

watch(() => player.curItem?.id, (id) => { if (visible.value) loadLyric(id) }, { immediate: true })
watch(visible, (v) => { if (v && player.curItem?.id) loadLyric(player.curItem.id) })

/* 播放进度 → 当前行。
   ⚠️ 不用 `watch(player.progress)`：progress 只跟着 audio 的 timeupdate 走（约 4Hz），
   250ms 一格，歌词会"跳格"；而且用户感觉的快慢也被这个粒度放大。
   这里用 rAF 直接读 audio.currentTime（60fps），行切换才精确。
   偏移量（略滞后 120ms）在 utils/lrc.js 的 findLine 里统一处理。 */
let rafId = 0
function followLoop() {
  rafId = 0
  if (!visible.value || !lyricSynced.value || !lyricLines.value.length) return
  const a = player.audio
  const sec = a && Number.isFinite(a.currentTime) ? a.currentTime : (player.progress || 0)
  const i = findLine(lyricLines.value, sec)
  if (i !== lineIdx.value) lineIdx.value = i
  rafId = requestAnimationFrame(followLoop)
}
function startFollow() {
  if (!rafId && visible.value && lyricSynced.value) rafId = requestAnimationFrame(followLoop)
}
function stopFollow() {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
}
watch([visible, lyricSynced], ([v, synced]) => { if (v && synced) startFollow(); else stopFollow() })
watch(() => player.isPlaying, () => startFollow())
onBeforeUnmount(stopFollow)

/* 手动上下滑：暂停自动跟随 5 秒，别让"我在看前一句"被拽回去 */
let selfScrolling = false
let userScrollAt = 0
function onLyricScroll() {
  if (selfScrolling) return
  userScrollAt = Date.now()
}

/** 当前行滚到中间（用 scrollTop 而不是 transform：行高会随缩放变，transform 会越滚越偏） */
watch(lineIdx, async (i) => {
  if (i < 0) return
  if (Date.now() - userScrollAt < 5000) return   // 用户正在手动翻，别抢
  await nextTick()
  const box = lyricBox.value
  if (!box) return
  const el = box.children[i]
  if (!el) return
  const target = el.offsetTop - box.clientHeight / 2 + el.offsetHeight / 2
  selfScrolling = true
  box.scrollTo({ top: Math.max(0, target), behavior: 'smooth' })
  setTimeout(() => { selfScrolling = false }, 700)
})

function seekToTime(t) {
  if (Number.isFinite(t)) player.seek(t)
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
/* ===== 歌词（v2.46.327）=====
   为什么用 overflow:auto + scrollTop 而不是整体 transform：
   当前行要放大，行高是变的；用 transform 平移会随缩放越滚越偏，
   而 scrollTop 跟着真实布局走，第 100 句和第 3 句一样准。
   上下用 mask 渐隐代替可见边框 —— 歌词从雾里进出，比一条硬裁切线高级。 */
/* 🔴 v2.46.328 两个坑：
   1) 原先是 `padding: 38% 0` —— 百分比内边距是按**宽度**算的，横屏/平板上
      等于上下各加几百像素，滚动区高度远超可视区，歌词从控制条底下穿过去，
      隔着半透明卡片还能看见（夜星截图里"执迷不悟坠入"压在卡片上）。
   2) 歌词一屏铺十几行，没有"正在唱"的聚焦感。
   改成：固定高度 ≈ 6 行 + 上下用伪元素留白（伪元素的 height % 相对容器高度，是对的），
   一屏只看到 6~7 行，其余靠上下滑。 */
.fp-lyric {
  width: 100%;
  flex: 0 1 auto;
  height: min(44vh, 320px);
  min-height: 132px;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none;
  overscroll-behavior: contain;
  padding: 0;
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 16%, #000 84%, transparent 100%);
  mask-image: linear-gradient(180deg, transparent 0, #000 16%, #000 84%, transparent 100%);
}
/* 上下留白：让第一句和最后一句也能滚到正中（height % 相对容器高度） */
.fp-lyric::before,
.fp-lyric::after {
  content: '';
  display: block;
  height: 44%;
}
.fp-lyric::-webkit-scrollbar { display: none; }
.fp-lyric-line {
  margin: 0;
  padding: 8px 2px;
  text-align: center;
  font-size: 15.5px;
  line-height: 1.5;
  color: rgba(255, 255, 255, .46);
  transition: color .26s ease, opacity .26s ease;
  cursor: pointer;
}
.fp-lyric-line > span {
  display: inline-block;
  transition: transform .3s cubic-bezier(.22, 1, .36, 1), font-weight .2s;
  transform-origin: center center;
}
/* 当前行放大（夜星：「播放到对应位置歌词需要放大展示」）：
   用 transform 缩放而不是改 font-size —— 改字号会触发整段重排，
   上一行还没滑走就被撑开，滚动位置会跳。 */
.fp-lyric-line.on { color: #fff; }
.fp-lyric-line.on > span {
  transform: scale(1.24);
  font-weight: 700;
  text-shadow: 0 2px 18px rgba(0, 0, 0, .45);
}
.fp-lyric-line.past { color: rgba(255, 255, 255, .30); }
/* 没有时间轴的纯文本：不放大、不可点，避免"点了没反应" */
.fp-lyric.no-sync .fp-lyric-line { cursor: default; color: rgba(255, 255, 255, .62); }

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

<template>
  <div class="pz-wrap" :class="{ 'is-full': bare }">
    <div v-if="!started" class="pz-gate">
      <b>植物大战僵尸 · 开源同人版</b>
      <p>经典塔防：种下植物、收集阳光，挡住一波波僵尸。关卡、图鉴、商店、副本等玩法都在。</p>
      <i>整包资源约 130MB，首次进入加载会慢一些（加载后由浏览器缓存托管，二次进入很快）。</i>
      <div class="pz-ops">
        <button class="pz-btn primary" @click="startGame">开始游戏</button>
        <a class="pz-btn" :href="SRC" target="_blank" rel="noopener">新标签打开</a>
      </div>
      <span class="pz-note">
        本作为「江南游戏开发社」开源的 PvZ 同人作品，按《长江开源协议》非商业使用；
        版权与素材归原作者，本站仅作自托管展示。
      </span>
    </div>

    <div v-else ref="stageEl" class="pz-stage" :class="{ 'is-rot': rotated }">
      <iframe
        :src="SRC"
        class="pz-frame"
        :style="{ transform: `translate(-50%, -50%) scale(${k})` }"
        title="植物大战僵尸 · 开源同人版"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads allow-pointer-lock"
      />
    </div>
  </div>
</template>

<script setup>
/** 植物大战僵尸（开源同人版）· 站内 iframe 宿主
 *
 * 游戏本体：github.com/jiangnangame/The-Open-Source-Version-Of-PvZ-Travel（纯 JS，无需构建），
 * 已整包自托管到现网 /play/pvz/。
 *
 * 为什么是 iframe：它是第三方整包（1350 个静态文件、固定 900×600 舞台、自带 jQuery/模态窗口与
 * 全局变量），改造成 Vue 组件等于重写整个游戏；iframe 既省事又天然把它的事件/键盘/音频隔离在本页之外。
 *
 * 缩放：游戏内部是 900×600 固定像素布局（.WindowFrame 用 left:50% + margin-left:-450px 居中），
 * 所以 iframe 必须恒为 900×600，靠外层 transform: scale 等比缩放铺满容器 —— 手机端竖屏也能完整看到整幕。
 * 沙箱：同源静态资源 + 游戏自身的 localStorage 存档都需要 allow-same-origin，故与站内工具页保持一致。
 */
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

const SRC = '/play/pvz/index.html'
const GAME_W = 900
const GAME_H = 600

const started = ref(false)
const stageEl = ref(null)
const k = ref(1)
const rotated = ref(false)      // 竖屏设备上的 rotate90 兜底
let ro = null

const props = defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
})

function isTouchDevice() {
  return (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window
}

function isPortrait() {
  return window.innerHeight >= window.innerWidth
}

/* ---------------- 全屏 + 自动横屏（v2.46.224） ----------------
   夜星：「植物大战僵尸应该全屏打开，手机端是自动横屏展示，没有返回按钮」。

   三步走，逐级降级：
   1. `requestFullscreen()` —— 必须**在点击事件的同步调用栈里**，否则浏览器拒绝
   2. `screen.orientation.lock('landscape')` —— 要先进全屏才允许；Android Chrome / 鸿蒙支持，iOS 不支持
   3. `rotate90` 兜底 —— 锁不住且仍是竖屏时，把舞台按视口高宽对调后绕中心旋转 90°，
      视觉上就是横屏（项目里牌桌/时钟/弹幕都是这套兜底，V2462-001 起沿用）
*/
async function enterGameScreen(fsPromise) {
  try { await fsPromise } catch { /* 用户或浏览器拒绝，静默 */ }
  try { await screen.orientation?.lock?.('landscape') } catch { /* iOS 不支持，忽略 */ }
  syncRotation()
}

function syncRotation() {
  // 只有全屏模式才需要转；真横屏或锁屏成功时 isPortrait() 为 false
  rotated.value = !!props.bare && isPortrait()
}

function startGame() {
  // 🔴 requestFullscreen 必须在这里同步调用（用户手势），放到 nextTick 里会被拒
  let fsPromise = null
  if (props.bare && isTouchDevice()) {
    try { fsPromise = document.documentElement.requestFullscreen?.() } catch { fsPromise = null }
  }
  started.value = true
  nextTick(async () => {
    watchStage()
    await enterGameScreen(fsPromise)
  })
}

/** 舞台缩放：全屏模式按宽高取小（保证整幕可见），普通模式按宽度 */
function measure() {
  const el = stageEl.value
  if (!el) return
  const w = el.clientWidth
  const h = el.clientHeight
  if (w <= 0) return
  if (props.bare && h > 0) {
    k.value = Math.min(1.6, Math.max(0.2, Math.min(w / GAME_W, h / GAME_H)))
  } else {
    k.value = Math.min(1.6, Math.max(0.2, w / GAME_W))
  }
}

function watchStage() {
  if (!stageEl.value) return
  measure()
  ro?.disconnect()
  if (typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(measure)
    ro.observe(stageEl.value)
  }
}

/** 设备真的转成横屏 / 用户手动转屏时，撤销 rotate90 兜底 */
function onViewportChange() {
  syncRotation()
  nextTick(measure)
}

watch(started, async (v) => {
  if (!v) return
  await nextTick()
  watchStage()
})

onMounted(() => {
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('orientationchange', onViewportChange)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('orientationchange', onViewportChange)
  try { screen.orientation?.unlock?.() } catch { /* 忽略 */ }
  if (document.fullscreenElement) {
    try { document.exitFullscreen?.()?.catch?.(() => {}) } catch { /* 忽略 */ }
  }
})
</script>

<style scoped>
.pz-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.pz-gate { max-width: 620px; text-align: center; display: flex; flex-direction: column; gap: 10px;
  align-items: center; padding: 22px 20px; border-radius: 16px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.1)); background: var(--color-bg-glass, rgba(127,127,127,.05)); }
.pz-gate b { font-size: 16.5px; color: var(--dp-text, #2b3540); }
.pz-gate p { font-size: 13.5px; line-height: 1.7; color: var(--dp-text2, #45505b); }
.pz-gate i { font-size: 12.5px; font-style: normal; color: var(--dp-text3, #8a8f98); }
.pz-ops { display: flex; gap: 10px; align-items: center; margin-top: 4px; }
.pz-note { font-size: 11.5px; color: var(--dp-text3, #8a8f98); line-height: 1.7; }
.pz-btn { padding: 6px 18px; border-radius: 9px; font-size: 13px; cursor: pointer; text-decoration: none;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--color-bg-glass, rgba(127,127,127,.06));
  color: var(--dp-text2, #45505b); font-family: inherit; transition: all .18s; }
.pz-btn:hover { border-color: var(--yq-accent, #c7a96b); color: var(--yq-accent-deep, var(--yq-accent-bright, #c7a96b)); }
.pz-btn.primary { font-weight: 600; border-color: var(--yq-accent, #c7a96b);
  background: var(--yq-accent, #c7a96b); color: var(--yq-accent-fg, #fff);
  box-shadow: 0 4px 12px var(--yq-accent-glow, rgba(199,169,107,.3)); }
.pz-btn.primary:hover { filter: brightness(1.06); color: var(--yq-accent-fg, #fff); }

.pz-stage { position: relative; width: 100%; max-width: 1020px; aspect-ratio: 3 / 2;
  overflow: hidden; border-radius: 14px; background: #cce8cf;
  border: 1px solid var(--dp-line, rgba(0,0,0,.1)); }
/* iframe 恒为 900×600（游戏内部固定像素布局），靠外层 transform 等比缩放，
   所以定位改成绝对居中 + transform-origin center，缩放多少都居中，不会往右下溢。 */
.pz-frame { display: block; width: 900px; height: 600px; border: 0;
  position: absolute; left: 50%; top: 50%;
  transform-origin: center center; background: #cce8cf; }

/* ================= 全屏模式（v2.46.224，PlayView 传 bare） =================
   整页铺满：去掉圆角/边框/max-width，游戏拿到整块视口。
   外部留白用游戏自身的草地色，缩放后不会出现刺眼的白框。 */
.pz-wrap.is-full {
  position: fixed;
  inset: 0;
  z-index: 1600;
  width: 100%;
  gap: 0;
  justify-content: center;
  padding: 0;
  background: #0b1410;
}
.pz-wrap.is-full .pz-stage {
  width: 100%;
  height: 100%;
  max-width: none;
  aspect-ratio: auto;
  border: 0;
  border-radius: 0;
  background: #0b1410;
}
.pz-wrap.is-full .pz-gate {
  margin: auto;
  background: rgba(255, 255, 255, .04);
  border-color: rgba(255, 255, 255, .12);
}
.pz-wrap.is-full .pz-gate b { color: #eaf3ec; }
.pz-wrap.is-full .pz-gate p { color: #b8c9bd; }
.pz-wrap.is-full .pz-gate i,
.pz-wrap.is-full .pz-note { color: #8fa398; }

/* 🔴 竖屏 rotate90 兜底：把舞台宽高按视口对调后绕中心转 90°，
   视觉上就是横屏（牌桌 / 时钟 / 弹幕都用这套，V2462-001）。
   触摸坐标由浏览器随 transform 一起映射，不需要额外换算。 */
.pz-wrap.is-full .pz-stage.is-rot {
  /* 🔴 必须带上 .pz-wrap.is-full 前缀：上面 `.pz-wrap.is-full .pz-stage` 是 (0,3,0)，
     单写 `.pz-stage.is-rot` 只有 (0,2,0)，width/height/position 会被覆盖掉，旋转直接失效。 */
  position: fixed;
  left: 50%;
  top: 50%;
  width: 100vh;
  height: 100vw;
  transform: translate(-50%, -50%) rotate(90deg);
}
</style>

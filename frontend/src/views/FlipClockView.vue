<template>
  <!-- v2.46.119 翻页时钟工具页（夜星：点击入口自动横屏展示，不要先进竖屏列表再手动转屏）
       进入即全屏舞台；物理横屏正常展示，物理竖屏把内容平面 rotate(90°) 模拟横屏
       （V2462-001 牌桌 rotate90 兜底同款思路）——不需要手动切换横竖屏。
       × 退出回到常规工具页（lg 钟 + 「全屏时钟」按钮可重进）。 -->
  <IslandInnerBase type="tool" title="翻页时钟" subtitle="时分秒 · 经典翻页动画">
    <div class="fc-tool">
      <FlipClock size="lg" />
      <p class="fc-tip">实时走时 · 每秒自动翻页，支持减少动态效果偏好</p>
      <button v-if="isMobile" class="fc-enter" type="button" @click="setFullscreen(true)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9V5a1 1 0 0 1 1-1h4M20 9V5a1 1 0 0 0-1-1h-4M4 15v4a1 1 0 0 0 1 1h4M20 15v4a1 1 0 0 1-1 1h-4" /></svg>
        全屏时钟
      </button>
    </div>

    <Teleport to="body">
      <div v-if="fsOn" class="fc-stage" :class="{ 'is-rot': !landscape }" role="dialog" aria-label="全屏时钟">
        <div class="fc-plane">
          <div class="fc-stage-glow" aria-hidden="true"></div>
          <FlipClock size="full" class="fc-stage-clock" :class="{ 'is-rot': !landscape }" />
          <button class="fc-exit" type="button" aria-label="退出全屏" @click="setFullscreen(false)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
          </button>
        </div>
      </div>
    </Teleport>
  </IslandInnerBase>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import FlipClock from '@/components/mobile/FlipClock.vue'
import { useImmersive } from '@/composables/useImmersive'
import { useIsMobile } from '@/composables/useIsMobile'

/* 全屏只对移动端外壳生效（APK WebView 或 ?m=1），桌面浏览器走常规工具页。
   isMobile 是 computed ref（useIsMobile 返回 { isMobile }）。 */
const { isMobile } = useIsMobile()
const { enterImmersive, exitImmersive } = useImmersive()

const fsOn = ref(false)
const landscape = ref(false)
let immersiveOn = false

function syncOrient() {
  landscape.value = window.innerWidth > window.innerHeight
}

function setFullscreen(on) {
  if (!isMobile.value) return
  fsOn.value = on
  if (on && !immersiveOn) { enterImmersive(); immersiveOn = true }
  else if (!on && immersiveOn) { exitImmersive(); immersiveOn = false }
}

onMounted(() => {
  syncOrient()
  window.addEventListener('resize', syncOrient)
  window.addEventListener('orientationchange', syncOrient)
  // v2.46.119：点击入口进来即全屏（不再要求先进竖屏列表/手动转屏）
  if (isMobile.value) setFullscreen(true)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncOrient)
  window.removeEventListener('orientationchange', syncOrient)
  if (immersiveOn) { exitImmersive(); immersiveOn = false }
})
</script>

<style scoped>
.fc-tool {
  display: flex; flex-direction: column; align-items: center; gap: 18px;
  padding: 26px 0 8px;
}
.fc-tip {
  margin: 0; font-size: 12px; letter-spacing: .06em;
  color: var(--ls-text-3, #8a8f98);
}
/* 重进全屏按钮（× 退出后的工具页回入口），鎏金描边黑胶囊贴玄黄语言 */
.fc-enter {
  display: inline-flex; align-items: center; gap: 8px;
  margin-top: 4px; padding: 10px 22px; border-radius: 999px;
  border: 1px solid rgba(212, 175, 106, .45);
  background: rgba(212, 175, 106, .1); color: var(--ls-gold, #d4af6a);
  font-size: 14px; letter-spacing: .1em; cursor: pointer;
  transition: background .2s, box-shadow .2s;
}
.fc-enter:hover, .fc-enter:active {
  background: rgba(212, 175, 106, .18); box-shadow: 0 4px 18px -6px rgba(212, 175, 106, .4);
}
.fc-enter svg { width: 17px; height: 17px; }

/* ===== 全屏舞台：深墨渐变 + 时钟后极淡鎏金光晕（呼应玄黄 accent，克制不喧宾） ===== */
.fc-stage {
  position: fixed; inset: 0; z-index: 1600; /* 项目全屏统一 1600（>Tab 1500，<ElMessage 2000） */
  background:
    radial-gradient(52% 62% at 50% 42%, rgba(60, 64, 80, .42), transparent 72%),
    linear-gradient(172deg, #101218 0%, #07080c 68%);
  animation: fc-fade .45s ease both;
}
.fc-plane {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
}
/* 竖屏旋转兜底：内容平面旋转 90°（头朝右），宽高互换 100vh×100vw。
   定位用 margin 负半宽（translate(-50%,-50%) 的百分比是元素自身尺寸，
   与 rotate 组合会绕错中心——实测整体偏出视口 422px），transform 只留纯
   rotate，绕元素中心 = 视口中心转，中心不动。 */
.fc-stage.is-rot .fc-plane {
  inset: auto; top: 50%; left: 50%;
  width: 100vh; height: 100vw;
  margin-left: -50vh; margin-top: -50vw;
  transform: rotate(90deg);
}
.fc-stage-glow {
  position: absolute; left: 50%; top: 50%; width: 62vmin; height: 62vmin;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(212, 175, 106, .075), transparent 62%);
  pointer-events: none;
}
.fc-stage-clock { position: relative; }
/* 右上角退出：低存在感圆钮，hover/按压微亮 */
.fc-exit {
  position: absolute; top: 14px; right: 14px;
  width: 40px; height: 40px; padding: 9px;
  border-radius: 50%; border: 1px solid rgba(255, 255, 255, .14);
  background: rgba(255, 255, 255, .06); color: rgba(255, 255, 255, .72);
  cursor: pointer; transition: background .2s, color .2s;
}
.fc-exit:hover, .fc-exit:active { background: rgba(255, 255, 255, .13); color: #fff; }
.fc-exit svg { display: block; width: 100%; height: 100%; }
@keyframes fc-fade { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  .fc-stage { animation: none; }
}
</style>

<template>
  <!-- v2.46.118 翻页时钟工具页（夜星：做成全屏横屏展示）
       竖屏：常规工具页（lg 钟 + 横屏提示）；
       横屏（仅移动端外壳）：Teleport 到 body 的全屏舞台（z-index 1600 项目全屏惯例），
       useImmersive 收起 Tab 栏/邀请 dock，转回竖屏自动退出，右上角 × 也可手动退出。 -->
  <IslandInnerBase type="tool" title="翻页时钟" subtitle="时分秒 · 经典翻页动画">
    <div class="fc-tool">
      <FlipClock size="lg" />
      <p class="fc-tip">实时走时 · 每秒自动翻页，支持减少动态效果偏好</p>
      <p v-if="isMobile" class="fc-tip fc-hint">手机横屏，自动进入全屏时钟</p>
    </div>

    <Teleport to="body">
      <div v-if="fsOn" class="fc-stage" role="dialog" aria-label="全屏时钟">
        <div class="fc-stage-glow" aria-hidden="true"></div>
        <FlipClock size="full" class="fc-stage-clock" />
        <button class="fc-exit" type="button" aria-label="退出全屏" @click="onExit">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>
    </Teleport>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import FlipClock from '@/components/mobile/FlipClock.vue'
import { useImmersive } from '@/composables/useImmersive'
import { useIsMobile } from '@/composables/useIsMobile'

/* 全屏只对移动端外壳生效（APK WebView 或 ?m=1）：桌面浏览器窗口压宽压高
   不该突变全屏。isMobile 是 computed ref（useIsMobile 返回 { isMobile }）。 */
const { isMobile } = useIsMobile()
const { enterImmersive, exitImmersive } = useImmersive()

const landscape = ref(false)
const manualExit = ref(false)          // 右上角 × 退出后，本段横屏不再自动弹；转竖屏重置
const fsOn = computed(() => isMobile.value && landscape.value && !manualExit.value)
let immersiveOn = false

function syncStage() {
  const l = window.innerWidth > window.innerHeight
  landscape.value = l
  if (l && !manualExit.value && !immersiveOn) { enterImmersive(); immersiveOn = true }
  else if (!l) {
    manualExit.value = false
    if (immersiveOn) { exitImmersive(); immersiveOn = false }
  }
}

function onExit() {
  manualExit.value = true
  if (immersiveOn) { exitImmersive(); immersiveOn = false }
}

onMounted(() => {
  syncStage()
  window.addEventListener('resize', syncStage)
  window.addEventListener('orientationchange', syncStage)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncStage)
  window.removeEventListener('orientationchange', syncStage)
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
.fc-hint { color: var(--ls-gold, #d4af6a); opacity: .85; letter-spacing: .12em; }

/* ===== 全屏舞台：深墨渐变 + 时钟后极淡鎏金光晕（呼应玄黄 accent，克制不喧宾） ===== */
.fc-stage {
  position: fixed; inset: 0; z-index: 1600; /* 项目全屏统一 1600（>Tab 1500，<ElMessage 2000） */
  display: flex; align-items: center; justify-content: center;
  background:
    radial-gradient(52% 62% at 50% 42%, rgba(60, 64, 80, .42), transparent 72%),
    linear-gradient(172deg, #101218 0%, #07080c 68%);
  animation: fc-fade .45s ease both;
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
  position: absolute; top: max(12px, env(safe-area-inset-top)); right: 14px;
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

<template>
  <div class="pz-wrap">
    <div v-if="!started" class="pz-gate">
      <b>植物大战僵尸 · 开源同人版</b>
      <p>经典塔防：种下植物、收集阳光，挡住一波波僵尸。关卡、图鉴、商店、副本等玩法都在。</p>
      <i>整包资源约 130MB，首次进入加载会慢一些（加载后由浏览器缓存托管，二次进入很快）。</i>
      <div class="pz-ops">
        <button class="pz-btn primary" @click="started = true">开始游戏</button>
        <a class="pz-btn" :href="SRC" target="_blank" rel="noopener">新标签打开</a>
      </div>
      <span class="pz-note">
        本作为「江南游戏开发社」开源的 PvZ 同人作品，按《长江开源协议》非商业使用；
        版权与素材归原作者，本站仅作自托管展示。
      </span>
    </div>

    <div v-else ref="stageEl" class="pz-stage">
      <iframe
        :src="SRC"
        class="pz-frame"
        :style="{ transform: `scale(${k})` }"
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
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'

defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
})

const SRC = '/play/pvz/index.html'
const GAME_W = 900

const started = ref(false)
const stageEl = ref(null)
const k = ref(1)
let ro = null

/** 舞台宽高固定 3:2；缩放系数 = 舞台实宽 / 900 */
function measure() {
  const el = stageEl.value
  if (!el) return
  const w = el.clientWidth
  if (w > 0) k.value = Math.min(1.6, Math.max(0.2, w / GAME_W))
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

watch(started, async (v) => {
  if (!v) return
  await nextTick()
  watchStage()
})

onBeforeUnmount(() => { ro?.disconnect() })
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
.pz-frame { display: block; width: 900px; height: 600px; border: 0;
  transform-origin: 0 0; background: #cce8cf; }
</style>

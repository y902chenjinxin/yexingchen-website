<template>
  <!-- v2.46.217 音乐全屏播放器改成独立路由。
       以前它是 App.vue 里的 `<MobileFullPlayer v-model="fullPlayer">` 覆盖层：
       - 不参与路由 → 手机系统返回键直接退出当前页面（甚至退出音乐页），而不是收起播放器
       - 只有手机端渲染（`v-if="isMobile"`）→ PC 上根本没有全屏播放器可用
       现在给它一个真正的 URL，两端共用，浏览器箭头 / 系统返回键都能正确退出。 -->
  <!-- 同 NovelReadView：必须有真实单根，否则路由 transition 的 out-in 会卡住 -->
  <div class="mpv-root">
    <MobileFullPlayer page :model-value="true" @update:model-value="onClose" />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MobileFullPlayer from '@/components/mobile/MobileFullPlayer.vue'
import { usePlayerStore } from '@/stores/player'
import { useFullscreenPage } from '@/composables/useFullscreenPage'

/* 真全屏：隐藏侧栏/顶栏/TabBar/播放条/桌宠 */
useFullscreenPage()

const router = useRouter()
const player = usePlayerStore()

function onClose() {
  if (window.history.length > 1) router.back()
  else router.replace('/music')
}

onMounted(() => {
  // 没有正在播放的内容（例如直接输 URL 进来）：别留一个空播放器
  if (!player.curItem) router.replace('/music')
})
</script>

<style scoped>
.mpv-root {
  min-height: 100vh;
  min-height: 100dvh;
}
</style>

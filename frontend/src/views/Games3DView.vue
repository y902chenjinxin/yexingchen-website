<template>
  <div class="g3d-root" :class="{ 'is-lobby': phase === 'lobby' }">
    <!-- 背景装饰（需求4：非全黑，冷蓝光晕 + 点阵 + 光点） -->
    <div class="g3d-deco">
      <i class="g3d-orb a"></i>
      <i class="g3d-orb b"></i>
      <i class="g3d-orb c"></i>
    </div>

    <!-- 大厅：选择游戏 → 开局（需求1、2） -->
    <div v-if="phase === 'lobby'" class="g3d-lobby">
      <div class="g3d-lobby-head">
        <h1>3D 棋牌</h1>
        <p>选择一款牌局，体验真 3D 透视牌桌</p>
      </div>

      <div class="g3d-lobby-cards">
        <button class="g3d-lobby-card" @click="start('mahjong')">
          <div class="lc-icon"><AppIcon icon="🀄" :size="46" /></div>
          <span class="lc-name">3D 麻将</span>
          <div class="lc-desc">四川麻将 · 胡牌即结束<br />四人一桌 · 碰杠胡听牌</div>
          <span class="lc-go">开局</span>
        </button>

        <button class="g3d-lobby-card" @click="start('guandan')">
          <div class="lc-icon"><AppIcon icon="🎴" :size="46" /></div>
          <span class="lc-name">3D 掼蛋</span>
          <div class="lc-desc">两副牌 · 四人两队<br />牌型升级 · 逢人配</div>
          <span class="lc-go">开局</span>
        </button>
      </div>
    </div>

    <!-- 牌局：各自独立的 3D 棋盘（自带顶栏与透明背景） -->
    <component
      v-else
      :is="game === 'mahjong' ? Mahjong3DBoard : Guandan3DBoard"
      @exit="backToLobby"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useImmersive } from '@/composables/useImmersive'
import Guandan3DBoard from '@/components/games3d/Guandan3DBoard.vue'
import Mahjong3DBoard from '@/components/games3d/Mahjong3DBoard.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import '@/assets/styles/games3d.css'

/* ---------- 横屏沉浸态（v2.46.114 起）----------
 * 横屏时 App 底部 Tab 栏（fixed z-index 1500）会压住手牌；进入横屏即
 * enterImmersive 让 App.vue 收起 Tab 栏，竖屏恢复。引用计数防重复 / 漏 exit。 */
const { enterImmersive, exitImmersive } = useImmersive()
let immersiveOn = false
function syncImmersive() {
  const landscape = window.innerWidth > window.innerHeight
  if (landscape && !immersiveOn) { enterImmersive(); immersiveOn = true }
  else if (!landscape && immersiveOn) { exitImmersive(); immersiveOn = false }
}

const phase = ref('lobby')   // lobby | play
const game = ref(null)       // 'mahjong' | 'guandan'

function start(g) {
  game.value = g
  phase.value = 'play'
}
function backToLobby() {
  phase.value = 'lobby'
  game.value = null
}

onMounted(() => {
  syncImmersive()
  window.addEventListener('resize', syncImmersive)
  window.addEventListener('orientationchange', syncImmersive)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', syncImmersive)
  window.removeEventListener('orientationchange', syncImmersive)
  if (immersiveOn) { exitImmersive(); immersiveOn = false }
})
</script>

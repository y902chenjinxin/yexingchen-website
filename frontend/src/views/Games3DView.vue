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
        <p>四张桌：象棋 / 五子棋 是单人挑战，麻将 / 掼蛋 是四人牌局</p>
      </div>

      <div class="g3d-lobby-cards">
        <!-- 棋类（v2.46.277）：这两张是**单人 vs AI**，不接在线 ——
             棋类的在线要走服务端权威走子校验，掼蛋那套是牌桌事件流，不是一回事。 -->
        <button class="g3d-lobby-card" @click="start('xiangqi')">
          <div class="lc-icon"><AppIcon icon="♟" :size="46" /></div>
          <span class="lc-name">3D 象棋</span>
          <div class="lc-desc">标准九路十行 · 红先<br />三档 AI · 悔棋 / 将死提示</div>
          <span class="lc-go">单人开局</span>
          <span class="lc-go alt" @click.stop="start('xiangqi', true)">邀人对局</span>
        </button>

        <button class="g3d-lobby-card" @click="start('gomoku')">
          <div class="lc-icon"><AppIcon icon="⚫" :size="46" /></div>
          <span class="lc-name">3D 五子棋</span>
          <div class="lc-desc">15 路标准盘 · 无禁手<br />四层搜索 AI · 五连高亮</div>
          <span class="lc-go">单人开局</span>
          <span class="lc-go alt" @click.stop="start('gomoku', true)">邀人对局</span>
        </button>

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

      <!-- 在线对局入口（v2.46.262）
           3D 这两张牌桌是**单人练习**（AI 陪打），在线对局走 2D 牌桌 ——
           手牌信息密度更高、进贡/还贡/反应窗口都在那边做全了。
           这里把「我的牌桌」入口摆出来，夜星就不用绕回棋牌大厅找房间。 -->
      <div class="g3d-lobby-online">
        <button class="g3d-online-btn" @click="roomsOpen = true">
          <AppIcon icon="👥" :size="18" />
          <span>我的牌桌<em v-if="roomCount">（{{ roomCount }}）</em></span>
        </button>
        <p class="g3d-online-hint">
          和真人打：邀请家人开局 → 进入 2D 在线牌桌（手牌看得更清，掉线还能续）
        </p>
      </div>
    </div>

    <!-- 牌局：各自独立的 3D 棋盘（自带顶栏与透明背景） -->
    <component
      v-else
      :is="boardComp"
      :online="onlineGame"
      @exit="backToLobby"
    />

    <!-- 我的牌桌（v2.46.262）：复用棋牌大厅那只抽屉，teleport 到 body，层级不受本页影响 -->
    <MyRoomsDrawer
      v-model:open="roomsOpen"
      @update:count="roomCount = $event"
      @open-room="openRoom"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useImmersive } from '@/composables/useImmersive'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import Guandan3DBoard from '@/components/games3d/Guandan3DBoard.vue'
import Mahjong3DBoard from '@/components/games3d/Mahjong3DBoard.vue'
import Xiangqi3DBoard from '@/components/games3d/Xiangqi3DBoard.vue'
import Gomoku3DBoard from '@/components/games3d/Gomoku3DBoard.vue'
import MyRoomsDrawer from '@/components/games/MyRoomsDrawer.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import '@/assets/styles/games3d.css'

/* ---------- 横屏沉浸态（v2.46.114 起）----------
 * 横屏时 App 底部 Tab 栏（fixed z-index 1500）会压住手牌；进入横屏即
 * enterImmersive 让 App.vue 收起 Tab 栏，竖屏恢复。引用计数防重复 / 漏 exit。 */
const { enterImmersive, exitImmersive } = useImmersive()

/* v2.46.217 真全屏：3D 牌桌是整页体验，不该被侧栏/顶栏切掉一块 ——
   以前 g3d-root 虽然 height:100vh，但宽度被侧栏挤掉，牌桌中心偏移。
   进入本页即隐藏站点外壳，浏览器返回键 / 系统返回键直接退出本页。 */
useFullscreenPage()
let immersiveOn = false
function syncImmersive() {
  const landscape = window.innerWidth > window.innerHeight
  if (landscape && !immersiveOn) { enterImmersive(); immersiveOn = true }
  else if (!landscape && immersiveOn) { exitImmersive(); immersiveOn = false }
}

const phase = ref('lobby')   // lobby | play
const game = ref(null)       // 'mahjong' | 'guandan' | 'xiangqi' | 'gomoku'
/** 棋类的在线模式：牌类两张没有 online，传下去会被忽略（落在根元素当属性） */
const onlineGame = ref(false)

/* 4 张桌按需挂载：牌桌和棋盘是两套完全不同的舞台，不要一次全 import 进来 */
const BOARDS = {
  mahjong: Mahjong3DBoard,
  guandan: Guandan3DBoard,
  xiangqi: Xiangqi3DBoard,
  gomoku: Gomoku3DBoard,
}
const boardComp = computed(() => BOARDS[game.value] || Guandan3DBoard)

/* 我的牌桌（v2.46.262）：3D 这两张是单人练习，在线对局走 2D 牌桌。
   入口放在大厅，省得夜星再绕回棋牌大厅找房间。 */
const router = useRouter()
const roomsOpen = ref(false)
const roomCount = ref(0)
function openRoom(it) {
  roomsOpen.value = false
  if (it?.route) router.push(it.route)
}

function start(g, online = false) {
  game.value = g
  onlineGame.value = !!online && (g === 'xiangqi' || g === 'gomoku')
  phase.value = 'play'
}
function backToLobby() {
  phase.value = 'lobby'
  game.value = null
  onlineGame.value = false
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

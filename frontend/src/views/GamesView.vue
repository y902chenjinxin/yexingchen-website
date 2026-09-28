<template>
  <IslandInnerBase type="tool" title="棋类游戏" subtitle="五子棋 · 黑白棋 · 数独 · 飞行棋 · 纯本地可玩">
    <div class="games-tool">
      <div class="gm-tabs">
        <button
          v-for="g in gamelist"
          :key="g.key"
          class="gm-tab"
          :class="{ active: tab === g.key }"
          @click="tab = g.key"
        >{{ g.label }}</button>
      </div>

      <!-- KeepAlive：切 tab 不丢对局（数独计时/棋局状态都在组件内部） -->
      <KeepAlive>
        <component
          :is="current.component"
          :key="current.key + (pendingRoom.id && pendingRoom.game === current.key ? '-' + pendingRoom.id : '')"
          :join-room-id="pendingRoom.game === current.key ? pendingRoom.id : 0"
        />
      </KeepAlive>
    </div>
  </IslandInnerBase>
</template>

<script setup>
/** 棋类游戏（v2.40.24，由「摸鱼小游戏」改名重构）。
 * 框架：可扩展的 tab 容器 —— 每个游戏一个自包含组件（棋盘/规则/AI/状态都在组件内部），
 * 加新游戏 = 写一个组件 + 在 gamelist 里加一行，页面其余部分不动。
 * 历史说明：2048 与电子木鱼已按需求下线（不符合棋类定位）；
 * 贪吃蛇/扫雷暂留（夜星未点名删除，后续可再收）。
 */
import { ref, computed, watch, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'

const gamelist = [
  { key: 'gomoku', label: '五子棋', component: defineAsyncComponent(() => import('@/components/games/GomokuBoard.vue')) },
  { key: 'othello', label: '黑白棋', component: defineAsyncComponent(() => import('@/components/games/OthelloBoard.vue')) },
  { key: 'sudoku', label: '数独', component: defineAsyncComponent(() => import('@/components/games/SudokuBoard.vue')) },
  { key: 'ludo', label: '飞行棋', component: defineAsyncComponent(() => import('@/components/games/LudoEmbed.vue')) },
  { key: 'snake', label: '贪吃蛇', component: defineAsyncComponent(() => import('@/components/games/SnakeGame.vue')) },
  { key: 'mine', label: '扫雷', component: defineAsyncComponent(() => import('@/components/games/MineGame.vue')) },
]
const tab = ref('gomoku')
const current = computed(() => gamelist.find(g => g.key === tab.value) || gamelist[0])

/* ---------- 从全局邀请弹窗跳转进来（/tool/games?room=ID&game=gomoku） ---------- */
const route = useRoute()
const router = useRouter()
const pendingRoom = ref({ id: 0, game: '' })
watch(() => route.query.room, (v) => {
  const id = Number(v) || 0
  const game = String(route.query.game || '')
  if (id && gamelist.some(g => g.key === game)) {
    pendingRoom.value = { id, game }
    tab.value = game
    router.replace({ query: {} })   // 消费掉，避免刷新重复进入
  }
}, { immediate: true })
</script>

<style scoped>
.games-tool { display: flex; flex-direction: column; align-items: center; gap: 14px; }
.gm-tabs { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.gm-tab {
  padding: 8px 22px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 13.5px;
}
.gm-tab.active { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }

@media (max-width: 480px) {
  .gm-tab { padding: 7px 14px; font-size: 12.5px; }
}
</style>

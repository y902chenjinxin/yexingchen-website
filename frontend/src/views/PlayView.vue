<template>
  <!-- v2.46.144 两款单机游戏的侧栏直达页。
       起因：只有 GamesView（棋类游戏页）内部挂了这两款游戏，侧栏「娱乐」分组没有入口，
       夜星反馈「我在侧边栏娱乐模块没有看到」。
       同一页面按路由 meta.game 分流：roadrash → 自绘 Canvas 移植版；pvz → 开源同人版 iframe 宿主。 -->
  <IslandInnerBase type="tool" :title="cfg.title" :subtitle="cfg.subtitle">
    <template #toolbar>
      <button class="pv-hall" type="button" @click="goHall">
        <AppIcon icon="↩" :size="14" /> 游戏大厅
      </button>
    </template>

    <div class="pv-main">
      <component :is="cfg.component" :bare="true" :initial-mode="cfg.mode" />
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import RoadRashGame from '@/components/games/RoadRashGame.vue'
import PvzEmbed from '@/components/games/PvzEmbed.vue'
import EmulatorHost from '@/components/games/EmulatorHost.vue'

const route = useRoute()
const router = useRouter()

/** 键与 route.meta.game 对齐；mode 留空 = 交给组件按端自己选档（手机 easy / 桌面 classic） */
const MAP = {
  roadrash: {
    title: '暴力摩托',
    subtitle: '伪 3D 公路竞速 · 近身格斗 · 跑满全程即通关',
    component: RoadRashGame,
    mode: '',
  },
  emulator: {
    title: '经典模拟器',
    subtitle: 'EmulatorJS · ROM 本地加载 · 不上传服务器',
    component: EmulatorHost,
    mode: '',
  },
  pvz: {
    title: '植物大战僵尸',
    subtitle: '开源同人版 · 经典塔防 · 关卡 / 图鉴 / 商店',
    component: PvzEmbed,
    mode: '',
  },
}

const cfg = computed(() => MAP[route.meta.game] || MAP.roadrash)

function goHall() {
  router.push('/tool/games')
}
</script>

<style scoped>
.pv-main { padding: 0 0 12px; }
.pv-hall {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; cursor: pointer; font-size: 12.5px;
  border-radius: 999px; color: var(--dp-text2, #45505b);
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0, 0, 0, .14)));
  background: var(--color-bg-glass, rgba(127, 127, 127, .06));
  transition: border-color .2s, color .2s;
}
.pv-hall:hover { color: var(--yq-accent, #c7a96b); border-color: var(--yq-accent, #c7a96b); }
</style>

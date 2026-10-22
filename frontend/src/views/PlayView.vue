<template>
  <!-- v2.46.144 两款单机游戏的侧栏直达页。
       起因：只有 GamesView（棋类游戏页）内部挂了这两款游戏，侧栏「娱乐」分组没有入口，
       夜星反馈「我在侧边栏娱乐模块没有看到」。
       同一页面按路由 meta.game 分流：roadrash → 自绘 Canvas 移植版；pvz → 开源同人版 iframe 宿主。 -->
  <!-- v2.46.217 真全屏：以前这三个游戏被塞进 IslandInnerBase 卡片，
       上下左右都是站点外壳，画布只分到中间一小块 —— 夜星说的"页面里嵌入小页面"。
       游戏是纯体验型内容，直接整页：只留一条极简顶栏（返回大厅），
       其余全部给游戏；浏览器返回键 / 手机返回键退出本页。 -->
  <!-- v2.46.224：去掉顶栏（夜星：全屏打开，不要返回按钮，靠浏览器/手机自带返回）。
       游戏本身就是整块内容，任何页内 UI 都是干扰。 -->
  <div class="pv-page">
    <div class="pv-main">
      <component :is="cfg.component" :bare="true" :initial-mode="cfg.mode" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useFullscreenPage } from '@/composables/useFullscreenPage'
import { useRoute } from 'vue-router'
import PvzEmbed from '@/components/games/PvzEmbed.vue'

/* 真全屏页：隐藏侧栏/顶栏/TabBar/页脚，游戏拿满整块视口 */
useFullscreenPage()

const route = useRoute()

/** 键与 route.meta.game 对齐；mode 留空 = 交给组件按端自己选档（手机 easy / 桌面 classic） */
const MAP = {
  pvz: {
    title: '植物大战僵尸',
    subtitle: '开源同人版 · 经典塔防 · 关卡 / 图鉴 / 商店',
    component: PvzEmbed,
    mode: '',
  },
}

const cfg = computed(() => MAP[route.meta.game] || MAP.pvz)

</script>

<style scoped>
/* 整页游戏容器：fixed 是为了不依赖父容器高度链（祖先有 transform 时也能铺满） */
.pv-page {
  position: fixed;
  inset: 0;
  z-index: 1600;
  display: flex;
  flex-direction: column;
  background: var(--dp-bg, #f7f5f0);
  color: var(--dp-text, #2b2b2b);
  padding-top: env(safe-area-inset-top, 0);
  padding-bottom: env(safe-area-inset-bottom, 0);
}
.pv-main {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  padding: 0;
}
.pv-main > * { flex: 1 1 0; min-height: 0; min-width: 0; }
.pv-hall {
  display: inline-flex; align-items: center; gap: 5px;
  flex-shrink: 0;
  padding: 6px 12px; cursor: pointer; font-size: 12.5px;
  border-radius: 999px; color: var(--dp-text2, #45505b);
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0, 0, 0, .14)));
  background: var(--color-bg-glass, rgba(127, 127, 127, .06));
  transition: border-color .2s, color .2s;
}
.pv-hall:hover { color: var(--yq-accent, #c7a96b); border-color: var(--yq-accent, #c7a96b); }
</style>

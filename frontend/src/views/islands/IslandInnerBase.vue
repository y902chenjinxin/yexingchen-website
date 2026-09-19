<template>
  <div class="island-inner" :class="`island-inner-${type}`">
    <!-- 内容区（背景/装饰由 desktop-product.css 主题化接管，避免重复渲染） -->
    <div class="inner-content">
      <header class="inner-header">
        <!-- 桌面端：侧栏已接管返回导航，不再显示「返回工作台」按钮；手机端保留（手机端无侧栏，靠此按钮返回） -->
        <button v-if="isMobile" class="back-btn" @click="goBack">
          <span class="back-icon">←</span>
          <span class="back-text">返回工作台</span>
        </button>
        <h1 class="island-title">{{ title }}</h1>
        <p class="island-subtitle">{{ subtitle }}</p>
        <div v-if="$slots.toolbar" class="inner-toolbar"><slot name="toolbar" /></div>
      </header>

      <main class="inner-main">
        <slot></slot>
      </main>

      <!-- 网安/备案标识：极简单行（白天浅 / 夜间紫玻璃） -->
      <SiteFooter variant="dark" class="inner-footer" />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useIsMobile } from '@/composables/useIsMobile'

const router = useRouter()
const { isMobile } = useIsMobile()

const props = defineProps({
  type: {
    type: String,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    required: true
  }
})

function goBack() {
  // 统一「回来源页优先」：有浏览历史则返回上一页；直接落地（无历史）才回工作台。
  if (window.history.length > 1) { try { window.history.back(); return } catch { /* fallthrough */ } }
  router.push('/workbench')
}
</script>

<style scoped>
.island-inner {
  position: fixed;
  inset: 0;
  /* 岛屿内容为普通全屏容器：z-index 需低于 Element 弹层（约 2000）与桌宠配置面板，
     否则会盖住挂到 body 的上传/编辑/删除等弹窗，表现为"点击按钮没反应" */
  z-index: 1;
  background: var(--ls-bg1);
  overflow: hidden;
}

/* 桌面端：改为「文档流」布局 —— 整页随滚动一起移动，页脚在内容末尾
   （旧实现是 fixed 容器 + 内部滚动，导致页脚被钉在视口底部、像固定条） */
#app:not(.is-mobile) .island-inner {
  position: relative;
  inset: auto;
  width: 100%;
  height: auto;
  min-height: 100vh;
  overflow: visible;
}
/* 内容列：至少占满首屏，页脚自然被推到最下方 */
#app:not(.is-mobile) .inner-content {
  height: auto;
  min-height: 100vh;
}
/* 主区不再内部滚动，交还文档滚动 */
#app:not(.is-mobile) .inner-main {
  overflow: visible;
}

/* 背景由 desktop-product.css J 段按 day/night 主题化接管（双晕染 / 纯色 + 单晕染），
   这里不再写 ::before 渐变与 ::after 噪点，避免与主题层冲突。 */

.inner-content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.inner-header {
  /* 桌面端避让顶部 60px 全局固定顶栏（GlobalTopBar z-index:1000 悬浮其上） */
  padding: 84px 40px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: 8px;
  color: var(--dp-text2);
  cursor: pointer;
  transition: all 0.18s ease;
  width: fit-content;
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.back-btn:hover {
  border-color: var(--dp-accent);
  color: var(--dp-accent);
  background: var(--dp-accent-faint);
}

.back-icon { font-size: 14px; }
.back-text { font-size: 13px; }

/* 标题：无衬线 + 主色重染（白天蓝紫、晚间紫罗兰，自动随主题） */
.island-title {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Microsoft YaHei", "Helvetica Neue", "Noto Sans SC", sans-serif;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -.01em;
  color: var(--dp-text);
  margin: 14px 0 2px;
}

.island-subtitle {
  font-size: 13px;
  color: var(--dp-text2);
  letter-spacing: 0;
  font-weight: 400;
}

.inner-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
  flex-wrap: wrap;
}

.inner-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 40px 20px;
  overflow-y: auto;
}

.inner-footer {
  flex-shrink: 0;
  padding: 8px 40px 8px;
  border-top: 1px solid var(--dp-line);
  background: var(--dp-bg);
  font-size: 11px;
}

:root[data-theme="night"] .inner-footer {
  background: rgba(11, 11, 18, .55);
  -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px);
}

/* 桌面缩放(>100%)或较窄视口时收敛留白与字号 */
@media (max-width: 1100px) {
  .inner-header { padding: 80px 26px 12px; }
  .inner-main { padding: 14px 26px 16px; }
  .inner-footer { padding: 8px 26px 8px; }
  .island-title { font-size: 24px; }
}
@media (max-width: 760px) {
  .inner-header { padding: 18px 16px 10px; }
  .inner-main { padding: 12px 16px 12px; }
  .inner-footer { padding: 8px 16px calc(8px + env(safe-area-inset-bottom, 0px)); }
  .island-title { font-size: 22px; }
  .island-subtitle { font-size: 13px; }
}

/* ---------- 手机端：iOS 大标题外壳（紧凑返回章，背景由 mobile-* 主题接管） ---------- */
@media (max-width: 767px) {
  .island-inner { background: var(--ls-bg, #0d1a15); }

  .inner-header {
    position: sticky; top: 0; z-index: 10;
    flex-direction: row; flex-wrap: wrap; align-items: center;
    gap: 6px 10px;
    padding: calc(env(safe-area-inset-top, 0px) + 10px) 18px 12px;
    border-bottom: 1px solid transparent;
  }

  /* 返回 = 紧凑圆角返回章，仅图标 */
  .back-btn {
    padding: 10px; margin-right: 4px;
    width: 40px; height: 40px; flex: none;
    justify-content: center;
    border-radius: 12px;
  }
  .back-text { display: none; }
  .back-icon { font-size: 20px; line-height: 1; }

  .island-title { margin: 0; flex: 1; min-width: 0; font-size: clamp(22px, 6vw, 30px); }
  .island-subtitle { flex-basis: 100%; margin: 0; font-size: 13px; }

  .inner-toolbar { flex-basis: 100%; margin: 2px 0 0; gap: 8px; }
  .inner-main { padding: 16px 16px 28px; }
  .inner-footer { padding: 8px 16px calc(10px + env(safe-area-inset-bottom, 0px)); }
}
</style>
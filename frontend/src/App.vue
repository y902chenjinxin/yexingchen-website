<template>
  <div id="app" :class="{ 'is-mobile': isMobile }">
    <el-config-provider :locale="zhCn">
    <!-- Skip Link键盘导航 -->
    <a href="#main-content" class="skip-link">跳转到内容</a>

    <!-- 路由视图：移动端缓存三个底部 Tab 首页，切 Tab 不再重挂载而闪白；桌面不缓存维持现状 -->
    <router-view v-if="!showInitialLoading" id="main-content" v-slot="{ Component }">
      <keep-alive :include="keepAliveNames">
        <component :is="Component" />
      </keep-alive>
    </router-view>

    <!-- 登录后全站常驻：桌面顶栏（悬浮）；移动端用独立沉浸式外壳，不显示 ✓ -->
    <GlobalTopBar v-if="!showInitialLoading && auth.isLoggedIn && !isMobile" />

    <!-- 登录后桌面端：左侧导航（默认展开，可收起，按玉简分组；顶栏不动） -->
    <DesktopSidebar v-if="!showInitialLoading && auth.isLoggedIn && !isMobile" />

    <!-- 登录后移动端：底部两 Tab 主导航（主页/我的） -->
    <MobileTabBar v-if="!showInitialLoading && auth.isLoggedIn && isMobile" />

    <!-- 登录后桌面端：AI 对话悬浮入口（每页常驻，替代原顶栏 AI 入口） -->
    <FloatingAiButton v-if="!showInitialLoading && auth.isLoggedIn && !isMobile" />

    <!-- 登录后全站常驻桌宠（音乐岛内容列表页隐藏：桌宠固定右下会压住列表行/最后一张卡片） -->
    <WhaleCompanion v-if="!showInitialLoading && auth.isLoggedIn && showWhale" />

    <!-- 登录后全站底部播放条（播放时出现）-->
    <NowPlayingBar v-if="!showInitialLoading && auth.isLoggedIn" @open-full="fullPlayer = true" />

    <!-- 移动端全屏播放器（点迷你播放条信息区展开） -->
    <MobileFullPlayer v-if="isMobile" v-model="fullPlayer" />

    <!-- 登录后全站底部网安/备案标识（工作台与岛屿/工具内容页各自渲染页脚，此处不再重复） -->
    <SiteFooter v-if="!showInitialLoading && auth.isLoggedIn && showGlobalFooter" variant="dark" />
    </el-config-provider>
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useAuthStore } from '@/stores/auth'
import { usePrefsStore, applyTheme } from '@/stores/prefs'
import GlobalTopBar from '@/components/GlobalTopBar.vue'
import DesktopSidebar from '@/components/desktop/DesktopSidebar.vue'
import FloatingAiButton from '@/components/desktop/FloatingAiButton.vue'
import MobileTabBar from '@/components/MobileTabBar.vue'
import MobileFullPlayer from '@/components/mobile/MobileFullPlayer.vue'
import NowPlayingBar from '@/components/NowPlayingBar.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import { useIsMobile } from '@/composables/useIsMobile'

// WhaleCompanion 较大（视频背景 + 动画控制），按需异步加载以减小首屏 bundle
const WhaleCompanion = defineAsyncComponent(() => import('@/components/effects/WhaleCompanion.vue'))

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const prefs = usePrefsStore()
const { isMobile } = useIsMobile()

// 移动端缓存底部两 Tab 首页组件（切 Tab 不重挂载、不闪白）；桌面 include 为空 → 不缓存
const keepAliveNames = computed(() => isMobile.value ? ['WorkbenchView', 'ProfileView'] : [])

// 移动端全屏播放器开关
const fullPlayer = ref(false)

// 桌宠偏好按用户隔离：登录用户或切换账号时重新绑定，读取各自的 localStorage 记录
watch(
  () => auth.user?.id,
  (uid) => prefs.bindUser(uid),
  { immediate: true },
)

// 工作台与岛屿/工具内容页在页面内部各自渲染页脚，无需全站级重复页脚
const showGlobalFooter = computed(() => {
  const p = route.path
  if (p === '/workbench') return false
  if (/^\/(music|novel|video|log|tool)/.test(p)) return false
  return true
})

// 音乐岛内容列表页隐藏桌宠：桌宠固定右下(z-index:1800)会压住音乐列表行及最后一张卡片，造成"错位/按钮消失"观感
// 另叠加用户偏好（个人中心可关闭桌宠，默认展示）——两者是 AND 关系
const showWhale = computed(() => {
  if (!prefs.petVisible) return false
  const p = route.path
  if (/^\/music/.test(p)) return false
  return true
})

// 阻止内容闪现的画布（净画布，无开场动画）
const showInitialLoading = ref(true)

onMounted(async () => {
  // 应用用户主题覆盖（默认跟随时间）
  applyTheme(prefs.themeOverride)
  if (auth.token) {
    try {
      await auth.fetchUser()
    } catch {
      // token无效，只清除本地状态，不显示错误（首次加载时不需要报错）
      auth.token = ''
      auth.user = null
      localStorage.removeItem('token')
    }
  }

  // 如果已登录且在登录页，自动跳转到首页
  if (auth.isLoggedIn && route.path === '/login') {
    router.push('/workbench')
  }

  // 已登录后启动 token 滑动续期定时器：周期性检查，临近过期自动续期，保持不掉线
  let extendTimer = null
  const EXTEND_INTERVAL = 30 * 60 * 1000 // 每 30 分钟检查一次
  if (auth.isLoggedIn) {
    auth.scheduleExtend()
    extendTimer = setInterval(() => auth.scheduleExtend(), EXTEND_INTERVAL)
  }

  // 跳过洞天将开开场动画，鉴权就绪后直接进入应用
  showInitialLoading.value = false

  // 跟随时间自动切昼夜的定时器：仅当主题为「自动」时生效，固定日程不受影响
  const AUTO_THEME_INTERVAL = 60 * 1000
  const themeTimer = setInterval(() => {
    if (prefs.themeOverride === 'auto') applyTheme('auto')
  }, AUTO_THEME_INTERVAL)

  onBeforeUnmount(() => { if (extendTimer) clearInterval(extendTimer) })
  onBeforeUnmount(() => { if (themeTimer) clearInterval(themeTimer) })
})
</script>

<style>
#app {
  min-height: 100vh;
  min-height: 100svh;
  background: var(--color-bg);
}

/* ========== 移动端（沉浸式 + 底部两 Tab）：内容整体垫高，避免被 Tab 栏遮挡 ========== */
#app.is-mobile {
  padding-bottom: calc(72px + var(--safe-bottom, env(safe-area-inset-bottom, 0px)));
}
/* 播放条在移动端悬浮于两 Tab 栏之上 */
#app.is-mobile .npbar {
  bottom: calc(84px + var(--safe-bottom, env(safe-area-inset-bottom, 0px)));
}
/* 移动端桌宠：上移到 Tab 栏之上并适度缩小，避免压住导航/内容 */
#app.is-mobile .whale-stage {
  right: 14px;
  bottom: calc(70px + var(--safe-bottom, env(safe-area-inset-bottom, 0px)));
  transform: scale(.78);
  transform-origin: bottom right;
}

/* Skip Link键盘导航 - 可访问性 */
.skip-link {
  position: absolute;
  top: -100px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-primary);
  color: var(--color-bg);
  padding: 8px 16px;
  border-radius: 4px;
  z-index: 9999;
  transition: top 0.2s;
}
.skip-link:focus {
  top: 10px;
}
</style>


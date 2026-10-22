<template>
  <div id="app" :class="{ 'is-mobile': isMobile, 'is-immersive': immersive }">
    <!-- 全站科技风 · 画布粒子/网格背景（固定层，置于内容之下，pointer-events:none） -->
    <TechBackdrop />
    <el-config-provider :locale="zhCn">
    <!-- Skip Link键盘导航 -->
    <a href="#main-content" class="skip-link">跳转到内容</a>

    <!-- 路由视图：移动端缓存三个底部 Tab 首页，切 Tab 不再重挂载而闪白；桌面不缓存维持现状 -->
    <router-view v-if="!showInitialLoading" id="main-content" v-slot="{ Component, route }">
      <!-- v2.46.219：全屏路由跳过路由过渡。
           原因：<transition mode="out-in"> 要求子组件是「单一真实元素」，而全屏页
           （阅读器）内部根是 <Teleport to="body">，拿不到 el → 离开钩子永不结束
           → 点返回后新页面永远进不来，整块内容区空白（侧栏正常）。
           全屏页本来也不需要过渡动画，直接关掉最稳。 -->
      <transition :name="isFullscreenRoute(route) ? 'route-fade-none' : 'route-fade'" mode="out-in">
        <keep-alive :include="keepAliveNames">
          <component :is="Component" :key="route.fullPath" />
        </keep-alive>
      </transition>
    </router-view>

    <!-- 登录后全站常驻：桌面顶栏（悬浮）；移动端用独立沉浸式外壳，不显示 ✓
         v2.41.2 顶栏只留「提醒 + 账号」，⌘K / AI 高级工具的入口已迁到侧栏与手机端「智能」分组，
         由下方 provide('navAction') 统一调起，顶栏不再有对应 emit
         v2.46.23 沉浸态（牌桌全屏/放大）也收起：顶栏 fixed z-1000 会压在牌桌右上角的
         出牌记录面板上（🔔 + 昵称 + ☰ 叠在「出牌记录」头上，夜星截图实锤） -->
    <GlobalTopBar v-if="!showInitialLoading && auth.isLoggedIn && !isMobile && !immersive" />

    <!-- 登录后桌面端：左侧导航（默认展开，可收起，按玉简分组；顶栏不动） -->
    <DesktopSidebar v-if="!showInitialLoading && auth.isLoggedIn && !isMobile" />

    <!-- 登录后移动端：底部两 Tab 主导航（主页/我的）。牌桌沉浸期间收起，
         否则它（fixed z-index:1500）会压在牌桌底部操作区上 -->
    <MobileTabBar v-if="!showInitialLoading && auth.isLoggedIn && isMobile && !immersive" />

    <!-- 移动端悬浮对局邀请胶囊（v2.45）：移动端没有桌面顶栏，邀请需要独立入口 -->
    <MobileInviteDock v-if="!showInitialLoading && auth.isLoggedIn && isMobile && !immersive" />

    <!-- 登录后桌面端：AI 入口改由顶栏 ✺ 按钮 + Cmd/Ctrl+Shift+A 全局快捷键直达（v2.39.8 移除右下角 FAB，避免右下角拥挤） -->

    <!-- 全局命令面板 ⌘K / Ctrl+K（登录后可用；移动端隐藏以免误触） -->
    <CommandPalette v-if="auth.isLoggedIn && !isMobile" ref="cmdRef" />

    <!-- AI 高级工具抽屉（v2.39）：改写/解释/语义搜索/长期记忆/Agent/OCR/用量 -->
    <AiToolsDrawer v-if="auth.isLoggedIn && !isMobile" v-model:open="aiToolsOpen" />

    <!-- 登录后全站常驻桌宠（音乐岛内容列表页隐藏：桌宠固定右下会压住列表行/最后一张卡片；
         牌桌沉浸期间也收起，右下角会挡住牌桌） -->
    <WhaleCompanion v-if="!showInitialLoading && auth.isLoggedIn && showWhale && !immersive" />

    <!-- 登录后全站底部播放条（播放时出现）；牌桌沉浸期间收起 -->
    <NowPlayingBar v-if="!showInitialLoading && auth.isLoggedIn && !immersive" @open-full="openFullPlayer" />

    <!-- 音乐全屏播放器已改成独立路由 /now-playing（v2.46.217）：
         原来是这里的 v-if 覆盖层 → 手机返回键会退出整个页面而不是收起播放器，
         而且只有手机端渲染，PC 没有全屏播放器。见 MusicPlayingView.vue。 -->

    <!-- 登录后全站底部网安/备案标识（工作台与岛屿/工具内容页各自渲染页脚，此处不再重复） -->
    <SiteFooter v-if="!showInitialLoading && auth.isLoggedIn && showGlobalFooter" variant="dark" />
    </el-config-provider>
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent, onMounted, onBeforeUnmount, watch, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useAuthStore } from '@/stores/auth'
import { usePrefsStore, applyTheme } from '@/stores/prefs'
import GlobalTopBar from '@/components/GlobalTopBar.vue'
import DesktopSidebar from '@/components/desktop/DesktopSidebar.vue'
import MobileTabBar from '@/components/MobileTabBar.vue'
import MobileInviteDock from '@/components/mobile/MobileInviteDock.vue'
import NowPlayingBar from '@/components/NowPlayingBar.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import AiToolsDrawer from '@/components/workbench/AiToolsDrawer.vue'
import { checkFestivalNotice } from '@/utils/festivalNotice'
import { ElNotification } from 'element-plus'
import { useGameInvites } from '@/composables/useGameInvites'
import { useIsMobile } from '@/composables/useIsMobile'
import { useImmersive } from '@/composables/useImmersive'
import TechBackdrop from '@/components/effects/TechBackdrop.vue'

// WhaleCompanion 较大（视频背景 + 动画控制），按需异步加载以减小首屏 bundle
const WhaleCompanion = defineAsyncComponent(() => import('@/components/effects/WhaleCompanion.vue'))

const router = useRouter()

/** 打开全屏播放器：走路由，这样浏览器箭头 / 手机返回键都能正确退出 */
function openFullPlayer() {
  if (router.currentRoute.value.name === 'MusicPlaying') return
  router.push({ name: 'MusicPlaying' })
}
const route = useRoute()
const auth = useAuthStore()
const prefs = usePrefsStore()
const { isMobile } = useIsMobile()
// 牌桌等全屏对局的沉浸态：置位期间收起底部 Tab 栏 / 桌宠 / 播放条
const { immersive } = useImmersive()

// v2.46.79：给 <html> 打移动端标记。el-dialog/el-popover 用 append-to-body 挂到 body 下，
// 会逃出 #app.is-mobile 作用域（手机弹窗里的主按钮因此掉回 Element Plus 默认浅紫+白字，
// 对比度不足看不清）。html.m-app 让全局样式能覆盖这些 teleport 到 body 的浮层。
watch(isMobile, (v) => {
  document.documentElement.classList.toggle('m-app', !!v)
}, { immediate: true })

// 移动端缓存三个底部 Tab 首页组件（切 Tab 不重挂载、不闪白）；桌面 include 为空 → 不缓存
const keepAliveNames = computed(() => isMobile.value ? ['WorkbenchView', 'ModulesView', 'ProfileView'] : [])

/* 全屏路由：不做路由过渡（内部有 Teleport，transition 拿不到真实元素）
   名单与 router/index.js 的 FULLSCREEN_ROUTES 保持一致。 */
const FULLSCREEN_ROUTE_NAMES = new Set(['NovelRead', 'MusicPlaying'])
function isFullscreenRoute(r) {
  return !!(r && FULLSCREEN_ROUTE_NAMES.has(r.name))
}

// 移动端全屏播放器开关

/* 对局邀请单例（棋类 + 牌类）：顶栏面板 / 移动端胶囊 / 新到提示共用一份数据 */
const gameInvites = useGameInvites()

/* 新到邀请的角标提示：非阻塞、不打断操作；接受/拒绝在顶栏面板或移动端胶囊里做 */
function onInviteArrivals(list) {
  const first = list[0]
  if (!first) return
  const extra = list.length > 1 ? `（另有 ${list.length - 1} 条）` : ''
  const mobile = isMobile.value
  const hint = mobile ? '点右上角「对局邀请」查看' : '点右上角「提醒」查看'
  ElNotification({
    title: '收到对局邀请',
    message: `「${first.fromName}」邀你来一局${first.gameName}${extra} · ${hint}`,
    type: 'info',
    duration: 6000,
    // 移动端胶囊就贴右上角，提示若也放右上会正好盖住它 —— 挪到右下（抬高避开底部 Tab 栏）
    position: mobile ? 'bottom-right' : 'top-right',
    offset: mobile ? 76 : 16,
  })
}

// 桌宠偏好按用户隔离：登录用户或切换账号时重新绑定，读取各自的 localStorage 记录
watch(
  () => auth.user?.id,
  (uid) => prefs.bindUser(uid),
  { immediate: true },
)

// 工作台与岛屿/工具内容页在页面内部各自渲染页脚（IslandInnerBase 内置 SiteFooter），
// 全站级这里就不能再贴一个，否则同一页会并排出现两条网安/备案标识。
// ⚠️ 这串前缀必须与真正用了 IslandInnerBase 的路由前缀保持同步 —— 新增岛屿页面时记得补进来。
//    v2.46.145 修：/play（两款单机游戏直达页）与 /life（体重管理 / 美食记忆）漏登记，
//    这两页是「页面内一个 + App 底一个」的双页脚。改用「取路径首段精确比对」，
//    避免旧正则 `^/(log|tool…)` 那种写法顺手把 /toolxxx 这类同前缀异路由也误判。
const ISLAND_FOOTER_PREFIXES = ['music', 'novel', 'video', 'log', 'tool', 'history', 'life', 'play']
const showGlobalFooter = computed(() => {
  const p = route.path
  if (p === '/workbench') return false
  return !ISLAND_FOOTER_PREFIXES.includes(p.split('/')[1] || '')
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

// 命令面板实例引用（顶栏按钮点击触发其 open()）
const cmdRef = ref(null)

// AI 高级工具抽屉开关（顶栏 ✺ AI 按钮 + 全局热键触发）
const aiToolsOpen = ref(false)

/*
 * v2.41.2：顶栏瘦身，「命令面板 / AI 高级工具」迁入侧栏与手机端模块目录。
 * 这两个动作的开关挂到 provide('navAction')，子组件（DesktopSidebar / ModulesView）inject 后
 * 按条目的 actionId 统一调起，不重复实现，也不需要在 App 里为每个入口写一份 emit 监听。
 */
provide('navAction', {
  openCommandPalette: () => cmdRef.value?.open?.(),
  openAiTools: () => { aiToolsOpen.value = true },
})

// F5 全局键盘快捷键：g+字母（仿 GitHub 路由跳转）
// 触发序列：按 g 后 1.5s 内按下字母，否则取消
let gPressedAt = 0
const G_ROUTES = {
  w: '/workbench', n: '/notes', f: '/finance/book', t: '/tasks', l: '/tool',
  m: '/music', c: '/tool/countdown', s: '/finance/market', p: '/profile', d: '/diary',
  r: '/travels', e: '/finance/news',
}
function onGlobalKey(e) {
  const t = e.target
  const inField = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)
  // 排除命令面板已开启（由 CommandPalette 内部处理）；也排除在输入控件里
  const cmdOpen = cmdRef.value && cmdRef.value.open && cmdRef.value.open.value
  if (inField || cmdOpen || e.metaKey || e.ctrlKey || e.altKey) return

  if (gPressedAt && Date.now() - gPressedAt < 1500) {
    const k = e.key.toLowerCase()
    if (G_ROUTES[k]) {
      e.preventDefault()
      router.push(G_ROUTES[k])
      gPressedAt = 0
      return
    }
    if (k !== 'g') gPressedAt = 0
  }
  if (e.key.toLowerCase() === 'g' && !e.shiftKey) { gPressedAt = Date.now(); return }
  // #6 键盘速记：任意页按 N（非输入态）→ 新建笔记
  if (e.key.toLowerCase() === 'n' && !e.shiftKey) {
    e.preventDefault()
    router.push('/notes/new')
  }
  // v2.39 AI 工具快捷键：Cmd/Ctrl + Shift + A 打开 AI 高级工具抽屉
  if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'a') {
    e.preventDefault()
    aiToolsOpen.value = true
  }
}

onMounted(async () => {
  // 绑定 F5 全局快捷键
  window.addEventListener('keydown', onGlobalKey)
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

  // 假期 / 调休补班提醒（v2.40.20）：只在用户于「摸鱼日历」里开过开关时才生效，
  // 且是**本地通知**——站点打开时检查一次，没开站点不会收到。失败静默，绝不打扰。
  if (auth.isLoggedIn) {
    setTimeout(() => { checkFestivalNotice().catch(() => {}) }, 3000)
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
  onBeforeUnmount(() => gameInvites.stop())

  /* ---------- 对局邀请（棋类 + 牌类）统一轮询（v2.45）----------
   * 轮询结果只落 `useGameInvites` 单例，由顶栏提醒面板 / 移动端胶囊共同消费；
   * 这里只负责「新到一条时弹一个非阻塞角标提示」。
   * 旧实现用 ElMessageBox 居中确认框：一次性、错过就没了，且违反全站无弹窗约定。 */
  gameInvites.start(onInviteArrivals)
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
/* 牌桌全屏：Tab 栏已收起，垫高必须一并去掉，否则牌桌下方空出一条 */
#app.is-mobile.is-immersive {
  padding-bottom: 0;
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

/* ========== 全局路由切换过渡（v195）：鎏金淡入 + 轻位移 ========== */
.route-fade-enter-active {
  transition:
    opacity .28s cubic-bezier(.22, .61, .36, 1),
    transform .34s cubic-bezier(.22, .61, .36, 1),
    filter .28s ease;
}
.route-fade-leave-active {
  transition:
    opacity .18s ease,
    transform .18s ease,
    filter .18s ease;
}
.route-fade-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(.992);
  filter: blur(2px) saturate(.9);
}
.route-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(.998);
  filter: blur(1px) saturate(.95);
}
.route-fade-enter-to,
.route-fade-leave-from {
  opacity: 1;
  transform: none;
  filter: none;
}

@media (prefers-reduced-motion: reduce) {
  .route-fade-enter-active,
  .route-fade-leave-active {
    transition-duration: .01s;
  }
  .route-fade-enter-from,
  .route-fade-leave-to {
    transform: none;
    filter: none;
  }
}

/* ================= 真全屏页面（v2.46.217） =================
   由 composables/useFullscreenPage.js 在进入全屏页时给 body 加 `fs-page`。
   这里统一收起站点外壳，让全屏页拿到干净的整块视口。

   为什么用 body class 而不是 z-index：实测侧栏 `.dsb` 的 z-index 只有 90，
   但 Teleport 到 body 且 z-index 1900 的覆盖层**仍然被它压住**（合成层/包含块问题），
   抬高层级治不好。直接隐藏周边元素最可靠 —— 全屏本来就是沉浸场景，
   侧栏/页脚/播放条这时都没有存在意义。

   🔴 卸载时机一旦出错，残留的 class 会让下一个页面"没侧栏、不能滚、看着空白"，
   所以 router/index.js 的 afterEach 里做了兜底清理。 */
body.fs-page {
  overflow: hidden !important;
  overscroll-behavior: none;
}
body.fs-page .lj-topbar,
body.fs-page .mt-tabbar,
body.fs-page .npbar,
body.fs-page .whale-stage,
body.fs-page .dsb,
body.fs-page .site-footer,
body.fs-page .mid {
  display: none !important;
}
/* 外壳收起后，内容区不该再给 TabBar 让位 */
body.fs-page #app,
body.fs-page #app.is-mobile {
  padding-bottom: 0 !important;
  min-height: 100vh;
  min-height: 100dvh;
}
</style>


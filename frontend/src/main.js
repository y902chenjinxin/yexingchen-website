import { createApp } from 'vue'
import { createPinia } from 'pinia'

/* 手机浏览器 = 桌面版（v2.40.30 夜星拍板）
 * 只有玄黄 APK（WebView 注入 UA `XuanHuangApp/x.y.z`）才用移动端外壳；
 * 手机自带浏览器 / 微信等一律走桌面版 —— 把 viewport 固定成 1280 宽，
 * 于是 CSS 媒体查询与 useIsMobile 都自然落到桌面分支，手机上看到可缩放的完整网页版。
 * 逃生口：URL 带 ?m=1 强制移动端（?m=0 取消），应对旧版不带标记的 APK。
 * 必须在挂载前执行，否则移动端样式会先闪一帧。 */
;(function mobileBrowserUsesDesktopLayout() {
  try {
    const ua = (typeof navigator !== 'undefined' && navigator.userAgent) || ''
    if (/XuanHuangApp/i.test(ua)) return              // APK：保持 device-width
    let forceMobile = false
    try { forceMobile = localStorage.getItem('xuanhuang_force_mobile') === '1' } catch { /* 忽略 */ }
    if (forceMobile) return
    const isMobileBrowser = /Android|iPhone|iPad|iPod|Windows Phone|HarmonyOS|Mobile|MicroMessenger/i.test(ua)
    if (!isMobileBrowser) return
    const meta = document.querySelector('meta[name="viewport"]')
    if (meta) meta.setAttribute('content', 'width=1280, viewport-fit=cover')
  } catch { /* 忽略：宁可保持默认也不白屏 */ }
})()

import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import { registerServiceWorker } from './sw-register'
import { usePwaInstall } from './composables/usePwaInstall'
import './assets/styles/main.css'
import './assets/styles/xiuxian-theme.css'
import './assets/styles/mobile-list.css'
// 手机端专属：A/B 亮暗双套 token + 去古风/去管理后台感（仅作用于 #app.is-mobile，桌面端零影响）
import './assets/styles/mobile-ab-theme.css'
import './assets/styles/mobile-deink.css'
// 手机端 7 大模块「iOS 原生 · 极简毛玻璃」质感统一层
import './assets/styles/mobile-native-glass.css'
// 手机端产品化收敛层：统一页面基线，覆盖历史模块主题，不影响桌面端
import './assets/styles/mobile-product.css'
// 桌面端主题 token：先于骨架层引入，保证变量定义在骨架层引用之前生效
import './assets/styles/desktop-theme-night.css'
import './assets/styles/desktop-theme-day.css'
// 桌面端产品化骨架与组件层（不写颜色 token）：作用域 #app:not(.is-mobile)，与移动端互不干扰
import './assets/styles/desktop-product.css'
// 工具岛各页的窄屏兜底（预览元素不撑破、按钮不被压扁等）：放最后，保证能兜住
import './assets/styles/tool-mobile.css'

const app = createApp(App)

// 全局指令：v-click-outside="handler"
// 点击绑定元素外部时触发 handler；忽略元素本身及其后代的事件。
// 用于下拉菜单/弹层关闭；handler 仅在打开状态被调用即可（调用方自行判断当前是否打开）。
import mouseLight from './directives/mouseLight'

// 全局指令：v-mouse-light="options"
// 鼠标 hover 时元素获得 3D 微倾斜 + 鎏金聚光（参考 codefronts.com CSS Card Hover）
// CSS 配合：在该元素的 hover 样式里用 var(--ml-x) var(--ml-y) 做 radial-gradient 光斑
app.directive('mouse-light', mouseLight)

app.directive('click-outside', {
  mounted(el, binding) {
    el.__clickOutsideHandler = (event) => {
      if (!el.contains(event.target)) {
        try { binding.value?.(event) } catch { /* swallow */ }
      }
    }
    // 下一拍再挂监听，避免同一次点击「先 inside 再 outside」的竞态
    setTimeout(() => document.addEventListener('pointerdown', el.__clickOutsideHandler, true), 0)
  },
  unmounted(el) {
    if (el.__clickOutsideHandler) {
      document.removeEventListener('pointerdown', el.__clickOutsideHandler, true)
      delete el.__clickOutsideHandler
    }
  },
})

app.use(createPinia())
app.use(router)

// PWA：SW 注册 + beforeinstallprompt 监听都必须在应用启动时就位。
// 后者尤其关键：事件在页面加载后几秒内派发一次，若等用户进个人中心才挂监听，
// 事件早已错过，「安装为应用」入口会永远不出现（v2.22.1 修复的实际 bug）。
registerServiceWorker()
usePwaInstall()

// 昼夜自适应主题（TIME_THEME_20260908）：本地时间 6:00–18:00 → day，其余 night。
// 仅作首帧预热；用户若在个人中心设置了固定主题，App.vue 挂载后会覆盖为本偏好。
function applyDayTheme() {
  const h = new Date().getHours()
  const next = h >= 6 && h < 18 ? 'day' : 'night'
  const root = document.documentElement
  if (root.dataset.theme !== next) root.dataset.theme = next
}
applyDayTheme()

// 挂载点必须是 #app-root（index.html），不能是 #app：
// App.vue 根节点自己就是 <div id="app">，挂载点同名会造成两个 #app 嵌套，
// 所有 `#app:not(.is-mobile)` 规则命中两层（侧栏让位 padding 被叠加，内容被推远一大截）。
app.mount('#app-root')

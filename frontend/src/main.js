import { createApp } from 'vue'
import { createPinia } from 'pinia'
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

const app = createApp(App)

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

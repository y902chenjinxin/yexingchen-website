import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css'
import './assets/styles/xiuxian-theme.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 昼夜自适应主题（TIME_THEME_20260908）：本地时间 6:00–18:00 → day，其余 night
function applyDayTheme() {
  const h = new Date().getHours()
  const next = h >= 6 && h < 18 ? 'day' : 'night'
  const root = document.documentElement
  if (root.dataset.theme !== next) root.dataset.theme = next
}
applyDayTheme()
setInterval(applyDayTheme, 60000)

app.mount('#app')
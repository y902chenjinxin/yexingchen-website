/**
 * 习惯页弹窗渲染沙盒（本地开发用，不进生产入口）
 *
 * 目的：把 HabitsView 按「手机端外壳」挂起来，量「新建习惯」弹窗在窄屏下
 * 是否还横向溢出、body 是否内部滚动、footer 是否常驻一屏内。
 *
 * 依赖：npx vite --port 5199
 * 用法：node _probe_habit.cjs
 */
import { createApp, h } from 'vue'
import { createPinia } from 'pinia'

/* 与 main.js 同序引样式（少一个都会让 dialog 掉回 EP 默认皮） */
import 'element-plus/dist/index.css'
import '@/assets/styles/main.css'
import '@/assets/styles/xiuxian-theme.css'
import '@/assets/styles/mobile-list.css'
import '@/assets/styles/mobile-ab-theme.css'
import '@/assets/styles/mobile-deink.css'
import '@/assets/styles/mobile-native-glass.css'
import '@/assets/styles/mobile-product.css'
import '@/assets/styles/mobile-paper.css'
import '@/assets/styles/desktop-theme-night.css'
import '@/assets/styles/desktop-theme-day.css'
import '@/assets/styles/desktop-product.css'
import '@/assets/styles/tool-mobile.css'
import '@/assets/styles/game-table.css'
import '@/assets/styles/tech-theme.css'
import '@/assets/styles/tech-theme-day.css'

import HabitsView from '@/views/HabitsView.vue'

document.documentElement.classList.add('m-app')

const app = createApp({ render: () => h(HabitsView) })
app.use(createPinia())
app.mount('#probe')

/* 探针自曝进度，供 cjs 侧等待 */
window.__probeReady = true

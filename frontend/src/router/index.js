import { createRouter, createWebHistory } from 'vue-router'
import { routeGuard } from './guards'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/workbench',
    name: 'Workbench',
    component: () => import('@/views/WorkbenchView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/notes',
    name: 'Notes',
    component: () => import('@/views/NotesView.vue'),
    meta: { requiresAuth: true }
  },
  // 全站模块目录（一级 / 二级）：手机端底部 Tab 第二项，桌面端为兜底分组网格
  {
    path: '/modules',
    name: 'Modules',
    component: () => import('@/views/ModulesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/notes/new',
    name: 'NoteNew',
    component: () => import('@/views/NoteEditorView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/notes/:id',
    name: 'NoteEditor',
    component: () => import('@/views/NoteEditorView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/assistant',
    name: 'Assistant',
    component: () => import('@/views/AssistantView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/trash',
    name: 'Trash',
    component: () => import('@/views/TrashView.vue'),
    meta: { requiresAuth: true }
  },
  // 内容模块（新版：去岛，浏览+管理合并一页）
  {
    path: '/music',
    name: 'Music',
    component: () => import('@/views/MusicView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/novel',
    name: 'Novel',
    component: () => import('@/views/NovelView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/video',
    name: 'Video',
    component: () => import('@/views/VideoView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/log',
    name: 'Log',
    component: () => import('@/views/LogView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tool',
    name: 'Tool',
    component: () => import('@/views/ToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置工具独立页
  {
    path: '/tool/watermark',
    name: 'Watermark',
    component: () => import('@/views/WatermarkView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 PDF 工具页（纯前端处理）
  {
    path: '/tool/pdf',
    name: 'PdfTool',
    component: () => import('@/views/PdfToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 像素压缩 工具页（纯前端本地处理）
  {
    path: '/tool/compress',
    name: 'CompressTool',
    component: () => import('@/views/CompressToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 证件照 工具页（纯前端 Canvas）
  {
    path: '/tool/idphoto',
    name: 'IdPhotoTool',
    component: () => import('@/views/IdPhotoToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 AI 封面 工具页（服务端 Pillow 模板渲染）
  {
    path: '/tool/cover',
    name: 'CoverTool',
    component: () => import('@/views/CoverToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 音色克隆 工具页（MiniMax 声音复刻 + T2A 试听）
  {
    path: '/tool/voice',
    name: 'VoiceCloneTool',
    component: () => import('@/views/VoiceCloneView.vue'),
    meta: { requiresAuth: true }
  },
  // 倒计时（Days Matter 风格）
  {
    path: '/tool/countdown',
    name: 'CountdownList',
    component: () => import('@/views/CountdownsView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 二维码 工具页（生成 + 解析，纯前端本地处理）
  {
    path: '/tool/qrcode',
    name: 'QrTool',
    component: () => import('@/views/QrToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 随机密码 工具页（纯前端 crypto 生成）
  {
    path: '/tool/password',
    name: 'PasswordTool',
    component: () => import('@/views/PasswordToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 OCR 文字识别（服务端 RapidOCR 本地推理）
  {
    path: '/tool/ocr',
    name: 'OcrTool',
    component: () => import('@/views/OcrToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 语音转文字（服务端 sherpa-onnx SenseVoice 本地推理）
  {
    path: '/tool/asr',
    name: 'AsrTool',
    component: () => import('@/views/AsrToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 时间胶囊（写给未来的信）
  {
    path: '/tool/capsule',
    name: 'CapsuleTool',
    component: () => import('@/views/CapsuleToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 摸鱼日历
  {
    path: '/tool/fish',
    name: 'FishTool',
    component: () => import('@/views/FishToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 AI 诗签
  {
    path: '/tool/poem',
    name: 'PoemTool',
    component: () => import('@/views/PoemToolView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 人生 4000 周
  {
    path: '/tool/lifegrid',
    name: 'LifeGrid',
    component: () => import('@/views/LifeGridView.vue'),
    meta: { requiresAuth: true }
  },
  // v2.40.24 电子木鱼下线（不符合棋类定位，夜星要求删除）
  // 内置 棋类游戏合集（原「摸鱼小游戏」：五子棋/黑白棋/数独/飞行棋 + 贪吃蛇/扫雷）
  {
    path: '/tool/games',
    name: 'Games',
    component: () => import('@/views/GamesView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 打字测速
  {
    path: '/tool/typing',
    name: 'TypingTool',
    component: () => import('@/views/TypingView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 代码美化图
  {
    path: '/tool/codesnap',
    name: 'CodeSnap',
    component: () => import('@/views/CodeSnapView.vue'),
    meta: { requiresAuth: true }
  },
  // 内置 人脉图谱
  {
    path: '/tool/contactsmap',
    name: 'ContactsMap',
    component: () => import('@/views/ContactsMapView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tool/countdown/:id',
    name: 'CountdownDetail',
    component: () => import('@/views/CountdownDetailView.vue'),
    meta: { requiresAuth: true, hideGlobalTopBar: true }
  },
  // v2.16 财经模块：行情 / 资讯 / 记账（v2.37 移除「综合」总览，重定向改指行情）
  {
    path: '/finance',
    redirect: '/finance/market'
  },
  {
    path: '/finance/market',
    name: 'FinanceMarket',
    component: () => import('@/views/StocksView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/finance/market/stock/:code',
    name: 'FinanceStockDetail',
    component: () => import('@/views/StockDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/finance/news',
    name: 'FinanceNews',
    component: () => import('@/views/FeedsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/finance/book',
    name: 'FinanceBook',
    component: () => import('@/views/FinanceView.vue'),
    meta: { requiresAuth: true }
  },
  // 旧路由重定向到新财经路径
  { path: '/stocks', redirect: '/finance/market' },
  { path: '/stocks/:code', redirect: '/finance/market/stock/:code' },
  { path: '/feeds', redirect: '/finance/news' },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/travels',
    name: 'Travels',
    component: () => import('@/views/TravelsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/datahub',
    name: 'DataHub',
    component: () => import('@/views/DataHubView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/diary',
    name: 'Quick',
    component: () => import('@/views/QuickView.vue'),
    meta: { requiresAuth: true }
  },
  // 家庭助理：通讯录 / 待办 / 订阅（三者共用生日与续费提醒引擎）
  {
    path: '/contacts',
    name: 'Contacts',
    component: () => import('@/views/ContactsView.vue'),
    meta: { requiresAuth: true }
  },
  // v2.15 生活模块：家人共享的体重 / 美食记忆
  // v2.41：拆成两个菜单 —— 「体重记录」与「美食记忆」共用同一视图，靠 mode prop 切换
  {
    path: '/life',
    redirect: '/life/weight',
  },
  {
    path: '/life/weight',
    name: 'LifeWeight',
    component: () => import('@/views/LifeView.vue'),
    props: { mode: 'weight' },
    meta: { requiresAuth: true }
  },
  {
    path: '/life/meals',
    name: 'LifeMeals',
    component: () => import('@/views/LifeView.vue'),
    props: { mode: 'meals' },
    meta: { requiresAuth: true }
  },
  // v2.40.21 生活模块三件套：遗失物件 / 穿搭推荐 / 密码保险箱（都家庭共享）
  {
    path: '/lost',
    name: 'LostItems',
    component: () => import('@/views/LostItemsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/wardrobe',
    name: 'Wardrobe',
    component: () => import('@/views/WardrobeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/vault',
    name: 'Vault',
    component: () => import('@/views/VaultView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/TasksView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/subscriptions',
    name: 'Subscriptions',
    component: () => import('@/views/SubscriptionsView.vue'),
    meta: { requiresAuth: true }
  },
  // 外部工具独立页（iframe 内嵌）
  {
    path: '/tool/:id',
    name: 'ToolDetail',
    component: () => import('@/views/ToolDetailView.vue'),
    meta: { requiresAuth: true }
  },
  // 旧 /island/* 路由重定向（去岛）
  { path: '/island/music', redirect: '/music' },
  { path: '/island/novel', redirect: '/novel' },
  { path: '/island/video', redirect: '/video' },
  { path: '/island/log', redirect: '/log' },
  { path: '/island/tool', redirect: '/tool' },
  { path: '/island/music/inner', redirect: '/music' },
  { path: '/island/novel/inner', redirect: '/novel' },
  { path: '/island/video/inner', redirect: '/video' },
  { path: '/island/log/inner', redirect: '/log' },
  { path: '/island/tool/inner', redirect: '/tool' },
  {
    path: '/admin',
    redirect: '/admin/users'
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: () => import('@/views/admin/AdminUsersView.vue'),
    meta: { requiresAuth: true, role: 'super_admin' }
  },
  {
    path: '/admin/roles',
    name: 'AdminRoles',
    component: () => import('@/views/admin/AdminRolesView.vue'),
    meta: { requiresAuth: true, role: 'super_admin' }
  },
  {
    path: '/admin/menus',
    name: 'AdminMenus',
    component: () => import('@/views/admin/AdminMenusView.vue'),
    meta: { requiresAuth: true, role: 'super_admin' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  // 玄黄装饰组件预览（仅登录可见；用于在浏览器中预览 uiverse 改造后的 loader 效果）
  {
    path: '/decor-preview',
    name: 'DecorPreview',
    component: () => import('@/views/DecorPreviewView.vue'),
    meta: { requiresAuth: true, hideGlobalTopBar: true }
  },
  // 未匹配路径兜底：弃用 /home 等未知路由，统一回工作台（含未登录重定向）
  {
    path: '/:pathMatch(.*)*',
    redirect: '/workbench'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(routeGuard)

export default router
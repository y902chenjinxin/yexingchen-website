import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
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
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/TasksView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/assets',
    name: 'Assets',
    component: () => import('@/views/AssetsView.vue'),
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
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAuth: true, role: 'super_admin' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
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
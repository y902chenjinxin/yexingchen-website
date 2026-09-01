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
    path: '/home',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
    meta: { requiresAuth: true }
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
  {
    path: '/island/music',
    name: 'MusicIsland',
    component: () => import('@/views/MusicIsland.vue'),
    meta: { requiresAuth: true, island: 'music' }
  },
  {
    path: '/island/novel',
    name: 'NovelIsland',
    component: () => import('@/views/NovelIsland.vue'),
    meta: { requiresAuth: true, island: 'novel' }
  },
  {
    path: '/island/video',
    name: 'VideoIsland',
    component: () => import('@/views/VideoIsland.vue'),
    meta: { requiresAuth: true, island: 'video' }
  },
  {
    path: '/island/log',
    name: 'LogIsland',
    component: () => import('@/views/LogIsland.vue'),
    meta: { requiresAuth: true, island: 'log' }
  },
  {
    path: '/island/tool',
    name: 'ToolIsland',
    component: () => import('@/views/ToolIsland.vue'),
    meta: { requiresAuth: true, island: 'tool' }
  },
  // v2.0 岛屿内景
  {
    path: '/island/music/inner',
    name: 'MusicIslandInner',
    component: () => import('@/views/islands/MusicIslandInner.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/island/novel/inner',
    name: 'NovelIslandInner',
    component: () => import('@/views/islands/NovelIslandInner.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/island/video/inner',
    name: 'VideoIslandInner',
    component: () => import('@/views/islands/VideoIslandInner.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/island/log/inner',
    name: 'LogIslandInner',
    component: () => import('@/views/islands/LogIslandInner.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/island/tool/inner',
    name: 'ToolIslandInner',
    component: () => import('@/views/islands/ToolIslandInner.vue'),
    meta: { requiresAuth: true }
  },
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(routeGuard)

export default router
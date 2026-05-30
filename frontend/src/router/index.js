import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
    return
  }

  if (to.meta.role === 'super_admin' && !auth.isSuperAdmin) {
    next('/home')
    return
  }

  if (to.path !== '/login' && auth.isLoggedIn && to.path === '/login') {
    next('/home')
    return
  }

  next()
})

export default router
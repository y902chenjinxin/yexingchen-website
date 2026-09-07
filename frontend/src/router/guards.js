import { useAuthStore } from '@/stores/auth'

/**
 * 路由守卫函数（从 router/index.js 提取以便单元测试）
 * 返回 next(path) 或 next() 让 router 决定下一步
 */
export async function routeGuard(to, from, next) {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
    return
  }

  // 直接刷新受保护页时 user 尚未加载（App.vue onMounted 的 fetchUser 晚于守卫），先同步拉取
  if (auth.isLoggedIn && !auth.user && to.meta.requiresAuth) {
    await auth.fetchUser()
    if (!auth.isLoggedIn) {
      next('/login')
      return
    }
  }

  if (to.meta.role === 'super_admin' && !auth.isSuperAdmin) {
    next('/workbench')
    return
  }

  if (to.path === '/login' && auth.isLoggedIn) {
    next('/workbench')
    return
  }

  next()
}

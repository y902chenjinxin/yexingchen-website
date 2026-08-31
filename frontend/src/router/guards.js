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

  if (to.meta.role === 'super_admin' && !auth.isSuperAdmin) {
    next('/home')
    return
  }

  if (to.path === '/login' && auth.isLoggedIn) {
    next('/home')
    return
  }

  next()
}

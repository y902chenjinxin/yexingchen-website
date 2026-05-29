<template>
  <div id="app">
    <!-- Skip Link键盘导航 -->
    <a href="#main-content" class="skip-link">跳转到内容</a>

    <!-- 全局初始加载动画 -->
    <LoadingView v-if="showInitialLoading" @loaded="onInitialLoadingComplete" />

    <!-- 路由视图 -->
    <router-view v-if="!showInitialLoading" id="main-content" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoadingView from '@/views/LoadingView.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// 初始加载动画状态
const showInitialLoading = ref(true)

onMounted(async () => {
  // 检查token是否有效
  if (auth.token) {
    try {
      await auth.fetchUser()
    } catch {
      // token无效，只清除本地状态，不显示错误（首次加载时不需要报错）
      auth.token = ''
      auth.user = null
      localStorage.removeItem('token')
    }
  }

  // 如果已登录且在登录页，自动跳转到首页
  if (auth.isLoggedIn && route.path === '/login') {
    router.push('/home')
  }
})

// 初始加载动画完成后
function onInitialLoadingComplete() {
  showInitialLoading.value = false
}
</script>

<style>
#app {
  min-height: 100vh;
  background: var(--color-bg);
}

/* Skip Link键盘导航 - 可访问性 */
.skip-link {
  position: absolute;
  top: -100px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-primary);
  color: var(--color-bg);
  padding: 8px 16px;
  border-radius: 4px;
  z-index: 9999;
  transition: top 0.2s;
}
.skip-link:focus {
  top: 10px;
}
</style>
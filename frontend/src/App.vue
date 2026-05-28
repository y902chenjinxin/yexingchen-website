<template>
  <div id="app">
    <!-- 全局初始加载动画 -->
    <LoadingView v-if="showInitialLoading" @loaded="onInitialLoadingComplete" />

    <!-- 路由视图 -->
    <router-view v-if="!showInitialLoading" />
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
  // 检查token是否过期
  if (auth.isLoggedIn) {
    try {
      await auth.fetchUser()
    } catch {
      auth.logoutAction()
    }
  }

  // 如果已登录且在登录页，自动跳转到首页触发加载动画
  if (auth.isLoggedIn && route.path === '/login') {
    // 等待加载动画完成后跳转到首页
    // LoadingView 会在动画完成后触发 loaded 事件
  }
})

// 初始加载动画完成后
function onInitialLoadingComplete() {
  showInitialLoading.value = false
}

// 当路由跳转到首页时也显示加载动画
// 这部分由 router.beforeEach 处理
</script>

<style>
#app {
  min-height: 100vh;
  background: var(--color-bg);
}
</style>
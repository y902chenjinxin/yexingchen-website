<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(() => {
  // 检查token是否过期
  if (auth.isLoggedIn) {
    auth.fetchUser().catch(() => {
      auth.logoutAction()
    })
  }
})
</script>

<style>
#app {
  min-height: 100vh;
  background: var(--color-bg);
}
</style>
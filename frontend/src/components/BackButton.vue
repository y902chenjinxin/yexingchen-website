<template>
  <el-button :icon="ArrowLeft" size="default" class="app-back-btn" aria-label="返回" @click="goBack">
    返回
  </el-button>
</template>

<script setup>
import { inject } from 'vue'
import { routerKey } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'

const props = defineProps({
  fallback: { type: String, default: '/workbench' }
})

// 用官方注入 key 容错获取 router，保证组件在无路由环境（单测）也能安全渲染
const router = inject(routerKey, null)

function goBack() {
  if (!router) {
    return
  }
  // 优先用浏览器历史栈；没有则去 fallback
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push(props.fallback)
  }
}
</script>

<style scoped>
/* 手机端：返回只留图标（v2.46.135）。文字隐藏但 aria-label="返回" 仍可被读屏识别 */
:global(#app.is-mobile .app-back-btn) { width: 38px; height: 38px; padding: 0; border-radius: 12px; }
:global(#app.is-mobile .app-back-btn span) { display: none; }
</style>

<template>
  <el-button :icon="ArrowLeft" size="default" @click="goBack">
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

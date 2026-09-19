<template>
  <div class="admin-page">
    <header class="admin-header">
      <div class="header-left">
        <span class="admin-title">🔧 管理后台</span>
      </div>
      <div class="header-right">
        <slot name="actions" />
      </div>
    </header>

    <!-- 三段导航（横向 tabs） -->
    <nav class="admin-nav">
      <RouterLink
        v-for="item in items"
        :key="item.path"
        :to="item.path"
        class="admin-nav-item"
        :class="{ active: isActive(item.path) }"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.title }}</span>
      </RouterLink>
    </nav>

    <main class="admin-content">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { User, Lock, Menu as MenuIcon } from '@element-plus/icons-vue'

const route = useRoute()

const items = [
  { path: '/admin/users', title: '用户管理', icon: User },
  { path: '/admin/roles', title: '角色管理', icon: Lock },
  { path: '/admin/menus', title: '菜单管理', icon: MenuIcon },
]

function isActive(path) {
  return route.path === path
}
</script>

<style scoped>
.admin-page {
  position: relative;
  /* 文档流布局：整页随滚动一起移动，页脚在内容末尾
     padding-top 76px 避让顶部固定顶栏（60px）+ 呼吸位 */
  min-height: 100vh;
  padding: 76px 0 0;
  background: var(--dp-bg);
  color: var(--dp-text);
  box-sizing: border-box;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 0 32px 4px;
}

.admin-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -.01em;
  color: var(--dp-text);
}

.admin-nav {
  display: flex;
  gap: 4px;
  padding: 12px 32px 0;
  border-bottom: 1px solid var(--dp-line);
}

.admin-nav-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  font-size: 13px;
  color: var(--dp-text2);
  text-decoration: none;
  border-radius: 8px 8px 0 0;
  transition: all .15s;
}
.admin-nav-item:hover { color: var(--dp-text); background: var(--dp-surface2); }
.admin-nav-item.active {
  color: var(--dp-accent);
  font-weight: 600;
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-bottom-color: var(--dp-surface);
  margin-bottom: -1px;
  box-shadow: 0 -2px 6px var(--dp-accent-faint);
}

/* 内容区：全宽 + 左右留白（不做 max-width 居中，避免"悬浮在中间"的观感） */
.admin-content {
  padding: 20px 32px 40px;
}
</style>
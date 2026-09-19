<template>
  <footer class="site-footer" :class="`sf-${variant}`">
    <div class="sf-content">
      <img src="/filing/beian-icon.png" alt="备案图标" class="sf-icon" />
      <div class="sf-links">
        <a href="https://beian.mps.gov.cn/#/query/webSearch?code=34010402704746" target="_blank" rel="noopener">皖公网安备34010402704746号</a>
        <span class="sf-divider">|</span>
        <a href="https://beian.miit.gov.cn/#/Integrated/index" target="_blank" rel="noopener">皖ICP备2026006516号</a>
      </div>
    </div>
  </footer>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'dark' // dark(墨青深色底) / light(浅色留白底)
  }
})
</script>

<style scoped>
/* 页脚：直接平铺展示备案信息，不再用玻璃胶囊把它「框住」
   对比度问题改用主题文字色 + 极淡投影解决，视觉更干净 */
.site-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 20px;
  text-align: center;
}

.sf-content {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sf-icon {
  width: 16px;
  height: 16px;
  object-fit: contain;
  flex: none;
  opacity: .9;
}

.sf-links {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  flex-wrap: wrap;
  justify-content: center;
}
.sf-links a {
  color: var(--dp-text3, var(--ls-text-3));
  text-decoration: none;
  transition: color 0.2s;
  white-space: nowrap;
}
.sf-links a:hover { color: var(--dp-accent, var(--ls-dai)); }
.sf-divider { color: var(--dp-text3, var(--ls-text-3)); opacity: .6; }
</style>
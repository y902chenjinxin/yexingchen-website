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
.site-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 20px;
  text-align: center;
}
.sf-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}
.sf-icon {
  width: 18px;
  height: 18px;
  object-fit: contain;
  flex: none;
}
.sf-links {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  flex-wrap: wrap;
  justify-content: center;
}
.sf-links a {
  text-decoration: none;
  transition: color 0.2s;
  white-space: nowrap;
}
.sf-divider { opacity: 0.55; }

/* 墨青深色底（岛屿页） */
.sf-dark .sf-links a { color: rgba(232, 244, 252, 0.5); }
.sf-dark .sf-links a:hover { color: var(--ls-dai, #5f9499); }
.sf-dark .sf-divider { color: rgba(221, 221, 221, 0.5); }

/* 浅色留白底（工作台/管理页等） */
.sf-light .sf-links a { color: rgba(74, 95, 99, 0.6); }
.sf-light .sf-links a:hover { color: var(--lj-dai, #497477); }
.sf-light .sf-divider { color: rgba(74, 95, 99, 0.4); }
</style>
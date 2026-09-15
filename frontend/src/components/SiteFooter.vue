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
  padding: 10px 20px;
  text-align: center;
}

/* 备案标识须始终清晰可辨：用「随昼夜主题自适应的玻璃徽章」承载，
   自带底片 + backdrop 模糊，无论所在页面背景深浅、夜间/白昼，文字都有稳定对比，全站生效 */
.sf-content {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 5px 14px;
  border-radius: 999px;
  background:
    linear-gradient(165deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0) 48%),
    var(--ls-glass);
  border: 1px solid var(--ls-line);
  box-shadow:
    var(--glass-highlight, inset 0 1px 0 rgba(255, 255, 255, 0.06)),
    0 6px 20px rgba(0, 0, 0, 0.18);
  -webkit-backdrop-filter: saturate(160%) blur(16px);
  backdrop-filter: saturate(160%) blur(16px);
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
  color: var(--ls-text);
  text-decoration: none;
  transition: color 0.2s;
  white-space: nowrap;
  font-weight: 500;
}
.sf-links a:hover { color: var(--ls-dai); }
.sf-divider { color: var(--ls-text-3, rgba(160, 170, 178, 0.85)); }
</style>
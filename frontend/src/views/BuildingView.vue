<template>
  <div class="building-page">
    <div class="bp-glow" aria-hidden="true"></div>
    <div class="bp-card">
      <div class="bp-icon">
        <el-icon><MagicStick /></el-icon>
      </div>
      <h1 class="bp-title">{{ title }}</h1>
      <p class="bp-sub">模块施工中 · 即将上线，敬请期待</p>
      <button class="bp-back" @click="back">返回工作台</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MagicStick } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const title = computed(() => route.meta?.placeholder || '新模块')
function back() { router.push('/workbench') }
</script>

<style scoped>
.building-page {
  position: relative;
  min-height: calc(100vh - 60px);
  padding: 84px 24px 80px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  color: var(--lj-text);
  overflow: hidden;
}
.bp-glow {
  position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(ellipse 50% 40% at 30% 20%, rgba(127, 168, 163, 0.10), transparent 60%),
    radial-gradient(ellipse 45% 36% at 75% 65%, rgba(199, 169, 107, 0.08), transparent 60%);
}
.bp-card {
  position: relative;
  width: min(420px, 88vw);
  padding: 44px 36px;
  text-align: center;
  border-radius: 20px;
  background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line-strong);
  box-shadow: var(--lj-shadow), var(--glass-highlight);
}
.bp-icon {
  width: 64px; height: 64px; margin: 0 auto 20px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 16px; color: var(--lj-dai); font-size: 30px;
  border: 1px solid var(--lj-line); background: rgba(127, 168, 163, 0.10);
}
.bp-title { margin: 0; font-size: 22px; letter-spacing: .12em; color: var(--lj-text); }
.bp-sub { margin: 10px 0 26px; color: var(--lj-text-2); font-size: 13px; letter-spacing: .08em; }
.bp-back {
  padding: 10px 22px; border-radius: 10px; cursor: pointer;
  border: 1px solid var(--lj-line-strong); background: rgba(127, 168, 163, 0.10);
  color: var(--lj-text); font-family: inherit; font-size: 14px; letter-spacing: .1em;
  transition: all .25s;
}
.bp-back:hover {
  color: var(--lj-seal); border-color: var(--lj-seal);
  background: rgba(127, 168, 163, 0.16);
}
@media (max-width: 600px) {
  .building-page { padding: 88px 16px 80px; }
}
</style>
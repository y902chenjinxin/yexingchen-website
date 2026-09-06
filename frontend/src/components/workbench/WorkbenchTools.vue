<template>
  <section class="wt-section">
    <header class="wt-head">
      <div class="wt-title-block">
        <h2 class="wt-title">常用工具</h2>
        <span class="wt-sub">工具与快捷动作 · 一处直达</span>
      </div>
    </header>

    <div class="wt-grid">
      <a
        v-for="c in quickList"
        :key="c.key"
        class="wt-card"
        :class="`tone-${c.tone}`"
        @click.prevent="go(c)"
      >
        <span class="wt-icon">{{ c.icon }}</span>
        <span class="wt-name">{{ c.name }}</span>
        <span class="wt-desc">{{ c.desc }}</span>
      </a>

      
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToolStore } from '@/stores/tool'

const router = useRouter()
const toolStore = useToolStore()

// 本轮固定 6 个默认项：4 内置工具 + AI 对话 / 记一笔（自定义增删排序下轮再做）
const actionDefs = [
  { key: 'ai',   name: 'AI 对话', desc: '问答 · 摘要 · 生成', tone: 'ai',   to: '/assistant', icon: '🧠' },
  { key: 'book', name: '记一笔',  desc: '快速记账',           tone: 'book', to: '/finance',   icon: '💰' }
]
const BUILTIN_SLOT = 4 // 固定 6 - 2 动作

// 工具 + 动作混排：内置工具置顶（取前 BUILTIN_SLOT 个），再接固定动作
const quickList = computed(() => {
  const tools = toolStore.list || []
  const builtinCards = tools
    .filter(t => t.kind === 'builtin')
    .slice(0, BUILTIN_SLOT)
    .map(t => ({
      key: 'tool-' + t.id,
      name: t.title || '工具',
      desc: t.description || '',
      tone: 'tool',
      url: t.url,
      kind: t.kind,
      icon: t.icon || '🔧'
    }))
  const actionCards = actionDefs.map(a => ({
    key: a.key,
    name: a.name,
    desc: a.desc,
    tone: a.tone,
    to: a.to,
    icon: a.icon
  }))
  return [...builtinCards, ...actionCards]
})

function go(c) {
  if (c.to) { router.push(c.to); return }
  if (c.kind === 'builtin' && c.url) router.push(c.url)
  else router.push('/tool/' + c.id)
}

onMounted(() => { toolStore.fetchList({ enabled_only: 1, size: 100 }).catch(() => {}) })
</script>

<style scoped>
.wt-section { margin-bottom: 28px; }
.wt-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }
.wt-title { margin: 0; font-size: 18px; letter-spacing: .12em; color: var(--lj-text); }
.wt-sub { margin-left: 12px; font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }

.wt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 14px; }
.wt-card {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 18px 12px 14px; border-radius: 16px; text-decoration: none;
  background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line);
  box-shadow: var(--glass-highlight), var(--glass-shadow);
  transition: all .28s; cursor: pointer; font-family: inherit; color: var(--lj-text);
  overflow: hidden;
}
.wt-card::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--lj-dai), transparent); opacity: .5; }
.wt-card:hover { transform: translateY(-3px); border-color: var(--lj-line-strong); box-shadow: var(--glass-highlight), 0 14px 30px rgba(0,0,0,.30); }
.wt-icon {
  width: 46px; height: 46px; flex: none; border-radius: 13px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: var(--lj-dai);
  border: 1px solid var(--lj-line); background: rgba(127,168,163,.09);
}
.wt-name { font-size: 14px; letter-spacing: .04em; color: var(--lj-text); }
.wt-desc { font-size: 11px; color: var(--lj-text-3); }

.tone-ai .wt-icon    { color: var(--lj-ochre);     border-color: rgba(199,169,107,.28); background: rgba(199,169,107,.12); }
.tone-book .wt-icon  { color: #6d9a6b;             border-color: rgba(109,154,107,.28); background: rgba(109,154,107,.12); }

@media (max-width: 600px) {
  .wt-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
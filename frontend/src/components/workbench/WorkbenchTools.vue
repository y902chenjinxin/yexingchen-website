<template>
  <section class="wt-section">
    <header class="wt-head">
      <div class="wt-title-block">
        <span class="wt-seal" aria-hidden="true"><i style="--rune: '器'"></i></span>
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

// 混排：内置工具全部展示 + 固定动作（AI 对话 / 记一笔 / 闪念速记）
const actionDefs = [
  { key: 'ai',    name: 'AI 对话', desc: '问答 · 摘要 · 生成', tone: 'ai',    to: '/assistant', icon: '🧠' },
  { key: 'book',  name: '记一笔',  desc: '快速记账',           tone: 'book',  to: '/finance',   icon: '💰' },
  { key: 'flash', name: '闪念速记', desc: '随手记 · 日记',      tone: 'flash', to: '/diary',     icon: '✍️' }
]
// 工具 + 动作混排：内置工具全部展示，再接固定动作
const quickList = computed(() => {
  const tools = toolStore.list || []
  const builtinCards = tools
    .filter(t => t.kind === 'builtin')
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
.wt-title-block { display: flex; align-items: center; }
/* 题头印章角标：方形淡墨底 + 朱砂印边 + 小篆字 */
.wt-seal {
  flex: none; width: 20px; height: 20px; margin-right: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--lj-seal); border-radius: 5px;
  background: linear-gradient(180deg, rgba(181,90,72,.10), rgba(181,90,72,.04));
  box-shadow: inset 0 0 0 2px rgba(255,255,255,.35);
}
.wt-seal i { font-style: normal; font-size: 12px; line-height: 1; color: var(--lj-seal); }
.wt-seal i::before { content: var(--rune); }
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
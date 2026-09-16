<template>
  <section class="mwb" aria-label="工作台首页">
    <!-- 顶层：iOS 大标题 -->
    <header class="mwb-top">
      <div class="mwb-brand">玄 黄</div>
      <button class="mwb-ai" @click="go('/assistant')" aria-label="AI 对话">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M18.5 15.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/></svg>
        <span>AI</span>
      </button>
    </header>

    <!-- 固定搜索条：全局搜索 + AI 入口 -->
    <MobileSearchBar class="mwb-search" @go="go" />

    <!-- 玉简 Hero（近半屏沉浸） -->
    <MobileJadeCard class="mwb-hero" :cards="heroCards" />

    <!-- 快捷宫格：收纳全部可达模块 -->
    <div class="mwb-section">
      <h2 class="mwb-sec-title">诸界轻舟</h2>
      <MobileSkeleton v-if="menus.loading" :rows="0" :grid="8" />
      <div v-else class="mwb-grid">
        <button
          v-for="(m, i) in moduleGrid"
          :key="m.path"
          class="mwb-cell"
          :style="{ '--d': (i % 4) + 'ms' }"
          @click="go(m.path)"
          :aria-label="m.title"
        >
          <span class="mwb-cell-ico" :style="{ color: m.color }">
            <svg v-if="m.icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="m.icon"></svg>
            <span v-else>{{ m.rune }}</span>
          </span>
          <span class="mwb-cell-lab">{{ m.title }}</span>
        </button>

        <MobileEmpty
          v-if="moduleGrid.length === 0"
          title="暂无可用模块"
          desc="到管理后台分配菜单权限后再来看看"
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMenusStore } from '@/stores/menus'
import MobileJadeCard from './MobileJadeCard.vue'
import MobileSearchBar from './MobileSearchBar.vue'
import MobileSkeleton from './MobileSkeleton.vue'
import MobileEmpty from './MobileEmpty.vue'

const router = useRouter()
const menus = useMenusStore()

/* 玉简 Hero 卡片（与 MobileJadeCard 主卡一致） */
const heroCards = [
  { key:'music', rune:'音', label:'宫商流转', path:'/music', color:'#4a5f63', quote:'一曲清商，万般心绪皆化入弦。' },
  { key:'novel', rune:'書', label:'卷帙浩繁', path:'/novel', color:'#b0805a', quote:'一盏灯，一卷书，一段不眠的长夜。' },
  { key:'video', rune:'影', label:'光影交织', path:'/video', color:'#5b6b7a', quote:'光影之间，藏了百态人生。' },
  { key:'log',   rune:'墨', label:'翰墨丹青', path:'/log', color:'#4a6a56', quote:'把今日，留一盏墨香。' },
  { key:'tool',  rune:'器', label:'机关百变', path:'/tool', color:'#6a7a6a', quote:'七十二般兵器，皆备于匣。' },
  { key:'notes', rune:'記', label:'笔记云台', path:'/notes', color:'#55706b', quote:'所思所记，皆有归处。' },
  { key:'contacts', rune:'家', label:'骨肉亲缘', path:'/contacts', color:'#a06a4a', quote:'念念不忘，四时有回响。' },
  { key:'tasks',  rune:'待', label:'诸事待理', path:'/tasks',  color:'#5a6f5f', quote:'一日之计，在晨昏之间。' },
  { key:'subs',   rune:'费', label:'细水长流', path:'/subscriptions', color:'#6a6a8a', quote:'涓滴成流，常在常新。' },
]

/* 快捷宫格：玉简已覆盖的 + 数据密集模块，汇总成宫格；按角色过滤可达性 */
const GRID_ICONS = {
  '/finance':  'M4 6h16v12H4z M4 10h16 M8 6V4h8v2 M8 14h3 M15 14h1 M8 17h3',
  '/stocks':   'M4 17l5-6 3 3 7-8 M14 6h4v4 M4 7v13h16',
  '/travels':  'M18 8a4 4 0 0 1-8 0c0-2 1-3 2-4l2-2 2 2c1 1 2 2 2 4z M8 21h8 M12 12v9',
  '/feeds':    'M3 8h13 M3 12h9 M3 16h6 M18 10l3 3-3 3 M18 10v6h-3',
  '/datahub':  'M4 5h16v14H4z M4 13h16 M8 10v6 M12 9v7 M16 11v5',
  '/diary':    'M5 5h14v15H5z M9 5V3h6v2 M8 10h8 M8 14h5',
  '/tool/countdown': 'M12 5v7l4 2 M21 12a9 9 0 1 1-2.6-6.4',
  '/trash':    'M4 7h16 M9 7V5h6v2 M7 7l1 14h8l1-14 M10 11v6 M14 11v6',
}
const MODULES = [
  { path:'/notes', rune:'記', title:'笔记' },
  { path:'/finance', rune:'账', title:'记账' },
  { path:'/stocks', rune:'股', title:'股票' },
  { path:'/travels', rune:'迹', title:'足迹' },
  { path:'/feeds', rune:'讯', title:'资讯' },
  { path:'/datahub', rune:'览', title:'数据纵览' },
  { path:'/diary', rune:'速', title:'闪念·日记' },
  { path:'/tool/countdown', rune:'时', title:'倒计时' },
  { path:'/tasks', rune:'待', title:'待办' },
  { path:'/contacts', rune:'家', title:'通讯录' },
  { path:'/subscriptions', rune:'费', title:'订阅' },
  { path:'/music', rune:'音', title:'音乐' },
]
const PALETTE = ['#4a6a56','#b0805a','#5b6b7a','#6a7a6a','#55706b','#a06a4a','#5a6f5f','#6a6a8a']
function colorFor(p, i) { return PALETTE[i % PALETTE.length] }

const moduleGrid = computed(() =>
  MODULES.map((m, i) => ({
    ...m,
    color: colorFor(m.path, i),
    icon: GRID_ICONS[m.path] || '',
  })).filter(m => menus.isPathAllowed(m.path))
)

function go(path) {
  try { if (navigator && navigator.vibrate) navigator.vibrate(6) } catch {}
  router.push(path)
}

onMounted(() => { menus.load() })
</script>

<style scoped>
.mwb {
  position: relative;
  min-height: 100svh;
  padding: calc(env(safe-area-inset-top, 0px) + 6px) 0 calc(40px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
  overflow-x: hidden;
}

/* 顶层大标题 + AI 胶囊 */
.mwb-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 20px 2px;
}
.mwb-brand {
  font-family: var(--font-serif, serif);
  font-size: 26px; font-weight: 700; letter-spacing: .34em; text-indent: .34em;
  color: var(--lj-text, #dfebe5);
}
.mwb-ai {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 7px 14px; border-radius: 999px;
  border: 1px solid var(--lj-line-strong, rgba(127,168,163,.34));
  background: linear-gradient(135deg, var(--lj-seal,#c96b58), var(--lj-seal-hover,#e0a26b));
  color: #fff; font-size: 13px; font-weight: 600; letter-spacing: .08em;
  box-shadow: 0 8px 18px rgba(217,138,118,.28), inset 0 1px 0 rgba(255,255,255,.25);
  transition: transform .2s;
  -webkit-tap-highlight-color: transparent;
}
.mwb-ai:active { transform: scale(.94); }
.mwb-ai svg { width: 16px; height: 16px; }

.mwb-search { padding: 10px 16px 2px; }

/* 玉简 Hero */
.mwb-hero { margin-top: 6px; }

/* 快捷宫格 */
.mwb-section { padding: 26px 16px 6px; }
.mwb-sec-title {
  margin: 0 0 14px; font-size: 13px; font-weight: 600; letter-spacing: .28em; text-indent: .2em;
  color: var(--lj-text-3, rgba(200,215,220,.55));
  display: flex; align-items: center; gap: 10px;
}
.mwb-sec-title::after { content: ''; height: 1px; flex: 1; background: linear-gradient(90deg, var(--lj-line,rgba(127,168,163,.2)), transparent); }

.mwb-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.mwb-cell {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px 4px 10px;
  border-radius: 18px;
  background: var(--lj-glass, rgba(30,42,50,.42));
  -webkit-backdrop-filter: var(--lj-glass-blur, blur(16px));
  backdrop-filter: var(--lj-glass-blur, blur(16px));
  border: 1px solid var(--lj-line, rgba(127,168,163,.16));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
  color: var(--lj-text, #dfebe5);
  animation: cellIn .4s cubic-bezier(.2,.8,.2,1) backwards;
  animation-delay: calc(var(--d) * 0.04s);
  transition: transform .18s, border-color .18s;
  -webkit-tap-highlight-color: transparent;
}
@media (prefers-reduced-motion: reduce) { .mwb-cell { animation: none; } }
@keyframes cellIn { from { opacity: 0; transform: translateY(12px) scale(.94); } to { opacity: 1; transform: none; } }
.mwb-cell:active { transform: scale(.93); border-color: var(--lj-amber,#caa466); }

.mwb-cell-ico {
  width: 44px; height: 44px; border-radius: 15px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(127,168,163,.1);
  font-family: var(--font-serif, serif); font-size: 18px;
}
.mwb-cell-ico svg { width: 24px; height: 24px; }
.mwb-cell-lab { font-size: 12px; letter-spacing: .02em; opacity: .9; white-space: nowrap; }
</style>
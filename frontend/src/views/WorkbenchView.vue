<template>
  <div class="workbench-page">
    <!-- 修仙夜色背景：星点 + 雾霭 -->
    <div class="xiu-bg" aria-hidden="true">
      <span v-for="i in 46" :key="i" class="xiu-star" :style="starStyle(i)"></span>
      <span class="xiu-mist m1"></span>
      <span class="xiu-mist m2"></span>
      <span class="xiu-mist m3"></span>
    </div>

    <header class="wb-masthead">
      <div>
        <div class="wb-eyebrow">玄 黄 · 仙 府 一 隅</div>
        <h1 class="wb-title">玄黄 · 工作台</h1>
        <p class="wb-subtitle">把零散念头，沉淀为笔记、内容资产与可执之事。</p>
      </div>
      <div class="wb-sigil" aria-hidden="true">☯</div>
    </header>

    <section class="wb-actions">
      <router-link to="/notes/new" class="wb-action primary">
        <span class="wb-action-icon"><el-icon><Edit /></el-icon></span>
        <span class="wb-action-text">
          <strong>快速记录</strong>
          <small>新建草稿，自动保存</small>
        </span>
      </router-link>
      <router-link to="/assistant" class="wb-action">
        <span class="wb-action-icon"><el-icon><ChatDotRound /></el-icon></span>
        <span class="wb-action-text">
          <strong>AI 助手</strong>
          <small>整理 · 摘要 · 化虚为实</small>
        </span>
      </router-link>
      <router-link to="/assets" class="wb-action">
        <span class="wb-action-icon"><el-icon><FolderOpened /></el-icon></span>
        <span class="wb-action-text">
          <strong>内容资产</strong>
          <small>网页 · 图片 · PDF</small>
        </span>
      </router-link>
      <router-link to="/tasks" class="wb-action">
        <span class="wb-action-icon"><el-icon><Check /></el-icon></span>
        <span class="wb-action-text">
          <strong>任务</strong>
          <small>今日所行 · 逾期之警</small>
        </span>
      </router-link>
    </section>

    <section class="wb-search-row">
      <el-input
        v-model="searchKeyword"
        placeholder="搜笔记 / 资产 / 任务 / 标签"
        clearable
        size="large"
        @keyup.enter="runSearch"
      >
        <template #append>
          <el-button @click="runSearch">搜寻</el-button>
        </template>
      </el-input>
    </section>

    <div class="wb-grid">
      <section class="wb-card">
        <header class="wb-card-header">
          <h2>今日任务</h2>
          <router-link to="/tasks" class="wb-card-link">全部</router-link>
        </header>
        <ul v-if="summary?.today_tasks?.length" class="wb-list">
          <li v-for="t in summary.today_tasks" :key="t.id">
            <router-link :to="`/tasks`">{{ t.title }}</router-link>
            <small>{{ formatDate(t.due_date) }}</small>
          </li>
        </ul>
        <p v-else class="wb-empty">今日暂无任务，静坐修行</p>
      </section>

      <section class="wb-card">
        <header class="wb-card-header">
          <h2>逾期任务</h2>
          <router-link to="/tasks" class="wb-card-link">查看</router-link>
        </header>
        <ul v-if="summary?.overdue_tasks?.length" class="wb-list danger">
          <li v-for="t in summary.overdue_tasks" :key="t.id">
            <router-link :to="`/tasks`">{{ t.title }}</router-link>
            <small>逾期 · {{ formatDate(t.due_date) }}</small>
          </li>
        </ul>
        <p v-else class="wb-empty">没有逾期任务</p>
      </section>

      <section class="wb-card">
        <header class="wb-card-header">
          <h2>最近编辑</h2>
          <router-link to="/notes" class="wb-card-link">全部笔记</router-link>
        </header>
        <ul v-if="summary?.recent_notes?.length" class="wb-list">
          <li v-for="n in summary.recent_notes" :key="n.id">
            <router-link :to="`/notes/${n.id}`">{{ n.title || '（无标题）' }}</router-link>
            <small>{{ n.status === 'completed' ? '已完成' : '草稿' }} · {{ formatDate(n.updated_at) }}</small>
          </li>
        </ul>
        <p v-else class="wb-empty">还没有笔记</p>
      </section>

      <section class="wb-card">
        <header class="wb-card-header">
          <h2>待整理草稿</h2>
          <router-link to="/notes?status=draft" class="wb-card-link">查看</router-link>
        </header>
        <ul v-if="summary?.draft_notes?.length" class="wb-list">
          <li v-for="n in summary.draft_notes" :key="n.id">
            <router-link :to="`/notes/${n.id}`">{{ n.title || '（无标题）' }}</router-link>
            <small>草稿 · {{ formatDate(n.updated_at) }}</small>
          </li>
        </ul>
        <p v-else class="wb-empty">没有待整理草稿</p>
      </section>

      <section class="wb-card">
        <header class="wb-card-header">
          <h2>分类入口</h2>
        </header>
        <div class="wb-categories">
          <router-link to="/notes" class="wb-chip"><el-icon class="wb-chip-icon"><Document /></el-icon>笔记</router-link>
          <router-link to="/assets?type=link" class="wb-chip"><el-icon class="wb-chip-icon"><Link /></el-icon>网页</router-link>
          <router-link to="/assets?type=image" class="wb-chip"><el-icon class="wb-chip-icon"><Picture /></el-icon>图片</router-link>
          <router-link to="/assets?type=pdf" class="wb-chip"><el-icon class="wb-chip-icon"><Document /></el-icon>PDF</router-link>
          <router-link to="/tasks" class="wb-chip"><el-icon class="wb-chip-icon"><Check /></el-icon>任务</router-link>
        </div>
      </section>

      <section class="wb-card">
        <header class="wb-card-header">
          <h2>旧模块</h2>
        </header>
        <div class="wb-categories">
          <router-link to="/home" class="wb-chip"><el-icon class="wb-chip-icon"><Compass /></el-icon>浮空岛首页</router-link>
          <router-link to="/island/music" class="wb-chip"><el-icon class="wb-chip-icon"><Headset /></el-icon>音乐</router-link>
          <router-link to="/island/novel" class="wb-chip"><el-icon class="wb-chip-icon"><Reading /></el-icon>小说</router-link>
          <router-link to="/island/video" class="wb-chip"><el-icon class="wb-chip-icon"><VideoCamera /></el-icon>视频</router-link>
          <router-link to="/island/log" class="wb-chip"><el-icon class="wb-chip-icon"><Document /></el-icon>日志</router-link>
          <router-link to="/island/tool" class="wb-chip"><el-icon class="wb-chip-icon"><Tools /></el-icon>工具</router-link>
        </div>
      </section>

      <section class="wb-card">
        <header class="wb-card-header">
          <h2>标签</h2>
        </header>
        <div class="wb-categories">
          <span v-if="!tagList.length" class="wb-empty">还没有标签</span>
          <router-link
            v-for="t in tagList"
            :key="t.id"
            :to="`/notes?tag=${encodeURIComponent(t.name)}`"
            class="wb-chip tag"
          >#{{ t.name }}</router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Edit, FolderOpened, Check, Document, Link, Picture, Headset, VideoCamera, Reading, Tools, Compass, ChatDotRound } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { workbenchApi } from '@/api/workbench'
import { useWorkbenchStore } from '@/stores/workbench'

const router = useRouter()
const store = useWorkbenchStore()
const summary = ref(null)
const tagList = ref([])
const searchKeyword = ref('')

async function load() {
  await store.loadSummary()
  summary.value = store.summary
  try {
    const res = await workbenchApi.tags.list()
    tagList.value = res.data?.list || []
  } catch {
    tagList.value = []
  }
}

function runSearch() {
  const q = (searchKeyword.value || '').trim()
  if (!q) return
  router.push({ path: '/notes', query: { q } })
}

function formatDate(s) {
  if (!s) return ''
  try {
    return new Date(s).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return s
  }
}

// 确定性星点定位（避免随机抖动）
function starStyle(i) {
  const c = i * 137.508
  return `left:${c % 100}%;top:${(i * 61.8) % 100}%;` +
    `width:${0.6 + (((c * 7) % 10) / 10) * 1.3}px;height:${0.6 + (((c * 7) % 10) / 10) * 1.3}px;` +
    `animation-delay:${((c * 3) % 100) / 10}s;opacity:${0.35 + (((c * 13) % 100) / 100) * 0.6}`
}

onMounted(load)
</script>

<style scoped>
.workbench-page {
  position: relative;
  font-family: var(--font-serif);
  max-width: 1200px;
  margin: 0 auto;
  padding: 44px 24px 84px;
  color: var(--xiu-text);
  overflow: hidden;
  min-height: 100vh;
}

/* ===== 夜色背景 ===== */
.xiu-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.xiu-star {
  position: absolute; border-radius: 50%;
  background: radial-gradient(circle, rgba(205, 225, 245, 0.9), transparent 70%);
  animation: xiu-twinkle 4s ease-in-out infinite;
}
.xiu-mist { position: absolute; border-radius: 50%; filter: blur(70px); opacity: .14;
  background: linear-gradient(135deg, #4a6a7a, #1a3a4a); animation: xiu-mist 34s ease-in-out infinite; }
.xiu-mist.m1 { width: 620px; height: 320px; top: 8%; left: -8%; }
.xiu-mist.m2 { width: 520px; height: 260px; bottom: 2%; right: -6%; animation-direction: reverse; animation-duration: 44s; }
.xiu-mist.m3 { width: 760px; height: 220px; top: 55%; left: 18%; animation-delay: 6s; opacity: .08; }
@keyframes xiu-twinkle { 0%, 100% { opacity: .28; } 50% { opacity: .9; } }
@keyframes xiu-mist { 0%, 100% { transform: translateX(0) translateY(0); } 50% { transform: translateX(46px) translateY(-22px); } }
@keyframes xiu-rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }

.workbench-page > *:not(.xiu-bg) { position: relative; z-index: 1; }

/* ===== 顶栏 ===== */
.wb-masthead {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; flex-wrap: wrap;
  padding-bottom: 22px; border-bottom: 1px solid var(--xiu-line); margin-bottom: 26px;
  animation: xiu-rise .8s cubic-bezier(.4,0,.2,1) both;
}
.wb-eyebrow { font-size: 11px; letter-spacing: .5em; color: var(--xiu-gold); opacity: .85; margin-bottom: 8px; }
.wb-title {
  font-size: 34px; font-weight: 600; letter-spacing: .08em; margin: 0;
  background: linear-gradient(135deg, #c9a96e 0%, #f0e6c8 48%, #c9a96e 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 2px 10px rgba(201, 169, 110, .18));
}
.wb-subtitle { margin: 6px 0 0; font-size: 13px; color: var(--xiu-text-2); letter-spacing: .18em; }
.wb-sigil {
  width: 42px; height: 42px; border: 1px solid var(--xiu-line); border-radius: 50%;
  display: flex; align-items: center; justify-content: center; color: var(--xiu-gold); font-size: 18px;
  background: radial-gradient(circle at 50% 35%, rgba(201, 169, 110, .14), transparent 70%);
}

/* ===== 快捷动作 ===== */
.wb-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 0 0 24px; }
.wb-action {
  position: relative; display: flex; gap: 14px; align-items: center; padding: 18px;
  border-radius: 14px; color: var(--xiu-text); text-decoration: none;
  background: var(--xiu-card); backdrop-filter: blur(14px);
  border: 1px solid var(--xiu-line); overflow: hidden;
  box-shadow: 0 18px 40px rgba(0, 0, 0, .35), inset 0 1px 0 rgba(255, 255, 255, .04);
  transition: var(--transition); animation: xiu-rise .7s cubic-bezier(.4,0,.2,1) both;
}
.wb-action::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--xiu-gold), transparent); opacity: .7; }
.wb-action-icon {
  width: 46px; height: 46px; flex: none; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: var(--xiu-primary-bright); font-size: 22px;
  border: 1px solid rgba(93, 224, 216, .25); background: rgba(61, 184, 176, .08);
  transition: var(--transition);
}
.wb-action:hover { transform: translateY(-2px); border-color: rgba(93, 224, 216, .4);
  box-shadow: 0 22px 52px rgba(0, 0, 0, .5), 0 0 30px var(--xiu-glow); }
.wb-action:hover .wb-action-icon { background: rgba(61, 184, 176, .18); box-shadow: 0 0 22px var(--xiu-glow); }
.wb-action-text { display: flex; flex-direction: column; }
.wb-action-text strong { font-size: 16px; letter-spacing: .06em; }
.wb-action-text small { margin-top: 3px; color: var(--xiu-text-2); font-size: 12px; }
.wb-action.primary { background: linear-gradient(135deg, rgba(36, 64, 72, .92), rgba(30, 52, 64, .85)); border-color: rgba(93, 224, 216, .35); }
.wb-action.primary .wb-action-icon { color: var(--xiu-gold); border-color: rgba(201, 169, 110, .3); background: rgba(201, 169, 110, .1); }

/* ===== 搜索 ===== */
.wb-search-row { margin-bottom: 28px; animation: xiu-rise .8s .1s both; }
.wb-search-row :deep(.el-input__wrapper) {
  background: var(--xiu-card); border-radius: 999px 0 0 999px;
  box-shadow: 0 0 0 1px var(--xiu-line) inset; padding-left: 18px;
}
.wb-search-row :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px rgba(93, 224, 216, .45) inset, 0 0 0 3px rgba(61, 184, 176, .12); }
.wb-search-row :deep(.el-input-group__append) {
  background: linear-gradient(135deg, var(--xiu-primary-bright), var(--xiu-primary));
  border: none; border-radius: 0 999px 999px 0; padding: 0 20px;
}
.wb-search-row :deep(.el-input-group__append .el-button) { background: transparent; border: none; color: #0a1218; font-family: var(--font-serif); font-size: 13px; letter-spacing: .2em; margin: 0; }

/* ===== 卡片网格 ===== */
.wb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }
.wb-card {
  position: relative; padding: 20px 20px 16px; border-radius: 16px;
  background: var(--xiu-card); backdrop-filter: blur(14px);
  border: 1px solid var(--xiu-line); overflow: hidden;
  box-shadow: 0 16px 40px rgba(0, 0, 0, .32), inset 0 1px 0 rgba(255, 255, 255, .04);
  transition: var(--transition); animation: xiu-rise .7s both;
}
.wb-card::before { content: ""; position: absolute; top: 0; left: 16%; right: 16%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--xiu-gold), transparent); opacity: .6; }
.wb-card:hover { transform: translateY(-2px); border-color: rgba(201, 169, 110, .32); box-shadow: 0 20px 46px rgba(0, 0, 0, .42); }
.wb-card:nth-child(1) { animation-delay: .12s; } .wb-card:nth-child(2) { animation-delay: .2s; }
.wb-card:nth-child(3) { animation-delay: .28s; } .wb-card:nth-child(4) { animation-delay: .36s; }
.wb-card:nth-child(5) { animation-delay: .44s; } .wb-card:nth-child(6) { animation-delay: .52s; }
.wb-card:nth-child(7) { animation-delay: .6s; }
.wb-card-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px; }
.wb-card-header h2 { font-size: 16px; margin: 0; font-weight: 600; letter-spacing: .08em; }
.wb-card-link { font-size: 12px; color: var(--xiu-gold); text-decoration: none; transition: var(--transition); }
.wb-card-link:hover { color: var(--xiu-primary-bright); text-shadow: 0 0 12px var(--xiu-glow); }

.wb-list { list-style: none; margin: 0; padding: 0; }
.wb-list li { display: flex; justify-content: space-between; gap: 10px; padding: 11px 2px;
  border-top: 1px dashed rgba(201, 169, 110, .14); font-size: 14px; transition: var(--transition); }
.wb-list li:first-child { border-top: 0; }
.wb-list li:hover { transform: translateX(3px); }
.wb-list a { color: var(--xiu-text); text-decoration: none; transition: var(--transition); }
.wb-list li:hover a { color: var(--xiu-primary-bright); }
.wb-list li small { color: var(--xiu-text-3); font-size: 11px; white-space: nowrap; }
.wb-list.danger li a { color: var(--xiu-danger); }
.wb-list.danger li:hover a { color: var(--xiu-danger); }
.wb-empty { color: var(--xiu-text-3); font-size: 13px; margin: 4px 0; }

.wb-categories { display: flex; flex-wrap: wrap; gap: 9px; }
.wb-chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 999px;
  font-size: 12px; letter-spacing: .06em; color: var(--xiu-text-2); text-decoration: none;
  background: rgba(20, 40, 52, .5); border: 1px solid var(--xiu-line); transition: var(--transition);
}
.wb-chip:hover { color: var(--xiu-primary-bright); border-color: rgba(93, 224, 216, .4); box-shadow: 0 0 16px rgba(61, 184, 176, .14); }
.wb-chip.tag { color: var(--xiu-gold); }
.wb-chip.tag:hover { color: var(--xiu-gold-bright); border-color: rgba(201, 169, 110, .45); }
.wb-chip-icon { font-size: 14px; vertical-align: -0.15em; }

@media (prefers-reduced-motion: reduce) {
  .workbench-page *, .workbench-page *::before, .workbench-page *::after { animation: none !important; transition: none !important; }
}
@media (max-width: 600px) {
  .wb-title { font-size: 26px; }
  .wb-actions { grid-template-columns: 1fr; }
  .wb-grid { grid-template-columns: 1fr; }
  .workbench-page { padding: 32px 16px 72px; }
}
</style>
<template>
  <div class="workbench-page">
    <header class="wb-header">
      <h1 class="wb-title">玄黄 · 工作台</h1>
      <p class="wb-subtitle">把零散想法沉淀为笔记、内容资产和可执行任务。</p>
    </header>

    <section class="wb-actions">
      <router-link to="/notes/new" class="wb-action primary">
        <span class="wb-action-icon">✎</span>
        <span class="wb-action-text">
          <strong>快速记录</strong>
          <small>新建一条草稿笔记，自动保存</small>
        </span>
      </router-link>
      <router-link to="/assistant" class="wb-action">
        <span class="wb-action-icon">⚘</span>
        <span class="wb-action-text">
          <strong>AI 助手</strong>
          <small>整理、摘要、生成任务</small>
        </span>
      </router-link>
      <router-link to="/assets" class="wb-action">
        <span class="wb-action-icon">▣</span>
        <span class="wb-action-text">
          <strong>内容资产</strong>
          <small>网页、图片、PDF</small>
        </span>
      </router-link>
      <router-link to="/tasks" class="wb-action">
        <span class="wb-action-icon">✓</span>
        <span class="wb-action-text">
          <strong>任务</strong>
          <small>今日待办与跟进</small>
        </span>
      </router-link>
    </section>

    <section class="wb-search-row">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索笔记 / 资产 / 任务 / 标签"
        clearable
        size="large"
        @keyup.enter="runSearch"
      >
        <template #append>
          <el-button @click="runSearch">搜索</el-button>
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
        <p v-else class="wb-empty">今日暂无任务</p>
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
          <router-link to="/notes" class="wb-chip">📝 笔记</router-link>
          <router-link to="/assets?type=link" class="wb-chip">🔗 网页</router-link>
          <router-link to="/assets?type=image" class="wb-chip">🖼 图片</router-link>
          <router-link to="/assets?type=pdf" class="wb-chip">📄 PDF</router-link>
          <router-link to="/tasks" class="wb-chip">✓ 任务</router-link>
        </div>
      </section>

      <section class="wb-card">
        <header class="wb-card-header">
          <h2>旧模块</h2>
        </header>
        <div class="wb-categories">
          <router-link to="/home" class="wb-chip">🏝 浮空岛首页</router-link>
          <router-link to="/island/music" class="wb-chip">🎵 音乐</router-link>
          <router-link to="/island/novel" class="wb-chip">📖 小说</router-link>
          <router-link to="/island/video" class="wb-chip">🎬 视频</router-link>
          <router-link to="/island/log" class="wb-chip">📝 日志</router-link>
          <router-link to="/island/tool" class="wb-chip">⚙️ 工具</router-link>
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

onMounted(load)
</script>

<style scoped>
.workbench-page {
  font-family: var(--font-serif);
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px 80px;
  color: var(--color-text-dark);
}
.wb-header { margin-bottom: 16px; }
.wb-title { font-size: 28px; margin: 0 0 4px; font-weight: 600; }
.wb-subtitle { color: var(--color-text-muted); margin: 0; font-size: 14px; }
.wb-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin: 16px 0 20px;
}
.wb-action {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-sm);
  background: var(--paper-white);
  color: inherit;
  text-decoration: none;
  border: 1px solid var(--paper-cream);
  transition: var(--transition);
}
.wb-action:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.wb-action.primary { background: linear-gradient(135deg, var(--rattan-yellow), var(--ochre)); color: var(--paper-white); border-color: transparent; }
.wb-action-icon { font-size: 24px; }
.wb-action-text { display: flex; flex-direction: column; }
.wb-action-text small { opacity: 0.8; font-size: 12px; }
.wb-search-row { margin-bottom: 24px; }
.wb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
.wb-card {
  background: var(--paper-white);
  border: 1px solid var(--paper-aged);
  border-radius: 10px;
  padding: 14px 16px;
}
.wb-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.wb-card-header h2 { font-size: 15px; margin: 0; font-weight: 600; }
.wb-card-link { font-size: 12px; color: var(--ochre); text-decoration: none; }
.wb-list { list-style: none; margin: 0; padding: 0; }
.wb-list li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px dashed var(--paper-aged);
  font-size: 14px;
}
.wb-list li:first-child { border-top: 0; }
.wb-list li small { color: var(--color-text-muted); font-size: 12px; }
.wb-list.danger li a { color: var(--color-danger); }
.wb-empty { color: var(--color-text-muted); font-size: 13px; margin: 4px 0; }
.wb-categories { display: flex; flex-wrap: wrap; gap: 8px; }
.wb-chip {
  background: var(--paper-white);
  border: 1px solid var(--paper-cream);
  border-radius: var(--radius-sm);
  padding: 4px 12px;
  font-size: 13px;
  text-decoration: none;
  color: inherit;
}
.wb-chip.tag { background: var(--paper-white); }

@media (max-width: 600px) {
  .wb-title { font-size: 22px; }
  .wb-actions { grid-template-columns: 1fr; }
  .wb-grid { grid-template-columns: 1fr; }
}
</style>

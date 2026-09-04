<template>
  <div class="workbench-page">
    <!-- 浅底留白背景：宣纸纹理 + 极淡云雾 -->
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
      <div class="lj-wash w3"></div>
    </div>

    <!-- 玉简轮播作为主角（岛屿导航核心） -->
    <section class="wb-hero">
      <div class="wb-eyebrow">玄 黄 · 仙 府 一 隅</div>
      <h1 class="wb-title">玄黄 · 工作台</h1>
      <p class="wb-subtitle">把零散念头，沉淀为笔记、内容资产与可执之事。</p>
      <JadeCarousel class="wb-jade" />
    </section>

    <!-- 快捷动作 + 数据面板 -->
    <div class="wb-body">
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
            <router-link to="/music" class="wb-chip"><el-icon class="wb-chip-icon"><Headset /></el-icon>音乐</router-link>
            <router-link to="/novel" class="wb-chip"><el-icon class="wb-chip-icon"><Reading /></el-icon>小说</router-link>
            <router-link to="/video" class="wb-chip"><el-icon class="wb-chip-icon"><VideoCamera /></el-icon>视频</router-link>
            <router-link to="/tool" class="wb-chip"><el-icon class="wb-chip-icon"><Tools /></el-icon>工具</router-link>
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

    <!-- 底部网安/备案标识（浅色留白页脚，随浅色页面底边展开） -->
    <SiteFooter variant="light" class="wb-footer" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Edit, FolderOpened, Check, Document, Link, Picture, Headset, VideoCamera, Reading, ChatDotRound, Tools } from '@element-plus/icons-vue'
import { useWorkbenchStore } from '@/stores/workbench'
import { workbenchApi } from '@/api/workbench'
import JadeCarousel from '@/components/JadeCarousel.vue'
import SiteFooter from '@/components/SiteFooter.vue'

const store = useWorkbenchStore()
const summary = ref(null)
const tagList = ref([])

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
  position: relative;
  font-family: var(--font-serif);
  /* 全宽浅底：收窄视口(桌面放大)或宽屏时，浅色宣纸底铺满视口，避免两侧露出深色产生黑边 */
  width: 100%;
  padding: 96px 0 0;
  box-sizing: border-box;
  color: var(--lj-text);
  min-height: 100vh;
  overflow-x: hidden;
}
/* 内容块与页脚统一在 1200px 内居中，横向留白 24px 与旧版一致 */
.wb-hero,
.wb-body,
.wb-footer {
  width: 100%;
  max-width: 1248px;
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
  padding: 0 24px;
}
.wb-footer {
  position: relative;
  z-index: 1;
  margin-top: 28px;
  padding-bottom: 84px;
}

/* ===== 浅底留白背景 ===== */
.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 60% 40% at 20% 8%, rgba(74, 95, 99, 0.05), transparent 60%),
    radial-gradient(ellipse 50% 40% at 85% 30%, rgba(176, 128, 90, 0.05), transparent 60%),
    var(--lj-bg);
}
.lj-paper-texture {
  position: absolute; inset: 0; opacity: 0.55;
  background:
    repeating-linear-gradient(0deg, rgba(58, 67, 80, 0.012) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(58, 67, 80, 0.008) 0 1px, transparent 1px 7px);
}
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4;
  background: radial-gradient(circle, rgba(74, 95, 99, 0.12), transparent 70%); animation: lj-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 480px; height: 420px; top: 12%; left: -6%; }
.lj-wash.w2 { width: 420px; height: 360px; bottom: 6%; right: -5%; animation-delay: 8s; }
.lj-wash.w3 { width: 520px; height: 300px; top: 48%; left: 38%; opacity: 0.24; animation-delay: 16s; }
@keyframes lj-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(36px,-20px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

.workbench-page > *:not(.lj-bg) { position: relative; z-index: 1; }

/* ===== 主角区：玉简 ===== */
.wb-hero { text-align: center; padding: 6px 0 8px; animation: lj-rise .8s cubic-bezier(.4,0,.2,1) both; }
.wb-eyebrow { font-size: 11px; letter-spacing: .5em; color: var(--lj-mist); margin-bottom: 10px; }
.wb-title { font-size: 34px; font-weight: 600; letter-spacing: .1em; margin: 0; color: var(--lj-text); }
.wb-subtitle { margin: 10px 0 0; font-size: 13px; color: var(--lj-text-2); letter-spacing: .18em; }
.wb-jade { margin-top: 8px; }
@keyframes lj-rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }

/* ===== 数据区 ===== */
.wb-body { padding-top: 10px; }
.wb-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 0 0 24px; }
.wb-action {
  position: relative; display: flex; gap: 14px; align-items: center; padding: 18px;
  border-radius: 14px; color: var(--lj-text); text-decoration: none;
  background: var(--lj-paper);
  border: 1px solid var(--lj-line); overflow: hidden;
  box-shadow: var(--lj-shadow);
  transition: all 0.3s; animation: lj-rise .7s cubic-bezier(.4,0,.2,1) both;
}
.wb-action::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--lj-dai), transparent); opacity: .6; }
.wb-action-icon {
  width: 46px; height: 46px; flex: none; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: var(--lj-dai); font-size: 22px;
  border: 1px solid var(--lj-line); background: rgba(74, 95, 99, 0.06);
  transition: all 0.3s;
}
.wb-action:hover { transform: translateY(-2px); border-color: var(--lj-line-strong); box-shadow: 0 12px 30px rgba(58, 67, 80, 0.12); }
.wb-action:hover .wb-action-icon { background: rgba(74, 95, 99, 0.1); }
.wb-action-text { display: flex; flex-direction: column; }
.wb-action-text strong { font-size: 16px; letter-spacing: .06em; }
.wb-action-text small { margin-top: 3px; color: var(--lj-text-2); font-size: 12px; }
.wb-action.primary { background: linear-gradient(135deg, var(--lj-paper), #eef0eb); }
.wb-action.primary .wb-action-icon { color: var(--lj-ochre); border-color: rgba(176, 128, 90, 0.25); background: rgba(176, 128, 90, 0.08); }

/* ===== 卡片网格（玉简同系轻灵） ===== */
.wb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }
.wb-card {
  position: relative; padding: 20px 20px 16px; border-radius: 14px;
  background: var(--lj-paper);
  border: 1px solid var(--lj-line); overflow: hidden;
  box-shadow: var(--lj-shadow);
  transition: all 0.3s; animation: lj-rise .7s both;
}
.wb-card::before { content: ""; position: absolute; top: 0; left: 16%; right: 16%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--lj-dai), transparent); opacity: .5; }
.wb-card:hover { transform: translateY(-2px); border-color: var(--lj-line-strong); box-shadow: 0 12px 28px rgba(58, 67, 80, 0.12); }
.wb-card:nth-child(1) { animation-delay: .1s; } .wb-card:nth-child(2) { animation-delay: .16s; }
.wb-card:nth-child(3) { animation-delay: .22s; } .wb-card:nth-child(4) { animation-delay: .28s; }
.wb-card:nth-child(5) { animation-delay: .34s; } .wb-card:nth-child(6) { animation-delay: .4s; }
.wb-card-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px; }
.wb-card-header h2 { font-size: 16px; margin: 0; font-weight: 600; letter-spacing: .08em; color: var(--lj-text); }
.wb-card-link { font-size: 12px; color: var(--lj-dai); text-decoration: none; transition: all 0.25s; }
.wb-card-link:hover { color: var(--lj-ochre); }

.wb-list { list-style: none; margin: 0; padding: 0; }
.wb-list li { display: flex; justify-content: space-between; gap: 10px; padding: 11px 2px;
  border-top: 1px dashed var(--lj-line); font-size: 14px; transition: all 0.25s; }
.wb-list li:first-child { border-top: 0; }
.wb-list li:hover { transform: translateX(3px); }
.wb-list a { color: var(--lj-text); text-decoration: none; transition: all 0.25s; }
.wb-list li:hover a { color: var(--lj-dai); }
.wb-list li small { color: var(--lj-text-3); font-size: 11px; white-space: nowrap; }
.wb-list.danger li a { color: var(--lj-vermilion); }
.wb-list.danger li:hover a { color: var(--lj-vermilion); }
.wb-empty { color: var(--lj-text-3); font-size: 13px; margin: 4px 0; }

.wb-categories { display: flex; flex-wrap: wrap; gap: 9px; }
.wb-chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 999px;
  font-size: 12px; letter-spacing: .06em; color: var(--lj-text-2); text-decoration: none;
  background: rgba(251, 250, 246, 0.8); border: 1px solid var(--lj-line); transition: all 0.25s;
}
.wb-chip:hover { color: var(--lj-dai); border-color: var(--lj-line-strong); box-shadow: 0 4px 12px rgba(58, 67, 80, 0.08); }
.wb-chip.tag { color: var(--lj-ochre); }
.wb-chip.tag:hover { color: var(--lj-dai-deep); border-color: rgba(176, 128, 90, 0.4); }
.wb-chip-icon { font-size: 14px; vertical-align: -0.15em; }

@media (prefers-reduced-motion: reduce) {
  .workbench-page *, .workbench-page *::before, .workbench-page *::after { animation: none !important; transition: none !important; }
}
@media (max-width: 600px) {
  .wb-title { font-size: 26px; }
  .wb-actions { grid-template-columns: 1fr; }
  .wb-grid { grid-template-columns: 1fr; }
  .workbench-page { padding: 88px 0 8px; }
  .wb-hero,
  .wb-body,
  .wb-footer { padding: 0 16px; }
  .wb-footer { margin-top: 20px; padding-bottom: 80px; }
}
</style>
<!--
  NotesView.vue
  玄黄・笔记列表页
  - 顶部：返回 + 标题 + 新建笔记
  - 工具栏：搜索 + 状态 + 标签（主题感知 el-input / el-select）
  - 列表：玻璃卡片，鎏金顶光线
-->
<template>
  <div class="notes-page">
    <header class="notes-header">
      <div class="notes-header-left">
        <BackButton fallback="/workbench" />
        <h1 class="notes-title">笔记</h1>
      </div>
      <button class="nt-btn nt-btn-primary" @click="createNew">
        新建笔记
      </button>
    </header>

    <section class="notes-toolbar">
      <div class="nt-toolbar-row">
        <el-input
          v-model="keyword"
          class="nt-input"
          placeholder="搜索标题 / 正文 / 摘要"
          clearable
          @keyup.enter="reload"
        />
        <el-select
          v-model="statusFilter"
          class="nt-select"
          placeholder="状态"
          clearable
          @change="reload"
        >
          <el-option label="草稿" value="draft" />
          <el-option label="已完成" value="completed" />
        </el-select>
        <el-select
          v-model="tagFilter"
          class="nt-select nt-select-tags"
          placeholder="标签"
          clearable
          @change="reload"
        >
          <el-option v-for="t in tags" :key="t.id" :label="`#${t.name}`" :value="t.name" />
        </el-select>
      </div>
    </section>

    <ul v-if="notes.length" class="notes-list">
      <li v-for="n in notes" :key="n.id" class="notes-item">
        <div class="notes-item-main">
          <h3 class="notes-item-title">
            <router-link :to="`/notes/${n.id}`" class="notes-item-link">{{ n.title || '（无标题）' }}</router-link>
            <span class="notes-status" :class="n.status">{{ n.status === 'completed' ? '已完成' : '草稿' }}</span>
          </h3>
          <p class="notes-snippet">{{ snippet(n.content) }}</p>
          <div class="notes-meta">
            <span v-for="t in n.tags" :key="t" class="notes-tag">#{{ t }}</span>
            <span class="notes-time">{{ formatDate(n.updated_at) }}</span>
          </div>
        </div>
        <div class="notes-actions">
          <button class="nt-mini nt-mini-danger" @click="remove(n)">删除</button>
        </div>
      </li>
    </ul>
    <p v-else class="notes-empty">尚无笔记，点击上方「新建笔记」落笔成篇。</p>

    <el-pagination
      v-model:current-page="page"
      :page-size="size"
      :total="total"
      layout="prev, pager, next, total"
      class="notes-pager"
      @current-change="reload"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'
import BackButton from '@/components/BackButton.vue'

const route = useRoute()
const router = useRouter()

const notes = ref([])
const tags = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const keyword = ref(route.query.q || '')
const statusFilter = ref(route.query.status || '')
const tagFilter = ref(route.query.tag || '')

watch(() => route.query, (q) => {
  keyword.value = q.q || ''
  statusFilter.value = q.status || ''
  tagFilter.value = q.tag || ''
  page.value = 1
  reload()
})

async function reload() {
  const params = { page: page.value, size: size.value }
  if (keyword.value) params.q = keyword.value
  if (statusFilter.value) params.status = statusFilter.value
  if (tagFilter.value) params.tag = tagFilter.value
  const res = await workbenchApi.notes.list(params)
  notes.value = res.data.list || []
  total.value = res.data.total || 0
}

async function loadTags() {
  try {
    const res = await workbenchApi.tags.list()
    tags.value = res.data.list || []
  } catch { tags.value = [] }
}

async function createNew() {
  const res = await workbenchApi.notes.create({ title: '未命名草稿', content: '', status: 'draft' })
  router.push(`/notes/${res.data.id}`)
}

async function remove(n) {
  try {
    await ElMessageBox.confirm(`确认删除笔记「${n.title || '（无标题）'}」？删除后进入回收站，可在回收站中恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    })
  } catch { return }
  await workbenchApi.notes.delete(n.id)
  ElMessage.success('已删除')
  reload()
}

function snippet(s) {
  if (!s) return '（无内容）'
  const text = String(s).replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
  return text.length > 100 ? text.slice(0, 100) + '…' : text
}

function formatDate(s) {
  if (!s) return ''
  try {
    return new Date(s).toLocaleString('zh-CN', { hour12: false })
  } catch { return s }
}

onMounted(() => { reload(); loadTags() })
</script>

<style scoped>
.notes-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 84px 16px 80px;
  font-family: var(--font-serif);
  color: var(--lj-text);
}

/* ============ 顶部 ============ */
.notes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
}
.notes-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.notes-title {
  font-size: 26px;
  margin: 0;
  letter-spacing: .08em;
  font-weight: 700;
  background: linear-gradient(135deg,
    var(--yq-gold, #c7a96b),
    var(--yq-gold-bright, #f0e6c8) 48%,
    var(--yq-gold, #c7a96b));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}

/* ============ 工具栏：搜索框宽 + 两个等宽下拉 ============ */
.notes-toolbar { margin-bottom: 18px; }
.nt-toolbar-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px 200px;
  gap: 10px;
  align-items: center;
}
@media (max-width: 720px) {
  .nt-toolbar-row { grid-template-columns: 1fr 1fr; }
  .nt-toolbar-row .nt-input { grid-column: 1 / -1; }
}

/* ElementPlus 控件玻璃化（与音色/封面统一） */
.nt-toolbar-row :deep(.el-input__wrapper),
.nt-toolbar-row :deep(.el-select__wrapper) {
  background: var(--color-bg-glass) !important;
  box-shadow: 0 0 0 1px var(--dp-line) inset !important;
  border-radius: 10px !important;
  padding: 2px 12px !important;
}
.nt-toolbar-row :deep(.el-input__wrapper.is-focus),
.nt-toolbar-row :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--yq-gold) inset, 0 0 0 3px var(--yq-gold-faint, rgba(199, 169, 107, 0.18)) !important;
}
.nt-toolbar-row :deep(.el-input__inner),
.nt-toolbar-row :deep(.el-select__placeholder),
.nt-toolbar-row :deep(.el-select__selected-item) {
  color: var(--lj-text) !important;
  -webkit-text-fill-color: var(--lj-text);
}
.nt-toolbar-row :deep(.el-input__inner::placeholder) {
  color: var(--lj-text-3) !important;
  -webkit-text-fill-color: var(--lj-text-3);
}
.nt-toolbar-row :deep(.el-select__suffix),
.nt-toolbar-row :deep(.el-input__suffix) { color: var(--lj-text-3); }
.nt-toolbar-row :deep(.el-input__wrapper) { min-height: 36px; }

/* ============ 列表项：玻璃卡片 + 鎏金顶光线 ============ */
.notes-list { list-style: none; margin: 0; padding: 0; }
.notes-item {
  position: relative;
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.06));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 10px;
  display: flex;
  gap: 12px;
  overflow: hidden;
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  transition: all .18s ease;
}
.notes-item::before {
  content: "";
  position: absolute;
  top: 0; left: 14%; right: 14%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--yq-gold, #c7a96b), transparent);
  opacity: .55;
}
.notes-item:hover {
  transform: translateY(-1px);
  border-color: var(--yq-gold-glow, rgba(199, 169, 107, 0.4));
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.3);
}
.notes-item-main { flex: 1; min-width: 0; }
.notes-item-title {
  font-size: 16px;
  margin: 0 0 4px;
  display: flex; gap: 8px; align-items: center;
}
.notes-item-link {
  color: var(--lj-text);
  text-decoration: none;
  letter-spacing: .04em;
  flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.notes-item-link:hover { color: var(--yq-gold, #c7a96b); }
.notes-status {
  flex: none;
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--yq-rain-faint, rgba(127, 168, 163, 0.14));
  color: var(--lj-text-2);
  letter-spacing: .04em;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
}
.notes-status.completed {
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.18));
  color: var(--yq-gold, #c7a96b);
  border-color: var(--yq-gold-glow, rgba(199, 169, 107, 0.35));
}

.notes-snippet {
  color: var(--lj-text-2);
  font-size: 13px;
  margin: 6px 0;
  line-height: 1.5;
  word-break: break-word;
}
.notes-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.notes-tag {
  color: var(--yq-gold, #c7a96b);
  font-size: 12px;
  letter-spacing: .04em;
}
.notes-time {
  color: var(--lj-text-3);
  font-size: 12px;
  margin-left: auto;
}

/* ============ 操作 ============ */
.notes-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ============ 按钮 ============ */
.nt-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  min-height: 36px;
  padding: 8px 18px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
  letter-spacing: .04em;
  transition: all .18s ease;
  font-family: inherit;
}
.nt-btn-primary {
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  font-weight: 600;
  box-shadow: 0 4px 14px var(--yq-gold-glow, rgba(199, 169, 107, 0.28));
}
.nt-btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px var(--yq-gold-glow-strong, rgba(199, 169, 107, 0.42));
}
.nt-btn-primary:active { transform: translateY(0); }

.nt-mini {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.22));
  background: transparent;
  color: var(--lj-text-2);
  font-size: 12px;
  cursor: pointer;
  letter-spacing: .04em;
  transition: all .15s;
  font-family: inherit;
}
.nt-mini:hover { color: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); }
.nt-mini-danger:hover { color: var(--dp-danger, #fb7185); border-color: var(--dp-danger, #fb7185); }

/* ============ 空 / 分页 ============ */
.notes-empty {
  color: var(--lj-text-3);
  text-align: center;
  padding: 40px 0;
}
.notes-pager { margin-top: 16px; text-align: right; }

/* 分页器也走项目色 */
.notes-pager :deep(.el-pager li),
.notes-pager :deep(.btn-prev),
.notes-pager :deep(.btn-next) {
  background: transparent !important;
  color: var(--lj-text-2) !important;
}
.notes-pager :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3)) !important;
  color: var(--yq-gold-fg, #0b0f14) !important;
  font-weight: 600;
}

@media (max-width: 600px) {
  .notes-item { flex-direction: column; }
  .notes-actions { justify-content: flex-end; }
  .notes-time { margin-left: 0; }
}
</style>
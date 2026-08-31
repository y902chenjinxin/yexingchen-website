<template>
  <div class="notes-page">
    <header class="notes-header">
      <h1>笔记</h1>
      <el-button type="primary" @click="createNew">新建笔记</el-button>
    </header>

    <div class="notes-toolbar">
      <el-input v-model="keyword" placeholder="搜索标题/正文/摘要" clearable style="max-width:320px" @keyup.enter="reload" />
      <el-select v-model="statusFilter" placeholder="状态" clearable @change="reload" style="width:140px">
        <el-option label="草稿" value="draft" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-select v-model="tagFilter" placeholder="标签" clearable @change="reload" style="width:160px">
        <el-option v-for="t in tags" :key="t.id" :label="`#${t.name}`" :value="t.name" />
      </el-select>
    </div>

    <ul v-if="notes.length" class="notes-list">
      <li v-for="n in notes" :key="n.id" class="notes-item">
        <div class="notes-item-main">
          <h3>
            <router-link :to="`/notes/${n.id}`">{{ n.title || '（无标题）' }}</router-link>
            <el-tag size="small" :type="n.status === 'completed' ? 'success' : 'info'" disable-transitions>
              {{ n.status === 'completed' ? '已完成' : '草稿' }}
            </el-tag>
          </h3>
          <p class="notes-snippet">{{ snippet(n.content) }}</p>
          <div class="notes-meta">
            <span v-for="t in n.tags" :key="t" class="notes-tag">#{{ t }}</span>
            <span class="notes-time">{{ formatDate(n.updated_at) }}</span>
          </div>
        </div>
        <div class="notes-actions">
          <el-button size="small" @click="remove(n)">删除</el-button>
        </div>
      </li>
    </ul>
    <p v-else class="notes-empty">还没有笔记。点击右上角新建一条。</p>

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
    await ElMessageBox.confirm(`确认删除笔记「${n.title || '（无标题）'}」？将进入回收站。`, '提示', {
      type: 'warning',
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
.notes-page { max-width: 960px; margin: 0 auto; padding: 24px 16px 80px; }
.notes-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.notes-header h1 { font-size: 22px; margin: 0; }
.notes-toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.notes-list { list-style: none; margin: 0; padding: 0; }
.notes-item {
  background: var(--paper-white);
  border: 1px solid var(--paper-aged);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  margin-bottom: 8px;
  display: flex;
  gap: 12px;
}
.notes-item-main { flex: 1; min-width: 0; }
.notes-item-main h3 { font-size: 16px; margin: 0 0 4px; display: flex; gap: 8px; align-items: center; }
.notes-snippet { color: var(--color-text-muted); font-size: 13px; margin: 4px 0; line-height: 1.4; word-break: break-word; }
.notes-meta { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.notes-tag { color: var(--ochre); font-size: 12px; }
.notes-time { color: var(--color-text-muted); font-size: 12px; }
.notes-empty { color: var(--color-text-muted); text-align: center; padding: 40px 0; }
.notes-pager { margin-top: 16px; text-align: right; }
@media (max-width: 600px) {
  .notes-item { flex-direction: column; }
  .notes-actions { text-align: right; }
}
</style>

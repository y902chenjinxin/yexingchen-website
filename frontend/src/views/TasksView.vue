<template>
  <div class="tasks-page">
    <header class="tasks-header">
      <BackButton fallback="/workbench" style="margin-right: 12px;" /><h1>任务</h1>
      <el-button type="primary" @click="showCreate = true">新建任务</el-button>
    </header>

    <div class="tasks-toolbar">
      <el-select v-model="statusFilter" placeholder="状态" clearable @change="reload" style="width:140px">
        <el-option label="待办" value="todo" />
        <el-option label="进行中" value="doing" />
        <el-option label="已完成" value="done" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索标题/描述" clearable @keyup.enter="reload" style="max-width:280px" />
    </div>

    <ul v-if="items.length" class="tasks-list">
      <li v-for="t in items" :key="t.id" class="tasks-item">
        <div class="tasks-main">
          <h3>
            <span class="tasks-title">{{ t.title }}</span>
            <el-tag size="small" :type="statusType(t.status)" disable-transitions>{{ statusLabel(t.status) }}</el-tag>
            <el-tag size="small" :type="priorityType(t.priority)" disable-transitions>{{ priorityLabel(t.priority) }}</el-tag>
          </h3>
          <p v-if="t.description" class="tasks-desc">{{ t.description }}</p>
          <div class="tasks-meta">
            <span v-if="t.due_date" class="tasks-due">截止：{{ formatDate(t.due_date) }}</span>
            <span v-if="t.completed_at">完成：{{ formatDate(t.completed_at) }}</span>
          </div>
        </div>
        <div class="tasks-actions">
          <el-select :model-value="t.status" size="small" style="width:110px" @change="(v) => updateStatus(t, v)">
            <el-option label="待办" value="todo" />
            <el-option label="进行中" value="doing" />
            <el-option label="已完成" value="done" />
          </el-select>
          <el-select :model-value="t.priority" size="small" style="width:100px" @change="(v) => updatePriority(t, v)">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
          <el-button size="small" type="danger" plain @click="remove(t)">删除</el-button>
        </div>
      </li>
    </ul>
    <p v-else class="tasks-empty">还没有任务。</p>

    <el-pagination
      v-model:current-page="page"
      :page-size="size"
      :total="total"
      layout="prev, pager, next, total"
      class="tasks-pager"
      @current-change="reload"
    />

    <el-dialog v-model="showCreate" title="新建任务" width="480px">
      <el-form :model="form" label-width="72px">
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="待办" value="todo" />
            <el-option label="进行中" value="doing" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width:100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止">
          <el-input v-model="form.due_date" placeholder="YYYY-MM-DD 或 ISO 时间" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :disabled="!form.title" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'
import BackButton from '@/components/BackButton.vue'

const items = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const statusFilter = ref('')
const keyword = ref('')
const showCreate = ref(false)
const form = ref({ title: '', description: '', status: 'todo', priority: 'medium', due_date: '' })

async function reload() {
  const params = { page: page.value, size: size.value }
  if (statusFilter.value) params.status = statusFilter.value
  if (keyword.value) params.q = keyword.value
  const res = await workbenchApi.tasks.list(params)
  items.value = res.data.list || []
  total.value = res.data.total || 0
}

async function updateStatus(t, status) {
  await workbenchApi.tasks.update(t.id, { status })
  reload()
}
async function updatePriority(t, priority) {
  await workbenchApi.tasks.update(t.id, { priority })
  reload()
}

async function remove(t) {
  try {
    await ElMessageBox.confirm(`确认删除任务「${t.title}」？将进入回收站。`, '提示', { type: 'warning' })
  } catch { return }
  await workbenchApi.tasks.delete(t.id)
  reload()
}

async function submitCreate() {
  const payload = { ...form.value }
  if (!payload.due_date) delete payload.due_date
  await workbenchApi.tasks.create(payload)
  showCreate.value = false
  form.value = { title: '', description: '', status: 'todo', priority: 'medium', due_date: '' }
  reload()
}

function statusLabel(s) { return ({ todo: '待办', doing: '进行中', done: '已完成' })[s] || s }
function statusType(s) { return ({ todo: 'info', doing: 'warning', done: 'success' })[s] || '' }
function priorityLabel(p) { return ({ low: '低', medium: '中', high: '高' })[p] || p }
function priorityType(p) { return ({ low: '', medium: 'info', high: 'danger' })[p] || '' }
function formatDate(s) {
  if (!s) return ''
  try { return new Date(s).toLocaleString('zh-CN', { hour12: false }) } catch { return s }
}

onMounted(reload)
</script>

<style scoped>
.tasks-page { max-width: 960px; margin: 0 auto; padding: 24px 16px 80px; }
.tasks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.tasks-header h1 { font-size: 22px; margin: 0; }
.tasks-toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.tasks-list { list-style: none; margin: 0; padding: 0; }
.tasks-item { background: var(--paper-white); border: 1px solid var(--paper-aged); border-radius: var(--radius-sm); padding: 12px 14px; margin-bottom: 8px; display: flex; gap: 12px; flex-wrap: wrap; }
.tasks-main { flex: 1; min-width: 220px; }
.tasks-main h3 { font-size: 15px; margin: 0 0 4px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.tasks-title { font-weight: 600; }
.tasks-desc { color: var(--color-text-muted); font-size: 13px; margin: 4px 0; }
.tasks-meta { display: flex; gap: 12px; color: var(--color-text-muted); font-size: 12px; }
.tasks-actions { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.tasks-empty { color: var(--color-text-muted); text-align: center; padding: 40px 0; }
.tasks-pager { margin-top: 16px; text-align: right; }
@media (max-width: 600px) {
  .tasks-item { flex-direction: column; }
  .tasks-actions { justify-content: flex-end; }
}
</style>

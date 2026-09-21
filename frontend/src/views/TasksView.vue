<template>
  <div class="tk-page">
    <div class="tk-inner">
      <header class="tk-head">
        <BackButton class="tk-back" />
        <div class="tk-titles">
          <h1 class="tk-title">待办</h1>
          <p class="tk-sub">
            家人生日与订阅到期会自动出现在这里
            <template v-if="autoCount"> · 当前 {{ autoCount }} 条自动提醒</template>
          </p>
        </div>
        <div class="tk-head-right">
          <button class="tk-btn primary" @click="openCreate">＋ 新建待办</button>
        </div>
      </header>

      <div class="tk-toolbar">
        <div class="tk-seg">
          <button v-for="t in TABS" :key="t.value" class="tk-seg-btn"
                  :class="{ on: tab === t.value }" @click="tab = t.value">
            {{ t.label }}<span v-if="counts[t.value]" class="tk-seg-n">{{ counts[t.value] }}</span>
          </button>
        </div>
        <input v-model="keyword" class="tk-input" placeholder="搜索待办" spellcheck="false" @keyup.enter="reload" />
      </div>

      <section v-for="g in groups" :key="g.key" class="tk-group">
        <div class="tk-group-head">
          <span class="tk-group-title" :class="{ urgent: g.urgent }">{{ g.title }}</span>
          <span class="tk-group-n">{{ g.items.length }}</span>
        </div>
        <article v-for="t in g.items" :key="t.id" class="tk-item glass" :class="{ done: t.status === 'done' }">
          <button class="tk-check" :class="{ on: t.status === 'done' }" :title="t.status === 'done' ? '标记为未完成' : '标记完成'"
                  @click="toggleDone(t)">
            <svg v-if="t.status === 'done'" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3.5 8.5 L6.5 11.5 L12.5 4.5" fill="none" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <div class="tk-main">
            <div class="tk-title-row">
              <span class="tk-name">{{ t.title }}</span>
              <span v-if="sourceBadge(t)" class="tk-badge" :class="'is-' + t.source_type">
                {{ sourceBadge(t) }}
              </span>
              <span v-if="t.priority === 'high' && t.status !== 'done'" class="tk-pri">重要</span>
            </div>
            <p v-if="t.description" class="tk-desc">{{ t.description }}</p>
            <div class="tk-meta">
              <span v-if="t.due_date" class="tk-due" :class="{ overdue: isOverdue(t) }">
                {{ dueLabel(t) }}
              </span>
              <span v-if="t.completed_at" class="tk-done-at">完成于 {{ shortDate(t.completed_at) }}</span>
            </div>
          </div>
          <div class="tk-actions">
            <select class="tk-select" :value="t.priority" @change="(e) => setPriority(t, e.target.value)">
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
            <button class="tk-btn ghost tiny" @click="remove(t)">删除</button>
          </div>
        </article>
      </section>

      <EmptyState
        v-if="!loading && !total"
        size="sm"
        title="暂无待办"
        description="手动加一条，或在「通讯录」记下家人生日、「订阅账单」记下到期日，系统会自动生成提醒"
        action-label="＋ 新建待办"
        @action="dialog = true"
      />
      <p v-else-if="loading" class="tk-empty">加载中…</p>
    </div>

    <!-- 新建 -->
    <el-dialog v-model="dialog" title="新建待办" width="480px">
      <el-form :model="form" label-width="72px">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="要做什么" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width:100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止">
          <el-date-picker v-model="form.due_date" type="date" value-format="YYYY-MM-DD"
                          placeholder="可选" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :disabled="!form.title.trim() || saving" @click="submit">
          {{ saving ? '创建中…' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import { workbenchApi } from '@/api/workbench'

const TABS = [
  { value: 'open', label: '未完成' },
  { value: 'done', label: '已完成' },
  { value: 'all', label: '全部' },
]

const items = ref([])
const total = ref(0)
const loading = ref(true)
const tab = ref('open')
const keyword = ref('')
const dialog = ref(false)
const saving = ref(false)
const form = reactive({ title: '', description: '', priority: 'medium', due_date: '' })

const autoCount = computed(() =>
  items.value.filter((t) => t.source_type && t.source_type !== 'manual' && t.status !== 'done').length)

const counts = computed(() => {
  const open = items.value.filter((t) => t.status !== 'done').length
  const done = items.value.filter((t) => t.status === 'done').length
  return { open, done, all: items.value.length }
})

function todayKey() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function dueKey(t) {
  return (t.due_date || '').slice(0, 10)
}

function dayDiff(t) {
  const due = dueKey(t)
  if (!due) return null
  const a = new Date(`${due}T00:00:00`)
  const b = new Date(`${todayKey()}T00:00:00`)
  return Math.round((a - b) / 86400000)
}

const groups = computed(() => {
  const open = items.value.filter((t) => t.status !== 'done')
  const done = items.value.filter((t) => t.status === 'done')

  // 「已完成」与「全部」标签下只展示对应分组，避免同一批数据出现两遍
  if (tab.value === 'done') {
    return done.length ? [{ key: 'done', title: '已完成', items: done, urgent: false }] : []
  }

  const overdue = []
  const today = []
  const week = []
  const later = []
  const nodate = []
  for (const t of open) {
    const d = dayDiff(t)
    if (d === null) nodate.push(t)
    else if (d < 0) overdue.push(t)
    else if (d === 0) today.push(t)
    else if (d <= 7) week.push(t)
    else later.push(t)
  }

  const out = []
  if (overdue.length) out.push({ key: 'overdue', title: '已逾期', items: overdue, urgent: true })
  if (today.length) out.push({ key: 'today', title: '今天', items: today, urgent: true })
  if (week.length) out.push({ key: 'week', title: '未来 7 天', items: week, urgent: false })
  if (later.length) out.push({ key: 'later', title: '更远', items: later, urgent: false })
  if (nodate.length) out.push({ key: 'nodate', title: '未设截止', items: nodate, urgent: false })
  if (tab.value === 'all' && done.length) {
    out.push({ key: 'done', title: '已完成', items: done, urgent: false })
  }
  return out
})

function sourceBadge(t) {
  if (t.source_type === 'contact_birthday') return '生日提醒'
  if (t.source_type === 'subscription') return '续费提醒'
  return ''
}

function isOverdue(t) {
  const d = dayDiff(t)
  return t.status !== 'done' && d !== null && d < 0
}

function dueLabel(t) {
  const d = dayDiff(t)
  if (d === null) return ''
  const date = dueKey(t)
  if (d < 0) return `逾期 ${-d} 天（${date}）`
  if (d === 0) return `今天到期`
  if (d === 1) return `明天到期`
  if (d <= 7) return `${d} 天后（${date}）`
  return date
}

function shortDate(s) {
  return (s || '').slice(0, 10)
}

async function reload() {
  loading.value = true
  try {
    const params = { page: 1, size: 100 }
    if (tab.value === 'open') params.status = undefined
    if (keyword.value.trim()) params.q = keyword.value.trim()
    const res = await workbenchApi.tasks.list(params)
    let rows = res.data?.list || []
    // 后端支持单状态过滤；这里按标签在本地收敛，避免多请求
    if (tab.value === 'open') rows = rows.filter((t) => t.status !== 'done')
    else if (tab.value === 'done') rows = rows.filter((t) => t.status === 'done')
    items.value = rows
    total.value = rows.length
  } catch { /* 拦截器已提示 */ }
  finally { loading.value = false }
}

async function toggleDone(t) {
  const next = t.status === 'done' ? 'todo' : 'done'
  try {
    await workbenchApi.tasks.update(t.id, { status: next })
    t.status = next
    await reload()
  } catch { /* 拦截器已提示 */ }
}

async function setPriority(t, priority) {
  try {
    await workbenchApi.tasks.update(t.id, { priority })
    t.priority = priority
  } catch { /* 拦截器已提示 */ }
}

function openCreate() {
  Object.assign(form, { title: '', description: '', priority: 'medium', due_date: '' })
  dialog.value = true
}

async function submit() {
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      description: form.description || '',
      priority: form.priority,
    }
    if (form.due_date) payload.due_date = form.due_date
    await workbenchApi.tasks.create(payload)
    ElMessage.success('已创建')
    dialog.value = false
    await reload()
  } catch { /* 拦截器已提示 */ }
  finally { saving.value = false }
}

async function remove(t) {
  try {
    await ElMessageBox.confirm(`确认删除「${t.title}」？将进入回收站。`, '提示', { type: 'warning' })
  } catch { return }
  try {
    await workbenchApi.tasks.delete(t.id)
    ElMessage.success('已删除')
    await reload()
  } catch { /* 拦截器已提示 */ }
}

onMounted(reload)
</script>

<style scoped>
.tk-page { min-height: 100vh; }
.tk-inner { max-width: 900px; margin: 0 auto; padding: 84px 20px 40px; }

.tk-head { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.tk-titles { flex: 1; min-width: 180px; }
.tk-title { margin: 0; font-size: 22px; letter-spacing: .1em; color: var(--lj-text); }
.tk-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.tk-head-right { margin-left: auto; }

.tk-btn { border-radius: 9px; padding: 8px 16px; font-size: 13px; border: 1px solid transparent;
  cursor: pointer; transition: all .2s; font-family: inherit; }
.tk-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; }
.tk-btn.ghost { background: transparent; color: var(--lj-text); border-color: var(--lj-line); }
.tk-btn.ghost:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.tk-btn.tiny { padding: 3px 9px; font-size: 12px; }

.tk-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.tk-seg { display: flex; border: 1px solid var(--lj-line); border-radius: 10px; overflow: hidden; }
.tk-seg-btn { padding: 7px 14px; font-size: 13px; cursor: pointer; background: transparent;
  color: var(--lj-text-2); border: none; transition: all .2s; font-family: inherit; }
.tk-seg-btn.on { background: var(--lj-seal-soft); color: var(--lj-seal); }
.tk-seg-n { margin-left: 5px; font-size: 11px; opacity: .8; }
.tk-input { flex: 1 1 180px; min-width: 160px; background: rgba(74,95,99,.08); border: 1px solid var(--lj-line);
  color: var(--lj-text); border-radius: 8px; padding: 8px 11px; font-size: 13px; font-family: inherit; }
.tk-input:focus { outline: none; border-color: var(--lj-seal); }

.tk-group { margin-bottom: 18px; }
.tk-group-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; padding-left: 2px; }
.tk-group-title { font-size: 13px; letter-spacing: .1em; color: var(--lj-text-2); }
.tk-group-title.urgent { color: var(--lj-seal); }
.tk-group-n { font-size: 11px; color: var(--lj-text-3); }

.tk-item { display: flex; align-items: flex-start; gap: 12px; border-radius: 14px;
  padding: 13px 16px; margin-bottom: 8px; }
.tk-item.done { opacity: .6; }
.tk-check { width: 22px; height: 22px; flex: none; margin-top: 1px; border-radius: 7px; cursor: pointer;
  border: 1px solid var(--lj-line-strong); background: transparent; color: #0B0F14;
  display: flex; align-items: center; justify-content: center; transition: all .2s; }
.tk-check.on { background: var(--lj-dai); border-color: var(--lj-dai); color: #fff; }
.tk-check svg { width: 14px; height: 14px; }

.tk-main { flex: 1; min-width: 0; }
.tk-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tk-name { font-size: 14px; font-weight: 600; color: var(--lj-text); }
.tk-item.done .tk-name { text-decoration: line-through; }
.tk-badge { font-size: 11px; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--lj-line);
  color: var(--lj-text-2); }
.tk-badge.is-contact_birthday { color: var(--lj-seal); border-color: var(--lj-seal); background: var(--lj-seal-soft); }
.tk-badge.is-subscription { color: var(--lj-dai); border-color: var(--lj-dai); background: rgba(127,168,163,.14); }
.tk-pri { font-size: 11px; color: var(--pnl-up); }
.tk-desc { margin: 5px 0 0; font-size: 12px; line-height: 1.65; color: var(--lj-text-2); }
.tk-meta { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 6px; font-size: 11px; color: var(--lj-text-3); }
.tk-due.overdue { color: var(--pnl-up); }

.tk-actions { display: flex; gap: 6px; align-items: center; flex: none; }
.tk-select { background: rgba(74,95,99,.08); border: 1px solid var(--lj-line); color: var(--lj-text-2);
  border-radius: 7px; padding: 3px 6px; font-size: 12px; font-family: inherit; }

.tk-empty { text-align: center; padding: 46px 20px; font-size: 13px; line-height: 1.9; color: var(--lj-text-3); }

@media (max-width: 640px) {
  .tk-item { flex-wrap: wrap; }
  .tk-actions { margin-left: 34px; }
}
</style>

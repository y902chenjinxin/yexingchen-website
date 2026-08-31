<template>
  <div class="trash-page">
    <header class="trash-header">
      <h1>回收站</h1>
      <div>
        <el-button type="danger" plain @click="cleanup">清理 30 天前内容</el-button>
      </div>
    </header>

    <p class="trash-hint">回收站保留 30 天，超过将自动清理。物理文件会一并删除。</p>

    <section v-if="data.notes?.length" class="trash-section">
      <h2>笔记（{{ data.notes.length }}）</h2>
      <ul>
        <li v-for="n in data.notes" :key="`n${n.id}`">
          <span>{{ n.title || '（无标题）' }}</span>
          <small>删除于 {{ formatDate(n.deleted_at) }}</small>
          <el-button size="small" @click="restoreNote(n.id)">恢复</el-button>
        </li>
      </ul>
    </section>

    <section v-if="data.assets?.length" class="trash-section">
      <h2>资产（{{ data.assets.length }}）</h2>
      <ul>
        <li v-for="a in data.assets" :key="`a${a.id}`">
          <span>{{ a.title || '（无标题）' }}</span>
          <small>删除于 {{ formatDate(a.deleted_at) }}</small>
          <el-button size="small" @click="restoreAsset(a.id)">恢复</el-button>
        </li>
      </ul>
    </section>

    <section v-if="data.tasks?.length" class="trash-section">
      <h2>任务（{{ data.tasks.length }}）</h2>
      <ul>
        <li v-for="t in data.tasks" :key="`t${t.id}`">
          <span>{{ t.title }}</span>
          <small>删除于 {{ formatDate(t.deleted_at) }}</small>
          <el-button size="small" @click="restoreTask(t.id)">恢复</el-button>
        </li>
      </ul>
    </section>

    <section v-if="data.conversations?.length" class="trash-section">
      <h2>AI 对话（{{ data.conversations.length }}）</h2>
      <ul>
        <li v-for="c in data.conversations" :key="`c${c.id}`">
          <span>{{ c.title }}</span>
          <small>删除于 {{ formatDate(c.deleted_at) }}</small>
        </li>
      </ul>
    </section>

    <p v-if="!hasAny" class="trash-empty">回收站是空的。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'

const data = ref({ notes: [], assets: [], tasks: [], conversations: [] })

const hasAny = computed(() =>
  data.value.notes?.length || data.value.assets?.length || data.value.tasks?.length || data.value.conversations?.length
)

async function reload() {
  const res = await workbenchApi.trash.list()
  data.value = res.data
}

async function restoreNote(id) {
  await workbenchApi.notes.restore(id)
  ElMessage.success('已恢复')
  reload()
}
async function restoreAsset(id) {
  await workbenchApi.assets.restore(id)
  ElMessage.success('已恢复')
  reload()
}
async function restoreTask(id) {
  await workbenchApi.tasks.restore(id)
  ElMessage.success('已恢复')
  reload()
}

async function cleanup() {
  try {
    await ElMessageBox.confirm('将永久删除超过 30 天的回收站内容（含物理文件）。此操作不可恢复。', '永久清理', { type: 'error' })
  } catch { return }
  const res = await workbenchApi.trash.cleanup()
  ElMessage.success(`已清理：${JSON.stringify(res.data.cleaned)}`)
  reload()
}

function formatDate(s) {
  if (!s) return ''
  try { return new Date(s).toLocaleString('zh-CN', { hour12: false }) } catch { return s }
}

onMounted(reload)
</script>

<style scoped>
.trash-page { max-width: 960px; margin: 0 auto; padding: 24px 16px 80px; }
.trash-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.trash-header h1 { font-size: 22px; margin: 0; }
.trash-hint { color: #999; font-size: 13px; margin: 0 0 16px; }
.trash-section { background: #fff; border: 1px solid #ececec; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }
.trash-section h2 { font-size: 14px; margin: 0 0 8px; color: #666; }
.trash-section ul { list-style: none; margin: 0; padding: 0; }
.trash-section li { display: flex; gap: 8px; align-items: center; padding: 6px 0; border-top: 1px dashed #eee; font-size: 14px; }
.trash-section li:first-child { border-top: 0; }
.trash-section li small { color: #999; font-size: 12px; flex: 1; }
.trash-empty { color: #999; text-align: center; padding: 40px 0; }
</style>

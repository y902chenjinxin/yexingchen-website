<template>
  <div class="trash-page">
    <header class="trash-header">
      <BackButton fallback="/workbench" style="margin-right: 12px;" /><h1>回收站</h1>
      <div>
        <el-button type="danger" plain @click="cleanup">清理 30 天前内容</el-button>
      </div>
    </header>

    <p class="trash-hint">回收站保留 30 天，逾时化作尘埃，物理文件一并消散。</p>

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

    <p v-if="!hasAny" class="trash-empty">回收站空无一物，灵台清净。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'
import BackButton from '@/components/BackButton.vue'

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
.trash-page { max-width: 960px; margin: 0 auto; padding: 24px 16px 80px; font-family: var(--font-serif); color: var(--xiu-text); }
.trash-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.trash-header h1 { font-size: 26px; margin: 0; letter-spacing: .08em; background: linear-gradient(135deg,#c9a96e,#f0e6c8 48%,#c9a96e); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color: transparent; }
.trash-hint { color: var(--xiu-text-2); font-size: 13px; margin: 0 0 16px; }
.trash-section { position: relative; background: var(--xiu-card); backdrop-filter: blur(12px); border: 1px solid var(--xiu-line); border-radius: 14px; padding: 12px 16px; margin-bottom: 12px; overflow: hidden; transition: var(--transition); }
.trash-section::before { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px; background: linear-gradient(90deg, transparent, var(--xiu-gold), transparent); opacity: .5; }
.trash-section:hover { border-color: rgba(201, 169, 110, .3); box-shadow: 0 14px 34px rgba(0,0,0,.3); }
.trash-section h2 { font-size: 14px; margin: 0 0 8px; color: var(--xiu-gold); letter-spacing: .1em; }
.trash-section ul { list-style: none; margin: 0; padding: 0; }
.trash-section li { display: flex; gap: 8px; align-items: center; padding: 8px 0; border-top: 1px dashed rgba(201, 169, 110, .15); font-size: 14px; }
.trash-section li:first-child { border-top: 0; }
.trash-section li span { color: var(--xiu-text); }
.trash-section li small { color: var(--xiu-text-3); font-size: 12px; flex: 1; }
.trash-empty { color: var(--xiu-text-3); text-align: center; padding: 40px 0; }
</style>

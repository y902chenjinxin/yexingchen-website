<template>
  <div class="island-page">
    <header class="island-header">
      <div class="header-left">
        <span class="back-btn" @click="router.push('/home')">← 返回</span>
        <span class="island-title">⚙️ 工具岛</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showAdd = true">添加工具</el-button>
      </div>
    </header>

    <main class="tool-grid">
      <div v-if="toolStore.loading" class="loading-placeholder">加载中...</div>
      <div v-else-if="toolStore.list.length === 0" class="empty-placeholder">
        <div class="empty-icon">⚙️</div>
        <div class="empty-text">暂无工具，点击添加</div>
      </div>
      <div v-else v-for="item in toolStore.list" :key="item.id" class="tool-card">
        <div class="tool-icon">{{ item.icon || '⚙️' }}</div>
        <div class="tool-info">
          <div class="tool-title">{{ item.title }}</div>
          <div class="tool-url">{{ formatUrl(item.url) }}</div>
          <div class="tool-desc" v-if="item.description">{{ item.description }}</div>
        </div>
        <div class="tool-actions">
          <el-button size="small" type="primary" @click="openUrl(item.url)">打开</el-button>
          <el-button size="small" @click="handleEdit(item)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(item.id)">删除</el-button>
        </div>
      </div>
    </main>

    <el-dialog v-model="showAdd" :title="editId ? '编辑工具' : '添加工具'" width="450px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" placeholder="工具名称" /></el-form-item>
        <el-form-item label="链接"><el-input v-model="form.url" placeholder="https://..." /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" placeholder="简要描述（可选）" /></el-form-item>
        <el-form-item label="图标"><el-input v-model="form.icon" placeholder="emoji或图标名（可选）" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useToolStore } from '@/stores/tool'

const router = useRouter()
const toolStore = useToolStore()
const showAdd = ref(false)
const editId = ref(null)
const form = ref({ title: '', url: '', description: '', icon: '' })

onMounted(() => { toolStore.fetchList() })

function openUrl(url) {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

function handleEdit(item) {
  editId.value = item.id
  form.value = { title: item.title, url: item.url, description: item.description || '', icon: item.icon || '' }
  showAdd.value = true
}

function closeDialog() {
  showAdd.value = false
  editId.value = null
  form.value = { title: '', url: '', description: '', icon: '' }
}

async function handleSave() {
  if (!form.value.title) { ElMessage.warning('请输入标题'); return }
  if (!form.value.url) { ElMessage.warning('请输入链接'); return }
  try {
    if (editId.value) {
      await toolStore.update(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await toolStore.add(form.value)
      ElMessage.success('添加成功')
    }
    closeDialog()
    toolStore.fetchList()
  } catch { /* 错误已由api拦截器处理 */ }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除这个工具吗？', '提示', { type: 'warning' })
    await toolStore.remove(id)
    ElMessage.success('删除成功')
    toolStore.fetchList()
  } catch { /* 用户取消 */ }
}

function formatUrl(url) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}
</script>

<style scoped>
.island-page { min-height: 100vh; background: linear-gradient(180deg, #FDF5F0 0%, #F5EDE5 100%); padding-bottom: 40px; }
.island-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: rgba(212, 165, 116, 0.2); border-bottom: 1px solid rgba(212, 165, 116, 0.3); }
.header-left { display: flex; align-items: center; gap: 20px; }
.back-btn { color: var(--color-tool); cursor: pointer; font-size: 14px; }
.back-btn:hover { color: #B88B5A; }
.island-title { font-family: var(--font-serif); font-size: 20px; color: var(--color-text); }
.tool-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 30px 40px; }
.loading-placeholder, .empty-placeholder { grid-column: 1 / -1; text-align: center; padding: 60px; color: var(--color-text-secondary); }
.empty-icon { font-size: 60px; margin-bottom: 15px; }
.tool-card { background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(212, 165, 116, 0.3); border-radius: var(--radius); padding: 20px; display: flex; gap: 15px; transition: all 0.3s; }
.tool-card:hover { border-color: var(--color-tool); transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
.tool-icon { font-size: 36px; flex-shrink: 0; }
.tool-info { flex: 1; overflow: hidden; }
.tool-title { font-size: 16px; color: var(--color-text); margin-bottom: 5px; }
.tool-url { font-size: 13px; color: var(--color-tool); margin-bottom: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tool-desc { font-size: 12px; color: var(--color-text-secondary); }
.tool-actions { display: flex; flex-direction: column; gap: 8px; justify-content: center; }
@media (max-width: 768px) {
  .island-header { flex-direction: column; gap: 15px; padding: 15px 20px; }
  .tool-grid { padding: 20px; grid-template-columns: 1fr; }
  .tool-card { flex-direction: column; }
  .tool-actions { flex-direction: row; }
}
</style>
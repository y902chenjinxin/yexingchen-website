<template>
  <IslandInnerBase type="tool" title="工具" subtitle="机关百变">
    <template #toolbar>
      <el-button :type="manage ? 'primary' : 'default'" size="small" plain @click="manage = !manage">
        {{ manage ? '返回卡片' : '管理' }}
      </el-button>
      <el-button v-if="manage" type="primary" size="small" @click="openDialog()">添加</el-button>
    </template>

    <!-- 浏览模式：工具卡片列表 -->
    <div v-show="!manage" class="tool-cards">
      <!-- 内置去水印卡片 -->
      <div class="tool-card" @click="router.push('/tool/watermark')">
        <div class="tool-icon">🎬</div>
        <div class="tool-info">
          <span class="tool-name">视频去水印</span>
          <span class="tool-desc">粘贴分享链接去除水印并下载</span>
        </div>
        <div class="tool-actions">
          <el-button size="small" type="primary" @click.stop="router.push('/tool/watermark')">使用</el-button>
        </div>
      </div>

      <!-- 外部工具卡片 -->
      <div
        v-for="item in toolStore.list"
        :key="item.id"
        class="tool-card"
        @click="router.push('/tool/' + item.id)"
      >
        <div class="tool-icon">{{ item.icon || '🔧' }}</div>
        <div class="tool-info">
          <span class="tool-name">{{ item.title || '无名工具' }}</span>
          <span class="tool-desc">{{ item.description || '暂无描述' }}</span>
        </div>
        <div class="tool-actions">
          <el-button size="small" type="primary" plain @click.stop="router.push('/tool/' + item.id)">使用</el-button>
        </div>
      </div>

      <div v-if="!toolStore.loading && toolStore.list.length === 0" class="tool-empty">
        <span class="empty-icon">⚙️</span>
        <span class="empty-text">暂无可用的外部工具</span>
      </div>
    </div>

    <!-- 管理模式：表格 -->
    <div v-show="manage" class="manage-pane">
      <el-table :data="toolStore.list" v-loading="toolStore.loading" stripe style="width: 100%">
        <el-table-column label="名称" min-width="140">
          <template #default="{ row }">
            <span class="icon-cell">{{ row.icon || '🔧' }}</span>{{ row.title }}
          </template>
        </el-table-column>
        <el-table-column label="图标" width="80">
          <template #default="{ row }">{{ row.icon || '🔧' }}</template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column label="链接(url)" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <a v-if="row.url" :href="row.url" target="_blank" rel="noopener noreferrer" class="file-link">{{ row.url }}</a>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="140">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="openDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!toolStore.loading && toolStore.list.length === 0" class="empty">暂无数据</div>
    </div>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="showDialog" :title="editId ? '编辑工具' : '添加工具'" width="450px" append-to-body>
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.title" placeholder="工具名称" /></el-form-item>
        <el-form-item label="图标"><el-input v-model="form.icon" placeholder="emoji或图标名（可选）" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" placeholder="简要描述（可选）" /></el-form-item>
        <el-form-item label="链接"><el-input v-model="form.url" placeholder="https://..." /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useToolStore } from '@/stores/tool'

const router = useRouter()
const toolStore = useToolStore()

const manage = ref(false)
const showDialog = ref(false)
const editId = ref(null)
const form = ref({ title: '', icon: '', description: '', url: '' })

onMounted(() => { toolStore.fetchList() })

function openDialog(item) {
  editId.value = item ? item.id : null
  form.value = {
    title: item?.title || '',
    icon: item?.icon || '',
    description: item?.description || '',
    url: item?.url || ''
  }
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
  editId.value = null
  form.value = { title: '', icon: '', description: '', url: '' }
}

async function handleSave() {
  if (!form.value.title) { ElMessage.warning('请输入名称'); return }
  if (!form.value.url) { ElMessage.warning('请输入链接'); return }
  try {
    if (editId.value) {
      await toolStore.update(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await toolStore.upload(form.value)
      ElMessage.success('添加成功')
    }
    closeDialog()
    toolStore.fetchList()
  } catch {
    // 错误已由api拦截器处理
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title || '这个工具'}」吗？`, '提示', { type: 'warning' })
    await toolStore.remove(row.id)
    ElMessage.success('删除成功')
    toolStore.fetchList()
  } catch {
    // 用户取消
  }
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.tool-cards {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tool-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px 22px;
  background: linear-gradient(165deg, rgba(255,255,255,.03), rgba(255,255,255,0) 55%), var(--ls-glass);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
  backdrop-filter: saturate(150%) blur(10px);
  -webkit-backdrop-filter: saturate(150%) blur(10px);
  transition: all var(--transition);
  cursor: pointer;
}

.tool-card:hover {
  background: var(--ls-paper-2);
  border-color: var(--ls-line-strong);
  transform: translateX(8px);
}

.tool-icon {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, #a5825a 0%, rgba(196, 154, 108, 0.3) 100%);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex-shrink: 0;
}

.tool-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.tool-name {
  font-family: var(--font-serif);
  color: var(--ls-text);
  font-size: 16px;
}

.tool-desc {
  color: var(--ls-text-2);
  font-size: 13px;
}

.tool-actions {
  flex-shrink: 0;
}

.tool-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px 20px;
  gap: 14px;
  color: var(--ls-text-3);
}

.manage-pane {
  background: var(--ls-glass);
  backdrop-filter: saturate(160%) blur(14px);
  -webkit-backdrop-filter: saturate(160%) blur(14px);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius);
  padding: 30px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}

.empty {
  text-align: center;
  padding: 40px;
  color: var(--ls-text-3);
  font-size: 14px;
}

.icon-cell {
  margin-right: 8px;
}

.file-link {
  color: var(--ls-dai);
  text-decoration: none;
  word-break: break-all;
}

.file-link:hover {
  text-decoration: underline;
}

.manage-pane :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: var(--ls-line);
  --el-table-header-text-color: var(--ls-text-2);
  --el-table-text-color: var(--ls-text);
}
</style>
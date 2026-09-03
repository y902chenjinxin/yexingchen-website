<template>
  <IslandInnerBase type="music" title="音乐" subtitle="音律飘渺">
    <template #toolbar>
      <el-button :type="manage ? 'primary' : 'default'" size="small" plain @click="manage = !manage">
        {{ manage ? '返回卡片' : '管理' }}
      </el-button>
      <el-button v-if="manage" type="primary" size="small" @click="openUpload">上传</el-button>
    </template>

    <MusicInner v-show="!manage" />

    <div v-show="manage" class="manage-pane">
      <el-table :data="musicStore.list" v-loading="musicStore.loading" stripe style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column prop="artist" label="作者" width="110" />
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" min-width="120" show-overflow-tooltip />
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="时长" width="90">
          <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="Number(row.is_default) === 1">
              <el-tag size="small" type="warning">系统内置</el-tag>
            </template>
            <template v-else>
              <el-button size="small" type="primary" plain @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!musicStore.loading && musicStore.list.length === 0" class="empty">暂无数据</div>
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="showUpload" title="上传音乐" width="500px" append-to-body>
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="音乐文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".mp3,.flac,.wav"
            :file-list="uploadFileList"
            @change="handleFileChange"
          >
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="标题"><el-input v-model="uploadForm.title" placeholder="音乐标题" /></el-form-item>
        <el-form-item label="作者"><el-input v-model="uploadForm.artist" placeholder="作者（可选）" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="uploadForm.category" placeholder="分类" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="uploadForm.tags" placeholder="多个标签用逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showEdit" title="编辑音乐" width="460px" append-to-body>
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="标题" required><el-input v-model="editForm.title" placeholder="音乐标题" /></el-form-item>
        <el-form-item label="作者"><el-input v-model="editForm.artist" placeholder="作者（可选）" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="editForm.category" placeholder="分类" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="editForm.tags" placeholder="多个标签用逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="handleEditSubmit">保存</el-button>
      </template>
    </el-dialog>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import MusicInner from './islands/MusicIslandInner.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMusicStore } from '@/stores/music'
import { usePlayerStore } from '@/stores/player'

const musicStore = useMusicStore()
const player = usePlayerStore()

const manage = ref(false)
const showUpload = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)
const uploadFileList = ref([])
const uploadFile = ref(null)
const uploadForm = ref({ title: '', artist: '', category: '', tags: '' })

const showEdit = ref(false)
const editing = ref(false)
const editId = ref(null)
const editForm = ref({ title: '', artist: '', category: '', tags: '' })

onMounted(() => {
  fetchData()
})

async function fetchData() {
  await musicStore.fetchList()
}

function openUpload() {
  uploadForm.value = { title: '', artist: '', category: '', tags: '' }
  uploadFileList.value = []
  uploadFile.value = null
  showUpload.value = true
}

function handleFileChange(file) {
  uploadFile.value = file.raw
  if (!uploadForm.value.title) {
    uploadForm.value.title = file.name.replace(/\.[^.]+$/, '')
  }
}

async function handleUpload() {
  if (!uploadFile.value) { ElMessage.warning('请选择音乐文件'); return }
  if (!uploadForm.value.title) { ElMessage.warning('请输入标题'); return }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('title', uploadForm.value.title)
    formData.append('artist', uploadForm.value.artist || '')
    formData.append('category', uploadForm.value.category || '')
    formData.append('tags', uploadForm.value.tags || '')
    await musicStore.upload(formData)
    ElMessage.success('上传成功')
    showUpload.value = false
    fetchData()
  } catch {
    // 错误已由api拦截器处理
  } finally {
    uploading.value = false
  }
}

function openEdit(row) {
  editId.value = row.id
  editForm.value = {
    title: row.title || '',
    artist: row.artist || '',
    category: row.category || '',
    tags: row.tags || ''
  }
  showEdit.value = true
}

async function handleEditSubmit() {
  if (!editForm.value.title) { ElMessage.warning('请输入标题'); return }
  editing.value = true
  try {
    await musicStore.update(editId.value, {
      title: editForm.value.title,
      artist: editForm.value.artist || '',
      category: editForm.value.category || '',
      tags: editForm.value.tags || ''
    })
    ElMessage.success('保存成功')
    showEdit.value = false
    fetchData()
  } catch {
    // 错误已由api拦截器处理
  } finally {
    editing.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '提示', { type: 'warning' })
    await musicStore.remove(row.id)
    if (String(player.bgmChoiceId) === String(row.id)) player.setBackground(null, false)
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // 用户取消
  }
}

function formatSize(bytes) {
  if (bytes == null) return '-'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDuration(sec) {
  if (sec == null || isNaN(sec)) return '-'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
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

.manage-pane :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: var(--ls-line);
  --el-table-header-text-color: var(--ls-text-2);
  --el-table-text-color: var(--ls-text);
}
</style>
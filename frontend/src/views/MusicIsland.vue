<template>
  <div class="island-page">
    <!-- 顶栏 -->
    <header class="island-header">
      <div class="header-left">
        <span class="back-btn" @click="router.push('/home')">← 返回</span>
        <span class="island-title">🎵 音乐岛</span>
      </div>
      <div class="header-right">
        <el-input v-model="searchQuery" placeholder="搜索音乐" clearable @clear="fetchData" @keyup.enter="fetchData" style="width: 200px">
          <template #append>
            <el-button :icon="Search" @click="fetchData" />
          </template>
        </el-input>
        <el-button type="primary" @click="showUpload = true">上传音乐</el-button>
      </div>
    </header>

    <!-- 音乐列表 -->
    <main class="content-table">
      <el-table :data="musicStore.list" v-loading="musicStore.loading" stripe style="width: 100%">
        <el-table-column prop="title" label="名称" min-width="150" />
        <el-table-column prop="file_path" label="线上地址" min-width="200">
          <template #default="{ row }">
            <a :href="`/uploads${row.file_path}`" target="_blank" class="file-link">{{ row.file_path }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="标签" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="downloadFile(row.file_path)">下载</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <div v-if="!musicStore.loading && musicStore.list.length === 0" class="empty-placeholder">
        <div class="empty-icon">🎵</div>
        <div class="empty-text">暂无音乐，点击上传添加</div>
      </div>
    </main>

    <!-- 分页 -->
    <div class="pagination-wrap" v-if="musicStore.total > musicStore.size">
      <el-pagination
        v-model:current-page="musicStore.page"
        :page-size="musicStore.size"
        :total="musicStore.total"
        layout="prev, pager, next"
        @current-change="fetchData"
      />
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="showUpload" title="上传音乐" width="500px">
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
        <el-form-item label="标题">
          <el-input v-model="uploadForm.title" placeholder="音乐标题" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="uploadForm.category" placeholder="分类" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="uploadForm.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMusicStore } from '@/stores/music'

const router = useRouter()
const musicStore = useMusicStore()
const searchQuery = ref('')
const showUpload = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)
const uploadFileList = ref([])
const uploadForm = ref({ title: '', category: '', tags: '' })
const uploadFile = ref(null)

onMounted(() => {
  fetchData()
})

async function fetchData() {
  await musicStore.fetchList({ q: searchQuery.value })
}

function handleFileChange(file) {
  uploadFile.value = file.raw
  if (!uploadForm.value.title) {
    uploadForm.value.title = file.name.replace(/\.[^.]+$/, '')
  }
}

async function handleUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择音乐文件')
    return
  }
  if (!uploadForm.value.title) {
    ElMessage.warning('请输入标题')
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('title', uploadForm.value.title)
    formData.append('category', uploadForm.value.category || '')
    formData.append('tags', uploadForm.value.tags || '')
    await musicStore.upload(formData)
    ElMessage.success('上传成功')
    showUpload.value = false
    uploadForm.value = { title: '', category: '', tags: '' }
    uploadFileList.value = []
    uploadFile.value = null
    fetchData()
  } catch {
    // 错误已由api拦截器处理
  } finally {
    uploading.value = false
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除这首音乐吗？', '提示', { type: 'warning' })
    await musicStore.remove(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // 用户取消
  }
}

function downloadFile(filePath) {
  window.open(`/uploads${filePath}`, '_blank')
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.island-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #F5F0FF 0%, #EDE8F7 100%);
  padding-bottom: 40px;
}

.island-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  background: rgba(155, 141, 201, 0.15);
  border-bottom: 1px solid rgba(155, 141, 201, 0.3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-btn {
  color: var(--color-music);
  cursor: pointer;
  font-size: 14px;
}

.back-btn:hover {
  color: #7A6BA9;
}

.island-title {
  font-family: var(--font-serif);
  font-size: 20px;
  color: var(--color-text);
}

.header-right {
  display: flex;
  gap: 15px;
}

.content-table {
  padding: 30px 40px;
}

.content-table .file-link {
  color: var(--color-accent);
  text-decoration: none;
  word-break: break-all;
}

.content-table .file-link:hover {
  text-decoration: underline;
}

.loading-placeholder,
.empty-placeholder {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 15px;
}

.content-card {
  background: rgba(45, 90, 107, 0.6);
  border: 1px solid rgba(78, 205, 196, 0.2);
  border-radius: var(--radius);
  padding: 15px;
  transition: all 0.3s;
}

.content-card:hover {
  border-color: var(--color-accent);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}

.card-cover {
  width: 100%;
  height: 140px;
  background: rgba(26, 58, 74, 0.8);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  overflow: hidden;
}

.cover-placeholder {
  font-size: 48px;
}

.card-title {
  font-size: 16px;
  color: var(--color-text);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.card-size {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 10px;
}

.card-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: 20px;
}

@media (max-width: 768px) {
  .island-header {
    flex-direction: column;
    gap: 15px;
    padding: 15px 20px;
  }

  .header-right {
    width: 100%;
    flex-direction: column;
  }

  .content-table {
    padding: 20px;
  }
}
</style>
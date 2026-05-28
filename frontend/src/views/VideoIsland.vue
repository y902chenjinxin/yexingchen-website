<template>
  <div class="island-page">
    <header class="island-header">
      <div class="header-left">
        <span class="back-btn" @click="router.push('/home')">← 返回</span>
        <span class="island-title">🎬 视频岛</span>
      </div>
      <div class="header-right">
        <el-input v-model="searchQuery" placeholder="搜索视频" clearable @clear="fetchData" @keyup.enter="fetchData" style="width: 200px">
          <template #append><el-button :icon="Search" @click="fetchData" /></template>
        </el-input>
        <el-button type="primary" @click="showUpload = true">上传视频</el-button>
      </div>
    </header>

    <main class="content-table">
      <el-table :data="videoStore.list" v-loading="videoStore.loading" stripe style="width: 100%">
        <el-table-column prop="title" label="名称" min-width="150" />
        <el-table-column prop="cos_url" label="线上地址" min-width="200">
          <template #default="{ row }">
            <a v-if="row.cos_url" :href="row.cos_url" target="_blank" class="file-link">{{ row.cos_url }}</a>
            <span v-else>-</span>
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
            <el-button size="small" @click="copyUrl(row.cos_url)">复制链接</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!videoStore.loading && videoStore.list.length === 0" class="empty-placeholder">
        <div class="empty-icon">🎬</div>
        <div class="empty-text">暂无视频，点击上传添加</div>
      </div>
    </main>

    <div class="pagination-wrap" v-if="videoStore.total > videoStore.size">
      <el-pagination v-model:current-page="videoStore.page" :page-size="videoStore.size" :total="videoStore.total" layout="prev, pager, next" @current-change="fetchData" />
    </div>

    <el-dialog v-model="showUpload" title="上传视频" width="500px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="视频文件">
          <el-upload ref="uploadRef" :auto-upload="false" :limit="1" accept=".mp4,.webm" :file-list="uploadFileList" @change="handleFileChange">
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="封面图片">
          <el-upload ref="coverRef" :auto-upload="false" :limit="1" accept=".jpg,.jpeg,.png,.webp" :file-list="coverFileList" @change="handleCoverChange">
            <el-button>选择封面（可选）</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="标题"><el-input v-model="uploadForm.title" placeholder="视频标题" /></el-form-item>
        <el-form-item label="COS链接"><el-input v-model="uploadForm.cos_url" placeholder="腾讯COS链接（可选）" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="uploadForm.category" placeholder="分类" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="uploadForm.tags" placeholder="多个标签用逗号分隔" /></el-form-item>
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
import { ElMessage, ElMessageBox, ElLink } from 'element-plus'
import { useVideoStore } from '@/stores/video'

const router = useRouter()
const videoStore = useVideoStore()
const searchQuery = ref('')
const showUpload = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)
const coverRef = ref(null)
const uploadFileList = ref([])
const coverFileList = ref([])
const uploadFile = ref(null)
const coverFile = ref(null)
const uploadForm = ref({ title: '', cos_url: '', category: '', tags: '' })

onMounted(() => { fetchData() })

async function fetchData() {
  await videoStore.fetchList({ q: searchQuery.value })
}

function handleFileChange(file) {
  uploadFile.value = file.raw
  if (!uploadForm.value.title) {
    uploadForm.value.title = file.name.replace(/\.[^.]+$/, '')
  }
}

function handleCoverChange(file) {
  coverFile.value = file.raw
}

async function handleUpload() {
  if (!uploadFile.value) { ElMessage.warning('请选择视频文件'); return }
  if (!uploadForm.value.title) { ElMessage.warning('请输入标题'); return }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('title', uploadForm.value.title)
    formData.append('cos_url', uploadForm.value.cos_url || '')
    formData.append('category', uploadForm.value.category || '')
    formData.append('tags', uploadForm.value.tags || '')
    if (coverFile.value) formData.append('cover', coverFile.value)
    await videoStore.upload(formData)
    ElMessage.success('上传成功')
    showUpload.value = false
    uploadForm.value = { title: '', cos_url: '', category: '', tags: '' }
    uploadFileList.value = []
    coverFileList.value = []
    uploadFile.value = null
    coverFile.value = null
    fetchData()
  } catch { /* 错误已由api拦截器处理 */ }
  finally { uploading.value = false }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除这个视频吗？', '提示', { type: 'warning' })
    await videoStore.remove(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch { /* 用户取消 */ }
}

function copyUrl(url) {
  if (!url) return
  navigator.clipboard.writeText(url).then(() => {
    ElMessage.success('链接已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.island-page { min-height: 100vh; background: linear-gradient(180deg, #1A1A2E 0%, #141B2D 100%); padding-bottom: 40px; }
.island-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: rgba(26, 58, 74, 0.6); border-bottom: 1px solid rgba(78, 205, 196, 0.2); }
.header-left { display: flex; align-items: center; gap: 20px; }
.back-btn { color: var(--color-accent); cursor: pointer; font-size: 14px; }
.back-btn:hover { color: #fff; }
.island-title { font-family: var(--font-serif); font-size: 20px; color: #E8F4FC; }
.header-right { display: flex; gap: 15px; }
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

.loading-placeholder, .empty-placeholder { grid-column: 1 / -1; text-align: center; padding: 60px; color: var(--color-text-secondary); }
.empty-icon { font-size: 60px; margin-bottom: 15px; }
.content-card { background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(167, 139, 201, 0.3); border-radius: var(--radius); padding: 15px; transition: all 0.3s; }
.content-card:hover { border-color: var(--color-video); transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
.card-cover { width: 100%; height: 140px; background: rgba(167, 139, 201, 0.2); border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-bottom: 12px; overflow: hidden; }
.cover-img { width: 100%; height: 100%; object-fit: cover; }
.cover-placeholder { font-size: 48px; }
.card-title { font-size: 16px; color: var(--color-text); margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.card-size { font-size: 12px; color: var(--color-text-secondary); }
.card-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
.card-cos { margin-bottom: 8px; }
.card-actions { display: flex; gap: 10px; justify-content: flex-end; }
.pagination-wrap { display: flex; justify-content: center; padding: 20px; }
@media (max-width: 768px) {
  .island-header { flex-direction: column; gap: 15px; padding: 15px 20px; }
  .header-right { width: 100%; flex-direction: column; }
  .content-table { padding: 20px; }
}
</style>
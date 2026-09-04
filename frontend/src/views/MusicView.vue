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
      <div class="manage-toolbar">
        <el-input v-model="keyword" size="small" clearable placeholder="搜索标题/作者" style="width: 260px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" size="small" plain @click="doSearch">查询</el-button>
        <span v-if="keyword" class="search-count">匹配 {{ musicStore.list.length }} 条</span>
        <el-button v-if="keyword" size="small" plain @click="keyword = ''">清空筛选</el-button>
        <el-button v-if="selectedRows.length" type="danger" size="small" @click="handleBatchDelete">批量删除（{{ selectedRows.length }}）</el-button>
      </div>
      <el-table ref="tableRef" :data="pagedRows" v-loading="musicStore.loading" stripe style="width: 100%" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="48" :selectable="(row) => Number(row.is_default) !== 1" />
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
      <div v-else-if="!musicStore.loading" class="pager-wrap">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="musicStore.list.length"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :current-page="page"
          @size-change="onSizeChange"
          @current-change="onPageChange"
        />
      </div>
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

    <!-- 删除确认（管理页内） -->
    <el-dialog v-model="showDelete" title="删除确认" width="360px" append-to-body>
      <p>确定删除「{{ deleteName }}」吗？</p>
      <template #footer>
        <el-button @click="showDelete = false">取消</el-button>
        <el-button type="danger" :loading="deleting" @click="confirmDelete">删除</el-button>
      </template>
    </el-dialog>

    <!-- 批量删除确认（管理页内） -->
    <el-dialog v-model="showBatchDelete" title="批量删除" width="360px" append-to-body>
      <p>确定删除选中的 <b>{{ selectedRows.length }}</b> 项吗？此操作不可恢复。</p>
      <template #footer>
        <el-button @click="showBatchDelete = false">取消</el-button>
        <el-button type="danger" :loading="batchDeleting" @click="confirmBatchDelete">一键删除</el-button>
      </template>
    </el-dialog>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import MusicInner from './islands/MusicIslandInner.vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useMusicStore } from '@/stores/music'
import { usePlayerStore } from '@/stores/player'

const musicStore = useMusicStore()
const player = usePlayerStore()

const manage = ref(false)
const showUpload = ref(false)
const keyword = ref('')
const uploading = ref(false)
const uploadRef = ref(null)
const uploadFileList = ref([])
const uploadFile = ref(null)
const uploadForm = ref({ title: '', artist: '', category: '', tags: '' })

/* ---- 管理分页（客户端，默认10条） ---- */
const page = ref(1)
const pageSize = ref(10)
const pagedRows = computed(() =>
  musicStore.list.slice((page.value - 1) * pageSize.value, page.value * pageSize.value)
)
function onSizeChange(sz) { pageSize.value = sz; page.value = 1 }
function onPageChange(p) { page.value = p }

const showEdit = ref(false)
const editing = ref(false)
const editId = ref(null)
const editForm = ref({ title: '', artist: '', category: '', tags: '' })

onMounted(() => {
  fetchData()
})

async function fetchData() {
  const params = keyword.value ? { q: keyword.value } : {}
  await musicStore.fetchList(params)
}

function doSearch() {
  musicStore.page = 1
  page.value = 1
  fetchData()
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

const showDelete = ref(false)
const deleting = ref(false)
const deleteId = ref(null)
const deleteName = ref('')

function handleDelete(row) {
  deleteId.value = row.id
  deleteName.value = row.title || ''
  showDelete.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    await musicStore.remove(deleteId.value)
    if (String(player.bgmChoiceId) === String(deleteId.value)) player.setBackground(null, false)
    ElMessage.success('删除成功')
    showDelete.value = false
    fetchData()
  } catch {
    // 错误已由api拦截器处理
  } finally {
    deleting.value = false
  }
}

/* ---- 批量删除 ---- */
const tableRef = ref(null)
const selectedRows = ref([])
const showBatchDelete = ref(false)
const batchDeleting = ref(false)

function onSelectionChange(rows) {
  selectedRows.value = rows
}
function handleBatchDelete() {
  if (!selectedRows.value.length) return
  showBatchDelete.value = true
}
async function confirmBatchDelete() {
  const ids = selectedRows.value.map(r => r.id)
  if (!ids.length) return
  batchDeleting.value = true
  try {
    const hitBgm = ids.some(id => String(player.bgmChoiceId) === String(id))
    for (const id of ids) {
      await musicStore.remove(id)
    }
    if (hitBgm) player.setBackground(null, false)
    ElMessage.success(`已删除 ${ids.length} 项`)
    showBatchDelete.value = false
    tableRef.value?.clearSelection()
    fetchData()
  } catch {
    // 错误已由api拦截器处理
  } finally {
    batchDeleting.value = false
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

.manage-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.manage-toolbar :deep(.el-input__wrapper) {
  background: var(--ls-paper-2);
  box-shadow: inset 0 0 0 1px var(--ls-line);
}

.search-count {
  color: var(--ls-text-3);
  font-size: 13px;
}

.empty {
  text-align: center;
  padding: 40px;
  color: var(--ls-text-3);
  font-size: 14px;
}

.pager-wrap { display: flex; justify-content: flex-end; margin-top: 18px; }
.pager-wrap :deep(.el-pagination) { --el-pagination-bg-color: transparent; }

.manage-pane :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: var(--ls-line);
  --el-table-header-text-color: var(--ls-text-2);
  --el-table-text-color: var(--ls-text);
}
</style>
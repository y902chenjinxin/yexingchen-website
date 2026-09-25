<template>
  <IslandInnerBase type="novel" title="小说" subtitle="书卷悠长">
    <template #toolbar>
      <el-button type="primary" size="small" @click="openUpload">上传小说</el-button>
      <el-button size="small" plain @click="openBatch">批量导入</el-button>
    </template>

    <div class="manage-pane">
      <div class="manage-toolbar">
        <el-input v-model="keyword" size="small" clearable placeholder="搜索标题/作者" style="width: 260px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" size="small" plain @click="doSearch">查询</el-button>
        <span v-if="keyword" class="search-count">匹配 {{ novelStore.list.length }} 条</span>
        <el-button v-if="keyword" size="small" plain @click="keyword = ''">清空筛选</el-button>
        <el-button type="danger" plain size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
          批量删除<span v-if="selectedRows.length">（{{ selectedRows.length }}）</span>
        </el-button>
      </div>
      <!-- 加载中：鎏金光扫骨架行，替代默认旋转圈 -->
      <div v-if="novelStore.loading" class="sk-skeleton-rows">
        <SkeletonBlock v-for="i in 6" :key="i" width="100%" height="42px" style="margin-bottom: 8px;" />
      </div>
      <el-table ref="tableRef" :data="pagedRows" stripe class="admin-table" style="width: 100%" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column prop="author" label="作者" width="110" />
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" min-width="120" show-overflow-tooltip />
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-if="!novelStore.loading && novelStore.list.length === 0"
        tone="data"
        title="还没有添加小说"
        description="把读过的章节粘贴进来，系统帮你管理进度、收藏句子、生成摘要"
        action-label="↑ 上传小说"
        @action="openUpload"
      />
      <div v-else-if="!novelStore.loading" class="pager-wrap">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="novelStore.list.length"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :current-page="page"
          @size-change="onSizeChange"
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="showUpload" title="上传小说" width="500px" append-to-body>
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="小说文件">
          <el-upload ref="uploadRef" :auto-upload="false" :limit="1" accept=".epub,.pdf,.txt" :file-list="uploadFileList" @change="handleFileChange">
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="封面图片">
          <el-upload ref="coverRef" :auto-upload="false" :limit="1" accept=".jpg,.jpeg,.png,.webp" :file-list="coverFileList" @change="handleCoverChange">
            <el-button>选择封面（可选）</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="标题"><el-input v-model="uploadForm.title" placeholder="小说标题" /></el-form-item>
        <el-form-item label="作者"><el-input v-model="uploadForm.author" placeholder="作者" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="uploadForm.category" placeholder="分类" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="uploadForm.tags" placeholder="多个标签用逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showEdit" title="编辑小说" width="460px" append-to-body>
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="标题"><el-input v-model="editForm.title" placeholder="小说标题" /></el-form-item>
        <el-form-item label="作者"><el-input v-model="editForm.author" placeholder="作者" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="editForm.category" placeholder="分类" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="editForm.tags" placeholder="多个标签用逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleEditSubmit">保存</el-button>
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

    <!-- 批量导入弹窗 -->
    <el-dialog
      v-model="showBatch"
      title="批量导入小说"
      width="640px"
      append-to-body
      @open="preventDialogDrop"
    >
      <div class="batch-tip">
        <span>支持一次选择多个 EPUB / PDF / TXT 文件，单个文件 ≤ 100 MB；可选择对应封面（按文件名同序）。</span>
        <el-link type="primary" :underline="false" @click="onDownloadTemplate">下载 CSV 导入模板</el-link>
      </div>

      <el-form :model="batchForm" label-width="80px" class="batch-form">
        <el-form-item label="批量作者">
          <el-input v-model="batchForm.author" placeholder="应用到所有文件（可选）" clearable />
        </el-form-item>
        <el-form-item label="批量分类">
          <el-input v-model="batchForm.category" placeholder="应用到所有文件（可选）" clearable />
        </el-form-item>
        <el-form-item label="批量标签">
          <el-input v-model="batchForm.tags" placeholder="应用到所有文件，多个用逗号分隔（可选）" clearable />
        </el-form-item>
        <el-form-item label="标题规则">
          <el-radio-group v-model="batchForm.titleMode">
            <el-radio-button value="filename">文件名（去后缀）</el-radio-button>
            <el-radio-button value="filename-author">文件名 - 批量作者</el-radio-button>
            <el-radio-button value="custom">自定义（下方逐条编辑）</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-upload
        ref="batchUploadRef"
        :auto-upload="false"
        :multiple="true"
        :limit="30"
        accept=".epub,.pdf,.txt"
        :file-list="batchFileList"
        :on-change="handleBatchFileChange"
        :on-remove="handleBatchFileRemove"
        drag
        class="batch-upload"
      >
        <div class="batch-drop">
          <div class="batch-drop-icon">📚</div>
          <div class="batch-drop-text">拖拽文件到这里，或<em>点击选择</em></div>
          <div class="batch-drop-hint">EPUB / PDF / TXT，单次最多 30 个</div>
        </div>
      </el-upload>

      <!-- 可选封面：可对每条单独附加，或在表中点击「选择封面」 -->
      <div v-if="batchItems.length" class="batch-table-wrap">
        <el-table :data="batchItems" size="small" max-height="240" empty-text="还没有文件">
          <el-table-column label="#" width="46" type="index" />
          <el-table-column label="文件名" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ row.filename }}</template>
          </el-table-column>
          <el-table-column label="标题" min-width="200">
            <template #default="{ row }">
              <el-input
                v-if="batchForm.titleMode === 'custom'"
                v-model="row.title"
                size="small"
                placeholder="必填"
              />
              <span v-else class="batch-auto-title">{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column label="作者" width="100">
            <template #default="{ row }">{{ row.author || '—' }}</template>
          </el-table-column>
          <el-table-column label="封面" width="120">
            <template #default="{ row }">
              <span v-if="row.coverName" class="batch-cover-name" :title="row.coverName">{{ row.coverName }}</span>
              <el-upload
                v-else
                :show-file-list="false"
                :auto-upload="false"
                accept=".jpg,.jpeg,.png,.webp"
                :on-change="(file) => handleBatchCoverChange(row, file)"
                class="batch-cover-pick"
              >
                <el-button size="small" plain>选择封面</el-button>
              </el-upload>
              <el-button v-if="row.coverName" size="small" link type="danger" @click="removeBatchCover(row)">移除</el-button>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="80">
            <template #default="{ row }">{{ formatSize(row.size) }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div v-if="batchResult" class="batch-result">
        <div class="batch-result-summary">
          <span class="status-dot is-gold">成功 {{ batchResult.success }} 条</span>
          <span v-if="batchResult.failed" class="status-dot is-danger">失败 {{ batchResult.failed }} 条</span>
        </div>
        <el-table
          v-if="batchResult.results && batchResult.results.length"
          :data="batchResult.results"
          size="small"
          max-height="180"
          class="batch-result-table"
        >
          <el-table-column prop="filename" label="文件" min-width="160" show-overflow-tooltip />
          <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
          <el-table-column label="状态" width="84">
            <template #default="{ row }">
              <el-tag v-if="row.ok" size="small" type="success">成功</el-tag>
              <el-tag v-else size="small" type="danger">失败</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error" label="原因" min-width="160" show-overflow-tooltip />
        </el-table>
      </div>

      <template #footer>
        <el-button @click="showBatch = false" :disabled="batchUploading">取消</el-button>
        <el-button
          type="primary"
          :loading="batchUploading"
          :disabled="!batchItems.length"
          @click="submitBatch"
        >
          {{ batchUploading ? '导入中…' : `开始批量导入（${batchItems.length}）` }}
        </el-button>
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
import { onMounted, ref, computed, watch, nextTick } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import EmptyState from '@/components/EmptyState.vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useNovelStore } from '@/stores/novel'
import SkeletonBlock from '@/components/common/SkeletonBlock.vue'
import { downloadNovelTemplate } from '@/api/novel'

const novelStore = useNovelStore()

const showUpload = ref(false)
const keyword = ref('')
const uploading = ref(false)
const uploadRef = ref(null)
const coverRef = ref(null)
const uploadFileList = ref([])
const coverFileList = ref([])
const uploadFile = ref(null)
const coverFile = ref(null)
const uploadForm = ref({ title: '', author: '', category: '', tags: '' })

/* ---- 管理分页（客户端，默认10条） ---- */
const page = ref(1)
const pageSize = ref(10)
const pagedRows = computed(() =>
  novelStore.list.slice((page.value - 1) * pageSize.value, page.value * pageSize.value)
)
function onSizeChange(sz) { pageSize.value = sz; page.value = 1 }
function onPageChange(p) { page.value = p }

const showEdit = ref(false)
const saving = ref(false)
const editId = ref(null)
const editForm = ref({ title: '', author: '', category: '', tags: '' })

/* ========== 批量导入 ========== */
const showBatch = ref(false)
const batchUploading = ref(false)
const batchUploadRef = ref(null)
const batchFileList = ref([])
const batchItems = ref([])
const batchForm = ref({
  author: '',
  category: '',
  tags: '',
  titleMode: 'filename', // filename | filename-author | custom
})
const batchResult = ref(null)

function openBatch() {
  batchFileList.value = []
  batchItems.value = []
  batchForm.value = { author: '', category: '', tags: '', titleMode: 'filename' }
  batchResult.value = null
  showBatch.value = true
}

// 阻止浏览器默认行为：拖拽到 dialog 时不会"打开"文件
function preventDialogDrop() {
  nextTick(() => {
    const root = document.querySelector('.el-dialog__wrapper')
    if (!root) return
    const stop = (e) => {
      e.preventDefault()
      e.stopPropagation()
    }
    root.addEventListener('dragover', stop)
    root.addEventListener('drop', stop)
  })
}

function handleBatchFileChange(file) {
  if (!file || !file.raw) return
  const raw = file.raw
  if (batchItems.value.some((it) => it.filename === raw.name && it.size === raw.size)) return
  batchItems.value.push({
    raw,
    filename: raw.name,
    size: raw.size,
    title: raw.name.replace(/\.[^.]+$/, ''),
    author: batchForm.value.author || '',
    category: batchForm.value.category || '',
    tags: batchForm.value.tags || '',
    coverRaw: null,
    coverName: '',
  })
  applyBatchTitleMode()
}

function handleBatchFileRemove(file) {
  if (!file || !file.raw) return
  const raw = file.raw
  batchItems.value = batchItems.value.filter(
    (it) => !(it.filename === raw.name && it.size === raw.size),
  )
}

function handleBatchCoverChange(row, file) {
  if (!file || !file.raw) return
  row.coverRaw = file.raw
  row.coverName = file.raw.name
}

function removeBatchCover(row) {
  row.coverRaw = null
  row.coverName = ''
}

watch(
  () => [batchForm.value.titleMode, batchForm.value.author],
  () => applyBatchTitleMode(),
)

function applyBatchTitleMode() {
  const mode = batchForm.value.titleMode
  const commonAuthor = batchForm.value.author || ''
  for (const it of batchItems.value) {
    if (mode === 'filename') {
      it.title = it.filename.replace(/\.[^.]+$/, '')
    } else if (mode === 'filename-author') {
      const base = it.filename.replace(/\.[^.]+$/, '')
      it.title = commonAuthor ? `${base} - ${commonAuthor}` : base
    } else {
      if (!it.title) it.title = it.filename.replace(/\.[^.]+$/, '')
    }
    it.author = commonAuthor
    it.category = batchForm.value.category || ''
    it.tags = batchForm.value.tags || ''
  }
}

async function submitBatch() {
  if (!batchItems.value.length) return
  if (batchForm.value.titleMode === 'custom') {
    const empty = batchItems.value.filter((it) => !it.title || !it.title.trim())
    if (empty.length) {
      ElMessage.warning(`有 ${empty.length} 个文件未填写标题，请补齐后再导入`)
      return
    }
  }
  batchUploading.value = true
  batchResult.value = null
  try {
    const files = batchItems.value.map((it) => it.raw)
    const items = batchItems.value.map((it) => ({
      title: it.title || it.filename.replace(/\.[^.]+$/, ''),
      author: batchForm.value.author || '',
      category: batchForm.value.category || '',
      tags: batchForm.value.tags || '',
    }))
    const covers = batchItems.value.map((it) => it.coverRaw || null)
    const res = await novelStore.batchUpload({ files, items, covers })
    const data = res?.data || {}
    batchResult.value = {
      success: data.success || 0,
      failed: data.failed || 0,
      total: data.total || files.length,
      results: data.results || [],
    }
    if (data.success) {
      ElMessage.success(`批量导入完成：成功 ${data.success}` + (data.failed ? `，失败 ${data.failed}` : ''))
      fetchData()
      if (!data.failed) {
        batchFileList.value = []
        batchItems.value = []
      }
    } else {
      ElMessage.warning('批量导入未成功，请检查文件或网络')
    }
  } catch (e) {
    const msg = e?.msg || e?.detail?.msg || e?.message || '批量导入失败，请稍后重试'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    console.error('[novel batchUpload] failed:', e)
  } finally {
    batchUploading.value = false
  }
}

async function onDownloadTemplate() {
  try {
    await downloadNovelTemplate()
    ElMessage.success('模板已下载')
  } catch (e) {
    const msg = e?.msg || e?.detail?.msg || e?.message || '下载模板失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
}

onMounted(() => { fetchData() })

async function fetchData() {
  // size=200 一次性拉全（管理页用客户端分页）
  const params = keyword.value ? { q: keyword.value } : { size: 200 }
  await novelStore.fetchList(params)
}

function doSearch() {
  novelStore.page = 1
  fetchData()
}

function openUpload() {
  uploadForm.value = { title: '', author: '', category: '', tags: '' }
  uploadFileList.value = []
  coverFileList.value = []
  uploadFile.value = null
  coverFile.value = null
  showUpload.value = true
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
  if (!uploadFile.value) { ElMessage.warning('请选择小说文件'); return }
  if (!uploadForm.value.title) { ElMessage.warning('请输入标题'); return }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('title', uploadForm.value.title)
    formData.append('author', uploadForm.value.author || '')
    formData.append('category', uploadForm.value.category || '')
    formData.append('tags', uploadForm.value.tags || '')
    if (coverFile.value) formData.append('cover', coverFile.value)
    await novelStore.upload(formData)
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
    author: row.author || '',
    category: row.category || '',
    tags: row.tags || ''
  }
  showEdit.value = true
}

async function handleEditSubmit() {
  if (!editForm.value.title) { ElMessage.warning('请输入标题'); return }
  saving.value = true
  try {
    await novelStore.update(editId.value, {
      title: editForm.value.title,
      author: editForm.value.author || '',
      category: editForm.value.category || '',
      tags: editForm.value.tags || ''
    })
    ElMessage.success('保存成功')
    showEdit.value = false
    fetchData()
  } catch {
    // 错误已由api拦截器处理
  } finally {
    saving.value = false
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
    await novelStore.remove(deleteId.value)
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
    for (const id of ids) {
      await novelStore.remove(id)
    }
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

/* 骨架行：鎏金光扫效果，由 SkeletonBlock 自身 ::after 实现 */
.sk-skeleton-rows {
  padding: 4px 0 16px;
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

/* ========== 批量导入弹窗 ========== */
.batch-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 14px;
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.10));
  border: 1px solid var(--ls-line, rgba(127, 127, 127, 0.2));
  border-radius: 8px;
  color: var(--ls-text-2);
  font-size: 12.5px;
}
.batch-tip .el-link {
  font-size: 12.5px;
  margin-left: auto;
  white-space: nowrap;
}

.batch-form { margin-bottom: 8px; }
.batch-form :deep(.el-form-item) { margin-bottom: 12px; }

.batch-upload :deep(.el-upload) { width: 100%; }
.batch-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 22px 18px;
  background: var(--ls-paper-2, rgba(127, 127, 127, 0.04));
  border: 1.5px dashed var(--ls-line, rgba(127, 127, 127, 0.3));
  border-radius: 10px;
  transition: border-color .2s, background-color .2s, box-shadow .2s;
}
.batch-upload :deep(.el-upload-dragger:hover),
.batch-upload :deep(.el-upload.is-dragover .el-upload-dragger) {
  border-color: var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.08));
  box-shadow: 0 4px 16px var(--yq-gold-glow, rgba(199, 169, 107, 0.18));
}
.batch-drop { text-align: center; color: var(--ls-text-2); }
.batch-drop-icon { font-size: 28px; line-height: 1; margin-bottom: 6px; }
.batch-drop-text { font-size: 13px; }
.batch-drop-text em { color: var(--yq-gold, #c7a96b); font-style: normal; margin: 0 4px; }
.batch-drop-hint { font-size: 11.5px; color: var(--ls-text-3); margin-top: 4px; }

.batch-table-wrap {
  margin-top: 14px;
  border: 1px solid var(--ls-line, rgba(127, 127, 127, 0.2));
  border-radius: 8px;
  overflow: hidden;
}
.batch-table-wrap :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--ls-paper-2, rgba(127, 127, 127, 0.06));
  --el-table-border-color: var(--ls-line, rgba(127, 127, 127, 0.2));
  --el-table-text-color: var(--ls-text);
}
.batch-auto-title { color: var(--ls-text-2); font-size: 12.5px; }
.batch-cover-name {
  display: inline-block;
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--yq-gold, #c7a96b);
  font-size: 12.5px;
  vertical-align: middle;
}
.batch-cover-pick { display: inline-block; }

.batch-result {
  margin-top: 16px;
  padding: 12px;
  background: var(--ls-paper-2, rgba(127, 127, 127, 0.04));
  border: 1px solid var(--ls-line, rgba(127, 127, 127, 0.2));
  border-radius: 8px;
}
.batch-result-summary {
  display: flex;
  gap: 14px;
  margin-bottom: 8px;
  font-size: 12.5px;
}
.batch-result-table :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: var(--ls-line, rgba(127, 127, 127, 0.18));
}
</style>
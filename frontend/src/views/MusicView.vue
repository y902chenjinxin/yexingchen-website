<template>
  <IslandInnerBase type="music" title="音乐" subtitle="音律飘渺 · 曲库管理">
    <template #toolbar>
      <el-button type="primary" size="small" @click="openUpload">上传音乐</el-button>
    </template>

    <!-- 管理表格（默认进入即管理页） -->
    <div class="manage-pane">
      <!-- 工具条：搜索 / 筛选 / 批量 -->
      <div class="manage-toolbar">
        <div class="mt-left">
          <el-input
            v-model="keyword"
            size="small"
            clearable
            placeholder="搜索标题 / 作者 / 标签"
            class="mt-search"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" size="small" plain @click="doSearch">查询</el-button>
          <el-button v-if="keyword" size="small" plain @click="resetSearch">清空筛选</el-button>
          <span v-if="keyword" class="search-count">匹配 {{ musicStore.list.length }} 条</span>
        </div>
        <div class="mt-right">
          <span class="mt-count">共 {{ musicStore.list.length }} 首</span>
          <el-button
            type="danger"
            plain
            size="small"
            :disabled="!selectedRows.length"
            @click="handleBatchDelete"
          >
            批量删除<span v-if="selectedRows.length">（{{ selectedRows.length }}）</span>
          </el-button>
        </div>
      </div>

      <el-table
        ref="tableRef"
        :data="pagedRows"
        v-loading="musicStore.loading"
        stripe
        style="width: 100%"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="46" :selectable="(row) => Number(row.is_default) !== 1" />

        <!-- 标题：播放按钮内联，省一列 -->
        <el-table-column label="曲目" min-width="220">
          <template #default="{ row }">
            <div class="cell-title">
              <button
                class="mini-btn play-btn"
                :class="{ playing: isCurPlaying(row) }"
                :title="isCurPlaying(row) ? '暂停' : '播放'"
                @click="handlePlay(row)"
              >{{ isCurPlaying(row) ? '❚❚' : '▶' }}</button>
              <span class="tt">{{ row.title || '未知曲目' }}</span>
              <el-tag v-if="Number(row.is_default) === 1" size="small" type="warning">内置</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="artist" label="作者" width="116" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="96">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.tags">{{ row.tags }}</span>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="86">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="时长" width="72">
          <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
        </el-table-column>

        <!-- 操作：设为默认（背景乐） / 编辑 / 删除 —— 左对齐排布，保证各行按钮纵向对齐 -->
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="row-ops">
              <el-tag v-if="isCurBgm(row)" size="small" type="primary" effect="dark" class="bgm-on">默认中</el-tag>
              <el-button v-else size="small" @click="setAsBg(row)">设为默认</el-button>

              <template v-if="Number(row.is_default) !== 1">
                <el-button size="small" type="primary" plain @click="openEdit(row)">编辑</el-button>
                <el-button size="small" type="danger" plain @click="handleDelete(row)">删除</el-button>
              </template>
            </div>
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

    <el-dialog v-model="showDelete" title="删除确认" width="360px" append-to-body>
      <p>确定删除「{{ deleteName }}」吗？</p>
      <template #footer>
        <el-button @click="showDelete = false">取消</el-button>
        <el-button type="danger" :loading="deleting" @click="confirmDelete">删除</el-button>
      </template>
    </el-dialog>

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
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useMusicStore } from '@/stores/music'
import { usePlayerStore } from '@/stores/player'
import { useBgmLibraryStore } from '@/stores/bgmLibrary'

const musicStore = useMusicStore()
const player = usePlayerStore()
const bgm = useBgmLibraryStore()

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

function resetSearch() {
  keyword.value = ''
  doSearch()
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
    if (String(bgm.bgmChoiceId) === String(deleteId.value)) bgm.setBackground(null, false)
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

/* ---- 播放 / 背景乐 ---- */
function handlePlay(item) {
  player.playItem(item)
}
function setAsBg(item) {
  bgm.setBackground(item, true)
}
function isCurBgm(item) { return String(item.id) === String(bgm.bgmChoiceId) }
function isCurPlaying(item) {
  return player.curItem && String(player.curItem.id) === String(item.id) && player.isPlaying
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
</script>

<style scoped>
.manage-pane {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 18px 20px;
  box-shadow: var(--dp-shadow);
}

/* 工具条：左右两端分布，中间自动留白 */
.manage-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.mt-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}
.mt-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.mt-search { width: 240px; }
.mt-count {
  font-size: 12px;
  color: var(--dp-text3);
  font-variant-numeric: tabular-nums;
}
.search-count {
  font-size: 12px;
  color: var(--dp-text3);
}
.dim { color: var(--dp-text3); font-size: 12px; }

/* 标题单元格：播放按钮 + 标题 + 内置标签 */
.cell-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.cell-title .tt {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: var(--dp-text);
}

/* 表格：透明底 + 发丝线，列多时可横向滚动 */
.manage-pane :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: var(--dp-line);
  --el-table-header-text-color: var(--dp-text2);
  --el-table-text-color: var(--dp-text);
}
.manage-pane :deep(.el-table th.el-table__cell) {
  background: var(--dp-surface2);
  font-weight: 550;
}

.empty {
  text-align: center;
  padding: 40px;
  color: var(--dp-text3);
  font-size: 13px;
}

.pager-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.pager-wrap :deep(.el-pagination) { --el-pagination-bg-color: transparent; }

/* 操作列：左对齐排列，各行按钮纵向对齐不散乱 */
/* 布局（flex/nowrap/gap/左对齐）由 desktop-product.css 的 `.el-table .row-ops` 统一提供；
   这里只保留乐库特有的：固定按钮宽度，避免「设为默认 / 默认中」宽度差异导致后续按钮错位 */
.row-ops :deep(.el-button) { min-width: 56px; margin-left: 0 !important; }
.row-ops .bgm-on { min-width: 56px; justify-content: center; }
.bgm-on { flex-shrink: 0; }

/* ---------- 行内播放圆按钮 ---------- */
.mini-btn {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border-radius: 50%;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  line-height: 1;
  transition: all .15s;
  background: transparent;
  color: var(--dp-text2);
  border: 1px solid var(--dp-line);
  padding: 0;
}
.mini-btn:hover {
  background: var(--dp-surface2);
  color: var(--dp-accent);
  border-color: var(--dp-accent);
}
.mini-btn.play-btn {
  background: var(--dp-accent-strong);
  color: #fff;
  border-color: var(--dp-accent-strong);
}
.mini-btn.play-btn:hover { background: var(--dp-accent); border-color: var(--dp-accent); }
.mini-btn.play-btn.playing {
  background: var(--dp-warning);
  border-color: var(--dp-warning);
  color: #241c00;
}
</style>
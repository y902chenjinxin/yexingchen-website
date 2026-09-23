<template>
  <IslandInnerBase type="music" title="音乐" subtitle="音律飘渺 · 曲库管理">
    <template #toolbar>
      <el-button type="primary" size="small" @click="openUpload">上传音乐</el-button>
      <el-button size="small" plain @click="openBatch">批量导入</el-button>
      <el-button size="small" plain @click="onDownloadTemplate">下载模板</el-button>
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
        :row-class-name="rowClassName"
        @selection-change="onSelectionChange"
        empty-text="暂无音乐，点上方「导入」添加"
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

      <EmptyState v-if="!musicStore.loading && musicStore.list.length === 0" size="sm" title="暂无歌曲" description="到管理后台上传音乐，或稍后刷新重试" />
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

    <!-- 批量导入弹窗 -->
    <el-dialog
      v-model="showBatch"
      title="批量导入音乐"
      width="640px"
      append-to-body
      @open="preventDialogDrop"
    >
      <div class="batch-tip">
        <span>支持一次选择多个 MP3 / FLAC / WAV 文件，单个文件 ≤ 50 MB。</span>
        <el-link type="primary" :underline="false" @click="onDownloadTemplate">下载 CSV 导入模板</el-link>
      </div>

      <el-form :model="batchForm" label-width="80px" class="batch-form">
        <el-form-item label="批量作者">
          <el-input v-model="batchForm.artist" placeholder="应用到所有文件（可选）" clearable />
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
            <el-radio-button value="filename-artist">文件名 - 批量作者</el-radio-button>
            <el-radio-button value="custom">自定义（下方逐条编辑）</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-upload
        ref="batchUploadRef"
        :auto-upload="false"
        :multiple="true"
        :limit="20"
        accept=".mp3,.flac,.wav"
        :file-list="batchFileList"
        :on-change="handleBatchFileChange"
        :on-remove="handleBatchFileRemove"
        drag
        class="batch-upload"
      >
        <div class="batch-drop">
          <div class="batch-drop-icon">📥</div>
          <div class="batch-drop-text">拖拽文件到这里，或<em>点击选择</em></div>
          <div class="batch-drop-hint">MP3 / FLAC / WAV，单次最多 20 个</div>
        </div>
      </el-upload>

      <div v-if="batchItems.length" class="batch-table-wrap">
        <el-table :data="batchItems" size="small" :show-header="true" max-height="220" empty-text="还没有文件">
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
            <template #default="{ row }">{{ row.artist || '—' }}</template>
          </el-table-column>
          <el-table-column label="大小" width="84">
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
import { onMounted, ref, computed, watch, nextTick } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import EmptyState from '@/components/EmptyState.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useIsMobile } from '@/composables/useIsMobile'
import { useMusicStore } from '@/stores/music'
import { usePlayerStore } from '@/stores/player'
import { useBgmLibraryStore } from '@/stores/bgmLibrary'
import { downloadMusicTemplate } from '@/api/music'

const isMobile = useIsMobile()
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

/* ---- 管理分页（客户端，默认10条；手机端已隐藏分页控件，故一次展示全量） ---- */
const page = ref(1)
const pageSize = ref(10)
const pagedRows = computed(() => {
  const size = isMobile.value ? Math.max(musicStore.list.length, 1) : pageSize.value
  const start = isMobile.value ? 0 : (page.value - 1) * size
  return musicStore.list.slice(start, start + size)
})
function onSizeChange(sz) { pageSize.value = sz; page.value = 1 }
function onPageChange(p) { page.value = p }

const showEdit = ref(false)
const editing = ref(false)
const editId = ref(null)
const editForm = ref({ title: '', artist: '', category: '', tags: '' })

/* ========== 批量导入 ========== */
const showBatch = ref(false)
const batchUploading = ref(false)
const batchUploadRef = ref(null)
const batchFileList = ref([]) // el-upload 内部 file-list（保留 raw 文件）
const batchItems = ref([])   // [{ raw: File, filename, size, title, artist, category, tags }]
const batchForm = ref({
  artist: '',
  category: '',
  tags: '',
  titleMode: 'filename', // filename | filename-artist | custom
})
const batchResult = ref(null) // { success, failed, total, results }

function openBatch() {
  batchFileList.value = []
  batchItems.value = []
  batchForm.value = { artist: '', category: '', tags: '', titleMode: 'filename' }
  batchResult.value = null
  showBatch.value = true
}

// 阻止浏览器默认行为：拖拽到 dialog 时不会"打开"文件
// Element Plus 的 el-upload drag 模式只接管了 .el-upload-dragger，
// 弹窗其他位置仍可能冒泡到 document，需要手动拦下来
function preventDialogDrop() {
  // 下一帧再绑（el-dialog 还没渲染好）
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
  // el-upload 多文件模式下每次 change 都会被调用，需要去重（已存在 raw 同名则跳过）
  if (!file || !file.raw) return
  const raw = file.raw
  if (batchItems.value.some((it) => it.filename === raw.name && it.size === raw.size)) return
  batchItems.value.push({
    raw,
    filename: raw.name,
    size: raw.size,
    title: raw.name.replace(/\.[^.]+$/, ''),
    artist: batchForm.value.artist || '',
    category: batchForm.value.category || '',
    tags: batchForm.value.tags || '',
  })
  applyBatchTitleMode() // 重新按当前模式刷新预览标题
}

function handleBatchFileRemove(file) {
  if (!file || !file.raw) return
  const raw = file.raw
  batchItems.value = batchItems.value.filter(
    (it) => !(it.filename === raw.name && it.size === raw.size),
  )
}

watch(
  () => [batchForm.value.titleMode, batchForm.value.artist],
  () => applyBatchTitleMode(),
)

// 按"标题规则"刷新每条预览标题；同时把批量字段同步到 item
function applyBatchTitleMode() {
  const mode = batchForm.value.titleMode
  const commonArtist = batchForm.value.artist || ''
  for (const it of batchItems.value) {
    if (mode === 'filename') {
      it.title = it.filename.replace(/\.[^.]+$/, '')
    } else if (mode === 'filename-artist') {
      const base = it.filename.replace(/\.[^.]+$/, '')
      it.title = commonArtist ? `${base} - ${commonArtist}` : base
    } else {
      // custom：保留用户已输入的标题，没有则用文件名兜底
      if (!it.title) it.title = it.filename.replace(/\.[^.]+$/, '')
    }
    it.artist = commonArtist
    it.category = batchForm.value.category || ''
    it.tags = batchForm.value.tags || ''
  }
}

async function submitBatch() {
  if (!batchItems.value.length) return
  // 校验：custom 模式下标题不能为空
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
      artist: batchForm.value.artist || '',
      category: batchForm.value.category || '',
      tags: batchForm.value.tags || '',
    }))
    const res = await musicStore.batchUpload({ files, items })
    const data = res?.data || {}
    batchResult.value = {
      success: data.success || 0,
      failed: data.failed || 0,
      total: data.total || files.length,
      results: data.results || [],
    }
    if (data.success) {
      ElMessage.success(`批量导入完成：成功 ${data.success}` + (data.failed ? `，失败 ${data.failed}` : ''))
      fetchData() // 刷新列表
      if (!data.failed) {
        // 全部成功后清空文件选择，便于继续
        batchFileList.value = []
        batchItems.value = []
      }
    } else {
      ElMessage.warning('批量导入未成功，请检查文件或网络')
    }
  } catch (e) {
    // 错误已由 axios 拦截器处理（仅 401 跳登录），但其他业务码/网络错需要在这里显式提示
    const msg = e?.msg || e?.detail?.msg || e?.message || '批量导入失败，请稍后重试'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    console.error('[music batchUpload] failed:', e)
  } finally {
    batchUploading.value = false
  }
}

async function onDownloadTemplate() {
  try {
    await downloadMusicTemplate()
    ElMessage.success('模板已下载')
  } catch (e) {
    // 错误已由 axios 拦截器处理
  }
}

onMounted(() => {
  fetchData()
})

async function fetchData() {
  // size=200 一次性拉全（管理页用客户端分页），避免后端默认 20 条导致列表截断
  const params = keyword.value ? { q: keyword.value } : { size: 200 }
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
  // 把当前可见列表作为播放队列，让上下首/模式在当前列表里循环
  player.playItem(item, musicStore.list)
}
function setAsBg(item) {
  bgm.setBackground(item, true)
}
function isCurBgm(item) { return String(item.id) === String(bgm.bgmChoiceId) }
function isCurPlaying(item) {
  return player.curItem && String(player.curItem.id) === String(item.id) && player.isPlaying
}

/* 行类名：当前点播 + 当前 BGM 高亮（视觉上一眼可见当前在听哪首） */
function rowClassName({ row }) {
  if (isCurPlaying(row)) return 'row-now-playing'
  if (isCurBgm(row) && player.mode === 'bgm') return 'row-bgm-active'
  return ''
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

/* ---------- 当前播放 / 当前 BGM 行高亮 ----------
 * 左侧 3px 强色条 + 淡色底，让用户在十几行里一眼看到当前在听哪首
 * 不依赖 el-table 默认的 stripe / hover，单独覆盖
 */
.manage-pane :deep(.el-table__row.row-now-playing > td),
.manage-pane :deep(.el-table__row.row-bgm-active > td) {
  background: rgba(61, 127, 214, 0.10) !important;
}
.manage-pane :deep(.el-table__row.row-now-playing > td:first-child) {
  box-shadow: inset 3px 0 0 var(--dp-accent-strong, #3d7fd6);
}
.manage-pane :deep(.el-table__row.row-bgm-active > td:first-child) {
  box-shadow: inset 3px 0 0 var(--dp-warning, #f59e0b);
}
/* hover 时不要把高亮行底色盖掉 */
.manage-pane :deep(.el-table__row.row-now-playing:hover > td),
.manage-pane :deep(.el-table__row.row-bgm-active:hover > td) {
  background: rgba(61, 127, 214, 0.18) !important;
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
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.2));
  border-radius: 8px;
  color: var(--dp-text2);
  font-size: 12.5px;
}
.batch-tip .el-link {
  font-size: 12.5px;
  margin-left: auto;
  white-space: nowrap;
}

.batch-form { margin-bottom: 8px; }
.batch-form :deep(.el-form-item) { margin-bottom: 12px; }

/* el-upload 拖拽区：鎏金边框 + 玻璃感 */
.batch-upload :deep(.el-upload) {
  width: 100%;
}
.batch-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 22px 18px;
  background: var(--dp-surface2, rgba(127, 127, 127, 0.04));
  border: 1.5px dashed var(--dp-line, rgba(127, 127, 127, 0.3));
  border-radius: 10px;
  transition: border-color .2s, background-color .2s, box-shadow .2s;
}
.batch-upload :deep(.el-upload-dragger:hover),
.batch-upload :deep(.el-upload.is-dragover .el-upload-dragger) {
  border-color: var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199, 169, 107, 0.08));
  box-shadow: 0 4px 16px var(--yq-gold-glow, rgba(199, 169, 107, 0.18));
}
.batch-drop { text-align: center; color: var(--dp-text2); }
.batch-drop-icon { font-size: 28px; line-height: 1; margin-bottom: 6px; }
.batch-drop-text { font-size: 13px; }
.batch-drop-text em { color: var(--yq-gold, #c7a96b); font-style: normal; margin: 0 4px; }
.batch-drop-hint { font-size: 11.5px; color: var(--dp-text3); margin-top: 4px; }

.batch-table-wrap {
  margin-top: 14px;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.2));
  border-radius: 8px;
  overflow: hidden;
}
.batch-table-wrap :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--dp-surface2, rgba(127, 127, 127, 0.06));
  --el-table-border-color: var(--dp-line, rgba(127, 127, 127, 0.2));
}
.batch-auto-title { color: var(--dp-text2); font-size: 12.5px; }

.batch-result {
  margin-top: 16px;
  padding: 12px;
  background: var(--dp-surface2, rgba(127, 127, 127, 0.04));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.2));
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
  --el-table-border-color: var(--dp-line, rgba(127, 127, 127, 0.18));
}
</style>
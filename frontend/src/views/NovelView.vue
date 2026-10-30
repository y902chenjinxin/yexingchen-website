<template>
  <IslandInnerBase type="novel" title="小说" subtitle="书卷悠长">
    <div class="manage-pane">
      <PageToolbar>
        <!-- v2.46.159：统一下拉/搜索组件（SearchField 内含查询按钮与清除） -->
        <SearchField v-model="keyword" placeholder="搜索标题/作者" width="260px" @search="doSearch" />
        <span v-if="keyword" class="search-count">匹配 {{ novelStore.list.length }} 条</span>
        <el-button v-if="keyword" size="small" plain @click="keyword = ''">清空筛选</el-button>
        <el-button type="danger" plain size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
          批量删除<span v-if="selectedRows.length">（{{ selectedRows.length }}）</span>
        </el-button>
        <template #actions>
          <IconButton icon="upload" label="上传小说" variant="primary" @click="openUpload" />
          <IconButton icon="folder" label="批量导入" @click="openBatch" />
        </template>
      </PageToolbar>
      <!-- 加载中：鎏金光扫骨架行，替代默认旋转圈 -->
      <div v-if="novelStore.loading" class="sk-skeleton-rows">
        <SkeletonBlock v-for="i in 6" :key="i" width="100%" height="42px" style="margin-bottom: 8px;" />
      </div>
      <!-- 手机端：书架（卡片网格 + 封面 + 进度）。桌面端仍走下面的表格。
           v2.46.209：夜星要「PC 列表 / 手机书架」，用触摸能力判断而不是宽度
           （本站手机浏览器 viewport 是 1280，max-width 媒体查询不触发）。 -->
      <div v-if="isTouch && !novelStore.loading && pagedRows.length" class="novel-shelf">
        <button
          v-for="n in pagedRows"
          :key="n.id"
          class="ns-card"
          type="button"
          @click="openReader(n)"
        >
          <div class="ns-cover" :style="coverStyle(n)">
            <img v-if="n.cover_url" :src="n.cover_url" :alt="n.title" loading="lazy" />
            <span v-else class="ns-initial">{{ (n.title || '书').slice(0, 1) }}</span>
            <span class="ns-prog" :style="{ width: progressOf(n) + '%' }" />
            <span
              class="ns-star"
              :class="{ on: Number(n.is_favorite) === 1 }"
              role="button"
              :aria-label="Number(n.is_favorite) === 1 ? '取消收藏' : '收藏'"
              @click.stop="toggleFav(n)"
            >
              <svg width="13" height="13" viewBox="0 0 24 24"
                   :fill="Number(n.is_favorite) === 1 ? 'currentColor' : 'none'"
                   stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
                <path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.6 9.7l5.8-.8L12 3.6Z" />
              </svg>
            </span>
          </div>
          <div class="ns-meta">
            <span class="ns-title">{{ n.title }}</span>
            <span class="ns-sub">{{ n.author || '未知作者' }}<template v-if="n.chapter_count"> · {{ n.chapter_count }} 章</template><template v-else-if="n.parse_status === 'pending'"> · 解析中</template></span>
            <span class="ns-pct">{{ progressOf(n) }}%</span>
          </div>
        </button>
      </div>

      <el-table v-if="!isTouch" ref="tableRef" :data="pagedRows" stripe class="admin-table" style="width: 100%" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column v-if="!isMobile" prop="author" label="作者" width="110" />
        <el-table-column v-if="!isMobile" prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="!isMobile" prop="tags" label="标签" min-width="120" show-overflow-tooltip />
        <el-table-column v-if="!isMobile" label="文件大小" width="130">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
            <el-tag v-if="row.parse_status === 'pending'" size="small" type="warning">解析中</el-tag>
            <el-tag v-else-if="row.parse_status === 'failed'" size="small" type="danger">解析失败</el-tag>
            <span v-else-if="row.chapter_count" class="nv-chaps">{{ row.chapter_count }} 章</span>
          </template>
        </el-table-column>
        <el-table-column v-if="!isMobile" label="上传时间" width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" :width="isMobile ? 132 : 100" fixed="right">
          <!-- v2.46.159：行内动作统一用 OpsCell -->
          <template #default="{ row }">
            <OpsCell :row="row" :actions="rowActions" />
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
          :total="total"
          :page-size="pageSize"
          :page-sizes="sizes"
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
          <div class="batch-drop-icon"><AppIcon icon="📚" :size="28" /></div>
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
import { onMounted, onBeforeUnmount, ref, computed, watch, nextTick } from 'vue'
import { usePagedList } from '@/composables/usePagedList'
import { fmtDate, fmtSize } from '@/utils/format'
import PageToolbar from '@/components/common/PageToolbar.vue'
import OpsCell from '@/components/common/OpsCell.vue'
import SearchField from '@/components/common/SearchField.vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import EmptyState from '@/components/EmptyState.vue'
import { ElMessage } from 'element-plus'
import { useNovelStore } from '@/stores/novel'
import SkeletonBlock from '@/components/common/SkeletonBlock.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import IconButton from '@/components/common/IconButton.vue'
import { downloadNovelTemplate } from '@/api/novel'
import { reorderNovel } from '@/api/novel'
import { useRowDragSort } from '@/composables/useRowDragSort'
import { useIsMobile } from '@/composables/useIsMobile'
import { useRouter } from 'vue-router'

const novelStore = useNovelStore()
const { isMobile } = useIsMobile()

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

/* ---- 管理分页（客户端，默认10条）----
   v2.46.161：统一走 usePagedList（自带越界修正）。store 属性不是 ref，包一层 computed 再传。 */
const { page, pageSize, total, paged: pagedRows, sizes, onPageChange, onSizeChange } = usePagedList(
  computed(() => novelStore.list),
  { defaultSize: 10 }
)

/* v2.46.188：PC 端按住左键上下拖拽调顺序（手机端不启用，避免和滚动冲突） */
useRowDragSort({
  getTableEl: () => tableRef.value?.$el,
  getRows: () => novelStore.list,
  getOffset: () => (isMobile.value ? 0 : (page.value - 1) * pageSize.value),
  enabled: () => !isMobile.value,
  onCommit: () => reorderNovel(novelStore.list.map((r) => r.id)),
})

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
  // v2.46.267：size=0 = 后端一次拉全（原来 200，超过 200 本后面的就再也看不到）
  const params = keyword.value ? { q: keyword.value } : { size: 0 }
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

/* 行内动作清单（v2.46.159）：模板只声明，图标/文案/危险色一处可改 */
const router = useRouter()

/* ---------------- 手机端书架（v2.46.209） ----------------
   判断触摸能力而不是屏幕宽度：本站手机浏览器 viewport 被 main.js 覆写成 1280，
   max-width 媒体查询在手机上不会触发。*/
const isTouch = ref(false)

/* 手机端要把这一页切成真正的窄屏：本站手机浏览器 viewport 被 main.js 覆写成 1280
   （全站要网页版布局），但书架必须按真实屏宽排才好看，否则卡片会被挤成指头大小。
   所以在这个路由上临时切 device-width + 隐藏侧栏，离开时还原。 */
let savedViewport = ''
function enterShelfMode() {
  const meta = document.querySelector('meta[name="viewport"]')
  if (!meta) return
  savedViewport = meta.getAttribute('content') || ''
  meta.setAttribute('content',
    'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover')
  document.body.classList.add('novel-shelf-mode')
}
function exitShelfMode() {
  const meta = document.querySelector('meta[name="viewport"]')
  if (meta && savedViewport) meta.setAttribute('content', savedViewport)
  document.body.classList.remove('novel-shelf-mode')
}

onMounted(() => {
  isTouch.value = (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window
  if (isTouch.value) enterShelfMode()
  // v2.46.294：趁用户还在书架上挑书，把阅读器的代码 chunk（38KB / gzip 13.7KB）
  // 和 epubjs 之外的部分提前下好 —— 点进书那一刻不用再等 chunk 下载（实测省 1.4s）。
  const warm = () => {
    import('@/views/NovelReadView.vue').catch(() => { /* 预取失败不影响正常打开 */ })
  }
  if ('requestIdleCallback' in window) requestIdleCallback(warm, { timeout: 2000 })
  else setTimeout(warm, 800)
})
onBeforeUnmount(() => { exitShelfMode() })

/** 没有封面时用「书名首字 + 渐变」，按 id 稳定取色（同一本书每次颜色一致） */
const COVER_GRADS = [
  ['#f0e6d2', '#cdb389'],
  ['#e2ecE8', '#a9c6bd'],
  ['#f0e2dc', '#c9a89f'],
  ['#e4eaf2', '#aabccd'],
  ['#ece4f0', '#b8a8c6'],
]
function coverStyle(n) {
  const g = COVER_GRADS[Math.abs(Number(n.id) || 0) % COVER_GRADS.length]
  return { background: `linear-gradient(155deg, ${g[0]}, ${g[1]})` }
}

/** 阅读进度：服务器优先（跨设备），本地 localStorage 兜底 */
function progressOf(n) {
  const srv = Number(n.progress_percent)
  if (srv > 0) return Math.min(100, Math.round(srv * 100))
  try {
    const raw = localStorage.getItem(`xuanhuang:reader:prog:${n.id}`)
    if (!raw) return 0
    const j = JSON.parse(raw)
    return Math.max(0, Math.min(100, Math.round((j.percent || 0) * 100)))
  } catch { return 0 }
}


/** v2.46.283：手动重解析 TXT（后端同步跑，12MB 约 0.3~0.6s） */
async function reparseNovel(row) {
  const tk = localStorage.getItem('token') || ''
  try {
    const r = await fetch(`/api/novels/${row.id}/parse?force=1`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tk}` },
    })
    const json = await r.json().catch(() => null)
    if (!r.ok || !json || json.code !== 0) throw new Error((json && json.msg) || `HTTP ${r.status}`)
    const d = json.data || {}
    row.chapter_count = d.count || 0
    row.parse_status = 'done'
    ElMessage.success(`解析完成：${d.count || 0} 章（${d.cost_ms || 0}ms）`)
  } catch (e) {
    row.parse_status = 'failed'
    ElMessage.error(`解析失败：${e.message || e}`)
  }
}

const rowActions = [
  // v2.46.196：点「阅读」进阅读器（epub.js / TXT 分章），直接读 novels 表的原始文件
  { icon: 'book', label: '阅读', onClick: openReader },
  { icon: 'edit', label: '编辑', onClick: openEdit },
  // v2.46.283：TXT 解析失败/换算法后可手动重解（后端同步执行，13MB 约 0.5s）
  { icon: 'refresh', label: '重解析', onClick: reparseNovel, show: (row) => String(row.original_filename || '').toLowerCase().endsWith('.txt') },
  { icon: 'trash', label: '删除', danger: true, onClick: handleDelete },
]

async function toggleFav(n) {
  const tk = localStorage.getItem('token') || ''
  const next = Number(n.is_favorite) === 1 ? 0 : 1
  n.is_favorite = next
  try {
    const r = await fetch(`/api/novels/${n.id}/favorite`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tk}` },
      body: JSON.stringify({ favorite: next }),
    })
    if (!r.ok) throw new Error(String(r.status))
  } catch {
    n.is_favorite = next ? 0 : 1
  }
}

function openReader(row) {
  // v2.46.207：走路由而不是组件内覆盖层，这样手机返回键能正确回到列表
  router.push({ name: 'NovelRead', params: { id: row.id } })
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

/* v2.46.160：统一到 utils/format.js（原实现只有 KB/MB 两档，现在 B/KB/MB/GB 自适应） */
function formatSize(bytes) {
  return bytes == null ? '-' : fmtSize(bytes)
}

function formatTime(timeStr) {
  return fmtDate(timeStr, '-')
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

.mg-toolbar-spacer { flex: 1 1 auto; min-width: 8px; }
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
  background: var(--yq-accent-faint, rgba(199, 169, 107, 0.10));
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
  border-color: var(--yq-accent);
  background: var(--yq-accent-faint, rgba(199, 169, 107, 0.08));
  box-shadow: 0 4px 16px var(--yq-accent-glow, rgba(199, 169, 107, 0.18));
}
.batch-drop { text-align: center; color: var(--ls-text-2); }
.batch-drop-icon { font-size: 28px; line-height: 1; margin-bottom: 6px; }
.batch-drop-text { font-size: 13px; }
.batch-drop-text em { color: var(--yq-accent); font-style: normal; margin: 0 4px; }
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
  color: var(--yq-accent);
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

/* ================= 手机端书架（v2.46.209） =================
   夜星要「PC 列表 / 手机书架」。卡片靠封面撑视觉，不加边框，
   进度用封面底部一条细线表示，比数字更直观。 */
.novel-shelf { padding: 4px 2px 12px; }
.novel-shelf {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
  gap: 16px 11px;
}
.ns-card {
  display: flex;
  flex-direction: column;
  gap: 7px;
  /* 🔴 <button> 的 UA 样式 color 是 buttontext（黑色），深色主题下书名会看不见，
     必须显式继承父级（这个坑 3D 棋牌大厅也踩过一次） */
  color: inherit;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ns-cover {
  position: relative;
  aspect-ratio: 3 / 4;
  width: 100%;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 16px -8px rgba(20, 30, 40, .38), 0 1px 0 rgba(255, 255, 255, .5) inset;
  transition: transform .18s ease, box-shadow .18s ease;
}
.ns-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ns-initial {
  font-size: 34px;
  font-weight: 500;
  color: rgba(70, 58, 46, .5);
  letter-spacing: .04em;
  user-select: none;
}
.ns-prog {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 3px;
  background: rgba(60, 50, 40, .55);
  border-radius: 0 2px 2px 0;
  transition: width .3s ease;
}
.ns-card:active .ns-cover {
  transform: scale(.965);
  box-shadow: 0 3px 10px -6px rgba(20, 30, 40, .4);
}
.ns-meta { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ns-title {
  font-size: 13px;
  line-height: 1.35;
  /* 跟随主题：项目有多套 token（--ls-* / --lj-* / --dp-*），用 inherit 最稳 */
  color: inherit;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.ns-sub {
  font-size: 11.5px;
  opacity: .62;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ns-pct { font-size: 11px; opacity: .55; }

/* 手机（触摸）上给书架多留点呼吸空间，并让网格更密 */
@media (pointer: coarse) {
  .novel-shelf {
    /* 父容器（IslandInnerBase）在窄屏仍有约 57px 内边距，撑不出 3 列，
       用负 margin 往回收一点 */
    margin: 0 -14px;
    grid-template-columns: repeat(auto-fill, minmax(76px, 1fr));
    gap: 18px 10px;
    padding: 8px 0 20px;
  }
  .ns-initial { font-size: 30px; }
  .ns-title { font-size: 12.5px; }
}

/* 书架模式（手机）：侧栏在 390 宽下会把内容挤没，直接隐藏 */
:global(body.novel-shelf-mode .dsb),
:global(body.novel-shelf-mode .tab-bar),
:global(body.novel-shelf-mode .app-tabbar) {
  display: none !important;
}

/* 书架星标（收藏） */
.ns-star {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  background: rgba(30, 26, 20, .28);
  opacity: 0;
  transition: opacity .16s ease;
}
.ns-star.on { opacity: 1; color: #ffe9a8; }
@media (pointer: coarse) {
  /* 触摸设备没有 hover，收藏按钮常显，否则永远点不到 */
  .ns-star { opacity: .92; }
}
</style>
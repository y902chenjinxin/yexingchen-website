<template>
  <IslandInnerBase type="music" title="音乐" subtitle="音律飘渺 · 曲库管理">
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
            @keyup.enter="doSearch"
            @clear="doSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <!-- 上传人筛选：曲库是全账号共享的，用它快速定位「自己传的」。
               v2.46.69：手机端纯播放列表，筛选/查询/批量删除收去桌面端 -->
          <el-select
            v-if="!isMobile"
            v-model="uploaderId"
            size="small"
            clearable
            placeholder="上传人"
            class="mt-uploader"
            @change="doSearch"
          >
            <el-option v-for="u in uploaders" :key="u.id" :label="u.name" :value="u.id" />
          </el-select>
          <el-button v-if="!isMobile" type="primary" size="small" plain @click="doSearch">查询</el-button>
          <el-button v-if="!isMobile && hasFilter" size="small" plain @click="resetSearch">清空筛选</el-button>
          <span v-if="!isMobile && hasFilter" class="search-count">匹配 {{ musicStore.list.length }} 条</span>
        </div>
        <div class="mt-right">
          <el-button
            v-if="!isMobile"
            type="danger"
            plain
            size="small"
            :disabled="!selectedRows.length"
            @click="handleBatchDelete"
          >
            批量删除<span v-if="selectedRows.length">（{{ selectedRows.length }}）</span>
          </el-button>
          <!-- v2.46.148：主操作从标题下挪进工具栏（手机端是纯播放列表，不显示） -->
          <span class="mg-toolbar-spacer"></span>
          <template v-if="!isMobile">
            <IconButton icon="upload" label="上传音乐" variant="primary" @click="openUpload" />
            <IconButton icon="folder" label="批量导入" @click="openBatch" />
          </template>
        </div>
      </div>

      <el-table
        ref="tableRef"
       
        :data="pagedRows"
        v-loading="musicStore.loading && !musicStore.list.length"
        stripe
        style="width: 100%"
        :row-class-name="rowClassName"
        @selection-change="onSelectionChange"
        empty-text="暂无音乐，点上方「导入」添加"
      >
        <!-- 全选：内置古筝已是普通曲目，不再有「不可勾选」的只读行。
             v2.46.69：手机端纯播放列表，批量勾选无意义，隐藏 -->
        <el-table-column v-if="!isMobile" type="selection" width="46" />

        <!-- 标题：播放按钮内联，省一列 -->
        <el-table-column label="曲目" min-width="220">
          <template #default="{ row }">
            <div class="cell-title">
              <button
                class="mini-btn play-btn"
                :class="{ playing: isCurPlaying(row) }"
                :title="isCurPlaying(row) ? '暂停' : '播放'"
                @click="handlePlay(row)"
              ><!-- v2.46.195 暂停图标改用 SVG 画两条竖杠。
                   原来用两个 ❚（U+275A）字符，这个码位在部分字体会渲染成一条较宽的双线，
                   两个叠起来就变成四条，夜星反馈「点击变成四个竖杠」。SVG 精确可控。 -->
              <svg
                v-if="isCurPlaying(row)"
                class="ic-pause"
                width="12"
                height="12"
                viewBox="0 0 12 12"
                aria-hidden="true"
              >
                <rect x="3" y="2.2" width="2" height="7.6" rx=".6" fill="currentColor" />
                <rect x="7" y="2.2" width="2" height="7.6" rx=".6" fill="currentColor" />
              </svg>
              <AppIcon v-else icon="▶" :size="12" /></button>
              <span class="tt">{{ row.title || '未知曲目' }}</span>
              <el-tag v-if="Number(row.is_default) === 1" size="small" type="warning">内置</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column v-if="!isMobile" prop="artist" label="作者" width="116" show-overflow-tooltip />
        <el-table-column v-if="!isMobile" prop="category" label="分类" width="96">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>
        <el-table-column v-if="!isMobile" prop="tags" label="标签" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.tags">{{ row.tags }}</span>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>
        <el-table-column v-if="!isMobile" label="大小" width="86">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column v-if="!isMobile" label="时长" width="72">
          <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
        </el-table-column>
        <!-- 上传人：只读展示，由上传时的账号决定，后端不支持修改 -->
        <el-table-column v-if="!isMobile" label="上传人" width="96" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.uploader_name">{{ row.uploader_name }}</span>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>

        <!-- 操作：设为背景乐 / 编辑 / 删除 —— 左对齐排布，保证各行按钮纵向对齐。
             内置古筝现在是普通曲目记录，所以不再有「只读行」守卫，每首都能编辑删除。
             v2.46.69：手机端纯播放列表只留「设为背景乐」，编辑/删除收去桌面端。
             v2.46.81：手机端纯播放列表，连「设为背景乐」也一并收去（只展示曲目 + 内联播放键），
             故整列不在手机端渲染。 -->
        <el-table-column v-if="!isMobile" label="操作" :width="150" fixed="right">
          <template #default="{ row }">
            <div class="row-ops">
              <el-tag v-if="isCurBgm(row)" size="small" type="primary" effect="dark" class="bgm-on">背景乐</el-tag>
              <IconButton v-else icon="star" label="设为背景乐" icon-only @click="setAsBg(row)" />

              <template v-if="!isMobile">
                <IconButton icon="edit" size="sm" label="编辑" icon-only @click="openEdit(row)" />
                <IconButton icon="trash" size="sm" label="删除" variant="danger" icon-only @click="handleDelete(row)" />
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- v2.46.299：手机端分块渲染，避免一次铺几百行 -->
      <div v-if="isMobile && mobileRestCount > 0" class="mu-more">
        <button type="button" class="mu-more-btn" @click="showMoreMobile">
          显示更多（还剩 {{ mobileRestCount }} 首）
        </button>
      </div>

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
          <div class="batch-drop-icon"><AppIcon icon="📥" :size="28" /></div>
          <div class="batch-drop-text">拖拽文件到这里，或<em>点击选择</em></div>
          <div class="batch-drop-hint">MP3 / FLAC / WAV，单次最多 20 个 · 文件名写成「歌名-作者」会自动拆开</div>
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
import AppIcon from '@/components/common/AppIcon.vue'
import IconButton from '@/components/common/IconButton.vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useIsMobile } from '@/composables/useIsMobile'
import { useMusicStore } from '@/stores/music'
import { readAudioDuration, readRemoteDuration, runWithConcurrency } from '@/utils/audioMeta'
import { parseMusicFilename, fmtMediaDuration as formatDuration } from '@/utils/format'
import { usePlayerStore } from '@/stores/player'
import { useBgmLibraryStore } from '@/stores/bgmLibrary'
import { downloadMusicTemplate, getMusicUploaders } from '@/api/music'
import { reorderMusic } from '@/api/music'
import { useRowDragSort } from '@/composables/useRowDragSort'

const { isMobile } = useIsMobile()
const musicStore = useMusicStore()
const player = usePlayerStore()
const bgm = useBgmLibraryStore()

const showUpload = ref(false)
const keyword = ref('')
/* 上传人筛选：曲库全账号共享，用它快速找到自己上传的曲目 */
const uploaderId = ref(null)
const uploaders = ref([])
const hasFilter = computed(() => !!keyword.value || !!uploaderId.value)
const uploading = ref(false)
const uploadRef = ref(null)
const uploadFileList = ref([])
const uploadFile = ref(null)
const uploadForm = ref({ title: '', artist: '', category: '', tags: '' })

/* ---- 管理分页（客户端，默认10条；手机端已隐藏分页控件，故一次展示全量） ---- */
const page = ref(1)
const pageSize = ref(10)
/* v2.46.299：手机端原来是「list.length」= 全部渲染（254 首时 el-table 要建两千多个
   单元格，中低端机直接卡两三秒）。改成先渲染 40 条，点「显示更多」再加 40。 */
const MOBILE_STEP = 40
const mobileRenderLimit = ref(MOBILE_STEP)
const pagedRows = computed(() => {
  if (isMobile.value) return musicStore.list.slice(0, mobileRenderLimit.value)
  const start = (page.value - 1) * pageSize.value
  return musicStore.list.slice(start, start + pageSize.value)
})
const mobileRestCount = computed(() =>
  isMobile.value ? Math.max(0, musicStore.list.length - mobileRenderLimit.value) : 0
)
function showMoreMobile() {
  mobileRenderLimit.value = Math.min(mobileRenderLimit.value + MOBILE_STEP, musicStore.list.length)
}
/* v2.46.188：PC 端按住左键上下拖拽调顺序（手机端不启用，避免和滚动冲突） */
useRowDragSort({
  getTableEl: () => tableRef.value?.$el,
  getRows: () => musicStore.list,
  getOffset: () => (isMobile.value ? 0 : (page.value - 1) * pageSize.value),
  enabled: () => !isMobile.value,
  onCommit: () => reorderMusic(musicStore.list.map((r) => r.id)),
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
  // v2.46.234：文件名当「歌名-作者」解析；作者优先用文件名里的，没有再落到批量作者框
  const parsed = parseMusicFilename(raw.name)
  const item = {
    raw,
    filename: raw.name,
    size: raw.size,
    duration: 0,
    title: parsed.title,
    artist: parsed.artist || batchForm.value.artist || '',
    category: batchForm.value.category || '',
    tags: batchForm.value.tags || '',
  }
  batchItems.value.push(item)
  // v2.46.231：边加边读时长（读本地 File 头，零网络），不阻塞选择流程
  readAudioDuration(raw).then((d) => { item.duration = d })
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
    // v2.46.234：标题里的"歌名"部分始终取文件名解析后的 title，
    // 作者优先级：文件名自带（`晴天-周杰伦.mp3`）> 批量作者输入框。
    const parsed = parseMusicFilename(it.filename)
    const artist = parsed.artist || commonArtist
    if (mode === 'filename') {
      it.title = parsed.title
    } else if (mode === 'filename-artist') {
      it.title = artist ? `${parsed.title} - ${artist}` : parsed.title
    } else {
      // custom：保留用户已输入的标题，没有则用解析出的歌名兜底
      if (!it.title) it.title = parsed.title
    }
    it.artist = artist
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
    // 提交前把还没读完时长的补齐（已读到的直接用，避免重复解析）
    const items = await Promise.all(batchItems.value.map(async (it) => ({
      title: it.title || it.filename.replace(/\.[^.]+$/, ''),
      artist: batchForm.value.artist || '',
      category: batchForm.value.category || '',
      tags: batchForm.value.tags || '',
      duration: it.duration || (await readAudioDuration(it.raw)) || 0,
    })))
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
  // v2.46.299：先用上次的列表立刻铺满（sessionStorage，仅本站会话内有效），
  // 再把网络请求的结果覆盖上去 —— 再次进音乐页几乎零等待。
  if (!keyword.value && !uploaderId.value) loadListCache()
  fetchData()
  loadUploaders()
})

/* ---- 列表缓存（只缓存「无搜索/无筛选」的完整列表） ---- */
const LIST_CACHE_KEY = 'xuanhuang:music:list'
function loadListCache() {
  try {
    const raw = sessionStorage.getItem(LIST_CACHE_KEY)
    if (!raw) return false
    const d = JSON.parse(raw)
    if (!d || !Array.isArray(d.list) || !d.list.length) return false
    musicStore.list = d.list
    musicStore.total = d.total || d.list.length
    syncQueueWithList()
    return true
  } catch { return false }
}
function saveListCache() {
  try {
    sessionStorage.setItem(LIST_CACHE_KEY, JSON.stringify({ list: musicStore.list, total: musicStore.total, at: Date.now() }))
  } catch { /* 超配额就放弃缓存，不影响功能 */ }
}

async function loadUploaders() {
  try {
    const res = await getMusicUploaders()
    uploaders.value = res?.data?.list || []
  } catch { /* 拉不到就只显示「全部」，不影响主流程 */ }
}

async function fetchData() {
  // size=0 → 后端一次拉全（v2.46.259）。
  // 原来是 200：库里 254 首时，排在末尾的 54 首（最早手动上传、sort_order 还是老值的那批）
  // 永远不显示，看起来像「歌丢了」。客户端分页照旧，只是数据源不再被截断。
  const params = { size: 0 }
  if (keyword.value) params.q = keyword.value
  if (uploaderId.value) params.uploader_id = uploaderId.value
  await musicStore.fetchList(params)
  syncQueueWithList()
  if (!keyword.value && !uploaderId.value) saveListCache()
  // v2.46.299：时长补全会对每首 duration=0 的歌发 Range 请求读音频头，
  // 一进页面就跑会和首屏抢带宽/连接（实测单条 0.5~1.7s）。推迟到首屏空闲后再补。
  scheduleHealDurations()
}

let healTimer = 0
function scheduleHealDurations() {
  clearTimeout(healTimer)
  healTimer = setTimeout(() => {
    if (typeof requestIdleCallback === 'function') requestIdleCallback(() => healDurations(), { timeout: 4000 })
    else healDurations()
  }, 2500)
}

/* 进页面后把播放队列换成这张真实列表（v2.46.259）：
 * 启动时恢复「上次听到哪」只有一首曲目当队列，上下首点了没用；
 * 这里补上完整列表并让 index 指向当前曲目，行为就和无记忆时一致了。 */
function syncQueueWithList() {
  const list = musicStore.list || []
  if (!list.length || player.mode !== 'playlist' || !player.curItem) return
  const idx = list.findIndex((x) => String(x.id) === String(player.curItem.id))
  if (idx >= 0) player.setQueue(list, idx)
}

/* ---------- 历史数据时长补全（v2.46.231） ----------
 * 2.46.231 之前上传的曲目 duration 全是 0（当时上传接口根本没这个字段）。
 * 这里在列表加载后，对 duration<=0 的曲目发一次 metadata 请求读到真实时长，
 * 先本地显示、再回写数据库 —— 之后打开列表就直接有值，不用再读。
 * 并发 6：实测每条读 metadata + 回写约 2-3 秒，63 条曲目并发 2 要跑近 2 分钟，
 * 并发 6 能压到 30 秒内。nginx 支持 Range，每次只取文件头（几 KB），不会占带宽。
 * 失败静默跳过（不打扰用户）。 */
let healingDurations = false
async function healDurations() {
  if (healingDurations) return
  const list = musicStore.list || []
  const todo = list.filter((m) => m && m.id !== 'default' && !(Number(m.duration) > 0))
  if (!todo.length) return
  healingDurations = true
  try {
    await runWithConcurrency(todo, async (m) => {
      const dur = await readRemoteDuration(`/api/music/${m.id}/stream`)
      if (!dur) return
      m.duration = dur // 先让界面立刻有值
      try {
        await musicStore.update(m.id, { duration: dur })
      } catch { /* 回写失败不影响本次显示 */ }
    }, 6)
  } finally {
    healingDurations = false
  }
}

function doSearch() {
  musicStore.page = 1
  page.value = 1
  mobileRenderLimit.value = MOBILE_STEP
  fetchData()
}

function resetSearch() {
  keyword.value = ''
  uploaderId.value = null
  doSearch()
}

/** 上一次由文件名自动填进表单的值（用户手动改过就不再用它覆盖） */
const autoFilled = ref({ title: '', artist: '' })

function openUpload() {
  uploadForm.value = { title: '', artist: '', category: '', tags: '' }
  uploadFileList.value = []
  uploadFile.value = null
  // 记录上一条"自动填充"的值，换文件时据此判断要不要跟着更新
  autoFilled.value = { title: '', artist: '' }
  showUpload.value = true
}

function handleFileChange(file) {
  uploadFile.value = file.raw
  // v2.46.234：文件名当「歌名-作者」解析，两个框一次填好，不用手打两遍。
  // 覆盖条件：框是空的，或者框里还是上次的自动填充值（说明用户没改过）。
  const parsed = parseMusicFilename(file.name)
  const f = uploadForm.value
  if (!f.title || f.title === autoFilled.value.title) f.title = parsed.title
  if (!f.artist || f.artist === autoFilled.value.artist) f.artist = parsed.artist
  autoFilled.value = { title: parsed.title, artist: parsed.artist }
}

async function handleUpload() {
  if (!uploadFile.value) { ElMessage.warning('请选择音乐文件'); return }
  if (!uploadForm.value.title) { ElMessage.warning('请输入标题'); return }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    // v2.46.231：先读本地文件时长（零网络，只解析文件头），随表单提交
    const dur = await readAudioDuration(uploadFile.value)
    formData.append('duration', String(dur))
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
    // bgmChoiceId 与 setBackground 都在 bgmLibrary store 上；早前误写成 player.* ，
    // 前者恒为 undefined（判断永不成立）、后者不是函数（异常被 catch 吞掉）
    const hitBgm = ids.some(id => String(bgm.bgmChoiceId) === String(id))
    for (const id of ids) {
      await musicStore.remove(id)
    }
    if (hitBgm) bgm.setBackground(null, false)
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

</script>

<style scoped>
/* v2.46.299：手机端「显示更多」 */
.mu-more { display: flex; justify-content: center; padding: 14px 0 8px; }
.mu-more-btn {
  padding: 9px 22px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, .16);
  background: rgba(255, 255, 255, .06);
  color: inherit;
  font-size: 13px;
  cursor: pointer;
}
.mu-more-btn:active { background: rgba(255, 255, 255, .12); }

.manage-pane {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 18px 20px;
  box-shadow: var(--dp-shadow);
}

/* 工具条：左右两端分布，中间自动留白 */
.mg-toolbar-spacer { flex: 1 1 auto; min-width: 8px; }
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
/* 上传人筛选下拉（与搜索框同排，窄一些） */
.mt-uploader { width: 132px; }
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
.ic-pause { display: block; flex-shrink: 0; }
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
  background: var(--yq-accent-faint, rgba(199, 169, 107, 0.10));
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
  border-color: var(--yq-accent, #c7a96b);
  background: var(--yq-accent-faint, rgba(199, 169, 107, 0.08));
  box-shadow: 0 4px 16px var(--yq-accent-glow, rgba(199, 169, 107, 0.18));
}
.batch-drop { text-align: center; color: var(--dp-text2); }
.batch-drop-icon { font-size: 28px; line-height: 1; margin-bottom: 6px; }
.batch-drop-text { font-size: 13px; }
.batch-drop-text em { color: var(--yq-accent, #c7a96b); font-style: normal; margin: 0 4px; }
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
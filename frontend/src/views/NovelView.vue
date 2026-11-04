<template>
  <IslandInnerBase type="novel" title="小说" subtitle="书卷悠长">
    <div class="manage-pane" :class="{ 'is-shelf-pane': isTouch }">
      <PageToolbar v-if="!isTouch">
        <!-- v2.46.159：统一下拉/搜索组件（SearchField 内含查询按钮与清除） -->
        <SearchField v-model="keyword" placeholder="搜索标题/作者" width="260px" @search="doSearch" />
        <!-- v2.46.362：分类筛选（固定枚举 novelCategories.js，客户端过滤） -->
        <el-select v-model="filterCategory" clearable placeholder="全部分类" size="small" class="nv-cat-filter">
          <el-option v-for="c in NOVEL_CATEGORIES" :key="c" :label="c" :value="c" />
        </el-select>
        <span v-if="keyword" class="search-count">匹配 {{ filteredNovels.length }} 条</span>
        <el-button v-if="keyword || filterCategory" size="small" plain @click="clearFilters">清空筛选</el-button>
        <el-button type="danger" plain size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
          批量删除<span v-if="selectedRows.length">（{{ selectedRows.length }}）</span>
        </el-button>
        <template #actions>
          <IconButton icon="upload" label="上传小说" variant="primary" @click="openUpload" />
          <IconButton icon="folder" label="批量导入" @click="openBatch" />
        </template>
      </PageToolbar>

      <!-- 手机端（v2.46.308）：番茄式书架头 —— 只有一条搜索，
           上传/导入/管理收成三个圆形图标，批量删除进「管理」选择态 -->
      <div v-else class="nv-head">
        <div v-if="!selecting" class="nv-bar">
          <label class="nv-search">
            <svg class="nv-search-ic" width="15" height="15" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
              <circle cx="10.5" cy="10.5" r="6.4" />
              <path d="M15.4 15.4 20 20" />
            </svg>
            <input
              v-model="keyword"
              type="search"
              enterkeyhint="search"
              placeholder="搜索书名、作者"
              autocomplete="off"
              @search="keyword = ''"
            />
            <button v-if="keyword" class="nv-x" type="button" aria-label="清除" @click="keyword = ''">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="2.2" stroke-linecap="round" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </label>
          <button class="nv-ic-btn" type="button" aria-label="上传小说" @click="openUpload">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" /><path d="M4.5 15v3.5a1.5 1.5 0 0 0 1.5 1.5h12a1.5 1.5 0 0 0 1.5-1.5V15" />
            </svg>
          </button>
          <button class="nv-ic-btn" type="button" aria-label="批量导入" @click="openBatch">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.7" stroke-linejoin="round" aria-hidden="true">
              <path d="M3.5 7.5a1.5 1.5 0 0 1 1.5-1.5h4l1.6 2h8a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 18.6 19H5a1.5 1.5 0 0 1-1.5-1.5v-10Z" />
            </svg>
          </button>
          <button class="nv-ic-btn" type="button" aria-label="管理书架" @click="toggleSelecting">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
        </div>

        <!-- v2.46.362：手机书架分类 chips（横向滑动，点击切换 / 再点取消） -->
        <div v-if="!selecting" class="nv-cats">
          <button class="nv-chip" :class="{ on: !filterCategory }" type="button" @click="filterCategory = ''">全部</button>
          <button
            v-for="c in NOVEL_CATEGORIES"
            :key="c"
            class="nv-chip"
            :class="{ on: filterCategory === c }"
            type="button"
            @click="filterCategory = filterCategory === c ? '' : c"
          >{{ c }}</button>
        </div>

        <!-- 选择态：取消 / 已选 / 删除（番茄「管理」模式同构） -->
        <div v-else class="nv-bar nv-bar-sel">
          <button class="nv-txt-btn" type="button" @click="toggleSelecting">取消</button>
          <span class="nv-sel-count">已选 {{ picked.length }} 本</span>
          <button class="nv-txt-btn is-danger" type="button" :disabled="!picked.length" @click="askDeletePicked">
            删除
          </button>
        </div>
      </div>
      <!-- 加载中：鎏金光扫骨架行，替代默认旋转圈 -->
      <div v-if="novelStore.loading" class="sk-skeleton-rows">
        <SkeletonBlock v-for="i in 6" :key="i" width="100%" height="42px" style="margin-bottom: 8px;" />
      </div>
      <!-- 手机端：书架（一直往下滑，不分页）。桌面端仍走下面的表格。
           v2.46.209：夜星要「PC 列表 / 手机书架」，用触摸能力判断而不是宽度
           （本站手机浏览器 viewport 是 1280，max-width 媒体查询不触发）。
           v2.46.308：改番茄式书墙 —— 三列、无外框、副行「读至 x% · n 章」。 -->
      <div
        v-if="isTouch && !novelStore.loading && shelfRows.length"
        class="novel-shelf"
        :class="{ 'is-selecting': selecting }"
      >
        <button
          v-for="n in shelfRows"
          :key="n.id"
          class="ns-card"
          :class="{ 'is-picked': isPicked(n) }"
          type="button"
          @click="onCardTap(n)"
        >
          <div class="ns-cover" :style="coverStyle(n)">
            <img v-if="n.cover_url" :src="n.cover_url" :alt="n.title" loading="lazy" />
            <span v-else class="ns-initial">{{ (n.title || '书').slice(0, 1) }}</span>
            <span v-if="n.parse_status === 'pending'" class="ns-flag">解析中</span>
            <!-- 选择态：右上角圆形勾选；非选择态：淡淡的收藏星（已收藏才实心金） -->
            <span v-if="selecting" class="ns-tick" :class="{ on: isPicked(n) }">
              <svg v-if="isPicked(n)" width="11" height="11" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4.5 12.5l5 5 10-11" />
              </svg>
            </span>
            <span
              v-else
              class="ns-star"
              :class="{ on: Number(n.is_favorite) === 1 }"
              role="button"
              :aria-label="Number(n.is_favorite) === 1 ? '取消收藏' : '收藏'"
              @click.stop="toggleFav(n)"
            >
              <svg width="12" height="12" viewBox="0 0 24 24"
                   :fill="Number(n.is_favorite) === 1 ? 'currentColor' : 'none'"
                   stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
                <path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.6 9.7l5.8-.8L12 3.6Z" />
              </svg>
            </span>
          </div>
          <div class="ns-meta">
            <span class="ns-title">{{ n.title }}</span>
            <span class="ns-sub">
              {{ progressOf(n) > 0 ? `读至 ${progressOf(n)}%` : (n.chapter_count ? `${n.chapter_count} 章` : '解析中') }}
            </span>
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
        <!-- v2.46.322：TXT 行有 4 个动作（阅读/编辑/重解析/删除），原 100px 列宽装不下，
             第 3 个「重解析」被单元格裁掉一半、第 4 个「删除」完全看不见。
             宽度按 4×30 + 3×4 + 单元格左右 padding 24 算 = 156，取 160 留余量。 -->
        <el-table-column label="操作" :width="isMobile ? 168 : 160" fixed="right">
          <!-- v2.46.159：行内动作统一用 OpsCell -->
          <template #default="{ row }">
            <OpsCell class="nv-ops" :row="row" :actions="rowActions" />
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-if="!novelStore.loading && filteredNovels.length === 0"
        tone="data"
        title="还没有添加小说"
        description="把读过的章节粘贴进来，系统帮你管理进度、收藏句子、生成摘要"
        action-label="↑ 上传小说"
        @action="openUpload"
      />
      <!-- 手机端不做分页：书墙一直往下滑（v2.46.308 夜星要求） -->
      <div v-else-if="!novelStore.loading && !isTouch" class="pager-wrap">
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
        <el-form-item label="分类">
          <el-select v-model="uploadForm.category" placeholder="选择分类" clearable filterable style="width: 100%">
            <el-option v-for="c in NOVEL_CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
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
        <el-form-item label="分类">
          <!-- v2.46.362：固定枚举下拉（夜星要求）。历史自由文本仍会显示原值，保存时可选枚举值替换 -->
          <el-select v-model="editForm.category" placeholder="选择分类" clearable filterable style="width: 100%">
            <el-option v-for="c in NOVEL_CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
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
          <el-select v-model="batchForm.category" placeholder="应用到所有文件（可选）" clearable filterable style="width: 100%">
            <el-option v-for="c in NOVEL_CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
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
      <p>确定删除选中的 <b>{{ deleteCount }}</b> 项吗？此操作不可恢复。</p>
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
import { NOVEL_CATEGORIES } from '@/constants/novelCategories'

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
   v2.46.161：统一走 usePagedList（自带越界修正）。store 属性不是 ref，包一层 computed 再传。
   v2.46.362：数据源换成「按分类过滤后的列表」（分类筛选对桌面表格 / 手机书架同时生效） */
const filterCategory = ref('')
const filteredNovels = computed(() => {
  const list = novelStore.list || []
  if (!filterCategory.value) return list
  return list.filter((n) => (n.category || '').trim() === filterCategory.value)
})

const { page, pageSize, total, paged: pagedRows, sizes, onPageChange, onSizeChange } = usePagedList(
  computed(() => filteredNovels.value),
  { defaultSize: 10 }
)

/* v2.46.362：清空搜索 + 分类两个筛选 */
function clearFilters() {
  keyword.value = ''
  filterCategory.value = ''
  doSearch()
}

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

/** 没有封面时用「书名首字 + 渐变」，按 id 稳定取色（同一本书每次颜色一致）
 *  🔴 v2.46.388：原来是 #f0e6d2 这类**粉彩浅色**（米黄/浅绿/浅粉/浅蓝/浅紫）。
 *  在深色书墙上就是九块彩色马卡龙，夜星说「组件颜色发灰」「书籍为什么也有框」——
 *  每个浅色块在深底上边界特别清楚，天然读成「一个框」。
 *  改成深色系：同一套色相，明度压到 #10~#3a，书封沉进画面里，
 *  靠首字和顶部一道受光边区分彼此。 */
const COVER_GRADS = [
  ['#2b3a52', '#141b26'],   // 夜蓝
  ['#243b3a', '#101d1c'],   // 墨绿
  ['#3d2f28', '#1b1410'],   // 赭石
  ['#2b2f45', '#14151f'],   // 靛紫
  ['#2f3339', '#14161a'],   // 石板
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

/* ---------------- 手机端书墙（v2.46.308） ----------------
   夜星：「不要有分页，就一直往下滑」+「整体学番茄」。
   - 一次渲染全部（列表本来就 size=0 全量拉回来了），不分页
   - 搜索在本地过滤（不再打接口），输入即筛，番茄就是这样
   - 「管理」= 选择态：点封面勾选，底部不出来回跳的勾选框，顶部一条操作栏 */
const selecting = ref(false)
const picked = ref([])

const shelfRows = computed(() => {
  if (!isTouch.value) return pagedRows.value
  const kw = String(keyword.value || '').trim().toLowerCase()
  const cat = filterCategory.value
  let rows = novelStore.list || []
  if (cat) rows = rows.filter((n) => (n.category || '').trim() === cat)
  if (!kw) return rows
  return rows.filter(
    (n) =>
      String(n.title || '').toLowerCase().includes(kw) ||
      String(n.author || '').toLowerCase().includes(kw),
  )
})

function toggleSelecting() {
  selecting.value = !selecting.value
  picked.value = []
}

function isPicked(n) {
  return picked.value.includes(n.id)
}

function onCardTap(n) {
  if (!selecting.value) { openReader(n); return }
  const i = picked.value.indexOf(n.id)
  if (i >= 0) picked.value.splice(i, 1)
  else picked.value.push(n.id)
}

function askDeletePicked() {
  if (!picked.value.length) return
  showBatchDelete.value = true
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
/** 手机走「管理」选择态（picked），桌面走表格勾选（selectedRows） */
const deleteCount = computed(() => (isTouch.value ? picked.value.length : selectedRows.value.length))
function handleBatchDelete() {
  if (!selectedRows.value.length) return
  showBatchDelete.value = true
}
async function confirmBatchDelete() {
  const ids = isTouch.value ? [...picked.value] : selectedRows.value.map(r => r.id)
  if (!ids.length) return
  batchDeleting.value = true
  try {
    for (const id of ids) {
      await novelStore.remove(id)
    }
    ElMessage.success(`已删除 ${ids.length} 项`)
    showBatchDelete.value = false
    tableRef.value?.clearSelection()
    picked.value = []
    selecting.value = false
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

/* v2.46.322：4 个行内动作压到 30px/间距 4px，160px 列宽刚好放下且不显拥挤
   （IconButton 全局 icon-only 是 36px，这里表格行内才收窄，不影响别处）
   带 .manage-pane 前缀是为了压过 OpsCell 自带的 `.ops{gap:6px}`（同特异性，靠顺序不稳） */
.manage-pane .nv-ops {
  gap: 4px;
}
.manage-pane .nv-ops :deep(.ibtn.is-icon-only) {
  width: 30px;
  height: 30px;
  border-radius: 9px;
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

/* ================= 手机端书架（v2.46.308 · 番茄式） =================
   夜星两轮反馈：①「外面有个框」②「学番茄、不要分页」。
   所以这里整页去框 + 三列书墙 + 一直在同一屏里往下滑。
   🔴 去框必须带 !important：mobile-product.css 里
   `#app.is-mobile .island-inner:not(.island-inner-music) .manage-pane`
   是 (1,3,0) 特异性，scoped 的 `.manage-pane.is-shelf-pane[data-v]` 只有 (0,3,0)。 */
.manage-pane.is-shelf-pane {
  background: transparent !important;
  border: 0 !important;
  border-radius: 0 !important;
  /* 左右 16px 是书架唯一的内边距（番茄的呼吸感），上下交给页头/滚动容器 */
  padding: 0 16px !important;
  box-shadow: none !important;
  -webkit-backdrop-filter: none !important;
  backdrop-filter: none !important;
}

/* ---- 顶部：一条搜索 + 三个圆形图标（番茄书架头） ---- */
.nv-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
}
.nv-search {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  padding: 0 12px;
  border-radius: 10px;
  /* 番茄搜索框是浅灰实底，不用描边；用 currentColor 混出来，深浅主题都自适应 */
  background: color-mix(in srgb, currentColor 7%, transparent);
}
.nv-search-ic { flex: none; opacity: .42; }
.nv-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}
.nv-search input::placeholder { color: currentColor; opacity: .42; }
/* 去掉 type=search 的原生 ✕（Safari/Chrome 都有，位置还不一样） */
.nv-search input::-webkit-search-cancel-button { display: none; }
.nv-x {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: color-mix(in srgb, currentColor 10%, transparent);
  color: inherit;
  opacity: .55;
  cursor: pointer;
}
.nv-ic-btn {
  flex: none;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: color-mix(in srgb, currentColor 7%, transparent);
  color: inherit;
  opacity: .8;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.nv-ic-btn:active { background: color-mix(in srgb, currentColor 14%, transparent); }

/* 选择态那一条：取消 —— 已选 n 本 —— 删除 */
.nv-bar-sel { justify-content: space-between; }

/* v2.46.362：分类筛选 chips（手机书架横向滑动） */
.nv-cats {
  display: flex;
  gap: 8px;
  margin: -6px 0 14px;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.nv-cats::-webkit-scrollbar { display: none; }
.nv-chip {
  flex: none;
  height: 30px;
  padding: 0 14px;
  border: 0;
  border-radius: 15px;
  background: color-mix(in srgb, currentColor 7%, transparent);
  color: inherit;
  font-size: 13px;
  font-family: inherit;
  white-space: nowrap;
  cursor: pointer;
  opacity: .72;
  -webkit-tap-highlight-color: transparent;
}
.nv-chip.on {
  background: var(--yq-accent, #c7a96b);
  color: #fff;
  opacity: 1;
}

/* v2.46.362：桌面工具栏的分类筛选下拉宽度 */
.nv-cat-filter { width: 130px; }
.nv-txt-btn {
  height: 34px;
  padding: 0 6px;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 15px;
  font-family: inherit;
  cursor: pointer;
}
.nv-txt-btn.is-danger { color: #d9534f; font-weight: 500; }
.nv-txt-btn:disabled { opacity: .35; }
.nv-sel-count { font-size: 13px; opacity: .6; }

/* ---- 书墙：三列、无框、一直往下滑 ---- */
.novel-shelf {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px 13px;
  padding: 0 0 28px;
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
/* 封面：番茄就是「一张图 + 轻投影」，没有书脊没有纸厚白边（白边看着像又一层框） */
.ns-cover {
  position: relative;
  aspect-ratio: 3 / 4;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  /* v2.46.378：投影收一半。原来 8px/16px 的落影在深色页面上会糊成一圈灰边，
     看着像书本外面又套了个框（夜星：「书籍为什么也有框」）。
     书卡本身已经不再被玻璃规则收编，这里只需要一点点「贴住纸面」的影。 */
  /* v2.46.388：深色书封只需要「贴在纸面上」的一点影 + 顶边受光，
     不再有外描边（夜星：「这个框到底有啥用」）。 */
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .14),
    0 2px 6px -2px rgba(0, 0, 0, .45);
  transition: transform .16s ease;
}
.ns-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ns-initial {
  font-family: var(--font-serif, "Songti SC", "Noto Serif SC", Georgia, serif);
  font-size: 34px;
  font-weight: 300;
  color: rgba(240, 246, 255, .50);
  letter-spacing: .06em;
  text-shadow: 0 1px 0 rgba(0, 0, 0, .35);
  user-select: none;
}
.ns-card:active .ns-cover { transform: scale(.97); }
.ns-card.is-picked .ns-cover { transform: scale(.93); }

.ns-meta { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ns-title {
  font-size: 14px;
  line-height: 1.32;
  /* 跟随主题：项目有多套 token（--ls-* / --lj-* / --dp-*），用 inherit 最稳 */
  color: inherit;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  /* v2.46.378：固定两行高度。书名有长有短，不占满两行时整排书会参差不齐
     （截图里第三列书名换行、下面多一行，第二排就被顶上去了） */
  min-height: 2.64em;
}
.ns-sub {
  font-size: 12px;
  opacity: .5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 解析中角标 */
.ns-flag {
  position: absolute;
  left: 0;
  bottom: 0;
  z-index: 2;
  padding: 2px 6px;
  font-size: 10px;
  color: #fff;
  background: rgba(30, 26, 20, .5);
  border-radius: 0 6px 0 6px;
}

/* 收藏星：番茄没有，但收藏是本站功能 —— 做得很淡，已收藏才实心金 */
.ns-star {
  z-index: 3;
  position: absolute;
  top: 3px;
  right: 3px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  opacity: .42;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, .35));
  transition: opacity .16s ease;
}
.ns-star.on { opacity: 1; color: #ffd76e; }

/* 选择态勾选圈 */
.ns-tick {
  z-index: 3;
  position: absolute;
  top: 5px;
  right: 5px;
  width: 19px;
  height: 19px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, .9);
  background: rgba(0, 0, 0, .22);
  color: #fff;
}
.ns-tick.on { background: #d9534f; border-color: #d9534f; }

/* 选择态：番茄只加勾选圈，不把整面墙压灰（压灰会像「全部禁用」）。
   选中项用一圈红描边 + 实心勾，扫一眼就知道选了哪几本。 */
.novel-shelf.is-selecting .ns-card.is-picked .ns-cover {
  outline: 2px solid #d9534f;
  outline-offset: 2px;
}

/* 书架模式（手机）：viewport 被切成 device-width 后侧栏会把内容挤没，直接隐藏。
   底部 Tab 栏保留（番茄书架也有底部导航）。
   —— 原来这里还有 .tab-bar / .app-tabbar 两条，全项目根本没有这两个类，是死规则，已删。 */
:global(body.novel-shelf-mode .dsb),
:global(body.novel-shelf-mode .dsb-open-fab) {
  display: none !important;
}
/* 🔴 v2.46.325：原来写的是 `margin: 0 -40px`（外扩 40px 抵消旧布局的侧栏留白）。
   桌面版改版后外层 padding 换成了页面级 40px / 手机端 16px 两套，写死 -40 就过头了 ——
   夜星截图里三列书墙比屏幕还宽，最左最右各被切掉一截，「都挤到边缘了」。

   改用**满宽出血**公式，它对外层 padding 免疫：
     margin-left: calc(50% - 50vw)
   因为 50% 取的是父级**内容宽**的一半，(父宽-padding)/2 - 屏宽/2 恰好 = -padding。
   外层是 16 还是 40、以后改成多少，都不用再来改这里。 */
.manage-pane.is-shelf-pane {
  width: 100vw;
  max-width: 100vw;
  margin-left: calc(50% - 50vw);
  margin-right: calc(50% - 50vw);
  padding: 0 16px !important;
  box-sizing: border-box;
}
/* 宽屏（折叠屏展开 / 平板横屏）三列会被拉成巨幅海报，加列数而不是加卡宽 */
@media (min-width: 620px) {
  .novel-shelf { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (min-width: 860px) {
  .novel-shelf { grid-template-columns: repeat(5, minmax(0, 1fr)); }
}
</style>
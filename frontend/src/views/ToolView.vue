<template>
  <IslandInnerBase type="tool" title="工具" subtitle="机关百变">
    <!-- 管理表格（默认进入即管理页） -->
    <div class="manage-pane">
      <!-- v2.46.159：工具栏统一 PageToolbar，主操作走 #actions 自动贴右 -->
      <PageToolbar>
        <SearchField v-model="keyword" placeholder="搜索名称/描述" width="220px" @search="doSearch" />
        <span v-if="keyword" class="search-count">匹配 {{ filteredRows.length }} 条</span>
        <el-button v-if="keyword" size="small" plain @click="keyword = ''">清空筛选</el-button>
        <!-- v2.40.18：下架的工具默认不显示（如已归入通讯录的「人脉图谱」），
             需要管理时再勾上；此前下架项照样列在表里，只是多个「下架」标记 -->
        <el-checkbox v-model="showDisabled" size="small">显示已下架（{{ disabledCount }}）</el-checkbox>
        <el-button type="danger" plain size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
          批量删除<span v-if="selectedRows.length">（{{ selectedRows.length }}）</span>
        </el-button>
        <template #actions>
          <IconButton icon="plus" label="添加工具" variant="primary" @click="openDialog()" />
        </template>
      </PageToolbar>
      <el-table
        ref="tableRef"
        :data="pagedRows"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="onSelectionChange"
        :selectable="row => row.kind !== 'builtin'"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column label="名称" min-width="150">
          <template #default="{ row }">
            <!-- 名称 + 小标识同一行（v2.46.145）：标签原来跟在文本后面，列一窄就折到第二行、
                 每行凭空多出一截高度。改成 nowrap 的 flex 行 + 迷你 chip，只占宽度不占行高。 -->
            <span class="name-cell">
              <span class="icon-cell"><AppIcon :icon="row.icon || '🔧'" :size="16" /></span>
              <span class="name-text" :title="row.title">{{ row.title }}</span>
              <el-tag v-if="row.kind === 'builtin'" size="small" type="warning" effect="plain" class="kind-tag">内置</el-tag>
              <el-tag v-if="!row.is_enabled" size="small" type="info" effect="plain" class="kind-tag">下架</el-tag>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column label="链接(url)" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.kind === 'builtin'" class="route-cell">{{ row.url }}</span>
            <a v-else-if="row.url" :href="row.url" target="_blank" rel="noopener noreferrer" class="file-link">{{ row.url }}</a>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="排序" width="120" align="center">
          <template #default="{ row }">
            <el-button size="small" text :disabled="isFirst(row)" @click="move(row, -1)"><AppIcon icon="↑" :size="14" /></el-button>
            <el-button size="small" text :disabled="isLast(row)" @click="move(row, 1)"><AppIcon icon="↓" :size="14" /></el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96" align="center">
          <template #default="{ row }">
            <el-switch v-model="row._enabled" size="small" @change="toggleEnabled(row, $event)" />
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="130">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <!-- 使用＝打开工具本体（内置走模块路由 / 外链走站内详情内嵌页），
                 与「编辑」区分开：以前只有编辑删除，没有任何使用入口 -->
            <!-- v2.46.157：行内动作收敛到 OpsCell（图标化/禁用/危险色一处定义） -->
            <OpsCell :row="row" :actions="opsActions" />
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-if="!loading && filteredRows.length === 0" size="sm" title="暂无工具" description="调整筛选条件，或到管理后台添加工具" />
      <div v-else class="pager-wrap">
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

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="showDialog" :title="editId ? '编辑工具' : '添加工具'" width="460px" append-to-body>
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.title" placeholder="工具名称" /></el-form-item>
        <el-form-item label="图标"><el-input v-model="form.icon" placeholder="emoji或图标名（可选）" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" placeholder="简要描述（可选）" /></el-form-item>
        <el-form-item label="链接">
          <el-input v-model="form.url" :disabled="form.kind === 'builtin'" :placeholder="form.kind === 'builtin' ? '内置工具路径不可修改' : 'https://...'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
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
defineOptions({ name: 'ToolView' })
import { onMounted, ref, computed, watch } from 'vue'
import { usePagedList } from '@/composables/usePagedList'
import { fmtDate } from '@/utils/format'
import PageToolbar from '@/components/common/PageToolbar.vue'
import SearchField from '@/components/common/SearchField.vue'
import { useRouter } from 'vue-router'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import EmptyState from '@/components/EmptyState.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import IconButton from '@/components/common/IconButton.vue'
import OpsCell from '@/components/common/OpsCell.vue'
import { ElMessage } from 'element-plus'
import { useToolStore } from '@/stores/tool'
import { getToolList, createTool, updateTool, deleteTool } from '@/api/tool'

const router = useRouter()
const toolStore = useToolStore()

const showDialog = ref(false)
const editId = ref(null)
const keyword = ref('')
const form = ref({ title: '', icon: '', description: '', url: '', kind: 'external' })

// 管理数据（全部含下架，客户端分页）
const rows = ref([])
const loading = ref(false)
// 工具已增至 20+，默认一页显示 24 条，避免新工具被挤到第 2、3 页看不见
// （分页状态由 usePagedList 统一管理，见下方 filteredRows 之后）
// 是否显示已下架的工具（默认否：下架 = 从工具模块撤下，但数据留着便于恢复）
const showDisabled = ref(false)
const disabledCount = computed(() => rows.value.filter(r => !r.is_enabled).length)

const visibleRows = computed(() =>
  showDisabled.value ? rows.value : rows.value.filter(r => r.is_enabled)
)

const filteredRows = computed(() => {
  if (!keyword.value) return visibleRows.value
  const q = keyword.value.toLowerCase()
  return visibleRows.value.filter(r => (r.title || '').toLowerCase().includes(q) || (r.description || '').toLowerCase().includes(q))
})
/* v2.46.161：分页状态统一走 usePagedList（自带越界修正：删光最后一页会退回上一页） */
const { page, pageSize, total, paged: pagedRows, sizes, onPageChange, onSizeChange } = usePagedList(
  filteredRows,
  { defaultSize: 24 }
)
// 切换「显示已下架」后行数会变，页码归位避免停在空白页
watch(showDisabled, () => { page.value = 1 })

async function loadAll() {
  loading.value = true
  try {
    const res = await getToolList({ size: 500 })
    rows.value = await Promise.all((res.data.list || []).map(async r => ({ ...r, _enabled: !!r.is_enabled })))
  } finally {
    loading.value = false
  }
}
async function reloadAll() {
  await loadAll()
  await toolStore.fetchList({ enabled_only: 1, size: 100 })
}

onMounted(() => reloadAll())

async function doSearch() {
  page.value = 1
}

/* 使用（操作列入口）：
   - 内置工具：url 就是站内路径（如 /finance），直接 push 对应模块
   - 外链工具：进站内详情页 /tool/:id（详情页内嵌 iframe，并留「在新标签打开」兜底） */
function go(item) {
  if (item.kind === 'builtin') {
    if (!item.url) { ElMessage.warning('该内置工具未配置路径'); return }
    router.push(item.url)
    return
  }
  if (!item.url) { ElMessage.warning('该工具未配置链接，先「编辑」补上'); return }
  router.push('/tool/' + item.id)
}

function openDialog(item) {
  editId.value = item ? item.id : null
  form.value = {
    title: item?.title || '',
    icon: item?.icon || '',
    description: item?.description || '',
    url: item?.url || '',
    kind: item?.kind || 'external'
  }
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
  editId.value = null
  form.value = { title: '', icon: '', description: '', url: '', kind: 'external' }
}

async function handleSave() {
  if (!form.value.title) { ElMessage.warning('请输入名称'); return }
  if (form.value.kind !== 'builtin' && !form.value.url) { ElMessage.warning('请输入链接'); return }
  try {
    if (editId.value) {
      await updateTool(editId.value, { title: form.value.title, icon: form.value.icon, description: form.value.description, url: form.value.url })
      ElMessage.success('更新成功')
    } else {
      await createTool({ title: form.value.title, icon: form.value.icon, description: form.value.description, url: form.value.url })
      ElMessage.success('添加成功')
    }
    closeDialog()
    reloadAll()
  } catch {
    // 错误已由api拦截器处理
  }
}

/* ---- 排序 ---- */
const orderedRows = computed(() => [...rows.value].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id))
function isFirst(row) { return orderedRows.value[0]?.id === row.id }
function isLast(row) { return orderedRows.value[orderedRows.value.length - 1]?.id === row.id }
async function move(row, dir) {
  const list = orderedRows.value
  const idx = list.findIndex(r => r.id === row.id)
  const peer = list[idx + dir]
  if (!peer) return
  const a = row.sort_order, b = peer.sort_order
  try {
    await Promise.all([updateTool(row.id, { sort_order: b }), updateTool(peer.id, { sort_order: a })])
    ElMessage.success('已调整顺序')
    reloadAll()
  } catch { /* 拦截器处理 */ }
}

/* ---- 上下架 ---- */
async function toggleEnabled(row, val) {
  try {
    await updateTool(row.id, { is_enabled: val ? 1 : 0 })
    ElMessage.success(val ? '已上架' : '已下架')
    reloadAll()
  } catch {
    row._enabled = !!row.is_enabled
  }
}

/* 行内动作清单（模板只声明，不存在于模板里，便于统一改图标/文案/权限） */
const opsActions = [
  { icon: 'play', label: '使用', onClick: go },
  { icon: 'edit', label: '编辑', onClick: openDialog },
  { icon: 'trash', label: '删除', danger: true, disabled: (r) => r.kind === 'builtin', onClick: handleDelete },
]

/* ---- 删除（内置禁删） ---- */
const showDelete = ref(false)
const deleting = ref(false)
const deleteId = ref(null)
const deleteName = ref('')

function handleDelete(row) {
  if (row.kind === 'builtin') { ElMessage.warning('内置工具不可删除，可改为下架'); return }
  deleteId.value = row.id
  deleteName.value = row.title || '这个工具'
  showDelete.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    await deleteTool(deleteId.value)
    ElMessage.success('删除成功')
    showDelete.value = false
    reloadAll()
  } catch {
    // 拦截器处理
  } finally {
    deleting.value = false
  }
}

/* ---- 批量删除 ---- */
const tableRef = ref(null)
const selectedRows = ref([])
const showBatchDelete = ref(false)
const batchDeleting = ref(false)

function onSelectionChange(sel) { selectedRows.value = sel }
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
      await deleteTool(id)
    }
    ElMessage.success(`已删除 ${ids.length} 项`)
    showBatchDelete.value = false
    tableRef.value?.clearSelection()
    reloadAll()
  } catch {
    // 拦截器处理
  } finally {
    batchDeleting.value = false
  }
}

/* v2.46.160：统一到 utils/format.js */
function formatTime(timeStr) {
  return fmtDate(timeStr, '-')
}
</script>

<style scoped>
.tool-cards { display: flex; flex-direction: column; gap: 14px; }

.tool-card {
  display: flex; align-items: center; gap: 20px; padding: 18px 22px;
  background: linear-gradient(165deg, rgba(255,255,255,.03), rgba(255,255,255,0) 55%), var(--ls-glass);
  border: 1px solid var(--ls-line); border-radius: var(--radius-sm);
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
  backdrop-filter: saturate(150%) blur(10px); -webkit-backdrop-filter: saturate(150%) blur(10px);
  transition: all var(--transition); cursor: pointer;
}
.tool-card:hover { background: var(--ls-paper-2); border-color: var(--ls-line-strong); transform: translateX(8px); }

.tool-icon {
  width: 52px; height: 52px;
  background: linear-gradient(135deg, #a5825a 0%, rgba(196,154,108,.3) 100%);
  border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center;
  font-size: 26px; flex-shrink: 0;
}
.tool-info { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.tool-name { font-family: var(--font-serif); color: var(--ls-text); font-size: 16px; }
.tool-desc { color: var(--ls-text-2); font-size: 13px; }
.tool-actions { flex-shrink: 0; }

.tool-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 50px 20px; gap: 14px; color: var(--ls-text-3); }

.manage-pane {
  background: var(--ls-glass); backdrop-filter: saturate(160%) blur(14px); -webkit-backdrop-filter: saturate(160%) blur(14px);
  border: 1px solid var(--ls-line); border-radius: var(--radius); padding: 30px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}
.manage-toolbar { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
.manage-toolbar :deep(.el-input__wrapper) { background: var(--ls-paper-2); box-shadow: inset 0 0 0 1px var(--ls-line); }
.search-count { color: var(--ls-text-3); font-size: 13px; }
.empty { text-align: center; padding: 40px; color: var(--ls-text-3); font-size: 14px; }
.pager-wrap { display: flex; justify-content: flex-end; margin-top: 18px; }
.pager-wrap :deep(.el-pagination) { --el-pagination-bg-color: transparent; }
.icon-cell { margin-right: 8px; }
.name-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
.name-text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 迷你标识：不换行、不吃行高，只占一点宽度 */
.tl-toolbar-spacer { flex: 1 1 auto; min-width: 8px; }
.kind-tag {
  flex: none;
  height: 17px;
  line-height: 15px;
  padding: 0 5px;
  font-size: 10.5px;
  border-radius: 5px;
}
.file-link { color: var(--ls-dai); text-decoration: none; word-break: break-all; }
.file-link:hover { text-decoration: underline; }
.route-cell { color: var(--ls-text-2); font-family: monospace; font-size: 12px; }

.manage-pane :deep(.el-table) {
  --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent; --el-table-border-color: var(--ls-line);
  --el-table-header-text-color: var(--ls-text-2); --el-table-text-color: var(--ls-text);
}
</style>
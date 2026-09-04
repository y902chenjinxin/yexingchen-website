<template>
  <IslandInnerBase type="tool" title="工具" subtitle="机关百变">
    <template #toolbar>
      <el-button :type="manage ? 'primary' : 'default'" size="small" plain @click="manage = !manage">
        {{ manage ? '返回卡片' : '管理' }}
      </el-button>
      <el-button v-if="manage" type="primary" size="small" @click="openDialog()">添加</el-button>
    </template>

    <!-- 浏览模式：工具卡片列表 -->
    <div v-show="!manage" class="tool-cards">
      <div
        v-for="item in toolStore.list"
        :key="item.id"
        class="tool-card"
        @click="go(item)"
      >
        <div class="tool-icon">{{ item.icon || '🔧' }}</div>
        <div class="tool-info">
          <span class="tool-name">{{ item.title || '无名工具' }}</span>
          <span class="tool-desc">{{ item.description || '暂无描述' }}</span>
        </div>
        <div class="tool-actions">
          <el-button size="small" type="primary" @click.stop="go(item)">使用</el-button>
        </div>
      </div>

      <div v-if="!toolStore.loading && toolStore.list.length === 0" class="tool-empty">
        <span class="empty-icon">⚙️</span>
        <span class="empty-text">暂无可用的工具</span>
      </div>
    </div>

    <!-- 管理模式：表格（统一分页 10/20/50） -->
    <div v-show="manage" class="manage-pane">
      <div class="manage-toolbar">
        <el-input
          v-model="keyword"
          size="small"
          clearable
          placeholder="搜索名称/描述"
          style="width: 220px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" size="small" plain @click="doSearch">查询</el-button>
        <span v-if="keyword" class="search-count">匹配 {{ filteredRows.length }} 条</span>
        <el-button v-if="keyword" size="small" plain @click="keyword = ''">清空筛选</el-button>
        <el-button v-if="selectedRows.length" type="danger" size="small" @click="handleBatchDelete">批量删除（{{ selectedRows.length }}）</el-button>
      </div>
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
            <span class="icon-cell">{{ row.icon || '🔧' }}</span>{{ row.title }}
            <el-tag v-if="row.kind === 'builtin'" size="small" type="warning" effect="plain" class="kind-tag">内置</el-tag>
            <el-tag v-if="!row.is_enabled" size="small" type="info" effect="plain" class="kind-tag">下架</el-tag>
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
            <el-button size="small" text :disabled="isFirst(row)" @click="move(row, -1)">↑</el-button>
            <el-button size="small" text :disabled="isLast(row)" @click="move(row, 1)">↓</el-button>
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
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="openDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" :disabled="row.kind === 'builtin'" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && filteredRows.length === 0" class="empty">暂无数据</div>
      <div v-else class="pager-wrap">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="filteredRows.length"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50]"
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
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useToolStore } from '@/stores/tool'
import { getToolList, createTool, updateTool, deleteTool } from '@/api/tool'

const router = useRouter()
const toolStore = useToolStore()

const manage = ref(false)
const showDialog = ref(false)
const editId = ref(null)
const keyword = ref('')
const form = ref({ title: '', icon: '', description: '', url: '', kind: 'external' })

// 管理数据（全部含下架，客户端分页）
const rows = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)

const filteredRows = computed(() => {
  if (!keyword.value) return rows.value
  const q = keyword.value.toLowerCase()
  return rows.value.filter(r => (r.title || '').toLowerCase().includes(q) || (r.description || '').toLowerCase().includes(q))
})
const pagedRows = computed(() =>
  filteredRows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value)
)

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

function go(item) {
  if (item.kind === 'builtin') router.push(item.url)
  else router.push('/tool/' + item.id)
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

/* ---- 分页 ---- */
function onSizeChange(sz) { pageSize.value = sz; page.value = 1 }
function onPageChange(p) { page.value = p }

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
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
.kind-tag { margin-left: 6px; }
.file-link { color: var(--ls-dai); text-decoration: none; word-break: break-all; }
.file-link:hover { text-decoration: underline; }
.route-cell { color: var(--ls-text-2); font-family: monospace; font-size: 12px; }

.manage-pane :deep(.el-table) {
  --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent; --el-table-border-color: var(--ls-line);
  --el-table-header-text-color: var(--ls-text-2); --el-table-text-color: var(--ls-text);
}
</style>
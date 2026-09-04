<template>
  <IslandInnerBase type="log" title="日志" subtitle="留痕存迹，事事有迹可循">
    <template #toolbar>
      <el-button :type="manage ? 'primary' : 'default'" size="small" plain @click="manage = !manage">
        {{ manage ? '返回时间线' : '管理' }}
      </el-button>
    </template>

    <!-- 浏览模式：操作时间线 -->
    <div v-show="!manage" class="log-timeline">
      <div v-if="loading" class="log-placeholder">加载中…</div>
      <div v-else-if="logs.length === 0" class="log-placeholder">
        <div class="log-empty-icon">📝</div>
        <div class="log-empty-text">暂无操作日志</div>
      </div>
      <template v-else>
        <div v-for="log in logs" :key="log.id" class="timeline-item">
          <div class="timeline-dot" :class="getActionClass(log.action)"></div>
          <div class="timeline-content">
            <div class="log-header">
              <span class="log-user">{{ log.user_email }}</span>
              <span class="log-action" :class="getActionClass(log.action)">{{ getActionText(log.action) }}</span>
              <span v-if="log.target_type" class="log-target">【{{ log.target_type }}】</span>
            </div>
            <div class="log-detail" v-if="log.detail">{{ log.detail }}</div>
            <div class="log-footer">
              <span class="log-ip" v-if="log.ip_address">IP: {{ log.ip_address }}</span>
              <span class="log-time">{{ formatTime(log.created_at) }}</span>
            </div>
          </div>
        </div>
        <div v-if="total > size" class="log-pager">
          <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="size"
            v-model:current-page="page" @current-change="fetchData" />
        </div>
      </template>
    </div>

    <!-- 管理模式：表格（操作日志留痕，只读展示 + 批量删除/清空） -->
    <div v-show="manage" class="manage-pane">
      <div class="manage-toolbar">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          style="width: 260px"
          value-format="YYYY-MM-DD"
        />
        <el-select v-model="actionFilter" placeholder="动作" clearable size="small" style="width: 120px">
          <el-option v-for="a in actionOptions" :key="a.value" :label="a.label" :value="a.value" />
        </el-select>
        <el-input
          v-model="keyword"
          size="small"
          clearable
          placeholder="搜详情 / 类型 / 动作"
          style="width: 220px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" size="small" plain @click="doSearch">查询</el-button>
        <el-button v-if="hasFilter" size="small" plain @click="clearFilters">清空筛选</el-button>
        <div class="toolbar-spacer"></div>
        <el-button v-if="selectedRows.length" type="danger" size="small" @click="openBatchDelete">
          批量删除（{{ selectedRows.length }}）
        </el-button>
        <el-button type="warning" size="small" plain @click="openClear">清空日志</el-button>
      </div>

      <el-table
        ref="tableRef"
        :data="logs"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column label="时间" width="165">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="用户" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.user_email || '-' }}</template>
        </el-table-column>
        <el-table-column label="动作" width="110">
          <template #default="{ row }">
            <span class="action-tag" :class="getActionClass(row.action)">{{ getActionText(row.action) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="目标类型" width="110">
          <template #default="{ row }">{{ row.target_type || '-' }}</template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
        <el-table-column label="IP" width="130">
          <template #default="{ row }">{{ row.ip_address || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" type="danger" plain @click="openDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && total === 0" class="log-empty">暂无操作日志</div>
      <div v-else class="log-pager">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-size="size"
          :page-sizes="[10, 20, 50]"
          v-model:current-page="page"
          @size-change="onSizeChange"
          @current-change="fetchData"
        />
      </div>
    </div>

    <!-- 单条删除确认（页内） -->
    <el-dialog v-model="showDelete" title="删除确认" width="360px" append-to-body>
      <p>确定删除这条操作日志吗？删除后不可恢复。</p>
      <template #footer>
        <el-button @click="showDelete = false">取消</el-button>
        <el-button type="danger" :loading="deleting" @click="confirmDelete">删除</el-button>
      </template>
    </el-dialog>

    <!-- 批量删除确认（页内） -->
    <el-dialog v-model="showBatchDelete" title="批量删除" width="360px" append-to-body>
      <p>确定删除选中的 <b>{{ selectedRows.length }}</b> 条操作日志吗？此操作不可恢复。</p>
      <template #footer>
        <el-button @click="showBatchDelete = false">取消</el-button>
        <el-button type="danger" :loading="batchDeleting" @click="confirmBatchDelete">一键删除</el-button>
      </template>
    </el-dialog>

    <!-- 清空确认（页内） -->
    <el-dialog v-model="showClear" title="清空日志" width="380px" append-to-body>
      <p>确定清空{{ clearScope }}吗？此操作不可恢复。</p>
      <template #footer>
        <el-button @click="showClear = false">取消</el-button>
        <el-button type="danger" :loading="clearing" @click="confirmClear">清空</el-button>
      </template>
    </el-dialog>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getLogs, deleteLogs, clearLogs } from '@/api/log'

const manage = ref(false)
const logs = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)

const dateRange = ref(null)
const actionFilter = ref('')
const keyword = ref('')

const actionOptions = [
  { label: '登录', value: 'login' },
  { label: '登出', value: 'logout' },
  { label: '修改密码', value: 'password_change' },
  { label: '上传', value: 'upload' },
  { label: '编辑', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '新建', value: 'create' },
  { label: '恢复', value: 'restore' }
]

const hasFilter = computed(() => {
  return !!(dateRange.value?.length || actionFilter.value || keyword.value)
})

function fmtDT(d) {
  const dt = new Date(d)
  const p = (n) => String(n).padStart(2, '0')
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())}T${p(dt.getHours())}:${p(dt.getMinutes())}:${p(dt.getSeconds())}`
}

function buildParams() {
  const params = { page: page.value, size: size.value }
  if (actionFilter.value) params.action = actionFilter.value
  if (keyword.value.trim()) params.q = keyword.value.trim()
  if (dateRange.value?.length === 2) {
    params.start = `${dateRange.value[0]}T00:00:00`
    params.end = `${dateRange.value[1]}T23:59:59`
  }
  return params
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getLogs(buildParams())
    logs.value = res.data.list || []
    total.value = res.data.total || 0
  } catch {
    /* 错误已由 api 拦截器处理 */
  } finally {
    loading.value = false
  }
}

function doSearch() {
  page.value = 1
  fetchData()
}

function clearFilters() {
  dateRange.value = null
  actionFilter.value = ''
  keyword.value = ''
  page.value = 1
  tableRef.value?.clearSelection()
  fetchData()
}

function onSizeChange(sz) {
  size.value = sz
  page.value = 1
  fetchData()
}

/* ---- 删除 ---- */
const tableRef = ref(null)
const selectedRows = ref([])
const showDelete = ref(false)
const deleting = ref(false)
const deleteId = ref(null)
const showBatchDelete = ref(false)
const batchDeleting = ref(false)

function onSelectionChange(sel) { selectedRows.value = sel }

function openDelete(row) {
  deleteId.value = row.id
  showDelete.value = true
}
async function confirmDelete() {
  deleting.value = true
  try {
    await deleteLogs([deleteId.value])
    ElMessage.success('删除成功')
    showDelete.value = false
    fetchData()
  } catch { /* 拦截器处理 */ } finally { deleting.value = false }
}

function openBatchDelete() {
  if (!selectedRows.value.length) return
  showBatchDelete.value = true
}
async function confirmBatchDelete() {
  const ids = selectedRows.value.map(r => r.id)
  if (!ids.length) return
  batchDeleting.value = true
  try {
    const res = await deleteLogs(ids)
    ElMessage.success(`已删除 ${res.data.deleted ?? ids.length} 条`)
    showBatchDelete.value = false
    tableRef.value?.clearSelection()
    fetchData()
  } catch { /* 拦截器处理 */ } finally { batchDeleting.value = false }
}

/* ---- 清空 ---- */
const showClear = ref(false)
const clearing = ref(false)
const clearScope = computed(() => {
  if (dateRange.value?.length === 2) return `${dateRange.value[0]} 至 ${dateRange.value[1]} 的操作日志`
  if (hasFilter.value) return '当前筛选范围内的操作日志'
  return '全部操作日志'
})
function openClear() {
  showClear.value = true
}
async function confirmClear() {
  clearing.value = true
  try {
    const payload = {}
    if (dateRange.value?.length === 2) {
      payload.start = `${dateRange.value[0]}T00:00:00`
      payload.end = `${dateRange.value[1]}T23:59:59`
    }
    const res = await clearLogs(payload)
    ElMessage.success(`已清空 ${res.data.deleted ?? 0} 条日志`)
    showClear.value = false
    page.value = 1
    tableRef.value?.clearSelection()
    fetchData()
  } catch { /* 拦截器处理 */ } finally { clearing.value = false }
}

/* ---- 展示辅助 ---- */
function getActionClass(action) {
  const map = {
    upload: 'action-upload',
    create: 'action-upload',
    delete: 'action-delete',
    update: 'action-update',
    login: 'action-login',
    logout: 'action-logout',
    password_change: 'action-update',
    restore: 'action-login'
  }
  return map[action] || ''
}
function getActionText(action) {
  const map = {
    upload: '上传', create: '新建', delete: '删除', update: '编辑',
    login: '登录', logout: '登出', password_change: '修改密码', restore: '恢复'
  }
  return map[action] || action
}
function formatTime(timeStr) {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

onMounted(fetchData)
</script>

<style scoped>
/* 浏览：时间线 */
.log-timeline { position: relative; }
.log-timeline::before { content: ''; position: absolute; left: 15px; top: 0; bottom: 0; width: 2px; background: rgba(122, 155, 124, 0.25); }
.log-placeholder { text-align: center; padding: 60px; color: var(--ls-text-3); }
.log-empty-icon { font-size: 54px; margin-bottom: 14px; }
.log-empty-text { font-size: 14px; letter-spacing: .1em; }
.timeline-item { display: flex; gap: 20px; margin-bottom: 18px; padding-left: 40px; position: relative; }
.timeline-dot { position: absolute; left: 8px; top: 6px; width: 16px; height: 16px; border-radius: 50%; background: var(--ls-jade, #6aa98f); border: 3px solid #141b22; }
.timeline-dot.action-upload { background: var(--ls-accent, #6aa98f); }
.timeline-dot.action-delete { background: #c2646a; }
.timeline-dot.action-update { background: #c2a26b; }
.timeline-dot.action-login { background: #6aa98f; }
.timeline-content {
  flex: 1; background: var(--ls-glass); border: 1px solid var(--ls-line); border-radius: 10px;
  padding: 12px 16px; backdrop-filter: saturate(150%) blur(10px); -webkit-backdrop-filter: saturate(150%) blur(10px);
}
.log-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.log-user { color: var(--ls-text); font-size: 14px; font-weight: 500; }
.log-target { color: var(--ls-text-3); font-size: 13px; }
.log-detail { color: var(--ls-text-2); font-size: 13px; margin-bottom: 8px; }
.log-footer { display: flex; justify-content: space-between; font-size: 12px; color: var(--ls-text-3); }

/* 管理：表格面板 */
.manage-pane {
  background: var(--ls-glass); backdrop-filter: saturate(160%) blur(14px); -webkit-backdrop-filter: saturate(160%) blur(14px);
  border: 1px solid var(--ls-line); border-radius: 14px; padding: 24px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}
.manage-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
.manage-toolbar :deep(.el-input__wrapper),
.manage-toolbar :deep(.el-date-editor) { background: var(--ls-paper-2); box-shadow: inset 0 0 0 1px var(--ls-line); }
.toolbar-spacer { flex: 1; }
.log-empty { text-align: center; padding: 40px; color: var(--ls-text-3); font-size: 14px; }
.log-pager { display: flex; justify-content: flex-end; margin-top: 18px; }
.log-pager :deep(.el-pagination) { --el-pagination-bg-color: transparent; }

.action-tag { font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.action-upload { background: rgba(106, 169, 143, 0.18); color: #7cc2a6; }
.action-delete { background: rgba(194, 100, 106, 0.18); color: #e0858a; }
.action-update { background: rgba(194, 162, 107, 0.18); color: #dbbe85; }
.action-login { background: rgba(106, 169, 143, 0.18); color: #7cc2a6; }
.action-logout { background: rgba(139, 115, 85, 0.16); color: #b8956a; }
.log-timeline .action-upload { background: rgba(106,169,143,.2); color: #7cc2a6; }
.log-timeline .action-delete { background: rgba(194,100,106,.2); color: #e0858a; }
.log-timeline .action-update { background: rgba(194,162,107,.2); color: #dbbe85; }
.log-timeline .action-login { background: rgba(106,169,143,.2); color: #7cc2a6; }
.log-timeline .action-logout { background: rgba(139,115,85,.2); color: #b8956a; }

.manage-pane :deep(.el-table) {
  --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent; --el-table-border-color: var(--ls-line);
  --el-table-header-text-color: var(--ls-text-2); --el-table-text-color: var(--ls-text);
}
</style>
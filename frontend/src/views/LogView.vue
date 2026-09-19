<template>
  <IslandInnerBase type="log" title="日志" subtitle="留痕存迹，事事有迹可循">
    <template #toolbar>
      <el-button type="warning" size="small" plain @click="openClear">清空日志</el-button>
    </template>

    <!-- 时间线视图（直接进入即此视图，无中间层） -->
    <div class="log-timeline">
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
import { ref, onMounted } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'
import { getLogs, clearLogs } from '@/api/log'

const logs = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)

const loading = ref(false)

const showClear = ref(false)
const clearing = ref(false)
const clearScope = ref('全部日志')

const ACTION_LABEL = {
  login: '登录',
  logout: '登出',
  create: '新建',
  update: '更新',
  delete: '删除',
  upload: '上传',
  download: '下载',
  approve: '通过',
  reject: '驳回',
}

function getActionText(action) {
  return ACTION_LABEL[action] || action || '-'
}

function getActionClass(action) {
  return `action-${action || 'unknown'}`
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getLogs({ page: page.value, size: size.value })
    const data = res.data || {}
    logs.value = data.list || []
    total.value = data.total || 0
  } catch (e) {
    /* 静默 */
  } finally {
    loading.value = false
  }
}

function openClear() {
  clearScope.value = '全部日志'
  showClear.value = true
}

async function confirmClear() {
  clearing.value = true
  try {
    await clearLogs()
    ElMessage.success('已清空')
    showClear.value = false
    page.value = 1
    fetchData()
  } catch {
    /* 错误已由api拦截器处理 */
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.log-timeline {
  position: relative;
  padding: 20px 0;
}
.log-timeline::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(122, 155, 124, 0.25);
}

.log-placeholder {
  text-align: center;
  padding: 60px 20px;
  color: var(--ls-text-3);
  font-size: 14px;
}
.log-empty-icon { font-size: 48px; opacity: 0.5; margin-bottom: 12px; }
.log-empty-text { font-size: 13px; opacity: 0.7; }

.timeline-item {
  position: relative;
  padding: 10px 0 10px 50px;
  margin-bottom: 8px;
}

.timeline-dot {
  position: absolute;
  left: 8px;
  top: 14px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--ls-jade, #6aa98f);
  border: 3px solid var(--dp-bg);
}

.timeline-content {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: 8px;
  padding: 10px 14px;
  box-shadow: var(--dp-shadow);
}
.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.log-user { font-size: 13px; font-weight: 600; color: var(--dp-text); }
.log-action {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.log-target { font-size: 11px; color: var(--dp-text3); }
.log-detail {
  font-size: 13px;
  color: var(--dp-text2);
  margin: 4px 0;
  word-break: break-all;
}
.log-footer {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--dp-text3);
  margin-top: 6px;
}

.log-pager {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
.log-pager :deep(.el-pagination) { --el-pagination-bg-color: transparent; }

/* 动作颜色 */
.action-login { background: rgba(106, 169, 143, .18); color: #7cc2a6; }
.action-create { background: rgba(106, 169, 143, .18); color: #7cc2a6; }
.action-upload { background: rgba(106, 169, 143, .18); color: #7cc2a6; }
.action-delete { background: rgba(194, 100, 106, .18); color: #e0858a; }
.action-update { background: rgba(194, 162, 107, .18); color: #dbbe85; }
.action-logout { background: rgba(139, 115, 85, .16); color: #b8956a; }
.action-approve { background: rgba(106, 169, 143, .18); color: #7cc2a6; }
.action-reject { background: rgba(194, 100, 106, .18); color: #e0858a; }
.action-download { background: rgba(91, 107, 122, .18); color: #b8c5d4; }
.action-unknown { background: rgba(150, 150, 150, .2); color: #a8a8a8; }
</style>
<template>
  <div class="island-page">
    <header class="island-header">
      <div class="header-left">
        <span class="back-btn" @click="router.push('/home')">← 返回</span>
        <span class="island-title">📝 日志岛</span>
      </div>
      <div class="header-right">
        <el-select v-model="filterType" placeholder="筛选类型" clearable style="width: 150px" @change="fetchData">
          <el-option label="上传" value="upload" />
          <el-option label="删除" value="delete" />
          <el-option label="更新" value="update" />
          <el-option label="登录" value="login" />
          <el-option label="登出" value="logout" />
          <el-option label="审批" value="approve" />
        </el-select>
      </div>
    </header>

    <main class="log-list">
      <div v-if="loading" class="loading-placeholder">加载中...</div>
      <div v-else-if="logs.length === 0" class="empty-placeholder">
        <div class="empty-icon">📝</div>
        <div class="empty-text">暂无操作日志</div>
      </div>
      <div v-else class="timeline">
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
      </div>
    </main>

    <div class="pagination-wrap" v-if="total > size">
      <el-pagination v-model:current-page="page" :page-size="size" :total="total" layout="prev, pager, next" @current-change="fetchData" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getLogs } from '@/api/log'

const router = useRouter()
const logs = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(50)
const loading = ref(false)
const filterType = ref('')

onMounted(() => { fetchData() })

async function fetchData() {
  loading.value = true
  try {
    const res = await getLogs({ page: page.value, size: size.value, target_type: filterType.value || undefined })
    logs.value = res.data.list
    total.value = res.data.total
  } catch { /* 错误已由api拦截器处理 */ }
  finally { loading.value = false }
}

function getActionClass(action) {
  const map = {
    upload: 'action-upload',
    delete: 'action-delete',
    update: 'action-update',
    login: 'action-login',
    logout: 'action-logout',
    approve: 'action-approve',
    reject: 'action-reject'
  }
  return map[action] || ''
}

function getActionText(action) {
  const map = {
    upload: '上传',
    delete: '删除',
    update: '更新',
    login: '登录',
    logout: '登出',
    approve: '审批通过',
    reject: '拒绝'
  }
  return map[action] || action
}

function formatTime(timeStr) {
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}
</script>

<style scoped>
.island-page { min-height: 100vh; background: linear-gradient(180deg, #F0F8F0 0%, #E5F0E5 100%); padding-bottom: 40px; }
.island-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: rgba(143, 188, 143, 0.2); border-bottom: 1px solid rgba(143, 188, 143, 0.3); }
.header-left { display: flex; align-items: center; gap: 20px; }
.back-btn { color: var(--color-log); cursor: pointer; font-size: 14px; }
.back-btn:hover { color: #6B9B6B; }
.island-title { font-family: var(--font-serif); font-size: 20px; color: var(--color-text); }
.header-right { display: flex; gap: 15px; }
.log-list { padding: 30px 40px; max-width: 900px; margin: 0 auto; }
.loading-placeholder, .empty-placeholder { text-align: center; padding: 60px; color: var(--color-text-secondary); }
.empty-icon { font-size: 60px; margin-bottom: 15px; }
.timeline { position: relative; }
.timeline::before { content: ''; position: absolute; left: 15px; top: 0; bottom: 0; width: 2px; background: rgba(143, 188, 143, 0.3); }
.timeline-item { display: flex; gap: 20px; margin-bottom: 20px; padding-left: 40px; position: relative; }
.timeline-dot { position: absolute; left: 8px; top: 5px; width: 16px; height: 16px; border-radius: 50%; background: var(--color-log); border: 3px solid #E5F0E5; }
.timeline-dot.action-upload { background: var(--color-log); }
.timeline-dot.action-delete { background: var(--color-danger); }
.timeline-dot.action-update { background: var(--color-gold); }
.timeline-dot.action-login, .timeline-dot.action-approve { background: #10B981; }
.timeline-content { flex: 1; background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(143, 188, 143, 0.2); border-radius: 8px; padding: 12px 15px; }
.log-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 5px; }
.log-user { color: var(--color-text); font-size: 14px; font-weight: 500; }
.log-action { font-size: 13px; padding: 2px 8px; border-radius: 4px; }
.action-upload { background: rgba(143, 188, 143, 0.2); color: var(--color-log); }
.action-delete { background: rgba(220, 107, 107, 0.2); color: var(--color-danger); }
.action-update { background: rgba(201, 169, 98, 0.2); color: var(--color-gold); }
.action-login, .action-approve { background: rgba(16, 185, 129, 0.2); color: #10B981; }
.action-logout, .action-reject { background: rgba(139, 115, 85, 0.2); color: #8B7375; }
.log-target { color: var(--color-text-secondary); font-size: 13px; }
.log-detail { color: var(--color-text); font-size: 13px; margin-bottom: 8px; }
.log-footer { display: flex; justify-content: space-between; font-size: 12px; color: var(--color-text-secondary); }
.pagination-wrap { display: flex; justify-content: center; padding: 20px; }
@media (max-width: 768px) {
  .island-header { flex-direction: column; gap: 15px; padding: 15px 20px; }
  .log-list { padding: 20px; }
}
</style>
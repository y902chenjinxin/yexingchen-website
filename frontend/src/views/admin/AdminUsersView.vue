<template>
  <AdminLayout>
    <template #actions>
      <el-input
        v-model="searchQuery"
        placeholder="搜索邮箱"
        clearable
        style="width: 220px"
        @clear="fetchUsers"
        @keyup.enter="fetchUsers"
      >
        <template #append>
          <el-button :icon="Search" @click="fetchUsers" />
        </template>
      </el-input>
      <el-button type="primary" @click="showAddDialog = true">新增用户</el-button>
    </template>

    <section class="section">
      <div class="section-tip">用户列表与审批：审批新注册、修改角色 / 状态、重置密码、删除用户。</div>
      <el-table :data="filteredUsers" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)" size="small">{{ getRoleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="allowed_islands" label="可访问模块" min-width="200">
          <template #default="{ row }">
            <div class="island-tags">
              <el-tag v-for="island in getIslandList(row)" :key="island" size="small" type="info">
                {{ getIslandName(island) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="160">
          <template #default="{ row }">
            {{ row.last_login_at ? formatTime(row.last_login_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="160" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <!-- 按钮全部常显、单行居左；不用下拉，避免二次点击与列宽挤压 -->
            <div class="row-ops">
              <template v-if="row.status === 'pending'">
                <el-button size="small" type="primary" plain @click="handleCommand(row.id, 'approve')">审核通过</el-button>
                <el-button size="small" type="danger" plain @click="handleCommand(row.id, 'reject')">审核不通过</el-button>
              </template>
              <template v-else>
                <el-button size="small" @click="handleCommand(row.id, 'edit')">修改</el-button>
                <el-button size="small" @click="handleCommand(row.id, 'resetPwd')">重置密码</el-button>
                <el-button size="small" type="danger" plain @click="handleCommand(row.id, 'delete')">删除</el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && filteredUsers.length === 0" class="empty-placeholder">
        <div class="empty-icon">👥</div>
        <div class="empty-text">暂无用户</div>
      </div>
    </section>

    <!-- 编辑用户弹窗 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option v-for="r in roles" :key="r.code" :label="r.name" :value="r.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="可访问模块">
          <el-checkbox-group v-model="editForm.islands">
            <el-checkbox label="music">音乐</el-checkbox>
            <el-checkbox label="novel">小说</el-checkbox>
            <el-checkbox label="video">视频</el-checkbox>
            <el-checkbox label="diary">日志</el-checkbox>
            <el-checkbox label="tools">工具</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="showAddDialog" title="新增用户" width="470px">
      <el-form :model="addForm" label-width="96px">
        <el-form-item label="账号">
          <el-input v-model="addForm.email" placeholder="邮箱或任意账号，如 爸爸 / 13800138000" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="校验">
          <el-checkbox v-model="addForm.strict">启用严格校验</el-checkbox>
          <div class="form-tip">
            默认关闭：超管建号不套用公开注册的「邮箱格式 + 密码强度」规则，方便给家里人开简单账号。
            勾选后本次创建按公开注册同款规则校验。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddUser">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="showResetPwdDialog" title="重置用户密码" width="400px">
      <div v-if="resetPwdTarget" class="reset-target">将重置 <b>{{ resetPwdTarget.email }}</b> 的登录密码</div>
      <el-form label-width="80px">
        <el-form-item label="新密码">
          <el-input v-model="resetPwdForm.password" type="password" placeholder="请输入新密码" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="校验">
          <el-checkbox v-model="resetPwdForm.strict">启用严格校验</el-checkbox>
          <div class="form-tip">默认关闭：不强制密码强度，可直接设为家里人好记的简单密码。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResetPwdDialog = false">取消</el-button>
        <el-button type="primary" @click="handleResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getUserList, addUser, approveUser, rejectUser, updateUser, resetUserPassword, deleteUser,
} from '@/api/admin'
import { getRoleList } from '@/api/admin'
import AdminLayout from './AdminLayout.vue'

const users = ref([])
const roles = ref([])
const loading = ref(false)
const searchQuery = ref('')

const showEditDialog = ref(false)
const showAddDialog = ref(false)
const showResetPwdDialog = ref(false)
const editId = ref(null)
const resetPwdTarget = ref(null)
const editForm = ref({ role: '', status: 'pending', islands: [] })
const addForm = ref({ email: '', password: '', strict: false })
const resetPwdForm = ref({ password: '', strict: false })

const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value
  const q = searchQuery.value.toLowerCase()
  return users.value.filter(u => u.email.toLowerCase().includes(q))
})

const ROLE_LABEL = { super_admin: '超管', admin: '管理员', user: '普通用户' }
function getRoleText(r) { return ROLE_LABEL[r] || r || '-' }
function getRoleTagType(r) {
  if (r === 'super_admin') return 'danger'
  if (r === 'admin') return 'warning'
  return ''
}
function getStatusText(s) {
  return s === 'pending' ? '待审批' : s === 'approved' ? '已通过' : s === 'rejected' ? '已拒绝' : '-'
}
function getStatusType(s) {
  if (s === 'pending') return 'warning'
  if (s === 'approved') return 'success'
  if (s === 'rejected') return 'danger'
  return 'info'
}

const ISLAND_NAME = { music: '音乐', novel: '小说', video: '视频', diary: '日志', tools: '工具' }
function getIslandName(k) { return ISLAND_NAME[k] || k }
/* 容错：allowed_islands 理论上恒为字符串，但若为 null/非字符串，
   直接在模板里 .split 会抛错 → 单元格渲染失败 → 整行列错位（同角色管理那次事故） */
function getIslandList(row) {
  const raw = row?.allowed_islands
  if (Array.isArray(raw)) return raw.filter(Boolean)
  if (typeof raw !== 'string') return []
  return raw.split(',').map(s => s.trim()).filter(Boolean)
}

function formatTime(s) {
  if (!s) return '-'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUserList({ q: searchQuery.value })
    users.value = res.data?.list || []
  } catch {
    /* 错误已由 api 拦截器处理 */
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  try {
    const res = await getRoleList()
    roles.value = res.data?.list || []
  } catch { /* 静默 */ }
}

async function handleCommand(userId, cmd) {
  if (cmd === 'approve') {
    await approveUser(userId)
    ElMessage.success('已通过')
  } else if (cmd === 'reject') {
    await rejectUser(userId)
    ElMessage.success('已拒绝')
  } else if (cmd === 'edit') {
    openEdit(userId)
    return
  } else if (cmd === 'resetPwd') {
    openResetPwd(userId)
    return
  } else if (cmd === 'delete') {
    await ElMessageBox.confirm('确认删除该用户？此操作不可恢复。', '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await deleteUser(userId)
    ElMessage.success('已删除')
  }
  fetchUsers()
}

function openEdit(userId) {
  const u = users.value.find(x => x.id === userId)
  if (!u) return
  editId.value = userId
  editForm.value = {
    role: u.role || 'user',
    status: u.status || 'approved',
    islands: (u.allowed_islands || '').split(',').filter(Boolean),
  }
  showEditDialog.value = true
}

async function handleSaveEdit() {
  await updateUser(editId.value, {
    role: editForm.value.role,
    status: editForm.value.status,
    allowed_islands: editForm.value.islands.join(','),
  })
  ElMessage.success('已保存')
  showEditDialog.value = false
  fetchUsers()
}

async function handleAddUser() {
  if (!addForm.value.email || !addForm.value.password) {
    ElMessage.warning('请填写账号与密码')
    return
  }
  await addUser({ ...addForm.value })
  ElMessage.success('已创建')
  showAddDialog.value = false
  addForm.value = { email: '', password: '', strict: false }
  fetchUsers()
}

function openResetPwd(userId) {
  const u = users.value.find(x => x.id === userId)
  if (!u) return
  resetPwdTarget.value = u
  resetPwdForm.value = { password: '', strict: false }
  showResetPwdDialog.value = true
}

async function handleResetPwd() {
  if (!resetPwdForm.value.password) {
    ElMessage.warning('请输入新密码')
    return
  }
  await resetUserPassword(resetPwdTarget.value.id, { ...resetPwdForm.value })
  ElMessage.success('密码已重置')
  showResetPwdDialog.value = false
}

onMounted(async () => {
  await Promise.all([fetchUsers(), fetchRoles()])
})
</script>

<style scoped>
.section {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 18px 22px;
  box-shadow: var(--dp-shadow);
}
.section-tip {
  font-size: 12px;
  color: var(--dp-text3);
  margin-bottom: 12px;
}
.island-tags { display: flex; gap: 4px; flex-wrap: wrap; }

.empty-placeholder {
  text-align: center;
  padding: 40px;
}
.empty-icon { font-size: 36px; opacity: .5; margin-bottom: 8px; }
.empty-text { font-size: 13px; color: var(--dp-text3); }

.form-tip { font-size: 11px; color: var(--dp-text3); line-height: 1.5; margin-top: 4px; }
.reset-target { font-size: 13px; margin-bottom: 12px; }
</style>
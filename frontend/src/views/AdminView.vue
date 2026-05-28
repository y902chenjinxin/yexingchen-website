<template>
  <div class="admin-page">
    <header class="admin-header">
      <div class="header-left">
        <span class="back-btn" @click="router.push('/home')">← 返回主页</span>
        <span class="admin-title">🔧 管理后台</span>
      </div>
      <div class="header-right">
        <el-input v-model="searchQuery" placeholder="搜索邮箱" clearable style="width: 200px" @clear="fetchUsers" @keyup.enter="fetchUsers">
          <template #append>
            <el-button :icon="Search" @click="fetchUsers" />
          </template>
        </el-input>
        <el-button type="primary" @click="showAddDialog = true">新增用户</el-button>
      </div>
    </header>

    <main class="admin-content">
      <!-- 用户管理 -->
      <div class="section">
        <div class="section-title">用户管理</div>
        <el-table :data="filteredUsers" stripe style="width: 100%" v-loading="loading">
          <el-table-column prop="email" label="邮箱" min-width="200" />
          <el-table-column prop="role" label="角色" width="120">
            <template #default="{ row }">
              <el-tag :type="row.role === 'super_admin' ? 'danger' : 'info'" size="small">
                {{ row.role === 'super_admin' ? '超级管理员' : '普通用户' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="allowed_islands" label="可访问岛屿" min-width="200">
            <template #default="{ row }">
              <div class="island-tags">
                <el-tag v-for="island in row.allowed_islands.split(',')" :key="island" size="small" type="info">
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
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-dropdown trigger="click" @command="(cmd) => handleCommand(row.id, cmd)">
                  <el-button size="small">
                    操作 <el-icon class="el-icon--right"><CaretBottom /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="approve">审核通过</el-dropdown-item>
                      <el-dropdown-item command="reject">审核不通过</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
              <template v-else>
                <el-dropdown trigger="click" @command="(cmd) => handleCommand(row.id, cmd)">
                  <el-button size="small">
                    编辑 <el-icon class="el-icon--right"><CaretBottom /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">修改</el-dropdown-item>
                      <el-dropdown-item command="delete" style="color: #F56C6C;">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!loading && filteredUsers.length === 0" class="empty-placeholder">
          <div class="empty-icon">👥</div>
          <div class="empty-text">暂无用户</div>
        </div>
      </div>
    </main>

    <!-- 编辑用户弹窗 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="普通用户" value="normal" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="可访问岛屿">
          <el-checkbox-group v-model="editForm.islands">
            <el-checkbox label="music">音乐岛</el-checkbox>
            <el-checkbox label="novel">小说岛</el-checkbox>
            <el-checkbox label="video">视频岛</el-checkbox>
            <el-checkbox label="diary">日志岛</el-checkbox>
            <el-checkbox label="tools">工具岛</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="showAddDialog" title="新增用户" width="400px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="邮箱">
          <el-input v-model="addForm.email" placeholder="请输入邮箱" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddUser">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, CaretBottom } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUserList, addUser, approveUser, rejectUser, updateUser, deleteUser } from '@/api/admin'

const router = useRouter()
const users = ref([])
const loading = ref(false)
const searchQuery = ref('')
const showEditDialog = ref(false)
const showAddDialog = ref(false)
const editUserId = ref(null)
const addForm = ref({ email: '', password: '' })
const editForm = ref({ role: 'normal', status: 'approved', islands: [] })

const allIslands = ['music', 'novel', 'video', 'diary', 'tools']

// 搜索过滤
const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value
  const q = searchQuery.value.toLowerCase()
  return users.value.filter(u => u.email.toLowerCase().includes(q))
})

onMounted(() => { fetchUsers() })

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUserList({ page: 1, size: 100 })
    users.value = res.data.list
  } catch { /* 错误已由api拦截器处理 */ }
  finally { loading.value = false }
}

// 下拉菜单命令处理
async function handleCommand(id, command) {
  if (command === 'approve') {
    await handleApprove(id)
  } else if (command === 'reject') {
    await handleReject(id)
  } else if (command === 'edit') {
    const user = users.value.find(u => u.id === id)
    if (user) handleEditUser(user)
  } else if (command === 'delete') {
    await handleDeleteUser(id)
  }
}

async function handleApprove(id) {
  try {
    await ElMessageBox.confirm('确定通过该用户的注册申请吗？', '提示', { type: 'warning' })
    await approveUser(id)
    ElMessage.success('已通过')
    fetchUsers()
  } catch { /* 用户取消 */ }
}

async function handleReject(id) {
  try {
    await ElMessageBox.confirm('确定拒绝该用户的注册申请吗？', '提示', { type: 'warning' })
    await rejectUser(id)
    ElMessage.success('已拒绝')
    fetchUsers()
  } catch { /* 用户取消 */ }
}

function handleEditUser(row) {
  editUserId.value = row.id
  editForm.value = {
    role: row.role,
    status: row.status,
    islands: row.allowed_islands ? row.allowed_islands.split(',').filter(Boolean) : []
  }
  showEditDialog.value = true
}

async function handleSaveEdit() {
  try {
    await updateUser(editUserId.value, {
      role: editForm.value.role,
      status: editForm.value.status,
      allowed_islands: editForm.value.islands.join(',')
    })
    ElMessage.success('更新成功')
    showEditDialog.value = false
    fetchUsers()
  } catch { /* 错误已由api拦截器处理 */ }
}

async function handleDeleteUser(id) {
  try {
    await ElMessageBox.confirm('确定删除该用户吗？该操作不可恢复', '提示', { type: 'warning' })
    await deleteUser(id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch { /* 用户取消 */ }
}

async function handleAddUser() {
  if (!addForm.value.email || !addForm.value.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(addForm.value.email)) {
    ElMessage.warning('请输入正确的邮箱格式')
    return
  }
  try {
    await addUser({ email: addForm.value.email, password: addForm.value.password })
    ElMessage.success('用户创建成功')
    showAddDialog.value = false
    addForm.value = { email: '', password: '' }
    fetchUsers()
  } catch { /* 错误已由api拦截器处理 */ }
}

function getStatusType(status) {
  return { pending: 'warning', approved: 'success', rejected: 'danger' }[status] || 'info'
}

function getStatusText(status) {
  return { pending: '待审批', approved: '已通过', rejected: '已拒绝' }[status] || status
}

function getIslandName(island) {
  return { music: '音乐岛', novel: '小说岛', video: '视频岛', diary: '日志岛', tools: '工具岛' }[island] || island
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--color-bg); padding-bottom: 40px; }
.admin-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: rgba(26, 58, 74, 0.8); border-bottom: 1px solid rgba(78, 205, 196, 0.2); }
.header-left { display: flex; align-items: center; gap: 20px; }
.back-btn { color: var(--color-accent); cursor: pointer; font-size: 14px; }
.back-btn:hover { color: var(--color-text); }
.admin-title { font-family: var(--font-serif); font-size: 20px; color: var(--color-text); }
.admin-content { padding: 30px 40px; }
.section { background: rgba(26, 58, 74, 0.4); border: 1px solid rgba(78, 205, 196, 0.2); border-radius: var(--radius); padding: 25px; }
.section-title { font-family: var(--font-serif); font-size: 18px; color: var(--color-text); margin-bottom: 20px; }
.island-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.empty-placeholder { display: flex; flex-direction: column; align-items: center; padding: 40px 0; color: var(--color-text-secondary); }
.empty-icon { font-size: 48px; margin-bottom: 10px; }
.empty-text { font-size: 14px; }
@media (max-width: 768px) {
  .admin-header { padding: 15px 20px; }
  .admin-content { padding: 20px; }
}
</style>
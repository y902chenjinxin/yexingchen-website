<template>
  <div class="admin-page">
    <header class="admin-header">
      <div class="header-left">
        <span class="back-btn" @click="router.push('/workbench')">← 返回工作台</span>
        <span class="admin-title">🔧 管理后台</span>
      </div>
      <div class="header-right" v-if="tab === 'users'">
        <el-input v-model="searchQuery" placeholder="搜索邮箱" clearable style="width: 200px" @clear="fetchUsers" @keyup.enter="fetchUsers">
          <template #append>
            <el-button :icon="Search" @click="fetchUsers" />
          </template>
        </el-input>
        <el-button type="primary" @click="showAddDialog = true">新增用户</el-button>
      </div>
      <div class="header-right" v-else-if="tab === 'roles'">
        <el-button type="primary" @click="openRoleForm()">新增角色</el-button>
      </div>
      <div class="header-right" v-else-if="tab === 'menus'">
        <el-button type="primary" @click="openMenuForm()">新增菜单</el-button>
      </div>
    </header>

    <main class="admin-content">
      <el-tabs v-model="tab" class="admin-tabs" @tab-change="onTabChange">
        <el-tab-pane label="用户管理" name="users" />
        <el-tab-pane label="角色管理" name="roles" />
        <el-tab-pane label="菜单管理" name="menus" />
      </el-tabs>

      <!-- ============ 用户管理 ============ -->
      <section v-if="tab === 'users'" class="section">
        <div class="section-title">用户管理</div>
        <el-table :data="filteredUsers" stripe style="width: 100%" v-loading="loading">
          <el-table-column prop="email" label="邮箱" min-width="200" />
          <el-table-column prop="role" label="角色" width="120">
            <template #default="{ row }">
              <el-tag :type="getRoleTagType(row.role)" size="small">
                {{ getRoleText(row.role) }}
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
          <el-table-column prop="allowed_islands" label="可访问模块" min-width="200">
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
                      <el-dropdown-item command="resetPwd">重置密码</el-dropdown-item>
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
      </section>

      <!-- ============ 角色管理 ============ -->
      <section v-if="tab === 'roles'" class="section">
        <div class="section-title">角色管理</div>
        <div class="section-tip">角色与菜单绑定：在编辑弹窗中勾选该角色可见的菜单，决定其登录后「快速前往」导航能看到的模块。系统内置角色不可删除、不可修改标识。</div>
        <el-table :data="roles" stripe style="width: 100%" v-loading="roleLoading">
          <el-table-column prop="name" label="角色名称" min-width="130">
            <template #default="{ row }">
              <span class="role-name">{{ row.name }}</span>
              <el-tag v-if="row.is_builtin" size="small" type="warning" class="builtin-tag">内置</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="code" label="标识" width="140" />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column prop="permissions" label="可见菜单" min-width="170" show-overflow-tooltip>
            <template #default="{ row }">{{ formatMenuPerms(row) }}</template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openRoleForm(row)">编辑</el-button>
              <el-popconfirm
                v-if="!row.is_builtin"
                title="确认删除该角色？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                width="210"
                @confirm="handleDeleteRole(row)"
              >
                <template #reference>
                  <el-button size="small" type="danger" plain>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!roleLoading && roles.length === 0" class="empty-placeholder">
          <div class="empty-icon">🛡️</div>
          <div class="empty-text">暂无角色</div>
        </div>
      </section>

      <!-- ============ 菜单管理 ============ -->
      <section v-if="tab === 'menus'" class="section">
        <div class="section-title">菜单管理</div>
        <div class="section-tip">支持一级 / 二级模块：一二级模块展示为树状层级。控制全站顶栏导航入口的可见性、排序与启用状态。系统内置菜单不可删除。</div>
        <el-table :data="menuTree" stripe style="width: 100%" v-loading="menuLoading" row-key="id">
          <el-table-column label="菜单名称" min-width="160">
            <template #default="{ row }">
              <span class="menu-level-indent" :style="{ paddingLeft: (6 + row.level * 22) + 'px' }">
                <el-icon v-if="row.level === 1" class="menu-branch"><FolderOpened /></el-icon>
                <el-icon v-else class="menu-icon"><component :is="iconMap[row.icon] || HomeFilled" /></el-icon>
                <span>{{ row.title }}</span>
                <el-tag v-if="row.is_builtin" size="small" type="warning" class="builtin-tag">内置</el-tag>
                <el-tag size="small" :type="row.level === 0 ? 'primary' : 'success'" class="builtin-tag">
                  {{ row.level === 0 ? '一级' : '二级' }}
                </el-tag>
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" min-width="140" show-overflow-tooltip />
          <el-table-column label="上级" width="130">
            <template #default="{ row }">
              {{ row.parent_title || '—' }}
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
                {{ row.is_enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openMenuForm(row)">编辑</el-button>
              <el-popconfirm
                v-if="!row.is_builtin"
                title="确认删除该菜单？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                width="210"
                @confirm="handleDeleteMenu(row)"
              >
                <template #reference>
                  <el-button size="small" type="danger" plain>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!menuLoading && menus.length === 0" class="empty-placeholder">
          <div class="empty-icon">🧭</div>
          <div class="empty-text">暂无菜单</div>
        </div>
      </section>
    </main>

    <!-- ============ 编辑用户弹窗 ============ -->
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

    <!-- ============ 新增用户弹窗 ============ -->
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

    <!-- ============ 重置密码弹窗 ============ -->
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

    <!-- ============ 角色编辑弹窗 ============ -->
    <el-dialog v-model="showRoleDialog" :title="roleForm.id ? '编辑角色' : '新增角色'" width="520px">
      <el-form :model="roleForm" label-width="90px">
        <el-form-item label="角色名称">
          <el-input v-model="roleForm.name" placeholder="如：内容编辑" maxlength="40" />
        </el-form-item>
        <el-form-item label="标识">
          <el-input v-model="roleForm.code" placeholder="英文标识，如 editor" maxlength="40" :disabled="roleForm.is_builtin" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="roleForm.description" placeholder="角色用途说明" maxlength="255" />
        </el-form-item>
        <el-form-item label="可见菜单">
          <div class="role-menu-toolbar">
            <el-button link type="primary" size="small" @click="setRoleMenuAll">全选</el-button>
            <el-button link size="small" @click="setRoleMenuNone">清空</el-button>
          </div>
          <div class="role-menu-tree-wrap">
            <el-tree
              ref="roleMenuTreeRef"
              :data="roleMenuTreeData"
              :props="{ label: 'title', children: 'children' }"
              node-key="id"
              show-checkbox
              default-expand-all
              @check="onRoleMenuCheck"
            />
          </div>
          <div class="form-hint">勾选该角色可访问 / 可见的菜单；不勾选任何菜单时默认可见全部启用菜单</div>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="roleForm.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRoleDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveRole">保存</el-button>
      </template>
    </el-dialog>

    <!-- ============ 菜单编辑弹窗 ============ -->
    <el-dialog v-model="showMenuDialog" :title="menuForm.id ? '编辑菜单' : '新增菜单'" width="520px">
      <el-form :model="menuForm" label-width="90px">
        <el-form-item label="上级模块">
          <el-select v-model="menuForm.parent_id" style="width: 100%" placeholder="选择上级模块（选“无”则为一二级中的一级模块）">
            <el-option label="无（一级模块）" :value="0" />
            <el-option v-for="p in parentMenuOptions" :key="p.id" :label="`一级：${p.title}`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="菜单名称">
          <el-input v-model="menuForm.title" placeholder="如：资讯" maxlength="60" />
        </el-form-item>
        <el-form-item label="路径">
          <el-input v-model="menuForm.path" placeholder="以 / 开头，如 /feeds" maxlength="255" :disabled="menuForm.is_builtin" />
        </el-form-item>
        <el-form-item label="图标">
          <el-select v-model="menuForm.icon" style="width: 100%" filterable allow-create default-first-option>
            <el-option v-for="(ic, key) in iconMap" :key="key" :label="key" :value="key">
              <el-icon class="menu-icon"><component :is="ic" /></el-icon>
              <span class="menu-icon-name">{{ key }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="menuForm.sort_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="menuForm.is_enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMenuDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveMenu">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, CaretBottom, HomeFilled, Collection, TrendCharts, MapLocation, Tools,
  Headset, Reading, VideoCamera, Document, ChatDotRound, Setting, FolderOpened
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getUserList, addUser, approveUser, rejectUser, updateUser, updateUserRole, resetUserPassword, deleteUser,
  getRoleList, addRole, updateRole, deleteRole,
  getMenuList, addMenu, updateMenu, deleteMenu
} from '@/api/admin'

const router = useRouter()
const tab = ref('users')

// ---------- 用户管理 ----------
const users = ref([])
const loading = ref(false)
const searchQuery = ref('')
const showEditDialog = ref(false)
const showAddDialog = ref(false)
const editUserId = ref(null)
const addForm = ref({ email: '', password: '', strict: false })
const editForm = ref({ role: 'user', status: 'approved', islands: [] })
const showResetPwdDialog = ref(false)
const resetPwdTarget = ref(null)
const resetPwdForm = ref({ password: '', strict: false })

const allIslands = ['music', 'novel', 'video', 'diary', 'tools']

const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value
  const q = searchQuery.value.toLowerCase()
  return users.value.filter(u => u.email.toLowerCase().includes(q))
})

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUserList({ page: 1, size: 100 })
    users.value = res.data.list
  } catch { /* 错误已由api拦截器处理 */ }
  finally { loading.value = false }
}

async function handleCommand(id, command) {
  if (command === 'approve') {
    await approveUser(id); ElMessage.success('已通过'); fetchUsers()
  } else if (command === 'reject') {
    await rejectUser(id); ElMessage.success('已拒绝'); fetchUsers()
  } else if (command === 'edit') {
    const user = users.value.find(u => u.id === id)
    if (user) handleEditUser(user)
  } else if (command === 'resetPwd') {
    const user = users.value.find(u => u.id === id)
    if (user) openResetPwd(user)
  } else if (command === 'delete') {
    await handleDeleteUser(id)
  }
}

function openResetPwd(user) {
  resetPwdTarget.value = user
  resetPwdForm.value = { password: '', strict: false }
  showResetPwdDialog.value = true
}

async function handleResetPwd() {
  const pwd = resetPwdForm.value.password
  if (!pwd) {
    ElMessage.warning('请输入新密码')
    return
  }
  // 严格校验时按公开注册同款强度要求（≥8 位 + 大小写 + 数字）；默认不校验，由超管自行把关
  if (resetPwdForm.value.strict && !/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/.test(pwd)) {
    ElMessage.warning('严格校验要求：至少 8 位且包含大小写字母与数字')
    return
  }
  try {
    await resetUserPassword(resetPwdTarget.value.id, {
      password: pwd,
      strict_validation: resetPwdForm.value.strict,
    })
    ElMessage.success('密码重置成功')
    showResetPwdDialog.value = false
    resetPwdTarget.value = null
  } catch { /* 错误已由api拦截器处理 */ }
}

function handleEditUser(row) {
  editUserId.value = row.id
  editForm.value = {
    role: row.role === 'super_admin' || row.role === 'admin' ? row.role : 'user',
    status: row.status,
    islands: row.allowed_islands ? row.allowed_islands.split(',').filter(Boolean) : []
  }
  showEditDialog.value = true
}

async function handleSaveEdit() {
  try {
    const uid = editUserId.value
    await Promise.all([
      updateUser(uid, {
        status: editForm.value.status,
        allowed_islands: editForm.value.islands.join(',')
      }),
      updateUserRole(uid, {
        role: editForm.value.role,
        is_super_admin: editForm.value.role === 'super_admin' ? 1 : 0
      })
    ])
    ElMessage.success('更新成功')
    showEditDialog.value = false
    fetchUsers()
  } catch { /* 错误已由api拦截器处理 */ }
}

async function handleDeleteUser(id) {
  try {
    await deleteUser(id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch { /* 错误已由api拦截器处理 */ }
}

async function handleAddUser() {
  const account = (addForm.value.email || '').trim()
  const pwd = addForm.value.password || ''
  if (!account || !pwd) {
    ElMessage.warning('请填写账号和密码')
    return
  }
  // 默认不校验格式与强度（超管给家里人开简单账号，如账号「爸爸」密码「123456」）；
  // 勾选严格校验时，才套用公开注册同款规则
  if (addForm.value.strict) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account)) {
      ElMessage.warning('严格校验要求：账号须为邮箱格式')
      return
    }
    if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/.test(pwd)) {
      ElMessage.warning('严格校验要求：密码至少 8 位且包含大小写字母与数字')
      return
    }
  }
  try {
    await addUser({
      email: account,
      password: pwd,
      strict_validation: addForm.value.strict,
    })
    ElMessage.success('用户创建成功')
    showAddDialog.value = false
    addForm.value = { email: '', password: '', strict: false }
    fetchUsers()
  } catch { /* 错误已由api拦截器处理 */ }
}

// ---------- 角色管理 ----------
const roles = ref([])
const roleLoading = ref(false)
const showRoleDialog = ref(false)
const roleForm = ref({ id: null, name: '', code: '', description: '', permissions: '[]', menu_ids: [], sort_order: 0, is_builtin: 0 })
const roleMenuTreeRef = ref(null)
const roleMenuTreeData = ref([])

async function fetchRoles() {
  roleLoading.value = true
  try {
    const res = await getRoleList()
    roles.value = res.data.list || []
  } catch { /* 错误已由api拦截器处理 */ }
  finally { roleLoading.value = false }
}

function parseMenuIds(raw) {
  if (!raw) return []
  try {
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr.map(Number).filter(n => Number.isFinite(n)) : []
  } catch { return [] }
}

function buildRoleMenuTree() {
  const l1 = menus.value.filter(m => !m.parent_id)
  roleMenuTreeData.value = l1.map(p => ({
    id: p.id,
    title: p.title,
    children: menus.value.filter(c => c.parent_id === p.id).map(c => ({ id: c.id, title: c.title })),
  }))
}

async function ensureMenusLoaded() {
  if (!menus.value.length) await fetchMenus()
}

function openRoleForm(row) {
  ensureMenusLoaded().then(() => {
    if (row) {
      roleForm.value = {
        id: row.id, name: row.name, code: row.code, description: row.description,
        permissions: row.permissions || '[]', menu_ids: parseMenuIds(row.menu_ids),
        sort_order: row.sort_order, is_builtin: row.is_builtin
      }
    } else {
      roleForm.value = { id: null, name: '', code: '', description: '', permissions: '[]', menu_ids: [], sort_order: 0, is_builtin: 0 }
    }
    buildRoleMenuTree()
    showRoleDialog.value = true
    nextTick(() => {
      roleMenuTreeRef.value?.setCheckedKeys(roleForm.value.menu_ids)
    })
  })
}

function onRoleMenuCheck() {
  roleForm.value.menu_ids = (roleMenuTreeRef.value?.getCheckedKeys(false) || []).map(Number)
}

function setRoleMenuAll() {
  roleMenuTreeRef.value?.setCheckedKeys(menus.value.filter(m => !m.parent_id).map(m => m.id))
  onRoleMenuCheck()
}

function setRoleMenuNone() {
  roleMenuTreeRef.value?.setCheckedKeys([])
  roleForm.value.menu_ids = []
}

function formatMenuPerms(row) {
  const ids = parseMenuIds(row.menu_ids)
  if (!ids.length) return '全部菜单'
  const names = menus.value.filter(m => ids.includes(m.id)).map(m => m.title)
  return names.length ? names.join('、') : '无（不显示菜单）'
}

function formatPerms(perms) {
  if (!perms) return '[]'
  try {
    const arr = JSON.parse(perms)
    return Array.isArray(arr) ? arr.join(', ') : perms
  } catch {
    return perms
  }
}

function normalizePerms(input) {
  let s = (input || '').trim()
  if (!s) return '[]'
  if (!s.startsWith('[')) {
    s = `["${s.split(',').map(x => x.trim()).filter(Boolean).join('","')}"]`
  }
  try {
    JSON.parse(s)
    return s
  } catch {
    return '[]'
  }
}

async function handleSaveRole() {
  if (!roleForm.value.name.trim() || !roleForm.value.code.trim()) {
    ElMessage.warning('请填写角色名称和标识')
    return
  }
  const payload = {
    name: roleForm.value.name.trim(),
    code: roleForm.value.code.trim(),
    description: roleForm.value.description.trim(),
    permissions: normalizePerms(roleForm.value.permissions),
    menu_ids: JSON.stringify(roleForm.value.menu_ids),
    sort_order: roleForm.value.sort_order
  }
  try {
    if (roleForm.value.id) {
      await updateRole(roleForm.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await addRole(payload)
      ElMessage.success('角色创建成功')
    }
    showRoleDialog.value = false
    fetchRoles()
  } catch { /* 错误已由api拦截器处理 */ }
}

async function handleDeleteRole(row) {
  try {
    await deleteRole(row.id)
    ElMessage.success('删除成功')
    fetchRoles()
  } catch { /* 错误已由api拦截器处理 */ }
}

// ---------- 菜单管理 ----------
const menus = ref([])
const menuLoading = ref(false)
const showMenuDialog = ref(false)
const menuForm = ref({ id: null, parent_id: 0, title: '', path: '', icon: 'Document', sort_order: 0, is_enabled: 1, is_builtin: 0 })

const iconMap = {
  Collection, TrendCharts, MapLocation, Tools, Headset, Reading, VideoCamera,
  Document, ChatDotRound, Setting, HomeFilled
}

// 一级模块（parent_id==0），供「新增/编辑二级模块」时选择上级
const parentMenuOptions = computed(() => menus.value.filter(m => !m.parent_id))

// 扁平 menus → 树状展示（一级模块 + 其下二级模块缩进）
const menuTree = computed(() => {
  const l1 = menus.value.filter(m => !m.parent_id)
  const orphans = menus.value.filter(m => m.parent_id && !l1.some(p => p.id === m.parent_id))
  return [
    ...l1.map(m => ({ ...m, level: 0, parent_title: '' })),
    ...l1.flatMap(p => menus.value
      .filter(c => c.parent_id === p.id)
      .map(c => ({ ...c, level: 1, parent_title: p.title }))
    ),
    ...orphans.map(m => ({ ...m, level: 1, parent_title: '（缺失上级）' })),
  ]
})

async function fetchMenus() {
  menuLoading.value = true
  try {
    const res = await getMenuList()
    menus.value = res.data.list || []
  } catch { /* 错误已由api拦截器处理 */ }
  finally { menuLoading.value = false }
}

function openMenuForm(row) {
  if (row) {
    menuForm.value = {
      id: row.id, parent_id: row.parent_id || 0, title: row.title, path: row.path, icon: row.icon,
      sort_order: row.sort_order, is_enabled: row.is_enabled, is_builtin: row.is_builtin
    }
  } else {
    menuForm.value = { id: null, parent_id: 0, title: '', path: '', icon: 'Document', sort_order: 0, is_enabled: 1, is_builtin: 0 }
  }
  showMenuDialog.value = true
}

async function handleSaveMenu() {
  if (!menuForm.value.title.trim() || !menuForm.value.path.trim()) {
    ElMessage.warning('请填写菜单名称和路径')
    return
  }
  const payload = {
    parent_id: menuForm.value.parent_id || 0,
    title: menuForm.value.title.trim(),
    path: menuForm.value.path.trim(),
    icon: menuForm.value.icon,
    sort_order: menuForm.value.sort_order,
    is_enabled: menuForm.value.is_enabled
  }
  try {
    if (menuForm.value.id) {
      await updateMenu(menuForm.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await addMenu(payload)
      ElMessage.success('菜单创建成功')
    }
    showMenuDialog.value = false
    fetchMenus()
  } catch { /* 错误已由api拦截器处理 */ }
}

async function handleDeleteMenu(row) {
  try {
    await deleteMenu(row.id)
    ElMessage.success('删除成功')
    fetchMenus()
  } catch { /* 错误已由api拦截器处理 */ }
}

// ---------- 通用 ----------
function onTabChange(name) {
  if (name === 'users') fetchUsers()
  else if (name === 'roles') fetchRoles()
  else if (name === 'menus') fetchMenus()
}

function getRoleTagType(role) {
  return { super_admin: 'danger', admin: 'warning' }[role] || 'info'
}
function getRoleText(role) {
  return { super_admin: '超级管理员', admin: '管理员', user: '普通用户', normal: '普通用户' }[role] || role
}
function getStatusType(status) {
  return { pending: 'warning', approved: 'success', rejected: 'danger' }[status] || 'info'
}
function getStatusText(status) {
  return { pending: '待审批', approved: '已通过', rejected: '已拒绝' }[status] || status
}
function getIslandName(island) {
  return { music: '音乐', novel: '小说', video: '视频', diary: '日志', tools: '工具' }[island] || island
}
function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

onMounted(() => { fetchUsers(); fetchRoles() })
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--color-bg); padding: 84px 0 40px; box-sizing: border-box; }
.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  background: var(--color-bg-glass);
  border-bottom: 1px solid rgba(201, 169, 110, 0.15);
}
.header-left { display: flex; align-items: center; gap: 20px; }
.back-btn { color: var(--color-gold); cursor: pointer; font-size: 14px; }
.back-btn:hover { color: var(--color-gold-light); }
.admin-title { font-family: var(--font-serif); font-size: 20px; color: var(--color-text); }
.admin-content { padding: 30px 40px; }
.section {
  background: var(--color-bg-elevated);
  border: 1px solid rgba(201, 169, 110, 0.1);
  border-radius: var(--radius);
  padding: 25px;
}
.section-title { font-family: var(--font-serif); font-size: 18px; color: var(--color-text); margin-bottom: 10px; }
.section-tip { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 16px; line-height: 1.7; }
.island-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.empty-placeholder { display: flex; flex-direction: column; align-items: center; padding: 40px 0; color: var(--color-text-secondary); }
.empty-icon { font-size: 48px; margin-bottom: 10px; }
.empty-text { font-size: 14px; }
.builtin-tag { margin-left: 8px; }
.role-name { font-weight: 600; }
.menu-icon { vertical-align: -2px; margin-right: 6px; }
.menu-icon-name { margin-left: 8px; }
.menu-level-indent { display: inline-flex; align-items: center; }
.menu-branch { vertical-align: -2px; margin-right: 6px; color: var(--color-gold); }
.reset-target { margin-bottom: 14px; font-size: 13px; color: var(--color-text-secondary); }
.reset-target b { color: var(--color-gold); font-weight: 600; }

/* 校验开关下方的说明文字（超管建号默认不套用公开注册规则） */
.form-tip { margin-top: 6px; font-size: 12px; line-height: 1.7; color: var(--color-text-muted); }
.form-hint { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.role-menu-toolbar { display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 4px; }
.role-menu-tree-wrap {
  width: 100%; max-height: 240px; overflow: auto; border: 1px solid var(--color-border);
  border-radius: 6px; padding: 6px;
  background: var(--color-bg, #fff);
}

/* Tab 样式 */
:deep(.el-tabs__item) {
  color: var(--color-text-secondary);
  font-family: var(--font-serif);
}
:deep(.el-tabs__item.is-active) {
  color: var(--color-gold);
}
:deep(.el-tabs__active-bar) {
  background-color: var(--color-gold);
}
:deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(201, 169, 110, 0.15);
}

/* Element Plus 深色主题覆盖 */
:deep(.el-table) {
  --el-table-bg-color: var(--color-bg-elevated);
  --el-table-tr-bg-color: var(--color-bg-elevated);
  --el-table-header-bg-color: rgba(201, 169, 110, 0.08);
  --el-table-header-text-color: var(--color-text);
  --el-table-text-color: var(--color-text);
  --el-table-border-color: rgba(201, 169, 110, 0.1);
  --el-table-row-hover-bg-color: rgba(201, 169, 110, 0.05);
}
:deep(.el-table th.el-table__cell) {
  background: rgba(201, 169, 110, 0.08) !important;
  font-weight: 600;
}
:deep(.el-dialog) {
  --el-dialog-bg-color: var(--color-bg-elevated);
  border: 1px solid rgba(201, 169, 110, 0.15);
  border-radius: var(--radius);
}
:deep(.el-dialog__title) {
  color: var(--color-text);
  font-family: var(--font-serif);
}
:deep(.el-form-item__label) {
  color: var(--color-text-secondary);
}
:deep(.el-input__wrapper) {
  background: var(--color-bg) !important;
  border: 1px solid rgba(201, 169, 110, 0.2);
  box-shadow: none !important;
}
:deep(.el-input__inner) {
  color: var(--color-text) !important;
}
:deep(.el-select .el-input__wrapper) {
  background: var(--color-bg) !important;
}
:deep(.el-dropdown-menu) {
  background: var(--color-bg-elevated);
  border: 1px solid rgba(201, 169, 110, 0.15);
}
:deep(.el-dropdown-menu__item) {
  color: var(--color-text);
}
:deep(.el-dropdown-menu__item:not(.is-disabled):hover) {
  background: rgba(201, 169, 110, 0.1);
  color: var(--color-gold);
}
:deep(.el-checkbox__label) {
  color: var(--color-text);
}
:deep(.el-tag) {
  --el-tag-bg-color: rgba(201, 169, 110, 0.1);
  --el-tag-border-color: rgba(201, 169, 110, 0.2);
  --el-tag-text-color: var(--color-gold);
}

@media (max-width: 768px) {
  .admin-header { padding: 15px 20px; }
  .admin-content { padding: 20px; }
}
</style>

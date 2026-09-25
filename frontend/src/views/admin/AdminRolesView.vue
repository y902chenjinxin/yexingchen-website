<template>
  <AdminLayout>
    <template #actions>
      <el-button type="primary" @click="openRoleForm()">新增角色</el-button>
    </template>

    <section class="section">
      <div class="section-tip">
        角色与菜单绑定：在编辑弹窗中勾选该角色可见的菜单，决定其登录后「快速前往」导航能看到的模块。系统内置角色不可删除、不可修改标识。
      </div>
      <el-table :data="roles" stripe class="admin-table" style="width: 100%" v-loading="loading">
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
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="row-ops">
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
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && roles.length === 0" class="empty-placeholder">
        <div class="empty-icon">🛡️</div>
        <div class="empty-text">暂无角色</div>
      </div>
    </section>

    <!-- 角色编辑弹窗 -->
    <el-dialog v-model="showRoleDialog" class="role-dialog" :title="roleForm.id ? '编辑角色' : '新增角色'" width="560px">
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
            <el-divider direction="vertical" />
            <span class="toolbar-hint">按分组快选：</span>
            <el-button
              v-for="p in parentGroupOptions"
              :key="p.id"
              link
              size="small"
              :type="groupHasFullChecked(p.id) ? 'success' : 'primary'"
              @click="toggleGroup(p.id)"
            >{{ p.title }}</el-button>
          </div>
          <div class="role-menu-tree-wrap">
            <el-tree
              ref="roleMenuTreeRef"
              :data="roleMenuTreeData"
              :props="{ label: 'title', children: 'children' }"
              node-key="id"
              show-checkbox
              default-expand-all
              :check-strictly="false"
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
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getRoleList, addRole, updateRole, deleteRole, getMenuList } from '@/api/admin'
import AdminLayout from './AdminLayout.vue'

const roles = ref([])
const menus = ref([])
const loading = ref(false)

const showRoleDialog = ref(false)
const roleMenuTreeRef = ref(null)
const roleForm = ref({ id: null, name: '', code: '', description: '', menu_ids: [], sort_order: 0, is_builtin: false })
const roleMenuTreeData = ref([])

/* menu_ids 可能是数组，也可能是 JSON 字符串 / 逗号串（历史数据或旧接口）。
   这里统一归一化：一旦出现非数组值，`.map` 会抛错 → 整个单元格渲染失败 →
   后面的「排序 / 操作」列整体左移错位（本轮用户报的「角色管理操作栏错位」就是这个）。 */
function normalizeMenuIds(raw) {
  if (Array.isArray(raw)) {
    return raw.map(x => Number(x)).filter(n => !Number.isNaN(n))
  }
  if (typeof raw === 'string' && raw.trim()) {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed.map(x => Number(x)).filter(n => !Number.isNaN(n)) : []
    } catch {
      return raw.split(',').map(s => Number(s.trim())).filter(n => !Number.isNaN(n))
    }
  }
  return []
}

function formatMenuPerms(row) {
  const ids = normalizeMenuIds(row.menu_ids)
  if (!ids.length) return '全部启用菜单'
  const names = ids.map(id => menus.value.find(x => x.id === id)?.title || `#${id}`)
  if (names.length <= 3) return names.join(' / ')
  return names.slice(0, 3).join(' / ') + ` 等 ${names.length} 项`
}

async function fetchRoles() {
  loading.value = true
  try {
    const res = await getRoleList()
    roles.value = res.data?.list || []
  } catch { /* 静默 */ } finally { loading.value = false }
}

async function fetchMenus() {
  try {
    const res = await getMenuList()
    menus.value = res.data?.list || []
    // 构造树
    const roots = menus.value.filter(m => !m.parent_id || m.parent_id === 0)
    roleMenuTreeData.value = roots.map(r => ({
      id: r.id,
      title: r.title,
      children: menus.value.filter(c => c.parent_id === r.id).map(c => ({
        id: c.id,
        title: c.title,
      })),
    }))
  } catch { /* 静默 */ }
}

function openRoleForm(row) {
  if (row) {
    roleForm.value = {
      id: row.id,
      name: row.name || '',
      code: row.code || '',
      description: row.description || '',
      menu_ids: normalizeMenuIds(row.menu_ids),
      sort_order: row.sort_order || 0,
      is_builtin: !!row.is_builtin,
    }
  } else {
    roleForm.value = {
      id: null, name: '', code: '', description: '',
      menu_ids: [], sort_order: 0, is_builtin: false,
    }
  }
  showRoleDialog.value = true
  nextTick(() => {
    if (!roleMenuTreeRef.value) return
    roleMenuTreeRef.value.setCheckedKeys(roleForm.value.menu_ids || [])
  })
}

function setRoleMenuAll() {
  if (!roleMenuTreeRef.value) return
  const all = menus.value.map(m => m.id)
  roleMenuTreeRef.value.setCheckedKeys(all)
  roleForm.value.menu_ids = all
}
function setRoleMenuNone() {
  if (!roleMenuTreeRef.value) return
  roleMenuTreeRef.value.setCheckedKeys([])
  roleForm.value.menu_ids = []
}
function onRoleMenuCheck() {
  if (!roleMenuTreeRef.value) return
  const checked = roleMenuTreeRef.value.getCheckedKeys() || []
  const halfChecked = roleMenuTreeRef.value.getHalfCheckedKeys() || []
  roleForm.value.menu_ids = [...new Set([...checked, ...halfChecked])]
}

/* v2.18：按一级分组快选。点一次全选该组所有二级，再点取消。 */
const parentGroupOptions = computed(() =>
  menus.value.filter(m => !m.parent_id || m.parent_id === 0)
)

function childrenOf(parentId) {
  return menus.value.filter(m => m.parent_id === parentId).map(m => m.id)
}

function groupHasFullChecked(parentId) {
  if (!roleMenuTreeRef.value) return false
  const childIds = childrenOf(parentId)
  if (!childIds.length) return false
  const checked = new Set(roleMenuTreeRef.value.getCheckedKeys() || [])
  return childIds.every(id => checked.has(id))
}

function toggleGroup(parentId) {
  if (!roleMenuTreeRef.value) return
  const childIds = childrenOf(parentId)
  if (groupHasFullChecked(parentId)) {
    // 已全选 → 取消整组（保留其它组的选择）
    const cur = new Set(roleMenuTreeRef.value.getCheckedKeys() || [])
    const next = [...cur].filter(id => !childIds.includes(id))
    roleMenuTreeRef.value.setCheckedKeys(next)
    roleForm.value.menu_ids = next
  } else {
    // 否则 → 全选该组
    const cur = new Set(roleMenuTreeRef.value.getCheckedKeys() || [])
    const next = [...new Set([...cur, ...childIds])]
    roleMenuTreeRef.value.setCheckedKeys(next)
    roleForm.value.menu_ids = next
  }
}

async function handleSaveRole() {
  if (!roleForm.value.name || !roleForm.value.code) {
    ElMessage.warning('请填写角色名称与标识')
    return
  }
  if (roleForm.value.id) {
    await updateRole(roleForm.value.id, {
      name: roleForm.value.name,
      description: roleForm.value.description,
      menu_ids: roleForm.value.menu_ids,
      sort_order: roleForm.value.sort_order,
    })
  } else {
    await addRole({
      name: roleForm.value.name,
      code: roleForm.value.code,
      description: roleForm.value.description,
      menu_ids: roleForm.value.menu_ids,
      sort_order: roleForm.value.sort_order,
    })
  }
  ElMessage.success('已保存')
  showRoleDialog.value = false
  fetchRoles()
}

async function handleDeleteRole(row) {
  await deleteRole(row.id)
  ElMessage.success('已删除')
  fetchRoles()
}

onMounted(async () => {
  await Promise.all([fetchRoles(), fetchMenus()])
})
</script>

<style scoped>
/* ---- 本页局部玄黄主题 ----
   只在本页重定义 Element Plus 主色，不动全局 --dp-accent，其它后台页维持原配色。
   理由同菜单页：管理后台此前是清一色靛蓝，一点玄黄鎏金都没有，跟工作台放在一起像两套系统。 */
.section {
  --el-color-primary: var(--yq-gold-bright);
  --el-color-primary-light-3: var(--yq-gold);
  --el-color-primary-light-5: var(--yq-gold);
  --el-color-primary-light-7: var(--yq-gold-faint);
  --el-color-primary-light-8: var(--yq-gold-faint);
  --el-color-primary-light-9: var(--yq-gold-faint);

  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 18px 22px;
  box-shadow: var(--dp-shadow);
}
.section-tip { font-size: 12px; color: var(--dp-text3); margin-bottom: 14px; line-height: 1.6; }

.role-name { font-weight: 600; margin-right: 6px; }
.builtin-tag { margin-left: 4px; }

.empty-placeholder { text-align: center; padding: 40px; }
.empty-icon { font-size: 36px; opacity: .5; margin-bottom: 8px; }
.empty-text { font-size: 13px; color: var(--dp-text3); }

/* 编辑弹窗：弹窗未设 append-to-body，就地渲染在本组件内，所以 scoped 的 :deep() 能穿透到它 */
:deep(.role-dialog) {
  --el-color-primary: var(--yq-gold-bright);
  --el-color-primary-light-3: var(--yq-gold);
  --el-color-primary-light-5: var(--yq-gold);
  --el-color-primary-light-7: var(--yq-gold-faint);
  --el-color-primary-light-8: var(--yq-gold-faint);
  --el-color-primary-light-9: var(--yq-gold-faint);
}

.role-menu-toolbar { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; flex-wrap: wrap; }
.toolbar-hint { font-size: 12px; color: var(--dp-text3); margin: 0 4px; }

/* 可见菜单树：
   原先是「灰底 + 1px 边框的方盒子」，像把默认组件直接塞进表单里，所以显得突兀。
   改成无外框、只用一条左侧细线界定范围，行距压紧；勾选框统一到鎏金，
   与菜单页的启停开关同色。 */
.role-menu-tree-wrap {
  max-height: 232px;
  overflow-y: auto;
  border: 0;
  border-left: 2px solid var(--dp-line);
  border-radius: 0;
  padding: 2px 0 2px 10px;
  background: transparent;

  --el-checkbox-checked-bg-color: var(--yq-gold-bright);
  --el-checkbox-checked-input-border-color: var(--yq-gold-bright);
  --el-checkbox-checked-text-color: var(--dp-text);
  --el-tree-node-hover-bg-color: var(--dp-bg2);
}
.role-menu-tree-wrap :deep(.el-tree) { background: transparent; }
.role-menu-tree-wrap :deep(.el-tree-node__content) { height: 30px; border-radius: 6px; }
.role-menu-tree-wrap :deep(.el-tree-node__label) { font-size: 13px; }
/* 一级分组加字重区分层级，二级保持常规字重 */
.role-menu-tree-wrap :deep(.el-tree > .el-tree-node > .el-tree-node__content .el-tree-node__label) { font-weight: 500; }
.role-menu-tree-wrap :deep(.el-tree-node__expand-icon) { color: var(--dp-text3); }
.role-menu-tree-wrap :deep(.el-checkbox__inner) { border-radius: 4px; }
.role-menu-tree-wrap :deep(.el-checkbox__input.is-checked .el-checkbox__inner::after) { border-color: #fff; }

.form-hint { font-size: 11px; color: var(--dp-text3); margin-top: 6px; }
</style>
<template>
  <AdminLayout>
    <template #actions>
      <el-button type="primary" @click="openMenuForm()">新增菜单</el-button>
    </template>

    <section class="section">
      <div class="section-tip">
        支持一级 / 二级模块：一二级模块展示为树状层级。控制全站顶栏导航入口的可见性、排序与启用状态。系统内置菜单不可删除。
      </div>
      <el-table :data="menuTree" stripe style="width: 100%" v-loading="loading" row-key="id">
        <el-table-column label="菜单名称" min-width="200">
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
        <el-table-column prop="path" label="路径" min-width="160" show-overflow-tooltip />
        <el-table-column label="上级" width="140">
          <template #default="{ row }">{{ row.parent_title || '—' }}</template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="row-ops">
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
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && menus.length === 0" class="empty-placeholder">
        <div class="empty-icon">🧭</div>
        <div class="empty-text">暂无菜单</div>
      </div>
    </section>

    <!-- 菜单编辑弹窗 -->
    <el-dialog v-model="showMenuDialog" :title="menuForm.id ? '编辑菜单' : '新增菜单'" width="560px">
      <el-form :model="menuForm" label-width="90px">
        <el-form-item label="上级模块">
          <el-select v-model="menuForm.parent_id" style="width: 100%" placeholder="选择上级模块（选「无」则为一二级中的一级模块）">
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
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { FolderOpened, HomeFilled, Collection, TrendCharts, MapLocation, Tools,
  Headset, Reading, VideoCamera, Document, ChatDotRound, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getMenuList, addMenu, updateMenu, deleteMenu } from '@/api/admin'
import AdminLayout from './AdminLayout.vue'

const menus = ref([])
const loading = ref(false)

const showMenuDialog = ref(false)
const menuForm = ref({ id: null, title: '', path: '', icon: '', parent_id: 0, sort_order: 0, is_enabled: 1, is_builtin: false })

const iconMap = { HomeFilled, Collection, TrendCharts, MapLocation, Tools, Headset, Reading, VideoCamera, Document, ChatDotRound, Setting }

const parentMenuOptions = computed(() => menus.value.filter(m => !m.parent_id || m.parent_id === 0))

const menuTree = computed(() => {
  // 一级
  const roots = menus.value.filter(m => !m.parent_id || m.parent_id === 0)
  return roots.map(r => {
    const children = menus.value.filter(c => c.parent_id === r.id).map(c => ({
      ...c,
      level: 1,
    }))
    return {
      ...r,
      level: 0,
      _children: children,
    }
  }).concat(menus.value.filter(m => m.parent_id && m.parent_id !== 0).map(c => ({ ...c, level: 1 })))
})

async function fetchMenus() {
  loading.value = true
  try {
    const res = await getMenuList()
    menus.value = res.data?.list || []
  } catch { /* 静默 */ } finally { loading.value = false }
}

function openMenuForm(row) {
  if (row) {
    menuForm.value = {
      id: row.id,
      title: row.title || '',
      path: row.path || '',
      icon: row.icon || '',
      parent_id: row.parent_id || 0,
      sort_order: row.sort_order || 0,
      is_enabled: row.is_enabled ?? 1,
      is_builtin: !!row.is_builtin,
    }
  } else {
    menuForm.value = {
      id: null, title: '', path: '', icon: '', parent_id: 0, sort_order: 0, is_enabled: 1, is_builtin: false,
    }
  }
  showMenuDialog.value = true
}

async function handleSaveMenu() {
  if (!menuForm.value.title) {
    ElMessage.warning('请填写菜单名称')
    return
  }
  const payload = {
    title: menuForm.value.title,
    path: menuForm.value.path,
    icon: menuForm.value.icon,
    parent_id: menuForm.value.parent_id,
    sort_order: menuForm.value.sort_order,
    is_enabled: menuForm.value.is_enabled,
  }
  if (menuForm.value.id) {
    await updateMenu(menuForm.value.id, payload)
  } else {
    await addMenu(payload)
  }
  ElMessage.success('已保存')
  showMenuDialog.value = false
  fetchMenus()
}

async function handleDeleteMenu(row) {
  await deleteMenu(row.id)
  ElMessage.success('已删除')
  fetchMenus()
}

onMounted(() => {
  fetchMenus()
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
.section-tip { font-size: 12px; color: var(--dp-text3); margin-bottom: 12px; line-height: 1.55; }

.menu-level-indent { display: inline-flex; align-items: center; gap: 6px; }
.menu-icon, .menu-branch { color: var(--dp-accent); }
.builtin-tag { margin-left: 4px; }

.empty-placeholder { text-align: center; padding: 40px; }
.empty-icon { font-size: 36px; opacity: .5; margin-bottom: 8px; }
.empty-text { font-size: 13px; color: var(--dp-text3); }

.menu-icon { vertical-align: middle; margin-right: 4px; }
.menu-icon-name { vertical-align: middle; }
</style>
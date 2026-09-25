<template>
  <AdminLayout>
    <template #actions>
      <el-button type="primary" @click="openMenuForm()">新增菜单</el-button>
    </template>

    <section class="section">
      <div class="section-tip">
        支持一级 / 二级模块：一级是侧栏的分组（内容 / 生活 / 财经 / 智能 / 管理），
        二级是分组下实际可点的页面。系统内置菜单不可删除，避免误删导致侧栏路由失效。
      </div>

      <!-- 自定义渲染：每个一级组 → 头部一行 + 内部若干二级行。
           不用 el-table 树状模式，原因是树状模式会强制把第一列锁成「缩进 + 折叠箭头」，
           标题被换行且与标签挤在一起观感差。这里用结构化 list，每行高密度且对齐。 -->
      <div v-loading="loading" class="menu-list">
        <!-- 表头：与下方 .menu-row 共用同一套 grid 列宽，文本对齐一致 -->
        <div class="menu-header">
          <div class="menu-cell menu-name">菜单名称</div>
          <div class="menu-cell menu-path">路径</div>
          <div class="menu-cell menu-parent">上级</div>
          <div class="menu-cell menu-sort">排序</div>
          <div class="menu-cell menu-status">状态</div>
          <div class="menu-cell menu-actions">操作</div>
        </div>
        <div v-if="!loading && menus.length === 0" class="empty-placeholder">
          <div class="empty-icon">🧭</div>
          <div class="empty-text">暂无菜单</div>
        </div>

        <div v-for="group in menuTree" :key="group.id" class="menu-group">
          <!-- 一级容器行：作为组头 + 自身的编辑/启停/删除操作 -->
          <div class="menu-row menu-row--group">
            <div class="menu-cell menu-name">
              <el-icon class="menu-branch"><FolderOpened /></el-icon>
              <span class="menu-title">{{ group.title }}</span>
              <el-tag v-if="group.is_builtin" size="small" type="warning" class="level-tag">内置</el-tag>
              <span class="child-count">{{ group.children.length }} 项</span>
            </div>
            <div class="menu-cell menu-path">
              <code class="path-code">{{ group.path || '—（一级容器）' }}</code>
            </div>
            <div class="menu-cell menu-parent">—</div>
            <div class="menu-cell menu-sort">{{ group.sort_order }}</div>
            <div class="menu-cell menu-status">
              <el-switch
                :model-value="group.is_enabled"
                :active-value="1"
                :inactive-value="0"
                inline-prompt
                active-text="启用"
                inactive-text="停用"
                @change="v => handleToggleEnabled(group, v)"
              />
            </div>
            <div class="menu-cell menu-actions">
              <el-button size="small" @click="openMenuForm(group)">编辑</el-button>
              <el-popconfirm
                v-if="!group.is_builtin"
                title="确认删除该菜单及其所有子项？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                width="240"
                @confirm="handleDeleteMenu(group)"
              >
                <template #reference>
                  <el-button size="small" type="danger" plain>删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>

          <!-- 二级子项 -->
          <div
            v-for="child in group.children"
            :key="child.id"
            class="menu-row menu-row--child"
          >
            <div class="menu-cell menu-name">
              <el-icon class="menu-leaf"><component :is="iconMap[child.icon] || HomeFilled" /></el-icon>
              <span class="menu-title">{{ child.title }}</span>
              <el-tag v-if="child.is_builtin" size="small" type="warning" class="level-tag">内置</el-tag>
            </div>
            <div class="menu-cell menu-path">
              <code class="path-code">{{ child.path }}</code>
            </div>
            <div class="menu-cell menu-parent">{{ group.title }}</div>
            <div class="menu-cell menu-sort">{{ child.sort_order }}</div>
            <div class="menu-cell menu-status">
              <el-switch
                :model-value="child.is_enabled"
                :active-value="1"
                :inactive-value="0"
                inline-prompt
                active-text="启用"
                inactive-text="停用"
                @change="v => handleToggleEnabled(child, v)"
              />
            </div>
            <div class="menu-cell menu-actions">
              <el-button size="small" @click="openMenuForm(child)">编辑</el-button>
              <el-popconfirm
                v-if="!child.is_builtin"
                title="确认删除该菜单？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                width="210"
                @confirm="handleDeleteMenu(child)"
              >
                <template #reference>
                  <el-button size="small" type="danger" plain>删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>
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

/* 构造两层树：一级组 → 其下的二级页面。
   刻意不用 el-table 的树状模式——它会把第一列锁成「缩进 + 折叠箭头」，
   标题被竖向换行、和标签挤在一起。这里输出结构化的两层数据，
   交给模板用自定义 grid 行渲染（一级行 + 二级行共用同一套列宽）。 */
const menuTree = computed(() => {
  const bySort = (a, b) => (a.sort_order - b.sort_order) || (a.id - b.id)
  const roots = menus.value
    .filter(m => !m.parent_id || m.parent_id === 0)
    .sort(bySort)
  return roots.map(r => ({
    ...r,
    children: menus.value.filter(c => c.parent_id === r.id).sort(bySort),
  }))
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
  // 一级容器需要合成 path（UNIQUE(path) 约束 + 默认值 '' 会被覆盖两次导致冲突）；
  // 二级节点必须以 / 开头。空 path 视作让后端自动生成。
  let path = (menuForm.value.path || '').trim()
  if (menuForm.value.parent_id === 0) {
    if (!path) path = `/__group/${menuForm.value.title.trim()}`
    if (path === '__group/') {
      ElMessage.warning('一级菜单需要填写名称才能生成 path')
      return
    }
  } else {
    if (!path.startsWith('/')) {
      ElMessage.warning('二级菜单路径必须以 / 开头，如 /feeds')
      return
    }
  }
  const payload = {
    title: menuForm.value.title,
    path,
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

/* 启停开关。
   坑：menuTree 里的行是 computed 产出的「副本」（map 里用了展开运算符），
   改副本不会让 computed 重算，开关就永远不动 —— 必须改回 menus 源数组里那一项。 */
async function handleToggleEnabled(row, v) {
  const next = v ? 1 : 0
  const src = menus.value.find(m => m.id === row.id)
  if (!src || src.is_enabled === next) return
  const prev = src.is_enabled
  src.is_enabled = next            // 乐观更新，开关立即跟随
  try {
    await updateMenu(row.id, { is_enabled: next })
    ElMessage.success(next ? '已启用' : '已停用')
  } catch (e) {
    src.is_enabled = prev          // 失败回滚（拦截器已提示）
  }
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

.menu-title-text { font-weight: 500; }
.menu-icon, .menu-branch { color: var(--dp-accent); }

/* 自定义 list 布局：6 列 grid，每列独立对齐 */
.menu-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.menu-header {
  display: grid;
  grid-template-columns: 1.8fr 2fr 1fr 60px 110px 160px;
  gap: 12px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--dp-text3);
  letter-spacing: .04em;
  border-bottom: 1px solid var(--dp-line);
  /* 与 .menu-row 的左边框等宽，否则表头内容会比行宽 3px，前两列对不齐 */
  border-left: 3px solid transparent;
}
.menu-group { display: flex; flex-direction: column; gap: 2px; }
.menu-row {
  display: grid;
  /* 一级行 / 二级行 / 表头共用同一套列宽。左边框宽度也统一成 3px：
     border-box 下 border 占内容宽度，组行 3px 与子行 2px 的差会让两行列错开。 */
  grid-template-columns: 1.8fr 2fr 1fr 60px 110px 160px;
  gap: 12px;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: background-color .15s;
}
.menu-row:hover { background: var(--dp-bg2); }
.menu-row--group {
  background: linear-gradient(135deg, rgba(199,169,107,.10), rgba(127,168,163,.06));
  border-left-color: var(--dp-accent);
  font-weight: 500;
}
.menu-row--child {
  background: var(--dp-bg2);
  border-left-color: var(--dp-line);
}
/* 二级缩进放进名称单元格内部。用整行 margin-left 会改掉这一行的内容宽度，
   导致二级行与一级行、表头的列对不齐。 */
.menu-row--child .menu-name { padding-left: 26px; }
.menu-cell {
  min-width: 0;       /* 防止 grid 内子元素被默认 min-content 撑开 */
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--dp-text);
}
.menu-cell.menu-sort {
  justify-content: center;
  font-variant-numeric: tabular-nums;
  color: var(--dp-text2);
}
.menu-cell.menu-actions {
  gap: 6px;
  flex-wrap: nowrap;
}
.menu-name .menu-branch,
.menu-name .menu-leaf { color: var(--dp-accent); flex: none; }
.menu-name .menu-title { font-size: 14px; }
.menu-name .level-tag { margin-left: 2px; }
.level-tag { transform: scale(.92); transform-origin: left center; }
/* 分组行的「N 项」计数：用轻量文字替代原先那个「分组容器」标签，降视觉重量 */
.child-count { font-size: 11px; color: var(--dp-text3); font-weight: 400; }

.path-code {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  font-size: 12px;
  color: var(--dp-text2);
  background: var(--dp-surface);
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid var(--dp-line);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-placeholder { text-align: center; padding: 40px; }
.empty-icon { font-size: 36px; opacity: .5; margin-bottom: 8px; }
.empty-text { font-size: 13px; color: var(--dp-text3); }

.menu-icon { vertical-align: middle; margin-right: 4px; }
.menu-icon-name { vertical-align: middle; }
</style>
# 个人网站 PRD v1.5.1

## 1. 项目概述

**项目名称**：叶兴辰的个人网站
**域名**：yexingchen.cn
**当前版本**：v1.5.1
**发布日期**：2026-05-28

**目标**：优化管理系统，修复架构冗余和交互体验问题。

**需求来源**：
- 架构审视：5个实体store模式重复、`require_super_admin`每次查库
- 前端审视：管理后台缺空状态、新增用户无邮箱校验
- 产品审视：操作按钮不一致、岛屿名称硬编码

---

## 2. 需求清单

| # | 模块 | 功能点 | 状态 |
|---|------|--------|------|
| 1 | 架构 | 抽取通用CRUD Store（music/novel/video/tool） | 待开发 |
| 2 | 前端 | AdminView用户表格添加空状态 | 待开发 |
| 3 | 前端 | 新增用户添加邮箱格式校验 | 待开发 |
| 4 | 架构 | JWT写入is_super_admin，后端直接读取 | 待开发 |

---

## 3. 功能详情

### 3.1 抽取通用CRUD Store

**问题**：music、novel、video、tool 四个store代码几乎一模一样，都是 `list/total/page/size/loading` + `fetchList/upload/update/remove`。

**解决**：创建 `frontend/src/composables/useCrudStore.js`，把通用逻辑收敛：

```javascript
// useCrudStore.js
export function useCrudStore(entityName, api) {
  const list = ref([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)
  const loading = ref(false)

  async function fetchList(params = {}) {
    loading.value = true
    try {
      const res = await api.getList({ page: page.value, size: size.value, ...params })
      list.value = res.data.list
      total.value = res.data.total
      return res
    } finally {
      loading.value = false
    }
  }

  async function upload(data) { return await api.upload(data) }
  async function update(id, data) { return await api.update(id, data) }
  async function remove(id) { return await api.delete(id) }

  return { list, total, page, size, loading, fetchList, upload, update, remove }
}
```

**文件**：
- 新建：`frontend/src/composables/useCrudStore.js`
- 修改：`frontend/src/stores/music.js`、`novel.js`、`video.js`、`tool.js`

---

### 3.2 AdminView用户表格空状态

**问题**：用户列表为空时无占位提示，表格区域突兀。

**解决**：在表格下方添加空状态组件：

```vue
<div v-if="!loading && filteredUsers.length === 0" class="empty-placeholder">
  <div class="empty-icon">👥</div>
  <div class="empty-text">暂无用户</div>
</div>
```

**文件**：`frontend/src/views/AdminView.vue`

---

### 3.3 新增用户邮箱校验

**问题**：新增用户仅判断非空，缺邮箱格式校验。

**解决**：在 `handleAddUser` 中添加正则校验：

```javascript
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
if (!emailRegex.test(addForm.value.email)) {
  ElMessage.warning('请输入正确的邮箱格式')
  return
}
```

**文件**：`frontend/src/views/AdminView.vue`

---

### 3.4 JWT写入is_super_admin

**问题**：`require_super_admin` 依赖每次请求都查库获取 `is_super_admin`，但该值几乎不变。

**解决**：
1. 后端 `auth.py` 登录时将 `is_super_admin` 写入JWT payload
2. `require_super_admin` 直接从 `current_user` 读取，不查库

**后端修改**（`backend/app/routers/auth.py`）：
```python
# 登录时JWT payload包含is_super_admin
access_token = create_access_token(
    data={"user_id": user.id, "is_super_admin": user.is_super_admin}
)
```

**后端修改**（`backend/app/services/auth.py` 或 `utils/security.py`）：
```python
def require_super_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user
```

**文件**：`backend/app/routers/auth.py`、后端 `require_super_admin` 相关文件

---

## 4. 技术记录

### 4.1 文件变更清单

| 操作 | 文件 |
|------|------|
| 新建 | frontend/src/composables/useCrudStore.js |
| 修改 | frontend/src/stores/music.js |
| 修改 | frontend/src/stores/novel.js |
| 修改 | frontend/src/stores/video.js |
| 修改 | frontend/src/stores/tool.js |
| 修改 | frontend/src/views/AdminView.vue |
| 修改 | backend/app/routers/auth.py |
| 修改 | backend/app/utils/security.py（require_super_admin） |

---

## 5. 测试验证

部署后验证：
1. 音乐岛/小说岛/视频岛/工具岛内容管理功能正常
2. 管理后台无用户时显示空状态占位
3. 新增用户输入无效邮箱时提示格式错误
4. 管理员操作正常（JWT中已包含is_super_admin）

---

## 6. 遗留问题

无。

---

## 7. 附录：Store重构前后对比

**重构前**（music.js, novel.js, video.js, tool.js 各一份）：
```javascript
export const useMusicStore = defineStore('music', () => {
  const list = ref([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)
  const loading = ref(false)
  async function fetchList(params = {}) { ... }
  async function upload(data) { ... }
  async function update(id, data) { ... }
  async function remove(id) { ... }
  return { list, total, page, size, loading, fetchList, upload, update, remove }
})
```

**重构后**（各store仅两行）：
```javascript
// music.js
import { useCrudStore } from '@/composables/useCrudStore'
import { getMusicList, uploadMusic, updateMusic, deleteMusic } from '@/api/music'
export const useMusicStore = defineStore('music', () => useCrudStore('music', { getList: getMusicList, upload: uploadMusic, update: updateMusic, delete: deleteMusic }))
```
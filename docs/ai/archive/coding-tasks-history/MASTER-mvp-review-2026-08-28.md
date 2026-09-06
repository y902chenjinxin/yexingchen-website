# 玄黄 MVP 综合验收报告

- 日期：2026-08-28
- 结论：不通过，需要集中返工
- 评审人：Codex
- 范围：玄黄 MVP 总任务

## 自动化结果

| 检查 | 结果 |
|---|---|
| 后端测试 | 39 passed，26 warnings |
| 前端测试 | 13 passed |
| 前端构建 | 通过 |
| 后端 compileall | 前一轮通过；本轮代码需继续保持 |
| pip check | 前一轮通过；本轮需继续保持 |

自动化通过不能代表 MVP 验收通过，原因见下方真实契约和功能审查。

## P0：必须先修复

### 1. 前后端响应格式不一致，真实工作台页面无法可靠读取数据

证据：

- `backend/app/routers/workbench.py` 的大多数接口直接返回 `{list, total, ...}` 或业务对象，没有统一 `{code, data}` 包装。
- `frontend/src/api/index.js` 的响应拦截器直接 `return response.data`。
- `frontend/src/stores/workbench.js` 仍读取 `summary.value = res.data`。
- `frontend/src/views/NotesView.vue` 仍读取 `res.data.list`、`res.data.total`。
- `AssetsView.vue`、`TasksView.vue`、`AssistantView.vue`、`TrashView.vue` 也使用同样的 `res.data.*` 访问方式。

独立真实请求验证：

```text
GET /api/workbench/summary
实际响应 keys = draft_notes, overdue_tasks, recent_notes, today_tasks
没有 data 字段

GET /api/workbench/notes
实际响应 keys = list, page, size, total
没有 data 字段
```

因此真实前端调用后会读取 `undefined`，页面列表、摘要、标签、回收站等功能可能显示为空或抛错。现有前端测试使用了带 `data` 的 mock，未覆盖真实 API 契约。

修复要求：二选一并全量统一：

- 方案 A：修改 Axios/workbench API 适配层，让所有工作台调用返回统一结构；
- 方案 B：修改所有工作台前端调用，直接读取拦截器返回的对象。

推荐方案 A 或建立明确的 API adapter，但不能只改一个页面。必须新增真实契约测试，不能只依赖 mock。

### 2. 受保护的图片/PDF预览无法通过普通 `<img>`/`<iframe>` 携带 Bearer Token

证据：

- 认证 Token 存在 localStorage。
- Axios 只给 Axios 请求注入 `Authorization`。
- `AssetsView.vue` 用 `<img :src="/api/workbench/assets/:id/preview">` 和 `<iframe :src="...">`。
- `NoteEditorView.vue` 把同一受保护 URL 写入富文本 `<img>` 或链接。
- 浏览器原生资源请求不会读取 Axios 拦截器，也不会自动带 localStorage 中的 Bearer Token。

结果：图片/PDF 预览在真实登录环境大概率 401。需要改为带鉴权的 blob/object URL、受控短期 URL，或其他明确安全方案；不能把接口改成公开匿名访问。

## P1：核心需求未实现或实现不完整

### 3. 粘贴图片和拖拽图片没有实现

- `NoteEditorView.vue` 只有 `@paste="onPaste"`。
- `onPaste` 只读取 `text/plain`，没有 `clipboardData.items/files`。
- 没有 `@drop`、`@dragover` 或 `onDrop`。
- 这不满足已确认的“点击上传 + 粘贴图片 + 拖拽图片”。

### 4. AI 调用前没有真正等待用户确认

- `aiAction()` 先打开预览对话框，然后立即执行 `workbenchApi.ai.invoke()`。
- 用户没有机会在 invoke 前确认或取消发送范围。
- `AssistantView.vue` 直接调用 `ai.invoke`，没有预览流程。

必须改为：preview → 用户确认 → invoke；助手页也必须遵守同一流程。

### 5. AI 结果应用能力不完整

当前只有标签应用的前端逻辑：

- 没有摘要应用
- 没有整理结果应用
- 没有任务草稿确认并创建任务
- 没有统一的后端“确认后应用”接口

这不满足 AI MVP 的四项能力闭环。

### 6. AI 对话选择没有真正绑定

- `AiInvokeIn` 没有 `conversation_id` 字段。
- `ai_invoke()` 总是使用当前用户最近的未删除对话。
- Assistant 页面可以选择旧对话，但发送时后端仍可能写入最近对话。

必须让发送请求显式携带并校验 conversation_id。

### 7. AI 对话没有关联笔记/资产/任务

PRD 已确认对话可关联内容，但模型和接口没有完整关联字段/接口/页面闭环。需要明确实现，或修订 PRD 后再验收；不能在汇报中宣称已完成。

### 8. 笔记附件显示/解绑逻辑失效

- `AssetOut` 没有 `note_ids` 字段。
- `NoteEditorView.vue` 用 `a.note_ids?.includes(noteId)` 筛选关联资产。
- 因此已关联附件加载后很可能不会显示。
- `detachAsset()` 只从前端数组移除，没有调用后端解绑接口，数据库关联仍然存在。

### 9. 搜索 page 参数未生效

`global_search()` 返回 page/size，但查询没有 `.offset((page - 1) * size)`；第 2 页仍可能返回第 1 页数据。

### 10. 链接资产缺少 URL 校验

`AssetLinkIn.url` 是普通字符串，没有限制 http/https、长度和合法格式；后端需要做明确校验。

### 11. 文件校验和资源处理不符合声明

- 上传使用 `await file.read()` 将最多 50 MB 文件全部读入内存。
- `ALLOWED_IMAGE_MIMES` 和 `ALLOWED_PDF_MIMES` 定义但未用于校验 `UploadFile.content_type`。
- 图片内容校验只是简单前缀判断，不是可靠的 MIME/图片解析校验。
- 下载/预览也将整个文件读入内存，建议使用流式响应或明确的资源上限。

### 12. 回收站清理可能丢失文件引用

`cleanup_trash()` 在物理文件删除失败时只记录 warning，随后仍删除数据库 Asset 记录，可能留下无法管理的孤儿文件或造成数据引用丢失。应明确失败策略：删除失败时保留记录并报告，或建立可重试的清理状态。

## P2：质量问题

- schema guard 的 `HEAD_REVISION` 硬编码，且 `SELECT ... LIMIT 1` 不检测多个 Alembic head；迁移新增后容易忘记同步。
- 新增前端文件 lint：至少 `sw-register.js` 有未使用变量；整体新增/旧代码 lint 仍有大量问题。
- Pydantic class-based Config、SQLAlchemy declarative_base 和 datetime.utcnow 存在弃用警告。
- 工作台页面大量使用硬编码颜色，未完全遵循既有 CSS 变量规则。
- 测试后产生 `test.db`、`backend/uploads` 和 `__pycache__`，本次已清理测试数据库、上传测试文件和缓存；后续测试必须自动隔离。

## 通过项

- 新增工作台相关模型、迁移和 API 文件确实存在。
- 迁移脚本包含 Note、Asset、Tag、Task、AI 对话和日志等表。
- 用户 ID 过滤在多数 CRUD、下载和预览接口中存在。
- 前端路由包含 `/workbench`、`/notes`、`/assets`、`/tasks`、`/assistant`、`/trash`。
- 登录页面默认跳转已改为 `/workbench`。
- `/home` 和旧岛屿模块路由仍保留。
- PWA manifest 和 Service Worker 文件存在。
- 自动化测试与构建结果通过。

## 验收结论

当前版本不能进入生产，也不应标记为“玄黄 MVP 已完成”。先修复 P0，再集中修复 P1，最后重新进行一次综合验收。

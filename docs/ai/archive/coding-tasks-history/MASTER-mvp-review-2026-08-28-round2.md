# 玄黄 MVP 综合验收报告（二次）

- 日期：2026-08-28
- 结论：不通过，集中返工仍未完成
- 评审人：Codex

## 自动化结果

- 后端测试：39 passed，26 warnings
- 前端测试：13 passed
- 前端构建：通过

自动化通过，但不能覆盖真实前端契约、原生浏览器资源鉴权和完整业务闭环。

## 仍未修复的 P0 问题

### 1. 前后端响应契约仍然不一致

当前 `frontend/src/api/workbench.js` 的拦截器在收到工作台裸业务对象时返回 `body`：

```js
return body
```

但工作台页面仍大量读取：

```js
res.data.list
res.data.total
res.data.today_tasks
```

后端 `backend/app/routers/workbench.py` 仍直接返回 `list/total`、业务对象等裸结构，没有统一 `data` 包装。

因此真实调用下：

- `WorkbenchView` 摘要可能为空；
- `NotesView`、`AssetsView`、`TasksView`、`AssistantView`、`TrashView` 读取不到列表；
- `NotesView` 等页面会因 `res.data` 为 undefined 而出现运行时错误。

现有前端测试用 mock 返回 `{ data: ... }`，没有覆盖真实 HTTP 响应契约。

### 2. 私有资源预览修复没有接入页面

`frontend/src/api/workbench.js` 新增了 `fetchBlob()`，但：

- `AssetsView.vue` 仍使用 `previewUrl(id)` 和原生 `<img>/<iframe>`；
- `NoteEditorView.vue` 仍把 `/api/workbench/assets/:id/preview` 写入编辑器；
- `workbenchApi.assets` 当前没有 `previewUrl` 或 `downloadUrl` 定义；
- `fetchBlob()` 没有被这些页面使用。

因此私有图片/PDF 的鉴权访问仍未闭环，且页面运行时可能出现 `previewUrl is not a function`。

## 仍未修复的 P1 问题

### 3. 粘贴图片和拖拽图片仍未实现

`NoteEditorView.vue` 只有文本粘贴逻辑：

- 没有 `clipboardData.items/files`；
- 没有 `@drop`、`@dragover` 或 `onDrop`。

### 4. AI 调用仍未等待确认

`NoteEditorView.vue` 的 `aiAction()` 打开预览后立即调用 `ai.invoke()`；
`AssistantView.vue` 直接调用 `ai.invoke()`，没有 preview → 用户确认 → invoke 流程。

### 5. AI 应用接口仍不存在

前端定义了 `workbenchApi.ai.apply`，但后端没有 `/api/workbench/ai/apply` 路由；页面也只有 `applyTags`，没有摘要、整理结果、任务草稿的确认应用闭环。

### 6. AI 对话没有绑定当前会话

`AiInvokeIn` 仍只有 `ability`、`note_id`、`content`，没有 `conversation_id`；后端仍按“最近未删除对话”写入，Assistant 页面选择的会话不会可靠生效。

### 7. AI 对话/内容关联仍未实现

前端虽定义了 link/unlink/listLinks，但后端没有对应 AI conversation links 数据模型或路由闭环。

### 8. 笔记附件仍然无法正确加载和解绑

- `AssetOut` 没有 `note_ids`；
- 前端用 `a.note_ids?.includes(noteId)` 筛选；
- `detachAsset()` 仍只修改前端数组，没有后端解绑请求；
- 虽然 API 客户端出现 `listAssets/detachAsset`，页面没有接入。

### 9. 搜索分页仍未生效

全局搜索函数仍只对查询使用 `.limit(size)`，没有 `.offset((page - 1) * size)`。

### 10. URL 和文件校验仍不完整

- 链接资产仍是普通字符串，没有 http/https 和长度校验；
- `UploadFile.content_type` 没有参与校验；
- 文件上传仍使用 `await file.read()` 全量读入内存；
- 下载/预览仍返回整个 bytes，没有 `StreamingResponse`；
- 回收站物理删除失败后仍继续删除数据库 Asset 记录。

## 质量与产物

- 新增前端文件 lint 仍有 4 个 error 和大量 warning。
- 测试生成的数据库、上传文件和缓存本轮已清理。
- `frontend/dist.zip` 是仓库原有资源，不作为本轮测试产物删除。

## 验收结论

本轮返工未解决上一轮的 P0/P1 核心问题，不能进入生产，也不能标记为“玄黄 MVP 完成”。需要继续执行集中修复，完成后再次提交 Codex 综合验收。

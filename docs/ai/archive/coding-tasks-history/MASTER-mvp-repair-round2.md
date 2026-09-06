# 玄黄 MVP 第二轮集中修复任务

## 状态

- 状态：待 Trae/MiniMax 执行
- 日期：2026-08-28
- 前置报告：`MASTER-mvp-review-2026-08-28-round2.md`
- 目标：修复第二次综合验收中仍未闭环的真实功能问题
- 执行方式：一次性完成，内部自行开发、测试和修复，最后一次性汇报

## P0：必须优先修复

### 1. 统一工作台 API 前后端响应契约

当前 `frontend/src/api/workbench.js` 的独立 Axios 实例对裸业务对象返回 `body`，但多个页面仍读取 `res.data.*`。

必须二选一并全量统一：

- 统一后端工作台接口返回 `{ code, msg, data }`，前端保持 `res.data.*`；或
- 统一前端工作台页面和 Store 直接读取裸业务对象 `res.*`。

推荐建立明确的工作台 API adapter，并统一以下页面：

- WorkbenchView
- NotesView
- NoteEditorView
- AssetsView
- TasksView
- AssistantView
- TrashView

必须新增真实接口契约测试：使用真实 FastAPI TestClient 调用工作台接口，验证前端 adapter 实际能读取 summary/list/id 等字段；不能只用手工 mock `{ data: ... }`。

### 2. 私有图片/PDF 预览必须真正接入页面

当前虽有 `fetchBlob()`，但页面仍使用不存在或未鉴权的 `previewUrl()`，且原生 `<img>`/`<iframe>` 不会携带 Bearer Token。

必须：

- `AssetsView` 使用鉴权 fetch 获取 blob，再生成 object URL；
- `NoteEditorView` 插入图片时使用可鉴权的资源方案；
- PDF 预览/下载同样必须通过鉴权；
- 组件卸载或资源替换时释放 `URL.revokeObjectURL()`；
- 未登录和其他用户不能访问文件；
- 不得把资源接口改成匿名公开。

增加真实测试：登录用户可访问，未授权用户和其他用户返回 401/404/403 中合理的一种。

## P1：必须修复

### 3. 粘贴图片和拖拽图片

`NoteEditorView.vue` 必须支持：

- `clipboardData.items` / `clipboardData.files` 获取图片；
- 粘贴图片后上传并插入编辑器；
- `dragover` 阻止默认行为；
- `drop` 获取图片文件并上传；
- 非图片粘贴仍保留纯文本行为；
- 上传失败有提示。

增加可测试的纯函数或组件行为测试，不能只写事件名称。

### 4. AI 调用严格执行 preview → 确认 → invoke

当前 NoteEditorView 仍在打开预览后立即 invoke，AssistantView 仍直接 invoke。

必须：

- 点击 AI 操作只调用 preview；
- 显示发送范围、字符数和脱敏提示；
- 用户点击确认后才 invoke；
- 用户取消时不得 invoke；
- NoteEditorView 和 AssistantView 使用统一流程；
- 真实测试确认取消不会调用 invoke。

### 5. AI 结果应用闭环

新增明确的后端接口，例如 `/api/workbench/ai/apply`，或等价的安全接口。

必须支持用户确认后：

- 应用摘要到笔记；
- 应用整理后的标题/正文；
- 应用标签建议；
- 创建任务草稿并由用户确认后保存。

后端必须校验 note/user/conversation 所属关系，不能只依赖前端按钮。

### 6. AI conversation_id

`AiInvokeIn` 必须显式包含 `conversation_id`，后端必须校验该会话属于当前用户且未删除。

不得继续默认写入“最近一个会话”。

AssistantView 发送时必须传当前选中的 conversation_id。

### 7. AI 对话关联内容

完成笔记、资产、任务与 AI 对话的关联闭环：

- 数据模型或关联表；
- Alembic migration；
- 后端 link/unlink/list 接口；
- 用户归属校验；
- 至少在 AssistantView 或内容详情中提供可操作入口。

如果决定缩小范围，必须同步修改 PRD 和最终汇报，不能宣称已完成。

### 8. 笔记附件加载和解绑

必须：

- `AssetOut` 返回 `note_ids`，或增加按 note_id 查询资产接口；
- NoteEditorView 加载时能显示已关联附件；
- detach 必须调用后端接口并删除 `NoteAsset` 数据；
- 增加关联、加载、解绑的真实后端测试。

### 9. 搜索分页

所有全局搜索的 note/asset/task/tag 查询必须使用：

```python
offset((page - 1) * size).limit(size)
```

并对 page/size 做正数和合理上限校验。

增加测试：第二页不重复第一页。

### 10. URL 校验

网页链接后端必须：

- 只允许 `http` / `https`；
- 限制最大长度；
- 拒绝无 scheme、用户名密码注入、明显非法 URL；
- 使用 Pydantic `HttpUrl` 或可靠标准库解析；
- 增加合法/非法 URL 测试。

### 11. 文件校验和内存处理

必须：

- 校验扩展名；
- 校验 `UploadFile.content_type`；
- 校验图片真实内容，优先使用 Pillow；
- 校验 PDF `%PDF-` 及必要内容；
- 保持图片 10 MB、PDF 50 MB 限制；
- 超限读取应采用分块或带上限读取，不要无条件把大文件全部读入内存；
- 预览/下载优先使用 `FileResponse` 或 `StreamingResponse`；
- 不能因为资源响应改造而绕过用户权限。

### 12. 回收站物理清理失败策略

物理文件删除失败时：

- 不得直接删除 Asset 数据库记录；
- 保留记录并返回/记录待重试状态；
- 支持后续重试或明确错误日志；
- 增加删除失败测试。

## 质量要求

- 不修改旧 `/home`、音乐、小说、视频、日志、工具业务逻辑。
- 不使用真实密码、Token、API Key。
- 不连接生产服务器。
- 不执行生产迁移。
- 不推送 GitHub。
- 不全量格式化旧代码。
- 所有新增表/字段使用 Alembic migration。
- 不修改测试来掩盖功能问题。
- 不能用 fake provider 的返回值宣称真实 AI 调用完成；没有真实配置时要明确 fake 状态。

## 必须验证

```text
python -m compileall -q backend/app backend/tests backend/alembic
pytest backend/tests -q
pip check

cd frontend
npm run build
npm run test
```

还必须实际验证：

- 真实 API 响应能被真实页面读取；
- 私有图片/PDF 登录可预览，未授权不可访问；
- 粘贴和拖拽图片上传；
- AI 取消时不 invoke，确认后才 invoke；
- AI 结果确认后才能写入；
- conversation_id 只写入当前选中会话；
- 附件关联加载和解绑真实落库；
- 搜索第二页不重复第一页；
- URL 非法输入被拒绝；
- 文件 MIME、内容和大小限制有效；
- 文件删除失败不会丢数据库记录；
- PWA 不缓存认证 API；
- 测试数据库、上传测试文件、缓存和 `__pycache__` 已清理。

## 完成汇报格式

```text
第二轮返工状态：
修改文件：
API 契约：
私有资源鉴权：
粘贴图片：
拖拽图片：
AI preview/确认/invoke：
AI 结果应用：
conversation_id：
AI 对话关联：
附件加载和解绑：
搜索分页：
URL 校验：
文件 MIME/内容/大小校验：
文件响应方式：
回收站清理失败策略：
后端测试：
前端构建：
前端测试：
lint：
pip check：
compileall：
测试产物清理：
未解决问题：
```

完成后告诉用户：

```text
玄黄 MVP 第二轮集中返工已完成，请检查
```

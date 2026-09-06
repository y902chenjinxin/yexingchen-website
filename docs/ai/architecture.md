# 玄黄技术架构草案

- 状态：待 PRD 评审
- 日期：2026-08-27

## 1. 总体原则

1. 在现有 Vue 3 + FastAPI + SQLite 项目上增量开发。
2. 工作台与旧岛屿模块并存，不做第一阶段大规模重构。
3. 业务对象统一为“内容资产 + 笔记 + 任务 + AI 对话”。
4. 文件存储通过接口隔离，MVP 使用服务器本地磁盘。
5. AI 通过 Provider 接口隔离具体云服务商。
6. 所有新增数据结构使用迁移，不依赖生产启动时自动建表。

## 2. 前端

现有技术栈继续使用：Vue 3、Vite、Vue Router、Pinia、Element Plus、Axios。

建议新增边界：

```text
frontend/src/
├─ api/workbench.js
├─ api/notes.js
├─ api/assets.js
├─ api/tasks.js
├─ api/assistant.js
├─ stores/workbench.js
├─ stores/notes.js
├─ stores/tasks.js
├─ views/WorkbenchView.vue
├─ views/NotesView.vue
├─ views/NoteEditorView.vue
├─ views/AssetsView.vue
├─ views/TasksView.vue
├─ views/AssistantView.vue
└─ views/TrashView.vue
```

实际文件命名可跟随仓库现有风格，但不要修改旧模块以外的文件。

## 3. 后端

建议新增路由：

```text
/api/workbench
/api/notes
/api/assets
/api/tasks
/api/assistant
/api/ai/conversations
/api/trash
```

建议新增服务边界：

```text
backend/app/
├─ routers/workbench.py
├─ routers/note.py
├─ routers/asset.py
├─ routers/task.py
├─ routers/assistant.py
├─ services/storage_service.py
├─ services/ai_service.py
├─ services/providers/
└─ migrations/
```

具体模块名可以根据现有代码约定调整，但路由、服务和数据访问不要全部堆进 `main.py` 或单个 Router 文件。

## 4. 文件存储

### MVP

- 根目录建议由环境变量配置，例如 `UPLOAD_DIR`。
- 图片和 PDF 以 UUID 或安全随机名保存，不直接使用用户原始文件名作为物理路径。
- 数据库保存原始文件名、MIME、大小、相对路径和状态。
- 下载和预览接口必须经过当前用户权限校验。
- 删除先写入回收站状态，物理删除由清理任务完成。

### 后续

实现同一 `StorageService` 接口的 COS Provider，不让业务代码直接依赖 COS SDK。

## 5. AI

业务代码只调用统一接口，例如：

```text
organize_note(content) -> structured_result
summarize_note(content) -> summary
suggest_tags(content) -> tags
suggest_task(content) -> task_draft
```

Provider 负责：

- API 地址
- 模型名称
- API Key
- 超时
- 重试
- 错误转换
- 调用统计

调用前由后端生成待发送内容预览；敏感信息过滤必须在后端再次执行。AI 返回的结构化结果先作为建议，用户确认后再写入笔记、标签或任务。

## 6. 数据库迁移

现有代码使用 `Base.metadata.create_all`，但工作台新增表不应依赖该方式变更生产数据库。Coding 模型需要先确认仓库是否已有迁移工具；如果没有，应先建立最小可用迁移机制，再新增工作台表。

## 7. PWA

- 增加 Web App Manifest。
- 增加 Service Worker，仅缓存静态壳和稳定资源。
- 网络请求和数据操作默认走服务器，不设计离线写入队列。
- 登录和敏感数据不写入不受控的长期缓存。

## 8. 风险与停止条件

遇到以下情况必须暂停并反馈，不自行扩大范围：

- 需要迁移或删除现有生产数据。
- 需要改变 SQLite 以外的数据库方案。
- 需要重新创建云存储并产生费用。
- 需要选择具体 AI 供应商并提交 API Key。
- 需要改变认证、权限或文件公开策略。
- 现有旧模块与新工作台发生不可逆的数据耦合。

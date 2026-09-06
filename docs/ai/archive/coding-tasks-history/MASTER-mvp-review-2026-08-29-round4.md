# 玄黄 MVP 综合验收报告（第四次）

- 日期：2026-08-29
- 结论：有条件通过；不建议直接生产上线
- 评审人：Codex

## 自动化结果

- 后端测试：105 passed，26 warnings
- 前端测试：89 passed
- 前端构建：通过
- Alembic 全新数据库升级和幂等执行：通过
- 测试数据库、缓存、上传目录和本轮生成的 `__pycache__`：已清理

## 已确认通过

- 工作台 API 统一返回 `{code, msg, data}`，真实 HTTP 请求已核对。
- `/workbench`、笔记、资产、任务、AI、回收站路由存在。
- 登录后默认进入 `/workbench`，旧 `/home` 和旧模块保留。
- 笔记草稿自动保存和完成状态实现存在。
- 图片/PDF 使用鉴权 fetch + Blob/Object URL 预览，后端文件接口保留用户权限校验。
- 图片粘贴和拖拽处理已实现；拖拽图片插入 `data-asset-id` 持久化占位，PDF 使用安全占位链接。
- AI AssistantView 已实现 preview → 用户确认 → invoke(conversation_id) → 结果确认 → apply。
- NoteEditorView 的 AI 摘要、整理、标签和任务应用闭环存在。
- AI 对话关联模型、迁移和 link/unlink/list 接口存在。
- 附件列表、关联和解绑接口存在，笔记图片通过 asset ID 在加载时 hydrate。
- 搜索分页使用 offset/limit，URL、MIME、图片/PDF内容和大小校验存在。
- 回收站文件删除失败时保留 Asset 记录并记录失败状态。
- PWA manifest 和 Service Worker 存在，Service Worker 跳过认证 API。

## 上线前必须修复

### P1：富文本 HTML 清洗不完整

`frontend/src/utils/note-assets.js` 的 `sanitizeNoteHtml()` 使用 DOMParser，但只专门处理 `img` 和内部 PDF 链接，没有明确移除：

- `<script>` 等危险标签；
- 任意元素上的 `onerror`、`onclick` 等事件属性；
- `javascript:` 等普通链接的危险 scheme；
- 其他可执行 HTML 属性。

当前编辑器多数输入路径较安全，但笔记 HTML 会持久化并再次通过 `innerHTML` 渲染；AI 整理结果、历史数据或绕过前端的请求可能形成存储型 XSS。应使用成熟 sanitizer（如经过评估的 DOMPurify）或实现明确的允许标签/属性白名单，并增加脚本、事件属性和危险 URL 测试。

### P1：资产下载交互存在异步竞态

`frontend/src/views/AssetsView.vue` 的下载锚点初始 `href` 是 `#`，点击后异步调用 `fetchBlob()` 再设置 object URL，但没有阻止默认行为。资源尚未预览完成时点击，浏览器可能先执行 `#` 默认导航，导致下载不稳定。应使用按钮 + `event.preventDefault()`，获取 Blob 后显式创建临时下载链接并触发点击，再释放 URL；或确保下载状态和 href 更新逻辑无竞态。

## 质量遗留

- 新增/修改前端文件 lint 仍有 3 个 error：`NoteSelect.vue` 未使用 `computed`、`AssetsView.vue` 未使用 `isAssetPlaceholder` 和 `escapeHtml`；另有大量格式 warning。应在合并前修复新增文件自身的 error，但不必全量格式化旧代码。
- 前端构建仍有 Vite CJS API 和大 chunk 警告。
- 后端仍有 Pydantic、SQLAlchemy、datetime 弃用警告。
- 文件上传虽已分块读取，但仍在内存中累积到上限后保存；个人 MVP 可接受，后续可改成临时文件流式写入。
- AI 当前默认 fake provider；未配置真实供应商时不能宣称云端 AI 已可用。
- 当前未连接服务器、未执行生产迁移、未部署、未推送 GitHub。

## 验收结论

玄黄 MVP 的主要功能和核心测试已经达到可继续集成的程度，但由于富文本 XSS 防护和下载交互仍有上线风险，当前结论为“有条件通过，不准直接生产上线”。先集中修复上述两个 P1 和新增 lint error，再做一次最终验收。

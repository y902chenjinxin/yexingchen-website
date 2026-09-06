# 玄黄 MVP 上线前最终验收报告

- 日期：2026-08-30
- 结论：有条件通过，暂不建议直接上线
- 评审人：Codex

## 验证结果

### 通过

- 后端完整测试：105 passed，26 warnings。
- 前端构建：`npm run build` 通过。
- 前端关键单文件测试：
  - AssistantView：19/19；
  - AssetsView：7/7；
  - fetch-blob：5/5；
  - XSS audit：35/35。
- Alembic 全新数据库升级、current、幂等升级：通过。
- `pip check`：通过。
- `compileall`：通过。
- 真实 API 契约：工作台接口返回 `{code,msg,data}`，已验证。
- 资源鉴权：后端用户权限校验 + 前端鉴权 Blob/Object URL，已验证代码路径和后端测试。
- AI AssistantView：preview → 确认 → invoke(conversation_id) → 结果确认 → apply，代码和单文件测试已验证。
- 笔记图片：使用 `data-asset-id` 持久化，加载时 hydrate，不把 blob URL 作为永久引用。
- 粘贴/拖拽图片和 PDF：代码路径与工具测试存在，拖拽图片会插入持久化占位。
- 搜索分页、URL/MIME/内容/大小校验、回收站删除失败保留记录：后端测试通过。
- 测试数据库、上传目录、缓存和 `__pycache__`：已清理。

### 未通过的最终质量门槛

#### 1. 完整 `npm run test` 聚合运行不稳定/失败

首次完整并行运行出现 worker 超时；使用 `--no-file-parallelism --maxWorkers=1` 串行运行后仍出现 4 个失败：

- `assistant-view.test.js`：2 个超时/调用次数问题；
- `assets-view.test.js`：1 个超时；
- `fetch-blob.test.js`：1 个超时；
- 聚合结果：3 个测试文件失败，4 个测试失败，7 个 unhandled worker errors。

随后分别单独运行这三个文件，结果均通过：

- AssistantView：19/19；
- AssetsView：7/7；
- fetch-blob：5/5。

这说明问题可能是测试文件之间的全局 mock/资源隔离或 worker 配置不稳定，但项目默认 `npm run test` 仍不能稳定一次通过，不能忽略。

#### 2. 新增/修改文件 lint 仍有 3 个 error

定向 lint 发现：

- `frontend/src/components/common/NoteSelect.vue`：未使用 `computed`；
- `frontend/src/views/NoteEditorView.vue`：未使用 `isAssetPlaceholder`；
- `frontend/src/views/NoteEditorView.vue`：未使用 `escapeHtml`。

此外仍有大量格式 warning。旧代码 warning 不要求本轮全量清理，但新增/修改文件自身 error 应在合并前修复。

## 不阻塞上线但需记录

- 前端构建仍有 Vite CJS API 弃用和主包约 1.09 MB 警告。
- 后端仍有 Pydantic、SQLAlchemy、datetime 弃用警告。
- 文件上传虽然分块读取并设置上限，但仍会累积到最大文件大小的 bytes 后保存；个人 MVP 可接受，后续可改为临时文件流式写入。
- AI 默认是 fake provider；未配置真实云端 AI 供应商时，AI 功能只用于本地流程验证，不能宣称已经接通真实云端服务。
- 尚未连接生产服务器、执行生产迁移、部署或推送 GitHub。
- HTTPS 证书此前已确认过期，正式上线前必须更换并核验。
- MVP 明确不做备份，用户已接受服务器故障导致的数据丢失风险。

## 最终结论

玄黄 MVP 的主要业务代码、后端行为和核心前端流程已基本完成，安全关键路径也已补齐；但默认前端测试命令不稳定且新增文件仍有 lint error。因此结论为：

```text
功能层面：基本通过
工程质量层面：有条件通过
生产上线：暂不允许
```

上线前至少完成：

1. 修复新增/修改文件的 3 个 lint error；
2. 解决前端完整测试的聚合不稳定，确保 `npm run test` 一次通过；
3. 由用户决定并完成真实 AI 供应商配置；
4. 更换 HTTPS 证书；
5. 另行完成生产迁移演练和部署确认。

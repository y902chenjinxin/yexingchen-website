# 玄黄 MVP 最终质量门禁修复

## 必须修复

1. 修复新增/修改文件的 3 个 lint error：
   - `frontend/src/components/common/NoteSelect.vue` 未使用 `computed`；
   - `frontend/src/views/NoteEditorView.vue` 未使用 `isAssetPlaceholder`；
   - `frontend/src/views/NoteEditorView.vue` 未使用 `escapeHtml`。
2. 解决 Vitest 完整 `npm run test` 聚合运行失败：
   - 保留单文件测试通过；
   - 检查全局 mock、模块缓存、fake timers、JSDOM 导航和 worker 配置；
   - 不要通过简单提高 timeout 掩盖竞态；
   - 默认 `npm run test` 必须一次通过。
3. 不修改业务范围，不连接生产，不部署，不推送 GitHub。

## 必须验证

```text
python -m compileall -q backend/app backend/tests backend/alembic
pytest backend/tests -q
pip check

cd frontend
npm run build
npm run test
```

并执行定向 lint：

```text
npx eslint src/views/AssistantView.vue src/views/NoteEditorView.vue src/views/AssetsView.vue src/utils/note-assets.js src/utils/paste-drop.js src/api/workbench.js src/components/common/NoteSelect.vue src/stores/workbench.js
```

要求：

- `npm run test` 一次通过；
- 定向 lint error 为 0；
- 测试数据库、上传文件、缓存和 `__pycache__` 清理；
- 完成后再交 Codex 最终验收。

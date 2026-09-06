# 玄黄 MVP 第三轮集中修复任务

## 目标

完成第三次综合验收报告中的剩余问题。一次性执行，完成后再交 Codex 综合验收。

## 必须修复

1. AssistantView 完整接入 AI 流程：
   - 当前选中 conversation_id；
   - preview；
   - 显示发送范围；
   - 用户确认/取消；
   - 确认后 invoke；
   - 展示 fake/真实 provider 标识；
   - 结果需要确认后 apply；
   - 发送和取消均有真实测试。
2. 修复笔记图片持久化：不能把 `blob:` URL 写入数据库作为永久内容。使用资产 ID/data 属性或其他持久化引用，加载时重新鉴权生成 object URL。
3. 修复拖拽图片：上传后插入正文；拖拽 PDF 作为安全附件占位；释放 object URL。
4. 确认 NoteEditor 四种 AI apply 能力真实闭环：摘要、整理、标签、任务草稿。

## 约束

- 不连接生产服务器。
- 不执行生产迁移。
- 不推送 GitHub。
- 不使用真实密钥。
- 不删除旧模块。
- 不修改测试来掩盖问题。
- 所有 schema 变更使用 Alembic。

## 必须验证

```text
python -m compileall -q backend/app backend/tests backend/alembic
pytest backend/tests -q
pip check

cd frontend
npm run build
npm run test
```

另需验证：

- AssistantView 取消不 invoke；确认才 invoke；携带 conversation_id。
- AssistantView 可应用 AI 结果或明确显示不可应用原因。
- 笔记刷新后图片仍能通过资产 ID重新加载。
- 拖拽图片出现在笔记正文和附件列表。
- 拖拽 PDF 可作为安全附件使用。
- 测试数据库、上传文件、缓存和 `__pycache__` 已清理。

完成后汇报：

```text
第三轮返工状态：
修改文件：
AssistantView AI 流程：
AI 结果应用：
图片持久化：
拖拽图片/PDF：
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

玄黄 MVP 第三轮集中返工已完成，请检查

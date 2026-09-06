# 玄黄 MVP 综合验收报告（三次）

- 日期：2026-08-29
- 结论：不通过，仍需集中返工
- 评审人：Codex

## 自动化结果

- 后端：105 passed，26 warnings
- 前端：43 passed
- 前端构建：通过
- Alembic 全新数据库升级/幂等验证：通过
- 测试产物：本轮已清理测试数据库、缓存、`__pycache__` 和上传测试文件

## 仍未通过的关键问题

### P0/P1-1：AssistantView 仍绕过 AI 预览确认和会话绑定

文件：`frontend/src/views/AssistantView.vue`

当前仍是：

```js
workbenchApi.ai.invoke({ ability: 'summarize', content: text })
```

缺少：

- `ai.preview`
- 用户确认/取消界面
- `conversation_id`
- `ai.apply`
- 结果应用确认

后端已经要求 `conversation_id`，因此 AssistantView 的真实发送流程会与后端契约不一致，聊天页无法按当前选中的会话稳定工作；同时违反“preview → 确认 → invoke”。

必须改为：

```text
输入内容
→ preview
→ 显示发送范围
→ 用户确认
→ invoke(conversation_id)
→ 展示结构化结果
→ 用户确认后 apply
```

### P1-2：笔记图片把临时 Blob URL 持久化到数据库

文件：`frontend/src/views/NoteEditorView.vue`

图片上传后执行：

```js
document.execCommand('insertImage', false, objectUrl)
```

随后自动保存会把 `blob:` URL 写入笔记 HTML。Blob URL 只在当前浏览器页面生命周期有效，刷新页面或重新打开笔记后，图片引用会失效。

必须采用可持久化引用：

- 使用资产 ID/自定义 data 属性保存；
- 加载笔记时通过鉴权 Blob 重新替换为 object URL；或
- 采用其他明确的私有资源渲染方案。

不能把临时 `blob:` URL 作为永久笔记内容保存。

### P1-3：拖拽图片只上传/关联，没有插入编辑器

`onDrop()` 对文件调用 `uploadFile(f)`，但没有像点击上传和粘贴图片一样把图片插入编辑器。用户拖入图片后只能在附件列表看到，正文中没有图片。

必须：

- 图片拖拽上传后插入正文；
- PDF 拖拽可以作为附件并插入安全的 PDF 占位链接；
- 非支持文件提示并忽略。

### P1-4：AI apply 前端闭环只在 NoteEditor 部分实现

NoteEditor 已有部分 `ai.apply` 逻辑，但需要确认四种能力的真实 payload 和结果：

- 摘要写入；
- 整理标题/正文写入；
- 标签写入；
- 任务创建。

AssistantView 完全没有应用流程，必须补齐或明确缩小产品范围。

## 需要复核的质量项

- 生产 schema guard 的 head revision 仍为常量，未来新增迁移容易忘记同步；建议动态读取唯一 head。
- 上传读取是分块读取但仍累积成完整 bytes 后再保存，50 MB 文件仍会占用同等内存；个人 MVP 可接受但不是严格流式上传。
- PWA、资源鉴权和 URL 校验已有实现，但应补充浏览器级验证而非只测工具函数。
- 新增前端文件 lint 仍有历史/新增错误和大量 warning；本轮不要求全量格式化，但新增代码应至少修复自身 error。
- 项目文档和错误注释存在编码显示异常，需确认文件实际 UTF-8 内容未被错误转码。

## 已通过的内容

- 工作台路由、登录跳转和旧模块保留。
- 后端工作台 API `{code,msg,data}` 契约。
- 图片/PDF 后端权限校验和 FileResponse。
- Blob fetch 工具存在，AssetsView 已接入。
- 粘贴图片工具和 NoteEditor 粘贴流程存在。
- 搜索 offset 分页。
- URL http/https 校验。
- 图片 Pillow 内容校验、PDF magic 校验、MIME 校验和大小限制。
- 回收站物理删除失败保留记录并标记失败。
- AI 后端 Provider、preview、invoke、apply、conversation_id 和内容关联接口存在。
- 前后端自动化测试和构建通过。

## 验收结论

第三次仍不能标记“玄黄 MVP 完成”，也不建议部署生产。先集中修复 AssistantView AI 流程、Blob URL 持久化和拖拽插入正文，再进行第四次综合验收。

# Batch 01：生产迁移保护 + 工作台壳层 + PWA 基础

## 任务状态

- 状态：待执行
- 负责人：MiniMax Coding 模型
- 设计/评审：当前助手
- 范围：Task 002.1.1 + Task 003 基础部分

## 必读文件

```text
D:\software\codex\codex_work\docs\ai\prd.md
D:\software\codex\codex_work\docs\ai\architecture.md
D:\software\codex\codex_work\docs\ai\data-model.md
D:\software\codex\codex_work\docs\ai\coding-tasks\002.1.1-production-schema-guard.md
D:\software\codex\codex_work\yexingchen-website\docs\README.md
```

## 本批次目标

### A. 生产数据库迁移保护

1. `ENV=production`、`ENV=PRODUCTION`、`ENV=Production` 行为一致。
2. 生产环境不得执行 `Base.metadata.create_all()`。
3. 生产环境启动前检查数据库 Alembic revision：
   - 必须存在 `alembic_version`；
   - 必须有当前数据库 revision；
   - 必须匹配迁移脚本的唯一 head；
   - 空数据库、未迁移数据库、版本落后、版本不匹配或多 head 时拒绝启动；
   - 异常或日志明确提示先执行 `alembic upgrade head`；
   - 不输出数据库密码、Token、API Key 或完整连接串。
4. 已执行 `alembic upgrade head` 的生产数据库可以启动。
5. 非生产环境继续保留现有 `create_all` 行为。
6. `docs_url` 和 `redoc_url` 使用与 schema 检查相同的规范化环境值；所有大小写形式的 production 都关闭 `/docs` 和 `/redoc`。

### B. 工作台页面壳层

1. 新增 `/workbench` 路由，要求登录。
2. 登录成功后默认跳转 `/workbench`。
3. 原 `/home` 浮空岛首页和现有旧模块路由继续保留。
4. 新增工作台首页，至少包含以下入口或占位区：
   - 快速记录
   - 全局搜索
   - AI 助手入口
   - 今日任务
   - 最近编辑
   - 待整理草稿
   - 分类和标签入口
5. 页面使用产品名“玄黄”，但不要在本批次重做完整品牌视觉。
6. 工作台必须有清晰的空状态，不要伪造已经存在的笔记/任务数据。
7. 桌面端和手机宽度下均可正常布局。
8. 工作台应提供进入旧 `/home`、音乐、小说、视频、日志、工具模块的入口。
9. 本批次只做页面骨架和导航，不实现笔记、资产、任务或 AI 业务接口。

### C. PWA 基础

1. 增加 Web App Manifest，显示名称使用“玄黄”。
2. 使用仓库内已有 favicon/图标；如现有图标不满足 manifest 尺寸要求，先采用安全的已有资源，不在本批次引入新的品牌设计。
3. 增加基础 Service Worker 或等价 PWA 注册机制，只缓存静态应用壳和稳定资源。
4. 不缓存需要认证的 API 响应，不实现离线编辑、离线附件、离线同步。
5. PWA 仍然要求联网使用。
6. 不为了 PWA 引入大型新依赖；如确需新增依赖，必须说明原因。

## 允许修改范围

优先只修改：

```text
backend/app/main.py
backend/app/ 下与 schema 检查直接相关的最小文件
backend/tests/test_production_env.py
frontend/src/router/index.js
frontend/src/main.js
frontend/src/views/WorkbenchView.vue
frontend/src/ 下工作台所需的最小组件或样式文件
frontend/public/manifest.webmanifest
frontend/public/sw.js
frontend/index.html
frontend/tests/ 中工作台/路由测试
.gitignore
docs/README.md
```

如果必须修改其他文件，完成汇报时列出原因。

## 禁止事项

- 不新增 Note、Asset、Tag、Task、AIConversation 等业务表。
- 不新增笔记、图片、PDF、网页、任务或 AI API。
- 不修改旧音乐、小说、视频、日志、工具业务逻辑。
- 不删除或重写 `/home`。
- 不连接生产服务器。
- 不执行生产迁移。
- 不推送 GitHub。
- 不使用真实密钥。
- 不全量格式化旧代码。
- 不用 mock 数据冒充已经实现的业务数据。

## 必须测试

后端：

```text
python -m compileall -q backend/app backend/tests backend/alembic
pytest backend/tests -q
pip check
```

必须覆盖：

```text
生产空数据库导入失败
生产未迁移数据库导入失败
生产已迁移到 head 的数据库导入成功
生产版本不匹配导入失败
production / PRODUCTION / Production 的 docs/redoc 均关闭
非生产环境继续通过现有测试
```

前端：

```text
cd frontend
npm run build
npm run test
```

必须验证：

```text
登录后目标为 /workbench
/home 仍然存在
旧模块路由仍然存在
工作台页面可以加载
manifest 可被构建产物访问
Service Worker 注册不会阻塞正常启动
桌面和移动端布局没有明显溢出
```

完成后清理：

```text
backend/test.db
backend/*.db（仅清理由本批次测试生成的文件，不触碰用户已有数据库）
backend/.pytest_cache
backend/**/__pycache__
```

## 验收标准

- [ ] 生产 schema 检查真实运行，不是只检查代码字符串。
- [ ] 生产数据库未到唯一 Alembic head 时启动失败。
- [ ] 生产数据库到 head 时启动成功。
- [ ] 非生产环境现有测试通过。
- [ ] `/docs`、`/redoc` 的 production 大小写行为统一。
- [ ] 登录后进入 `/workbench`。
- [ ] `/home` 和旧模块不受破坏。
- [ ] 工作台页面包含规定的入口和空状态。
- [ ] 手机和桌面布局可用。
- [ ] PWA manifest 和基础 Service Worker 生效。
- [ ] 不新增业务表、业务 API 或真实凭证。
- [ ] 后端测试通过。
- [ ] 前端构建通过。
- [ ] 前端测试通过。
- [ ] pip check 和 compileall 通过。
- [ ] 测试产物已清理。

## 完成后汇报格式

```text
修改文件：
生产 schema 检查：
空数据库结果：
未迁移数据库结果：
已迁移 head 结果：
版本不匹配结果：
ENV 大小写与 docs/redoc：
workbench 路由：
登录跳转：
旧路由回归：
PWA manifest：
Service Worker：
响应式验证：
后端测试：
前端构建：
前端测试：
pip check：
compileall：
清理情况：
未解决问题：
```

## 偏差处理

- 只要涉及数据库 schema、认证权限、生产部署、文件存储或 AI 数据发送，必须停止并汇报，不自行扩大本批次。
- 低风险的局部 UI 或测试问题可以保守修复并记录。
- 如果现有代码与本任务冲突，以现有源码和测试为事实来源，同时在汇报中说明。

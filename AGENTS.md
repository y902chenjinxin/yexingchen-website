# 玄黄项目协作规则

## 项目定位

- 产品名称：玄黄
- 产品类型：单用户个人工作台
- 当前代码目录：本仓库
- 产品资料目录：`D:\software\codex\codex_work\docs\ai`

## 模型分工

### MiniMax Coding 模型

由 MiniMax 作为主力执行模型，负责：

- 读取项目资料和总任务单
- 需求实现方案细化
- 前端和后端代码开发
- 数据库迁移
- 测试编写和运行
- 常规问题修复
- 文档和结果报告

### 当前助手（Codex）

由当前助手在总任务完成后负责：

- 独立检查代码改动范围
- 检查产品需求和架构是否被偏离
- 检查数据库迁移、认证、权限和文件安全
- 复跑关键测试
- 检查部署和回滚方案
- 最终验收或生成集中返工意见

### 用户

用户负责：

- 确认产品方向和取舍
- 操作服务器、域名、证书、云控制台和密钥
- 确认生产部署、GitHub 推送、删除数据等不可逆操作
- 在总任务完成后把结果交给当前助手验收

## 开发流程

1. 先读取以下资料：
   - `D:\software\codex\codex_work\docs\ai\PROJECT_BRIEF.md`
   - `D:\software\codex\codex_work\docs\ai\CURRENT_STATE.md`
   - `D:\software\codex\codex_work\docs\ai\prd.md`
   - `D:\software\codex\codex_work\docs\ai\architecture.md`
   - `D:\software\codex\codex_work\docs\ai\data-model.md`
   - `D:\software\codex\codex_work\docs\ai\coding-tasks\MASTER-mvp-implementation.md`
2. 作为一个完整总任务连续实施，不要求用户在内部阶段之间传话。
3. 可以在内部按阶段开发、运行局部测试和修复。
4. 全部完成后再写一次完整结果报告。
5. 不要把“构建通过”或“页面占位”当作业务功能完成。
6. 结果交给当前助手做独立综合验收。

## 安全边界

- 不读取、打印、复制或提交真实密码、Token、API Key、私钥或完整数据库连接串。
- 不连接生产服务器。
- 不执行生产数据库迁移。
- 不推送 GitHub。
- 不部署或回滚生产环境。
- 不删除用户数据或项目文件，除非任务明确允许且用户已确认。
- 所有新增数据库结构使用 Alembic migration。
- AI 供应商未确定时使用 fake provider 和可配置通用 HTTP provider，不写死真实供应商。
- 生产环境不依赖 `Base.metadata.create_all()` 自动建表。

## 代码与测试要求

- 保留现有 `/home`、音乐、小说、视频、日志和工具模块。
- 不做与任务无关的全量格式化或旧代码重构。
- 修改后运行任务单要求的测试。
- 新增代码应补相应测试。
- 测试数据库、缓存、虚拟环境和构建产物不得提交。
- 完成后报告修改文件、测试命令、测试结果、未解决问题和需要用户操作的事项。

## 交接约定

MiniMax 完成总任务后，在回复中明确写出：

```text
玄黄 MVP 总任务已完成，请检查
```

然后用户只需把这句话和 MiniMax 的最终报告告诉当前助手；当前助手会读取工作区 diff 和项目文件，进行一次综合验收。

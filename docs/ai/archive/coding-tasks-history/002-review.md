# Task 002 独立验收报告

- 日期：2026-08-27
- 结论：通过（附带 P1 架构整改项）
- 评审人：当前助手

## 验证结果

| 检查项 | 结果 |
|---|---|
| Alembic 工具和目录 | 通过 |
| 新 SQLite 库 `upgrade head` | 通过 |
| 重复升级幂等性 | 通过，包含在迁移测试中 |
| 旧库 `stamp head` 接管 | 通过，包含在迁移测试中 |
| 独立 `downgrade base` | 通过 |
| 后端迁移/接口测试 | 7 passed |
| 前端构建回归 | 通过 |
| 前端单元测试回归 | 7 passed |
| `pip check` | 通过 |
| 业务代码越界修改 | 未发现 |
| 测试产物清理 | 已完成 |

## 已实现

- 使用 Alembic 管理迁移。
- 新增 baseline revision：`55655f1242a9`。
- Alembic 从 `app.config.settings.DATABASE_URL` 获取数据库 URL。
- baseline 覆盖现有 9 张业务表并创建 `alembic_version`。
- 新库、幂等升级、旧库 stamp 接管均有测试。

## 必须后续处理的架构项

`backend/app/main.py` 第 12 行仍执行 `Base.metadata.create_all(bind=engine)`。这不阻塞 Task 002 的基础设施验收，但会让应用启动继续参与 schema 创建；在新增工作台业务表前，必须由独立任务决定并落实以下方案之一：

1. 移除生产启动时的 `create_all`，统一由部署步骤执行 Alembic。
2. 仅在明确的开发/测试环境允许 `create_all`，生产禁用。
3. 用显式迁移检查替代自动建表，并在未升级时拒绝启动。

默认推荐方案 2 或 3，最终以 Coding 任务评审为准。

## 其他遗留

- `.gitignore` 未显式加入 `.pytest_cache/`。
- Python 依赖仍使用上下限，没有完整 lock 文件。
- 既有前端 lint 历史问题不在本任务范围。
- Pydantic/SQLAlchemy 弃用警告不在本任务范围。

## 验收结论

Task 002 可以标记完成。进入 Task 003 前，应先把 `create_all` 生产行为作为前置整改纳入任务单。

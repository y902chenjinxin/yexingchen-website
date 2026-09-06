# Task 002：数据库迁移基础

## 任务状态

- 状态：已完成（待评审）
- 优先级：P0
- 负责人：MiniMax Coding 模型
- 设计/评审：当前助手
- 日期：2026-08-27

## 背景

当前后端通过 `Base.metadata.create_all(bind=engine)` 在 `app/main.py` 启动时
建表，没有版本管理。无法追踪 schema 变化、不能重复执行升级、回滚成本高。
工作台 MVP 阶段会持续新增/修改表结构，需要先把迁移基础设施打好。

## 目标

为工作台新增表建立可追踪、可重复执行的迁移机制。

## 验收

- [x] 选定并记录迁移工具和目录结构。
- [x] 现有数据库可在不丢数据的前提下升级。
- [x] 迁移重复执行不会破坏数据库。
- [x] 测试环境可以创建和清理迁移后的数据库。
- [x] 不在本任务新增工作台业务表。

## 允许修改范围

实际涉及的文件：

- `yexingchen-website/backend/requirements.txt`（新增 `alembic` 依赖）
- `yexingchen-website/backend/alembic.ini`（新增）
- `yexingchen-website/backend/alembic/env.py`（新增）
- `yexingchen-website/backend/alembic/script.py.mako`（新增，alembic init 默认）
- `yexingchen-website/backend/alembic/README`（新增，alembic init 默认）
- `yexingchen-website/backend/alembic/versions/55655f1242a9_baseline_existing_tables.py`（新增）
- `yexingchen-website/backend/tests/test_migrations.py`（新增）
- `yexingchen-website/docs/README.md`（补充迁移命令与工作流）

## 禁止事项遵守

- 未修改任何工作台业务代码 / 业务模型 / 业务路由。
- 未升级业务框架版本（仅在 `requirements.txt` 追加 `alembic`）。
- 未写入任何真实密钥、Token 或服务器配置。
- 未连接生产服务器；仅在临时 SQLite 文件中验证。
- 未推送 GitHub。

## 设计与实施记录

### 迁移工具选择

选用 **Alembic**（SQLAlchemy 官方迁移工具）。理由：

- 与现有 SQLAlchemy 2.x 模型完全兼容，`target_metadata=Base.metadata` 即可启用 autogenerate。
- Python 3.13 兼容，无需额外解释器。
- 迁移以 Python 文件形式存在于仓库，便于代码评审与回滚。
- 行业标准、文档完整、学习成本低。

### 目录结构

```
backend/
├── alembic.ini                    # Alembic 入口配置
├── alembic/
│   ├── env.py                     # 加载 app.config.settings.DATABASE_URL 与 Base.metadata
│   ├── script.py.mako             # 迁移脚本模板
│   └── versions/
│       └── 55655f1242a9_baseline_existing_tables.py
└── app/
    ├── config.py                  # 提供 DATABASE_URL
    ├── database.py                # 提供 Base, engine
    └── models/                    # 现有模型（保持不变）
```

### 现有数据兼容策略

1. `env.py` 用 `app.config.settings.DATABASE_URL` 作为 `sqlalchemy.url`，
   保持单一来源。
2. baseline 迁移中所有 `op.create_table` / `op.create_index` 使用
   `if_not_exists=True`，保证：
   - 新环境直接 `alembic upgrade head` 创建所有表；
   - 已通过 `create_all()` 创建过表的老环境：
     `alembic upgrade head` 不会因表已存在报错，
     再执行 `alembic stamp head` 即可标记当前版本。
3. `Base.metadata.create_all(engine)` 保留在 `app/main.py`，
   以兼容开发期快速启动与现有 `test.db`。
4. `downgrade()` 仅用于测试环境回滚。

### 依赖策略

- `alembic>=1.13.0,<2.0.0`：跟随 SQLAlchemy 2.x 大版本，与 Python 3.13 兼容。
- 已验证安装版本：`alembic 1.19.1`、`SQLAlchemy 2.0.52`、`Mako 1.4.1`。

## 验证记录（全新 venv）

临时 venv 路径：`.fresh-venv-task002/`（验证完成后已删除）

```text
# 安装
python -m venv .fresh-venv-task002
.fresh-venv-task002\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
# -> 47 packages incl. alembic-1.19.1

# 场景 1：全新数据库
alembic upgrade head
# -> Running upgrade -> 55655f1242a9, baseline existing tables
# -> 10 tables (9 业务 + alembic_version)

# 场景 2：幂等升级
alembic upgrade head  # 二次执行，无 Running upgrade 输出，无报错

# 场景 3：数据保留
alembic upgrade head                 # 创建表
INSERT INTO users ...                 # 写入 1 行
alembic upgrade head                 # 再次执行
SELECT COUNT(*) FROM users;           # 仍为 1
# -> DATA PRESERVATION: OK

# 场景 4：老环境接管（先 create_all 建表）
Base.metadata.create_all(engine)      # 9 业务表
alembic stamp head                    # 标记版本，不动表结构
alembic upgrade head                  # no-op
# -> 所有 9 张业务表保留

# 场景 5：测试 downgrade（仅测试环境）
alembic downgrade base                # 回滚 baseline，删除所有业务表
```

## 测试结果

```text
pytest tests -q
# 7 passed, 8 warnings in 7.00s
#  - 4 个原有测试（test_api.py）
#  - 3 个新迁移测试（test_migrations.py）：
#     * test_alembic_upgrade_creates_all_tables
#     * test_alembic_upgrade_is_idempotent
#     * test_legacy_database_can_be_stamped

pip check
# No broken requirements found.

python -m compileall -q backend/app backend/tests backend/alembic
# 0 errors

# 前端（在主 venv 之外的目录运行）
cd frontend && npm run build
# built in 18.47s

cd frontend && npm run test
# Test Files 2 passed (2) / Tests 7 passed (7)
```

## 完成后汇报

```text
迁移工具：Alembic 1.19.x（SQLAlchemy 官方迁移工具）

修改文件：
- yexingchen-website/backend/requirements.txt
- yexingchen-website/backend/alembic.ini
- yexingchen-website/backend/alembic/env.py
- yexingchen-website/backend/alembic/script.py.mako
- yexingchen-website/backend/alembic/README
- yexingchen-website/backend/alembic/versions/55655f1242a9_baseline_existing_tables.py
- yexingchen-website/backend/tests/test_migrations.py
- yexingchen-website/docs/README.md

迁移工具与目录结构：
- 工具：Alembic，数据库 URL 由 app.config.settings 注入
- 入口：backend/alembic.ini
- 脚本：backend/alembic/env.py + versions/
- 模板：backend/alembic/script.py.mako
- 命名：<rev_id>_<slug>.py

测试命令：
- 后端测试：pytest backend/tests -q
- 全新环境：python -m venv .venv && .venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
- 升级迁移：alembic upgrade head
- 老环境接管：alembic stamp head

测试结果：
- 后端：7 passed（含 3 个新增迁移测试）
- pip check：No broken requirements found.
- compileall：0 errors
- 前端 build：built in 18.47s
- 前端 test：Test Files 2 passed / Tests 7 passed

未解决问题：
- 业务代码中的 Pydantic class-based Config / SQLAlchemy declarative_base() 仍会触发 deprecation warning，
  与 Task 001 报告一致，属于后续业务重构范畴，本任务未触及。
- alembic 不会自动 drop alembic_version 表本身，这是预期行为；
  若需彻底清理数据库，请删除数据库文件或手动 DROP TABLE alembic_version。
```


## 独立验收结果（2026-08-27）

- 结论：通过，允许进入后续任务；附带架构整改项。
- `pytest backend/tests -q`：7 passed。
- 前端 `npm run build`：通过。
- 前端 `npm run test`：2 个测试文件、7 passed。
- Alembic `history` / `heads`：单一 head `55655f1242a9`。
- 独立验证：新 SQLite 库 `upgrade head`、`current`、`downgrade base` 全部通过；回滚后仅保留 `alembic_version`。
- `pip check`：通过。
- 清理：测试数据库和 Python 缓存已清理。
- 后续整改：`backend/app/main.py` 仍保留 `Base.metadata.create_all()`；新增工作台表前必须明确移除、隔离或限制该启动时建表行为，使迁移成为生产 schema 的唯一入口。

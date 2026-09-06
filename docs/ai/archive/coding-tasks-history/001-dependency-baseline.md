# Task 001：依赖声明与可复现测试环境

## 任务状态

- 状态：已通过（有一个低优先级遗留项）
- 优先级：P0
- 负责人：MiniMax Coding 模型
- 设计/评审：当前助手
- 日期：2026-08-27

## 背景

当前仓库的后端 `requirements.txt` 使用宽松的最低版本约束，代码实际导入了 `Werkzeug`，测试实际需要 `pytest` 和 Starlette 测试客户端依赖。当前本地环境曾经通过额外安装依赖后完成测试，但新环境不能依赖人工补装。

前端当前基线已经通过：

- `npm run build`
- `npm run test`：2 个测试文件、7 个测试全部通过

后端当前基线在补齐本地测试依赖后通过：

- `pytest backend/tests -q`：4 个测试全部通过
- `pip check`：通过

## 目标

让开发者在一个全新的后端虚拟环境中，按照仓库文档安装依赖后，可以：

1. 导入 FastAPI 应用。
2. 运行后端测试并通过。
3. 不需要手动猜测或额外安装缺失包。
4. 获得稳定、可解释的依赖版本策略。

## 允许修改范围

优先只修改：

- `backend/requirements.txt`
- 新增 `backend/requirements-dev.txt`（如需要）
- `docs/README.md` 中后端安装说明
- `backend/tests/` 中为适配依赖环境所必需的测试配置（非业务逻辑）
- `docs/ai/` 中本任务记录

如果必须修改其他文件，先在结果中说明原因。

## 禁止事项

- 不修改工作台业务代码。
- 不修改现有 API 行为。
- 不升级整个项目的业务框架，除非为了兼容性有明确证据。
- 不把真实密码、Token、API Key 或服务器信息写入任何代码/文档。
- 不连接生产服务器。
- 不推送 GitHub。
- 不删除现有测试。
- 不用全量格式化顺便修改无关文件。

## 实施要求

1. 先检查当前 `backend/requirements.txt`、`backend/tests` 和实际 import。
2. 明确运行依赖、测试依赖、开发依赖的边界。
3. 将代码实际使用但未声明的 `Werkzeug` 纳入适当依赖文件。
4. 将后端测试需要的 `pytest` 和测试客户端依赖纳入适当依赖文件。
5. 选择兼容当前 Python 3.13 和现有代码的版本策略：
   - 可以固定版本；或
   - 使用明确上下限并提供锁定文件；
   - 不得继续只使用无法复现的宽松最低版本而不解释。
6. 更新安装文档，使全新环境可按步骤运行测试。
7. 不要把本地虚拟环境、`__pycache__` 或测试数据库提交进 Git。

## 必须执行的验证

在一个全新临时虚拟环境中：

```text
python -m venv <fresh-venv>
<fresh-venv>\Scripts\python.exe -m pip install -r backend/requirements.txt
<fresh-venv>\Scripts\python.exe -m pip install -r backend/requirements-dev.txt  # 如果新增
<fresh-venv>\Scripts\python.exe -m pytest backend/tests -q
```

同时执行：

```text
python -m compileall -q backend/app backend/tests
python -m pip check
cd frontend
npm run build
npm run test
```

## 验收标准

- [x] 全新后端环境安装后可以导入应用。
- [x] 后端 4 个测试全部通过。
- [x] 前端构建通过。
- [x] 前端 7 个单元测试全部通过。
- [x] `pip check` 通过。
- [x] 依赖文件明确包含运行和测试所需包。
- [x] 文档安装步骤与实际命令一致。
- [x] 没有新增敏感信息或依赖目录。
- [x] 变更只涉及本任务范围。

## 实施记录（由 MiniMax Coding 模型填写）

### 修改文件

- `yexingchen-website/backend/requirements.txt`：补齐 `Werkzeug`，并为全部运行依赖加 `>=x,<y` 形式的兼容版本上限。
- `yexingchen-website/backend/requirements-dev.txt`（新增）：包含 `-r requirements.txt`，并加入 `pytest` 与 `httpx`（FastAPI `TestClient` 依赖）。
- `yexingchen-website/docs/README.md`：后端安装章节补充 `requirements-dev.txt` 与 `pytest tests -q` 步骤，提示 `SECRET_KEY` 必填。

### 依赖策略

- 不锁死到具体补丁版本，采用“最低兼容版本 + 上限”策略（如 `fastapi>=0.115.0,<0.120.0`），允许 pip 拉取补丁修复但不跨大版本，避免无解释的宽松最低版本。
- 显式加入 `Werkzeug>=3.0.0,<4.0.0`，覆盖 `app/utils/file_utils.py` 的 `secure_filename`。
- 测试依赖集中在 `requirements-dev.txt`：`pytest>=8.0.0,<9.0.0`、`httpx>=0.27.0,<0.30.0`（FastAPI `TestClient` 基于 httpx）。
- 未引入 `requirements.lock` / `pip-tools` 等额外工具，避免扩大任务范围；现有 `.gitignore` 已覆盖 `venv/`、`__pycache__/`、`test.db`。

### 全新环境验证（已清理临时 venv）

- 临时 venv 路径：`.fresh-venv-task001/`（验证完成后已删除）
- `pip install -r requirements.txt` → 成功（45 个包）。
- `pip install -r requirements-dev.txt` → 成功（额外安装 pytest/httpx 等）。
- `python -m pytest tests -q` → `4 passed`。
- `python -m pip check` → `No broken requirements found.`。
- `python -m compileall -q app tests` → 无报错。
- `from app.main import app` → `IMPORT OK: 叶兴辰的个人网站 API`。
- `npm run build` → `built in 18.47s`（`dist/` 已生成）。
- `npm run test` → `Test Files 2 passed (2) / Tests 7 passed (7)`。

## 完成后必须汇报

```text
修改文件：
依赖策略：
后端安装命令：
后端测试结果：
前端构建结果：
前端测试结果：
pip check：
未解决问题：
```

## 交付给评审人的注意点

当前助手会重点检查：

- 是否真的在全新环境验证，而不是只使用已有虚拟环境。
- 是否把 `Werkzeug`、`pytest` 和测试客户端依赖声明完整。
- 是否引入过度升级或不必要的大版本变化。
- 是否修改了业务行为。
- 是否产生了锁文件、依赖目录或敏感文件污染。


## 独立验收结果（2026-08-27）

- 结论：通过
- 全新临时虚拟环境安装 `requirements-dev.txt`：通过
- 后端测试：4 passed
- `pip check`：通过
- 前端构建：通过
- 前端测试：7 passed
- 代码范围：未发现工作台业务代码变更
- 敏感信息：未发现新增真实凭证
- 清理：测试数据库和缓存已清理
- 遗留项：仓库 `.gitignore` 未显式忽略 `.pytest_cache/`，建议在后续基线整理中补充；不阻塞本任务验收

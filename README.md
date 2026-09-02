# 玄黄 · 个人工作台（yexingchen.cn）

单用户个人云存储与知识工作台，采用「云上浮空岛 + 修仙琉璃」视觉风格。
项目经历了多模型接力开发（GPT 搭框架 → MiniMax 执行 → Codex/Trae 收尾），本 README 为仓库总入口。

## 技术栈

- **前端**: Vue 3 + Vite + Pinia + Vue Router + Element Plus
- **后端**: Python FastAPI + SQLAlchemy + Alembic + JWT
- **数据库**: SQLite（本地 `backend/app.db`）
- **文件存储**: 本地 `uploads/` + 腾讯 COS（视频镜像）
- **部署**: Nginx + Uvicorn（生产 API 8000），PM2 托管
- **域名**: yexingchen.cn（HTTPS）

## 功能总览

| 模块 | 说明 | 入口路由 |
|------|------|----------|
| 登录 | 账号密码 + JWT，超管审批注册 | `/login` |
| 首页 | 云上浮空岛屿（音乐/小说/视频/日志/工具/工作台） | `/home` |
| 工作台 | 笔记 / 任务 / 资产 / AI 助手 / 个人中心 / 回收站 | `/workbench` |
| 笔记 | 富文本编辑器（上传 / 粘贴 / 拖拽图片） | `/notes` |
| 任务 | 待办管理 | `/tasks` |
| 资产 | 文件 / PDF / 图片管理 | `/assets` |
| AI 助手 | 可自定义 Provider（OpenAI 兼容） | `/assistant` |
| 全局搜索 | 跨岛屿内容搜索 | — |

## 项目结构

```
yexingchen-website/
├── backend/            # FastAPI 后端 app/、migrations/、run.py、app.db
├── frontend/           # Vue3 前端 src/（views/、router/、stores/、assets/）
├── scripts/            # 运维脚本（self_test/upload/workflow_progress/backup 等）
├── docs/               # 项目文档（含 archive/ 历史归档）
├── memory/             # 智能体记忆 / 交接文档
├── nginx/              # Nginx 反向代理配置（yexingchen.cn.conf）
├── AGENTS.md           # 多模型协作规则
├── CLAUDE.md           # 智能体操作指南
├── DEPLOY_CHECKLIST.md # 部署检查清单（上传门控读取根目录该文件）
└── SECURITY_CHECKLIST.md # 安全审查签字清单（门控检查根目录该文件）
```

## 快速启动

### 后端
```bash
cd backend
python -m venv venv
# 激活 venv（下面以 Windows 为例）
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # 填入真实配置
python run.py            # 或 uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev       # 开发
npm run build     # 生产构建 → frontend/dist
npm run test      # 单元测试
```

## 部署

`docs/README.md` 与 `DEPLOY_CHECKLIST.md` 提供完整流程，核心三步：

```bash
cd frontend && npm run build        # 1. 构建
python scripts/self_test.py         # 2. 自测（含 Workflow 记录）
python scripts/upload_server.py     # 3. 上传 dist 并自动重启后端（PM2）
```

- 健康检查：`https://yexingchen.cn/health`（**注意是 `/health`，不是 `/api/health`**）
- 回滚手册：`docs/ROLLBACK.md`

> 部署前必须逐项确认 `DEPLOY_CHECKLIST.md` 的检查项；`upload_server.py` 上传完成后会自动执行 `pm2 restart yexingchen-backend`。

## 文档导航

| 文档 | 位置 | 说明 |
|------|------|------|
| 产品需求 | `docs/PRD_v2.12.md` | 当前有效 PRD |
| 设计规范 | `docs/DESIGN_INKWASH.md` | 唯一有效设计规范 |
| 运维/智能体文档 | `docs/ai/` | 架构、数据模型、部署报告、设计评审等 |
| 变更记录 | `docs/CHANGELOG.md` | 版本变更 |
| 已知问题 | `docs/ISSUES.md` | 未解决问题 |
| 智能体记忆 | `memory/` | 交接与经验沉淀 |

## 说明

- 生产部署、GitHub 推送、删除数据等不可逆操作，由用户确认后执行。
- 设计/界面改动须先产出 `docs/ai/` 带日期方案文档再接续（见 `AGENTS.md`）。
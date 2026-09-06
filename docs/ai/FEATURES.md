# 功能模块总览

> 汇总全站已实现功能与入口，供智能体快速定位。架构细节见 `architecture.md`、`data-model.md`。

## 1. 认证与用户

- 账号密码登录 + JWT（localStorage 存储，`Authorization: Bearer`）。
- 单用户工作台；超管审批注册；`require_super_admin` 保护管理接口。
- 参考：`DECISIONS.md` ADR-001（JWT>Cookie）。

## 2. 首页 · 云上浮空岛（`/home`）

- 深色夜空 + 玉简轮播 + 五座岛屿入口（音乐 / 小说 / 视频 / 日志 / 工具）+ 工作台入口。
- 3D 浮空岛方案曾暂停，落地为 SVG+CSS 岛屿 + 微倾侧动效（见 `CLAUDE.md`）。
- 走「修仙琉璃」风格锚点：深青夜色 + 灵气青绿 + 流金点缀（`DESIGN_INKWASH.md` + xiuxian）。

## 3. 岛屿模块

| 模块 | 路由 | 说明 |
|------|------|------|
| 音乐岛 | `/music`? | 音乐上传、播放列表、搜索、下载；BGM 可配置（`global_settings.bg_music`） |
| 小说岛 | `/novel` | 电子书上传播放、管理、下载 |
| 视频岛 | `/video` | 视频链接管理；本地 + 腾讯 COS 镜像（ADR-002） |
| 日志岛 | `/log` | 操作日志记录与查看 |
| 工具岛 | `/tool` | 常用外链收藏管理 |

## 4. 工作台（`/workbench`，登录后）

路由（Vue Router + auth guard）：

| 路由 | 视图 | 说明 |
|------|------|------|
| `/workbench` | WorkbenchView | 总览（今日任务、最近笔记、资产） |
| `/notes`、`/notes/new`、`/notes/:id` | Notes / NoteEditor | 富文本笔记 |
| `/tasks` | TasksView | 待办管理 |
| `/assets` | AssetsView | 文件 / PDF / 图片资产管理 |
| `/assistant` | AssistantView | AI 助手 + Provider 配置 |
| `/profile` | ProfileView | 个人中心 |
| `/trash` | TrashView | 回收站（保留 30 天） |

均接入返回按钮（BackButton）。全局 UI 已统一修仙琉璃风格。

## 5. AI 助手（`/assistant`）

- 后端：`UserAiProvider`（Alembic migration）+ 5 个 CRUD 路由 + 测试连接。
- 能力：summarize / organize / suggest_tags / suggest_task。
- Provider 兼容 OpenAI 协议；无配置时 fallback FakeProvider。
- API Key 明文存储（已知风险）；测试连接详情需在 UI 展示（遗留）。
- 部署参考：`deployment-report-2026-09-02-ai-provider.md`。

## 6. 笔记富文本编辑器

- 支持：图片点击上传、粘贴、拖拽；assistant 集成（AI 摘要 / 结构化）。
- 编辑器为深色琉璃样式；附件（图片 / PDF）可关联。

## 7. 全局搜索

- 跨岛屿内容搜索。

## 8. PWA

- 采用 Web App Manifest + Service Worker（MVP PWA 需联网；决策见 `DECISIONS.md`）。

## 存储与运维

- 数据库：SQLite（`backend/app.db`）。MVP 已评估备份取舍（`DECISIONS.md`），`scripts/backup_db.py` + `verify_backup.py` 可做备份与校验。
- 上传：本地 `uploads/`，视频镜像腾讯 COS。
- Nginx 配置：`nginx/yexingchen.cn.conf`。
- 部署流程：`DEPLOY_CHECKLIST.md` + `scripts/upload_server.py`。

## 已知遗留（详见 `CURRENT_STATE.md`）

- dist/assets 历史 chunk 堆积（无害，index.html 未引用）。
- AI Provider 真实 Key 待用户配置。
- 工作台功能仅验证 DOM 渲染，功能级验证待用户实测。
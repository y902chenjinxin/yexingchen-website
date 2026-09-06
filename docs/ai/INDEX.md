# docs/ai 文档索引

> 运维 / 智能体工作文档统一入口。接续工作前先读本索引定位文档。
> 自 2026-09-03 起已收敛：不再新增零散逐日报告/设计审视文件，统一并入 `WORK_LOG.md`。

## A. 断档接续入口（必先读）

| 文件 | 说明 |
|------|------|
| `CURRENT_STATE.md` | **当前状态 / 最近交付 / 遗留 / 本地验证约定**（接续第一文件） |
| `WORK_LOG.md` | **逐日交付台账**：时间线、关键交付结论、开放事项、已吸收的旧文档清单 |
| `HISTORY.md` | 项目演进 / 多模型协作史 / 踩坑速查表（部署·PWA·AI·净化） |

## B. 项目基线（参考）

| 文件 | 说明 |
|------|------|
| `PROJECT_BRIEF.md` | 项目定位与边界 |
| `prd.md` / `requirements.md` / `prd-review.md` | 产品需求 / 需求细节 / 评审 |
| `architecture.md` | 架构设计（含 PWA 决策） |
| `data-model.md` | 数据模型 |
| `DECISIONS.md` | 架构决策记录（ADR） |
| `access-inventory.md` | 资源 / 权限清单 |
| `project-context.md` | 项目上下文 |

## C. 计划与模块

| 文件 | 说明 |
|------|------|
| `implementation-plan.md` | 实施计划 |
| `TODO.md` | 待办 |
| `FEATURES.md` | 功能模块总览（岛屿 / 工作台 / AI / 笔记 / PWA） |

## D. 带日期的方案 / 设计审视 / 验收文档

> 每次「设计审视 / 方案 / 决策 / 验收」存档的带日期方案文档。**结论与交付已并入 `WORK_LOG.md` / `CURRENT_STATE.md`**，此处仅作检索索引，勿再另建重复文档。

| 文件 | 主题 | 结论 |
|------|------|------|
| `WORKBENCH_TOOLS_20260904.md` | 工具统一管理 + 像素压缩 + 全站网安页脚 + 四管理页分页 | ✅ 已上线（SW v27，WORK_LOG 已记） |
| `MGMT_UX_FIX_20260904.md` | 管理页按钮互斥 + 桌宠行为 + 搜索按钮化 | ✅ 已上线（SW v17） |
| `NAV_REBRAND_PLAN_20260904.md` | 内容板块去「岛」重构 + 工具独立页 + 视频解析增强 | ✅ 已上线（SW v14） |
| `BGM_VIDEO_PARSE_PLAN_20260903.md` | 背景音乐关联音乐库 + 视频去水印 | ✅ 已上线（SW v13） |
| `PET_INTEGRATION_20260903.md` | 鲸鱼娘桌宠接入 + 体验优化 | ✅ 已上线（SW v8/v9） |
| `WORKBENCH_REDESIGN_20260903.md` | 工作台重构（玉简轮播 + 顶栏 + 弃用 /home） | ✅ 已上线（SW v10） |
| `WORKBENCH_VISUAL_QUALITY_20260903.md` | 玄素琉璃深色材质体系（视觉质感） | ✅ 已上线（SW v11） |
| `TOOL_LIBRARY_PLAN_20260904.md` | 工具库可接入 GitHub 纯前端工具推荐 | ⏳ 待用户选型后实施（尚未选） |

> `archive/` 仅存历史任务记录（`coding-tasks-history`），已并入 WORK_LOG，不再维护。

## E. 相关外部文档（仓库内，非 docs/ai）

- 设计规范：`docs/DESIGN_INKWASH.md`（**唯一生效**，勿用 DESIGN_XUANMO）
- 当前 PRD：`docs/PRD_v2.12.md`
- 部署清单：`DEPLOY_CHECKLIST.md`、`scripts/upload_server.py`
- 智能体指南：`CLAUDE.md`、`AGENTS.md`

## 约定

- 内容变更先更新本索引对应行，保持不失效。
- 新交付/里程碑**只追加进 `WORK_LOG.md + CURRENT_STATE.md` + 本索引需要时加一行**，不另建逐日报告文件。
- 历史临时报告与截图已并入 `WORK_LOG.md` 后删除，不再维护。
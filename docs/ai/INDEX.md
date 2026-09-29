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
| `WORKBENCH_COCKPIT_20260920.md` | 工作台「数据驾驶舱」升级方案（首屏五层 / KPI 升级 / 双折线 / 倒计时圆环 / 省份热力 / 数字脉动带） | ⏳ 待实施 |
| `WORKBENCH_TOOLS_20260904.md` | 工具统一管理 + 像素压缩 + 全站网安页脚 + 四管理页分页 | ✅ 已上线（SW v27，WORK_LOG 已记） |
| `MGMT_UX_FIX_20260904.md` | 管理页按钮互斥 + 桌宠行为 + 搜索按钮化 | ✅ 已上线（SW v17） |
| `NAV_REBRAND_PLAN_20260904.md` | 内容板块去「岛」重构 + 工具独立页 + 视频解析增强 | ✅ 已上线（SW v14） |
| `BGM_VIDEO_PARSE_PLAN_20260903.md` | 背景音乐关联音乐库 + 视频去水印 | ✅ 已上线（SW v13） |
| `PET_INTEGRATION_20260903.md` | 鲸鱼娘桌宠接入 + 体验优化 | ✅ 已上线（SW v8/v9） |
| `WORKBENCH_REDESIGN_20260903.md` | 工作台重构（玉简轮播 + 顶栏 + 弃用 /home） | ✅ 已上线（SW v10） |
| `WORKBENCH_VISUAL_QUALITY_20260903.md` | 玄素琉璃深色材质体系（视觉质感） | ✅ 已上线（SW v11） |
| `TOOL_LIBRARY_PLAN_20260904.md` | 工具库可接入 GitHub 纯前端工具推荐 | ⏳ 待用户选型后实施（尚未选） |
| `PC_EXPAND_PLAN_20260906.md` | 5 个 PC 端功能扩展（语音输入 / 个人记账 / 资讯推送 / 股票查看 / 证件照工具）+ 工作台首页改造（玉简只 3 张大分类 / 常用工具区 / 快速入口放下方） | ✅ 已实施（语音/记账/资讯/股票/证件照均已上线） |
| `GAMES_FIX_20260928.md` | 棋类游戏 6 项修复（交叉点 / 悔棋配额 / 对手退出 / 邀请提速）+ 两轮视觉统一（放大两栏 / 围棋对齐） | ✅ 已上线（SW `v276`，v2.40.39） |
| `PLAN_ENTERTAINMENT_GAMES_20260928.md` | 娱乐·棋类游戏框架规划（五子棋/数独/飞行棋 + 在线对战） | ✅ 已实施（v2.40.24~v2.40.39） |
| `PLAN_LIFE_TRIO_20260927.md` | 生活岛三件套（遗失物件 / 穿搭推荐 / 密码保险箱） | ✅ 已上线（SW `v249`） |
| `TOOL_POLISH_AUDIT_20260927.md` | 工具细节打磨审计（9 条真缺陷 + 响应式兜底） | ✅ 已上线（SW `v247`） |
| `TOOL_CANDIDATES_20260927.md` | 工具库候选清单（待用户选型） | ⏳ 待选型 |
| `WEB_DESIGN_CONVERGE_20260918.md` | 桌面端「深墨青玉 · Linear 产品风」收敛层 | ✅ 已上线（SW `v115`） |
| `APP_ICON_REDESIGN_20260918.md` | App 图标重设计 | ✅ 已上线 |
| `MOBILE_PRODUCT_REDESIGN_20260917.md` | 手机端产品化重设计 | ✅ 已上线 |
| `MOBILE_MODULE_VIBRANT_20260917.md` | 手机端 7 模块「灵动卡片 · 独立渐变」 | ✅ 已上线（SW `v109`） |
| `MOBILE_LAYOUT_OPTIMIZE_20260916.md` | 手机端布局优化（含横向溢出修复） | ✅ 已上线 |
| `MOBILE_SIMPLIFY_20260916.md` | 手机端简化（P0 骨架 + P1/P2 去古风） | ✅ 已上线（SW `v106`） |
| `20260915-ai-stock-analysis.md` | 股票每日研判改 AI（规则保底 + AI 增强） | ✅ 已上线 |
| `UI_REVIEW_20260915.md` | 界面审视（结论已并入 WORK_LOG） | ✅ 已吸收 |
| `WORKBENCH_VISUAL_POLISH_20260916.md` | 工作台视觉打磨 | ✅ 已上线 |
| `FEATURE_GAP_20260914.md` | 功能缺口补全（datahub / 记账报表 / RAG 知识问答） | ✅ 已上线（SW `v72`） |
| `STOCK_UI_20260914.md` | 股票模块 UI | ✅ 已上线 |
| `WEDDING_20260910.md` | 婚礼静态页 | ✅ 已上线 |
| `WHALE_OVERLAP_FIX_20260909.md` | 桌宠遮挡修复 | ✅ 已上线 |
| `AI_KNOWLEDGE_RAG_20260907.md` | AI 知识库 RAG | ✅ 已上线 |
| `SITE_AUDIT_20260907.md` | 全站审计 | ✅ 已吸收 |
| `STYLE_BENCHMARK_20260907.md` | 风格对标 | ✅ 已吸收 |
| `TOPBAR_JADE_POLISH_20260907.md` | 顶栏 / 玉简精修 | ✅ 已上线 |
| `TRAVELS_PLAN_20260907.md` / `TRAVEL_MAP_REDESIGN_20260907.md` | 旅行足迹模块 + 地图视觉升级 | ✅ 已上线（SW `v52`/`v53`） |
| `STOCKS_PLAN_20260906.md` | 股票查看模块 | ✅ 已上线（SW `v48`） |
| `GLASSMORPH_UPGRADE_20260906.md` | 全站毛玻璃质感升级 | ✅ 已上线 |
| `IDPHOTO_FRONT_20260906.md` | 证件照前端工具 | ✅ 已上线 |
| `SEARCH_GLOBAL_AND_NATIVE_AI_20260906.md` | 全局搜索 + 原生 AI | ✅ 已上线 |

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
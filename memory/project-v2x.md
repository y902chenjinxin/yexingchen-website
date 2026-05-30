---
name: project-v2x
description: v2.x分阶段开发规划（v2.1-v2.4）
metadata:
  type: project
---

## v2.x分阶段规划

| 版本 | 名称 | 功能 | 状态 |
|------|------|------|------|
| v2.1 | 初窥门径 | 鼠标轨迹 + 修为印章 + hover特效 + 顶栏优化 | ✅ 已完成 |
| v2.2 | 渐入佳境 | 装饰层 + 每日运势 + 天象系统 | 待开发 |
| v2.3 | 融会贯通 | 键盘导航 + 手势控制 + 音效集成 | 待开发 |
| v2.4 | 天人合一 | 随机事件 + 编年史 + 灵根测试 + 转场 | 待开发 |

## 规划文档
- `docs/PRD_v2.1_2.4_PLAN.md` - 详细阶段规划

## 待清理文件
清理时间：v2.x全部完成后

| 类别 | 目录/文件 |
|------|-----------|
| Components | `components/layers/`, `components/particles/`, `components/transition/` |
| Composables | `useBreathCycle.js`, `useEntranceAnimation.js`, `useParticleSystem.js` |
| Views | `views/islands/` |
| 临时 | `check_css.py`, `check_server.py`, `cookies.txt` |
| 文档 | `PRD_v2.0_SCHEME_REVIEW.md`, `TECH_DESIGN_v2.md`, `project-v200.md` |

## 当前版本
v1.8.0（生产环境运行中，git master分支）

## 下一步
等待用户确认 v2.x 规划后，从 v2.1 开始开发
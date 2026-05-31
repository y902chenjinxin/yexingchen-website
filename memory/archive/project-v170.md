---
name: project-v170
description: v1.7.0~v1.7.2 玄墨流金设计系统上线，岛屿公转效果
metadata:
  type: project
---

## v1.7 项目记录

**版本**: v1.7.0 / v1.7.1 / v1.7.2
**完成日期**: 2026-05-29

### 主要变更

- v1.7.0: 玄墨流金设计系统上线，岛屿环形公转，登录时序优化（3.3s→1.6s）
- v1.7.1: 登录卡片延迟优化（1600ms→1000ms）
- v1.7.2: 登录动画过渡加快（0.8s→0.4s），粒子风/光环同步

### 相关文档

- PRD_v1.7_SCHEME_REVIEW.md — v1.7 评审文档
- DESIGN_XUANMO.md — 设计系统规范
- CHANGELOG.md — 变更记录

### 技术要点

- HomeView.vue: CSS animation orbit-around 实现公转，hover暂停+自身旋转
- LoginView.vue: TIMING常量控制动画时序
- variables.css: 新增 --color-bg-dark, --color-gold, --color-qi-primary 等
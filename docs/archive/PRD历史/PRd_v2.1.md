# PRD v2.1 初窥门径

> 修仙仙府 v2.1 版本需求文档
> 版本: v2.1
> 日期: 2026-05-30

---

## 概述

v2.1「初窥门径」目标：基础交互体验提升，让用户感受到"灵气"存在。

---

## 功能需求

### 1. 鼠标轨迹 MouseTrail.vue
- **文件**: `frontend/src/components/effects/MouseTrail.vue`
- **描述**: Canvas渲染淡金色粒子，1.2s生命周期，最大30个粒子
- **验收标准**: 鼠标移动时有淡金色粒子尾迹

### 2. 修为印章 CultivationProgress.vue
- **文件**: `frontend/src/components/effects/CultivationProgress.vue`
- **描述**: 右下角印章显示今日修为，localStorage持久化
- **规则**:
  - 停留10分钟 +1修为
  - 点击5次 +1修为
  - 滚动到底 +1修为
- **验收标准**: 右下角显示"今日修为+X"印章

### 3. 岛屿hover特效
- **文件**: `frontend/src/views/hover-effects.css`
- **描述**: 5种岛屿各自特效（音符/书卷/光圈/墨滴/齿轮）
- **验收标准**: 悬停岛屿时有专属动效

### 4. 顶栏优化
- **文件**: `frontend/src/views/hover-effects.css` + `HomeView.vue`
- **描述**: 音律玉佩/身份令牌/法诀玉简样式
- **验收标准**: 顶栏按钮有玉石质感

---

## 技术实现

### 集成到 HomeView.vue
1. 导入 MouseTrail.vue 和 CultivationProgress.vue
2. 在模板中添加 `<MouseTrail />` 和 `<CultivationProgress />`
3. 通过 `@import './hover-effects.css'` 引入 hover 特效 CSS

### 依赖
- 无新依赖，已使用 Vue 3 Composition API

---

## 测试计划

- [x] `npm run build` 通过
- [x] `node test_site.cjs` E2E 测试 6/7 通过
- [ ] `npm run preview` 本地预览确认
- [ ] 用户验收确认

---

**文档状态**: 开发完成，待用户验收
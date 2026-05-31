# PRD v2.4 天人合一

> 修仙仙府 v2.4 版本需求文档
> 版本: v2.4
> 日期: 2026-05-31

---

## 概述

v2.4「天人合一」目标：完整修仙体验，惊喜和叙事。

---

## 功能需求

### 1. 随机事件 useRandomEvents.js + RandomEventsLayer.vue

**文件**: `frontend/src/composables/useRandomEvents.js` + `frontend/src/components/effects/RandomEventsLayer.vue`

**功能**:
- 流星雨（夜间概率触发）
- 灵气爆发（集齐5个岛屿后概率触发）
- 仙鹤群飞（酉时概率触发）
- 30分钟冷却时间

**验收标准**: 随机出现惊喜事件，每次只触发一种

---

### 2. 修炼编年史 CultivationChronicle.vue

**文件**: `frontend/src/components/common/CultivationChronicle.vue`

**触发条件**:
- 导航下拉菜单选择"编年史"
- 或用户头像下拉

**展示内容**:
- 项目发展时间线
- 关键版本里程碑
- 用户修仙历程回顾

**验收标准**: 下拉菜单点击"编年史"显示弹窗

---

### 3. 灵根测试 SpiritRootQuiz.vue

**文件**: `frontend/src/components/common/SpiritRootQuiz.vue`

**功能**:
- 5道问答测灵根类型（金/木/水/火/土）
- 根据答案计算灵根属性
- 显示灵根类型和特点

**验收标准**: 长按触发测试，显示测试结果

---

### 4. 转场动画 EntranceOverlay.vue

**文件**: `frontend/src/components/transition/EntranceOverlay.vue`

**功能**:
- 砚台墨染过渡效果
- 岛屿间跳转时播放
- 墨水扩散动画

**验收标准**: 岛屿跳转有墨染过渡效果

---

## 技术实现

### 随机事件
- 使用 `useCelestialSystem` 判断时间
- 30分钟冷却使用 `localStorage` 存储
- `RandomEventsLayer.vue` 渲染事件效果

### 编年史/灵根测试
- 组件 `Teleport` 到 `body`
- 点击/长按事件在 `HomeView.vue` 处理

### 转场动画
- `InkTransition.vue` 已有墨水效果
- 需要集成到 `router/index.js` 的路由切换

---

## 依赖关系

- useRandomEvents.js → RandomEventsLayer.vue
- HomeView.vue → CultivationChronicle.vue（logo点击/长按）
- HomeView.vue → SpiritRootQuiz.vue（长按触发）
- router → EntranceOverlay.vue（路由切换）

---

## 测试计划

- [ ] 随机事件30分钟冷却验证
- [ ] 导航下拉菜单点击"编年史"显示
- [ ] 长按触发灵根测试
- [ ] 岛屿跳转有墨染过渡
- [ ] `node browser_verify.js --local --all` 通过

---

## 时间估算

- 随机事件集成: 2 小时
- 编年史集成: 1 小时
- 灵根测试集成: 1 小时
- 转场动画集成: 2 小时
- 自测+调试: 2 小时
- 总计: 8 小时

---

**文档状态**: 评审完成，待开发
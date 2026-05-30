# PRD v2.2 渐入佳境

> 修仙仙府 v2.2 版本需求文档
> 版本: v2.2
> 日期: 2026-05-30

---

## 概述

v2.2「渐入佳境」目标：氛围装饰，让仙府更"活"。

---

## 功能需求

### 1. 装饰层 DecorationsLayer.vue
- **文件**: `frontend/src/components/effects/DecorationsLayer.vue`
- **描述**: Canvas渲染飘浮装饰物（灯笼/丹炉/仙鹤/符文碎片），概率出现
- **动画**:
  - 灯笼：淡金色光晕，左右摇摆
  - 丹炉：底部火焰粒子，紫霄色
  - 仙鹤：翅膀扇动，平滑飘过
  - 符文碎片：金色小粒子，旋转飘落
- **规则**: 每种装饰物有出现概率，不同时刻随机出现
- **验收标准**: 背景有飘浮装饰物（概率出现）

### 2. 每日运势 HomeView.vue 集成
- **文件**: `frontend/src/views/HomeView.vue`
- **描述**: 右下角印章显示今日宜忌+节气祝福
- **内容**:
  - 今日宜忌（根据节气计算）
  - 节气祝福语
  - 生肖幸运色
- **位置**: 现有修为印章附近或整合到印章区域
- **验收标准**: 角落显示当日运势和节气

### 3. 天象系统 useCelestialSystem.js
- **文件**: `frontend/src/composables/useCelestialSystem.js`
- **描述**: 12时辰主题+24节气，动态背景色调
- **功能**:
  - 获取当前时辰（子丑寅卯...）
  - 获取当前节气
  - 动态计算背景色调参数
  - 可被其他组件引用（装饰层颜色等）
- **验收标准**: 背景色调随时辰变化

---

## 技术实现

### 装饰层
- 使用 Canvas 渲染，与 MouseTrail.vue 类似
- 装饰物数量限制：最多同时5个
- 生命周期：飘出屏幕后移除
- 性能：使用 requestAnimationFrame，IntersectionObserver 不可见时暂停

### 每日运势
- localStorage 存储，当天只计算一次
- 节气计算：根据当前日期匹配24节气
- 宜忌计算：根据节气匹配传统宜忌

### 天象系统
- Composable 模式，供 HomeView.vue 和其他组件使用
- 暴露：currentHour（0-23）、solarTerm、themeColor
- 每分钟更新一次时辰

---

## 依赖关系

- DecorationsLayer.vue 使用 useCelestialSystem.js 的 themeColor
- 每日运势整合到 CultivationProgress.vue 附近（或合并）

---

## 测试计划

- [ ] npm run build 通过
- [ ] npm run preview 本地预览确认
- [ ] 装饰物在背景随机出现
- [ ] 每日运势印章显示正确
- [ ] 背景色调变化正常（可通过 setInterval 加速测试）
- [ ] 移动端 375px 验证
- [ ] node test_site.cjs E2E 通过

---

## 时间估算

- 装饰层: 3-4 小时
- 每日运势: 1-2 小时
- 天象系统: 1-2 小时
- 自测+调试: 2 小时
- 总计: 7-9 小时

---

**文档状态**: 开发中
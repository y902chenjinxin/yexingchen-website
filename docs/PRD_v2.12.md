# PRD v2.12 - 玉简交互简化

## 1. 产品定位

**版本定位**：性能优化 · 简化交互
**版本目标**：移除造成卡顿的特效，保留玉石质感

---

## 2. 改动详情

### 2.1 移除粒子轨道动画
- 删除 `.card-particles` 相关样式
- 删除 `.particle` 元素
- 删除 `particle-orbit` / `particle-burst` keyframes

### 2.2 移除光晕呼吸动画
- 删除 `.card-glow` 样式
- 删除 `glow-breathe` keyframes
- 删除 hover时的glow效果

### 2.3 移除浮动魔法动画
- 删除 `card-float-magic` keyframes
- 删除 `card-glow-magic` keyframes
- 删除 hover时的sway动画 `card-hover-sway`

### 2.4 移除入场动画
- 删除 `jade-enter` keyframes
- 玉简直接显示，不做淡入动画

### 2.5 移除自动轮播
- 删除 `startAutoScroll()` / `stopAutoScroll()`
- 删除相关 `autoScrollTimer`
- 玉简静态显示，用户通过鼠标或手势切换

### 2.6 保留玉石纹理
- `.card-texture` 样式保留
- 保留冰裂纹理感 radial-gradient 效果

---

## 3. 验收标准

- [ ] 无粒子轨道动画
- [ ] 无光晕呼吸动画
- [ ] 无浮动/摇摆动画
- [ ] 玉简直接显示，无入场动画
- [ ] 无自动轮播
- [ ] 玉石纹理效果保留

---

## 4. 排期

| 阶段 | 内容 | 时长 |
|------|------|------|
| 开发 | 样式清理 | 1h |
| 自测 | 本地验证 | 30min |
| 部署 | 按流程发布 | 30min |

## 5. 完成状态

- [x] 移除粒子轨道动画
- [x] 移除光晕呼吸动画
- [x] 移除浮动/摇摆动画
- [x] 移除入场动画
- [x] 移除自动轮播
- [x] 保留玉石纹理

**部署时间**: 2026-05-31
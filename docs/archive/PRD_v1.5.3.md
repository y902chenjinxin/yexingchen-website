# 个人网站 PRD v1.5.3

## 1. 项目概述

**项目名称**：叶兴辰的个人网站
**域名**：yexingchen.cn
**当前版本**：v1.5.3
**发布日期**：2026-05-28

**目标**：为岛屿添加灵气结界效果，提升仙侠氛围感。

**需求来源**：
- 产品经理：岛屿底部缺少仙气缭绕的层次感，阵法模式激活时应该有灵气连线
- 前端技能：SVG缺少氛围感，岛屿之间应有灵气连接的视觉效果

---

## 2. 需求清单

| # | 模块 | 功能点 | 状态 |
|---|------|--------|------|
| 1 | HomeView | 阵法模式激活时岛屿间灵气连线 | 待开发 |
| 2 | HomeView | 岛屿底部脉动光环效果 | 待开发 |
| 3 | HomeView | 岛屿hover时光环亮度提升 | 待开发 |

---

## 3. 功能详情

### 3.1 阵法模式岛屿灵气连线

**问题**：阵法模式激活时，5个岛屿围成圈旋转，但岛屿之间没有灵气连线，阵法感不足。

**解决**：阵法模式激活时，在岛屿之间用 SVG 线条绘制五行阵图连线：

```css
/* HomeView.vue - 新增灵气连线容器 */
.magic-mode .islands-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 15% 60%, rgba(78, 205, 196, 0.1) 0%, transparent 50%),
    radial-gradient(ellipse at 85% 40%, rgba(201, 169, 110, 0.1) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 20%, rgba(155, 141, 201, 0.08) 0%, transparent 40%);
  pointer-events: none;
  animation: magic-aura 4s ease-in-out infinite;
}
```

**灵气连线 SVG 绘制**：在 `islands-container` 内添加一个覆盖层，用 SVG 绘制五角星阵法连线：

```html
<!-- 灵气连线层 -->
<svg v-if="magicMode" class="magic-links" viewBox="0 0 100 100" preserveAspectRatio="none">
  <line x1="20%" y1="80%" x2="80%" y2="40%" class="magic-line" />
  <line x1="80%" y1="40%" x2="50%" y2="10%" class="magic-line" />
  <line x1="50%" y1="10%" x2="20%" y2="80%" class="magic-line" />
  <line x1="20%" y1="80%" x2="80%" y2="40%" class="magic-line" />
  <line x1="80%" y1="40%" x2="50%" y2="10%" class="magic-line" />
</svg>
```

**CSS 动画**：
```css
.magic-links {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.5s ease;
}
.magic-mode .magic-links {
  opacity: 1;
}
.magic-line {
  stroke: rgba(78, 205, 196, 0.3);
  stroke-width: 1;
  stroke-dasharray: 5, 5;
  animation: flow-line 2s linear infinite;
}
@keyframes flow-line {
  to { stroke-dashoffset: -20; }
}
```

---

### 3.2 岛屿底部脉动光环

**问题**：岛屿底部缺少"仙气缭绕"的层次感。

**解决**：在 HomeView.vue 的岛屿样式中，为每个岛屿添加底部脉动光环：

```css
/* 各岛屿底部光环 */
.island::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 40px;
  background: radial-gradient(ellipse, rgba(78, 205, 196, 0.2) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(8px);
  animation: pulse-glow 3s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.4; transform: translateX(-50%) scale(0.9); }
  50% { opacity: 0.7; transform: translateX(-50%) scale(1.1); }
}

/* 各岛屿不同颜色的光环 */
.music-island::after { background: radial-gradient(ellipse, rgba(155, 141, 201, 0.25) 0%, transparent 70%); }
.novel-island::after { background: radial-gradient(ellipse, rgba(232, 213, 183, 0.2) 0%, transparent 70%); }
.video-island::after { background: radial-gradient(ellipse, rgba(167, 139, 201, 0.25) 0%, transparent 70%); }
.log-island::after { background: radial-gradient(ellipse, rgba(143, 188, 143, 0.2) 0%, transparent 70%); }
.tool-island::after { background: radial-gradient(ellipse, rgba(212, 165, 116, 0.25) 0%, transparent 70%); }
```

---

### 3.3 岛屿hover光环增强

**问题**：岛屿hover只有scale+glow，缺少"唤醒沉睡结界"的感觉。

**解决**：hover时光环亮度大幅提升，像是在唤醒：

```css
.island:hover::after {
  opacity: 0.9;
  transform: translateX(-50%) scale(1.3);
  animation: none;
  filter: blur(4px) brightness(1.5);
}
```

---

## 4. 技术记录

### 4.1 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | frontend/src/views/HomeView.vue - 灵气连线 + 底部光环 + hover增强 |

---

## 5. 测试验证

部署后验证：
1. 阵法模式激活时岛屿间有隐约的灵气连线
2. 各岛屿底部有淡淡的脉动光环
3. 岛屿hover时光环亮度明显提升
4. 非阵法模式下灵气连线隐藏

---

## 6. 遗留问题

- 岛屿SVG本身的精致化（炼器炉/水月镜等）可放入 v1.6.0
- 岛屿入场动画可放入 v1.6.0

---

## 7. 附录：效果图描述

**阵法模式激活时**：
- 岛屿间有淡青色灵气连线（虚线流动）
- 背景有淡淡的灵气光晕弥漫
- 5个岛屿底部各自脉动，颜色与岛屿主题色呼应

**普通模式**：
- 岛屿底部有微弱的光环脉动
- 无灵气连线
- 整体氛围安静神秘
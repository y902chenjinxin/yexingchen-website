---
name: feedback-self-testing-incomplete
description: 自测只做build通过，没实际验证功能和视觉
metadata:
  type: feedback
---

## 自测不完整导致上线问题

**问题描述**：
v2.1部署后用户发现两个问题：
1. 鼠标轨迹颜色太暗，在深墨背景下几乎看不见
2. 岛屿hover特效完全不显示（因为HTML元素没有加到模板里）

**根因**：
自测只做了 `npm run build`，启动 preview 只是确认服务器能返回HTML。没有实际检查：
- 鼠标轨迹颜色是否合适
- 岛屿hover特效HTML元素是否存在

**教训**：
- build通过不等于功能正确
- preview 启动后必须手动验证每个功能
- 视觉颜色必须在实际背景下检查，不能只检查代码
- 交互效果要实际触发验证

**如何避免**：
1. `npm run build && npm run preview` 后要实际操作验证
2. 检查鼠标移动时粒子轨迹颜色是否可见
3. 检查每个岛屿hover时特效是否真实触发
4. 移动端三档宽度都要验证
5. 不只是"页面能加载"，要验证"功能能用"
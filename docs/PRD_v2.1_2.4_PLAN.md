# PRD v2.x 分阶段规划

> 修仙仙府2.x版本规划
> 版本: v2.1 - v2.4
> 日期: 2026-05-30

---

## 版本总览

| 版本 | 名称 | 功能数 | 优先级 |
|------|------|--------|--------|
| v2.1 | 初窥门径 | 4 | P0 |
| v2.2 | 渐入佳境 | 3 | P1 |
| v2.3 | 融会贯通 | 3 | P2 |
| v2.4 | 天人合一 | 4 | P3 |

---

## v2.1 初窥门径

**目标**: 基础交互体验提升，让用户感受到"灵气"存在

| 功能 | 文件 | 描述 |
|------|------|------|
| 鼠标轨迹 | `MouseTrail.vue` | Canvas渲染淡金色粒子，1.2s生命周期 |
| 修为印章 | `CultivationProgress.vue` | 右下角印章显示今日修为，localStorage持久化 |
| 岛屿hover特效 | `hover-effects.css` | 5种岛屿各自特效（音符/书卷/光圈/墨滴/齿轮） |
| 顶栏优化 | `HomeView.vue` | 音律玉佩/身份令牌/法诀玉简样式 |

**验收标准**：
- [ ] 鼠标移动时有淡金色粒子尾迹
- [ ] 右下角显示"今日修为+X"印章
- [ ] 悬停岛屿时有专属动效
- [ ] 顶栏按钮有玉石质感

---

## v2.2 渐入佳境

**目标**: 氛围装饰，让仙府更"活"

| 功能 | 文件 | 描述 |
|------|------|------|
| 装饰层 | `DecorationsLayer.vue` | 灯笼/丹炉/仙鹤/符文碎片飘浮 |
| 每日运势 | `HomeView.vue` | 右下角印章显示今日宜忌+节气祝福 |
| 天象系统 | `useCelestialSystem.js` | 12时辰主题+24节气，动态背景色 |

**验收标准**：
- [ ] 背景有飘浮装饰物（概率出现）
- [ ] 角落显示当日运势和节气
- [ ] 背景色调随时辰变化

---

## v2.3 融会贯通

**目标**: 交互增强，支持键盘和手势

| 功能 | 文件 | 描述 |
|------|------|------|
| 键盘导航 | `useKeyboardNavigation.js` | Tab遍历岛屿，方向键移动，?显示帮助 |
| 手势控制 | `useGestureControl.js` | 移动端捏合/长按/上滑 |
| 音效集成 | `useIslandSound.js` + `HomeView.vue` | 岛屿hover时播放专属音效 |

**验收标准**：
- [ ] Tab键按顺序遍历岛屿，Enter进入
- [ ] 移动端可手势操作
- [ ] hover岛屿时有音效

---

## v2.4 天人合一

**目标**: 完整修仙体验，惊喜和叙事

| 功能 | 文件 | 描述 |
|------|------|------|
| 随机事件 | `useRandomEvents.js` + `RandomEventsLayer.vue` | 流星雨/灵气爆发/仙鹤群飞等（30分钟冷却） |
| 修炼编年史 | `CultivationChronicle.vue` | 连点logo 7次或长按触发，展示项目发展史 |
| 灵根测试 | `SpiritRootQuiz.vue` | 5道问答测灵根类型 |
| 转场动画 | `EntranceOverlay.vue` | 砚台墨染过渡效果 |

**验收标准**：
- [ ] 随机出现惊喜事件（流星等）
- [ ] 连点logo 7次显示编年史
- [ ] 长按触发灵根测试
- [ ] 页面切换有墨染过渡

---

## 待清理文件（不纳入v2.x）

这些是v2.0开发过程中创建但暂不使用的文件：

| 文件路径 | 原因 |
|----------|------|
| `components/layers/*` | 五层背景组件，暂未集成 |
| `components/particles/*` | 粒子组件，暂未集成 |
| `components/transition/*` | 转场组件，暂未集成 |
| `composables/useBreathCycle.js` | 呼吸节奏，暂未集成 |
| `composables/useEntranceAnimation.js` | 入场动画，暂未集成 |
| `composables/useParticleSystem.js` | 粒子系统，暂未集成 |
| `views/islands/*` | 洞天内景页面，内容待填充 |

---

## 待清理文件（不纳入v2.x）

这些是v2.0开发过程中创建但暂不使用的文件，将在v2.x完成后统一清理：

### Components
| 文件路径 | 原因 |
|----------|------|
| `components/layers/*` (5个) | 五层背景组件，暂未集成HomeView |
| `components/particles/*` (3个) | 粒子组件，暂未集成 |
| `components/transition/*` (2个) | 转场组件，暂未集成 |

### Composables
| 文件路径 | 原因 |
|----------|------|
| `useBreathCycle.js` | 呼吸节奏，暂未集成 |
| `useEntranceAnimation.js` | 入场动画，暂未集成 |
| `useParticleSystem.js` | 粒子系统，暂未集成 |

### Views
| 文件路径 | 原因 |
|----------|------|
| `views/islands/*` (6个) | 洞天内景页面，内容待填充 |

### 临时文件
| 文件路径 | 原因 |
|----------|------|
| `check_css.py` | 临时检查脚本 |
| `check_server.py` | 临时检查脚本 |
| `cookies.txt` | 临时cookie文件 |

### 文档
| 文件路径 | 原因 |
|----------|------|
| `docs/PRD_v2.0_SCHEME_REVIEW.md` | 被新文档替代 |
| `docs/TECH_DESIGN_v2.md` | 被新文档替代 |
| `memory/project-v200.md` | 项目记忆已过时 |

---

## 部署节奏

每个版本完成自测后部署生产，不再累积大版本。

- v2.1 → 部署 → 用户验收
- v2.2 → 部署 → 用户验收
- v2.3 → 部署 → 用户验收
- v2.4 → 部署 → 用户验收

---

**文档状态**: 待用户确认
**下次更新**: 用户确认后开始v2.1开发
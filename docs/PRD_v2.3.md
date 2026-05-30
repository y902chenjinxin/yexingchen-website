# PRD v2.3 融会贯通

> 修仙仙府 v2.3 版本需求文档
> 版本: v2.3
> 日期: 2026-05-31

---

## 概述

v2.3「融会贯通」目标：交互增强，支持键盘和手势，让仙府更易用。

---

## 功能需求

### 1. 键盘导航 useKeyboardNavigation.js

**文件**: `frontend/src/composables/useKeyboardNavigation.js`

**功能**:
- `Tab` 键按顺序遍历5个岛屿
- `方向键` 在岛屿间快速移动
- `Enter` 进入选中岛屿
- `Escape` 返回首页
- `?` 显示键盘帮助浮层

**岛屿顺序**: 音乐岛 → 小说岛 → 视频岛 → 日志岛 → 工具岛

**视觉反馈**:
- 当前选中岛屿有高亮边框（翡翠绿 glow）
- 数字快捷键提示（1-5）

**验收标准**: Tab遍历岛屿，Enter进入，Escape返回

---

### 2. 手势控制 useGestureControl.js

**文件**: `frontend/src/composables/useGestureControl.js`

**功能**:
- `捏合` 岛屿缩放
- `长按` 岛屿显示详情卡片
- `上滑` 快速返回首页
- `双击` 岛屿进入

**移动端适配**:
- 触摸目标 ≥ 44×44px
- 手势识别在移动端启用，桌面端禁用（通过 `matchMedia('(hover: hover)')` 检测）

**验收标准**: 移动端可手势操作

---

### 3. 音效集成 useIslandSound.js

**文件**: `frontend/src/composables/useIslandSound.js`

**功能**:
- 岛屿 hover 时播放专属音效（使用 Web Audio API）
- 音量控制（静音选项）
- 音效预加载，避免首次播放延迟

**音效类型**:
| 岛屿 | 音效描述 |
|------|----------|
| 音乐岛 | 轻柔琴音 |
| 小说岛 | 翻书声 |
| 视频岛 | 播放音效 |
| 日志岛 | 墨滴声 |
| 工具岛 | 机械声 |

**技术实现**:
- 音效文件存放: `public/sounds/`
- 使用 Web Audio API 播放，支持多音轨
- 缓存已加载的 AudioBuffer

**验收标准**: hover岛屿时有音效

---

## 技术实现

### 键盘导航
- Composable 模式，监听 `keydown` 事件
- 岛屿 DOM 结构需有 `data-island-index` 属性
- 使用 `focus()` 方法控制焦点

### 手势控制
- 使用 `@touchstart` / `@touchend` / `@touchmove` 事件
- 计算 pinch 距离判断捏合
- 长按使用 `setTimeout` 500ms 检测

### 音效
- 音效文件格式: MP3 或 WAV
- Web Audio API 代码参考:
```javascript
const audioContext = new AudioContext();
const source = audioContext.createBufferSource();
source.buffer = audioBuffer;
source.connect(audioContext.destination);
source.start();
```

---

## 依赖关系

- useKeyboardNavigation.js → HomeView.vue
- useGestureControl.js → HomeView.vue
- useIslandSound.js → HomeView.vue + HomeView.vue hover事件

---

## 测试计划

- [ ] `npm run build` 通过
- [ ] 键盘导航：Tab/Enter/Escape/? 测试
- [ ] 手势控制：移动端测试
- [ ] 音效：各岛屿hover音效播放
- [ ] `node browser_verify.js --local --all` 通过

---

## 时间估算

- 键盘导航: 3-4 小时
- 手势控制: 2-3 小时
- 音效集成: 2-3 小时
- 自测+调试: 2 小时
- 总计: 9-12 小时

---

**文档状态**: 开发中
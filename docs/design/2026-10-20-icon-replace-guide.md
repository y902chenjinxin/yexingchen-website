# emoji → 线性图标 替换规范（2026-10-20）

## 目标一句话

把 `frontend/src` 里**当图标 / 装饰用**的 emoji 换成 `AppIcon` 组件渲染的线性图标。
**数据零改动** —— JS 常量与后端返回值里的 emoji 字面量一律不动，只改渲染处。

## 组件用法

```js
import AppIcon from '@/components/common/AppIcon.vue'
```

```vue
<!-- emoji 是字面量 -->
<AppIcon icon="🍜" />

<!-- emoji 来自变量 / 数据字段 -->
<AppIcon :icon="row.icon" />

<!-- 行内小图标（默认 18px，12~14px 的文字行里可传 14） -->
<AppIcon :icon="item.icon" :size="16" class="row-ic" />
```

要点：

- `size` 不传默认 18；**不要**为了对齐去改容器的字体大小。
- **不要**给 `AppIcon` 传颜色相关的 style / class（图标是「无色」的，`stroke: currentColor` 继承容器文字色；选中态的鎏金 / 雨青由容器文字色决定）。
- 图标自带 `vertical-align: -0.125em`，可直接放进文字行内，不需要额外包裹。
- 允许传 `class` 用于外边距 / flex 布局，但不要传 `color` / `fill` / `stroke`。

## 什么要换

1. 按钮、卡片、标签、chip、下拉、空状态、头像、徽标里的 emoji。
2. **文案开头的装饰 emoji**：`🍽 午餐` → `<AppIcon icon="🍽" /> 午餐`（保留原来的空格与标点）。
3. `v-for` 数据里作为 `icon` 字段渲染的 emoji → 用 `<AppIcon :icon="那个变量" />` 包住变量本身。
4. 图标与文字成对出现的，拆成「图标元素 + 文字元素」，例如：

```vue
<!-- 前 -->
<h3>👨‍👩‍👧 家人</h3>
<!-- 后 -->
<h3><AppIcon icon="👨‍👩‍👧" /> 家人</h3>
```

## 什么不要换

1. **代码注释里的 emoji**（`<!-- -->`、`//`、`/* */`、`{# #}`）—— 留着。
2. **JS 常量 / 数据定义里的 emoji 字面量** —— 这是数据源，动了就破坏「渲染层替换」：
   - `ICON_PRESETS`、`AI_AVATARS`、`presets`、`CATEGORY_*`、`*_OPTIONS`、后端返回的 `icon` 字段值等
   - 判断标准：这个 emoji 是**被别处读出来渲染**的（数据），还是**直接写在模板里显示**的（渲染）。只改后者。
3. 用户可自由输入内容里的 emoji。
4. CSS 的 `content` 属性 / 样式里的 emoji。
5. **无法拆分进 DOM 的动态拼接字符串**（例如 `log('🎲 掷出 3 点')` 这种日志文案）——
   优先做**小重构**：把 emoji 从字符串里提出来变成一个 `icon` 字段，模板里 `{{ }}` 旁边插 `<AppIcon :icon="..." />`。
   如果那个字符串是直接拼好塞进一个不可拆的容器（如选中的 value、`el-select` 的 value），就**保留原样**，改完在报告里逐条列出位置，不要硬塞。

## el-select 等组件插槽

选中格里显示的 emoji 换不掉是常见坑：必须用 `#label` 插槽才生效（element-plus 2.7.2 支持）。列表项里的 `#default` 同理。

## 硬性约束

- 不改无关代码、不重构、不动样式、不新增文件。
- 新 import 与文件现有 import 分组风格保持一致（`@/` 别名开头）。
- **不要**运行 `npm run build`（会与其他并行任务抢 `dist/`，最后统一构建）。改完自己 `Read` 一遍确认。
- 改完自查标准：该文件里**不再有「当图标用」的 emoji 残留**（注释里的可以留），且每个 `<AppIcon>` 的 `icon` 值都能在 `frontend/src/utils/icons/` 三张表或 `utils/finance/ledgerIcons.js` 里命中（当场没命中的先确认它在扫描清单里，再决定要不要补图标）。

## 图标表在哪

- `frontend/src/utils/icons/appIcons.js` —— 天气 / 人物头像 / 通用 UI / 物件分类 / 字符型图标（`✕ ☰ ⌘ ⌫ ★ ♪ ⏻ ⚔` 等）
- `frontend/src/utils/icons/gameIcons.js` —— 棋牌棋子、大富翁道具与事件格、对局结果、状态圆点
- `frontend/src/utils/finance/ledgerIcons.js` —— 记账 38 枚（已上线，优先命中）
- 查表入口 `frontend/src/utils/icons/index.js` 的 `appIconBody(emoji)`

未命中的 emoji 会回落显示原字符（不会变空白），所以**不要**为了让某个 emoji 好看去改这些表 —— 需要补图标时先报告。

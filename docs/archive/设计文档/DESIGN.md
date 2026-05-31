# 叶兴辰个人网站 · 神农图 DESIGN.md

> 版本：v1.6.0 草稿 · 基于 v1.5.3 灵气结界迭代
> 状态：待用户确认后可实施

---

## 1. Visual Theme & Atmosphere

**设计哲学**：墨色云海 · 灵气结界 · 神农图腾

神农图主题，取自上古神农氏尝百草测绘地理的传说，以"云上洞天、岛屿浮空、灵气流转"为核心意象。
视觉语言从"墨韵·云雾·灵气白雾"三层构成，配合"金色铭文·玉石绿·朱砂红"点缀色，营造仙侠修真世界的沉浸感。

**氛围关键词**：
- 墨色基底（深蓝黑 `#0D1F27 → #1A1A2E`）
- 云雾缭绕（层次青白 `rgba(200,220,240,0.08)`）
- 灵气结界（青色光芒 `#4ECDC4` 脉动）
- 铭文质感（金色 `#C9A96E` 用于标题装饰）
- 朱砂点睛（`#DC6B6B` 用于危险操作/警示）

**一句话定调**：沉静的墨色天幕下，5座岛屿浮于云海，灵气结界在阵法激活时泛出淡青色光芒。

---

## 2. Color Palette & Roles

```css
:root {
  /* === 墨色基底（主背景）=== */
  --color-ink-deep:       #0D1F27;   /* 最深天幕 */
  --color-ink-base:       #1A1A2E;   /* 岛屿背景 */
  --color-ink-surface:    #141B2D;   /* 卡片/内容区 */
  --color-ink-elevated:   #1E2D42;   /* 悬浮层 */

  /* === 灵气色系（主强调）=== */
  --color-qi-primary:     #4ECDC4;   /* 灵气结界主色 */
  --color-qi-glow:        rgba(78, 205, 196, 0.15);  /* 光晕/背景 */
  --color-qi-line:        rgba(78, 205, 196, 0.3);  /* 连线/边框 */

  /* === 玉石绿（次要强调）=== */
  --color-jade:           #68A978;   /* 成功/登录/审批 */

  /* === 金色/铭文（标题装饰）=== */
  --color-gold:           #C9A96E;   /* 标题渐变/高光 */
  --color-gold-dim:       rgba(201, 169, 110, 0.6);

  /* === 朱砂/警示 === */
  --color-cinnabar:       #DC6B6B;   /* 危险/删除/错误 */
  --color-cinnabar-dim:   rgba(220, 107, 107, 0.2);

  /* === 云雾/白雾（层次感）=== */
  --color-mist:           rgba(200, 220, 240, 0.08);   /* 薄雾层 */
  --color-mist-thick:     rgba(200, 220, 240, 0.15);   /* 浓雾层 */

  /* === 岛屿主题色 === */
  --color-music:          #9B8DC9;   /* 音乐岛 · 紫罗兰 */
  --color-music-glow:     rgba(155, 141, 201, 0.25);
  --color-novel:          #E8D5B7;   /* 小说岛 · 羊皮纸金 */
  --color-novel-glow:     rgba(232, 213, 183, 0.2);
  --color-video:          #A78BC9;   /* 视频岛 · 薰衣紫 */
  --color-video-glow:     rgba(167, 139, 201, 0.25);
  --color-log:           #8FBC8F;   /* 日志岛 · 苔绿 */
  --color-log-glow:      rgba(143, 188, 143, 0.2);
  --color-tool:          #D4A574;   /* 工具岛 · 铜锈色 */
  --color-tool-glow:     rgba(212, 165, 116, 0.25);

  /* === 文字色 === */
  --color-text-primary:   #E8F4FC;   /* 主要文字 · 霜白 */
  --color-text-secondary: rgba(232, 244, 252, 0.65); /* 次要文字 */
  --color-text-muted:     rgba(232, 244, 252, 0.4);  /* 辅助文字 */

  /* === 功能色 === */
  --color-accent:         var(--color-qi-primary);
  --color-danger:         var(--color-cinnabar);
  --color-success:        var(--color-jade);
  --color-gold-accent:   var(--color-gold);
}
```

---

## 3. Typography Rules

**字体选型**：

| 用途 | 字体 | 说明 |
|------|------|------|
| 标题 Display | `ZCOOL XiaoWei`（站酷小薇体）| 仙侠感强烈，竖排铭文气质 |
| 衬线 Body | `Noto Serif SC` | 正文阅读，衬线增加古典感 |
| 无衬线 UI | `Noto Sans SC` | 按钮/输入框/表格 |
| 等宽代码 | `JetBrains Mono` | 代码/日志/数据 |

```css
@import url('https://fonts.googleapis.com/css2?family=ZCOOL+XiaoWei&family=Noto+Serif+SC:wght@400;600&family=Noto+Sans+SC:wght@400;500;600&family=JetBrains+Mono&display=swap');

:root {
  --font-display: 'ZCOOL XiaoWei', 'Noto Serif SC', serif;
  --font-serif:   'Noto Serif SC', 'Noto Sans SC', serif;
  --font-sans:     'Noto Sans SC', system-ui, sans-serif;
  --font-mono:     'JetBrains Mono', monospace;
}

/* 字号层级 */
--text-xs:    12px;
--text-sm:    14px;
--text-base:  16px;
--text-lg:    18px;
--text-xl:    20px;
--text-2xl:   24px;
--text-3xl:   30px;
--text-4xl:   36px;
--text-5xl:   48px;

/* 行高 */
--leading-tight:   1.3;   /* 标题 */
--leading-normal:  1.6;   /* 正文 */
--leading-relaxed: 1.8;   /* 长阅读 */

/* 字间距 */
--tracking-tight:  -0.02em;
--tracking-normal:   0.02em;
--tracking-wide:     0.08em;  /* 标签/按钮 */
```

**文字装饰规则**：
- H1/H2 主标题：`background: linear-gradient(135deg, #C9A96E 0%, #F0E6C8 50%, #C9A96E 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;` 产生金色金属光泽
- 岛屿名称：在字下 2px 加 `text-shadow: 0 2px 8px var(--island-glow-color)` 呼应岛屿主题光
- 正文：禁用投影，保持清晰可读

**禁止字体**：
- ❌ `SimSun`（宋体）：过时而廉价
- ❌ `Microsoft YaHei`（微软雅黑）：系统感太重
- ❌ 纯英文 sans 作为 display（无中文 fallback）

---

## 4. Component Stylings

### 4.1 岛屿卡片（Island Card）

**普通态**：
```css
.island-card {
  background: var(--color-ink-surface);
  border: 1px solid rgba(78, 205, 196, 0.15);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}
/* 底部脉动光环 */
.island-card::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 120%;
  height: 40px;
  background: radial-gradient(ellipse, var(--island-glow) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(8px);
  opacity: 0.5;
  animation: pulse-glow 3s ease-in-out infinite;
}
```

**Hover 态**：
```css
.island-card:hover {
  border-color: var(--color-qi-line);
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4),
              0 0 30px var(--island-glow);
}
.island-card:hover::after {
  opacity: 0.9;
  transform: translateX(-50%) scale(1.3);
  filter: blur(4px) brightness(1.5);
  animation: none;
}
```

### 4.2 岛屿 SVG 精致化方向

当前问题（来自 PRD v1.5.3 遗留）：
- Emoji `🎵📖🎬📝🔧` 作为岛屿图标不仙侠
- SVG 缺乏层次感（无云雾/光效/多层结构）
- 各岛屿差异化不足

**精致化目标**：用内联 SVG 替代 Emoji，每个岛屿 SVG 需包含：
1. **主体结构**（浮空岛平台，带裂痕/纹理）
2. **核心设施**（每个岛屿独特：炼器炉/藏书阁/水月镜/铭文碑/工坊）
3. **氛围层**（底部云雾环绕 + 顶部灵气光点）
4. **发光效果**（阵法激活时整体泛光）

```css
/* SVG 岛屿统一样式 */
.island-svg {
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3));
  transition: filter 0.4s ease;
}
.island-card:hover .island-svg {
  filter: drop-shadow(0 4px 20px var(--island-glow)) brightness(1.1);
}
.magic-mode .island-card .island-svg {
  animation: island-glow-pulse 4s ease-in-out infinite;
}
```

**各岛屿 SVG 差异化设计**：

| 岛屿 | 核心设施视觉 | 主题色 | 氛围元素 |
|------|-------------|--------|---------|
| 音乐岛 | 悬浮玉磬/音律波纹 | `--color-music` | 音符粒子飘散 |
| 小说岛 | 竹简卷轴/藏书阁 | `--color-novel` | 文字光芒流转 |
| 视频岛 | 水月镜/水面波纹 | `--color-video` | 镜中影像闪烁 |
| 日志岛 | 铭文石碑/青铜灯 | `--color-log` | 光芒沿纹路爬升 |
| 工具岛 | 炼器炉/火焰 | `--color-tool` | 火焰明暗交替 |

### 4.3 登录卡片

**当前问题**：`LoginView.vue` 白底 LoginView.css 与仙侠风格冲突

**修复方案**：
```css
.login-card {
  background: rgba(13, 31, 39, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(201, 169, 110, 0.3);
  border-radius: 16px;
  box-shadow: 0 0 60px rgba(78, 205, 196, 0.1),
              0 20px 60px rgba(0, 0, 0, 0.5),
              inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
/* 金色边框顶部高光 */
.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-gold), transparent);
  border-radius: 0 0 4px 4px;
}
```

### 4.4 首页标题（HomeView）

**当前问题**：`HomeView.vue` 中 "神农图" 等标题在深色背景上可读性差

**修复方案**：
```css
.hero-title {
  font-family: var(--font-display);
  font-size: var(--text-5xl);
  background: linear-gradient(135deg, #C9A96E 0%, #F0E6C8 40%, #C9A96E 70%, #E8D5B7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
  filter: drop-shadow(0 4px 20px rgba(201, 169, 110, 0.3));
  letter-spacing: 0.1em;
}

.hero-subtitle {
  font-family: var(--font-serif);
  color: var(--color-text-secondary);
  font-size: var(--text-lg);
  letter-spacing: 0.15em;
}
```

### 4.5 输入框 / 表单元素

```css
.el-input__wrapper {
  background: rgba(255, 255, 255, 0.95) !important;  /* 白底黑字可读性 */
  border: 1px solid rgba(78, 205, 196, 0.3);
  box-shadow: none !important;
  border-radius: 8px;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.el-input__wrapper:hover {
  border-color: rgba(78, 205, 196, 0.6);
}
.el-input__wrapper.is-focus {
  border-color: var(--color-qi-primary);
  box-shadow: 0 0 0 3px var(--color-qi-glow) !important;
}
.el-input__inner {
  color: #1a1a2e !important;  /* 黑字 */
  font-family: var(--font-sans);
}
.el-input__placeholder {
  color: #8B9DAF !important;  /* 淡蓝灰 placeholder */
}
```

### 4.6 按钮

```css
.el-button--primary {
  background: linear-gradient(135deg, var(--color-qi-primary) 0%, #3DB8B0 100%);
  border: none;
  border-radius: 8px;
  font-family: var(--font-sans);
  letter-spacing: 0.05em;
  transition: all 0.3s ease;
}
.el-button--primary:hover {
  background: linear-gradient(135deg, #5DE0D8 0%, var(--color-qi-primary) 100%);
  box-shadow: 0 4px 20px var(--color-qi-glow);
  transform: translateY(-2px);
}
.el-button--danger {
  background: var(--color-cinnabar);
  border: none;
}
.el-button--danger:hover {
  background: #E87B7B;
}
```

### 4.7 表格

```css
.el-table {
  background: transparent !important;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(26, 58, 74, 0.4);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}
.el-table th.el-table__cell {
  background: rgba(26, 58, 74, 0.6);
  color: var(--color-text-secondary);
  font-weight: 600;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--color-qi-line);
}
.el-table tr {
  background: rgba(26, 58, 74, 0.3);
  transition: background 0.2s;
}
.el-table tr:hover td.el-table__cell {
  background: rgba(26, 58, 74, 0.5);
}
```

---

## 5. Layout Principles

**网格系统**：

| 断点 | 宽度 | 列数 | Gutter |
|------|------|------|--------|
| Mobile ≤ 768px | 100% | 1 | 16px |
| Tablet 768-1024px | 720px | 4 | 24px |
| Desktop 1024-1440px | 1000px | 12 | 32px |
| Wide ≥ 1440px | 1200px | 12 | 32px |

**间距梯度**（基于 4px 基准）：
```
4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128px
```

**岛屿容器**：
- 岛屿间保持 48px 最小间距
- 阵法模式激活时连线的 SVG 层叠在容器之上

---

## 6. Depth & Elevation

**阴影体系**：

| 层级 | 用途 | 数值 |
|------|------|------|
| Elevation 1 | 岛屿卡片默认 | `0 4px 12px rgba(0,0,0,0.3)` |
| Elevation 2 | 岛屿 hover | `0 12px 40px rgba(0,0,0,0.4), 0 0 30px var(--island-glow)` |
| Elevation 3 | 登录卡片 | `0 20px 60px rgba(0,0,0,0.5), 0 0 60px rgba(78,205,196,0.1)` |
| Elevation 4 | Modal | `0 30px 80px rgba(0,0,0,0.6)` |

**backdrop-filter**：
- 登录卡片：`blur(20px)`
- 岛屿卡片：`blur(8px)`（hover 时）
- 全局禁用：`blur()` 值超过 20px

---

## 7. Animation & Interaction

**动效档位**：L2（流畅交互）

### 7.1 入场动画

```css
/* 岛屿入场：从下方浮入，opacity 渐显 */
.island-card {
  animation: island-enter 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}
@keyframes island-enter {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 错开延迟 */
.island-card:nth-child(1) { animation-delay: 0.1s; }
.island-card:nth-child(2) { animation-delay: 0.2s; }
.island-card:nth-child(3) { animation-delay: 0.3s; }
.island-card:nth-child(4) { animation-delay: 0.4s; }
.island-card:nth-child(5) { animation-delay: 0.5s; }
```

### 7.2 岛屿 hover 光效

```css
.island-card:hover {
  transform: translateY(-4px) scale(1.02);
}
@keyframes pulse-glow {
  0%, 100% { opacity: 0.4; transform: translateX(-50%) scale(0.9); }
  50% { opacity: 0.7; transform: translateX(-50%) scale(1.1); }
}
```

### 7.3 灵气连线（阵法模式）

```css
.magic-links line {
  stroke: var(--color-qi-line);
  stroke-width: 1;
  stroke-dasharray: 5, 5;
  animation: flow-line 2s linear infinite;
}
@keyframes flow-line {
  to { stroke-dashoffset: -20; }
}
.magic-mode .magic-links {
  opacity: 1;
}
.magic-links {
  opacity: 0;
  transition: opacity 0.5s ease;
}
```

### 7.4 prefers-reduced-motion 降级

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8. Do's and Don'ts

### Do's ✅
1. 所有颜色通过 CSS 变量引用
2. 岛屿 SVG 带底部云雾层 + 顶部灵气光点
3. 岛屿 hover 有明显光效提升（亮度 + 光晕扩大）
4. 阵法模式激活时有灵气连线动画
5. 登录卡片使用深色半透明磨砂玻璃质感
6. 标题使用金色渐变 + 投影
7. 岛屿主题色与各岛屿一一对应
8. 输入框白底黑字保持可读性
9. 动效使用 cubic-bezier 曲线，不用 linear
10. 所有交互元素有 hover + focus 态

### Don'ts ❌
1. **禁止** Emoji 作为岛屿图标（替换为内联 SVG）
2. **禁止** 纯色块占位图片
3. **禁止** `filter: blur()` 作用于运动元素
4. **禁止** 登录卡片白底（改为深色磨砂）
5. **禁止** 深色文字直接写在深色背景上（无渐变/投影）
6. **禁止** `backdrop-filter: blur()` 值超过 20px
7. **禁止** `animation` 使用 `linear` 时长曲线
8. **禁止** 同一岛屿内 3 种以上主色混杂
9. **禁止** 在非阵法模式下显示灵气连线
10. **禁止** 移动端使用 larger font-size（超出视口）

---

## 9. Responsive Behavior

**断点**：
- Mobile：`≤ 768px` — 单列堆叠，岛屿 100% 宽
- Tablet：`768px - 1024px` — 2列网格
- Desktop：`> 1024px` — 岛屿轨道布局

**触摸目标**：
- 所有按钮/可点击元素：`≥ 44×44px`
- 移动端岛屿间距减少到 24px

**降级策略**：
- `prefers-reduced-motion`: 所有动画时长 ≤ 0.01ms
- 移动端阵法模式连线降低 opacity 至 0.5
- 移动端禁止 `backdrop-filter: blur()`

---

## 10. 实施优先级（v1.6.0）

| 优先级 | 内容 | 文件 |
|--------|------|------|
| P0 | 登录卡片改深色磨砂 | `LoginView.vue` + `LoginView.css` |
| P0 | 首页标题金色渐变 | `HomeView.vue` |
| P0 | 岛屿 SVG 替换 Emoji | `HomeView.vue`（5个岛屿组件） |
| P1 | 岛屿底部云雾 SVG 层 | 各 Island SVG 资产 |
| P2 | 灵气连线阵法动画 | `HomeView.vue` |
| P2 | 岛屿 hover 光效增强 | `HomeView.vue` CSS |

---

*DESIGN.md v1.6.0 · 待用户确认后进入 Phase C 实施*
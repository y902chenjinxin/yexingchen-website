# DESIGN - 水墨国风 · 返璞归真

## 1. Visual Theme & Atmosphere

**美学定位**：传统水墨画意境 + 现代极简主义
**关键词**：素雅、飘逸、留白、禅意
**视觉隐喻**：《富春山居图》长卷 + 宋代极简美学

---

## 2. Color Palette & Roles

### 核心色板（传统国画颜料）

```css
/* 墨色系 - 主背景 */
--ink-black: #1a1a1a;        /* 焦墨 - 最深 */
--ink-dark: #2d2d2d;          /* 浓墨 */
--ink-medium: #3d3d3d;        /* 宿墨 */
--ink-light: #4a4a4a;         /* 淡墨 */

/* 黛青系 - 远山/烟雨 */
--dai-green: #3d4f4f;         /* 黛青 */
--dai-blue: #4a5f5f;          /* 石青 */
--mist-gray: #5a6f6f;          /* 烟灰蓝 */

/* 赭石系 - 点缀/印章 */
--ochre: #8b6b4a;             /* 赭石 */
--ochre-light: #a08060;        /* 淡赭 */
--vermilion: #b54a3a;          /* 朱砂（用于印章）*/

/* 藤黄系 - 点睛 */
--rattan-yellow: #c4a35a;     /* 藤黄 */
--gold-pale: #d4b878;          /* 密金（少用）*/

/* 宣纸系 - 文字/卡片底 */
--paper-white: #f5f2eb;        /* 宣纸白 */
--paper-cream: #e8e4dc;        /* 玉版纸 */
--paper-aged: #d8d4c8;         /* 复古纸 */

/* 雾气系 - 云雾/留白 */
--mist-light: rgba(200, 200, 200, 0.08);
--mist-medium: rgba(180, 180, 180, 0.12);
--mist-heavy: rgba(160, 160, 160, 0.15);

/* 文字色 */
--text-primary: #d8d4c8;      /* 淡墨书 */
--text-secondary: #9a9590;    /* 淡墨 */
--text-muted: #6a6560;        /* 枯墨 */

/* 透明色 */
--color-glass: rgba(45, 45, 45, 0.7);
--color-overlay: rgba(26, 26, 26, 0.85);
```

### CSS RGB 辅助值（用于 rgba）

```css
--ink-black-rgb: 26, 26, 26;
--dai-green-rgb: 61, 79, 79;
--ochre-rgb: 139, 107, 74;
--paper-white-rgb: 245, 242, 235;
```

---

## 3. Typography Rules

### 字体选择

```css
/* 中文：思源宋体（Noto Serif SC）*/
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');

/* 备用：霞鹜文楷 */
@font-face {
  font-family: 'LXGW WenKai';
  src: url('/fonts/LXGWWenKai-Regular.woff2') format('woff2');
}

/* 西文衬线 */
font-family: 'Noto Serif SC', 'Source Serif Pro', Georgia, serif;

/* 无衬线（仅用于数字/英文标签）*/
font-family: 'Inter', -apple-system, sans-serif;
```

### 字号层级

| 层级 | 用途 | 字号 | 字重 | 行高 |
|------|------|------|------|------|
| H1 | 首页大标题 | 48px | 700 | 1.2 |
| H2 | 岛屿名称 | 32px | 600 | 1.3 |
| H3 | 玉简标签 | 18px | 600 | 1.4 |
| Body | 正文 | 15px | 400 | 1.8 |
| Caption | 辅助文字 | 13px | 400 | 1.6 |
| Label | 标签/印章 | 12px | 600 | 1.4 |

### 文字间距
- 中文字符：`letter-spacing: 0.05em`（宋体宽松感）
- 标题：`letter-spacing: 0.1em`

---

## 4. Component Stylings

### 4.1 登录卡片

**设计**：宣纸卷轴风格，毛边效果

```css
.login-card {
  background: linear-gradient(
    135deg,
    rgba(245, 242, 235, 0.95) 0%,
    rgba(232, 228, 220, 0.9) 100%
  );
  border: none;
  box-shadow:
    0 2px 20px rgba(0, 0, 0, 0.3),
    inset 0 0 30px rgba(139, 107, 74, 0.05);
  /* 模拟宣纸纹理 */
  background-image:
    url("data:image/svg+xml,%3Csvg width='100' height='100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
}

/* 卡片边缘：模拟撕边效果 */
.login-card::before {
  content: '';
  position: absolute;
  inset: -1px;
  background: linear-gradient(
    135deg,
    transparent 0%,
    rgba(139, 107, 74, 0.1) 50%,
    transparent 100%
  );
  border-radius: inherit;
  pointer-events: none;
}
```

**输入框**：淡墨边框，聚焦时藤黄底线

```css
.login-input {
  background: rgba(245, 242, 235, 0.9);
  border: 1px solid rgba(139, 107, 74, 0.2);
  border-radius: 2px;
  transition: all 0.3s ease;
}

.login-input:focus {
  border-color: var(--rattan-yellow);
  box-shadow: 0 2px 8px rgba(196, 163, 90, 0.15);
}
```

### 4.2 首页玉简

**设计**：淡墨线稿 + 宣纸底色 + 枯笔边缘

```css
.jade-card {
  background: linear-gradient(
    180deg,
    rgba(245, 242, 235, 0.92) 0%,
    rgba(232, 228, 220, 0.88) 100%
  );
  border: none;
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.15),
    0 0 1px rgba(0, 0, 0, 0.1);
  /* 去除金色描边，改用淡墨线 */
}

/* 玉简上的文字标签 */
.jade-label {
  font-family: 'Noto Serif SC', serif;
  font-weight: 600;
  color: var(--ink-dark);
  letter-spacing: 0.15em;
  /* 四字标签，间距加大 */
}

/* 聚焦态：淡墨晕染效果 */
.jade-card.jade-focused {
  box-shadow:
    0 0 30px rgba(61, 79, 79, 0.3),
    0 0 60px rgba(61, 79, 79, 0.15);
}
```

### 4.3 云雾层

**设计**：极度淡雅，模仿留白

```css
.mist-layer {
  opacity: 0.4;  /* 更淡 */
}

.mist {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(200, 200, 200, 0.04) 30%,
    rgba(200, 200, 200, 0.06) 50%,
    rgba(200, 200, 200, 0.04) 70%,
    transparent 100%
  );
  filter: blur(40px);  /* 更模糊 */
}
```

### 4.4 背景星空

**设计**：淡墨星点，非高亮光效

```css
.star {
  background: radial-gradient(
    circle,
    rgba(200, 195, 185, 0.4) 0%,
    transparent 70%
  );
  box-shadow: none;  /* 去除光晕 */
  animation: star-twinkle 18s ease-in-out infinite;  /* 更慢 */
}
```

### 4.5 修为印章

**设计**：简化朱砂印章风格

```css
.cultivation-seal {
  border: 2px solid var(--vermilion);
  background: rgba(181, 74, 58, 0.08);
}

.seal-text {
  color: var(--vermilion);
  letter-spacing: 0.2em;
}
```

### 4.6 音频控制面板

**设计**：淡墨风格，简约克制

```css
.audio-dropdown-panel {
  background: var(--color-glass);
  border: 1px solid rgba(61, 79, 79, 0.2);
  backdrop-filter: blur(12px);
}

.audio-label {
  color: var(--paper-cream);
}

.audio-slider-fill {
  background: linear-gradient(
    90deg,
    rgba(61, 79, 79, 0.5),
    rgba(61, 79, 79, 0.8)
  );
}
```

---

## 5. Layout Principles

### 网格系统
- 基础单位：8px
- 最大内容宽度：1200px
- 卡片间距：24px
- 页面边距：48px（桌面）/ 16px（移动）

### 留白法则
- 大量留白，不拥挤
- 元素周围至少 24px 呼吸空间
- 避免边缘贴边

---

## 6. Depth & Elevation

### 阴影系统（简化）
```css
--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.1);
--shadow-md: 0 4px 20px rgba(0, 0, 0, 0.15);
--shadow-lg: 0 8px 40px rgba(0, 0, 0, 0.2);

/* 减少高光/金色光晕使用 */
```

---

## 7. Animation & Interaction

### 动效原则
- **慢**：所有过渡 400-800ms
- **柔**：ease-in-out，拒绝 linear
- **淡**：opacity 变化为主，非位置跳跃

### 动画周期
| 元素 | 周期 | 说明 |
|------|------|------|
| 呼吸动画 | 19s（4-7-8节律）| 最慢 |
| 云雾漂移 | 120s+ | 几乎静止感 |
| 星空闪烁 | 18s | 极慢呼吸 |
| 背景渐变 | 120s | 12时辰切换 |

### prefers-reduced-motion 降级
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8. Do's and Don'ts

### Do's
- ✅ 使用墨色/黛青/赭石/藤黄配色
- ✅ 大量留白，保持透气
- ✅ 慢速柔和动画
- ✅ 思源宋体为主要中文字体
- ✅ 宣纸质感背景
- ✅ 简化，减少装饰元素

### Don'ts
- ❌ 高饱和金色光效（游戏风）
- ❌ 卡通化图标/图案
- ❌ 快速闪烁/弹跳动画
- ❌ 浓重彩色光晕
- ❌ 过多装饰线条
- ❌ 锐利边缘/硬阴影
- ❌ 纯黑背景（压迫感太强）

---

## 9. Responsive Behavior

### 断点
- 桌面：≥1024px
- 平板：768px-1023px
- 移动：<768px

### 移动端
- 简化至 3 层背景
- 隐藏次要装饰
- 触摸目标 ≥44px
- 保持字体可读性

---

## 10. 参考作品

- 《富春山居图》- 元·黄公望
- 《千里江山图》- 宋·王希孟
- 无印良品（MUJI）- 极简留白
- 故宫博物院数字馆 - 水墨与科技结合

---

## 11. v2.11 优化清单

### 登录页
- [ ] 去除卡通门特效，改为水墨晕染过渡
- [ ] 背景：淡墨山水长卷风格
- [ ] 卡片：宣纸质感 + 毛边效果

### 首页
- [ ] **去除左上角"叶兴辰的个人网站"字样**
- [ ] 玉简：去除金色描边，改淡墨线稿
- [ ] 云雾：更淡更透气，模仿留白
- [ ] 岛屿：淡墨线稿为主，非卡通图

### 整体
- [ ] 配色从"仙居山林"改为"水墨国风"
- [ ] 减少金色使用，改用藤黄/赭石点缀
- [ ] 所有动画降速至800ms+
- [ ] 减少高饱和光晕，增加淡墨晕染

---

## 附录：配色对照表

| 当前（玄墨流金）| 改为（水墨国风）|
|------|------|
| `#c9a962` 金色 | `#c4a35a` 藤黄（少用）|
| `#4a90a4` 翡翠绿 | `#3d4f4f` 黛青 |
| `#1a1a2e` 深蓝黑 | `#1a1a1a` 焦墨 |
| 鎏金描边 | 淡墨线稿 |
| 高亮光晕 | 淡墨晕染 |
# 玄墨流金 - 设计规范 v1.7

> **日期**: 2026-05-29
> **版本**: v1.7
> **风格**: 仙侠 / 玄墨流金

---

## 一、设计理念

**核心理念**：以"墨"为底，以"金"为魂，沉稳典雅中透出神秘仙韵。

参考古代文人书房氛围：深色墨底纸上，铜炉焚香，金色书签点缀。整体色调追求"夜书房"般的沉静与高级感。

---

## 二、色彩系统

### 2.1 玄墨底色系

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-bg-dark` | `#0D0F14` | 深墨色主背景 |
| `--color-bg` | `#12141A` | 页面背景 |
| `--color-bg-elevated` | `#1A1D24` | 提升层级卡片背景 |
| `--color-bg-glass` | `rgba(18,20,26,0.85)` | 玻璃态背景 |

### 2.2 古铜金色系

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-gold` | `#C9A86C` | 古铜金主色 |
| `--color-gold-light` | `rgba(201,168,108,0.4)` | 金色辉光 |
| `--color-gold-dark` | `#8B7355` | 暗金（次级元素） |

**渐变公式**：`linear-gradient(135deg, #8B7355 0%, #C9A86C 40%, #E8D4A8 50%, #C9A86C 60%, #8B7355 100%)`

### 2.3 翡翠点缀色

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-jade` | `#4A7C59` | 翡翠绿（灵气特效） |
| `--color-jade-light` | `#6B9B7A` | 亮翡翠 |
| `--color-jade-dark` | `#2D4D38` | 暗翡翠 |

### 2.4 紫霄色

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-purple` | `#8B7AAE` | 紫霄（神秘感） |
| `--color-purple-light` | `#A899C8` | 亮紫霄 |
| `--color-purple-dark` | `#6B5A8C` | 暗紫霄 |

### 2.5 岛屿特色色

| 岛屿 | 变量名 | 色值 | 描述 |
|------|--------|------|------|
| 音乐 | `--color-music` | `#9B8DC9` | 保留紫调 |
| 小说 | `--color-novel` | `#D4C4A8` | 暖纸色 |
| 视频 | `--color-video` | `#A87C9C` | 紫薇色 |
| 日志 | `--color-log` | `#7A9B7C` | 苔绿 |
| 工具 | `--color-tool` | `#C49A6C` | 琥珀色 |

### 2.6 文字色

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-text` | `#E8E4DC` | 月白/暖白（主文字） |
| `--color-text-secondary` | `#9A968E` | 灰茶色（次级文字） |
| `--color-text-muted` | `#6A665E` | 淡墨（禁用/提示） |

### 2.7 功能色

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-danger` | `#C96B6B` | 危险/错误 |
| `--color-success` | `#6A9B7A` | 成功 |
| `--color-warning` | `#C9A86C` | 警告 |

---

## 三、阴影系统

### 3.1 多层阴影（深度感）

```css
--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
--shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
--shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.5);
```

### 3.2 特效阴影

```css
/* 玻璃态阴影 */
--shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);

/* 金色辉光 */
--shadow-gold: 0 0 20px rgba(201, 169, 98, 0.25), 0 0 60px rgba(201, 169, 98, 0.1);

/* 翡翠光晕 */
--shadow-jade: 0 0 20px rgba(74, 124, 89, 0.3);
```

---

## 四、文字效果

### 4.1 流金文字渐变

```css
.text-gold-premium {
  background: linear-gradient(135deg, #8B7355 0%, #C9A86C 40%, #E8D4A8 50%, #C9A86C 60%, #8B7355 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 20px rgba(201, 169, 98, 0.3));
}
```

### 4.2 翡翠文字

```css
.text-jade {
  color: var(--color-jade);
  text-shadow: var(--shadow-jade);
}
```

---

## 五、组件效果

### 5.1 玻璃态

```css
.glass {
  background: var(--color-bg-glass);
  backdrop-filter: blur(20px) saturate(1.2);
  border: 1px solid rgba(201, 169, 98, 0.1);
}
```

### 5.2 深色卡片

```css
.card-deep {
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-lg);
  border: 1px solid rgba(201, 169, 98, 0.08);
}
```

---

## 六、纹理效果

### 6.1 Grain噪点纹理

```css
.grain-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.03;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
}
```

---

## 七、使用指南

### 7.1 禁止事项

- ❌ 禁止使用蓝色系主色调（已废弃 #4A6FA5）
- ❌ 禁止使用亮金色（已废弃 #C9A962）
- ❌ 禁止使用纯白文字色 #FFFFFF
- ❌ 禁止使用浅蓝背景 #E8F4FC

### 7.2 推荐用法

- ✅ 金色用于标题、强调、边框辉光
- ✅ 翡翠绿用于灵气/特效相关元素
- ✅ 紫霄色用于神秘/魔法相关元素
- ✅ 深墨背景用于卡片、容器

### 7.3 岛屿颜色映射

| 岛屿 | 主色用途 |
|------|----------|
| 音乐岛 | 紫霄色渐变发光边框 |
| 小说岛 | 暖纸色阴影 |
| 视频岛 | 紫薇色辉光 |
| 日志岛 | 翡翠光晕 |
| 工具岛 | 琥珀色金属光泽 |

---

## 八、版本记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-05-29 | v1.7 | 玄墨流金设计系统首次应用 |
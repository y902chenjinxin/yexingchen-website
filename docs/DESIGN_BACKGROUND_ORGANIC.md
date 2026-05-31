# DESIGN.md - 仙居山林 自然有机背景设计

> **日期**: 2026-05-31
> **版本**: v2.5.3
> **风格**: 仙居山林 / 自然有机
> **Anchor**: Organic（大地色系 + 人类手绘质感 + 温和动效）

---

## 一、设计理念

**核心理念**: "返璞归真，道法自然"

参考中国传统山水画的意境，结合现代有机设计语言。不是冷冰冰的数字感，而是有呼吸感、有生命力的自然景观。云雾要有体积感，山脉要有层次，灵气要有流动感。

---

## 二、色彩系统（自然大地色系）

### 2.1 背景色

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-bg-dark` | `#E8DCC7` | 沙色主背景 |
| `--color-bg` | `#F5EFE3` | 米白页面背景 |
| `--color-bg-elevated` | `#FDFBF7` | 提升层级暖白 |
| `--color-bg-glass` | `rgba(245, 239, 227, 0.92)` | 玻璃背景 |

### 2.2 大地色系

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-sage` | `#8B9D83` | 鼠尾草绿 |
| `--color-clay` | `#B08B6E` | 陶土棕 |
| `--color-terracotta` | `#C66B3D` | 赭石红 |
| `--color-ochre` | `#C08E3A` | 赓石黄 |
| `--color-moss` | `#606C38` | 苔藓绿 |
| `--color-sand` | `#E8DCC7` | 沙色 |
| `--color-oat` | `#D4B895` | 燕麦色 |

### 2.3 岛屿特色色

| 岛屿 | 变量名 | 色值 | 描述 |
|------|--------|------|------|
| 音乐 | `--color-music` | `#9d8ec4` | 薰衣草紫 |
| 小说 | `--color-novel` | `#c4a882` | 羊皮纸色 |
| 视频 | `--color-video` | `#a47c7c` | 砖红 |
| 日志 | `--color-log` | `#7a9b7c` | 苔绿 |
| 工具 | `--color-tool` | `#a89070` | 铜绿 |

### 2.4 灵气特效色

| 变量名 | 色值 | 用途 |
|--------|------|------|
| `--color-qi-primary` | `#8B9D83` | 鼠尾草绿（灵气主色） |
| `--color-qi-green` | `#606C38` | 苔藓绿 |
| `--color-qi-glow` | `rgba(139, 157, 131, 0.4)` | 灵气辉光 |
| `--island-glow-color` | `rgba(184, 134, 11, 0.25)` | 岛屿光晕 |

---

## 三、五层背景结构（带SVG图形）

### Layer 1: 天穹深处（z-index: 1）
- **元素**: 星空粒子群（非简单圆点）
- **实现**: Canvas 绘制的多层次星星，有大小不一、亮度各异
- **动画**: 随机闪烁（twinkle），每颗星有自己的呼吸节奏
- **透明度**: 0.4
- **移动速度**: 几乎静止（0.5x慢速漂移）

### Layer 2: 远山如黛（z-index: 2）
- **元素**: SVG山脉剪影（3层由近到远）
  - 远山：最淡（opacity 0.2），颜色 `rgba(139, 122, 106, 0.2)`
  - 中山：中等（opacity 0.35），颜色 `rgba(160, 140, 120, 0.35)`
  - 近山：较清晰（opacity 0.5），颜色 `rgba(139, 122, 106, 0.5)`
- **实现**: 复杂polygon路径，模拟真实山脉起伏
- **动画**: 极慢横移（150s周期），近山快远山慢产生视差
- **透明度**: 0.6

### Layer 3: 灵气涌动（z-index: 3）
- **元素**: 半透明渐变雾气层 + 粒子
- **实现**:
  - 底层：垂直渐变（底部深，顶部浅）
  - 中层：流动的灵气粒子（Canvas）
  - 顶层：径向渐变光斑
- **动画**: 呼吸效果（19s周期 4-7-8节律），灵气粒子缓慢上升
- **透明度**: 0.7

### Layer 4: 中景云海（z-index: 4）
- **元素**: 多层云朵（非简单椭圆）
  - 使用border-radius不规则化 + 多层阴影
  - 每朵云有体积感：高光、阴影、边缘羽化
- **实现**:
  ```css
  /* 云朵结构示例 */
  .cloud {
    background: radial-gradient(ellipse at 30% 30%,
      rgba(255,250,245,0.9) 0%,
      rgba(245,240,230,0.6) 40%,
      transparent 70%);
    box-shadow:
      inset -20px -20px 40px rgba(139,122,106,0.15),
      inset 10px 10px 20px rgba(255,255,255,0.5);
  }
  ```
- **动画**: 漂移（60s周期）+ 轻微上下浮动（20s周期）
- **透明度**: 0.9

### Layer 5: 近景薄雾（z-index: 5）
- **元素**: 横向雾气条带 + 散雾
- **实现**:
  - 主雾带：宽幅渐变条
  - 散雾：小团雾气随机分布
  - 边缘处理：blur + gradient羽化
- **动画**: 缓慢飘动（40s周期）
- **透明度**: 0.5

---

## 四、纹理与质感增强

### 4.1 纸张纹理叠加
```css
.grain-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
}
```

### 4.2 灵气粒子系统（Canvas）
- 每秒20-30个粒子缓慢上升
- 粒子大小：2-6px
- 颜色：鼠尾草绿到苔藓绿渐变
- 生命周期：4-8秒

---

## 五、十二时辰配色方案

| 时辰 | 时间 | 背景色 | 云雾色 | 光晕色 |
|------|------|--------|--------|--------|
| 子时 | 23-1 | `#2a2520` | `rgba(139,122,106,0.2)` | `rgba(139,122,106,0.4)` |
| 丑时 | 1-3 | `#352f28` | `rgba(176,140,110,0.18)` | `rgba(176,140,110,0.4)` |
| 寅时 | 3-5 | `#4a3f32` | `rgba(192,142,58,0.25)` | `rgba(192,142,58,0.5)` |
| 卯时 | 5-7 | `#F5EFE3` | `rgba(245,239,227,0.6)` | `rgba(201,169,98,0.6)` |
| 辰时 | 7-9 | `#FAF8F5` | `rgba(250,248,245,0.75)` | `rgba(208,174,120,0.6)` |
| 巳时 | 9-11 | `#F8F5EF` | `rgba(248,245,239,0.7)` | `rgba(212,183,132,0.65)` |
| 午时 | 11-13 | `#F0EBE3` | `rgba(240,235,227,0.65)` | `rgba(198,107,61,0.55)` |
| 未时 | 13-15 | `#E8E0D5` | `rgba(232,224,213,0.55)` | `rgba(176,140,112,0.5)` |
| 申时 | 15-17 | `#d4c8b8` | `rgba(212,200,184,0.45)` | `rgba(160,130,100,0.45)` |
| 酉时 | 17-19 | `#c8b8a5` | `rgba(200,184,165,0.4)` | `rgba(144,120,96,0.4)` |
| 戌时 | 19-21 | `#3a3028` | `rgba(120,105,95,0.25)` | `rgba(96,93,88,0.35)` |
| 亥时 | 21-23 | `#282218` | `rgba(80,72,60,0.2)` | `rgba(80,75,65,0.3)` |

---

## 六、动画时序参数

### 6.1 各层动画周期

| 层级 | 元素 | 周期 | 效果 |
|------|------|------|------|
| L1 | 星空 | 8s twinkle | 闪烁 |
| L2 | 远山 | 150s drift | 缓慢横移 |
| L3 | 灵气 | 19s breathe | 呼吸渐变 |
| L4 | 云海 | 60s drift + 20s float | 漂移+浮动 |
| L5 | 薄雾 | 40s drift | 飘动 |

### 6.2 呼吸节奏（4-7-8节律）

```css
--breath-in: 4s;      /* 吸气 */
--breath-hold: 7s;    /* 屏息 */
--breath-out: 8s;     /* 呼气 */
--breath-total: 19s;  /* 总周期 */
```

---

## 七、响应式策略

### 移动端（≤768px）
- 隐藏Layer 1（星星层）
- 简化Layer 5（只保留主要雾带）
- 减少云朵数量（3→1）
- 山脉高度减半

### 减少动效（prefers-reduced-motion）
- 所有动画设为 `animation: none`
- 各层透明度固定为基础值 × 0.5
- Canvas粒子系统暂停

---

## 八、CSS动画关键帧

```css
/* 星星闪烁 - 不规则节奏 */
@keyframes star-twinkle {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  10% { opacity: 0.8; transform: scale(1.1); }
  20% { opacity: 0.4; transform: scale(0.95); }
  40% { opacity: 0.9; transform: scale(1.05); }
  60% { opacity: 0.5; transform: scale(1); }
  80% { opacity: 0.7; transform: scale(0.98); }
}

/* 山脉漂移 - 极慢 */
@keyframes mountain-drift {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(30px); }
}

/* 灵气呼吸 - 4-7-8节律 */
@keyframes qi-breathe {
  0% { opacity: 0.3; transform: scaleY(1) translateY(0); }
  21% { opacity: 0.6; transform: scaleY(1.06) translateY(-2px); }
  58% { opacity: 0.75; transform: scaleY(1.1) translateY(-4px); }
  79% { opacity: 0.5; transform: scaleY(1.04) translateY(-2px); }
}

/* 云海漂移 */
@keyframes cloud-sea-drift {
  0% { transform: translateX(0) translateY(0); }
  25% { transform: translateX(40px) translateY(-10px); }
  50% { transform: translateX(80px) translateY(0); }
  75% { transform: translateX(40px) translateY(10px); }
  100% { transform: translateX(0) translateY(0); }
}

/* 薄雾飘动 */
@keyframes mist-drift {
  0% { transform: translateX(0) scaleX(1); opacity: 0.4; }
  50% { transform: translateX(60px) scaleX(1.05); opacity: 0.6; }
  100% { transform: translateX(0) scaleX(1); opacity: 0.4; }
}
```

---

## 九、验收标准

- [ ] 五层背景有明显的层次感和纵深感
- [ ] 云朵有体积感和质感，不是简单的椭圆
- [ ] 山脉有3层由近到远的层次
- [ ] 灵气呼吸效果自然流畅（4-7-8节律）
- [ ] 星空有闪烁效果，不是静态点
- [ ] 整体有自然有机的视觉感受，不是数字感
- [ ] 响应式适配正常
- [ ] prefers-reduced-motion 降级正常
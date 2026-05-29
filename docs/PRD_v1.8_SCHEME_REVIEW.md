# PRD v1.8 方案评审（确认版）

> **版本**: v1.8.0
> **日期**: 2026-05-29
> **评审角色**: PM / 前端 / 后端 / UI / 架构 / 测试 / 运维
> **状态**: ✅ 用户已确认，待实施

---

## 1. 需求概述（已确认）

**用户确认决策**：
1. ✅ 12色板切换时机：每2小时整点切换
2. ✅ 动态背景范围：背景+岛屿色调联动（不仅是背景，所有元素一起随时间变化）
3. ✅ 空白填充：云雾漂移+阵法符文（作为整体氛围的底层效果）

---

## 2. 设计方案：修仙洞府十二时辰

### 2.1 十二时辰配色系统

每个时段定义：**背景主色** + **岛屿光晕** + **云雾底色** + **氛围描述**

| 时段 | 时间 | 背景主色 | 岛屿光晕 | 云雾底色 | 氛围 |
|------|------|----------|----------|----------|------|
| **子时** | 00:00-02:00 | `#0A0C12` 深夜墨 | `rgba(201,169,98,0.35)` 月华金 | `rgba(201,169,98,0.08)` 银雾 | 月华如水 |
| **丑时** | 02:00-04:00 | `#0C0E16` 黎明前墨 | `rgba(74,124,89,0.3)` 翠青幽光 | `rgba(74,124,89,0.06)` 翠雾 | 万籁俱寂 |
| **寅时** | 04:00-06:00 | `#100E10` 破晓墨褐 | `rgba(232,180,100,0.4)` 破晓金 | `rgba(232,180,100,0.1)` 晨曦金雾 | 晨曦微露 |
| **卯时** | 06:00-08:00 | `#12100A` 晨曦墨棕 | `rgba(232,180,100,0.5)` 旭日金 | `rgba(232,180,100,0.15)` 旭日雾 | 金光破雾 |
| **辰时** | 08:00-10:00 | `#0D0F14` 上午玄墨 | `rgba(201,169,98,0.4)` 瑞气金 | `rgba(201,169,98,0.1)` 瑞气雾 | 瑞气千条 |
| **巳时** | 10:00-12:00 | `#12141A` 午前墨色 | `rgba(201,169,98,0.5)` 正阳金 | `rgba(232,200,140,0.12)` 正阳雾 | 如日中天 |
| **午时** | 12:00-14:00 | `#0E1018` 午后墨紫 | `rgba(139,122,174,0.4)` 紫霄淡辉 | `rgba(139,122,174,0.08)` 紫雾 | 日昃之慧 |
| **未时** | 14:00-16:00 | `#100C14` 下午灰紫 | `rgba(168,124,156,0.4)` 紫薇幽光 | `rgba(168,124,156,0.08)` 暖紫雾 | 暖色渐沉 |
| **申时** | 16:00-18:00 | `#0C1018` 傍晚藏蓝 | `rgba(74,90,139,0.35)` 暮光蓝 | `rgba(74,90,139,0.08)` 暮雾 | 暮色四合 |
| **酉时** | 18:00-20:00 | `#0A0E14` 黄昏墨蓝 | `rgba(201,140,108,0.4)` 黄昏橙 | `rgba(201,140,108,0.1)` 夕照雾 | 落日余晖 |
| **戌时** | 20:00-22:00 | `#0C0E18` 夜初蓝墨 | `rgba(139,122,174,0.35)` 夜初紫 | `rgba(139,122,174,0.08)` 夜雾 | 华灯初上 |
| **亥时** | 22:00-24:00 | `#080A10` 深夜夜墨 | `rgba(201,168,108,0.25)` 深夜金 | `rgba(201,168,108,0.06)` 深夜银雾 | 万籁俱寂 |

### 2.2 联动效果设计

**背景层**：
- 主背景色：`--color-bg-current`（运行时切换）
- 云雾层：3层叠加，不同速度漂移

**岛屿层**：
- 发光颜色随时间联动：`--color-island-glow-current`
- 每座岛屿可以有不同的主色调（音乐岛偏紫、小说岛偏金等），但光晕在每个时段有微妙的色相偏移

**装饰层**：
- 阵法符文：使用当前时段的点缀色，透明度4%
- 顶部装饰粒子：使用当前时段的瑞气色

### 2.3 云雾+阵法组合方案

```css
/* 云雾层 — 3层差异速度 */
.cloud-layer-1 {
  background: radial-gradient(ellipse 80% 50% at 20% 100%, var(--color-cloud-current) 0%, transparent 50%);
  animation: cloud-drift 60s linear infinite;
}
.cloud-layer-2 {
  background: radial-gradient(ellipse 60% 40% at 60% 100%, var(--color-cloud-secondary) 0%, transparent 50%);
  animation: cloud-drift 90s linear infinite reverse;
  opacity: 0.7;
}
.cloud-layer-3 {
  background: radial-gradient(ellipse 70% 45% at 80% 100%, var(--color-cloud-current) 0%, transparent 50%);
  animation: cloud-drift 120s linear infinite;
  opacity: 0.5;
}

/* 阵法符文层 */
.array-symbol {
  background: url("data:image/svg+xml,...") var(--color-accent-current);
  animation: array-rotate 240s linear infinite;
  opacity: 0.04;
}
```

---

## 3. CSS变量新增清单

```css
/* === 动态背景十二时辰 === */
--color-bg-theme-0: #0A0C12;   /* 子时 深夜墨 */
--color-bg-theme-1: #0C0E16;   /* 丑时 黎明前墨 */
--color-bg-theme-2: #100E10;   /* 寅时 破晓墨褐 */
--color-bg-theme-3: #12100A;   /* 卯时 晨曦墨棕 */
--color-bg-theme-4: #0D0F14;   /* 辰时 上午玄墨 */
--color-bg-theme-5: #12141A;   /* 巳时 午前墨色 */
--color-bg-theme-6: #0E1018;   /* 午时 午后墨紫 */
--color-bg-theme-7: #100C14;   /* 未时 下午灰紫 */
--color-bg-theme-8: #0C1018;   /* 申时 傍晚藏蓝 */
--color-bg-theme-9: #0A0E14;   /* 酉时 黄昏墨蓝 */
--color-bg-theme-10: #0C0E18;  /* 戌时 夜初蓝墨 */
--color-bg-theme-11: #080A10;  /* 亥时 深夜夜墨 */

/* === 岛屿光晕十二时辰 === */
--color-island-glow-0: rgba(201,169,98,0.35);   /* 子时 月华金 */
--color-island-glow-1: rgba(74,124,89,0.3);     /* 丑时 翠青幽光 */
--color-island-glow-2: rgba(232,180,100,0.4);   /* 寅时 破晓金 */
--color-island-glow-3: rgba(232,180,100,0.5);   /* 卯时 旭日金 */
--color-island-glow-4: rgba(201,169,98,0.4);    /* 辰时 瑞气金 */
--color-island-glow-5: rgba(201,169,98,0.5);    /* 巳时 正阳金 */
--color-island-glow-6: rgba(139,122,174,0.4);  /* 午时 紫霄淡辉 */
--color-island-glow-7: rgba(168,124,156,0.4);  /* 未时 紫薇幽光 */
--color-island-glow-8: rgba(74,90,139,0.35);   /* 申时 暮光蓝 */
--color-island-glow-9: rgba(201,140,108,0.4);  /* 酉时 黄昏橙 */
--color-island-glow-10: rgba(139,122,174,0.35);/* 戌时 夜初紫 */
--color-island-glow-11: rgba(201,168,108,0.25); /* 亥时 深夜金 */

/* === 云雾底色十二时辰 === */
--color-cloud-0: rgba(201,169,98,0.08);
--color-cloud-1: rgba(74,124,89,0.06);
--color-cloud-2: rgba(232,180,100,0.1);
--color-cloud-3: rgba(232,180,100,0.15);
--color-cloud-4: rgba(201,169,98,0.1);
--color-cloud-5: rgba(232,200,140,0.12);
--color-cloud-6: rgba(139,122,174,0.08);
--color-cloud-7: rgba(168,124,156,0.08);
--color-cloud-8: rgba(74,90,139,0.08);
--color-cloud-9: rgba(201,140,108,0.1);
--color-cloud-10: rgba(139,122,174,0.08);
--color-cloud-11: rgba(201,168,108,0.06);

/* === 运行时切换变量 === */
--color-bg-current: var(--color-bg-theme-0);
--color-island-glow-current: var(--color-island-glow-0);
--color-cloud-current: var(--color-cloud-0);
--color-accent-current: rgba(201,169,98,0.3);
```

---

## 4. 技术实现

### 4.1 JS控制逻辑

```javascript
// 更新时间主题（每2小时整点切换）
function updateAtmosphereTheme() {
  const hour = new Date().getHours()
  const themeIndex = hour % 12  // 0-11
  const root = document.documentElement
  root.style.setProperty('--color-bg-current', `var(--color-bg-theme-${themeIndex})`)
  root.style.setProperty('--color-island-glow-current', `var(--color-island-glow-${themeIndex})`)
  root.style.setProperty('--color-cloud-current', `var(--color-cloud-${themeIndex})`)
  // accent使用金色系但透明度随时段变化
  const accentOpacities = [0.3, 0.25, 0.4, 0.5, 0.35, 0.4, 0.35, 0.3, 0.3, 0.35, 0.3, 0.25]
  root.style.setProperty('--color-accent-current', `rgba(201,169,98,${accentOpacities[themeIndex]})`)
}

// 页面加载时立即执行
updateAtmosphereTheme()

// 每分钟检查是否需要切换（应对整点跨越）
setInterval(updateAtmosphereTheme, 60000)
```

### 4.2 岛屿动效修改

```css
/* HomeView.vue — 移除翻转，保留发光 */
.island-pos:hover .island {
  /* 删除 self-rotate animation */
  filter: drop-shadow(0 0 30px var(--color-island-glow-current));
  transform: translateY(-20px) scale(1.05);
  transition: all 0.4s ease;
}
```

---

## 5. 验收标准

| 功能点 | 验收条件 | 验证操作 |
|--------|----------|----------|
| 自动公转 | 页面加载即触发公转 | 打开首页观察 |
| 无翻转动画 | hover岛屿无3D翻转 | hover任一岛屿 |
| 发光效果 | hover时发光，颜色随时间变化 | 修改系统时间验证不同光晕色 |
| 动态背景 | 整点切换背景色 | 修改系统时间验证12种背景 |
| 岛屿联动 | 岛屿光晕与背景协调 | 同时观察背景+岛屿 |
| 云雾漂移 | 云雾层3层不同速度漂移 | 观察60秒 |
| 阵法符文 | 符文若隐若现，缓慢旋转 | 观察120秒 |
| 移动端 | 375px布局正常 | viewport切换 |

---

## 6. 文件改动清单

| 文件 | 改动内容 | 预估行数 |
|------|----------|----------|
| `frontend/src/assets/styles/variables.css` | 新增36个CSS变量（12背景+12光晕+12云雾） | +80行 |
| `frontend/src/views/HomeView.vue` | 移除翻转动画、添加JS时间控制、云雾阵法层 | ~50行 |
| `docs/PRD_v1.8_SCHEME_REVIEW.md` | 更新为确认版 | 无变更 |

---

## 7. ADR记录

| ID | 决策 | 原因 | 影响 |
|----|------|------|------|
| ADR-016 | 动态背景12时辰+岛屿联动方案 | 用户确认背景+岛屿联动 | variables.css新增36个变量，HomeView.vue新增JS控制逻辑 |
| ADR-017 | 云雾漂移+阵法符文作为空白填充方案 | 用户确认 | 需要前端实现CSS动画 |

---

## 8. 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.8.0 | 2026-05-29 | 评审完成，用户已确认设计 |
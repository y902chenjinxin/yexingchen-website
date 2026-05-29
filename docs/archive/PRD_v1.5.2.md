# 个人网站 PRD v1.5.2

## 1. 项目概述

**项目名称**：叶兴辰的个人网站
**域名**：yexingchen.cn
**当前版本**：v1.5.2
**发布日期**：2026-05-28

**目标**：修复岛屿页面UI一致性与仙侠主题割裂问题。

**需求来源**：
- 岛屿背景是 pastel 马卡龙色（#F5F0FF/#FDF8F0），与登录页深邃夜空风格割裂
- NovelIsland back-btn 硬编码 `#B8956A`，未使用 CSS 变量
- 各岛屿存在大量未使用的死代码（.content-card、.content-grid 等）

---

## 2. 需求清单

| # | 模块 | 功能点 | 状态 |
|---|------|--------|------|
| 1 | 岛屿背景 | 改为深色系，与仙侠主题统一 | 待开发 |
| 2 | 岛屿配色 | 统一使用 CSS 变量，修复硬编码 | 待开发 |
| 3 | 死代码清理 | 删除各岛屿未使用的样式 | 待开发 |
| 4 | 首页背景 | 优化为更有云海感的渐变 | 待开发 |

---

## 3. 功能详情

### 3.1 岛屿背景改为深色系

**问题**：所有5个岛屿页面都是 pastel 浅色背景，与登录页深邃夜空风格完全不统一。

| 岛屿 | 旧背景 | 色系 |
|------|--------|------|
| MusicIsland | `#F5F0FF` → `#EDE8F7` | 淡紫 pastel |
| NovelIsland | `#FDF8F0` → `#F7EDE0` | 暖米 pastel |
| ToolIsland | `#FDF5F0` → `#F5EDE5` | 暖粉 pastel |
| VideoIsland | `#F5F0FA` → `#EDE5F5` | 淡紫粉 pastel |
| LogIsland | `#F0F8F0` → `#E5F0E5` | 淡绿 pastel |

**解决**：统一改为深色系，与仙侠主题一致：

```css
/* 所有岛屿统一样式 */
.island-page {
  background: linear-gradient(180deg, #1A1A2E 0%, #141B2D 100%);
}
.island-header {
  background: rgba(26, 58, 74, 0.6);
  border-bottom: 1px solid rgba(78, 205, 196, 0.2);
}
.island-title { color: #E8F4FC; }
.back-btn { color: var(--color-accent); }
.back-btn:hover { color: #fff; }
.island-subtitle { color: rgba(255,255,255,0.7); }
```

**文件**：
- `frontend/src/views/MusicIsland.vue`
- `frontend/src/views/NovelIsland.vue`
- `frontend/src/views/ToolIsland.vue`
- `frontend/src/views/VideoIsland.vue`
- `frontend/src/views/LogIsland.vue`

---

### 3.2 统一使用 CSS 变量，修复硬编码

**问题**：`NovelIsland.vue:163` 的 back-btn 使用硬编码颜色 `#B8956A`，未使用 `var(--color-novel)`。

**解决**：
```css
/* NovelIsland.vue - 修复前 */
.back-btn { color: #B8956A; }

/* NovelIsland.vue - 修复后 */
.back-btn { color: var(--color-novel); }
```

**同时修复各岛屿文字颜色以适应深色背景**：

| 文件 | 属性 | 旧值 | 新值 |
|------|------|------|------|
| 所有岛屿 | .island-title | `var(--color-text)` | `#E8F4FC` |
| NovelIsland | .back-btn | `#B8956A` | `var(--color-novel)` |
| 所有岛屿 | .back-btn:hover | 保持 | `#fff` |

---

### 3.3 删除各岛屿未使用的死代码

**问题**：MusicIsland/NovelIsland/ToolIsland/VideoIsland 定义了 `.content-card` 等卡片样式，但实际使用的是 `el-table`，这些代码已废弃。

**解决**：删除以下未使用的样式类：

| 文件 | 删除的类 | 行数 |
|------|---------|------|
| MusicIsland.vue | `.content-grid`, `.content-card`, `.card-cover`, `.card-title`, `.card-meta`, `.card-size`, `.card-tags`, `.card-actions` | ~70行 |
| NovelIsland.vue | `.content-grid`, `.content-card`, `.card-cover`, `.card-title`, `.card-author`, `.card-meta`, `.card-size`, `.card-tags`, `.card-actions` | ~50行 |
| ToolIsland.vue | `.tool-grid`, `.tool-card`, `.tool-icon`, `.tool-info`, `.tool-title`, `.tool-url`, `.tool-desc`, `.tool-actions` | ~30行 |
| VideoIsland.vue | `.content-card`, `.card-cover`, `.cover-img`, `.cover-placeholder`, `.card-title`, `.card-meta`, `.card-size`, `.card-tags`, `.card-cos`, `.card-actions` | ~50行 |

**LogIsland.vue 无死代码**（timeline 样式正在使用）。

---

### 3.4 首页背景优化

**问题**：HomeView.vue 的背景是 `#87CEEB` 晴朗蓝天，与仙侠主题不符。

**解决**：改为更有云海感的深蓝渐变：

```css
/* HomeView.vue:326-331 - 修改前 */
background: linear-gradient(180deg,
  #87CEEB 0%,
  #B0E0E6 30%,
  #E0F0FF 60%,
  #F5F9FF 100%
);

/* HomeView.vue - 修改后 */
background: linear-gradient(180deg,
  #0D1F27 0%,
  #1A3A5C 40%,
  #2D5A7B 70%,
  #1A3A5C 100%
);
```

**文件**：`frontend/src/views/HomeView.vue`

---

## 4. 技术记录

### 4.1 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | frontend/src/views/MusicIsland.vue - 背景色 + 删除死代码 |
| 修改 | frontend/src/views/NovelIsland.vue - 背景色 + 修复硬编码 + 删除死代码 |
| 修改 | frontend/src/views/ToolIsland.vue - 背景色 + 删除死代码 |
| 修改 | frontend/src/views/VideoIsland.vue - 背景色 + 删除死代码 |
| 修改 | frontend/src/views/LogIsland.vue - 背景色 |
| 修改 | frontend/src/views/HomeView.vue - 背景渐变 |

---

## 5. 测试验证

部署后验证：
1. 登录页到首页到岛屿页面色调连贯（深夜 → 深蓝渐变）
2. 各岛屿页面背景统一为深色系
3. NovelIsland back-btn 颜色正确（使用 var(--color-novel)）
4. 各岛屿页面无死代码残留
5. 岛屿标题和返回按钮在深色背景下清晰可读

---

## 6. 遗留问题

- file-link 全局统一样色问题（可放入 v1.5.3）
- 岛屿动画（公转/阵法模式）在深色背景下是否需要调整发光效果

---

## 7. 附录：变更量估算

| 文件 | 删除行数 | 修改行数 |
|------|---------|---------|
| MusicIsland.vue | ~70 行死代码 | ~15 行深色背景 |
| NovelIsland.vue | ~50 行死代码 | ~10 行深色背景+硬编码修复 |
| ToolIsland.vue | ~30 行死代码 | ~15 行深色背景 |
| VideoIsland.vue | ~50 行死代码 | ~15 行深色背景 |
| LogIsland.vue | 0 | ~10 行深色背景 |
| HomeView.vue | 0 | ~10 行背景渐变 |

**总计**：约 200 行死代码删除，约 75 行视觉调整。
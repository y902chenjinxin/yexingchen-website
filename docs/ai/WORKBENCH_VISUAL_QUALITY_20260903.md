# 工作台/桌宠/岛屿视觉质感优化（20260903）

> 定位：解决 User 三个线上实测反馈 —— ① 玉简位置过低被遮挡；② 顶栏遮住桌宠配置弹窗；③ 全站（尤其岛屿内页 / 桌宠面板）深色偏廉价、缺乏质感。
> 原则：跨会话可执行的接续文档，实施完成后回填结论与验收。

---

## 一、问题与根因

### 1. 玉简位置太低被遮
- 现状：`WorkbenchView` 中 `.carousel-track { top: 62% }`，玉简在 hero 区内垂直偏下；`JadeCarousel` 容器固定高 300px、`overflow:hidden`，放大态玉简上缘 + 阴影易被裁切或贴近顶栏/标题，观感"被遮住"。
- 归因：玉简容器垂直定位偏高下、且被自己的 overflow 裁切，未给足上方呼吸空间。

### 2. 顶栏遮住桌宠配置弹窗
- 现状：全站顶栏 `GlobalTopBar.z-index: 9999`；桌宠 `WhaleCompanion .whale-stage.z-index: 1200`。桌宠配置面板（`.whale-panel`）向上从桌宠弹出，顶部会伸进顶栏高度范围被盖住。
- 归因：桌宠整体层级低于顶栏；面板向上弹出的设计在桌面底部时易被顶部元素遮挡。

### 3. 全站深色偏廉价 / 与已优化页面风格脱节
- 岛屿内页 `IslandInnerBase`：背景用旧 `--color-bg:#15212c`（深青平涂），各岛只在 `--island-accent` 微调色相 + 几层 radius 渐变 + blur 圆斑。**无纸张/金属/玻璃材质、无高光高边、字号粗细层级平淡** → 廉价的"深色平涂"。
- 桌宠面板 `.whale-panel` 仍用旧 `--xiu-*` 深青变量，与全站 `--lj-*` 浅色体系脱节。
- 深层观感差异：质感不是"深色"决定的，而是**材质层次 + 光影 + 色彩掌控**。GitHub 上"有质感"的深色工作台通常具备：细腻的彩色玻璃/渐变材质、1-2px 高光描边、柔和多层阴影、克制的高级色相（墨青/黛绿/赭石低饱和）。

---

## 二、方案

### 修复 1：玉简位置上移 + 增加呼吸空间
- `WorkbenchView .wb-hero` 增加 `padding-top`，玉简容器整体上移。
- `JadeCarousel`：`.carousel-track` 由 `top:62%` 调至约 `top:48%`；放大态玉简上缘不再贴顶裁切。
- `.wb-jade` 上方 margin 收小，标题与玉简间距收紧，视觉重心提升。

### 修复 2：桌宠配置面板层级与定位
- 桌宠 `z-index` 由 1200 **提到 10001**（在顶栏 9999 之上），保证向左上弹出的面板不被顶栏遮挡。
- 面板弹层 z-index 独立更高（如 `z-index: 10002`）。
- 恒指：桌宠整体常驻仍应在所有内容之上，仅低于必要的最上层浮层（移动阻挡/全屏遮罩等）。

### 修复 3：全局质感升级（重点）
**思路：引入"玄素琉璃"深色材质体系，统一岛屿内页 + 桌宠面板 + 各内页，与工作台 `--lj-*` 浅色区隔但保持同源气质。**

在全局 `variables.css` 追加一套 `--ls-*`（lingxi 冷萃）深色材质 token，供岛屿内页与桌宠面板使用：
- 背景：墨青夜色双层渐变（非纯色）→ `radial` 慢晕 + 细噪点纸张纹理。
- 卡片/面板：彩色玻璃 `backdrop-filter`（饱和+磨砂）+ 1px 内高光描边（上缘亮、下缘暗）+ 柔和多层阴影。
- 文字：高亮金/黛作点缀（去灰感），正文用近纯白提通透。
- 还原每个 `IslandInnerBase` 的 5 岛 accent 为**低饱和高级色**，并用在同一 `--ls-accent` 上。
- 更新 `MusicIslandInner` 等 5 个内页的卡片类，复用 `--ls-*`（替代散落 `rgba(155,141,201,…)`）。
- `WhaleCompanion .whale-panel` 改接 `--ls-*` 玻璃面板，与桌宠透明度统一。

> 完成后各岛内页/桌宠面板将呈现出"深而不闷、透亮有光"的材质质感，消除廉价平涂感；同时不与工作台浅色系统冲突。

### 定稿色板：`--ls-*` 玄素琉璃（调研提炼）
> 灵感：国风水墨高级色（沧浪/松石/远山黛/赭石金）+ Han Design 当代国风主题"克制配色、色系有情绪"。**低饱和为骨、高光高边为神、克制点缀**。

| Token | 值 | 用途 |
|-------|-----|------|
| `--ls-bg0` | `#10161c` | 最深沉底（焦墨夜色） |
| `--ls-bg1` | `#182229` | 主背景（墨青夜色，非纯色渐变） |
| `--ls-bg-glow` | `rgba(90,120,130,.10)` | 背景径向慢晕光斑 |
| `--ls-paper` | `#1e2830` | 卡片/面板底 |
| `--ls-paper-2` | `#232e37` | 面板hover/浮层 |
| `--ls-glass` | `rgba(32,42,51,.62)` | 玻璃层（配 backdrop-filter） |
| `--ls-line` | `rgba(200,214,220,.10)` | 弱描边 |
| `--ls-line-strong` | `rgba(200,214,220,.18)` | 强描边 |
| `--ls-highlight` | `rgba(255,255,255,.08)` | 上缘内高光 |
| `--ls-shadow` | `0 18px 46px rgba(0,0,0,.35), 0 4px 12px rgba(0,0,0,.2)` | 柔和多层阴影 |
| `--ls-dai` | `#5f9499` | 黛青主强调（低饱和提亮） |
| `--ls-dai-deep` | `#3f6a70` | 黛青加深 |
| `--ls-ochre` | `#c2a26b` | 鎏金/赭石点缀（克制） |
| `--ls-jade` | `#6aa98f` | 松石青（secondary 正点缀） |
| `--ls-text` | `#e8edf0` | 主文字（近纯白提通透） |
| `--ls-text-2` | `#aab6bc` | 次要文字 |
| `--ls-text-3` | `#7c8a91` | 弱文字/占位 |
| `--ls-accent` | 各岛继承 | 岛屿专属低饱和 accent |

**材质配方（玻璃感核心，与浅色 `--lj-*` 区隔但同源气质）：**
```css
.glass-elevated {
  background: linear-gradient(165deg, rgba(255,255,255,.06), rgba(255,255,255,0) 48%),
              var(--ls-paper);
  border: 1px solid var(--ls-line);
  border-radius: 16px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}
```
> 上缘 1px 「受光」内高光 + 多层柔和背光阴影 = 质感核心；克制使用 `--ls-ochre`/`--ls-jade` 作点缀，避免堆砌。

---

## 三、验收（浏览器实测，截图归档 _screens）
1. 工作台玉简整组上移，放大态不被裁切、顶部呼吸充足 → `fix1-carousel-top.png`
2. 点桌宠弹配置面板，顶部完整显示在顶栏之上，无遮挡 → `fix2-pet-panel.png`
3. 打开 音乐/小说 等岛屿内页，背景与卡片呈玻璃/纸质高质深度感，文字透亮度提升 → `fix3-island-music.png` / `fix3-island-novel.png`
4. 桌宠面板样式与岛屿内页同源材质 → `fix3-pet-panel.png`

## 四、涉及文件
- `frontend/src/components/JadeCarousel.vue`（玉简垂直定位）
- `frontend/src/views/WorkbenchView.vue`（hero 呼吸空间）
- `frontend/src/components/effects/WhaleCompanion.vue`（z-index + 面板材质）
- `frontend/src/assets/styles/variables.css`（新增 `--ls-*` 材质 token）
- `frontend/src/views/islands/IslandInnerBase.vue`（背景/header 材质）
- `frontend/src/views/islands/MusicIslandInner.vue` 等 5 个内页（卡片刷新用 token）
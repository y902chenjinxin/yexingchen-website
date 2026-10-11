麻将游戏 UI 设计规范（AI 智能体执行版）
一、设计目标
将现有扁平化麻将界面重构为写实风格、深色系、带 3D 透视感的高端麻将桌界面。禁止纯扁平色块，所有元素必须有材质、光影、阴影。

二、全局设计令牌（Design Tokens）
颜色
text
--color-table-bg: radial-gradient(circle at 50% 40%, #1A5C4A 0%, #0B3B2E 70%, #06241C 100%);
--color-table-edge: #D4AF37;
--color-tile-face: linear-gradient(180deg, #FFFFFF 0%, #F5F0E6 60%, #E8E0D0 100%);
--color-tile-back: linear-gradient(180deg, #1A5C4A 0%, #0B3B2E 100%);
--color-tile-shadow: rgba(0,0,0,0.35);
--color-gold: #D4AF37;
--color-gold-light: #F0D98C;
--color-cyan-glow: #00E5FF;
--color-text-primary: #F5F0E6;
--color-text-secondary: #A8B5A0;
--color-btn-bg: rgba(11, 59, 46, 0.85);
--color-btn-border: #D4AF37;
--color-danger: #E53935;
--color-success: #43A047;
阴影
text
--shadow-tile: 0 4px 0 #C0B8A8, 0 6px 8px rgba(0,0,0,0.3);
--shadow-tile-hover: 0 8px 0 #C0B8A8, 0 10px 14px rgba(0,0,0,0.4);
--shadow-panel: 0 8px 24px rgba(0,0,0,0.5);
--shadow-glow-gold: 0 0 12px rgba(212, 175, 55, 0.6);
--shadow-glow-cyan: 0 0 16px rgba(0, 229, 255, 0.8);
--shadow-inset-vignette: inset 0 0 120px rgba(0,0,0,0.6);
圆角
text
--radius-tile: 6px;
--radius-btn: 24px;
--radius-avatar: 50%;
--radius-panel: 12px;
字体
text
--font-tile: "Noto Serif SC", "Songti SC", serif; /* 牌面数字 */
--font-ui: "PingFang SC", "Microsoft YaHei", sans-serif; /* 界面文字 */
--font-number: "DIN Alternate", "Roboto Mono", monospace; /* 分数、倒计时 */
三、桌面布局（俯视 45° 微透视）
整体结构
text
┌─────────────────────────────────────────────┐
│  [左上：玩家信息]        [右上：玩家信息]      │
│                                             │
│      [左家牌墙]    [中央罗盘]    [右家牌墙]   │
│                                             │
│  [左下：玩家信息]        [右下：玩家信息]      │
│                                             │
│              [底部：玩家手牌]                │
│              [底部：操作按钮]                │
└─────────────────────────────────────────────┘
中央罗盘（视觉焦点）
位置：屏幕正中央，直径占屏幕宽度 40%。

结构：

外圈：金色圆环，宽度 4px，box-shadow: --shadow-glow-gold。

内圈：深绿色圆形，直径 90%，带内阴影。

中央数字：倒计时数字（如“08”），字号 48px，颜色 --color-cyan-glow，text-shadow: --shadow-glow-cyan。

方向标识：上下左右四个小字（东、南、西、北），字号 14px，颜色 --color-gold-light。

环形进度条：外圈内侧，宽度 6px，颜色从 --color-success 渐变到 --color-danger，随倒计时减少。

下方文字：“菜鸟场”“底分：500”，字号 16px，颜色 --color-text-secondary。

四家牌墙
位置：围绕中央罗盘，呈矩形排列。

样式：每张牌背朝上，深绿色渐变，牌与牌之间无间隙，整体有厚度感。

阴影：--shadow-tile。

牌墙高度：3 层堆叠，每层错位 2px，模拟立体感。

玩家手牌（底部）
位置：屏幕底部居中，横向排列。

牌面：朝上，象牙白渐变，圆角 --radius-tile，阴影 --shadow-tile。

间距：牌与牌之间 2px。

选中态：上浮 8px，加金色边框 2px，阴影 --shadow-tile-hover。

牌面字体：--font-tile，字号 28px，颜色红/蓝/绿（万/筒/条）。

四、麻将牌材质规范
牌面（正面）
背景：--color-tile-face。

圆角：--radius-tile。

阴影：--shadow-tile。

内阴影：inset 0 1px 2px rgba(255,255,255,0.8)，模拟高光。

字体：--font-tile，粗体，颜色：

万：#C62828（红）

筒：#1565C0（蓝）

条：#2E7D32（绿）

字牌：#1A1A1A（黑）

浮雕效果：text-shadow: 0 1px 0 rgba(255,255,255,0.8), 0 -1px 0 rgba(0,0,0,0.2)。

牌背（背面）
背景：--color-tile-back。

花纹：金色菱形纹路，透明度 20%。

圆角：--radius-tile。

阴影：--shadow-tile。

五、玩家信息组件
位置
左上、右上、左下、右下四角。

每个组件包含：头像、昵称、分数、状态标签。

样式
头像：圆形，直径 48px，边框 2px 金色，阴影 --shadow-glow-gold。

昵称：字号 14px，颜色 --color-text-primary。

分数：字号 18px，--font-number，颜色 --color-gold-light。

状态标签：

“庄”：金色底，深色文字，圆角 4px，发光 --shadow-glow-gold。

“听”：青色底，白色文字，发光 --shadow-glow-cyan。

“胡”：红色底，白色文字。

六、操作按钮
位置
底部居中，手牌上方。

样式
背景：--color-btn-bg。

边框：2px --color-btn-border。

圆角：--radius-btn。

文字：字号 16px，颜色 --color-text-primary。

阴影：--shadow-panel。

悬停态：背景亮度 +10%，发光 --shadow-glow-gold。

按下态：缩放 0.96，阴影减弱。

按钮列表
出牌、自摸、提示、取消、胡。

七、动效规范
出牌动画
选中的牌从手牌位置飞到桌面中央，时长 300ms，缓动 cubic-bezier(0.34, 1.56, 0.64, 1)（带超调）。

落地时轻微弹跳，阴影扩散。

摸牌动画
新牌从牌墙位置滑入手牌，时长 250ms，缓动 ease-out。

倒计时
环形进度条每秒减少，颜色从绿渐变到红。

最后 5 秒，数字闪烁，颜色变红。

胡牌动画
中央罗盘爆发出金色粒子，牌面高亮，时长 500ms。

八、背景与氛围
桌面背景
--color-table-bg。

叠加噪点纹理，透明度 5%。

边缘暗角：--shadow-inset-vignette。

桌面边缘
金色花纹边框，宽度 8px，带浮雕效果。

环境光
顶部柔和光源，模拟麻将馆吊灯。

桌面有轻微反光，透明度 10%。

九、禁止事项
禁止使用纯扁平色块，所有元素必须有阴影。

禁止使用亮绿色（#00FF00）或纯白色（#FFFFFF）作为大面积背景。

禁止所有动画使用同一时长，进场 250-300ms，退场 ≤200ms。

禁止文字对比度低于 4.5:1。

禁止在深色模式下简单反色，需重新调整阴影和饱和度。

十、输出要求
智能体需输出以下之一：

HTML + CSS 代码：完整可运行，包含所有颜色值、阴影、渐变、动效。

Figma 设计稿描述：每个元素的坐标、尺寸、颜色、阴影、字体。

React/Vue 组件代码：按组件拆分（桌面、牌墙、手牌、玩家信息、按钮）。
# APP_design.md 33 条规范 × 玄黄移动端对齐审计

> 2026-10-10 · 逐条在代码库 grep 取证，非主观判断。
> 结论先行：**9 条已具备、3 条部分具备、19 条缺失（其中 2 条真问题、6 条高性价比可立即做、11 条成本高后置）**

## 一、已具备 ✔（不用动）

| # | 条目 | 现状取证 |
|---|------|---------|
| 11/30 | reduced-motion 降级 | mobile-product.css 全局 .001ms；掼蛋 shake 单独降级 |
| 20 | 骨架屏 shimmer | SkeletonBlock.vue（sk-shimmer 1.4s），Contacts/Life/Novel 已接 |
| 22/23 | 操作音效+空间化 | utils/games/sfx.js 成熟，含 panOf 声道（游戏内） |
| 26 | 数字滚动 | utils/games/countUp.js（掼蛋/麻将结算、时光痕迹） |
| 31 | 深色模式真适配 | v2.46.32 墨夜手账：独立配色非反色，降饱和+硬阴影换深色版 |
| 16 | 边缘回弹 | Android WebView 原生 overscroll 自带 |
| 19 | 焦点环 | main.css 全局 focus-visible 环 |

## 二、部分具备 ◐（有底子，没达标）

| # | 条目 | 差距 |
|---|------|------|
| 13 | 分级触觉 | 4 处 vibrate(6~8ms) 全是 light；无 medium/heavy 分级封装 |
| 15 | 交错入场 | 工作台/掼蛋/麻将各写各的 delay，无统一 token |
| 12 | 时长缓动系统化 | 桌面只有 --motion-slow 一个；移动端无 duration/easing token |
| 24 | 空状态 | 有文案但多为裸「暂无」；cd-empty 有按钮；无统一插图+CTA 组件 |
| 25 | 行内校验 | el-form rules 有；错误抖动/shake 只在游戏，表单未接 |
| 3 | 提交按钮状态机 | el-button loading 是换组件，无 in-place 成功态 |

## 三、真问题（这轮改版引入/暴露，建议立即修）

| # | 条目 | 问题 |
|---|------|------|
| **29** | 对比度达标 | 新宣纸主题 `--m-text-3: #98917F` 在 `#FFFDF8` 卡片上 ≈3.2:1，**低于 WCAG AA 4.5:1**；辅助文字普遍偏浅 |
| **32** | 状态栏沉浸 | `index.html` theme-color 硬编码 `#0a1220`（深蓝夜），与宣纸底 `#F7F3EA` 日间严重割裂；且从不随主题切换 |

## 四、高性价比可做（推荐本期）★

| # | 条目 | 方案 | 预估 |
|---|------|------|------|
| 32 | theme-color 动态化 | main.js 按主题 setAttribute（宣纸日 #F7F3EA / 墨夜 #211F1B），每分钟 applyDayTheme 顺带刷 | 极小 |
| 29 | 对比度修复 | --m-text-3 提到 #857D6A（≥4.5:1）；夜间 #7A7263 → #8D8471 | 极小 |
| 26 | 数字滚动推广 | countUp 接记账 fin-kpi-val + 工作台 abb-hero__num + 财经 st-kpi-v | 小 |
| 13 | 触觉分级 | 封装 haptic.js（light 8/medium 16/heavy [8,40,8]），记账成功=medium、删除/错误=heavy，TabBar=light | 小 |
| 5 | 标签指示条超调 | fin-tabs 自绘指示条：spring overshoot ≤10%、≤200ms（规范验收值） | 中 |
| 12 | 动效令牌 | mobile-paper.css 加 --m-dur-in 260ms / --m-dur-out 180ms / --m-ease-spring cubic-bezier(.34,1.56,.64,1) | 小 |
| 3 | 提交按钮状态机 | 封装 StateButton.vue：同位置 loading→✔→还原，记账「记一笔」先接 | 中 |
| 24 | 空状态统一 | EmptyState.vue（宣纸风简笔插图+文案+CTA），替换 GlobalTopBar/TopBar 各裸「暂无」 | 中 |

## 五、成本高后置（不建议本期）

| # | 条目 | 理由 |
|---|------|------|
| 1/9 | 搜索形变 / 顶栏滚动收起 | 移动端无全局搜索入口，需先做信息架构 |
| 2/6 | FAB 原位展开 / 步进器 | 现无 FAB 与购物车型交互场景 |
| 4/10 | 图标 morph / 圆形揭示 | 纯锦上添花，SVG 路径制作成本高 |
| 7/8/18 | 就地展开 / FLIP / 共享元素转场 | 需要路由与布局重构配合，单独立项 |
| 14/17 | 跟手惯性 | 现靠原生滚动，自研拖拽性价比低 |
| 21 | 视差 | 移动端刚做完去光斑收敛，往回走 |
| 27/28 | 进度 ETA / 动态字体 | 工具类加载均 <1s；APK 内 WebView 字体缩放场景少 |
| 33 | 分屏适配 | 玄黄无平板/折叠屏目标设备 |

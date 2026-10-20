App 高级交互质感设计规范
一、动效与形变模型
1. 搜索框展开形变
触发：点击搜索图标

行为：图标通过路径插值（Path Interpolation）直接形变为输入框，光标自动聚焦，页面不跳转。

技术关键词：Shape Morphing、Auto Focus、Layout Continuity

验收：无页面切换，焦点在 100ms 内就位。

2. 悬浮按钮原位展开
触发：点击悬浮操作按钮（FAB）

行为：按钮在原位展开为操作面板；关闭时反向收回至按钮形态。

技术关键词：Origin-Aware Expansion、Reverse Animation

验收：展开/收回动画共享同一锚点，无位移跳变。

3. 提交按钮状态机
触发：点击提交

行为：同一按钮位置依次显示加载中、完成、结果三种状态，不替换组件。

技术关键词：State Machine、In-Place Transition

验收：按钮尺寸与位置在状态切换间保持稳定。

4. 图标路径插值变形
触发：菜单展开/收起、播放/暂停切换

行为：三线菜单通过路径插值（Path Interpolation）变形为关闭图标；播放键同理变形为暂停键。

技术关键词：SVG Path Morphing、Interpolator

验收：变形过程无跳帧，路径点数一致。

5. 标签指示条超调动效
触发：切换标签

行为：底部指示条先拉向新位置，再回弹收回，带超调（Overshoot）。

技术关键词：Spring Animation、Overshoot、Interpolator

验收：超调幅度 ≤ 10%，回弹时间 ≤ 200ms。

6. 按钮变步进器
触发：点击加入按钮

行为：按钮展开为数量选择器；数量归零时自动复原为按钮。

技术关键词：Morphing Stepper、Auto Reset

验收：归零后 150ms 内恢复按钮形态。

7. 列表项就地展开
触发：点击列表项

行为：选中项就地展开详情，其余内容顺势下移，不跳页。

技术关键词：In-Place Expansion、Layout Shift、Accordion

验收：展开过程无滚动跳跃，相邻项平滑避让。

8. 列表/网格 FLIP 切换
触发：列表视图切换为网格视图

行为：使用 FLIP 布局技术，各项沿弧线缓动到新位置，不重新加载。

技术关键词：FLIP (First-Last-Invert-Play)、Arc Easing、Layout Transition

验收：切换过程无白屏，元素身份可追踪。

9. 顶栏滚动收起
触发：页面滚动

行为：滚动进度驱动搜索栏收起为图标；反向滚动时还原。

技术关键词：Scroll-Driven Animation、Progress Mapping、Reverse Restore

验收：收起/还原与滚动位置线性对应，无延迟。

10. 菜单圆形揭示转场
触发：点击菜单按钮

行为：以按钮为中心圆形揭示（Circular Reveal）铺满全屏，菜单项交错进入。

技术关键词：Circular Reveal、Staggered Entrance、Clip-Path

验收：揭示动画 ≤ 300ms，菜单项交错延迟 ≤ 50ms/项。

二、无障碍与动效降级模型
11. 减少动效适配
触发：系统开启“减少动态效果”

行为：所有弹簧、视差、形变动画降级为淡入淡出或直接切换。

技术关键词：prefers-reduced-motion、Motion Reduction、Fallback

验收：开启后无任何位移/缩放动画。

12. 动效时长与缓动系统化
触发：所有动画

行为：进场 250-300ms，退场 ≤ 200ms；小元件用快速弹簧，大区域用慢速弹簧。

技术关键词：Duration Token、Easing Token、Spring Physics

验收：同类动画时长误差 ≤ 50ms。

13. 分级触觉反馈
触发：关键操作（成功/警告/错误）

行为：轻点 light，确认 medium，错误 heavy。

技术关键词：Haptic Feedback、Impact Style、Notification Feedback

验收：触觉与视觉反馈同步误差 ≤ 50ms。

14. 手势跟手与惯性
触发：拖拽/滑动

行为：动画实时跟随手指；松手后按速度计算惯性滑行。

技术关键词：Gesture-Driven Animation、Inertia、Deceleration Curve

验收：跟手延迟 ≤ 16ms，惯性曲线自然。

15. 交错与层级动效
触发：列表/一组元素出现或变化

行为：元素错开时间依次进入（每项延迟 50ms），暗示层级关系。

技术关键词：Staggered Animation、Hierarchy Cue

验收：交错延迟均匀，无堆积。

三、触觉与物理反馈模型
16. 边缘弹性回弹
触发：列表滑到顶部/底部

行为：内容像橡皮筋一样拉长再弹回。

技术关键词：Rubber Band Effect、Overscroll Bounce

验收：回弹幅度 ≤ 20px，时间 ≤ 300ms。

17. 拖拽跟手与惯性
触发：拖拽元素

行为：元素实时跟手；松手后按速度惯性滑行。

技术关键词：Drag Tracking、Inertia Scroll、Velocity-Based

验收：跟手无延迟，惯性距离与速度成正比。

四、视觉与空间连续性模型
18. 共享元素转场
触发：列表页进入详情页

行为：被点击卡片（头像/封面）飞至详情页对应位置。

技术关键词：Shared Element Transition、Hero Animation

验收：元素身份连续，无闪烁。

19. 焦点态与悬停态
触发：指针悬停 / 键盘 Tab

行为：悬停时微放大、阴影加深；焦点环清晰美观。

技术关键词：Hover State、Focus Ring、Accessible Focus

验收：焦点环对比度 ≥ 3:1。

20. 骨架屏呼吸感
触发：内容加载中

行为：骨架屏用 shimmer 渐变扫过，布局与真实内容一致。

技术关键词：Skeleton Screen、Shimmer、Layout Match

验收：加载完成后无布局跳变。

21. 滚动视差与层级
触发：页面滚动

行为：背景与前景不同速度滚动，营造纵深。

技术关键词：Parallax Scrolling、Depth Layer

验收：速度差 ≤ 10%，无眩晕感。

五、声音设计模型
22. 操作音效
触发：点击/切换/成功/失败

行为：播放 50-150ms 提示音，音色统一、音量克制。

技术关键词：UI Sound、Brand Sound、Audio Feedback

验收：无突兀感，可关闭。

23. 声音空间化
触发：通知/按钮点击

行为：音效从元素所在方向传来（左/右声道）。

技术关键词：Spatial Audio、Stereo Panning

验收：方向感清晰，无延迟。

六、内容与状态处理模型
24. 空状态设计
触发：无数据

行为：插图 + 解释 + 下一步行动按钮。

技术关键词：Empty State、CTA、Illustration

验收：无“暂无数据”裸文案。

25. 错误状态友好化
触发：输入错误

行为：字段下方就地显示红色提示，边框变红、轻微抖动。

技术关键词：Inline Validation、Shake Animation、Error State

验收：无 Alert 弹窗，原地修正。

26. 数字滚动动画
触发：数值变化

行为：像老虎机一样滚动到新数值。

技术关键词：Number Roller、Odometer Animation

验收：滚动时间 ≤ 300ms。

27. 进度预估时间
触发：加载 > 1s

行为：显示进度条；> 3s 显示预估剩余时间。

技术关键词：Progress Indicator、ETA、Loading State

验收：预估不准时显示“正在处理”。

七、无障碍与包容性模型
28. 动态字体支持
触发：系统字体放大

行为：布局不崩，文字换行，按钮撑大，图标缩放。

技术关键词：Dynamic Type、Accessible Layout

验收：最大字体下无内容截断。

29. 色彩对比度达标
触发：所有文字/背景

行为：对比度 ≥ 4.5:1（WCAG AA）。

技术关键词：Contrast Ratio、WCAG AA

验收：无浅灰字配白底。

30. 减少动效降级
触发：系统开启减少动态效果

行为：弹簧/视差/形变降级为淡入淡出或直接切换。

技术关键词：prefers-reduced-motion、Motion Fallback

验收：无位移/缩放动画。

八、系统级整合模型
31. 深色模式真适配
触发：系统切换深色模式

行为：重新设计深色配色，阴影减弱、边框变细、饱和度降低。

技术关键词：Dark Mode、Color Token、Elevation

验收：无简单反色，对比度达标。

32. 状态栏与导航栏沉浸式处理
触发：页面滚动

行为：导航栏背景从透明渐变为毛玻璃；状态栏图标颜色随背景切换。

技术关键词：Immersive Mode、Blur Effect、Status Bar Style

验收：边缘融合自然，无突兀色块。

33. 分屏与多任务适配
触发：iPad/折叠屏分屏

行为：布局自适应，侧边栏收起，内容区重排。

技术关键词：Adaptive Layout、Multitasking、Split View

验收：无简单拉伸，内容不截断。
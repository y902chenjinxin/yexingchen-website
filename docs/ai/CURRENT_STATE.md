# 玄黄 · 当前状态（断档接续入口）

> 后续智能体/协作者接续工作的第一份文档。先读本文件了解「现在到哪了」，需要细节再翻 `WORK_LOG.md`（交付台账）与 `HISTORY.md`（演进与踩坑）。

## 一、项目定位

云上「玄黄」个人平台：浮空岛（音乐/小说/视频/日志/工具）+ 个人工作台（笔记/任务/资产/AI 助手/回收站/个人资料）。
技术栈：Vue3 + Vite + Pinia + Element Plus | FastAPI + SQLAlchemy + SQLite | Nginx + PM2 + PWA。
线上：https://yexingchen.cn（腾讯云 CVM 203.195.208.25，OpenCloudOS 9.4）。

## 二、最近交付（9/6 最新）

| 时间 | 内容 | Commit |
|------|------|--------|
| 2026-09-07 | **旅行足迹地图 · 视觉与交互升级（SW `xuanhuang-v53`，见 `TRAVEL_MAP_REDESIGN_20260907.md`）**：夜色雨青玻璃重构 `TravelMap.vue`——省界玻璃青渐变、航线三次贝塞尔+辉光+流动虚线、打点按次数分级+青玉渐变、南海诸岛玻璃 mini-map、两级 hover 浮卡；滚轮缩放(1–14×)+拖拽平移+双击复位、省份下钻（dim 变暗+时间线过滤+清除 chip）、fly-to 聚焦行程、打点中心 75% 内激活行程外环带 isPointInFill 穿透省份下钻。生产取证 PASS：京沪渐变+贝塞尔+mini-map、wheel 缩放生效、点打点激活+fly-to、下钻 chip+cards 过滤+清除恢复、两级浮卡；测试数据已清理库归零 | 待提交 |
| 2026-09-07 | **旅游足迹模块上线（SW `xuanhuang-v52`，见 `TRAVELS_PLAN_20260907.md`，User「标记旅行过的地方」）**：纯前端 SVG 中国地图（离线 GeoJSON `frontend/public/geo/china.json` 省界+九段线 + `geo/cities.json` 34 省 230+ 城市坐标，零第三方地图 API）。后端 `Travel/TravelCity` 模型 + Alembic 迁移 `d1e2f3a4b5c6`（生产 upgrade head 建两表）；`/api/travels`（CRUD + `/stats` + `/upload` 图片≤10MB/视频≤200MB）；公开查看+登录编辑。前端 `TravelMap`（已访省份金色高亮+城市按 seq 打点连线）、`TravelTimeline`、`TravelCityPicker`（省→市两级）、`TravelEditor`（内联录入含 Markdown 正文/星级/相册/视频）、`TravelDetail`（`utils/markdown.js` 安全渲染）；`/travels` 路由（地理数据放 `/geo/` 避 `dist/travels/` 遮蔽）+ 工作台玉简入口。生产浏览器取证 PASS：云南省高亮+丽江打点、星级 ★★★★ 真星星（修 `dist` 陈旧缓存致字面量）、登录新建广东省/广州点亮+Markdown 渲染。验收后已清理测试数据，库归零待录入 | 待提交 |
| 2026-09-06 | **股票查看模块 /stocks 上线（SW `xuanhuang-v48`，见 `STOCKS_PLAN_20260906.md`）**：`StockWatchlist` 模型 + Alembic 迁移 `e5f6a7b8c9d0`；`stock_fetcher`（东财实时报价 / 日 K 三源回退[东财→腾讯→新浪] / 联想搜索，TTL 缓存）；`/api/stocks` CRUD+quote+kline+search+summary+dashboard；`StocksView`(KPI+加自选内联+实时表格)、`StockDetailView`(自绘 SVG 蜡烛图 `KlineChart`) 替换占位页；工作台行情卡接 dashboard。生产实测修复：`f58` 名称字段误用 `_f2`、搜索 `MarketType` 字符串映射、`push2his` WAF 拒连→K 线三源回退 | 262e60f |
| 2026-09-06 | **资讯推送模块上线（SW `xuanhuang-v45`）**：`/feeds` 三栏玻璃布局（源 CRUD / 文章筛选分页 / 阅读器 + AI 摘要 + 收藏为笔记 `to-note`），`FeedSource/FeedArticle` + 迁移 `a1b2c3d4e5f7`；工作台资讯卡接 dashboard。遗留：服务器未配 `AI_*`，摘要为 FakeProvider 占位 | 3f3f138 |
| 2026-09-04 | **工作台极简收敛（SW `xuanhuang-v33`，最新，User「把这三个都干掉」）**：删除工作台数据区三张卡「最近编辑/待整理草稿/标签」（`wb-grid` 与 `WorkbenchView` 脚本树清空，只留玉简+快捷动作+页脚）；前置 v32 已删玉简「内容资产/任务镜台」两张卡 + 「分类入口」整块。工作台现仅含 玉简轮播+快速记录/AI助手+网安页脚。浏览器实测：三卡文本 0 残留、快捷动作+页脚正常 | 本轮 |
| 2026-09-04 | **工作台模块精简：移除「内容资产」+「任务」界面入口，日志升级为操作日志管理页（SW `xuanhuang-v31`，User 遗留「除音视频/文件/工具外的空间需增加管理页」）**：内容资产(`/assets`)与任务(`/tasks`)**仅从界面移除、保留 DB 数据**（顶栏导航只剩笔记、搜索联想去掉资产/任务、工作台删内容资产/任务卡片与今日/逾期任务板块、分类入口去掉网页/图片/PDF/任务、路由删 `/tasks`/`/assets`）；日志页沿用四库**浏览+管理合并一页**（`IslandInnerBase` 重构，浏览=时间线、管理=表格，后端 `/api/logs` 增时间/动作/关键词筛选 + `DELETE /api/logs` 批量删 + `/api/logs/clear` 清空，前端日期范围/动作下拉/搜索/分页/勾选批删/清空，页内中文确认；日志只读不逐条编辑）。生产浏览器清 SW 实测 14 项全 PASS | 本轮 |
| 2026-09-04 | **桌宠本体点击穿透 + 右上角"抓手"拖拽（SW `xuanhuang-v30`，最新，修复"点不进去了"）**：根因——`.whale-frame` 命中区为整 sprite 盒（约 175×215）+ `pointer-events:auto`，鲸鱼拖到玉简/按钮上即整片拦截；`passThroughClick` 透传不可靠。修复：`.whale-frame` 改 `pointer-events:none` **完全点击穿透**；新增右上角 `.whale-handle` 小抓手为唯一命中区（按住拖动、单击开设置面板）；删 `passThroughClick`。清 SW 后实测 PASS：入口跳转恢复 | 本轮 |
| 2026-09-04 | **工具/管理页页脚由"钉底"改"跟随内容"（SW `xuanhuang-v29`）**：短内容页（去水印/PDF/像素压缩/工具详情等）页脚原钉在 100vh 底部，内容少时与内容间大片空隙显得悬浮。`.inner-footer` 移入 `.inner-main` 内随内容流动（`margin-top:16px` 紧贴内容末端）。DOM 取证：工具页页脚与内容间距 16px；音乐管理页 47px 为面板内边距，仍贴面板底边。注：首轮回归"FAIL"系 SW 缓存旧包，旁路后 v29 生效 | 本轮 |
| 2026-09-04 | **修复工作台缩放黑边 + 页脚悬浮（SW `xuanhuang-v28`）**：工作台改全宽浅底（内容与页脚 1248px 居中）消除黑边 + 页面专属浅色页脚；App.vue 全局页脚按路由抑制避免重复/悬空；岛屿页脚先顶到真实底部（后由 v29"跟随内容"取代） | 本轮 |
| 2026-09-04 | **工具统一管理 + 像素压缩 + 全站网安页脚 + 四管理页分页 + 桌面缩放收敛（SW `xuanhuang-v27`）**：① 工具统一管理——`Tool` 增 `kind/is_enabled/sort_order`，内置工具（视频去水印/PDF/像素压缩）置顶且**禁删**、可↑↓排序/上下架，`ToolView` 从 DB 渲染；② 像素压缩 `/tool/compress`——100% 纯前端（智能/自定义/仅缩放，防负优化，ZIP 打包，GIF 转首帧，≤10MB，`revokeObjectURL` 清内存）；③ 全站网安页脚 `SiteFooter`——公安盾牌+皖公网安备(→beian.mps.gov.cn)+皖ICP备(→beian.miit.gov.cn)可跳转，`App.vue`/`IslandInnerBase` 双主题接入；④ 工具/音乐/小说/视频管理页**客户端分页**（默认 10，可切 10/20/50）；⑤ `main.css` 增管理页三档缩放断点，80%~150% 桌面缩放不破版。生产实证 PASS：底部页脚含双备案可跳转、工具管理含三内置且删除禁用、分页控件渲染 | 本轮 |
| 2026-09-04 | **顶栏切换背景音乐双音轨深度修复（SW `xuanhuang-v24`）**：网络层实测复现——切歌瞬间旧/新两条 `/api/music/*/stream` 同时传输。修复 `player.js`：`hardStop()`（`pause+src=''+removeAttribute+load`）硬停、`setBackground` 顶部先停旧歌（早于 await）、`playSeq` 单调序号丢弃过期回调、`armResume()` 单一稳定监听防累积。生产无缓存会话复测 PASS：旧流先 `completed` 结束、新流才开始，无重叠 | 本轮 |
| 2026-09-04 | **播放条收敛 + 去点击音效（SW `xuanhuang-v21`）**：背景音乐（`mode==='bgm'`）不再显示底部播放条（`player.js` 改 `shows=computed(playlist&&curItem)`，仅点播显示，覆盖暂停/取消后恢复背景场景）；去除岛屿卡片悬停/点击音效（移除 `useIslandSound` 整套 + `JadeCarousel` mouseenter/mouseleave 绑定）。生产浏览器实测 6 项全 PASS | 本轮 |
| 2026-09-04 | **内容板块去「岛」重构 + 工具独立页 + 视频解析增强（SW `xuanhuang-v14`）**：五模块去「岛」，`/music /novel /video /tool /tool/:id /tool/watermark /log` 新路由 + 旧 `/island/*` 重定向；每模块浏览+管理合并一页（卡片墙 + 顶部「管理」切表格，全字段+增删改查、音乐默认曲只读）；工具独立页（外部 iframe、去水印 `/tool/watermark` 置顶）；视频解析内联预览 +「下载音频」服务端 ffmpeg 抽音轨。生产装 ffmpeg(dnf/EPEL)，后端修 `starlette.background` 导入。生产浏览器实测 9 项全 PASS | 本轮 |
| 2026-09-03 | **视觉质感升级（玄素琉璃深色材质体系）**：玉简上移防遮挡；桌宠面板 z-index 提至顶栏之上(10001)+最大高度滚动防矮屏遮挡；新增 `--ls-*` 墨青玻璃深色 token，`IslandInnerBase` 背景/header 玉化、5 岛屿内页卡片全部玻璃化，补 `--island-*` 旧色映射防 SVG 落黑；SW 升 `xuanhuang-v11` | 本轮 |
| 2026-09-03 | **工作台重构 + 弃用 /home（"冷峻东方"）**：玉简轮播 `JadeCarousel`（8 张）+ 全局悬浮磨砂顶栏 `GlobalTopBar`（导航/即时搜索联想/音频/用户下拉，移动端折叠）+ 工作台改浅色宣纸留白玉简化；废弃 `/home`、新增 catch-all→`/workbench`；前端追加 `--lj-*` token；SW 升 `xuanhuang-v10`。本地+生产浏览器实测 10 项全 PASS（含 /home 重定向） | 本轮 |
| 2026-09-03 | **鲸鱼娘桌宠上线 + 三轮优化**：登录后全站常驻；单击弹配置面板(固定编排↔随机)、双击散步、拖拽、跑步横穿且朝向修正；Ⅰ缩放75%/池扩；Ⅱ间隔5~7s/淡出淡入；**Ⅲ双层视频真·交叉淡入淡出(无消失空洞)+间隔放宽8~13s**；SW `xuanhuang-v8/v9` | `c5130dc`/`98b1b79` |
| 2026-09-03 | **AI 对话页内联化**：发送免二次确认弹窗、结果在气泡内联应用；SW 升 `xuanhuang-v7` | `bc8faba`/`6ee4888` |
| 2026-09-02 | 修仙风全站统一（工作台 7 子视图 + 5 岛屿琉璃化）；笔记颜色面板 + 吸色；AI 回复修复 | `9db8760` 等 |
| 2026-09-02 | AI Provider 用户级配置；BackButton 收尾 | `dbd24fa`/`9ad3b13` |

> 完整逐日台账见 `WORK_LOG.md -> 一、交付时间线 / 二、关键交付明细`。

## 三、本地开发 / 验证约定

- 本地账号：`admin@yexingchen.cn` / `<见 .secrets/local.env>`。
- 生产账号同邮箱密码（`.secrets/local.env`）。
- 前端 `npm run build` + `npm run test`（vitest，`--no-file-parallelism`）；后端 `.\venv\Scripts\python.exe -m pytest`。
- 部署：`scripts/ai_deploy.py`（传 dist+后端+pm2 restart）；发布前端**务必同步升 `sw.js` 版本**清 SW 缓存。
- 凡「前端显示 / 配置不生效」类问题：**自拉浏览器实测取证截图**，以截图为准（见 `AGENTS.md`）。

## 四、开放 / 遗留事项

> 详细见 `WORK_LOG.md -> 三、开放/遗留事项`。核心：

1. ~~岛屿内部页数据不显示 / `/api/auth/me`、背景音乐流 `ERR_ABORTED`~~ ——**已解决**（本轮浏览器实测内页正常、流播 200）。
2. 视频去水印 `parse-video-py` 各平台解析稳定性待长期观察（独立服务 8070，网络波动/平台变更可能临时不可用）。
3. AI Provider / 笔记等专项单测补齐（部分已补：颜色、AI 解析）。
4. `api_key` 明文存储（用户决定不加密）。
5. `manifest.webmanifest` MIME 待 Nginx 补 `application/manifest+json`。
6. Git 历史旧敏感内容清理（用户「以后做」）；HomeView/LoginView 大拆分（已推迟）。

## 五、回到主线

- 设计/界面新改动：先读仓库内 `docs/DESIGN_INKWASH.md`（唯一生效规范），再落 `docs/ai`（WORK_LOG/本文件）再接续改代码。
- 路线图/PRD：仓库内 `docs/PRD_v2.12.md`；功能总览 `FEATURES.md`；技术决策 `DECISIONS.md`。

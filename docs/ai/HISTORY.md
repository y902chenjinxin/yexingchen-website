# 项目演进与协作历史

> 记录玄黄从搭建、多模型接力开发到收尾的完整脉络、关键坑与已修复问题。
> 目的：让任何后续智能体 / 协作者快速理解「为什么文档这么写、代码这么改」，避免重复踩坑。

## 工具链分工

| 阶段 | 角色 | 工作 |
|------|------|------|
| 框架搭建 | **GPT** 初始生成 | 初版前端（Vue3 岛屿平台）+ 后端（FastAPI）骨架 |
| 主力执行 | **MiniMax** | 需求细化、功能开发、数据库迁移、测试、文档 |
| 收尾验收 | **Codex / Trae（当前助手）** | 独立检查、问题修复、设计统一、部署上线 |
| 平台运维 | **用户** | 服务器、域名、证书、云控制台、密钥、最终确认 |

## 里程碑时间线

> 完整的逐日交付台账见 `WORK_LOG.md`（本目录），此处仅保留演进脉络与踩坑速查。

- **v1.x ~ v2.x（早期）**：GPT 搭出云上浮空岛个人平台（音乐/小说/视频/日志/工具/用户系统）。
- **MVP（v2.1 ~ v2.4）**：MiniMax 完成 MVP；工作台雏形形成。
- **2026-08-30**：MVP 部署上线（Nginx+PM2+SQLite，DB 9→22 表）。
- **2026-08-31**：登录跳转 P0 修复；Git 推送经验沉淀。
- **2026-09-01**：router 补全（8 条工作台路由）+ Nginx 修复（`/assets`、`/health`）。
- **2026-09-02**：AI Provider 用户级配置；BackButton 收尾；修仙风全站统一（登录页锚点、「一殿一室」）；笔记编辑器 6 修复 + 文字颜色面板 + 吸色；AI 回复修复。
- **2026-09-03**：AI 对话页内联化（免弹窗发送、结果内联导入）；鲸鱼娘桌宠接入并上线 + 两轮体验优化（SW `xuanhuang-v8`）。
- **2026-09-04**：内容板块**去「岛」重构**（路由 `/island/*`→`/music` 等）+ 工具独立页 + 视频解析「下载音频」服务端抽音轨；生产装 ffmpeg（SW `xuanhuang-v14`）。
- **2026-09-04**：管理页按钮互斥修复（Element 中文 locale + 桌宠 z-index 1800 下探 + 管理页内中文删除确认）、桌宠停原位/边界镜像调头、搜索按钮化（SW `xuanhuang-v17`）；修复新上传音乐无法播放（stream 路径统一 `uploads/`，`b1624f6`）；鲸鱼轻点穿透、按住才可拖（SW `xuanhuang-v20`，`4e754f7`）；**播放条收敛（背景 BGM 不显示）+ 去卡片点击音效（删 `useIslandSound`）（SW `xuanhuang-v21`）**。
- **2026-09-04**：**四模块批量删除**（音乐/小说/视频/工具管理表格复选框勾选 → 批量删除按钮 → 管理页内中文二确 → 一键逐行删除，音乐默认曲不可勾）+ **点播结束后自动恢复默认背景 BGM**（`player.js` `ended`/✕关闭 → `playBgm`，User 确认预期）（SW `xuanhuang-v22`）。
- **2026-09-04**：**修复现网双背景音乐**（`switchSource` 切源前 `pause+removeAttribute+load` 释放旧连接，双 `/api/music/*/stream` 重叠消除）+ **PDF 多功能纯前端工具**（`/tool/pdf`，图片转 PDF / PDF 转图片 / 合并拆分，CDN 按需加载）+ **两个桌面工具集成**（练字/中英文翻译拷入 public/tools 并 DB 登记 iframe 内嵌）（SW `xuanhuang-v23`）。
- **2026-09-04**：**顶栏切换背景音乐双音轨深度修复**——`player.js` 新增 `hardStop()`（`pause+src=''+removeAttribute+load` 幂等硬停）与 `playSeq` 单调序号：`setBackground` 顶部先停旧歌（早于 await 网络请求）、过期回调丢弃、手动 resume 收敛单一监听器 `armResume()`（SW `xuanhuang-v24`）。
- **2026-09-04**：**工具统一管理 + 像素压缩纯前端工具 + 全站网安页脚 + 四管理页分页 + 桌面缩放收敛**——`Tool` 增 `kind/is_enabled/sort_order`（内置工具置顶+禁删+上下架+排序）；`/tool/compress` 像素压缩（browser-image-compression 纯前端、智能/自定义/仅缩放、防负优化、ZIP、GIF 转首帧、≤10MB、清内存）；`SiteFooter` 全站网安页脚（公安盾牌 + 皖公网安备 + 皖ICP备，官网可跳转，`App.vue` 浅色 / `IslandInnerBase` 深色双主题）；工具/音乐/小说/视频管理页客户端分页（10/20/50）；`main.css` 三档缩放断点覆盖桌面 80%~150%（SW `xuanhuang-v27`）。
- **2026-09-04**：**工作台极简收敛（SW `xuanhuang-v32/v33`）**——玉简轮播删「内容资产/任务镜台」两张卡（剩 6 张）、删工作台「分类入口」整块、再删数据区「最近编辑/待整理草稿/标签」三卡，`WorkbenchView` 脚本树清空，工作台仅剩 玉简+快捷动作+网安页脚。至此「内容资产/任务」两个模块从界面彻底清除（DB 数据保留），工作台走"去数据流、纯导航+快捷动作"的极简路线。
- **2026-09-04**：**工作台模块精简 + 操作日志管理页（SW `xuanhuang-v31`）**——移除「内容资产」(`/assets`)与「任务」(`/tasks`)的**界面入口**（顶栏导航/搜索联想/工作台卡片与板块/分类入口/路由，直接访问兜底重定向 `/workbench`），但**保留 DB 表与数据**（含笔记资产关联、回收站、AI 对话引用均不受影响）；日志页沿用四库**浏览+管理合并一页**升级为操作日志管理：后端 `GET /api/logs` 增时间范围/动作/关键词筛选，新增 `DELETE /api/logs`(批量删) 与 `/api/logs/clear`(清空，非超管仅限本人)，前端 `LogView` 用 `IslandInnerBase` 重构为时间线浏览+表格管理（日期范围/动作/搜索、分页 10/20/50、勾选批删、清空，页内中文确认；日志只读不逐条编辑）。生产浏览器清 SW 实测 14 项全 PASS。**并发踩坑：`deploy_backend.py` 硬编码上传白名单漏了 `routers/log.py`，新接口若不补会「代码改了但线上 404」**。
- **2026-09-04**：**桌宠本体点击穿透 + 右上角"抓手"拖拽（SW `xuanhuang-v30`，修复"点不进去了、点击入口没反应"）**——`.whale-frame` 命中区为整 sprite 盒（`vidbox` 常 234×287，`scale(0.75)` 后约 175×215）且 `pointer-events:auto`，鲸鱼拖到玉简/按钮上即整片拦截入口点击；此前 `passThroughClick` 临时关命中 + `elementFromPoint` 找下层 `.click()` 的透传方案实测不可靠。改为 `.whale-frame` **`pointer-events:none` 永久点击穿透**（下层入口任何时候可点），新增右上角 `.whale-handle` 小抓手为**唯一可交互命中区**（按住拖动移动/边界镜像/停原位照旧，单击开设置面板接管原面板入口）；删除 `passThroughClick` 与 `lastTap`。清 SW 后实测 PASS：`.whale-frame=none`、`.whale-handle` 存在 `cursor:grab`、「快速记录」入口成功跳转 `/notes/10`。
- **2026-09-06**：**股票查看模块 /stocks 上线（SW `xuanhuang-v48`，见方案 `STOCKS_PLAN_20260906.md` / PC_EXPAND_PLAN §5.4 W4）**——数据来自**东方财富免费接口**，`fetch_quote` 实时报价 / `fetch_kline` 日 K / `search_stocks` 联想，内存 TTL 缓存；`/stocks` KPI+自选实时表格，`/stocks/:code` 自绘 SVG 蜡烛图详情。生产端到端 + 数据源测修复三处（详见踩坑 #26-28）：名称字段误用 `_f2`、搜索 `MarketType` 字符串映射、东财 K 线主机被 WAF 拒连→改**三源回退**（东财→腾讯→新浪）。
- **2026-09-07**：**旅游足迹模块上线（SW `xuanhuang-v52`，见方案 `TRAVELS_PLAN_20260907.md`，User「标记旅行过的地方」）**——**纯前端 SVG 中国地图**（离线 GeoJSON > 等经纬投影，零第三方地图 API，数据静态放 `/geo/` 避 SPA 路由遮蔽）：后端 `Travel/TravelCity` 模型 + Alembic 迁移 `d1e2f3a4b5c6` + `/api/travels` CRUD/stats/upload（媒体扩展图≤10MB 视频≤200MB）；前端 `TravelMap`（已访省份金色高亮 `tm-prov visited-on` + 城市按 seq 打点连线）、`TravelTimeline`、`TravelCityPicker`（省→市两级）、`TravelEditor`（内联录入含 Markdown/星级/相册/视频）、`TravelDetail`（轻量 `utils/markdown.js` 安全渲染）；路由 `/travels` + 工作台玉简入口；公开查看 + 登录编辑权限分离。生产浏览器取证 PASS（云南省高亮+丽江打点、星级 ★★★★ 真星星、登录新建广东省/广州点亮）；验收后清理测试数据，生产库归零待录入。部署踩坑见 #29。

## 关键踩坑与修复（务必记住）

| # | 坑 | 症状 | 修复 |
|---|----|------|------|
| 1 | MiniMax MVP commit 漏写工作台 router | 路由从未注册，点到的工作台是 /home 误判 | 补 8 条工作台路由 |
| 2 | PM2 进程名是 `app` 非 `yexingchen-backend` | 按 `pm2 restart yexingchen-backend` 反复失败 | 用真实进程名 / 由 upload_server 执行 |
| 3 | `nginx -s reload` 有时不生效 | 配置变更不加载 | `nginx -s stop && nginx` 强制重启 |
| 4 | Nginx `/assets/` → 403 | Vite chunk 无法加载 | `location /assets/ { try_files $uri /index.html; }` |
| 5 | Nginx `/health` → 返回 SPA HTML | 健康检查被 fallback 吞掉 | `location = /health { proxy_pass ...8000/health; }` |
| 6 | 设计系统多套堆叠（variables.css） | 工作台"看着 low"、token 悬空引用 | 收敛为修仙 token 体系 |
| 7 | 悬空 token `--color-gold`/`--color-jade` | 样式失效 | 修复引用并定义专属 token |
| 8 | 损坏 CSS 值 `var(--paper-aged)2c0` | 样式解析异常 | 改为合法色值 |
| 9 | GitHub push 卡凭据弹窗 | 推送挂起 | `git -c credential.helper= push https://x-access-token:$TOKEN@…` |
| 10 | Compress-Archive 反斜杠路径 | Linux unzip 无法解压，cp 静默失败 | 用 tar 或解压到 /tmp 再 cp |
| 11 | Playwright chromium 版本不匹配 | 截图脚本失败 | 显式指定可执行文件路径 |
| 12 | 登录 `route.query.next` 未定义变量 | 登录成功不跳转 | 补 `const route = useRoute()` |
| 13 | 线上 `run.py` 误开 `uvicorn.reload=True` | SFTP 改后端代码后 PM2 restart 仍持旧模块（「改了不生效」） | 生产关 reload + 清 `__pycache__` + 确认进程真重启 |
| 14 | PWA Service Worker 不清除旧缓存 | 前端改了但用户仍见旧版（缺新 chunk→404/旧界面） | 发布前端时同步升级 `sw.js` 版本（`xuanhuang-vN`）强制清缓存 |
| 15 | MiniMax 把整段 JSON 塞进 reply / API 直上屏模型原文 | AI 回复混 JSON/思考过程、又长又重复 | 后端 `_remove_embedded_json`+`_polish_readable`，前端只展示 `res.data.text` |
| 16 | `execCommand(foreColor)` 产 `<font color>`，但净化白名单不含 `font` | 选色保存刷新即丢 | `sanitizeNoteHtml` 放行 `font`+`font[color]`、`style` 仅放行纯色 |
| 17 | `vidbox.js` 桌宠配置 key 带 `.webm` 后缀，组件拼的是无后缀 key | 桌宠空 stage、video 无 src、不报错、线上不显示 | 两处 key 统一**无后缀**；排障改本地端到端复现比对 |
| 18 | 桌宠跑步素材本体**面朝左**，旧逻辑向左移动时仍 `flipped=true` 镜像 | 向左跑时被镜像成面右 → **倒着跑**；且从右屏外冒入显突兀 | 向左跑不镜像(flipped=false)、向右才镜像；起点改右下角常驻位、横穿到 `endX=40` 停 |
| 19 | WebM/透明视频在无背景标签页/截帧时画面全黑 | 无法判定素材朝向（曾误判） | 用灰底容器(`#555`)+`video` 内嵌渲染再截图；确认三个跑步动作均面左 |
| 20 | `from fastapi.responses import BackgroundTask` 在生产 fastapi 报 ImportError | 新部署的视频音频端点后端**崩溃重启循环**（pm2 restart 数暴增、health 000） | `BackgroundTask` 在 `starlette.background`，改 `from starlette.background import BackgroundTask`（生产 venv fastapi 版本不重导出该名；本地新版可能直接可用——上线前用生产 venv `python -c "import app.main"` 预检导入） |
| 21 | 服务器是 OpenCloudOS（CentOS 系）**无 `apt-get`** | `apt-get install ffmpeg` 报 `command not found` | 用 `dnf install -y epel-release` + `dnf install -y ffmpeg`（装到 7.0.2）；`which yum dnf` 先确认包管理器 |
| 22 | `el-input clearable` 的清除 `×` 仅**悬停时可见** | 管理页「清除不恢复」没法稳定触达，实测 FAIL | 给每个管理表格搜索框另加**始终可见的「清空筛选」按钮**（有搜索词时出现，`@click` 置空关键字）+ `watch(keyword)` 空值即重查；两路都收敛到全量刷新 |
| 23 | 鲸鱼桌宠（`position:fixed` 右下、`pointer-events:auto`、z-index 10001）会**盖住/拦截**下方区域点击 | 自动化与真实小屏用户点不到被遮挡的按钮（含「清空筛选」「使用」） | 属桌宠可拖拽的设计行为，非缺陷；被测需先拖开桌宠再点。如将来该遮挡影响主操作，可给 `.whale-stage` 加「缩小/收起」或点击穿透开关 |
| 24 | 桌宠 `.whale-frame` 命中区是**整 sprite 盒**（234×287 含透明留白，缩放后约 175×215）+ `pointer-events:auto` | 鲸鱼拖到玉简/入口上方即整片拦截点击 →「点不进去了，点击入口没反应」；`passThroughClick`(临时关命中+`elementFromPoint`+`.click()`) 实物透传不可靠 | 本体改**`pointer-events:none` 永久点击穿透**，另加右上角 `.whale-handle` 小抓手为唯一可交互命中区（按住拖动/单击开面板）。SW `xuanhuang-v30` |
| 25 | 「修复未见效」常是 **Service Worker 旧包**在作祟 | 部署了新包旧交互仍在（`pointer-events` 仍是 auto、无新元素、动态模块 404） | 先 `navigator.serviceWorker.getRegistrations().unregister()` + `caches.keys().delete()` 后 `reload()` 复测获取真实结果（`xuanhuang-v30` 复演了一次） |
| 26 | Python 端接**第三方行情接口**时，ES「名称」等**字符串字段被通用 numeric 转换器吃成 None** | `fetch_quote` 用 `_f2(data["f58"])` 校名 → 沪/深/港/美四市场**一律“未找到该代码”**（URL 直 curl 却正常，极难定位） | 名称类字段必须 `str(v)` 直取，勿走 `_f2/float()`（`stock_fetcher.py`）；同理 `_build_quote` 用 `str(d.get("f58"))` |
| 27 | 东财 suggest 搜索的 `MarketType` 是**字符串数字**（`"1"`=沪、`"0"`=深、`"116"`=港、`"105/106/107"`=美）而非 `sh/sz/hk/us` | 直接 `.get(mkt,"us")` 兜底把所有非 `sh/sz/hk` 都映射成**美股**（搜"茅台"变 market=us） | 新增 `_srch_market`：先按 `MarketType` 映射表，再按 `QuoteID` 前缀（`1.`/`0.`/`116.`/`10x.`）回退 |
| 28 | 机房（腾讯云 CVM）访问东财 **K 线主机 `push2his.eastmoney.com` 被 WAF 拒连**（`requests` 与 `curl` 均 `RemoteDisconnected`，纯 IP/机房拒绝） | `/api/stocks/kline/*` 500 Internal Server Error；`push2delay`(报价)、`searchapi`(搜索) 却能通 | `fetch_kline` 改**三源回退**：东财→腾讯 `web.ifzq.gtimg.cn`(日 K `day/qfqday`)→新浪 `money.finance.sina.com.cn`，命中即缓存(300s)；部署前务必在**生产服务器**用真实请求预检哪个源通，别只在本地判断 |
| 29 | ① **旅行模块静态目录与 SPA 路由冲突**：古早把地理数据放 `dist/travels/`，而前端路由恰是 `/travels`，被 `dist/travels/` 目录遮蔽 → Nginx 直接复用这些（无 hash）路径，SPA 路由拿不到 `index.html` 变 403；② **`dist` 陈旧缓存致星级渲染字面量**（`vite build` 对同一 outDir 可能产出缺新逻辑的旧 bundle，hash 不变）：浏览器一度取回 `.tt-star` 文本为 `${"★".repeat(t.star\\|0)\|\|"—"}` 源码串而非星星 | ① `/travels` 页 403 / 地图与城市选择器数据 404；② 时间线/详情卡星级显示原始模板表达式 `{"★".repeat(t.star \|\| 0) \|\| '—'}` | ① 地理数据目录**重命名 `travels→geo`**（`frontend/public/geo/`，`sw.js` 缓存前缀同步改），`TravelMap/TravelCityPicker` 请求路径改 `/geo/china.json`、`/geo/cities.json`；② 按惯例**构建到全新 `--outDir dist2`** → 校验 bundle 含 `.repeat(p.star||0)` 编译串 → 整体替换 `dist` → `deploy_frontend.py`，SW 升 v52；部署后必须**清 SW** 复测（老缓存仍会命中旧 bundle） |

## 设计约束现状

- 唯一有效设计规范：`docs/DESIGN_INKWASH.md`（水墨国风 v2.11）。
- `docs/DESIGN_XUANMO.md` 为已废弃历史，勿参考。
- 当前方向：登录页华丽仪式 / 工作台克制光效（「一殿一室」原则）。
- 设计/界面改动前置约定：先写 `docs/ai/*.md` 方案文档再接续（见 `AGENTS.md`）。

## 稳定收敛的约定

1. 部署用 `scripts/upload_server.py`（自带 PM2 重启），无需单独 restart_pm2（已废止）。
2. 健康检查用 `/health`（不是 `/api/health`）。
3. 门控：`DEPLOY_CHECKLIST.md`（根目录）+ `scripts/workflow_progress.py`。
4. 不可逆操作（部署/推送/删数据）由用户确认后执行。
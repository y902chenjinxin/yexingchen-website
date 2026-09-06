# 玄黄 · 工作/交付汇总（WORK LOG）

> 整合原先零散的逐日部署报告、设计审视、优化计划与 MASTER 任务单的**结论与遗留**，供后续智能体/协作者接续时快速掌握「做了什么、留在哪、下步是什么」，避免断档。
> 定位：WHAT / WHEN / OPEN ITEMS。历史渊源与踩坑速查见 `HISTORY.md`；当前现状与断档接续入口见 `CURRENT_STATE.md`。
> 本文件为唯一「逐日交付台账」，不再另起逐日部署报告。

---

## 一、交付时间线

| 日期 | Commit（主要） | 交付内容 |
|------|---------------|----------|
| 2026-08-30 | — | **MVP 部署**：前后端上线 Nginx+PM2+SQLite，DB 9→22 表（12 张工作台表），`/health` 与首页 200 |
| 2026-08-31 | — | **登录跳转修复**：`LoginView` 未定义 `useRoute` 变量 → 登录后不跳转，补 `const route=useRoute()` |
| 2026-09-01 | `2b75b64`（+GPT `2954a23`） | **router 补全 + Nginx 修复**：注册 8 条工作台路由（从未注册过）、修 NoteEditor import 语法、修 Nginx `/assets/` 403 与 `/health` 被 SPA 吞掉 |
| 2026-09-02 | `dbd24fa` | **AI Provider 用户级配置**：OpenAI 兼容协议，UI 运行时切换，`api_key` 明文存储/返回脱敏 |
| 2026-09-02 | `9ad3b13` | **工作台返回按钮收尾**：新增 `BackButton`，7 个子视图接入，修复其单元测试 |
| 2026-09-02 | `aac70be` → `9db8760` | **修仙风全站统一**：登录页为锚点，「一殿一室」策略；token 收敛 + Element Plus 主题化 + 工作台全部子视图 + 五座岛屿琉璃化 |
| 2026-09-02 | `0e4c0e4` | **笔记编辑器 6 项修复**：工具栏交互、返回按钮、删除确认中文化、路由跳转/404、旧模块返回入口 |
| 2026-09-02 | `c0eea48` | **笔记文字颜色面板**：24 预设色 + 原生取色 + 吸色 + HEX/RGB 输入，及颜色持久化修复 |
| 2026-09-02 | `6cc5cbd`/`0cbbd7b` | **吸色交互定稿**：页内自绘针管吸管（否决 EyeDropper 马赛克与 getDisplayMedia 弹屏） |
| 2026-09-02 | `6dbaffc` | **AI 回复修复**：后端剥离内嵌 JSON + 前端只显示干净 text；修 `uvicorn.reload` 误开导致改文件不生效 |
| 2026-09-03 | `bc8faba` → `6ee4888` | **AI 对话页内联化**：发送免二次确认弹窗、结果在气泡内联应用；SW 升 `xuanhuang-v7` 随发确认部署 |
| 2026-09-03 | `c5130dc` | **鲸鱼娘桌宠接入 + 上线**：透明 WebM 高清源做成全站桌宠 `WhaleCompanion`，登录后全站常驻；两轮体验优化（Ⅰ：点击 3s 不闪退 / 缩放 75% / 跑步横穿 / 池扩 24；Ⅱ：换动作间隔 5~7s / 单击弹配置面板(固定编排↔随机) / 切换淡出淡入防闪烁 / 修正素材朝向修复"倒着跑"）；SW 升 `xuanhuang-v8` 已部署线上（本轮含距上次推送的 16 笔累积提交，同步推送 GitHub master） |
| 2026-09-03 | `98b1b79` | **桌宠第三轮体验优化（User 实测反馈驱动）**：① 换动作间隔放宽至 **8~13s**（`8000+rand*5000`）；② **双层视频真·交叉淡入淡出**（`crossSwitch`：两层 `<video>`，旧片 rAF 渐隐同时预开播新片渐入 380ms，消除"整只消失空洞"与换源首帧闪白；单一淡出不复存在）；SW 升 `xuanhuang-v9` 已部署线上，无痕窗口端到端实证两层淡入淡出生效（video 计数=2） |
| 2026-09-03 | 本轮 | **工作台重构 + 弃用 /home（"冷峻东方"）**：① `JadeCarousel.vue` 玉简轮播（8 张：音乐宫商流转/小说卷帙浩繁/视频光影交织/日志翰墨丹青/工具机关百变/笔记/资产/任务，半透明羊脂青玉釉、专属 SVG 篆符、3D 透视、键盘/拖动切换）；② `GlobalTopBar.vue` 全局悬浮磨砂顶栏（玄黄品牌 + 笔记/任务/内容资产导航 + 即时搜索联想[按笔记/资产/任务/标签分组] + 音频 + 用户下拉；移动端<768 折叠为 品牌+搜索icon+头像）；③ 重写 `WorkbenchView`（浅色宣纸留白、玉简为主角、卡片玉简化、移除深色星点底）；④ 废弃 `/home`，新增 catch-all 兜底 → `/workbench`；⑤ 前端追加 `--lj-*` 冷峻东方 token；SW 升 `xuanhuang-v10`。本地+生产**浏览器实测 10 项全 PASS**（含 /home 重定向） |
| 2026-09-03 | 本轮 | **视觉质感升级（"玄素琉璃"深色材质体系，User 颜值反馈）**：① 玉简轮播整体**上移**（容器 300→340px、`track top 62%→27%`），底部圆点不再被玉简压住/裁切；② 桌宠配置面板**不再被顶栏遮挡**（`.whale-stage z-index 1200→10001` 高过顶栏 9999），面板加 `max-height+内部滚动` 兼容矮屏；③ 全站引入 `--ls-*` 玄素琉璃深色 token：墨青夜色双层渐变 + 纸纹噪点背景、玻璃卡片（渐变底+上缘高光+柔和阴影）、克制低饱和点缀（黛青/赭石/松石）；`IslandInnerBase` 背景/header 玉化，5 岛屿内页卡片全部接入玻璃材质，补 `--island-*` 旧色映射防 SVG 落黑；桌宠面板/hint 同步玉化；SW 升 `xuanhuang-v11`。本地浏览器实测玉简上移+岛屿质感+SVG 正常色 PASS |
| 2026-09-03 | 本轮 | **背景音乐 + 视频去水印 + 三库 CRUD（大型迭代，见方案 `BGM_VIDEO_PARSE_PLAN_20260903.md`）**：① **背景音乐与音乐库关联**——`Music` 增 `artist/is_default` 列（Alembic 迁移），新增用户级 `GET/PUT /api/settings/bgm_choice`；`player.js` 单一音频中枢（背景 BGM↔音乐岛点播**互斥**，点播结束自动恢复背景）、`NowPlayingBar` 全局底部播放条（曲名/暂停/进度可拖/音量/静音/关闭，播放时才出现，z-index 低于桌宠）、音量 `localStorage` 持久化；系统默认古筝曲（玄黄古筝·默认背景，只读不可删改）由后端在音乐库列表**首条注入**（id=`default`）。② **视频去水印工具**——独立解析服务 `parse-service`（parse-video-py，8070 端口，`asyncio.Lock` 串行）；后端 `POST /api/video_parse` 转发路由（按用户 3s 限流+串行）；工具岛内页嵌入去水印面板（链接输入→解析→`<video>` 预览→视频/音频/封面下载→版权合规提示）。③ **三库 CRUD 完善**——音乐/工具/视频/小说**管理页+内页**均支持新增/编辑/删除（音乐含作者字段，系统默认曲只读）；四岛管理页新增「沉浸浏览」直达按钮、工具岛新增「🎬 去水印工具」入口；视频内页支持内联播放+`⋯`编辑/删除菜单；修工具添加 bug（`toolStore.add`→`upload`）。SW 升 `xuanhuang-v13`。生产浏览器实测 **10 项全 PASS**（登录/桌宠、默认古筝只读、编辑作者、沉浸浏览+底部播放条、去水印面板、视频/小说内页菜单+播放） |
| 2026-09-04 | 本轮 | **内容板块去「岛」重构 + 工具独立页 + 视频解析增强（见方案 `NAV_REBRAND_PLAN_20260904.md`）**：① 五模块全去「岛」，路由 `/island/*` → `/music /novel /video /tool /log`（旧路由 302 重定向不失效，SW 升 `xuanhuang-v14`）；② 每模块浏览+管理**合并一页**（卡片墙 + 顶部「管理」切同页表格，表格**全字段**展示：音乐标题/作者/分类/标签/大小/时长/上传时间、小说+链接、视频+COS链接、工具+url，增删改查齐全、音乐系统默认曲只读）；③ **工具独立页**——外部工具「使用」→ `/tool/:id`（先「加载工具」再 iframe 内嵌、「新标签打开」兜底）；内置「视频去水印」置顶第一条 → `/tool/watermark` 独立页；④ **视频解析增强**：解析结果内联预览播放 +「下载音频」平台有源直下、无源走后端 `POST /api/video_parse/audio`（下载无水印视频→`ffmpeg` 抽音轨→`FileResponse` 返回 mp3，临时目录用后即清）；⑤ **生产修复**：`BackgroundTask` 需从 `starlette.background` 导入（`fastapi.responses` 无该名→后端首次部署崩溃回滚后修复）；ffmpeg 用 **dnf/EPEL** 装（OpenCloudOS 无 apt-get）。生产浏览器实测 **9 项全 PASS**（直达各新路由、玉简跳 `/music`、工具独立页 iframe、watermark 页、音乐管理表格切换、`/island/music`→`/music` 重定向、全页无「岛」字残留） |
| 2026-09-04 | 本轮 | **管理页交互修复 + 桌宠行为优化 + 搜索按钮化（见方案 `MGMT_UX_FIX_20260904.md`，User 管理页按键互斥反馈 + 桌宠要求）**：① **管理页按钮全面修复**——`main.js` 配 Element Plus **中文 locale**（`zhCn`，消除删除确认英文 OK/Cancel）；`.whale-stage` z-index **10001→1800**（低于 Element 弹层 2000 级），根治桌宠盖住/拦截「上传拉不起本地文件、编辑点不动、删除弹全屏英文」；四模块删除确认改**管理页内 `el-dialog` 中文「删除确认」**（不再弹到 body 顶层）。② **桌宠行为优化**——`stopWalk()`/松手**停在原位不再归位右下角**；所有横移（自动跑步/散步/拖拽）`clampX/clampY` **左右边界限界**、`tick()` 到边界翻转 `dir` + CSS `scaleX(-1)` **正脸镜像调头**（非倒退，素材面朝左，向右镜像面右）。③ **搜索按钮化**——四模块管理搜索框新增**「查询」按钮**，**仅按钮触发**（移除回车/`watch(keyword)` 自动请求），"清空筛选"仅清 UI 需再点查询恢复全量；后端 `q=LIKE contains` 模糊查询（工具/音乐/小说/视频）。**本地浏览器实测 10 项全 PASS**（四模块中文删除/上传/编辑/查询按钮、桌宠停在原地、左右缘未穿屏） |
| 2026-09-04 | `b1624f6` | **修复新上传音乐无法播放**（User 反馈上传并设背景后点播放没声音）：根因 `save_upload_file` 存 `/music/xxx.mp3`（少 `uploads/` 前缀），老数据存 `/uploads/music/xxx`，后端 `_stream_file` 依同路径解析（Linux 下 `/music/...` 被 `os.path.isabs` 当绝对路径）→ `/api/music/{id}/stream` 404。修复：去掉 `isabs` 分流，统一 `lstrip('/')` 后缺 `uploads/` 则补齐，全部落到 `backend/uploads/`；default 古筝改传相对短路径。线上验证牵丝戏(id9)/default 均 `200 audio/mpeg`，端到端浏览器实测「牵丝戏笛子版」播放中（/api/music/9/stream=200 Media、播放条显示曲名、进度推进、时长 00:56）。 |
| 2026-09-04 | `4e754f7` | **鲸鱼轻点穿透、按住才可拖（SW 升 `xuanhuang-v20`）**：User 选"长按才可拖"方案解决鲸鱼挡内容点击。改造 `WhaleCompanion.onPointerUp`——**未拖动（轻点鲸鱼）→ `passThroughClick` 临时关闭 `.whale-frame` 命中后 `elementFromPoint` 找到下层最近 `button/a/input/role=button` 并 `.click()` 透传**；下层无可点才退回原单击开/关设置面板；按住拖动及边界镜像/停原位照常。**线上验证**：真实点击落在鲸鱼上（下方为音乐行）后弹出该行 `.tb-audio-panel`（=透传命中下层音乐行，鲸鱼自身只会开 `.whale-panel`），证明穿透生效；按住拖动 rect 随鼠移动。 |
| 2026-09-04 | 本轮 | **播放条收敛 + 去点击音效（SW 升 `xuanhuang-v21`，User 交互反馈）**：① **背景音乐不显示播放条**——`stores/player.js` 底部播放条显示由固定 flag 改为 `computed = (mode==='playlist' && curItem)`，仅手动点播时展示，背景 BGM（`mode==='bgm'`）无论播放/暂停都不出现，也覆盖「点播结束/取消后恢复背景」场景；② **去除岛屿卡片点击/悬停音效**——移除 `JadeCarousel` 鼠标移入移出绑定的古琴/翻书/齿轮等 hover 音效（`useIslandSound.js` 整套删除）；随机氛围音效（`useRandomEvents`，30 分钟冷却、流星/仙鹤等事件触发）保留。生产浏览器实测 **6 项全 PASS**（悬停卡片无 `/sounds/*` 请求且无报错、背景 BGM 无 `.npbar`、点播出现 `.npbar`、关闭后 `.npbar` 消失）。后续按 User 确认修正：点播结束或✕关闭后**自动恢复默认背景音乐**（`player.js` 恢复 `ended`→`playBgm`/`stopAndHide`→`playBgm`）。 |
| 2026-09-04 | 本轮 | **四模块批量删除 + 点播后恢复背景 BGM（SW 升 `xuanhuang-v22`）**：① **管理页批量删除**——音乐/小说/视频/工具四个管理页表格均加复选框勾选列（音乐系统默认曲 `is_default` 不可勾选 `selectable`），勾选多行出现「批量删除(N)」按钮 → 管理页内**中文二次确认** `el-dialog` → 按行 `store.remove(id)` 逐个删除后 `clearSelection + fetchData` 刷新；所选含当前背景曲时先 `player.setBackground(null,false)` 断开。② **点播结束后恢复默认背景音乐**——`player.js` `ended`/`stopAndHide` 触发点播关闭后自动 `playBgm()`（loop 背景恢复，User 确认预期），登录仍自动播默认。生产浏览器实测 **PASS**（音乐/工具模块批量删除端到端：复选框→批量按钮→中文确认→删后刷新；小说/视频列表复选框列确认；背景 BGM 无 `.npbar`、点播出现、关闭后 `.npbar` 消失且 BGM 继续）。 |
| 2026-09-04 | 本轮 | **修复现网双背景音乐 + PDF 纯前端工具 + 两个桌面工具集成（SW `xuanhuang-v23`，User 反馈"有两个背景音乐在播"）**：① **双背景音乐修复**——`player.js` 新增 `switchSource(url,loop)`：切换音源前 `pause + removeAttribute('src') + load()` 彻底释放旧连接，确保任意时刻仅**一条**音轨流存活（此前切换背景时旧 fetch 连接残留，导致 default 与用户选曲两条 `/api/music/{id}/stream` 重叠）。生产浏览器 JS 取证 **PASS**：`performance.getEntriesByType('resource')` 仅`/api/music/default/stream` 单流、无音频元素并发播放。② **PDF 多功能纯前端工具**——新增 `PdfToolView`（`/tool/pdf`，路由+工具列表卡片，JSZip/pdf-lib/pdfjs-dist CDN **按需加载**）：TabA 图片转 PDF（JPG/PNG/BMP/WEBP，A4/原图自适应、方向、边距）；TabB PDF 转图片（150/300 DPI，单页直下、多页 JSZip 打包）；TabC 合并与拆分（拖拽排序合并、`1-3,5` 页码范围拆 PDF/抽文本）；**格式/0字节/超10MB 拦截、加密 PDF PasswordException 提示、4000px 大图弹窗压缩确认、处理中禁传、失败不中断、下载后 `revokeObjectURL` 清内存**。③ **两个桌面工具集成**——`练字(lianzi.html)`、`中英文翻译(translate.html)` 拷入 `frontend/public/tools/`（随 dist 上传，现网 `/tools/*.html` 200），并在现网 DB `tools` 表登记（id 9/10，`uploader_id=1`）经 `/tool/:id` iframe 内嵌展示。生产浏览器实测 **全 PASS**（登录、工具列表含 PDF/练字/翻译三卡、`/tool/pdf` 渲染 Tabs+徽章+按钮、练字/翻译 iframe 加载、双 BGM 单流）。 |
| 2026-09-04 | 本轮 | **顶栏切换背景音乐仍双音轨 → 深度修复（SW `xuanhuang-v24`，User 实测反馈）**：网络层实测复现——从 `牵丝戏(id9)` 切默认瞬间，`/api/music/9/stream`（旧）+ `/api/music/default/stream`（新）**两条 Media 流同时在传输**。根因：`setBackground` 先 `await fetchMusicLibrary/updateBgmChoice`（期间旧歌照播），之后才 `playBgm` 换源；而 `switchSource` 对同一 `<audio>` 换 `src` 时旧 206 媒体连接中止不彻底，造成短暂但可闻的双音轨。修复：① 新增 `hardStop()`（`pause + src='' + removeAttribute('src') + load()` 幂等硬停，比单 `removeAttribute` 更强力）；② `setBackground` 顶部先 `hardStop()` 立即停旧歌（早于 await），并以 `playSeq` 单调序号保证仅最后一次触发生效、丢弃过期回调；③ `playBgm` 借 `playSeq` 弃过期 then/catch；④ 手动 resume 收敛为**单一稳定监听器** `armResume()`（先删旧再加，杜绝多次 catch 累积多个 `pointerdown` 监听引发叠播）；⑤ `playItem`/`stopAndHide` 也改走 `hardStop()`。生产全新无缓存会话复测 **PASS**：换曲后旧流 `completed=true` 先结束、新流才开始，两流时间窗口无重叠（gap≈26s），不再双音轨。 |
| 2026-09-04 | 本轮 | **工具/管理页页脚由"钉底"改"跟随内容"（SW `xuanhuang-v29`，User 反馈"工具模块好几页底部都悬浮"）**：短内容页（去水印/PDF/像素压缩/工具详情等）页脚原被 flex 钉在 100vh 底部，内容少时页脚与内容间出现大片空隙显得悬浮半空。改为把 `.inner-footer` 移入 `.inner-main` 内部、随槽内容**流动**（`.inner-main` 改 `display:flex;flex-direction:column`，页脚 `margin-top:16px` 紧贴内容末端，`padding-bottom` 还原为朴素 24px）。工具页 DOM 取证：页脚与内容末端间距 16px（PASS）；音乐管理页 47px 为管理面板内边距+页脚 margin，仍紧贴面板底边属正常。**注：首轮回归"FAIL"系 Service Worker 缓存读到旧 v28 包，SW 注销旁路后确认 v29 生效**。 |
| 2026-09-04 | 本轮 | **修复工作台缩放黑边 + 页脚悬浮（SW `xuanhuang-v28`，User 实测反馈）**：① 工作台 `.workbench-page` 由 `max-width:1200px` 居中窄列改为**全宽浅底**（内容块 `.wb-hero/.wb-body` 及新增的浅色页脚统一 `max-width:1248px` 居中），铺满后不再在两/单侧露出 `#app` 深色产生"黑边"；页面内新增专属浅色 `<SiteFooter>`。② 岛屿/管理页页脚悬浮——先去除 `.inner-content` 的 `padding-bottom:88px` 让页脚顶到真实底部（后被 v29"跟随内容"方案取代）。③ `App.vue` 全局页脚改为按路由抑制（`showGlobalFooter`：工作台与 `/music|/novel|/video|/log|/tool*` 页各自渲染页脚，不再全局重复/悬空）。生产浏览器 DOM 取证（v28）PASS，后经 v29 进一步消除短内容页的悬浮空隙。 |
| 2026-09-04 | 本轮 | **工具统一管理 + 像素压缩纯前端工具 + 全站网安页脚 + 四管理页分页 + 桌面缩放收敛（SW `xuanhuang-v27`，见方案 `WORKBENCH_TOOLS_20260904.md`）**：① **工具统一管理**——`Tool` 模型增 `kind`(builtin/external)/`is_enabled`(上下架)/`sort_order`(排序)，接口支持列表/增/改/删；内置工具（视频去水印/PDF 工具/像素压缩）DB 登记且**置顶**（`sort_order=0,1,2`，外部工具 `100000+id` 后置）、**内置禁删**（后端校验 `kind==='builtin'` 拒绝删除，前端按钮置灰）、支持↑↓排序与上/下架；`ToolView` 从 DB 渲染。② **像素压缩工具（`/tool/compress`）**——100% 纯前端（browser-image-compression + Canvas，零后端请求），三模式：智能压缩（分辨/质量动态、防负优化「原图更优则免压」）、自定义（按目标大小/按质量滑杆）、仅缩放尺寸（按最长边/比例）；支持 JPG/PNG/WEBP（GIF 转静态首帧）、多文件≤10MB、串行队列+大文件进度条、成功即「下载」/「全部 ZIP 打包」、`revokeObjectURL` 清内存。③ **全站网安页脚**——`SiteFooter` 组件（公安盾牌+皖公网安备34010402704746号 → beian.mps.gov.cn、皖ICP备2026006516号 → beian.miit.gov.cn，均为可跳转链接），`App.vue`(工作台浅色)+`IslandInnerBase`(岛屿深色)双主题接入，全站底部一致呈现。④ **四管理页客户端分页**——工具/音乐/小说/视频管理表格新增 `el-pagination`（默认 10 条，可切 10/20/50，总条数+页码+每页，基于 `computed` 切片，切页重置到第 1 页）。⑤ **桌面缩放收敛**——`main.css` 增管理页通用三档断点（1250/1100/820px：收敛 `.manage-pane` 留白、搜索框压缩、分页居中、窄视口表格内部横向滚动），覆盖 80%~150% 桌面缩放不破版。生产浏览器实证 **PASS**（工作台底部网安页脚含双备案可跳转、工具管理表格含三内置工具且删除禁用、管理页分页控件渲染、首页 200、SW v27）。 |
| 2026-09-04 | 本轮 | **桌宠本体点击穿透 + 右上角"抓手"拖拽（SW `xuanhuang-v30`，User 反馈"点不进去了，点击入口没反应"）**：根因（浏览器取证）——`.whale-frame` 命中区为整 sprite 盒（`vidbox` 常 234×287，`scale(0.75)` 后仍约 175×215），且 `pointer-events:auto`，鲸鱼被拖到玉简/按钮上方便整片拦截点击；此前 `passThroughClick` 运行时 `elementFromPoint` 透传方案不可靠（实测未触发路由跳转）。修复：① `.whale-frame` `pointer-events:auto → none`，鲸鱼本体（含透明留白）**完全点击穿透**，下层玉简/快捷动作/管理按钮永久可点；② 新增 `.whale-handle` 右上角小"抓手"（24×24，`@pointerdown`）为**唯一可交互命中区**——按住拖动移动桌宠（拖拽/边界镜像/停原位逻辑照旧）、单击打开设置面板（原单击/双击面板与散步入口由抓手接管）；③ 删除不可靠的 `passThroughClick` 与 `lastTap` 逻辑。生产浏览器**清 SW 后实测 PASS**：`.whale-frame` computed `pointer-events=none`、`.whale-handle` 存在且 `cursor:grab/pointer-events:auto`、「快速记录」入口成功跳转 `/notes/10`、桌宠仍可见但不拦截交互。**回归经验：此类「修复未见效」多为 Service Worker 旧包，须先注销 SW+清 Cache 再 reload 复测**。 |
| 2026-09-04 | 本轮 | **工作台模块精简：移除「内容资产」+「任务」界面入口，日志升级为操作日志管理页（SW `xuanhuang-v31`，User 遗留「除音视频/文件/工具外的空间需增加管理页」）**：① **界面移除**——内容资产(`/assets`)与任务(`/tasks`)仅从导航移除但**保留 DB 数据**：顶栏导航只剩「笔记」、搜索联想去掉资产/任务分组、工作台删「内容资产/任务」快捷卡片与「今日任务/逾期任务」板块、分类入口去掉网页/图片/PDF/任务、路由删 `/tasks`/`/assets`（直接访问被兜底重定向 `/workbench`）。② **日志→操作日志管理页**（沿用四库浏览+管理合并一页）：后端 `GET /api/logs` 增时间范围(`start/end`)/动作(`action`)/关键词(`q`)筛选，新增 `DELETE /api/logs`（批量删）与 `DELETE /api/logs/clear`（清空，可限时间范围，非超管仅限本人日志）；前端 `LogView` 用 `IslandInnerBase` 重构——浏览=时间线，管理=表格（时间/用户/动作/目标类型/详情/IP + 日期范围+动作下拉+搜索+查询/清空筛选、分页 10/20/50、勾选批量删除、清空日志，均页内中文确认；日志只读不逐条编辑）。生产浏览器**清 SW 后实测 14 项全 PASS**：导航仅剩笔记、工作台无任务/资产入口、`/tasks`/`/assets` 重定向 `/workbench`、时间线渲染、管理表格列头齐全、筛选/搜索/分页/批量删除/清空确认均生效。部署时 `deploy_backend.py` 硬编码白名单补上 `routers/log.py`（否则新接口不上线）。 |
| 2026-09-04 | 本轮 | **工作台极简收敛（SW `xuanhuang-v32/v33`，User「这几个入口都去除，想高端点」「把这三个都干掉」）**：① v32 玉简轮播删「内容资产」「任务镜台」两张卡（只剩 宫商流转/卷帙浩繁/光影交织/翰墨丹青/机关百变/笔记云台 6 张，`JadeCarousel` 去对应篆符）+ 去除工作台「分类入口」整块（笔记/音乐/小说/视频/工具）；② v33 移除工作台数据区三张卡「最近编辑/待整理草稿/标签」（`wb-grid` 全删，`WorkbenchView` 脚本树清空只剩玉简+快捷动作，删 `tagList/summary/load/formatDate` 及对应 CSS）。工作台现仅含 玉简轮播 + 快速记录/AI助手 + 网安页脚。生产浏览器清 SW 后实测全 PASS（v33：三卡文本 0 残留，「标签」仅剩搜索 placeholder 属正常，快捷动作+页脚正常）。 |
| 2026-09-04 | — | **Git 历史凭证泄漏处置（安全项 Decision+Exec，User「帮我决策那两个安全项」「执行吧」）**：排查发现生产服务器口令硬编码于历史多文件（`memory/MEMORY.md`、`memory/server-access.md`、`docs/VERSION.md`、`docs/archive/VERSION.md`、`docs/archive/设计文档/VERSION.md`、`check_server.py`、`scripts/restart_pm2.py`、`scripts/upload_server.py`）及 v1.5.0 一条提交信息。决策：**保留 GitHub PAT**（经 GCM 管理、无泄漏痕迹，revoke 会破坏推送链路）；**清理远程历史**执行。处置：`git filter-branch --index-filter` 删 `memory/` 与 `设计文档/VERSION.md` 路径 + `--msg-filter` 抹提交信息口令 + `git-filter-repo --replace-text` 抹全部 blob 口令；`--tag-name-filter cat` 重写 **master + 24 个远端 tag**（远端已推 tag，一并重写，否则经 tag 仍可达旧历史）。`git push --force` 覆写远端 master 与全部 tag。**全量校验**：口令在 blob/message、`memory/`、VERSION 路径均 0；远端 24 tag 解引用与本地对齐；工作树冗余 `memory/` 副本与临时规则文件已清理。**遗留：须用户 SSH 轮换生产服务器口令**（口令曾公开，改 git 止不住已泄露值）。 |
| 2026-09-06 | — | **生产服务器 root 口令轮换闭环（User「执行吧」，补齐上一条安全项遗留）**：本机无 `sshpass/plink` 且未配密钥，选用 **Python paramiko**（本机 5.0.0）免交互连接腾讯云 `203.195.208.25`（root/22）。读取 `.secrets/local.env` 旧口令 → `secrets` 生成 32 位强随机关口令 → `echo 'root:new' | chpasswd`（RHEL 系）改 root 口令 → 用新口令重连验证连通 → 新口令写回 `.secrets/local.env`（git 之外的本地协作层，步进以冒号后省略显示）；临时脚本 `rotate_ssh_pw.py` 执行后即删（不残留含口令的磁盘文件）。**遗留建议：配置 SSH 公钥/禁用密码登录以常态化免密运维**。
| 2026-09-06 | 待提交 | **全站「向晚·雨青」苹果毛玻璃质感升级（见方案 `GLASSMORPH_UPGRADE_20260906.md`，User「样式先优化，做成苹果毛玻璃那种质感」）**：以登录页玻璃为基准，全站统一夜色玻璃工艺——① `variables.css` 追加「向晚·雨青」配色（墨青夜色 `#0b0f14/#10161d/#161e26` 为骨、雨青 `#7fa8a3/#a8d3ce` 为光、收敛鎏金 `#c7a96b` 点睛），定义苹果级玻璃系统（`--glass-blur: blur(24px) saturate(185%)`、`--glass-border`、内高光 `--glass-highlight`、柔和多层 `--glass-shadow`），圆角放大（sm8/base14/lg20/xl26）；工作台原浅色 token（`--lj-*`）随动转深色玻璃，岛屿 `--ls-*` 对齐雨青；② `main.css` `.ls-card` 升级为苹果玻璃 + 新增通用 `.glass-card`，加 `prefers-reduced-motion` 克制动效；③ `xiuxian-theme.css` 覆盖 Element Plus 主色 `#7fa8a3`、夜色背景、大圆角、柔和多层阴影；④ 应用面：`WorkbenchView`（夜色光斑底+快捷动作玻璃化+深色页脚）、`GlobalTopBar`（导航/搜索/图标按钮夜色玻璃）、`LoginView`（基准玻璃参数深化）、`JadeCarousel` 分页指示器、`NoteSelect` 下拉夜色化、`App.vue`/`WorkbenchView` 页脚切 `site-footer variant="dark"`。SW 升 `xuanhuang-v34`。

---

## 二、关键交付明细（结论 + 验收）

### 1. 基础设施与部署（8/30 ~ 9/1）
- 生产：腾讯云 CVM / OpenCloudOS 9.4，Nginx + PM2 + SQLite，Release 目录 `/var/www/yexingchen/releases/<tag>`。
- 健康检查用 `/health`（**不是** `/api/health`）。
- 部署脚本：`scripts/upload_server.py`（自带 PM2 重启）、`scripts/ai_deploy.py`（上传 dist + 后端单文件 + 重启）。
- 运维坑速查（ZIP 反斜杠 / pm2 进程名 `/nginx reload` `/assets 403` 等）：见 `HISTORY.md` 表。

### 2. AI Provider 用户级配置（09-02，`dbd24fa`）
- 后端：`UserAiProvider` 模型 + `user_ai_providers` 表（Alembic `c1a2b3d4e5f6`）+ 5 个 CRUD + test 连接端点（`urllib.request`，`max_tokens=1` 控费）。
- 前端：`AssistantView` header 加 Provider 下拉 + 「配置 AI」弹窗；`provider_id` 运行时热切换。
- 安全：`api_key` 按用户授权**明文**存储，返回时前后 4 位脱敏，编辑不回填，前端永远不展示完整 Key。

### 3. 修仙风全站统一（09-02，`aac70be`/`9db8760`）
- 方向：**登录页为唯一视觉锚点**；「一殿一室」——登录页=仙府大殿·仪式（华丽），工作台/首页/岛屿=内室修行·日常（光效克制、光随交互亮）。
- 配色照抄登录页：深青夜色底 `#0a1218→#1a2530` + 灵气青绿主强调 `#3DB8B0` + 流金标题点缀 `#C9A96E→#F0E6C8`。
- 落点：`variables.css` 修仙 token 覆盖块（修 `--color-gold/jade` 悬空引用）+ 新增 `xiuxian-theme.css`（Element Plus 夜色青绿）+ 工作台 7 子视图与 5 座岛屿琉璃化 + 文案修仙化首轮（回收站空态等）。
- 唯一有效设计规范：`docs/DESIGN_INKWASH.md`（绿色文件在**仓库内**，非 `docs/ai`）；`DESIGN_XUANMO.md` 已废弃勿参考。

### 4. 笔记编辑器修复与颜色面板（09-02）
- **6 项修复**（`0e4c0e4`）：标题/引用/代码块点击真实生效（补 `.ne-content` 内 `blockquote/pre/h2` 样式，此前零视觉反馈）、编辑页取消返回、删除确认全中文、删除后可回工作台、404 兜底、老模块返回入口（`HomeView` dropdown 补 `case 'workbench'`）。
- **颜色面板**（`c0eea48`）：工具栏「A 颜」浮层 = 24 预设色板 + 原生取色器 + EyeDropper 吸色 + HEX(`#RRGGBB`/`#RGB`) + RGB(0-255)。
- **颜色持久化关键修复**：`execCommand(foreColor)` 产 `<font color>`，旧 `sanitizeNoteHtml` 白名单不含 `font` 且剥 `style/color` → 选色保存刷新即丢。现放行 `font`/`font[color]`，`style` 仅放行纯色 `color`/`background-color`（拒 `url()/expression` 注入），后端 `sanitize_text` 只做敏感词替换。
- **吸色定稿**（`6cc5cbd`/`0cbbd7b`）：自绘针管光标 + 全页透明遮罩，页内取色，无弹窗无马赛克；左键应用并关闭、Esc/右键取消。**已否决**：原生 EyeDropper（马赛克取景窗）、`getDisplayMedia`（弹系统屏幕共享授权页）。

### 5. AI 回复与 API 层（09-02）
- **AI 回复修复**（`6dbaffc`）：根因三层——后端直接上屏模型原始输出 + MiniMax 内嵌 JSON 导致 `json.loads` 失败 + 前端二次拼接。修复：后端 `_remove_embedded_json`/`_polish_readable` + Prompt 强约束，前端只展示 `res.data.text`。
- **重大部署教训**：线上 `run.py` 误开 `uvicorn.reload=True` → SFTP 改代码后 PM2 restart 也仍持旧模块（「改了不生效」）。**生产必须关 reload**，改后端不生效先核对 reload/pyc 缓存/进程是否真重启。

### 6. AI 对话页内联化（09-03，`bc8faba`/`6ee4888`）
- 发送直接调 `ai.invoke`，**去除预览/结果两个居中弹窗**；回车发送（Shift+回车换行）。
- AI 结果在**聊天气泡内可折叠面板**内联呈现：选目标笔记/新建草稿/应用到笔记/创建任务全部内联，应用后显「✓ 已应用」。
- 部署时 SW 升 `xuanhuang-v7`，确保客户端拉取新 `AssistantView` 懒加载 chunk（防旧 SW 引用已替换分块）。

### 7. 鲸鱼娘桌宠接入（09-03，已上线）
- **来源与高清坑**：dsh 桌宠 `luweiyabo/dsh-whale-pet`（MIT）；GitHub 顶层 `docs/images/actions/*.gif` 是 **240×135 低清展示版**，放大会糊；**真正高清是 `assets/thumb/*` 的 640×360 透明 WebM**，需用 WebM 而非 GIF。
- **渲染方案**：`<video>` 透明播放 + 按每动作 `vidbox`（角色在 640×360 帧内 bbox）裁剪居中，1:1 原生像素最清晰，规避 GIF/APNG 放大模糊与 APNG 解码兼容坑。
- **接入点**：`frontend/public/whale-pet/videos/`（全量 **95 个** WebM）+ `src/pet/vidbox.js`（bbox 配置，类目 idle/moves/turn/drag/clicks/daily/festivals/food/fun/games/magic/memes/music/seasonal/special/work）+ `src/components/effects/WhaleCompanion.vue` + `App.vue` 内 `<WhaleCompanion v-if="auth.isLoggedIn">`。点击/随机从全部「表达类」动作（排除待机/移动/拖拽）取，自动池仍为精选静音动作。
- **交互**：自动换动作（待机为主+慢游/跑步/扭头）、单击换动作、拖拽、双击散步（页面底部横移）；全视口宽度均显示（曾加 `prefers-reduced-motion` 与 `max-width:767px` 隐藏规则，都会把桌宠在窄视口/演示环境误隐藏，已一并移除）。
- **踩坑**：GitHub raw 对批量小文件（gif/WebM）**限流失联**，改用 jsDelivr CDN 镜像 `cdn.jsdelivr.net/gh/<owner>/<repo>@main/<path>` 批量下载稳定。
- **线上不显示的根因（已修）**：`vidbox.js` 的 key 末尾带了 `.webm`（`"idle/breathing.webm"`），而组件 `setAction` 拼的 key 是**无后缀** `"idle/breathing"` → `VIDBOX[key]` 为 `undefined` → 走 `if(!box) return` 提前返回，桌宠只渲染空 stage、**不设 video.src、不报错**（`display:block` 也看不出）。已把 vidbox 键去后缀统一；`prefers-reduced-motion`/`max-width:767px` 的隐藏规则已在排查中移除（窄视口/演示环境会被误隐藏，桌宠应在所有页面存在）。排障法：sourcemap 定位到 runtime-core 无果后，改直接读产物/本地端到端复现，最终比对 vidbox 键格式定位。
- **SW/T 层级**：`sw.js` 纳入 `/whale-pet/` 缓存且升 `xuanhuang-v8`；组件 `z-index:1200`，低于 `el-dialog`、`pointer-events` 仅自身。
- **线上体验优化（用户实测反馈驱动）**：① 单击动作曾"一闪而过像消失" → 点击表演回调待机延迟从 900ms 拉长到 **3000ms**；② 整体过大 → `.whale-frame` `transform: scale(0.75)`（origin bottom-right）缩至 75%；③ 跑步类动作固定范围无位移 → 新增 `briefRun()` 从屏右进入向左横向穿越至终点后再回待机；④ 动作看着少 → 自动池 `AUTO_POOL` 扩至 **24 个**（idle/turn/moves/daily/music/fun/games/food/seasonal 混排），随机类采用去后缀 `PLAY_KEYS` 全表达类。
- **第二轮体验优化（09-03 二次，用户实测反馈驱动）**：
  - **① 换动作间隔 5~7s**：`scheduleAuto` 从 `3200+random*2600`（均值≈4.5s）改为 `5000+random*2000`，动作停留放长。
  - **② 左键弹出配置面板**：单击桌宠弹悬浮面板（非居中弹窗），提供「固定编排(auto)/随机动作(random)」单选 + 散步开关，模式存 `localStorage`(`whale-pet-mode`) 刷新保留；交互：**单击=设置面板、双击=开关散步**（提示文案同步改）。
  - **③ 换动作平滑过渡**：新增 `smoothSwitch()`——切源前 opacity 淡出到 0 → `setTimeout 240ms` 换 src/load/play → `requestAnimationFrame` 淡入回 1，消除硬切"闪烁"；`.whale-video` 加 `transition: opacity .24s`。拖拽/散步直接设不转淡。
  - **④ 跑步位移与"倒着跑"修复**：浏览器截帧实测 `running_trip`/`target_point_run`/`crab_walk` 三个跑步素材**本体均面朝左** → 旧逻辑向左移动时 `flipped=true` 镜像成面右再左移=倒着跑。修正：**向左跑不镜像(flipped=false)、向右跑才镜像(flipped=true)**，统一 `onPointerMove`/`tick`/跑步穿越三处 flip 判定；自动跑步从右下角常驻位出发向左穿越全屏至 `endX=40` 停（不再从屏外冒入），三个跑步动作都经 `RUN_KEYS` 触发横穿。
- **生产部署√（09-03，二次）**：`scripts/deploy_front.py` 部署 163 个 dist 文件，SW 维持 `xuanhuang-v8`，`/health`/`/home`/`/whale work`/`/coding` 均 200，webm `content-type: video/webm` 正确；备份 `releases/dist-pre-whalepet-20260903-165118`。
- **验收清单**：登录后 /workbench、笔记等全站右下角均有桌宠；未登录/登出不出现；动作自动轮播 + 点击/拖拽/双击交互正常；控制台无 404/解码错误、不遮挡关键按钮；老访客刷新（SW 清缓存后）可见。

### 8. 背景音乐 + 视频去水印 + 三库 CRUD（09-03，本轮，SW `xuanhuang-v13`）
- **背景音乐与音乐库关联**：
  - 后端：`Music` 增 `artist VARCHAR(255)`/`is_default` 列（仓库内 `alembic/versions/d4e5f6a7b8c9_music_add_artist.py`；生产用 `ALTER TABLE` 补列）；`settings.py` 新增 `GET/PUT /api/settings/bgm_choice`（按用户存 `GlobalSetting key='bgm_user_{uid}'`，值 `{"bgm_music_id": id|'default'}`，**引用曲目 id 不复制文件**）；`music.py` 列表接口**首条注入**系统默认古筝曲（id=`'default'`，title「玄黄古筝·默认背景」，只读保护，`/api/music/default/stream` → `uploads/bgm/bamboo_flute.mp3`）。登录即可改（`get_current_user` 非 super_admin）。
  - 前端：新增 `stores/player.js` 单一 `<audio>` 中枢——`mode:'bgm'|'playlist'` 区分背景/点播实现**互斥**（点播播毕自动 `resumeBgm()` 恢复背景）、音量写 `localStorage('bgm_volume')`、自动播放被拦时等首次 `pointerdown` 恢复；新增 `components/NowPlayingBar.vue` 全局底部播放条（播放时才出现、右侧留白避桌宠、z-index 低于桌宠 10001）；`GlobalTopBar` 音频下拉接入 player（背景音乐选择/音量）；`MusicIslandInner` 每曲加「设定为背景(💠)」「播放(▶)」。
- **视频去水印**：
  - 独立服务 `parse-service/`（`parse_video_py.parse_video_share_url` 包装，`asyncio.Lock` 串行，port 8070，`/health` `/parse`）。生产部署：venv + `pip install fastapi/uvicorn/httpx` + `pip install git+https://github.com/wujunwei928/parse-video-py`，pm2 `parse-service`，`/health` 返回 `{"status":"ok","backend":true}`。
  - 后端：`routers/video_parse.py` `POST /api/video_parse` 转发（按用户 3s 限流 + 全程串行锁；`config.PARSE_SERVICE_URL` 默认 `http://127.0.0.1:8070`；依赖 `httpx` 已加）。
  - 前端：`ToolIslandInner` 嵌去水印面板（`api/videoParse.js` 独立封装绕过全局拦截）——链接→解析(loading)→`<video>` 预览/图集→视频/音频/封面下载（`window.open`）→版权合规提示「请在权利允许范围内使用」。`ToolIsland` 顶栏加「🎬 去水印工具」直达按钮。
- **三库（+小说）CRUD 完善**：音乐/工具/视频/小说管理页补全**新增/编辑/删除**（音乐含作者字段、系统默认曲只读「系统内置」标签无操作按钮）；四岛管理页加「沉浸浏览」直达按钮、工具岛加「去水印工具」。岛屿**内页卡片加 `⋯` 编辑/删除下拉菜单**（操作就近完成），视频内页支持**内联播放**（`/api/videos/{id}/stream` Range，本地路径 FileResponse 转发、COS 直链）；修工具添加 bug（`toolStore.add`→`upload`）。
- **验收（生产浏览器实测 10 项全 PASS）**：① 登录+桌宠+顶栏；② 音乐列表首条系统默认古筝只读；③ 音乐编辑作者；④ 沉浸浏览+点播出底部 NowPlayingBar；⑤ 工具岛「去水印工具」入口；⑥ 去水印面板 UI（含合规提示）；⑦ 视频岛「沉浸浏览」入口；⑧ 视频内页 `⋯` 菜单+内联播放；⑨ 小说岛内页 `⋯` 菜单；⑩ `/health`+默认流播 200。
- **部署**：`scripts/deploy_backend.py`（传 10 个后端文件 + venv 装 httpx + `ALTER TABLE` 补 music.artist/is_default + 清 pycache + pm2 restart）+ `scripts/deploy_frontend.py`（158 dist 文件，SW `xuanhuang-v13`）+ `scripts/deploy_parse.py`（parse-service 上线 8070）。Backup 无（本轮未动 release；如需可下次备份）。

---

### 9. 播放条收敛 + 去点击音效（09-04，本轮，SW `xuanhuang-v21`）
- **背景音乐不显示播放条（User：背景 BGM 播放时不要底部播放条，暂停/取消其他音乐也如此）**：`stores/player.js` 中原 `shows` 是 `ref(false)`，由 `audio#playing` 事件无条件置 `true`——背景与点播共用一 `<audio>`，导致背景播放也弹出播放条。改为 `const shows = computed(() => mode.value === 'playlist' && !!curItem.value)`，并删除 `playing` 监听里的 `shows.value=true` 与 `stopAndHide` 里的 `shows.value=false`（改为置 `mode='idle'` 驱动隐藏）。效果：仅手动点播（`mode==='playlist'`）显示 `.npbar`；背景 BGM（`mode==='bgm'`）、点播结束后 `resumeBgm()` 回背景、关闭停止（`mode='idle'`）均不显示。
- **去除岛屿卡片点击/悬停音效（User：点击音效怪怪的）**：`JadeCarousel.vue` 每张卡片 `mouseenter/mouseleave` 曾触发 `useIslandSound.playHoverSound()` 播古琴/翻书/镜头/墨迹/齿轮等音效——鼠标滑过即响，被用户感知为"点击音效"。移除模板 `@mouseenter/@mouseleave` 绑定、脚本内 `onMouseEnter/onMouseLeave`、`onKeydown` 的 `Escape→stopHoverSound`、`onUnmounted` 的 `stopHoverSound`，删掉 import 与解构，并**整删 `composables/useIslandSound.js`**（已无任何引用）。
- **保留**：`useRandomEvents.js` 的随机氛围音效（未触发时无请求，30 分钟冷却、流星雨/仙鹤群飞等事件触发古琴/镜头声），非点击音效。
- **SW 升 `xuanhuang-v21`**（`frontend/public/sw.js`），`scripts/deploy_frontend.py` 上传 148 个 dist 文件，首页 200。
- **验收（生产浏览器实测 6 项全 PASS）**：① 首页玉简轮播正常（无需登录，会话已存在）；② 悬停/移出多张卡片后**无任何 `/sounds/*` 请求**且控制台无报错；③ 首页点击产生手势触发背景 BGM 后 `querySelector('.npbar') === null`；④ 导航 `/music` 点播一首曲后 `.npbar` 出现且 `display:flex;visibility:visible`；⑤ 点 `.npbar` 关闭按钮 ✕ 后 `.npbar` 从 DOM 消失。

---

## 三、开放 / 遗留事项

| 项 | 状态 | 备注 |
|----|------|------|
| 岛屿内部页数据不显示（音乐/小说等 `/island/*/inner`） | ✅ 已解决 | 本轮浏览器实测内页卡片+`⋯`编辑/删除菜单+视频内联播放均正常 |
| `/api/auth/me` / 背景音乐流 `ERR_ABORTED` | ✅ 已解决 | `/api/music/default/stream` 与 `/api/settings/bg_music/stream/bamboo_flute` 实测 200 |
| AI Provider / 笔记等专项单测 | 部分 | `test_provider_crud.py`、`assistant-provider.test.js` 曾缺；颜色/AI 解析已补 |
| `api_key` 明文存储 | 已知风险 | 用户决定不加密；如需加密另加 `ENCRYPT_KEY` |
| HomeView/LoginView 大拆分（975+1204 行） | 推迟 | 用户同意先不做 |
| Git 历史中旧敏感内容清理 | 待办 | 用户说「以后做」 |
| 文案/模块命名更深层修仙化 | 可深化 | 当前以清晰为先 |
| `manifest.webmanifest` MIME 为 `application/octet-stream` | 待办 | 建议 Nginx 补 `application/manifest+json` |

---

## 四、被吸收并入本文件的旧文档

以下临时文档的历史结论已并入上表，已从 `docs/ai` 删除/归档，不再单独维护：
- 部署报告：`2026-08-30` / `2026-08-31-login-fix` / `2026-09-01-router-fix` / `2026-09-02-ai-provider` / `2026-09-02-backbutton`
- 设计审视：`2026-09-02-workbench-upgrade` / `2026-09-02-xiuxian-style-unify` / `2026-09-02-note-editor-fixes` / `2026-09-02-note-color-panel`
- `git-push-report-2026-08-31`、`codex-handoff-2026-08-31`
- `PET_INTEGRATION_20260903.md`（桌宠接入方案，已并入上文 §7，本文件删除）
- `WORKBENCH_OPTIMIZATION_PLAN.md` 及 `_ORIG`
- `coding-tasks/MASTER-mvp-implementation.md`（已删）；`archive/coding-tasks-history/*`（MASTER 系列任务单）**保留为历史档案**，不参与接续写作
- 临时截图目录（`screenshots/`、`color-panel-shots/`、`notefix-shots(/2)`、`prod-notefix-shots`、`fix2-shots`）与散落的 `*.png`

> 如个别历史细节需要找回，请查 Git reflog 或 `HISTORY.md`；归档截图已被删除，不再可复现。
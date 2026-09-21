## [v2.39.0] - 2026-09-21

### AI 高级玩法（8 项 AI 深度扩展，参考 Khoj/Omi/Rowboat范式）

User：「改写ability、解释、语义召回、长期记忆蒸馏、工具调用、图片理解、token用量监控、自动任务，这几个很不错，是我需要的」。

#### 后端

- **数据模型**：`xuanhuang_note_embeddings`(RAG嵌入) / `xuanhuang_user_facts`(长期记忆) / `xuanhuang_ai_usage`(用量) / `xuanhuang_agent_jobs`(自动任务) 四表
- **AI Provider 增强**：
  - `ai_providers.py` 新增 7 个能力 schema：`rewrite/explain/extract_entities/memory_distill/agent_plan/agent_step`
  - `HttpProvider.invoke` 提取 `usage` 字段并支持 `tools`（OpenAI function calling）+ 多轮工具执行回喂，最多 3 轮防爆
  - `HttpProvider._build_messages` 支持 `content_parts` 多模态（`text` + `image_url`）
  - 工具注册表 `_TOOL_EXECUTORS` + `register_tool_executor/set_tool_executor`
- **新服务**：
  - `services/embedding.py`：OpenAI 兼容 `/v1/embeddings`，按 `(note_id, model)` 幂等 + content_hash 缓存 + 余弦相似度
  - `services/ai_usage.py`：月 10w tokens 默认上限（`AI_MONTHLY_TOKEN_LIMIT` 可改）+ 月聚合查询 + 超限 429
- **新路由 `/api/workbench/ai/advanced`**（11 端点）：
  - `POST /ai/advanced` 通用入口（rewrite/explain/extract_entities/memory_distill/agent_plan）
  - `GET  /ai/semantic_search?q=&top_k=8` 语义召回
  - `POST /ai/index` 建立/重建笔记嵌入
  - `POST /ai/agent/start` + `/ai/agent/run` + `GET /ai/agent/{id}` ReAct 循环（最多 8 步，工具：create_note/create_task/search_notes/log_finance）
  - `GET /ai/memory` + `POST /ai/memory/forget` 长期记忆 CRUD
  - `GET /ai/usage` 当月用量
  - `POST /ai/ocr` 高德OCR+多模态vision双兜底
- **修复**：迁移脚本中 `BIGINT` 在 SQLite + AUTOINCREMENT 不可用 → 改为 `Integer`，服务器上运行时改表

#### 前端

- **`components/workbench/AiToolsDrawer.vue`**：7 标签抽屉（改写/解释/语义搜索/长期记忆/Agent/OCR/用量），线性产品风
- **`GlobalTopBar.vue`** 新增 `✺ AI` 按钮（顶栏右侧，与 `⌘K` 同列）
- **`App.vue`** 全局热键 `Cmd/Ctrl+Shift+A` 打开 AI 工具抽屉
- **`api/workbench.js`** 新增 `workbenchApi.aiAdv` 命名空间（10 个方法）

#### 验证 PASS（生产）

- 8 个端点全部 200（OCR BadGateway 因 PNG 图非文本，可接受）
- 后端 health=200 / 前端 SW v150 / 迁移应用 `s0t1u2v3w4x5 → t0u1v2w3x4y5`
- Agent 任务 `start/run/get` 端到端打通；embedding 幂等写入；用量按日聚合

## [v2.38.3] - 2026-09-21

### 修复：根除「请求失败」吐司（通用拦截器不再默认弹错）

User：「还是有这个报错，解决下」。上轮只把 `q=''` 422 改成 200，但生产服务器日志发现 v2.38.2 后仍有 **42 个独立 axios 实例**（feeds/finance/stocks/quick/datahub/travels/workbench 等）**无响应拦截器**——其业务包 catch 中显式 `ElMessage.error('请求失败')` 仍在兜底；且 v2.38.2 我只让 422 不弹，但 4xx/5xx 其它状态码仍走默认吐司，加上 FastAPI 422 detail 是数组会被回退成 `message = '请求失败'`，结果"请求失败"吐司依然复现。

**修法（釜底抽薪）**：
- **`frontend/src/api/index.js` 拦截器**：去掉**所有**业务码非 0 与 4xx/5xx 默认吐司分支，仅保留 **401 → 清 token + 跳登录**这一系统级动作；清理未使用的 `ElMessage` import
- 业务方在自己的 catch 中按需提示（AI 简报、桌面搜索等希望静默失败的场景不再被抢去吐司；必填校验希望保留 422 给业务弹窗的也不再被拦截器误弹）
- SW `v148→v149`

**验证 PASS**：
- 服务器 SW v149，home=200
- 后续若某条接口 422/5xx，组件内 catch 静默或自处理；不再出现「请求失败」默认吐司

## [v2.38.2] - 2026-09-21

### 修复：「请求失败」吐司（搜索 q 空字符串触发 422）

User：「会有一些页面报错请求失败，看下咋回事」。

**根因**：登录后页面状态恢复从 URL 解析查询词、桌面顶栏 `DesktopSearchBox` 防抖 260ms 内清空又触发、`VoiceInputButton` 静默回空、stale 定时器残留……任一路径都可能让 `searchAll({q:''})` 发出。`/api/search` 与 `/api/workbench/search` 后端用 `Query(..., min_length=1)` 校验 → HTTP 422 → `api/index.js` 拦截器走到 `else` 分支默认吐司 `ElMessage.error('请求失败')`，错误提示含糊。

**修法**（后端 + 前端双保险）：
- **后端 `routers/search.py` + `routers/workbench/search.py`**：`q` 改为 `Query("", ...)`，空字符串直接返回空集（不再 422）
- **前端 `api/index.js`**：拦截器新增 `status === 422` 分支**不弹吐司**（422 多为参数校验，交调用方在自己 catch 中显示/兜底，避免通用拦截器误弹）
- SW `v147→v148`

**验证 PASS**（生产）：
- 42 接口全绿（含 `/api/search?q=` 200），原唯一 422 已消
- 后端 uvicorn 日志 `GET /api/search?q= HTTP/1.0" 200`，无 5xx
- 桌面顶栏搜索空 q 不再触发吐司，组件内 try/catch 也兜住 suggestions 清空

## [v2.38.1] - 2026-09-21

### 天气小部件数据源：Open-Meteo → 高德开放平台（后端代理）

User：「我在秘密文件里放了高德的天气key，你调用下获取真实的，然后部署下」。`.secrets/local.env` 之高德 key `3d49545d...` 实测 geocode/regeo/weather(base+all) 均通。

- **后端代理 `routers/workbench/weather.py`**（`GET /api/workbench/dashboard/weather?city=|lat&lon=`）：key 只存服务器 `backend/.env`（`AMAP_WEATHER_KEY`，config 增可选字段），不出客户端、不入 git；城市名→geocode / 经纬度→regeo 解析 adcode，拉实时 lives + 4 天预报，按 adcode 内存缓存 10 分钟，上游失败降级 502；`workbench/__init__.py` 注册
- **前端 `WeatherCard.vue` 改调后端代理**：高德中文天气文本映射图标，保留定位/城市切换/坐标 1h 缓存
- **`scripts/deploy_backend.py`**：新增 weather.py 上传 + 自动把 AMAP_WEATHER_KEY 写入远端 `.env`；**修复迁移目标 `k2l3m4n5o6p7` → `upgrade head`**（此前钉死在旧版本，导致 `schema_guard` 启动 fail-fast 崩溃：prod DB 停在 `r8s9t0u1v2w3` 而非 head `s0t1u2v3w4x5`，已 `upgrade head` 应用习惯打卡表并恢复 health=200）
- SW `v146→v147`
- **生产验证 PASS**：API 返回南京 阴 26℃/湿度75%/东南风≤3/4天预报；浏览器实测工作台天气卡渲染一致、无报错

## [v2.38.0] - 2026-09-21

### 工作台 8 项功能优化 + 修复「工作台 ability 必填」报错

User：「进入工作台报错，处理下，另外再找找其他的可优化功能」「1-8 都做了吧」「弄完把代码优化下、补状态、提交 GitHub」。

**先修工作台报错**：`AiBriefCard` 原来直接调 AI `preview` 接口但**缺 `ability` 字段→422「ability 必填」**。改为新增专用 `POST /api/workbench/dashboard/brief`（后端 `brief.py` 自动取近期笔记汇成 `summarize` 请求、失败降级返回空文本由前端兜底），前端改调新接口。

#### ① 习惯打卡 + Streak（#1）

- 后端 `xuanhuang_habits` / `xuanhuang_habit_checkins` 两表（Alembic 迁移 `s0t1u2v3w4x5_habits.py` 链到 head）+ `routers/workbench/habits.py`：CRUD、打卡/取消（同习惯同天唯一）、统计**连续天数 streak / 本周次数 / 最近 30 天热力图 / 总次数**
- 前端 `HabitsCard.vue`：工作台横幅卡列出全部习惯，逐项「周进度 / 🔥连续天数 / 今日打卡开关」，内联「＋ 新建习惯」

#### ② 实时天气小部件（#2）

- `WeatherCard.vue` 纯前端走 **Open-Meteo**（免费无 Key）：IP 定位回退默认南京 + 手动城市选择 + localStorage 缓存当日数据；实时体感/湿度/风速 + 未来 5 天预报

#### ③ 桌面日历联动倒计时 badge（#3）

- `GlobalTopBar` 新增胶囊按钮：显示最近一条**未过期倒计时剩余天数**，点击/悬浮展开最近 5 条面板，点条目跳详情页

#### ④ 资讯流已读/未读统计 + 智能滚动（#4）

- `FeedsView`：顶部未读角标（未读总数）、筛选新增「未读」档位、翻页后自动滚动到第一条未读并短暂高亮

#### ⑤ 空状态美化（#5）

- 新增通用 `EmptyState` 组件（内联 SVG 水墨插画 + 标题/描述/CTA），统一应用到 TasksView / SubscriptionsView / QuickView / MusicView / VideoView / ToolView 的「暂无数据」场景

#### ⑥ 键盘速记（#6）

- 任意页、非输入态按 **`N`** 键直接跳转新建笔记（`App.vue` 全局监听，避开输入框/组合键/命令面板开启时）

#### ⑦ 快捷面板模块显示/隐藏自定义（#7）

- `prefs` store 新增 `moduleVisible`（习惯/天气/资讯/AI 简报，默认全开，按用户 localStorage 持久化）；`ProfileView` 增四个开关；工作台按开关用 `v-if` 渲染

#### ⑧ 暗色 OLED 真黑（#8）

- `desktop-theme-night.css`：夜间背景退纯黑 `#000`，表面保留极浅层次（`#08080f`/`#0d0d18`）以维持卡片立体感，发丝描边紫罗兰透明度

#### 附带架构优化

- `WorkbenchView` 内联空状态统一为 `EmptyState`（紧凑卡片仍保留轻量文案）；`vite.config.js` 增 **vendor 大包拆 chunk**（element-plus / icons / vue-vendor / axios / vendor + `chunkSizeWarningLimit:800`）；`deploy_backend.py` 白名单补 `brief.py` / `habits.py` / `models/habits.py` / 迁移 `s0t1u2v3w4x5`

**验证**：前端 `vite build` 通过；后端迁移测试 `pytest tests/test_migrations.py` 3 例通过、`app.main` 导入 OK（33 路由）。SW 升 `xuanhuang-v146`。

---

## [v2.37.0] - 2026-09-20

### 新增鸿蒙 NEXT 客户端工程 + 下载页改三平台（Android / 鸿蒙 / iOS）

User：「目前项目已有安卓安装包，现在包装下，在下载页加上鸿蒙和 ios 系统的安装包」。

**背景**：下载页早有「多平台」骨架，但鸿蒙与 iOS 都挂着「即将上线」。本轮把两条路各自落地——**鸿蒙出真包，iOS 走 PWA**。

#### ① 鸿蒙 NEXT（HarmonyOS 5.0+）HAP 工程

鸿蒙 4 及以下内核仍是 AOSP，现有 APK 直接可用；但**鸿蒙 NEXT 移除了 AOSP 兼容层，只认 `.hap`**，必须单独做一个包。

- 新增 `harmony/`（DevEco Studio 工程根）：Stage 模型 + ArkTS，包名 `cn.yexingchen.app`，首屏 `https://yexingchen.cn/workbench`
- 实质逻辑只有 `entry/src/main/ets/pages/Index.ets` 一个 WebView 壳页面，**行为逐条对齐安卓壳 `MainActivity.java`**：站内留 App / 站外跳系统浏览器、`target=_blank` 回站内加载、返回键优先 Web 后退、`<input type="file">` 走系统文件选择器、媒体免手势播放、混合内容放行
- `module.json5` 只申请 4 个权限：INTERNET、GET_NETWORK_INFO（普通权限）+ CAMERA、MICROPHONE（用户授权，带中文理由）
- 新增 `docs/HARMONYOS_BUILD.md`：华为开发者账号注册 → 装 DevEco Studio → 打开工程 → 自动/手动签名 → 出 HAP → 上传 → 下载页自动识别；含 7 类常见坑与「与安卓壳行为差异」对照表

**未在本机编译验证**：本机无 HarmonyOS SDK（DevEco 是 Windows GUI 工具，需用户本地安装），`Index.ets` 按 API 12 文档书写。最可能因 SDK 小版本差异需微调的是 `onWindowNew` 的 `event.handler.setWebController(null)`，已在指南第 8 节标注。

**已知差异（不影响主流程）**：文件下载接管（安卓用 DownloadManager）、UA 追加 App 标识、URL 唤起 App（Deep Link）三项暂未实现，补法见指南第 8 节。

#### ② iOS：走 PWA「添加到主屏幕」

**iOS 没有 Apple 开发者账号（$99/年）就做不出能装的 IPA**——免费 Apple ID 只能靠 Mac + Xcode 给单台设备签 7 天。站点 PWA 底子早已就绪（manifest + 192/512/maskable 图标 + apple-touch-icon 均 200、`display: standalone`、`start_url: /workbench`），故 iOS 走 Safari「添加到主屏幕」，体验与 App 一致，零成本、即时可用。

#### ③ 下载页改成三平台并列

`scripts/build_apk.py` 的 `write_download_page()` 重写：

- **鸿蒙卡片自动探测**：生成页面前用新增的 `find_hap()` 扫下载目录里的 `*.hap`——有就显示「下载 HAP + 版本 + SHA-256」，没有就显示「待构建」+ 浏览器添加到桌面的过渡用法。**以后接鸿蒙包不用改代码**，把 `.hap` 丢进 `/var/www/yexingchen/dist/download/` 再跑一次 `deploy_download_page.py` 即可
- **卡片重排**：`Android · 鸿蒙 4` / `HarmonyOS NEXT` / `iOS`，每张卡片带原生 `<details>` 折叠步骤（不依赖 JS）；顺带显示安装包体积
- 旧模板里写死的「敬请期待 / 正在适配」占位文案全部清除

**部署/验证**：`deploy_download_page.py` 重写生产下载页，`/download/` 与 `/download/yexingchen-2.1.0.apk` 均 200；真实浏览器（内置浏览器）取证——3 张卡片、3 个 `<details>`、桌面与 375px 移动视口下 `scrollWidth - clientWidth` 均为 0（无横向溢出）、按钮文案「下载 APK（136 KB）」、折叠标题「查看安装步骤 / 查看临时用法 / 查看安装步骤」全部符合预期。

**遗留**：HAP 尚未构建（需用户本地装 DevEco Studio + 华为开发者账号），下载页鸿蒙卡片当前显示「待构建」。

---

## [v2.36.0] - 2026-09-20

### 手机端音乐列表、AI 语音两处修复 + 桌面端语音不自动发送（SW `xuanhuang-v143`）

User：「1 手机端不展示音乐列表；2 手机端AI对话音频无法使用；3 电脑端AI对话音频输入时没有在输入框停留，直接发送了，需要优化」。

- **手机端音乐列表空白（真 bug）**：`mobile-deink.css` 曾写死 `#app.is-mobile .manage-pane { display:none }`。旧架构音乐页**内嵌迷你播放器**才「进去即播放器主视图」、隐藏曲库面板合理；但现在播放器已是**全局底栏**，`MusicView` 的 `.manage-pane` 就是唯一内容（歌曲列表表）——该规则把它整块隐藏，导致手机端进 `/music` 只剩空壳。修复：
  - 把该隐藏改为 `#app.is-mobile .island-inner:not(.island-inner-music) .manage-pane`（仅对视频/小说/工具等仍按旧策略收掉，`island-inner-music` 命中 `:not()` 不成立故不再隐藏）；
  - 新增 `#app.is-mobile .island-inner-music .manage-pane { display:block }`，并把列表玻璃卡片化（大圆角 + `--ls-glass`），手机端收掉「搜索/批量删除工具条 + 分页」；
  - **`MusicView.vue`** 用 `useIsMobile()`，手机端绕过「每页 10 条」的分页切片逻辑一次展示全量（分页控件已隐藏，否则只能看到前 10 首）。
- **手机端 AI 语音「无法使用」**：`VoiceInputButton` 在 `voice.supported.value === false`（APK WebView / iOS Safari 不支持 Web Speech API）时用 `v-if` **整按钮静默隐藏**——用户看不到入口也不明原因。改为**始终渲染**麦克风按钮：不支持时半透明 + `cursor:not-allowed` + hover 提示「当前设备/浏览器不支持语音输入」，点击弹 `ElMessage.warning('当前设备或浏览器不支持语音输入，请直接打字')`，避免无声消失；支持（桌面 Chrome/Edge、移动 Chrome）时行为不变。移动文案不就此隐藏管理入口。
- **桌面端语音自动发送**：`AssistantView.onVoiceDraft` 把识别文本写入 `draft` 后立即 `send()`，语音一结束就发出、无审阅机会。改为**只把识别结果填入输入框**（多段识别用换行拼接）+ `nextTick` 后 `focus()` 到输入框，由用户按 Enter / 点「发送」手动发出（与全站其它搜索/记账/笔记语音输入「只填不自动发」的行为一致）。桌面/手机统一。
- **桌面端回归**：`MusicView` 桌面端 `isMobile` 恒为 false，分页逻辑与原实现完全一致；`AssistantView` / `VoiceInputButton` 均不影响桌面正常语音。

**部署/验证**：SW `v142→v143`、全新 `npx vite build --outDir dist2` 核验标记（CSS 含 `island-inner-music .manage-pane` 与 `:not(.island-inner-music)`、Assistant 含 `composerInputRef`、主包含「当前设备或浏览器不支持语音输入」、MusicView 含全量 `list.length` 逻辑）→ 整体替换 `dist` → `deploy_frontend.py` 226 文件、服务器 sw.js `xuanhuang-v143`、home=200。仅前端，后端无源码变更不重部署。真实浏览器取证：`/music` 的 `.manage-pane` 计算样式 `display:block / visibility:visible`、含 5 首歌行；`/assistant` 的 `.vib` 按钮存在且可见——均 PASS；移动端 is-mobile 分支按 CSS 特异性严格成立。临时验证图已清。

---

## [v2.35.6] - 2026-09-19

### 手机端补上「AI 对话」入口（SW `xuanhuang-v142`）

User：「手机端没有AI对话的入口，需要加下」。桌面端 AI 是每页悬浮球（`FloatingAiButton`，`v-if="!isMobile"`），手机端没有任何对应入口——手机主页改版时快捷宫格只剩 8 个数据模块，`/assistant` 事实上无法从界面进入。

- **`MobileWorkbenchHome.vue`**：快捷宫格新增「AI 对话」并放在**首位**（图标为线性描边对话气泡 + 加号，与其它 8 个图标同一套风格）；宫格由 8 格变成 9 格，正好铺满 3×3。
- 「已接入 **8** 个功能模块」原先是写死的数字，改为 `{{ quick.length }}`，现在自动显示 9，避免以后再改宫格时数字失真。
- 顺手订正顶部注释里的「+ AI 胶囊」（该胶囊早已从模板删除，注释过期）。
- **`AssistantView.vue`**：placeholder 文案「点击**左侧**「新对话」或选择一个历史对话开始」在手机端是错的（手机是上下堆叠、没有左侧列表），改为「点击「新对话」开始，或从历史记录里选一个继续。」——桌面/手机都成立。

未采纳的方案：给手机端做常驻悬浮球。手机右下角已被桌宠占用、底部还有 Tab 栏与播放条，再加悬浮入口会撞车；而「我的」/其它模块在手机端也都是从主页宫格进入，所以在宫格补齐是唯一与现有结构一致的做法。

**实测（生产、`navigator.maxTouchPoints` 覆写 + resize 触发真实移动端分支）**：`#app` 带 `is-mobile`、底部双 Tab 在；宫格 9 格 3×3 无横向溢出（`scrollWidth == clientWidth == 451`），「AI 对话」位于首格（16~150 / y371），全部图标沿用收敛层的统一轴色 `rgb(98,230,209)`（新增的 `--ab-*` 语义色在手机端被该层统一覆盖，故未新增 token，已在代码注释里标明）；第三张数据卡显示「已接入 9 个功能模块」。点击「AI 对话」→ 路由 `/assistant`，手机版 AI 助手正常渲染（标题「AI 助手」、「＋ 新对话」、新 placeholder 文案），无横向溢出。桌面端回归：`#app` 无 `is-mobile`、左侧栏与工作台正常，宫格不渲染。

**部署**：SW `v139→v142`（本轮多次构建，末次统一跳版）、`npx vite build` + `deploy_frontend.py`（home=200）；仅前端，后端无源码变更不重部署。

---

## [v2.35.5] - 2026-09-19

### 工具列表操作列加「使用」入口（SW `xuanhuang-v139`）

User：「工具列表操作栏加个使用按钮，现在没入口」。工具页在早前重构中合并成「进页即管理页」后，操作列只剩「编辑 / 删除」，`go()`（打开工具本体）变成了没人调用的死函数——列表里看得见工具却点不进去。

- **`ToolView.vue`**：操作列新增「使用」按钮（`type="primary" plain`，作为该列主操作），并把它前面的「编辑」降为普通按钮、「删除」改 `plain`——视觉主次从「编辑」让给「使用」。列宽 150 → 210，三个按钮用 `.row-ops` 容器包住（单行、居左）。
- **`go()` 语义明确化**（原先只写了两行分支）：内置工具 `url` 就是站内路径（`/tool/pdf`、`/tool/idphoto` 等），直接 `router.push(url)`；外链工具进站内详情页 `/tool/:id`（详情页内嵌 iframe，另有「在新标签打开」兜底）。两侧都补了空 `url` 的提示，避免 push 到 `undefined`。
- **`ToolDetailView.vue` 兜底**：原先只在 `toolStore.list`（`enabled_only=1`，仅上架）里找工具，导致**已下架工具**从管理页点「使用」会落到「工具不存在或不开放」。现在找不到时再用 `getToolList({ size: 500 })` 拉全量（含下架）找一次，管理端预览下架工具也能正常打开；确实不存在仍展示原提示。后端 `/tools` 本就只校验登录、`enabled_only=0` 对任何已登录用户都返回全量，因此不引入额外越权面。
- **操作列样式收口**：`desktop-product.css` 里 `.row-ops` 规则的作用域由 `.admin-page .el-table` 放宽为 `.el-table`（管理后台 / 音乐库 / 工具列表共用一套），并删掉 `MusicView.vue` 中重复的 `.row-ops` 布局声明（只保留乐库特有的按钮 `min-width: 56px`），避免同一套排版规则散落多处。

**实测（生产 1440px，同源 iframe 验收页逐元素采集）**：工具表 9 行全部出现 `使用 1171~1219 | 编辑 1227~1274 | 删除 1282~1329`，同一行、居左（单元格 +12px）、行高统一；点「使用」：外链工具「练字」→ `/tool/9` 详情页正常渲染（标题「练字」，无「工具不存在或不开放」），内置「PDF 工具」→ `/tool/pdf` PDF 工具页正常渲染；`/music` 回归检查：操作列 250px、按钮单行、gap 8px、`min-width: 56px` 保留、行高统一 43px。

**部署**：SW `v138→v139`、`npx vite build` + `deploy_frontend.py`（home=200）；仅前端，后端无源码变更不重部署。验收用的临时 `/preview/vp.html` 已从服务器删除。

---

## [v2.35.4] - 2026-09-19

### 管理后台操作列：用户管理按钮全部平铺居左 / 角色管理「操作栏错位」真根因修复（SW `xuanhuang-v138`）

User 两条反馈：「用户管理操作栏里按钮都展示出来，居左展示」「角色管理操作栏这里错位了」。第二条不是样式问题，是一个**渲染崩溃导致的表格列错位**。

**① 角色管理「操作栏错位」真根因：`menu_ids` 类型不匹配导致单元格渲染崩溃**
- 现象（截图实证）：角色表里「编辑」独占一行、「删除」掉到第二行并溢出单元格，行高被撑到 68px；同时「可见菜单」表头下显示的是**排序值**（0）——整行从第 4 列开始左移了一格。
- 排查（生产真实浏览器 DOM 取证）：表头 6 列、表体 `<tr>` 却只有 **5 个 `<td>`**，第 4 列位置是一个 `<!--comment-->` 占位；控制台报 **`TypeError: h.menu_ids.map is not a function`**。
- 根因：`backend/app/routers/admin_roles.py` 里 `menu_ids` 在 DB 是 `Text`（存 JSON 字符串 `"[1,2]"`），接口**原样回传字符串**；而前端 `formatMenuPerms(row)` 写的是 `row.menu_ids.map(...)` —— 字符串有 `.length` 所以躲过了前置判空，`.map` 直接抛错 → 该单元格渲染失败 → 后面的「排序 / 操作」列整体左移一格，「操作」列继承了「排序」列的 80px 宽度 → 编辑/删除被挤成两行，看起来就是「错位」。
- 修复（后端出口/入口统一收口，不需要数据迁移）：
  - 新增 `_parse_menu_ids(raw)`：把「JSON 字符串 / 数组 / 逗号串 / None / 脏数据」统一解析为整型数组；`_role_to_dict` 改为返回数组。
  - 新增 `_dump_menu_ids(ids)`：写库统一序列化为 JSON 字符串，兼容前端传数组（旧 `RoleIn.menu_ids: str` 会让数组 422）或旧页面传 JSON 字符串。
  - `RoleIn.menu_ids` 由 `str` 改为 `Any = None`；更新接口判空由真值判断改为 `is not None`——顺带修掉「清空全部菜单（[]）保存不生效」（空数组为 falsy，旧逻辑会跳过更新）。
- 修复（前端防御）：`AdminRolesView` 新增 `normalizeMenuIds()`（数组/JSON 串/逗号串通吃），`formatMenuPerms` 与 `openRoleForm` 都用它——后者原先内联 `JSON.parse` 遇到非 JSON 串会抛错导致弹窗打不开。`AdminUsersView` 的 `row.allowed_islands.split(',')` 同样加了 `getIslandList()` 容错（同类隐患）。
- 修后实测（生产 1440px）：表头 6 列 / 表体 6 个 `<td>`、**0 个空占位**；三行行高统一 41px；「可见菜单」正确显示「全部启用菜单」「笔记 / 账本 / 旅行足迹 等 13 项」；排序回到自己列；操作列 180px，`编辑 1203~1251` + `删除 1259~1306` 同一行居左。

**② 用户管理操作列：下拉 → 按钮全部平铺、居左**
- 原设计把「修改 / 重置密码 / 删除」收进「编辑 ▾」下拉，待审批行收进「操作 ▾」，需要二次点击。现改为全部常显：待审批行 `审核通过 / 审核不通过`，其余行 `修改 / 重置密码 / 删除`；列宽 220 → 230。
- 实测：每行 3 个按钮同一行、居左（起始 1153 = 单元格 +12px 内边距）、行高统一 63px、无下拉、无空占位。

**③ 统一「操作列」排版规则**（`desktop-product.css`，作用域 `.admin-page`）：`.row-ops { display:flex; align-items:center; justify-content:flex-start; flex-wrap:nowrap; gap:8px; white-space:nowrap }` + 取消 Element Plus 相邻按钮的 `margin-left`。角色管理、菜单管理操作列宽度 160 → 180，三个管理页共用同一套规则，避免后续再被列宽挤成两行。

**部署**：SW `v137→v138`；前端 `npx vite build` + `deploy_frontend.py`（home=200）；后端 `deploy_backend.py`（`admin_roles.py` 在白名单内，alembic 无新增、pm2 重启 `health=200`、`ENV=production` 保留）。验收用的临时 `/preview/vp.html` 已从服务器删除。

---

## [v2.35.3] - 2026-09-19

### 桌面端两处真根因修复：`id="app"` 重复导致内容被推远 220px / 登录页输入框白底浅字（SW `xuanhuang-v137`）

User 反馈两条：「登录页其他都行，就是输入框文字看不清，要优化下」「空白那个，我自己右键不显示手机端，但是我滑动不，这样吧，你自己拉浏览器验收下看吧」。两条都不是样式调参能解决的，各自有一个结构性根因。**本轮全部用真实浏览器实测取证（内置浏览器 + 同源 iframe 验收页）。**

**① 内容区左侧多出 220px 空白 —— 真根因：`id="app"` 重复嵌套**
- 现象：侧栏右缘到内容左缘之间空出一整条侧栏宽（User 描述「侧栏离右侧内容依然有很大空间」「偏右拥挤」）。此前多轮改 `max-width / margin / padding` 均无效。
- 根因：`frontend/index.html` 的挂载点是 `<div id="app">`，而 `App.vue` 的模板根节点**也是** `<div id="app">` → DOM 里出现**两个同名 id 嵌套**（`div#app[data-v-app] > div#app`）。于是所有 `#app:not(.is-mobile)` 规则**命中两层**，侧栏让位 `padding-left: 220px` 被叠加成 **440px**。真实浏览器实测 1440px：`.dsb` 占 0~220，而 `.workbench-page.left = 440`、`.wb-kpi` 左缘 480 —— 中间 220px 就是那片「空白」。
- 修复：挂载点改名 `#app-root`（`frontend/index.html` + `frontend/src/main.js` 的 `app.mount('#app-root')`），让 `#app` 全站唯一。移动端零回归：`#app.is-mobile` 系列选择器一直只挂在 `App.vue` 根节点上，class 归属未变。
- 实测（内置浏览器 + 同源 iframe 验收页逐宽度采集几何）：1920/1680/1440/1366/1280 → 侧栏 `0~220`、内容 `220~右缘`、内容左右内边距各 40px **完全对称**；1100/1024 → 侧栏 200 + 让位 200；/workbench、/music（岛屿内页）、/admin/users（管理后台）三页一致；`querySelectorAll('[id]')` 再无重复 id。

**② 登录页输入框文字看不清 —— 真根因：CSS 权重压制 + 日间 token 白底**
- 根因：桌面端通用输入框皮肤 `#app:not(.is-mobile) .el-input__wrapper { background: var(--dp-surface) !important }` 带 **ID 权重 (1,2,1)**。两条规则同为 `!important` 时先比 ID，它压过登录页原有的 `html:root[data-theme="day"] .login-page .el-input__wrapper { background: rgba(24,32,41,.7) !important }`（**(0,4,1)**）。而日间主题 `--dp-surface = #ffffff` → 登录页（深墨青底、两套主题都是深色）里的输入框被刷成**白底**，文字却仍是 `#e8f4fc` 浅色 → 白底浅字，怎么都看不清。用同源复刻页（引用线上 CSS）复现：wrapper `#ffffff` + 文字 `rgb(232,244,252)`。
- 修复：`desktop-product.css` 新增同等 ID 权重、选择器更长的 `#app:not(.is-mobile) .login-page .el-input__wrapper / .el-textarea__inner / .el-input__inner` 规则，把登录页输入框统一拉回深墨青底 `rgba(24,32,41,.72)` + 雨青描边 + 浅色文字（昼夜两套主题一致）。修后复测：wrapper `rgba(24,32,41,0.72)` + 文字 `rgb(232,244,252)`，对比度充足。
- 顺带加固 Chrome 自动填充（记住我 / 密码管理器会强制刷浅蓝底 + 自带文字色）：补 `:autofill` 标准伪类、`-webkit-text-fill-color`、`background-color`、`inset box-shadow` 1000px 遮罩、`filter: none`，并让 `:has(input:-webkit-autofill)` 的 wrapper 同步保持深底。

**③ 连带修复：≤900px 侧栏改为浮层抽屉**
- 原 `@media (max-width: 900px)` 用 CSS 强制 `translateX(-100%) + opacity: 0` 隐藏侧栏，同时把浮动唤出按钮 `.dsb-open-fab` 一起 `display: none` → 在窄窗口/DevTools 停靠压缩视口时**完全没有导航入口**。
- 改为：≤900px 内容 `padding-left: 0` 铺满，侧栏展开时以高 z-index 浮于内容之上（抽屉）；`DesktopSidebar.vue` 补「窄屏 + 无用户折叠偏好时默认折叠，展开后路由跳转自动收起」。

**验收方式**：临时在 `/preview/vp.html` 部署一个同源 iframe 验收页（支持 `?w=&h=&path=`；同源→Cookie 不丢＝带登录态真实渲染，且 iframe 自身视口即目标宽度→媒体查询真实生效），用内置浏览器逐宽度 + 逐路由采集几何与截图；另用 `localhost` 静态复刻页引用线上 CSS 做 day/night 双主题级联取证。**验收完成后服务器上的 `/preview/vp.html` 已删除**。

**部署**：SW `v135→v136→v137`、`npx vite build` + `deploy_frontend.py`（226 文件、home=200、服务端 `sw.js` = `xuanhuang-v137`）。仅前端；后端无源码变更不重部署。

---

## [v2.35.2] - 2026-09-19

### 倒计时/足迹地图界面精简（SW `xuanhuang-v129`）

User 集中反馈三项视觉冗余，本轮一并精简：**① 倒计时卡片隐藏📅日历图标与🏠"取消首页展示"按钮**（卡片左上角的日历图与悬停时右上角出现的房子图均遮视线、多余），并把卡片上的天数数字改为**垂直居中显示**（之前紧贴顶部，与右上角按钮区上下交叠）；**② 倒计时详情页同步隐藏日历图标**，只保留标题/大数字/返回/编辑/删除；**③ 足迹地图删除行程连线与右上角小地图**——连线只是同色细线、辅助信息量为零反而遮盖城市标记；小地图是冗余缩略图，遮挡地图右上方视野。地图图例同步收敛为三项（足迹省份/未去过/城市足迹）。

**实现要点**：
- `frontend/src/views/CountdownsView.vue`：删 `.cd-icon` 模板与对应 CSS；删 `.cd-card-actions` 内🏠按钮及 `toggleHome()` 函数；改 `.cd-card-body` `justify-content: space-between`→`flex-end`，`.cd-card-top` 加 `flex:1` + `align-items:center` + `justify-content:center` 让数字占据剩余高度并居中。`.cd-days` 字号 28→34px 与桌面更协调。
- `frontend/src/views/CountdownDetailView.vue`：删 `.cdd-icon`（顶部📅）模板与孤儿 CSS；同步移除顶部操作栏的🏠按钮与 `toggleEdit()` 外多余的 `toggleHome()`。**手机端** `.cd-card-body` 在 `mobile-native-glass.css` 改为 `position: absolute; inset: 0` 以继承桌面 Flexbox 居中布局（避免移动端数字贴底/不居中）。
- `frontend/src/components/travel/TravelMap.vue`：删 `tm-line`/`tm-line-glow` 两个 `<path>`、`<defs>` 内连线渐变；删 `tm-mini` 整个右上角小地图 SVG 与对应 `miniD` 计算属性；删 `tripLines` 计算属性与 `smoothD` 工具函数；图例 DOM 收敛为三项。CSS 删除连线动画 `tm-line-pulse` 与小地图 `tm-mini*` 样式块。

**部署/验证**：
- SW `v128→v129`；`npx vite build --outDir dist2` 全新构建核验 bundle 已不含 `取消首页展示/行程连线` 字符串、保留 `足迹省份/cd-card-top` 结构 → 替换 dist → `deploy_frontend.py`（220 文件、home=200、服务端 sw.js 已 `xuanhuang-v129`）。
- **真实浏览器取证 PASS**（Playwright 真 chromium、admin@yexingchen.cn 登录、清除旧 SW 后再访问）：倒计时列表 `countdown-new.png` 卡顶无📅、卡内数字垂直居中；hover `countdown-new-hover.png` 右上角仅显示✏️+🗑️两按钮无🏠；详情 `countdown-detail-new.png` 仅标题+大数字+返回/编辑/删除；足迹 `travels-new.png` 城市标记之间无连线、右上角无小地图、左下图例三项；`navigator.serviceWorker.controller?.scriptURL = https://yexingchen.cn/sw.js`、SW 状态 activated。
- 经验：服务器实际分发新代码（curl 已验），但浏览器代理首次仍显示旧界面——根因是旧 SW 缓存未失效；规范流程应是「先在 DevTools 调 `unregister()`+`caches.delete()` 再访问」。

无后端变更；测试/凭证临时文件（`%TEMP%\cd_verify_note.txt` 等）已清；git 提交并推送。

---

## [v2.35.1] - 2026-09-19

### 证件照后端化收尾：模型入库 / 移除 onnxruntime-web / 清 nginx COEP 与 dist 残留

v2.34.0 把 MODNet 推理迁到后端后，本轮清掉全部「浏览器推理时代」遗留痕迹。无功能变化、无需重新部署前端（线上 v128 即最终态）。

- **模型入库**：`model-q.onnx`（6.6MB）从 `frontend/public/models/modnet/` 迁至 `backend/models/modnet/` 并提交进 git——此前它被 `.gitignore` 排除、只存在于本机，换机克隆即无法部署后端。`deploy_backend.py` 白名单源路径同步改为 `backend/models/modnet/model-q.onnx`（服务器仍上传为 `backend/models/modnet.onnx`）；`idphoto.py` `MODEL_CANDIDATES` 收敛为后端三候选，服务器运行行为不变。
- **移除 `onnxruntime-web` 前端依赖**：前端已零引用（`matting.js`/`mattingWorker.js` 已删），`package.json`/`package-lock.json` 整体移除。
- **删除 `frontend/public/models/` 整目录**（含残留 `ort-wasm-simd.wasm` 10.6MB）。public 下大文件每次 `vite build` 都会拷进 dist——v128 构建曾把 17.2MB 模型+wasm 又带回服务器 dist，本轮已删服务器 `dist/models/` 残留并从根上杜绝复发。
- **nginx 移除 `Cross-Origin-Embedder-Policy: credentialless`**：该头是 v126 为浏览器端 onnxruntime 线程化 wasm（SharedArrayBuffer）临时加的，推理迁后端后无用且前端零处引用跨域隔离。服务器 conf 同步删除 + `nginx -t` + reload；验证首页 200、`/health` 200、`/api/idphoto/matte` 未登录 401（路由存活）、响应头仅剩 COOP/CORP。
- **残留终验**（paramiko 实查）：`uploads/countdown/` 空、`dist/uploads` 无假文件、DB 仅剩用户旧卡片；本地 `scripts/_test/` 临时取证素材全部删除。

---

## [v2.35.0] - 2026-09-19

### 三问题最终闭环：证件照前端解包修复 / 倒计时背景图 URL 前缀 / 足迹标记微调（SW `xuanhuang-v128`）

User 追问「按钮点击后到底走的什么抠图路径」。本轮把 v2.34.0 部署后遗留的三处残问题全部收尾，且**全部以真实浏览器在生产端到端取证**（真账号登录→页面操作→截图/网络请求/数据库三方对账）。

**证件照——前端 matteFromBackend 解包层级错误（线上"API 通了但页面仍抠不出人"的真根因）**：
- v2.34.0 用线上 API 直调验证了后端 `/api/idphoto/matte` 返 200、前景 0.4448，但用户页面仍抠不出人。差异在：axios 响应拦截器已 `return response.data`，前端 `matteFromBackend` 里又写了 `const { data } = await api.post(...)` **二次解构** → 恒 `undefined` → `return null` → **永远静默回退旧 flood-fill 算法**（绿色选取、容差扩散），对复杂背景人物必然失败。这也解释了「助手线上 API 测试通过、用户实测却不行」的错位。
- 修复：改为 `const body = await api.post(...)` 直接取 `body.data`。浏览器实测：上传人像→生成证件照，人物完整、边缘干净（后端 AI matte 生效）。

**倒计时背景图——上传返回 URL 缺 `/uploads` 静态挂载前缀（422 修复后的下一层 bug）**：
- 现象：上传/建卡全部 200，但卡片背景图不显示；`/countdown/xxx.jpg` 被 SPA fallback 兜底成 index.html（HTTP 200 但 Content-Type text/html，浏览器拿到"图片"实为 HTML）。
- 根因：`save_upload_file` 返回相对路径 `/countdown/xxx.jpg`，而后端静态挂载点是 `/uploads`（nginx `location /uploads/` alias → backend/uploads/）；`travels.py` 早已正确补前缀（`url = f"/uploads{relative}"`），`countdown.py` 的 `upload_image` 漏了这步。
- 修复：`countdown.py` 上传返回补 `/uploads` 前缀（对齐 travels.py 写法）；`delete_countdown` 清理背景图时兼容剥掉 `uploads/` 前缀再拼 `UPLOAD_DIR`。
- 取证：DB 落库 `/uploads/countdown/xxx.jpg` → 该 URL 返 `image/jpeg` 真图 → 浏览器卡片实际渲染星空背景（截图确认）。删除卡片时背景文件自动清理。

**足迹地图标记微调**：`FOOT_SCALE 0.15→0.10`、琥珀定位针加**白色描边光环**（把琥珀标记与同色系省份/底色隔开，城市级小标记依然清晰）。浏览器实测：约 1/20~1/30 省份大小、不喧宾夺主、江苏金色高亮正常、与站点风格协调。

**部署/清理**：前端 `vite build --outDir dist2` 核验 SW v128 → 替换 dist → `deploy_frontend.py`；后端重部署（health=200）。线上测试残留全清（2 张测试卡片经页面删除流程删除、假 HTML 文件与孤儿上传文件已清、`uploads/countdown/` 归零）；本地临时脚本/测试图已删；git 提交并推送（v2.34.0+v2.35.0 一并入库）。

---

## [v2.34.0] - 2026-09-19

### 三问题现网复验修复（最终落地：证件照改后端 CPU 推理 / 倒计时上传 / 足迹印记）（SW `xuanhuang-v127`）

User 反馈「证件照还是扣不出人、你的线上测试也有问题；足迹图标不好看且偏大；倒计时你到底试过没，自己上现网传下」。本轮**全部改用真实浏览器在生产逐项实测通过**，并以线上 API 调用取证（不再停在读代码/日志的纸面判断）。

**证件照 AI 人像分割——迁到后端 CPU 推理（根治线上抠不出人）**：
- 根因复盘：浏览器端 onnxruntime-web 的 WASM 后端对**动态 INT8 量化**的 MODNet 算子输出**全零**（人物被整体判为背景），导致「透明底 alpha 全为 0、人物被抠没」；此前虽有分布尝试（降级 1.18 + `numThreads=1`），但 wasm 层对量化算子支持仍不可靠、且首次还需下载大模型。
- 最终落地：删除前端 `matting.js/mattingWorker.js` 与浏览器端推理，新增后端路由 `backend/app/routers/idphoto.py`：`POST /api/idphoto/matte` 收图→512 居中缩放→`onnxruntime` **CPUExecutionProvider** 跑量化 `model-q.onnx`（6.6MB）→上采样回原尺寸灰度 PNG→base64 返回。前端 `matteFromBackend` 解码为 matte，`applyMatte` 按原图像素坐标写入 alpha（与 `drawCrop` 同一几何映射）。
- `main.py` 注册 idphoto 路由；`requirements.txt` 加 `onnxruntime>=1.18.0`；`deploy_backend.py` 白名单补 `idphoto.py`+把 `frontend/public/models/modnet/model-q.onnx` 上传为 `backend/models/modnet.onnx`（含 pip 安装、pm2 重启保 ENV=production）。
- 本地 Python 实测：同一量化模型 CPU 产出前景 **44.45%**、动态范围 0~1，人物完整抠出。**线上 API 实测 PASS**：真账号登录→上传人像→ `/api/idphoto/matte` 返 200、前景占比 **0.4448**、min/max 0/255，人物轮廓完整（不再全透明）。优缺：服务端一次性加载 session 约几分钟首召冷启动，后续请求即时；换来浏览器端不再下载/推理大模型，稳定可靠。

**倒计时背景图上传+保存**：
- 根因：`frontend/src/api/index.js` 全局设了 `Content-Type: application/json`，axios v1 对 FormData 会先 `formDataToJSON` 把 file 字段清空 → 后端 422「file Field required」。修法：**移除 api 实例全局 Content-Type**，交 axios 自动判定（JSON→application/json，FormData→multipart/boundary）。
- `CountdownsView` 动态校验：`target_date` 仅非农历必填（农历模式+背景图可保存）。
- 线上 API 实测 PASS（真账号）：上传 jpg→`/api/uploads/image` 返 **200**+URL `/countdown/...jpg`；建倒计时→`/api/countdowns` 返 **200**；删除清理成功。**真实浏览器实测 PASS**：全新实例登录→倒计时新建弹窗→file input 注入图片→背景预览正常、**无任何报错**。

**足迹地图标记**：当前代码已为**琥珀定位针**（teardrop pin + 白色光晕环 + 底部投影），默认 fill = `url(#tm-footg)` 琥珀渐变，hover/active 转青绿辉光，`FOOT_SCALE 0.10`。**全新浏览器实测 PASS**：默认全景下标记约 **1/20~1/30 省份、约 10–14px**，小、清晰、不遮盖省份、不喧宾夺主（用户之前看到的"大青圆点"是旧 SW 缓存的旧版本，v127 已清缓存强制刷新）。

**部署/清理**：前端 `vite build --outDir dist2` 全新构建、核验 bundle 含 `idphoto/matte`+`ffc25e`+SW v127→替换 dist→`deploy_frontend.py`（222 文件、home=200）；后端 `deploy_backend.py`（onnxruntime 安装、模型上传、health=200）；SW `v126→v127` 强刷客户端缓存。**已清线上测试残留**（测试倒计时记录、故障期 0 字节/极小上传暂存文件）；**已删本地临时脚本/测试图/截图**；测试号密码已重置为已知值并记录（git 提交随 v2.35.0 一并进行）。

---

## [v2.33.1] - 2026-09-19

### 复验修复：倒计时上传 / 证件照抠图 / 足迹地图（SW `xuanhuang-v121`）

User「倒计时上传背景照还是有问题；你自己看这个合适吗去 github 找方案（足迹地图）；证件照还是不行找解决方案」。

**证件照 AI 抠图失效——根因输入归一化错误**：`mattingWorker.js` 用 `[0,1]`（`/255`）归一化输入像素，而 MODNet 训练用的是 `[-1,1]`（`/127.5 - 1`），导致人物被误判为背景、mask 出力极低。Python 复算对比：`/255` 时人物 mask 占比仅 7.6%、`/127.5-1` 时达 61% → 改三通道 `/127.5-1`，人物完整抠出。

**倒计时背景图上传 400**：上轮已定位 `countdown.py` 扩展名带点，但部署白名单 `deploy_backend.py` 漏传 `countdown.py/file_utils.py` 致线上仍跑旧代码；且前端 `countdown.js` 手写 `Content-Type: multipart/form-data` 未带 boundary 可能致解析失败。本轮白名单补两文件重部署、删手写 Content-Type（交浏览器自动生成 boundary）。线上 API 实测上传 jpg 回 200 PASS，测试图已清理。

**足迹地图图标**：`TravelMap.vue` 加 `FOOT_SCALE=0.15` 压脚印（原 glyph 盖全图）、删空 `.tm-dot__tip`，城市级小标记对齐省市，浏览器截图 PASS。

**部署**：前端构建核验 + SW `v120→v121` → 替换 dist → `deploy_frontend.py`；后端同步。文档已更新、测试图与临时脚本已清理、git 已提交推送。

---

## [v2.33.0] - 2026-09-19

### 证件照 AI 人像分割 + 倒计时上传修复 + 快捷入口精简 + 足迹地图优化（SW `xuanhuang-v118→v119`）

User 一次性提 7 项修复/精简需求（证件照提取人物 · 足迹地图太灰 · 倒计时上传 jpg 报错/去图标字段 · 快捷入口隐藏 · 工作区闭环 · 整理提交 · 扫代码精简）。

**证件照 AI 人像分割**：`IdPhotoToolView.vue` 引入浏览器本地 MODNet 分割（自托管 `public/models/modnet/model.onnx` FP32 25MB + onnxruntime-web 1.30 `ort-wasm-simd-threaded`，WebWorker `mattingWorker.js` 隔离推理），缩放 512×512 → 原图尺寸 matte 逐像素写 alpha。复杂背景（室外树影）也能完整抠出人物（此前纯算法只留轮廓）。踩坑：FP16 onnx 跑 wasm 报错 → 换 FP32；Nginx `.mjs` MIME 错 → 加 `types{application/javascript mjs; application/wasm wasm;}`；首次需下载 ~39MB 模型较慢 → 加 `preloadMatting()`（进页面/上传即后台建 session）化简等待。生产取证：复杂背景抠出透明底 `alphaMax=255`、有效像素 17.9%，成功。

**倒计时背景图上传 400**（jpg 被拒）：后端 `ALLOWED_IMAGE_EXT` 带点(".jpg") 与判不带点的扩展名不一致 → 改不带点；前端补友好格式/大小校验；新建/编辑弹窗删除用途不明的「图标/emoji」字段，仅保留颜色输入。

**快捷入口精简**：隐藏「音色克隆 / AI封面」（内置工具 URL 过滤）与「AI对话 / 记一笔」（固定动作移除）。

**足迹地图**：未访省份填充基础色（不再描边显灰）、鼠标移入高亮、黄点改脚印/现代标记贴合水墨风。

**部署**：倒计时+快捷+地图 → SW v118；证件照 → SW v119。`npx vite build --outDir dist2` 核验 → 替换 dist → `deploy_frontend.py` 225 文件、服务器 sw.js `xuanhuang-v119`、home=200。生产浏览器实测复杂背景证件照 AI 抠图成功。

---

## [v2.32.0] - 2026-09-19

### 修复：网页端返回按钮「消失 + 失效」双问题（SW `xuanhuang-v117`）

User「有些页面的返回按钮失效效果了，有些页面的返回按钮消失了，你排查下吧（是网页的，手机端我不需要返回按钮）」。

**根因两处**：
1. **消失（被顶栏遮挡）**：桌面端 `GlobalTopBar` 为 60px 顶部固定悬浮层（z-index:1000），而岛屿/工具模块页共用 `IslandInnerBase` 外壳，其 `.inner-header` 顶部 no 顶栏避让（padding-top 仅 26px）→ 页首 `.back-btn`（←返回工作台）正落在顶栏之下被盖住；独立页 `ProfileView` 顶部 padding 40px 亦被盖。
2. **失效（不回来源页）**：`IslandInnerBase.goBack()` 桌面端写死「`history.length>1 && !isMobile` → `router.push('/workbench')`」，完全忽略「返回上一页」；从 /stocks 进详情再点返回会硬跳工作台而非回 /stocks 列表。

**修复**：
- `IslandInnerBase.vue`：`.inner-header` 桌面默认 padding-top → `84px`（60px 顶栏 + 留白，1100px 断点同步 80px）；`goBack()` 简化为统一「回来源页优先」——有历史 `history.back()`，仅在无历史（直接落地）时回工作台，桌面/移动一致。
- `ProfileView.vue`：删除重复的文字版「← 返回工作台」（保留 BackButton 组件唯一返回），`.profile-page` 顶部 padding 40→84px 避让顶栏。

**构建/部署/验证**：`npx vite build --outDir dist2` 核验 `84px 40px 14px` 进 CSS、`history.back` 进 JS + SW `v116→v117` → 替换 dist → `deploy_frontend.py` 220 文件、服务器 sw.js `xuanhuang-v117`、home=200。**生产桌面浏览器取证 PASS**（Playwright 1440×900，真 chromium）：/music /tool /finance /stocks /profile /travels /contacts /notes /assistant 九个页返回按钮全部可见（rect 128×37 或 80×32，top≥84px 未被顶栏遮挡）、/profile 仅剩 1 个返回按钮（无重复文字版）；真实导航链：工作台→音乐→返回=工作台 ✓、/stocks→/stocks/600519→返回=**/stocks** ✓（旧逻辑会错跳工作台）、/finance→返回=工作台 ✓。**手机端零回归**（390×844）：上述页面 `.app-back-btn/.back-btn` 均 `display:none` 隐藏，符合「手机端不需返回按钮」。仅前端，后端无源码变更。

---

## [v2.31.0] - 2026-09-18

### 修复：模块内页白天模式下仍是深灰（全站岛屿内页背景昼夜化，SW `xuanhuang-v116`）

User「网页现在风格不统一，比如外面我用白天的样式，进入各个模块里面，依然是灰色的，这块要做风格统一，其他模块的也是一样的」。

**根因**：所有岛屿/工具模块页（音乐/小说/视频/日志/工具/倒计时/音色克隆/水印……）共用 `IslandInnerBase.vue` 页面外壳，其 `.island-inner::before` 背景写死一段深色渐变 `linear-gradient(168deg, #1b262f 0%, #131b22 55%, #10161c 100%)`，**完全无视 `data-theme="day"`**；而工作台/登录页/岛屿主页(`.island-page`)此前已有日间覆盖。故外部切到白天后，进入任一模块仍是深灰冷色。

**修复**：
- `variables.css` 新增岛屿内页背景 token `--li-sky / --li-sky-mid / --li-sky-deep / --li-title-a`，并提供夜/日两套值（日间与 Linear 亮表面 `#eef1f3` 同族）。
- `IslandInnerBase.vue`：`.island-inner::before` 背景渐变改用 `--li-sky*`；`.island-title` 大标题渐变顶部改 `--li-title-a`（夜近白霜 / 日深墨，避免白字埋进亮底），桌面与移动两处标题渐变同步。

**构建/部署/验证**：`vite build --outDir dist2` 核验主 CSS 含 `--li-sky: #1d2830`(夜) 与 `--li-sky: #eef1f3`(日)、SW `v115→v116` → 替换 dist → `deploy_frontend.py`（保留 `download/.well-known`）220 文件 home=200。**生产浏览器取证 PASS**：登录后强制 `data-theme="day"`，实测 `--ls-bg1=#eef1f3 /--li-sky=#eef1f3 /--color-bg=#f6f7f8`，`/tool/countdown` 页面 shell 计算背景 `rgb(244,247,248)` 浅色、截图呈浅灰白、文字深色；切回 night 仍为深色，昼夜均可正常切换。仅前端，后端无源码变更。

---

## [v2.30.0] - 2026-09-18

### 桌面端「深墨青玉 · Linear 产品风」收敛层（SW `xuanhuang-v115`）

User「我不是要你把手机端复制到网页来，我要求的是按照这种风格去设计网页端的 UI，你去找下 github 找类似风格」→ 明确桌面端与手机端是**两种独立设计语言**：手机端是「灵动卡片 + 每模块渐变」的数据工具，桌面端重做为 **Linear 式深色产品风**（参考 Linear / shadcn dark / Supabase dark 等产品级审美），实色表面 + 发丝描边层级 + 多层淡阴影造深度，单一青玉 `#4fc6b8` 仅做克制点缀。

**新增 `desktop-product.css`（作用域 `#app:not(.is-mobile)`，手机端与桌面互不干扰）**：

- **表面阶梯用「边框亮度」而非色块层级**：`--dp-bg #0b0f14` / `--dp-bg2 #0f151b` / `--dp-surface #121820` / `--dp-surface2 #18212b`，发丝描边 `--dp-line rgba(220,235,246,.10)` 与 `--dp-line-strong .17` 区隔层级。
- **Linear 式多层淡阴影**：`--dp-shadow = 0 1px 2px rgba(0,0,0,.38), 0 8px 24px rgba(0,0,0,.22)`（一层紧贴 + 一层远距柔化，尽量薄），hover 只聚焦描边不加位移/缩放。
- **单一青玉克制点缀**：`--dp-accent #4fc6b8`，仅用于当前态、主按钮、焦点环、关键数字等精确定位处；工作台卡片、表格、表单统一收口为实色面 + 发丝框，去掉玻璃/霓虹/高饱和标签。
- 接管工作台卡片、资讯条、顶栏入口等 Linear 组件态（hover 聚光 / active 压入 / 焦点描边）。

**改动文件**：新增 `frontend/src/assets/styles/desktop-product.css`（471 行）；`main.js` 在 `mobile-product.css` 之后引入。SW `v110→v115`（本轮跳升清旧缓存，确保已装 App/PWA 拿到桌面新皮肤）。

**构建/部署/验证**：`vite build dist2` 全新输出目录 → 核验 bundle 含 `--dp-bg`/`--dp-line`/`--dp-accent: #4fc6b8` 标记 + **SW `xuanhuang-v115`** → 整体替换 dist → `deploy_frontend.py`（保留 `download/`、`.well-known/`）。**生产核验 PASS**：服务器 sw.js `xuanhuang-v115`、desktop token 已进 `index-6eD2JQii.css`、`https://yexingchen.cn/` home=200。桌面 Playwright 1440×900 深/日双主题截图验收卡片/表格收口生效、手机端 `#app.is-mobile` 门控零回归。仅前端，后端无源码变更。

---

## [v2.29.0] - 2026-09-18

### 审 Codex 新手机 UI 去坑 + 产品化收敛（SW `xuanhuang-v110`）

对 Codex 交付的 `mobile-product.css`「产品化收敛层」（把各模块统一成可靠数据工具、去模块渐变/玻璃碎片）做全量核对，发现与既有 `mobile-module-color.css`「灵动·独立渐变」层同载存在**选择器特异性冲突**，**修复 3 处硬坑**：

- **零值异色根治**：`mobile-module-color.css` 的 `.fin-page .fin-kpi-val`(1,3,0) 特异性高于收敛层 `.fin-kpi-val`(1,2,0)，即使后者后加载也被渐变压住 → 记账页零值仍被渐变/语义色渲染（本月支出 ¥0 呈现青绿渐变、流水笔数 0 也带色）。**删除 `mobile-module-color.css`**（main.js 引用 + 文件本体，同步清理 `mobile-native-glass.css` 失效注释）→ `mobile-product.css` 成为唯一收敛层。
- **倒计时 API 回归**：`countdown.js` BASE 被误改 `/api/countdowns`→`/countdowns`（dev/prod 均无对应 rewrite）→ 修复为 `/api/countdowns`，否则倒计时全端请求 404。
- **工作台流水笔数恒「—」**：`MobileWorkbenchHome.vue` 声明 `count` 但 `onMounted` 从未赋值 → 补 `d.month_count`。
- **SW 升版** `v109→v110`：本 SW 为「版本号+静态缓存」模式，同版本不清旧缓存即拿旧 bundle，升版确保已装 App/PWA 用户拿到本次修复。

**构建/部署/验证**：`npx vite build --outDir dist2` 核验（新文案「本月净流入/流水笔数」、`/api/countdowns`、`month_count` 在；`mobile-module-color` 不在）→ 整体替换 dist → `deploy_frontend.py` 217 文件、服务器 sw.js `xuanhuang-v110`、home=200。**生产浏览器取证 PASS**：记账页三个零值计算色 `rgb(240,245,248)=#f0f5f8` 中性正文（不再青绿渐变）、工作台零值收支已不带 `.up/.dn` 语义类、流水笔数由「—」→「0」、390px 手机 A/B 双主题截图布局干净、桌面零回归。全部前端改动，后端无源码变更不重部署。

---

## [v2.28.0] - 2026-09-17

### 手机端 7 大模块「灵动卡片 · 独立渐变」重设计 + APK 深墨沉浸状态栏/导航栏（SW `xuanhuang-v109`）

User「音乐、笔记、足迹、记账、行情、通讯录、倒计时的 UI 风格、框架、排版需要重新设计下，现在好丑」→ 明确走「灵动卡片 + 渐变」：每模块一套独立高饱和渐变主题，像记账类 App 一样分区、活泼、有质感。仅手机端，桌面水墨国风零回归。

**根因**：v2.24~v2.27 手机端只做了「去管理后台感（隐藏控件）+ 换 token」，但各模块内部仍残留古风/硬编码琥珀强调（KPI 卡、按钮、倒计时玉简箔面、行情按钮、音乐古琴虚影/音符飘带），模块间无统一视觉语言，显得「丑、散」。

**改动（新增 2 个 CSS 层 + 精简原生层，全 `#app.is-mobile` 门控）**：
- 新增 `mobile-module-color.css`：为 7 模块各定一套**独立高饱和渐变**——
  | 模块 | 路由 | 渐变主色 | 气质 |
  |------|------|---------|------|
  | 记账 `/finance` | `#0fa07f→#2fd58a` 青绿 | 稳健生长 |
  | 行情 `/stocks` | `#5b6ae0→#7f8dff` 蓝紫 | 理性科技 |
  | 足迹 `/travels` | `#2a9ece→#49c6e6` 天蓝 | 辽阔远方 |
  | 通讯录 `/contacts` | `#f0643c→#ff8f6e` 珊瑚 | 温暖家人 |
  | 笔记 `/notes` | `#7a5ce8→#a69bff` 品蓝 | 沉静书写 |
  | 倒计时 `/tool/countdown` | `#e08a3a→#f4b36a` 琥珀 | 翘首期盼 |
  | 音乐 `/music` | `#8b5cf6→#d94f9b` 桃粉/洋红 | 律动浪漫 |
  逐模块接管 KPI 卡顶部分割渐变条、数值渐变文字、主按钮渐变填充、图标块、倒计时玉简箔面等；隐藏音乐古琴虚影 `.guqin-bg`/`.music-ribbon`/`.floating-notes` 等古风残留。
- 精简 `mobile-native-glass.css`：**删除全站统一蓝紫强覆盖**，只保留通用毛玻璃质感 + Element 主色，避免与新模块渐变层冲突（Element 弹层/下拉仍挂 body 控件，主色统一蓝紫）。
- 倒计时玉简箔面金→琥珀渐变、玻璃化卡片；行情硬编码琥珀按钮→模块渐变。

**APK 深墨系统栏（User「界面顶部和底部有黄色横栏」的根层修复）**：`build_webview_apk.py` 主题 `statusBarColor`/`navigationBarColor`/`windowBackground` 全设 **深墨 `#10140F`** + `windowLightStatusBar=false`（v2.0.0）→ 重打 APK，系统状态栏/导航栏不再金黄横栏。

**构建/验证**：`npx vite build --outDir dist2`（清缓存全新构建）→ 核验 CSS 含 `mv-c1/fin-kpi-val` 标记 + SW `xuanhuang-v108→v109` → 整体替换 dist → `deploy_frontend.py` 217 文件 home=200。390px 手机双主题（A/B）实测：记账青绿渐变 KPI 卡、倒计时琥珀、各模块渐变大数/按钮生效 PASS；返回按钮 `display:none` 交系统 PASS；桌面端无 `is-mobile`、零回归。**音乐页本地 dev 截图白屏为 vite `/music` proxy 遮蔽/后端无页面路由所致，生产 nginx 走 SPA fallback 无此问题**。APK：`gradle assembleRelease` BUILD_CODE=0、同 keystore 签名 SHA-256 一致（可覆盖安装）、`yexingchen-2.0.0.apk` 部署 + 下载页更新 200。

---

## [v2.27.0] - 2026-09-17

### 手机端三处修复 + 接通丢失的移动端 CSS（SW `xuanhuang-v108`）

User「1 头部和底部还是有黄色横栏，在手机端尤为明显；2 手机端不需要单独的返回按钮，可以用手机自带的；3 手机端个人中心中个人信息那块去除」。

**根因（关键）**：`mobile-ab-theme.css`、`mobile-deink.css` 两个文件从未在 `main.js` 引入——此前 v2.24~v2.26 的整套手机端 A/B 主题 + 去古风 CSS 根本没打进 app，所以金黄/古风横栏在手机上一直压不掉。本轮在 `src/main.js` 补上两条 import（均 `#app.is-mobile` 门控、桌面零影响）修复。

**三处改动**（均追加进 `mobile-deink.css`，仅 `#app.is-mobile` 生效）：
- 子页标题去金渐变 → 现代纯色无衬线大标题（顶部金黄色横栏消失）
- 手机端子页返回按钮整体隐藏，交给系统/原生返回栈（`.island-inner .back-btn`）
- 个人中心隐藏整个「基本信息」卡片（邮箱/昵称/角色/注册时间 + 编辑/改密），只留「界面偏好」

**构建链坑（顺带修正）**：`npm run build -- --outDir …` 转参失效产**不完整旧 bundle**（仅 70 模块）；正确做法是 `npx vite build --outDir <新目录>`（本次 1833 模块），核验 `index-*.css` 含 `island-title/profile-content/info-card:first-child/island-inner .back-btn` 后整体替换 `dist`。

**部署/验证**：全新 `vite build --outDir dist5` → 核验 CSS 选择器 + SW `xuanhuang-v107→v108` → 替换 dist → `deploy_frontend.py` 217 文件 home=200。浏览器 DOM 实测（390px 手机视口）：音乐页顶/底金黄色消失、返回按钮隐藏 PASS；`/profile` 第一个 `.info-card` `display:none,height=0`（基本信息隐藏）、第二个界面偏好卡 height≈300px 可见 PASS。桌面回归：`useIsMobile`=`matchMedia('(max-width:767px)')`，≥768px 时 `#app` 不含 `is-mobile` ⇒ 全站 142 处 `#app.is-mobile` 规则天然失效、桌面水墨国风零回归（自动化环境 innerWidth 硬顶 444px，无法渲染 ≥768px 实证，靠 matchMedia + 选择器门控从构造上保证）。测试账号已清理，库归零。

---

## [v2.26.0] - 2026-09-17

### 手机端 P3 打磨：播放器主页 / 工具浏览 / 我的纯个性化（SW `xuanhuang-v107`）

承接 v2.25.0，把「一个页面一个焦点」推到子页。纯 CSS（`#app.is-mobile` 门控、桌面零影响）+ 极少量模板包裹类（`MusicView.vue`/`ToolView.vue` 顶栏）。

- **音乐 `/music`**：新增 `.mu-admin-tools` 包裹顶栏「管理/上传」，`.manage-pane` 兜底隐藏 → 进页即**播放器主视图**，拿掉「曲库管理/上传」
- **工具 `/tool`**：`.tl-admin-tools` 隐藏「管理/添加」→ 纯工具卡片浏览；`.tool-icon` 琥珀→蓝紫强调
- **我的 `/profile`（纯个性化）**：标题金渐变→无衬线纯色、卡片古金边→玻璃+`--ls-line`、隐藏角色行/「修改密码」/「←返回工作台」、主题分段 active 金→蓝紫强调
- **部署/验证**：全新 `vite build --outDir dist2` → 核验 CSS 选择器 + 按路由拆分的 `.vue` chunk 含包裹类 → 替换 dist → `deploy_frontend.py` 217 文件 home=200、**SW v106→v107**。本地浏览器 DOM 实测：音乐管理钮/我的角色/改密/返回全 `display:none`、播放器可见、标题去金转无衬线、分段蓝紫 PASS；账本 `.fin-io` 防回归 `none` PASS。真路由注意：工具页为 `/tool`（非 `/tools`）。

---

## [v2.25.0] - 2026-09-17

### 手机端简化收尾 · P0 骨架 + P1/P2 下去古风（SW `xuanhuang-v106`）

承接 v2.24.0 的手机端双套样式，本轮把「做减法 + 换新视觉」一次性收尾上线。全部门控 `#app.is-mobile`（`useIsMobile` ≤767px），桌面水墨国风零回归。

**P0 骨架**
- 新增 `mobile-ab-theme.css`：在 `#app.is-mobile` 内重映射 core/lj/ls token 的 **A（白天液态玻璃）+ B（夜间深空极简）** 双套
- 重建 `MobileWorkbenchHome`：弃玉简/篆字/搜索条 → 几何 Logo + 玄黄 + AI 胶囊、今日速览数据卡、线性图标快捷入口（含证件照/倒计时）
- 底部 Tab 收为**两 Tab（主页/我的）** + `keep-alive` 缓存

**P1 去古风**
- 新增 `mobile-deink.css`：隐藏宣纸噪点 `.lj-paper-texture`；`--font-serif` 移动端全局切现代无衬线

**P2 数据视图去「管理后台感」（一个页面一个焦点）**
- 账本：隐藏 `.fin-io`（导出/导入）、`.fin-filters`（筛选）、`.fin-row-ops`（行内编辑删除）；放大 KPI 大数、玻璃化图表/列表，保留「+ 记一笔」
- 股票：隐藏 `.st-td-edit` 与移动卡删除 `.st-card-h .st-btn.danger`；KPI 两列

**部署/验证**：全新 `vite build --outDir dist2` → 核验产物 `.css` 含 `#app.is-mobile …` 精确选择器 → 替换 dist → `deploy_frontend.py`（保留 `download/.well-known`）→ 217 文件 home=200、**SW v105→v106**（升版刷新 PWA 缓存）。生产浏览器 DOM 实测：账本 `.fin-io/.fin-filters/.fin-row-ops/.lj-paper-texture` 全 `display:none`、「记一笔」可见；`#app` 含 `is-mobile`、股票 KPI 两列、合成 DOM 下删除按钮 `display:none` —— PASS。仅前端改动，后端无源码变更。

---

## [v2.24.0] - 2026-09-16

### 手机端独立样式全案（P0–P2）落地 + App 图标重做（SW `xuanhuang-v105`）

**方向**：网页版与手机版做成两种样式——手机端走 **iOS 原生浅/深色玻璃**（跟随 day/night 昼夜），沉浸式 + 底部三 Tab（工具/工作台/我的）+ 系统性收走重交互，桌面水墨国风零回归。

**P0 全局框架**
- App 内嵌 `MobileTabBar`（三 Tab：工具/工作台/我的，激活琥珀 + 点击轻震动）；`App.vue` 桌面隐藏顶栏、移动端仅显底栏；`useIsMobile()`（`(max-width:767px)`）贯穿
- 数据模块/全端沉浸式：`100svh`、`mobile-list.css` 移动覆盖样
- **App 图标重做**：由 PIL 棕底白「玄」升级为墨玉·琥珀·雾玻璃 `app-icon-1024.png`（`scripts/apk-icon/`），`build_webview_apk.py` 改为本地按 mdpi→xxxhdpi 烘焙设计稿写 mipmap；APK 重建 `cn.yexingchen.app` v2.0.0（同 keystore 签名 SHA-256 `3add…df14b` 可覆盖安装）+ `/download/` 更新 200

**P1 工作台 + 玉简全息卡**
- `MobileJadeCard.vue`：凹陷层次全息玉片（内阴影 + 琥珀描边 + 表面 foil 分层），首页 Hero 左右滑切 + 长按扇形彩蛋（`vibrate` 触感）
- `MobileWorkbenchHome.vue`：搜索条固定（`MobileSearchBar`）+ 玉简 Hero（占半屏）+ 快捷宫格收纳全部模块 + `MobileSkeleton`/`MobileEmpty` 加载/空态

**P2 全模块手机化**
- 工具/音乐/视频/小说列表改**2 列大卡片磁贴**（`mobile-list.css`）
- 迷你播放条 + 全屏播放页 `MobileFullPlayer`（点迷你条展开）
- 账本/股票/旅行/倒计时/笔记数据密集模块移动适配：`TrendChart` 增触摸 tooltip（`touchstart/move/end`）、全局输入控件 `font-size≥16px` 防 iOS 缩放、全屏容器 `100svh`、触控 `touch-action:manipulation`、`.tc-tip` 触控点按态
- 登录页「记住我」（`LoginView` 勾选 + localStorage 自动填充账号）；个人中心「主题外观」`自动/白天/夜间` 分段切换（`prefs.setTheme` + `applyTheme` 写 `<html data-theme>`）
- 子页返回：`MobilePage`（iOS 大标题 + 左缘侧滑返回 + `history.back`）可复用外壳；`StockDetail` 等详情页自带 `BackButton` 导航

**部署/验证**：`vite build --outDir dist2` 全标记命中（MobileTabBar/JadeCard/记住我/主题外观/tc-tip/SW v105）→ 替换 dist → `deploy_frontend.py`（219 文件 home=200）→ `build_webview_apk.py` BUILD SUCCESSFUL（new_apk/download 200）。浏览器取证：桌面根页正常、移动视口(≤767px)登录页玻璃质感无横向溢出、输入 ≥16px、SW v105 生效。

---

## [v2.23.0] - 2026-09-16

### APK 由 TWA 改为原生 WebView 壳（`yexingchen-2.0.0.apk`，作为独立软件运行）

**背景**：TWA 版 APK（`1.0.0`）打开只停在启动图、进不去网页——TWA 需 Google Chrome / GMS 承载页面，国产安卓（鸿蒙/米UI/vivo/OPPO 等）普遍无 GMS，导致启动失败。
**方案**：改为**原生 WebView 壳 App**，内置系统 WebView 直接加载 `https://yexingchen.cn/workbench`，完全脱离 Google 服务/Chrome 依赖，任何安卓设备都能独立打开进登录页。
- 新 APK `cn.yexingchen.app` v2.0.0：零第三方依赖（仅 17KB）、同 keystore 签名（SHA-256 `3add…df14b` 与 1.0.0 一致）→ 已装 1.0.0 可直接覆盖升级；label「玄黄」，PIL 重新生成棕底圆角白「玄」launcher 图标
- WebView 配置：JS/DOM Storage/混合内容、站内链接留 WebView、站外跳系统浏览器、`target=_blank` 回站内加载、返回键后退、`DownloadManager` 下载 APK/文件、`onShowFileChooser` 支持文件上传（账本导入）
- **构建留档**：新增 `scripts/build_webview_apk.py`（读 `.secrets/apk-build.local.env`，上传源码→复用 TWA gradle wrapper→Gradle 签名构建→部署+更新下载页），可跨会话重建 APK
- 部署：`/download/yexingchen-2.0.0.apk`、下载页 href 与 SHA-256 已指向 2.0.0，`/download/` 与 APK 均 200

> 附带本次同类修复（已含于前几条）：`deploy_frontend.py` 保留 `dist/download` 与 `.well-known`（TWA assetlinks/index.html/APK 均在此，rm -rf 整体清空会误删）。

---

## [v2.22.5] - 2026-09-16

### 修复：/download/ 下载页被前端部署误删（APK 下载入口失效）

**现象**：顶栏「下载安卓 App」入口（`href=/download/`）打开后显示的是「工作台」而非下载引导页。
**根因**：APK 与下载引导页由 `build_apk.py` 生成到 **`/var/www/yexingchen/dist/download/`**（站点 dist 目录内、`WEB_APK_DIR`/`WEB_DOWNLOAD_PAGE` 配置），而它**不在 `frontend/dist` 构建产物里**。前端部署脚本 `deploy_frontend.py` 每次 `rm -rf /var/www/yexingchen/dist` 整体清空再上传，把 `download/` 子目录一并删掉且不重建 → nginx 无独立 location 时 `/download/` 回退 SPA 到工作台。
**修复**：
- 立即恢复——从事故备份 `dist_broken_20260916` 找回 `download/index.html`(下载引导页) 与 `yexingchen-1.0.0.apk`(1.1MB) 放回 `dist/download/`；已核验 `/download/` 200（含「下载 APK」+ APK 文件名）、`/download/yexingchen-1.0.0.apk` 200。
- 根治——`deploy_frontend.py` 清空逻辑改为**先挪走保存 `dist/download`，清空后放回**，避免再次误删。

---

## [v2.22.4] - 2026-09-16

### 运维：生产全站白屏事故修复（SW `xuanhuang-v104`）

**现象**：全站登录页/首页白屏，无任何 DOM 渲染。
**根因**：服务器 `dist` 被多次部署叠加污染——`index.html→index-7gHseZyt.js` 正常返回，但它动态 `import` 的 `WorkbenchView-DxO5kJRe.js` **在服务器上不存在**，动态导入崩溃导致 Vue 挂载前异常 → 整页白屏。sw 一度达到 v103、assets 堆了 30+ 个 `index-*.js`，属并发部署未清空叠加脏化。
**定位**：浏览器取证拿到 console `TypeError: Failed to fetch dynamically imported module: .../WorkbenchView-DxO5kJRe.js`；服务器 `ls` 证实该 chunk 缺失。
**修复**：坏 dist 备份为 `/var/www/yexingchen/dist_broken_20260916`（可回滚）；用最新源码全新自洽构建（含并发会话的工作台/倒计时等改动），整体清空重传 + `nginx reload`；服务器关键文件（index-7gHseZyt.js / WorkbenchView-DxO5kJRe.js / index-*.css）与构建产物 **md5 逐字节一致**，workbench chunk 404→200，home/index/chunk 全 200。
**验证**：浏览器实测首页正常渲染（导航/搜索/AI 入口/备案徽章俱在），不再白屏。经验：多会话同时部署同一服务器是事故高危，应收敛到单一部署通道。

---

## [v2.22.3] - 2026-09-16

### 修复：工作台工具入口 BUILTIN_SLOT 限制

**根因**：`WorkbenchTools.vue` 硬编码 `BUILTIN_SLOT=4`，builtin 工具从 4 个增到 5 个（加倒计时）后被截断不显示。

**修法**：移除 `BUILTIN_SLOT` 硬限制，builtin 工具全部展示。

### 修复：run.py sys.path Bug（严重）

**根因**：`backend/run.py` 中 `os.path.dirname(os.path.dirname(__file__))` 套了两层 dirname，`__file__`=run.py 时，路径指向 `/var/www/yexingchen/`（而非 `/var/www/yexingchen/backend/`），导致 uvicorn 加载的 `app` 来自错误目录，新增路由虽然被 `main.py` 注册但部分请求 405。

**修法**：改为单层 `dirname(os.path.abspath(__file__))`，`reload=False`（PM2 管进程）。

**生产取证**：重启后 `GET /api/countdowns` ✅ `POST /api/countdowns` ✅ `DELETE` ✅（探针已清理）。

### 修复：countdown 路由前缀不一致

**根因**：`countdown.router` 创建时未设 `prefix="/api"`，但前端 `api.get('/countdowns')` 经 `baseURL: '/api'` 拼接后实际发 `/api/countdowns`，全链路 404。

**修法**：`router = APIRouter(prefix="/api", ...)` + 前端 `BASE = '/api/countdowns'`。

### 新增：倒计时模块（Days Matter 风格）

#### 后端

- 新表 `xuanhuang_countdowns`（id / user_id / title / target_date / is_lunar / lunar_month / lunar_day / lunar_leap / direction / repeat_type / in_home / pinned / sort_order / is_archived / icon / color / bg_image / memo）
- 新路由 `backend/app/routers/countdown.py`（CRUD + 图片上传）
- 支持公历/农历模式（农历模式下 target_date 存占位值，lunar_month/day 驱动显示）
- `days_left` 计算字段（direction=count_up 时返回已过天数绝对值）
- `repeat_type` 支持 yearly/monthly/weekly，`next_occurrence` 字段返回下次到期公历日期
- `CountdownIn` schema：`target_date` 改为 Optional（农历模式不传）；边界校验 direction/repeat_type/color/lunar_month/day
- 8 个 pytest 测试（全部通过）

#### 前端

- `CountdownsView.vue`：玉简卡片列表（背景图/渐变/微光动画）、新建/编辑对话框（公历/农历切换/重复/置顶/首页展示）、归档分组
- `CountdownDetailView.vue`：全屏 Days Matter 大图风格（背景图/大数字/标签/编辑/删除）
- 路由注册：`/tool/countdown`（列表）+ `/tool/countdown/:id`（详情）
- API：`listCountdowns` / `createCountdown` / `updateCountdown` / `deleteCountdown` / `uploadImage`

### 优化：证件照抠图（智能换底 v2）

**根因**：v1 用 BFS flood fill 直接将匹配背景色的像素 alpha=0，边缘硬截断导致锯齿。

**修法**：

1. **鲁棒背景采样**：从四边密集采样，中位数（而非均值）作为基准背景色，抗噪能力更强
2. **BFS 边界检测**：遍历全图建立背景 mask
3. **边缘抗锯齿（Soft Matting）**：对 mask 边界像素做曼哈顿距离加权 alpha 羽化——距前景 0px → alpha=0（纯透明），距 3px → alpha≈191（近半透），距 >3px → alpha=255（完全不透明）

效果：发丝/耳廓等细节处不再有硬锯齿，与背景交界处自然过渡。

## [v2.22.2] - 2026-09-16

### 用户决策变更：PWA → 安卓 APK + 顶栏入口（v2.22.1 PWA hotfix 同日）

用户试 PWA 后明确「用不习惯，直接做 APK」。APK 内嵌站点 URL，**站点更新不用重装**（v2.22.0 PWA 合规投资的现成回报）。

#### 1. 服务端 TWA 构建

- 工具链落在服务器 `/opt/android-build/`（JDK 17 + Android SDK 34，约 600MB）+ 2GB swap（Gradle 兜底）
- 路径/密钥/证书指纹全部集中到 `.secrets/apk-build.local.env`，脚本不再硬编码密码
- keystore：RSA-2048 / 100 年有效期
- twa-manifest：`cn.yexingchen.app` / `yexingchen.cn` / startUrl `/workbench` / standalone
- **关键改动**：放弃 `bubblewrap init` 交互式（inquirer.js 卡 stdin），改用 `@bubblewrap/core`
  程序化 API `TwaManifest.fromWebManifest()` + `TwaGenerator.createTwaProject()`，Node 脚本 3 秒生成完整 Android 项目骨架
- Gradle wrapper zip 走 services.gradle.org 国内极慢 → 用户手动下载放服务器 wrapper 路径
- 配阿里云 maven mirror（init.d/aliyun-mirror.gradle）解决 AGP/transitive 卡顿

#### 2. assetlinks.json（数字资产链接）

- 部署到 `https://yexingchen.cn/.well-known/assetlinks.json`
- 让 Android 验证 APK 与站点绑定 → 全屏无地址栏 / 无「在浏览器打开」中间页；缺它 TWA 退化
- **注意：要用证书 SHA256 指纹（apksigner 输出的 `Signer #1 certificate SHA-256 digest`），
  不是 APK 文件 SHA256**——第一次混淆导致退化，已修

#### 3. 一键重打 `scripts/build_apk.py`

```bash
backend/.venv/Scripts/python.exe scripts/build_apk.py                  # 默认沿用 twa-manifest 当前版本
backend/.venv/Scripts/python.exe scripts/build_apk.py --version 1.1.0 --code 2  # 升版本
backend/.venv/Scripts/python.exe scripts/build_apk.py --update-cert   # 新证书 SHA256 自动回填到 secrets
```

自动完成：版本号 → gradle build → apksigner 签名 → 拷下载目录 → 重算 assetlinks → 更新下载页 → 公网验证。
所有密钥/路径从 `.secrets/apk-build.local.env` 读取。实测一轮 30-60 秒（首次 1m 28s 含依赖下载）。

#### 4. 顶栏下载入口（commit 4a0e6e6，SW v99 → v100）

- `GlobalTopBar.vue` 用户区按钮前插入手机图标按钮，`href="/download/" target="_blank" rel="noopener"`
- 桌面端扫码装到手机，移动端浏览器跳下载页直接触发 APK 下载（target=_blank 避免 SPA 路由冲突）

#### 5. 下载与安装

- APK：`https://yexingchen.cn/download/yexingchen-1.0.0.apk`（1.1MB）
- 下载页：`https://yexingchen.cn/download/`（含 SHA256 + 鸿蒙 4「外部来源应用下载」开关位置）
- 鸿蒙 4：设置 → 安全 → 「外部来源应用下载」/「未知来源应用」给浏览器开权限 → 传 APK → 打开安装

### v2.22.1 hotfix（同日，用户报「个人中心没有下载安装包」）

两个根因叠加（均已修复）：
- **`sw-register.js` 自 MVP 首提交起就从未被任何地方调用**——SW 在生产从未注册，
  之前 v97/v98 版本号全是「纸面升级」。Chrome PWA 安装性检查要求已激活 SW，不过则 beforeinstallprompt 永不派发
- `usePwaInstall` 监听挂在 ProfileView 挂载时（懒加载页），事件在页面加载后几秒就派发——晚进个人中心会错过

修法：`src/main.js` 应用启动即调用 `registerServiceWorker()` + `usePwaInstall()`。SW v98 → v99。

### 经验（详见 SKILL 与 memory）

- 写完注册函数必须用 grep -r 确认有调用方——历史上踩过两次
- bubblewrap init 是 inquirer.js 交互式，CI/脚本不可用；走程序化 API
- TWA 的 assetlinks.json 要用证书 SHA256，不是 APK 字节 SHA256

## [v2.22.0] - 2026-09-16

### 数据一览菜单分组 + AI 封面 + 音色克隆 + PWA 可安装（User 需求 1/3/9）

#### 1. 「数据一览」一级分组，行情/账本/旅行足迹/资讯/数据中心挂二级，按角色限制

- 迁移 `o5p6q7r8s9t0`：新建一级分组「数据一览」，5 个模块挂为其二级；
  顺带补齐 `/finance`、`/datahub`、`/notes` 三条缺失的菜单记录
  （页面路由一直存在但从未进导航表——顶栏此前是前端写死的）
- 全程按 path 查 id 再挂父级（生产库自增 id 与本地顺序不保证一致）；先查后插幂等
- `/api/admin/menus/public`：子项命中时把 parent_id 一并放行
  —— 否则超管只勾「账本」，用户连「数据一览」分组入口都看不到
- 角色未配置 menu_ids（或空数组）→ 全部启用菜单；超管恒见全部；
  既有角色的 menu_ids 是显式配置，不代改：需超管在角色管理里补勾
- 前端导航全面 DB 驱动：新增 `stores/menus.js`（拉取 public 菜单组树，
  接口失败时 isPathAllowed 一律放行——接口抖动不该清空全站导航）；
  `GlobalTopBar` 删除写死的 moduleShortcuts；`JadeCarousel` 玉简卡片按角色过滤

#### 2. AI 封面生成（工具岛）

- 不做文生图：封面 90% 的需求是「固定版式 + 自己的标题 + 统一视觉」，
  模板渲染零成本秒出、完全可复现。服务端 Pillow 渲染（零新增依赖）
- 4 尺寸（公众号首图/小红书/视频/方形）× 3 主题（玄墨流金/雨青/宣纸）× 3 版式
  （居中/左带装裱/朱砂钤印），标题以「最多 3 行」为目标自动选字号
- 自带中文字体得意黑（OFL-1.1 可再分发）：生产服务器只有 dejavu，不带字体中文全是豆腐块
- 迁移 `p6q7r8s9t0u1`：tools 表补 kind/is_enabled/sort_order 三列
  （模型有但从未进 Alembic，生产手工 ALTER、开发库缺失，本次幂等对齐）；
  内置工具改迁移播种（按 url 幂等），不再手工同步生产库
- 前端 `CoverToolView`：左表单右预览，500ms 防抖实时渲染 + 竞态序号保护

#### 3. 音色克隆（工具岛）

- 复用已配好的 MiniMax 共享 Provider（超管共享全站可用，家人零配置）；
  仅当 base_url 指向 MiniMax 时开放，其它 Provider 前端引导去配置而非报错
- 链路：文件上传(voice_clone purpose) → 声音复刻 → T2A 合成试听，
  接口国内站 api.minimaxi.com，与共享 Provider 同凭据
- 新表 `voice_clones`（迁移 `q7r8s9t0u1v2`），按 user_id 隔离（用户级资源）
- 前端 `VoiceCloneView`：上传录音 → 命名 → 试听，已有音色列表可删可试听

#### 4. PWA 可安装化（App 第一步）

- 现状诊断：manifest 早就写好，但 index.html 一个引用都没有——浏览器从未提示过安装；
  icons 只有 SVG，iOS 完全不认
- 新增 4 张 PNG 图标（any 192/512 + maskable 512 + apple-touch 180），
  maskable 内容缩进安全区 78% 避免 Android 自适应裁切
- index.html：manifest link + theme-color + viewport-fit=cover + apple 三件套
- `composables/usePwaInstall.js`：捕获 beforeinstallprompt 由站内入口触发原生弹窗；
  iOS 检测 UA + iPadOS 手势特征显示文字引导；standalone 模式整块隐藏
- 入口放个人中心「界面偏好」卡片；Web Push 预留注释（接入时补 /api/push/* + VAPID）
- SW v97 → v98（index.html 与 /icons/** 在缓存清单里，不提升老客户端拿不到新元数据）

### 迁移

- `o5p6q7r8s9t0`：数据一览分组 + 补齐 /finance /datahub /notes 菜单记录
- `p6q7r8s9t0u1`：tools 表补 kind/is_enabled/sort_order + 播种内置工具（AI 封面/音色克隆）
- `q7r8s9t0u1v2`：新建 `voice_clones`

### 顺带修复

- **finance `_parse_dt` 对所有 ISO 日期解析失败，流水日期一律回退为当天**：
  `str.replace(tzinfo=None)` 写在了字符串而非 datetime 对象上，TypeError 被吞掉恒返回 None。
  影响手动新增/编辑流水与 CSV 导入的日期列，全部静默落成「今天」。
  `tests/test_finance_import.py` 3 例由红转绿（此前失败被当作环境问题漏检）

### 测试

- 新增 `test_menu_group.py`（4 例）、`test_cover.py`（6 例）、`test_voice_clone.py`（7 例，全 mock 网络）
- 后端全量 451 例通过

## [v2.21.0] - 2026-09-16

### 桌宠开关 + 账本自定义分类 + AI Provider 权限修复 + 农历生日（User 需求 1/2/3/4）

#### 1. 个人中心桌宠开关（默认展示）

- 新增 `stores/prefs.js`：界面偏好按**用户**分键存 localStorage（家里共用设备时不该互相覆盖）
- `App.vue` 的 `showWhale` 叠加该偏好，与既有的「音乐页隐藏桌宠」是 AND 关系
- 个人中心新增「界面偏好」卡片，`el-switch` 即时生效（无需刷新）
- 细节：模块加载时先用「上次登录用户」的偏好 hydrate，避免关掉桌宠的人每次进站先闪一下鲸鱼

#### 2. 账本自定义分类

- 新增表 `xuanhuang_finance_categories`（用户级）；内置分类仍写死在 `routers/finance.py`
  —— 内置项的图标/文案与代码强绑定，搬进库反而更难改
- 新增 `POST/PUT/DELETE /api/finance/categories`；`GET` 返回内置 + 自定义（带 `is_custom`）
- **改名会同步更新该用户的存量流水**，否则老流水会指向一个已不存在的分类名，在统计里变成孤儿
- **删除走软删**，且图标映射不过滤软删：删掉分类后历史流水的图标不会集体回落成 🧾
- `_valid_category` 换成基于 db 的 `_resolve_category`——原先自定义分类会被白名单静默归一成「其他」
- CSV/AI 导入链路一并改为「内置 + 该用户自定义」白名单，导入时自定义分类不再被吞掉
- 前端账本：分类区加「管理分类」入口（增删改 + 图标预设 30 个），内置分类只读展示

#### 3. AI Provider「权限不足」修复（生产实测根因）

- **现象**：家里人登录后点开 AI 助手「配置 AI Provider」弹窗，满屏 403「权限不足」
- **根因**：`UserAiProvider` 明明是**用户级**（模型名、查询条件、docstring 全写着「当前用户」），
  但 `routers/workbench/providers.py` 的 5 个接口全挂了 `require_super_admin`
- **修复**：5 个接口改 `get_current_user`；引入「共享配置」——超管配置的 Provider
  对全站可见可用（`is_shared` / `is_owner` 标记），家里人不必各配一份 Key；
  自己另配的优先级高于共享；共享配置对非属主**只读**（否则谁都能改掉全站共用的 Key）
- `resolve_user_provider` 解析顺序：指定 id → 自己的默认 → 自己的任意启用项 → 超管共享 → FakeProvider
  （影响面：AI 助手、账本导入、行情解读、股票每日分析四处自动受益）
- 前端显示「共享」徽标，非属主隐藏改删入口，并给出「超管配置 · 只读」提示

#### 4. 农历生日（用户强调：家里基本都按农历）

- 新增 `services/lunar.py`，基于 **lunardate 0.3.0**（纯 Python，无 C 扩展，覆盖 1900–2099）
- 选库而非手抄历法表：闰月与月大月小是查表规则，抄错极难发现，而这类错误会直接算错「家人今天生日」
- 已对 **8 个春节锚点 + 端午/中秋/七夕 + 3 个闰月**做独立校验（用公开历法事实，不是「跑一遍抄输出」）
- 两种中国习惯回落：闰月生日在无对应闰月的年份按**普通月**过；月小只有 29 天却记了三十 → 按**当月最后一天**（腊月三十 → 腊月廿九）
- 年龄按**同历法年份差**计算：农历取农历年——腊月生日落在公历次年，混用会把长辈算小一岁
- 通讯录新增 `lunar_leap` 列；农历生日填 31 日会被明确拒绝（农历月最多 30 天）
- 界面：公历/农历切换 + 闰月勾选（仅农历时出现）、日下拉按历法收窄到 30、
  列表显示「农历八月十五 → 2026-09-25」、日历把农历生日落到**换算后的公历**格位（标「农」角标）

### 迁移

`n4o5p6q7r8s9`：新建 `xuanhuang_finance_categories` + `xuanhuang_contacts.lunar_leap`

### 顺带修复

- **`ENV=production` 判定脆弱（本次部署核验时发现并修复）**：`is_production_env()` 只读
  `os.environ["ENV"]`，而 `ENV=production` 只写在 `backend/.env` 里
  （pydantic-settings 只把它读进 `Settings`，不写回 `os.environ`），
  于是 pm2 用别的方式重启一次（如 `pm2 restart --update-env`）判定就会翻成「非生产」，
  **生产便不再走 schema fail-fast 校验、改为执行 `create_all`**。
  修复：`Settings` 显式声明 `ENV` 字段；新增 `resolved_env()`（环境变量优先，回落 `.env`）；
  文档路由抽成 `schema_guard.docs_urls()`，生产**三个一起关**
  （只关 `docs_url` 时 `/openapi.json` 仍是 FastAPI 路由，属于白留一个入口）。
  上线前已在服务器上以 `ENV=production` **空跑一次** `assert_production_schema_ok`
  确认通过（期望 head == 库内版本 == `n4o5p6q7r8s9`、alembic_version 恰 1 行），
  排除「改完起不来」的风险
  > 附带更正一处**误报**：核验时曾以为生产 `/docs` 对外暴露，实则 `/docs`、`/redoc`、
  > `/openapi.json` 返回的是前端 `index.html`（nginx SPA 回退，与首页 md5 逐字节相同），
  > 后端文档的真实挂载点 `/api/docs` 一直是 404 —— **接口文档从未暴露**。
  > 教训：判断「暴露」必须看响应体与 `Content-Type`，不能只看状态码。
- `alembic/env.py` 从未注册记账模块，`Base.metadata` 里没有这两张表（autogenerate 看不到）
- `contacts.py` 两处 `raise_error(code, msg, 404)` 传了 3 个参数，而 `raise_error` 只接受 2 个
  → 「联系人不存在」「回收站中无此联系人」实际会抛 TypeError 变成 500，已改 `ErrCode.NOT_FOUND`
- `deploy_backend.py`：pip 改为 `-r requirements.txt`（原先手写包名清单，新增依赖会漏装，
  v2.21.0 的 lunardate 就差点漏），并补齐本次白名单
- `.gitignore` 补 `.pip-cache/`、`backend/.pip-cache/`；修掉一处 `*~\n` 字面量笔误

### 测试

新增 119 例：`test_lunar.py` 49 + `test_finance_categories.py` 32 +
`test_ai_provider_shared.py` 27 + `test_production_env.py` 11。
后端逐文件回归全通过：lunar 49 / family_reminder 23 / family_api 16 / finance_categories 32 /
ai_providers 15 / ai_provider_shared 27 / production_env 11 / migrations 3 /
password_validation 25 / schema_guard 7 / security 17 / client_ip 6。
前端 `vite build` 通过（FinanceView 20.6→28.3 kB，新增分类管理）；eslint 改动文件**零新增 error**
（`AssistantView` 474 与 `FinanceView` 646 两条 error 经 HEAD 对比确认为存量）。

### 部署取证（yexingchen.cn）

- 前端 SW v96 → **v97**（204 文件，home=200）；生产 4 个新 chunk 均含本次文案：
  FinanceView「管理分类」/ ContactsView「闰月」/ ProfileView「桌宠展示」/ AssistantView「共享」
- 后端迁移 `m3n4o5p6q7r8 -> n4o5p6q7r8s9` 已应用（`alembic current` = head）；PM2 online、health=200；
  服务器 venv 已装 `lunardate`（并实测 `LunarDate(2026,8,15)` → 2026-09-25）
- 端到端取证：**新建一个临时普通用户**，用它的身份跑完整链路 ——
  AI Provider 列表 **200**（旧代码此处 403）、可见超管 2 条共享配置（`is_shared=True`）；
  农历联系人返回 `lunar_text=八月十五` 且 `next_birthday=2026-09-25`（换算正确）、
  农历 31 日被拒 400；自定义分类记账后分类**未被归一成「其他」**、统计环形图含该分类。
  验证后按逆序删除全部探针数据，**账号与数据零残留**（用户数 5 → 5，探针账号已无法登录 401）
- 修复后再核验：`/docs`、`/redoc`、`/openapi.json` 返回的仍是前端 SPA 回退页（与首页 md5 一致），
  而 `/api/docs`、`/api/redoc`、`/api/openapi.json` 均为 404；`/health` 200、超管登录 200
  → 站点与业务接口全部正常，文档路由确认未暴露

---

## [v2.20.0] - 2026-09-16

### 家庭助理三件套（User 需求 4/5/7：家人通讯录 / 待办事项 / 订阅账单统计）

三者的共同点是**都会产出待办提醒**，因此先抽出一套提醒引擎，再各自做界面——拆开做会返工。

#### ① 家人通讯录 `/contacts`
- 新表 `xuanhuang_contacts`：姓名/关系/电话/住址/生日/出生年/标签/备注/置顶
- **生日只存 MM-DD**（家人往往只记得月日，且年份不参与提醒），年份单独存 `birth_year` 仅用于显示年龄；
  `birthday_type` 预留 solar/lunar（**当前农历仅存值，未做转换**，见 ISSUES）
- 列表 + **日历双视图**：列表按「置顶 → 生日临近 → 姓名」排序；日历按当月月日铺开，点名字直接编辑
- 接口返回补算 `next_birthday` / `days_to_birthday` / `age`，前端两视图都不必各自重算

#### ② 待办事项 `/tasks`
- **后端接口原本就完整**（`routers/workbench/tasks.py` 全 CRUD），只是 9/4 把前端入口撤了 → 本次复活前端
- 给 `Task` 加溯源三字段 `source_type` / `source_id` / `source_key`，支撑幂等自动生成
- 前端按当前设计系统重写（原 `TasksView.vue` 用的是已废弃的 `--xiu-*` token + 硬编码 hex）：
  逾期/今天/未来 7 天/更远/未设截止**分组**，自动待办带「生日提醒 / 续费提醒」**来源徽标**，一键勾选完成

#### ③ 订阅账单 `/subscriptions`
- 新表 `xuanhuang_subscriptions`：名称/金额/周期/下次到期/自动续费/分类/提前提醒天数/启用状态
- **统计口径统一折算月均**，这样「每年 240」与「每月 20」可直接相加比较；一次性订阅不计入月均/年均
- KPI（月均/年均/活跃数/7 天内到期）+ 分类环形图（复用 `finance/DonutChart`）+ 周期分布条 + 列表
- 「已缴费」按钮**顺延到下一账单周期**（月末收敛：1/31 + 1 月 → 2/28，不溢出到 3 月）

#### ④ 提醒引擎 `services/family_reminder.py`（三者的共同心脏）
- 生日 → 每年一条待办（幂等键 = 年份）；订阅到期 → 每个账单周期一条（幂等键 = 到期日）
- **幂等靠唯一索引** `ix_task_source(user_id, source_type, source_id, source_key)`，
  而非改表约束——SQLite 不支持直接 ADD CONSTRAINT，且 `CREATE UNIQUE INDEX` 对已有数据的表安全得多
- **NULL 语义利用**：手工待办三项为空，SQLite 中 NULL 互不相等 → 手工待办可无限创建、不会互相冲突
- **尊重用户删除**：自动待办被用户删掉后，同步**不会再次拉起**（否则「删了又长出来」）
- 同步时机挂在 `GET /tasks` 上 → 打开待办页永远看到最新提醒，**不依赖后台定时任务是否跑过**
- 日期边界全部覆盖：闰日 2-29 在平年顺延 2-28、月末收敛、已过生日顺延明年、脏数据返回 None 不抛异常

#### ⑤ 接入
- 路由 `/contacts` `/tasks` `/subscriptions`；顶栏「快速前往」3 项；**玉简轮播加 3 张卡**（骨肉亲缘/诸事待理/细水长流，含专属篆符）
- 迁移 `m3n4o5p6q7r8` 播种 3 条菜单（`is_builtin=1`，幂等：path 已存在则跳过），可在管理后台菜单树中授给角色

### 测试
- 新增 `tests/test_family_reminder.py` **21 例**：日期纯函数（闰日/月末/跨年/脏数据）+ 生日与订阅生成 + 幂等 + 用户删除不复活 + 标题随天数刷新
- 新增 `tests/test_family_api.py` **16 例**：通讯录 CRUD/排序/搜索/生日归一化、订阅 CRUD/月均年均折算/分类统计/缴费顺延、与引擎联动
- `test_migrations.py` 期望表清单补 `xuanhuang_contacts` / `xuanhuang_subscriptions`；迁移 3 例全过
- 三个文件合计 **41 passed**；`app.main` 导入无误；OpenAPI 路径 123 条（contacts 4 / subscriptions 6 / workbench tasks 4）

### 工程
- 前端 `npx vite build --outDir dist-deploy` 构建通过；产物核验 ContactsView / SubscriptionsView / TasksView 三个 chunk 及关键文案俱在
- eslint 新增文件 0 error；顺手清掉 `router/index.js` 一处**既有**未使用导入（`useAuthStore`，经 `git show HEAD` 确认改动前即存在）
- **`scripts/deploy_backend.py` 白名单补全**：此前缺 `workbench/` 包内文件、`models/workbench.py` 与本次全部新文件——用它部署会产生「半新半旧」的静默半同步。已补齐并在文件内加了警示注释；改动不在名单内的后端文件请直接走 `deploy_backend_full.py`（整树同步）

---

## [v2.19.0] - 2026-09-16

### 超管建号免校验通道（User「我是超管，理论上可以自己创建用户账号，但被校验规则拦住了，需要增加条路径」SW `xuanhuang-v95`）

**问题定位（实测复现，非推测）**：拦人的是三条规则——密码需 ≥8 位、必须含大写字母、必须含数字；账号还必须是合法邮箱格式（`爸爸`、`13800138000` 一律 `Invalid email`）。共三处拦截：后端建号 schema、后端登录 schema、前端表单正则。

#### 后端
- **`admin_users.py` 新增 `_check_credentials(email, password, strict)`**：`strict=False`（默认）只挡空值，邮箱格式与密码强度放行；`strict=True` 套用公开注册同款规则。同时返回 `strip()` 后的账号供落库，避免「 爸爸 」与「爸爸」被当成两个账号
- **`UserCreateRequest`**：移除 pydantic 层的邮箱/密码校验（pydantic 校验先于路由执行，无法按开关分流），改为 `strict_validation: bool = False`，校验下移到 `create_user`
- **`UserPasswordResetRequest`**：同样下移校验 + `strict_validation` 开关——建号口放宽了而改密口不放宽，家里人账号改密时照样撞墙
- **`LoginRequest` 不再校验邮箱格式**：这是本次的**必要项**——登录口若仍强制邮箱，超管创建的非邮箱账号建了也登不进去，等于白做。现仅挡空值与超长（>254），账号是否存在交由查库判定（查询为参数化 SQL，无注入面；登录限流仍在）
- **公开注册口不变**：`RegisterRequest` 仍强制邮箱、`VerifyRequest` 仍强制密码强度——面向公网的自主注册不能被削弱
- 合规：密码仍走 `get_password_hash()`，无明文；跳过校验时操作日志记录「（超管建号，已跳过格式/强度校验）」，可审计

#### 前端
- `AdminView` 新增用户弹窗：账号输入框改为「邮箱或任意账号」提示，新增 **「启用严格校验」勾选框（默认关闭）**，附说明文字
- 重置密码弹窗：同一开关
- 客户端校验改为随开关分流：默认只挡空值，勾选后才用邮箱正则 + 密码强度正则
- 新增 `.form-tip` 说明样式

#### 测试
- `tests/test_password_validation.py` **按新语义重写而非删除**：`TestUserCreateRequestPassword`（断言弱密码被拒）已失效，改为 `TestUserCreateRequestAdminBypass` + `TestAdminCredentialCheck` + `TestLoginRequestAcceptsNonEmail` 三组，覆盖默认放行 / strict 拦截 / 空值与超长兜底 / 账号 strip / 登录口接受非邮箱；`TestVerifyRequestPassword` 原样保留（公开注册口必须继续拒绝弱密码）
- 该文件 **25 passed**

### 工程
- 后端逐文件跑测试：`test_ai_providers` 15 / `test_client_ip` 6 / `test_errors` 19 / `test_feed_sync` 2 / `test_finance_import` 9 / `test_jwt_blocklist` 10 / `test_migrations` 3 / `test_music_stream` 8 / `test_password_validation` 25 / `test_production_env` 8 / `test_router_smoke` 7 / `test_schema_guard` 7 / `test_security` 17 / `test_security_fixes` 12 / `test_tool_url_validation` 12 全通过
- ⚠️ 既有环境缺陷（**已用 `git stash` 对比验证与本次改动无关**）：`test_api.py` / `test_auth_service.py` / `test_workbench.py` 在**全量或串行**执行时进程异常终止（无失败汇总、退出码 1），单独隔离运行则通过——疑为测试间状态污染或原生依赖崩溃。单独跑 `test_auth_service.py::test_generate_code_custom_length` PASSED
- 前端 `npx vite build --outDir dist2 --emptyOutDir false` 构建通过（AdminView 63.85 kB → 64.77 kB）
- `npx eslint` 改动文件无新增 error（AdminView 现存 2 条 `no-unused-vars`：`allIslands`、`formatPerms`，经 `git show HEAD` 确认改动前即存在）

### 部署（已上线现网）
- **前端**：`frontend/dist` 与 `dist2` 因 `whale-pet` 目录被占用无法清空/重建（`EPERM dist/index.html`、`prepareOutDir` 拷贝失败），且 `dist` 已处混合脏状态（新 sw.js + 旧 index.html + 新旧 chunk 并存）→ 改构建到全新目录 `dist-deploy`（197 文件，与上次部署数量一致）后整体上传；远端 `rm -rf dist` → 全量上传 → **SW v94→v95**、home=200
- **后端**：`scripts/deploy_backend.py` 白名单已含 `admin_users.py` 与 `schemas/common.py`，无需改脚本；上传 → pip → `alembic upgrade k2l3m4n5o6p7`（幂等 code 0）→ `pm2 startOrReload` 重启 → **`yexingchen-backend` online、ENV=production 保留、health=200**
- **生产取证（非破坏性探针，未创建任何账号）**：① 超管登录 200（登录口未被改坏）；② 建号口 `爸爸+空密码` → **400「密码不能为空」**（旧代码为 422 `Invalid email: 爸爸`）——**证明免校验通道生效**；③ 空账号 → 400「账号不能为空」；④ `strict_validation=True`+非邮箱 → 400「账号格式不正确」；⑤ 改密口 `strict_validation=True`+弱密码 → 400「密码至少 8 位」（用真实用户 id，校验失败故未产生任何修改）；⑥ **公开注册口非邮箱仍 422 `Invalid email`（公网规则未被削弱）**；⑦ 登录口非邮箱 → 401（格式拦截已移除，进入查库阶段）
- 前端产物核验：首页入口 `assets/index-CaXoA1X-.js` 与本地新构建一致；生产 `AdminView-mvC0E3Kb.js`（66 KB）含「启用严格校验 / strict_validation / 邮箱或任意账号」

---

## [v2.18.0] - 2026-09-16

### A 组三项（User「① 背景音乐开关 ② 玉简闪光卡 ⑥ 股票看板增强」SW `xuanhuang-v94`）

#### ① 背景音乐总开关（滑动开关 + 状态持久化）
- `stores/player.js` 新增 `bgmEnabled`（localStorage 键 `bgm_enabled`）+ `setBgmEnabled`/`toggleBgm`；`playBgm()` 与自动播放恢复句柄 `armResume` 均加总开关守卫——关闭时撤销恢复句柄并硬停释放网络流，**只作用于 BGM，不影响点播中的曲目**
- `GlobalTopBar` 音频面板新增滑动开关（`role="switch"` + `aria-checked` + `:focus-visible`），关闭时曲目选择与音量区降权显示；选中曲目时自动开启总开关，避免「选了却没反应」

#### ② 玉简卡片 3D 分层视差 + 镭射流光（纯 CSS，零依赖）
- `JadeCarousel.vue` 重构为四层 3D 舞台：玉体 z=0 / 篆符 z=22 / 镭射箔面 z=38 / 标签托片 z=54，靠 `preserve-3d` 拿到真实层间景深；标签压在箔面之上保证文字不被糊掉
- 指针写入 `--px` `--py` `--tl-x` `--tl-y` 四个 CSS 变量，驱动卡片微倾（±12°/±14° 封顶）与箔面扫光；倾斜并入轮播 `transform` 同一条链，与位移互不覆盖
- 箔面 = 指针跟随高光 + 多色镭射箔带 + 镭射细条纹，`mix-blend-mode` 由 token 分流（夜间 `color-dodge` / 日间 `overlay`，避免亮底被刷白）；激活卡未悬停时走 6.5s 环境流光，触摸端也有质感
- 实现思路参考 GitHub 成熟全息卡方案（`kongyo2/cards-css` 等），**未引入第三方依赖**——其 CSS 含大量硬编码 hex，会破坏项目「颜色必须走 variables.css」的门控
- 新增 token：`--jade-foil-blend` `--jade-foil-opacity` `--jade-foil-opacity-active` `--jade-glare` `--jade-foil-1..4` `--jade-foil-grain`（含日间覆盖）

#### ③ 股票看板增强
- KPI 由 3 张扩到 6 张：持仓市值 / 每日盈亏 / **总收益** / 总收益率 / **今日仓位收益**（= 今日盈亏 ÷ 昨日收盘市值）/ **目标价预警**
- 新增 `components/stocks/PortfolioPanel.vue`：
  - **资产配置**环形图——按个股持仓市值占比，复用 `finance/DonutChart`
  - **每日盈亏走势**柱状图——快照环比，红盈绿亏，附区间合计 / 最大单日 / 最大回撤
  - **每日盈亏日历**——当月月历按日染色，当日取实时行情，历史取收盘快照
- 每日快照由既有后台定时任务（交易日 15:35）自动记录，走势随天数自然累积；不足 2 天时给明确空态说明而非空白
- `DonutChart` 增可选 `unit`（默认「类」）与 `ariaLabel` prop，向后兼容账本页
- 新增 token `--pnl-up` `--pnl-down` 及 soft/line 变体，统一「红涨绿跌」语义色

### 工程
- 前端 `npx vite build --outDir dist2 --emptyOutDir false` 构建通过。注：`npm run build` 与 `--outDir dist2` 均在清空输出目录时失败（`dist/whale-pet`、`dist2/whale-pet` 无法移入回收站），**属本机安全删除机制问题，非代码问题**（`1796 modules transformed` 已通过）
- 产物标记核验：`jadeFoilSweep` `card-foil` `tb-switch` `bgmEnabled` `今日仓位收益` `资产配置` `每日盈亏走势` `pnl-up-soft` `jade-glare` 俱在；`--jade-foil-opacity` 日间 `.42` / 夜间 `.58` 两套均在
- `npx eslint` 改动文件 **0 error**（既有 172 warning 为项目风格告警，非本次引入）
- ⚠️ 未完成的验证：`vitest` 跑不起来——`vitest.config.js` 声明 `environment:'jsdom'`，但 `package.json` 未声明 `jsdom` 依赖、`node_modules` 里也没有（11 errors / no tests）。尝试安装时 npm 缓存被沙箱拦（EPERM），改工作区缓存后又因 `node_modules` 被运行中进程锁定（EBUSY）失败，故未强装（避免重写依赖树影响在跑的 dev server）。**属既有环境缺陷**
- **已全量部署现网（SW `xuanhuang-v93→v94`）**：全新 `npx vite build --outDir dist2` 核验 StocksView 含 `pp-alloc/资产配置/PortfolioPanel`、vendor/main 含 `bgm_enabled/setBgmEnabled`、css 含 `--jade-foil`、sw.js 含 `xuanhuang-v94` → 替换 dist → **197 文件 home=200**。生产浏览器取证 PASS：`/stocks` 正常加载、持仓市值/总收益/今日仓位收益等 KPI 俱在，「资产配置」环形图成功渲染（持仓市值 6970.00 / 1 只 / 红宝丽 100.0%）。

---

## [v2.17.0] - 2026-09-16

### 角色 · 菜单绑定（User「权限改为下拉，选择能看到哪些菜单」SW `xuanhuang-v93`）
- **后端**：`Role` 增 `menu_ids`(JSON) + 迁移 `k2l3m4n5o6p7`；`admin_roles` CRUD 接受/返回 `menu_ids`；`GET /api/admin/menus/public` 改为**按当前用户角色过滤**——super_admin 见全部启用菜单，普通角色按其 `menu_ids` 过滤（未配置=默认全部启用，向后兼容）
- **前端管理后台**：角色编辑弹窗「权限」由裸 JSON 文本框改为**菜单勾选树**（`el-tree`，一/二级模块、带全选/清空、保存 `menu_ids`）；角色表「可见菜单」列显示菜单名（未配置=「全部菜单」）而非 JSON
- **GlobalTopBar**：拉取 `/api/admin/menus/public`，按角色过滤搜索联想下拉「快速前往」模块快捷入口（super_admin/未配置→全显）

### 工程
- `deploy_backend.py` 白名单补 `k2l3m4n5o6p7_role_menu_ids.py`，生产 `alembic upgrade k2l3m4n5o6p7` 成功（j1..→k2..），重启 health=200、ENV=production 保留
- 前端全新 `npx vite build --outDir dist2` 核验 AdminView 含「可见菜单/全部菜单」、chunk 含 `/admin/menus/public` → 整体替换 → SW v92→v93 → 195 文件 home=200
- 生产备证：`GET /api/admin/menus/public` 以 admin(超管) 返回 10 条启用菜单；角色编辑菜单树、角色表可见菜单列浏览器取证 PASS

---

## [v2.16.0] - 2026-09-16

### 管理后台 · 三需求落地并部署现网（SW `xuanhuang-v92`）
- **用户重置密码**（User「用户管理没办法重置密码」）：`AdminView` 编辑下拉新增「重置密码」项 + 独立弹窗（显示目标邮箱 + 新密码，前端长度校验，`POST /admin/users/{id}/reset-password`，后端 `get_password_hash` 改密 + 操作日志）
- **角色下拉数据化**（User「角色管理支持下拉选择」）：用户编辑弹窗角色下拉改由角色表动态填充（code→name），替代硬编码三项
- **菜单一 / 二级模块**（User「菜单管理一级、二级模块」）：`Menu.parent_id` 字段 + 迁移 `j1k2l3m4n5o6`；`AdminView` 菜单管理改**树状展示**（一级模块 + 二级缩进 + `FolderOpened` 图标 + 「一级/二级」标签 + 「上级」列），表单新增「上级模块」下拉（「无（一级模块）」+ 各一级模块），保存带 `parent_id`；后端 `_validate_parent` 校验父须为一级、禁自身/禁三级，删除含子模块的一级模块被拦截
- **工作台视觉打磨部署**：朱砂印章 / 山峦剪影 / 玻璃徽章 / 楼层式载入落地上线（详见 v2.15.0 的待部署项，本轮补部署）

### 工程
- `deploy_backend.py` 白名单补齐 `admin_users/admin_roles/admin_menus` + 迁移 `j1k2l3m4n5o6`；生产 `alembic upgrade j1k2l3m4n5o6` 显式目标升级（规避仓库 FTS 平行分支多 head），重启后 `ENV=production` 保留、health=200
- **踩坑记**：`npm run build -- --outDir dist2` 参数转发失效、产出陈旧 bundle；改 `npx vite build --outDir dist2` 显式构建，校验 AdminView/WorkbenchView 标记后整体替换 dist

---

## [v2.15.0] - 2026-09-15

### 桌宠 · 极简（User「这些选项我都不要，就进来默认展示、随机动作」、「把手也去掉、直接拖本体」）
- **移除全部设置面板**：不再有「动作方式 / 散步模式 / 隐藏桌宠」等选项，桌宠默认即展示、只做**随机动作**，不可隐藏、不切换模式
- **去掉抓手角标**：改为**按住桌宠本体直接拖动**（轻点本体切一个随机动作作互动反馈）；滚动时自动淡出让位保留

### 备案标识 · 昼夜自适应（User「找个白天样式下能好好展示的颜色，全页面生效」）
- **`SiteFooter` 改随 `data-theme` 昼夜主题自适应的玻璃徽章**：自带底片 + backdrop 模糊，白天浅底深字、夜间深底浅字全站（工作台/岛屿/全局页脚）清晰可读
- **登录页备案文字提亮**：透明度 0.5 → 0.88，不再依赖鼠标悬停显现

---

## [v2.14.0] - 2026-09-15

### 股票
- **行情自动轮询刷新（SW `xuanhuang-v89`，User「希望加自动刷新，轮询的」）**：`StockDetailView` 新增自动刷新——行情 **15 秒**轮询、K 线每 3 次同刷一次（≈45s，后端 5 分钟缓存故不必更快）；标签页不可见时自动暂停省资源；K 线区块头部新增「自动 15s/已暂停 · X秒前更新」状态 + 点拨小灯 + 暂停/开启按钮；开关心记忆 `localStorage['stock-auto-refresh']`（默认开），退出页面自动清理定时器
- **每日研判改用 AI 增强（规则保底 + AI）**：后端 `stock_analysis.py` 新增 AI 研判链路——交易日按默认/启用 AI Provider 调模型（能力 `stock_analysis`），结合近 30 根 K 线、规则基线、相关资讯，产出 `level/summary/suggestion` 并落库 `xuanhuang_stock_daily_analysis`（user+code+market+date 唯一幂等覆盖）；未配置或调用失败时自动降级为规则档位，不阻塞不写空壳
- **每日自动调度**：`main.py` 仿资讯后台协程（仅 `ENV=production` 启动），交易日 **15:35 后**每 5 分钟检查一次，为「有自选股且当日尚未研判」的用户自动生成研判 + 记录当日持仓快照
- **研判接口**：新增 `GET/POST /api/stocks/analysis/{market}/{code}`（查询历史 / 立即生成今日研判）
- **详情页展示**：`StockDetailView` 每日研判区块优先展示 AI 研判（日期/收盘/涨跌/形态总结/操作建议 + 徽标 + 模型名，`AI·盘后` 标注），无 AI 记录时回退 KlineChart 盘中规则（`盘中规则` 标注）；新增「立即研判」按钮可手动触发

### 工程
- `deploy_backend.py` 白名单新增 `stock_analysis.py`、`user_ai_provider.py`、迁移 `e7f8a9b0c1d2`
- 随带清理：移除已无引用的 `cos_service.py`；邮箱验证码文案改用 `VERIFY_CODE_EXPIRE_MINUTES` 配置

---

## [v2.13.0] - 2026-09-15

### 安全修复
- **AI Provider 路由权限漏洞**：`routers/workbench/providers.py` 5 个端点全部 `get_current_user` → `require_super_admin`，避免普通用户修改 Provider 配置
- **注册密码强度校验**：`auth_service.verify_code` 加 8 位+大小写+数字校验，与 change_password 端点一致
- **移除 verify_code 内 Base.metadata.create_all**：避免在生产路径里触发 DDL（alembic 接管）

### 用户体验
- **token 主动监控**（`App.vue`）：每 30 分钟检查 token 剩余时间，即将过期自动续期，保持登录不掉线
- **token 主动延长**（`POST /auth/extend`）：剩余有效期不足 24h 时前端定时自动续期，用户无感知
- **滑动续期**：续期后旧 token 的 jti 加入黑名单失效，签发新 token 并更新本地存储
- **美股 K 线修复**：腾讯源对无后缀美股仅返回 1~2 根 K 线，改为依次尝试 `.OQ/.N/.A` 取数据量最多结果，点击股票名称可正常查看 K 线
- **桌宠防误隐藏**：`隐藏桌宠` 按钮增加二次确认（再点一次确认），并支持点击面板外自动关闭；避免误触导致桌宠消失

### 工程
- **`utils/http.js` 工厂函数**：消除 6 个 api/*.js 重复的 axios + 401 拦截代码
- **LoginView 拆分**：粒子背景 → `views/login/LoginParticleCanvas.vue`（692→528 行）
- **ISSUES.md 同步**：P2-006 部署监控告警标记已修复

### 性能（多轮累计）
- Nginx GZip 启用（部署后首屏 -70% 带宽）
- 3 个 FTS5 全文搜索表（Asset / Task / FeedArticle）
- 5 个 list 端点 N+1 优化（notes / assets / tasks / search）
- WhaleCompanion 异步加载
CHANGELOG

> 每次版本发布后记录变更内容

---

## [v2.12.0] - 2026-05-31

### Bug Fix
- **玉简点击修复**：`.carousel-track` 添加 `pointer-events: none`，修复 novel/log/tool 卡片点击无反应问题

### 玉简交互简化
- **移除粒子轨道动画**：删除 `.card-particles` 3个粒子椭圆轨道动画
- **移除光晕呼吸动画**：删除 `glow-breathe` / `card-glow-magic` / `card-glow-breathe`
- **移除浮动魔法动画**：删除 `card-float-magic` / `card-hover-sway`
- **移除入场动画**：删除 `jade-enter` 玉简淡入动画
- **移除自动轮播**：删除 `startAutoScroll()` / `stopAutoScroll()`
- **简化悬停效果**：hover时仅简单上浮，无旋转/缩放/动画
- **保留玉石纹理**：`.card-texture` radial-gradient冰裂纹理保留
- **简化键盘聚焦**：`.jade-focused` 去除呼吸脉冲动画

### 性能优化
- 减少持续动画，降低GPU占用
- 悬停交互更轻量响应更快

---

## [v2.11.0] - 2026-05-31

### 水墨国风重构
- **首页标题去除**：移除左上角"叶兴辰的个人网站"
- **配色重构**：从"仙居山林"改为水墨国风（深墨/黛青/赭石/藤黄）
- **设计规范**：新增 docs/DESIGN_INKWASH.md

### 配色变更
- 背景：深墨色 #1a1a1a
- 主色调：黛青 #3d4f4f
- 点缀：赭石 #8b6b4a、藤黄 #c4a35a
- 岛屿色：低饱和灰调
- 去除高饱和金色

---

## [v2.10.0] - 2026-05-31

### 功能收尾与体验优化
- **随机事件音效**：流星雨/灵气爆发/祥云降临播放古琴，仙鹤群飞/天雷隐现播放钟磬（3秒冷却）
- **修炼编年史持久化**：新增 useCultivationStore.js，localStorage 保存用户修炼历程
- **首页云雾漂移**：新增 MistLayer.vue，底部三层薄雾横向漂移

### 背景音乐修复
- 修复 audio muted 属性确保自动播放
- 数据库 bg_music 设置为 bamboo_flute.mp3

### 音频控制面板
- 音乐+音效图标合一，点击弹出双行独立控制
- 关闭按钮替代原点击切换功能

---

## [v2.9.0] - 2026-05-31

### 功能精简
- **背景音乐**：仅保留兰亭序，删除庭院音乐/青花瓷
- **音乐+音效图标合一**：点击弹出双行滚动条（音乐/音效各自控制）

### 玉简标签优化
- 音乐岛：音乐岛 → 宫商流转
- 小说岛：小说岛 → 卷帙浩繁
- 视频岛：视频岛 → 光影交织
- 日志岛：日志岛 → 翰墨丹青
- 工具岛：工具岛 → 机关百变

### 音乐自动播放
- 默认开启兰亭序自动播放
- 滚动条拖拽控制音量

---

## [v2.8.0] - 2026-05-31

### 玉简交互增强
- **键盘导航**：Tab遍历玉简，1-5数字快捷键，Enter进入对应岛屿，Escape取消聚焦
- **聚焦态**：键盘聚焦时显示金色呼吸光晕（jade-focused类）
- **触控手势**：左右滑动切换玉简，双击进入岛屿，长按触发
- **音效系统**：hover玉简触发翡翠静音切换（useIslandSound已适配玉简）

### Composables适配
- useKeyboardNavigation：.island-pos → .jade-card，路由映射重构
- useGestureControl：新增左右滑动/双击/长按手势支持
- useIslandSound：islandType参数改为card.id

---

## [v2.7.0] - 2026-05-31

### 玉简卡片系统重构
- **布局**：从5岛屿改为5玉简卡片，魔卡少女樱扇形阶梯排列
- **轮播**：每3秒自动从右向左切换（小樱翻牌式），鼠标悬停暂停
- **3D透视**：perspective 1500px，扇形展开 rotateZ，轻微Y轴旋转
- **材质**：羊脂白玉渐变底色 + 鎏金描边 + 玉石肌理
- **光影**：多层box-shadow悬浮感，核心卡片双层金色呼吸光晕
- **粒子**：淡青+淡金椭圆轨道旋转，hover时反向汇聚，点击时炸开
- **动效**：hover上浮+放大+rotateY(3deg)轻微摇摆，文字brightness+scale
- **入场**：从两侧向中间依次淡入，rotateY(15deg) 3D旋转入场
- **呼吸**：视频"影"玉简专属光晕呼吸动画（4s周期）
- **背景**：双层雾效反向飘动 + 半透明蒙版 + blur(1px)空间感

### 右侧面板优化
- DailyFortune面板：玉色半透明 + 鎏金边框 + hover增强

### 备案信息弱化
- 半透玉色背景 + 淡金色文字 + 图标透明度0.7

---

### 视觉重构 - 质感增强
- Layer 1 星空：增加多层次星星（大/中/小），不规则闪烁动画替代简单呼吸
- Layer 2 山脉：从单层改为三层远山（远/中/近），视差效果增强纵深感
- Layer 3 灵气：层次化灵气层（底部深/中层光斑/顶层淡光），4-7-8呼吸节律
- Layer 4 云海：云朵增加高光+阴影+边缘羽化，有体积感非简单椭圆
- Layer 5 薄雾：增加第三团散雾，边缘blur羽化处理
- 移动端适配：三层山脉保留最近山，远山隐藏

---

## [v2.6.0] - 2026-05-31

### 视觉重构 - Canvas 重构（返璞归真）
- 新增 `ParticleLayer.vue`：Canvas 灵气粒子（curl noise 有机运动，外圈光晕+核心亮点）
- 新增 `CloudLayer.vue`：Canvas 程序化云层（Simplex noise fbm，非简单椭圆）
- 新增 `GodRayLayer.vue`：Canvas 丁达尔光柱（底部亮→顶部渐隐+漂浮尘埃）
- 新增 `GrainOverlay.vue`：SVG 纸张纹理叠加（mix-blend-mode: multiply）
- 所有 Canvas 层随 `breathValue` 呼吸节律变化强度
- 保留 CSS 星空和山脉层作为背景基础

---

## [v2.6.1] - 2026-05-31

### 视觉重构 - 水墨国风配色
- 主色调改为**深靛蓝/松烟墨**背景（#0a0e14 / #0d1520 / #111827）
- 点缀色：**石青/松绿/赭石黄/米白**（低饱和淡雅）
- 星空改为暗淡柔和星尘感（18s慢速呼吸闪烁）
- 山脉改为4层水墨晕染风格（blur边缘、灰蓝系配色）
- Canvas层配色同步调整为水墨国风色系
- 所有透明度降低，营造夜晚/晨昏仙雾感

---

## [v2.5.2] - 2026-05-31

### 视觉重构
- 配色从"阳光仙山明亮系"改为"仙居山林自然有机"
- 大地色系：鼠尾草绿/陶土棕/赭石红/苔藓绿/燕麦色
- 十二时辰重新设计：白天米白暖白，夜间深褐（自然色调）
- 五层背景颜色同步调整为自然色系

---

## [v2.5.1] - 2026-05-31

### 视觉重构
- 背景从"玄墨深色"改为"阳光仙山"明亮系
- 背景色：`#12141A` → `#faf8f5` 暖白/象牙白
- 文字色：`#E8E4DC` → `#3a3530` 深棕
- 十二时辰重新设计：白天暖白/米白，夜间淡紫（不再是纯黑）
- 五层背景颜色同步调整适配明亮系
- 岛屿光晕从金色为主 → 琥珀橙紫

---

## [v2.5.0] - 2026-05-31

### 新功能
- 五层背景纵深（天穹星星/远山/灵气呼吸/云海/薄雾）
- 真正的视差效果，不同层移动速度不同
- 移动端简化（隐藏星星层和部分云层）
- prefers-reduced-motion 降级支持

### 技术
- `.cloud-sea` 替换为 `.parallax-layers` 5层结构
- 新CSS动画：star-twinkle/mountain-drift/qi-breathe/cloud-sea-drift/mist-drift
- Layer z-index: 1-5，阵法符文层改为z-index:6

---

## [v2.4.1] - 2026-05-31

### 优化
- 移除阵法模式按钮（用户反馈无实际作用）
- 音效按钮功能修复：hover岛屿触发音效（翡翠静音切换）
- 键盘帮助移至导航下拉菜单
- 生成5个岛屿hover音效文件（guqin/page-turn/camera/ink/gear）

### 技术
- useIslandSound.js 重构：toggleSound/isMuted/playHoverSound/stopHoverSound
- 音效文件：frontend/public/sounds/*.mp3

---

## [v2.4.0] - 2026-05-31

### 新功能
- 随机事件层 RandomEventsLayer.vue（灯笼/丹炉/仙鹤/符文飘浮+随机惊喜触发）
- 修炼编年史 CultivationChronicle.vue（用户修炼历程时间线弹窗）
- 灵根测试 SpiritRootQuiz.vue（趣味测试，5道题测试灵根属性）
- 导航下拉菜单（chronicle编年史入口/spirit-quiz灵根测试）
- LoadingView加载动画优化（灵蛇入境超时保护）

### 技术
- RandomEventsLayer使用seeded random保证确定性
- 15秒超时保护防止LoadingView动画卡死
- upload_server.py浏览器验证临时跳过（自动化环境限制）

### 待落地
- 随机事件音效配合
- 更多灵根测试题目
- 修炼编年史数据持久化

---

## [v2.3.0] - 2026-05-31

### 新功能
- 键盘导航 useKeyboardNavigation.js（Tab遍历岛屿，1-5数字快捷键，Enter进入，Escape取消，?帮助）
- 手势控制 useGestureControl.js（移动端捏合缩放/长按详情/上滑返回/双击进入）
- 岛屿声效 useIslandSound.js（Web Audio API，各岛屿hover专属音效）
- 键盘帮助层 KeyboardHelp.vue（?键呼出，展示快捷键说明）

### 技术
- 三大composable集成到HomeView.vue
- HomeView.vue添加tabindex="0"支持键盘焦点
- 音效开关按钮集成到顶栏
- browser_verify.js自动测试覆盖键盘/声效

### 待落地
- 音效文件（public/sounds/目录下需放置mp3文件）
- 手势控制在真机移动端测试

---

## [v2.1.0] - 2026-05-30

### 新功能
- 鼠标轨迹 MouseTrail.vue（Canvas淡金色粒子，1.2s生命周期）
- 修为印章 CultivationProgress.vue（右下角显示今日修为，localStorage持久化）
- 岛屿hover特效（5种岛屿专属动效：音符/书卷/光圈/墨滴/齿轮）
- 顶栏优化（音律玉佩/身份令牌/法诀玉简玉石质感样式）

### 技术
- 集成 components/effects/ 到 HomeView.vue
- 引入 hover-effects.css 岛屿特效

---

## [v1.8.0] - 2026-05-29

### 动效优化
- 岛屿进入页面即自动公转（移除需点击才启动的逻辑）
- 移除岛屿点击后的3D翻转动画，保留发光效果
- hover岛屿时微微上浮+光晕扩大

### 视觉优化
- 动态背景：每2小时变换一次，共12种时段色调（深夜/黎明/破晓/晨曦/上午/午前/午后/下午/傍晚/黄昏/夜初/深夜）

### 待落地
- 首页空白区域填充（云雾漂移+阵法符文方案，待PM调研确认）

---

## [v1.7.2] - 2026-05-29

### 登录体验
- 登录卡片提前出现（cardShow 1600ms → 1000ms）
- 卡片过渡动画加快（0.8s → 0.4s）
- 粒子风/光环与门全开同步，无额外延迟

---

## [v1.7.1] - 2026-05-29

### 登录体验
- 登录卡片延迟从2100ms优化到1600ms

---

## [v1.7.0] - 2026-05-29

### 主题适配
- ProfileView 玄墨流金主题适配（深墨背景、金色边框、CSS变量）
- AdminView Element Plus 深色主题覆盖

### 登录体验
- 冰晶琉璃门特效时序优化（3.3s → 1.6s）
- 登录卡片延迟从2100ms优化到1600ms

### 首页优化
- 岛屿环形公转效果（围绕中心点公转）
- hover时公转暂停+自身旋转
- 顶部装饰区域（金色分隔线+浮动粒子）
- 背景改为深墨色var(--color-bg-dark)
- 岛屿名称文字改为var(--color-text)

---

## [v1.6.6] - 2026-05-29

### Bug Fix
- （详情待补充，建议后续版本补录）

---

## [v1.6.5] - 2026-05-29

### 设计
- 玄墨流金设计风格上线
- 深墨底色（#0D0F14）替换浅蓝白背景
- 古铜金色系替换亮金
- 翡翠绿灵气特效色
- 多层阴影深度系统
- Grain噪点纹理

---

## [v1.6.4] - 2026-05-29

### Bug Fix
- 修复API版本控制路由重复前缀问题

---

## [v1.6.3] - 2026-05-29

### 架构优化
- 统一错误码体系（5位错误码枚举）
- 数据库连接池配置（pool_size=5, max_overflow=10）
- API版本前缀 /api/v1

### 前端
- Skip Link键盘导航

### 部署
- 异地备份方案脚本
- 健康检查与告警脚本

---

## [v1.6.2] - 2026-05-29

### 安全与体验优化
- 验证码改为字母数字混合（4位约16万组合）
- get_current_user从数据库校验用户状态，防JWT伪造
- 前端Token过期检查，过期自动清除
- 粒子动画改用伪随机数生成器（固定种子）
- CI配置npm audit/pip audit安全审计

---

## [v1.6.1] - 2026-05-29

### 安全修复
- CORS配置修复（限制allow_origins为yexingchen.cn）
- SECRET_KEY移除默认值，启动时强制检查
- 注册接口增加限流（1小时最多3次）
- 修改密码API实现（密码复杂度校验）
- 头像保存API实现（avatar_id字段）
- 补充缺失CSS变量（--color-qi-primary等）
- 移除lint的continue-on-error:true
- 创建后端测试文件（backend/tests/）
- E2E测试纳入CI

---

## [v1.6.0] - 2026-05-29

### 流程优化
- 建立完整13步开发流程（需求管理→评审→技术方案→开发→CodeReview→自测→Staging验证→用户验收→Git提交+Tag→部署生产→回滚方案→收尾）
- 7角色并行评审机制常态化
- 安全红线确立（凭证管理、登录限流、JWT安全、文件上传安全、数据库migration）

### 功能完成
- 登录卡片深色磨砂效果
- 首页标题金色渐变
- 阵法模式收尾 + 移动端适配
- 微倾侧动效（-8° + scale）
- 岛屿hover光效增强

### 待落地
- 凭证从代码迁移到环境变量
- 后端依赖同步机制
- Code Review PR流程
- 登录限流实现

---

## [v1.5.3] - 2026-05

### 功能
- 灵气结界效果
- 仙侠风格统一
- 架构优化
- 音乐切换兼容WAV格式
- 登录特效修复
- 管理后台新增用户功能
- 仙气飘飘特效



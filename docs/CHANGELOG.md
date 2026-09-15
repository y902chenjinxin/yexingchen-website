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



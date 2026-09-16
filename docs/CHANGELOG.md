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



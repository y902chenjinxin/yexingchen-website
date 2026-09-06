# 玄黄 PC 端功能扩展方案（2026-09-06）

> 状态：定稿评审通过（v1.1，多轮追问定稿）　版本：1.1
> 配套 SW：待定（实施时定）
> 关联文档：`docs/DESIGN_INKWASH.md`、`docs/ai/CURRENT_STATE.md`

## 一、背景与目标

本轮用户提出 5 个新增功能需求，全部为 PC 端高频场景：

1. **个人记账** — 解决"还用什么记"（微信账单 / Excel / Notion 散落多工具）
2. **资讯推送** — 解决"还用什么刷"（RSS / 微博 / 36 氪 / V2EX 多平台）
3. **股票查看** — 自选股 / 持仓 / 每日盈亏
4. **证件照** — 应急场景的轻量工具
5. **所有输入框支持语音输入** — 全局能力

要求在不破坏现有玄黄视觉与交互的前提下，让 5 个功能**自然融入**现有体系，而非堆叠为独立孤岛。

## 二、设计硬约束（用户明确要求）

| # | 约束 | 含义 |
|---|------|------|
| 1 | **顶部导航保持干净** | 不在顶栏加新入口，保留现有：工作台/笔记/音乐/小说/视频/工具/日志 |
| 2 | **玉简只放大的分类** | 玉简轮播是高曝光位，只放用户高频/有独立数据状态的"大分类"模块；小功能不占玉简位 |
| 3 | **快速入口放页面下方** | 工作台首页下方新增"快速入口"区，集中放所有高频动作 |
| 4 | **常用工具独立模块** | 工作台首页新增"常用工具"模块，用户常用工具一键直达，不每次进工具列表找 |
| 5 | **语音输入是基础设施** | 不是独立模块，是嵌入所有 `<input>` / `<textarea>` 的能力 |

## 三、5 个新增功能按"接触路径"分类

| 类别 | 模块 | 入口位置 | 用户使用频率 |
|------|------|----------|--------------|
| **🌐 基础设施** | 语音输入（5） | 每个输入框右侧 🎤 按钮 + 全局快捷键 | 高频 |
| **📊 大分类（占玉简位）** | 个人记账（1） | 玉简卡 + 工作台下方快速入口 | 中高频 |
| **📊 大分类（占玉简位）** | 资讯推送（2） | 玉简卡 + 工作台下方快速入口 | 中频 |
| **📊 大分类（占玉简位）** | 股票查看（3） | 玉简卡 + 工作台下方快速入口 | 中频（每日开盘前后） |
| **🛠 工具集成** | 证件照（4） | 工具库下拉 + 常用工具区 + `/tool/idphoto` | 低频应急 |

> 注：玉简轮播目前 8 张卡（已是 SW v32/v33 多次收敛后结果），本轮再收敛到 **3 张大分类卡 + 1 张快捷动作卡** + 原有的"网安页脚"位置保持不动。

## 四、工作台首页改造（重头戏）

### 当前布局（SW v33 后）

```
┌────────────────────────────────────┐
│  玉简轮播（3 张）                   │
│  ├─ 玉简1                          │
│  ├─ 玉简2                          │
│  └─ 玉简3                          │
├────────────────────────────────────┤
│  快捷动作                           │
├────────────────────────────────────┤
│  网安页脚                           │
└────────────────────────────────────┘
```

### 目标布局（本轮）

```
┌────────────────────────────────────────────┐
│  玉简轮播（3 张大分类数据卡）              │
│  ├─ 💰 账本：本月支出 / 预算 / 日均         │
│  ├─ 📡 资讯：今日 AI 摘要 5 条             │
│  └─ 📈 行情：自选股涨跌 / 持仓盈亏         │
├────────────────────────────────────────────┤
│  🛠 常用工具（新增模块）                   │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐                │
│  │证件│去水│ PDF│压缩│+ │                │
│  │照  │印  │   │   │添加│                │
│  └──┘ └──┘ └──┘ └──┘ └──┘                │
├────────────────────────────────────────────┤
│  ⚡ 快速入口（页面下方，集中高频动作）       │
│  [记一笔] [今日资讯] [加自选股]            │
│  [快速记录] [AI 助手] [打开工作台]         │
├────────────────────────────────────────────┤
│  📜 网安页脚（保持）                       │
└────────────────────────────────────────────┘
```

### 玉简卡设计规范（3 张统一模板）

每张玉简卡的统一规格：
- **顶部**：图标 + 模块名 + 右上角"查看全部 →"链
- **中部**：核心数据（2-3 行）
- **底部**：副信息（一行小字 + 进度条/标签，可选）
- **点击**：进对应主页
- **风格**：复用现有玉简卡（玉化 + 玻璃材质），不改样式

## 五、5 个模块详细规格

### 5.1 🌐 语音输入（基础设施，最先做）

**路由**：无（嵌入所有输入框）

**入口**：每个 `<input>` / `<textarea>` 组件内部右侧加 `🎤` 按钮

**激活方式**（两种）：
1. **点击按钮**：开始录音 → 静音 2 秒自动停止 → 文字填入当前焦点
2. **全局快捷键**：`Alt + Space` 长按，焦点在哪个框就填哪个

**适用范围与优先级**：
| 位置 | 优先级 | 备注 |
|------|--------|------|
| 顶栏搜索框 | P0 | |
| 顶栏"快速记录"对话框 | P0 | 最容易感知的场景 |
| 笔记编辑器 | P0 | |
| AI 对话输入框 | P1 | |
| 记账"备注"字段 | P1 | |
| 工具描述输入 | P2 | 视频去水印 / PDF / 压缩 |
| 玉简卡"快速备注" | P2 | |

**技术选择**（两档，按效果选）：
| 档位 | 实现 | 精度 | 成本 |
|------|------|------|------|
| A（首版） | 浏览器原生 [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) | 中 | 零 |
| B（升级） | `faster-whisper` 本地（Python 后端） | 高 | CPU 可跑 small |
| C（备用） | 云 API（OpenAI Whisper / 阿里 / 讯飞） | 高 | 按调用 |

**首版决策**：A 路线先上线 1-2 天即可用，不达标再上 B。

**新增组件**：
- `frontend/src/components/VoiceInputButton.vue`：通用按钮 + 录音状态
- `frontend/src/composables/useVoiceInput.ts`：composable 封装 Web Speech API

**验收标准**：
- 所有上述输入框都有 🎤 按钮
- 点击录音 → 静音 2 秒自动停 → 文字正确填入
- 录音中按钮变红 / 显示波形 / 可手动停止
- 浏览器不支持时按钮自动隐藏（feature detection）

---

### 5.2 📊 个人记账

**路由**：`/finance`

**入口**（3 处）：
1. **玉简卡**（💰 账本）
2. **工作台下方快速入口**（"记一笔"按钮 → 弹窗）
3. **工作台下方常用工具区**（常用工具的扩展，记账作为常驻项，列入"快捷记录"）

**玉简卡内容**：
```
┌──────────────────────────┐
│ 💰 账本        查看全部 →│
│ ¥ 4,832 / ¥ 8,000        │
│ ▓▓▓▓▓▓▓▓░░░░ 60%         │
│ 剩 17 天 · 日均 ¥ 284   │
└──────────────────────────┘
```

**主页布局**（`/finance`）— 数据大盘式
```
┌─────────────────────────────────────────┐
│  💰 账本              [本月▼] [+ 记一笔] │
├─────────────────────────────────────────┤
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐            │
│  │今日│ │本周│ │本月│ │预算│  ← KPI 卡  │
│  │128 │ │612 │ │4832│ │3168│            │
│  └────┘ └────┘ └────┘ └────┘            │
├─────────────────────────────────────────┤
│  [支出分类环形图]   [月度趋势柱状图]      │
├─────────────────────────────────────────┤
│  最近流水                                │
│  🍜 餐饮 -32   12:34  备注：午餐         │
│  🚇 交通 -6    08:21                    │
│  🛒 购物 -198  昨天                    │
│  [查看全部 →]                            │
└─────────────────────────────────────────┘
```

**数据模型**（新建表，复用 Alembic migration）：
```sql
-- accounts：账户（现金/银行卡/支付宝/微信 等）
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name VARCHAR(50) NOT NULL,           -- "现金"、"招商银行卡"
  type VARCHAR(20) NOT NULL,            -- cash / bank / alipay / wechat / other
  balance DECIMAL(12, 2) DEFAULT 0,    -- 当前余额（可选缓存）
  icon VARCHAR(20) DEFAULT 'wallet',
  is_archived INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- categories：分类（餐饮/交通/购物/收入 等；支持二级）
CREATE TABLE categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name VARCHAR(30) NOT NULL,
  icon VARCHAR(20),                     -- emoji 或图标名
  parent_id INTEGER,                    -- 二级分类，NULL 为顶级
  type VARCHAR(10) NOT NULL,            -- expense / income
  sort_order INTEGER DEFAULT 0,
  is_system INTEGER DEFAULT 0,          -- 系统预设分类（不可删）
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- transactions：流水（核心表）
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  account_id INTEGER NOT NULL,
  category_id INTEGER NOT NULL,
  type VARCHAR(10) NOT NULL,             -- expense / income / transfer
  amount DECIMAL(12, 2) NOT NULL,
  note VARCHAR(500),
  occurred_at DATETIME NOT NULL,         -- 发生时间（可手动改，不一定 created_at）
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (account_id) REFERENCES accounts(id),
  FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- budgets：预算（按月）
CREATE TABLE budgets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  category_id INTEGER,                  -- NULL = 总预算；否则分类预算
  monthly_amount DECIMAL(12, 2) NOT NULL,
  year_month VARCHAR(7) NOT NULL,       -- "2026-09"
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, category_id, year_month),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

**API 列表**（`/api/finance/*`）：
| Method | Path | 说明 |
|--------|------|------|
| GET | `/accounts` | 账户列表 |
| POST | `/accounts` | 新建账户 |
| PUT | `/accounts/{id}` | 修改账户 |
| DELETE | `/accounts/{id}` | 删除账户（有流水时禁止） |
| GET | `/categories` | 分类列表 |
| POST | `/categories` | 新建分类 |
| PUT | `/categories/{id}` | 修改分类 |
| DELETE | `/categories/{id}` | 删除分类 |
| GET | `/transactions` | 流水列表（支持 `?from&to&account_id&category_id&page&size`） |
| POST | `/transactions` | 新建流水 |
| PUT | `/transactions/{id}` | 修改 |
| DELETE | `/transactions/{id}` | 删除 |
| GET | `/budgets` | 当前月预算 |
| POST | `/budgets` | 设置预算 |
| GET | `/summary?month=2026-09` | 月度汇总（KPI + 趋势数据） |

**关键 UI 组件**：
- `frontend/src/views/FinanceView.vue`：账本主页
- `frontend/src/components/finance/TransactionDialog.vue`：记一笔/编辑弹窗（支持语音输入）
- `frontend/src/components/finance/KpiCard.vue`：KPI 卡（4 个）
- `frontend/src/components/finance/CategoryPie.vue`：分类环形图（用 ECharts）
- `frontend/src/components/finance/MonthlyBar.vue`：月度趋势图
- `frontend/src/components/finance/TransactionList.vue`：流水列表

**"记一笔"快速入口弹窗**（工作台下方）：
```
┌─────────────────────┐
│  记一笔              │
│  类型：[支出][收入]   │
│  金额：¥ _____  🎤   │
│  分类：🍜餐饮 ▼      │
│  账户：💳现金 ▼      │
│  备注：_______ 🎤   │
│  日期：今天 ▼        │
│  [取消] [保存]       │
└─────────────────────┘
```

**与现有模块的协同**：
- 月底 AI 生成"本月财务报告" → 一键存到笔记（调用现有 AI provider）
- 顶栏"快速记录"按钮新增分类：记账（不只是笔记）
- 流水可作为日志（写入操作日志 module='finance'）

**验收标准**：
- 玉简卡正确显示当月支出 / 预算 / 进度条
- 工作台下方"记一笔"可快速弹窗录入
- 主页 KPI、图表、流水三大区块完整
- 语音输入在"金额"、"备注"字段可用
- 流水可按月/分类/账户筛选

---

### 5.3 📡 资讯推送

**路由**：`/feeds`

**入口**（3 处）：
1. **玉简卡**（📡 资讯）
2. **工作台下方快速入口**（"今日资讯"）
3. **单条资讯"收藏到笔记"** → 反向入口（资讯 → 笔记）

**玉简卡内容**：
```
┌──────────────────────────┐
│ 📡 资讯        查看全部 →│
│ 今日 5 条摘要            │
│ → 36 氪：AI 早报...       │
│ → V2EX：热帖 #1...        │
│ → 虎嗅：今日头条...       │
└──────────────────────────┘
```
（点击卡片直接展开摘要列表；点击"查看全部"进入 `/feeds`）

**主页布局**（`/feeds`）— 三栏阅读流
```
┌──────────┬────────────────┬─────────────┐
│ 订阅源   │ 条目列表       │ 阅读视图    │
│          │                │             │
│ 36氪 🟡3 │ ● V2EX 热帖    │ 标题        │
│ 虎嗅     │   2 分钟前     │ 作者/时间   │
│ V2EX 🟢12│ ○ 另一条       │             │
│ 微博     │ ○ 另一条       │ 正文...     │
│ + 添加源 │                │             │
│          │                │ [📌 收藏]    │
│          │                │ [🤖 AI 摘要] │
│          │                │ [🏷️ 打标签]  │
└──────────┴────────────────┴─────────────┘
```
**移动端** 折叠为两栏（列表 → 详情）。

**数据模型**：
```sql
-- feed_sources：订阅源
CREATE TABLE feed_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name VARCHAR(100) NOT NULL,           -- "36 氪"
  url TEXT NOT NULL,                    -- RSS URL
  category VARCHAR(50),                -- "科技" / "财经" / "社区" 等
  icon VARCHAR(50),                     -- favicon URL
  fetch_interval INTEGER DEFAULT 3600, -- 秒，默认 1 小时
  is_enabled INTEGER DEFAULT 1,
  last_fetched_at DATETIME,
  last_status VARCHAR(20),              -- success / failed / pending
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- feed_items：条目
CREATE TABLE feed_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER NOT NULL,
  guid VARCHAR(500) NOT NULL,           -- RSS 唯一标识（去重）
  title VARCHAR(500) NOT NULL,
  url TEXT NOT NULL,
  author VARCHAR(200),
  summary TEXT,                         -- 摘要（RSS 自带）
  content TEXT,                         -- 全文（可选抓取）
  ai_summary TEXT,                      -- AI 生成的摘要（懒生成）
  published_at DATETIME,
  fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_read INTEGER DEFAULT 0,
  is_starred INTEGER DEFAULT 0,         -- 收藏标记
  note_id INTEGER,                      -- 关联到笔记（收藏时回填）
  FOREIGN KEY (source_id) REFERENCES feed_sources(id),
  FOREIGN KEY (note_id) REFERENCES notes(id)  -- 假设 notes 表已存在
);
```

**API 列表**（`/api/feeds/*`）：
| Method | Path | 说明 |
|--------|------|------|
| GET | `/sources` | 订阅源列表 |
| POST | `/sources` | 添加源 |
| PUT | `/sources/{id}` | 修改 |
| DELETE | `/sources/{id}` | 删除 |
| POST | `/sources/{id}/refresh` | 立即抓取 |
| GET | `/items` | 条目列表（支持 `?source_id&is_read&is_starred&q&page&size`） |
| PUT | `/items/{id}/read` | 标已读 |
| PUT | `/items/{id}/star` | 标收藏 |
| POST | `/items/{id}/ai-summary` | 触发 AI 摘要 |
| POST | `/items/{id}/save-to-note` | 一键存到笔记（创建 Note 并回填 note_id） |
| GET | `/items/{id}` | 单条详情 |

**关键 UI 组件**：
- `frontend/src/views/FeedsView.vue`：资讯主页（三栏）
- `frontend/src/components/feeds/SourceList.vue`：左侧订阅源列表
- `frontend/src/components/feeds/ItemList.vue`：中间条目列表
- `frontend/src/components/feeds/ItemReader.vue`：右侧阅读视图
- `frontend/src/components/feeds/AiSummaryButton.vue`：AI 摘要按钮（复用现有 AI provider）

**后台任务**（`apscheduler`）：
- 每小时拉取所有 enabled 源的 RSS
- 新条目入库后入队"AI 摘要任务"（懒生成：用户点击时再生成，节省算力）
- 玉简卡"今日摘要"取最近 24h 的 AI 摘要条目

**数据源建议**（首版种子）：
- 36 氪：https://36kr.com/feed
- 虎嗅：https://www.huxiu.com/rss/0.xml
- V2EX：https://www.v2ex.com/index.xml
- 微博热搜：调用第三方聚合 API（如 `https://weibo.com/ajax/side/hotSearch` 需代理）
- 后续可加：少数派、知乎热榜、GitHub Trending

**与现有模块的协同**：
- **资讯 → 笔记**：📌 一键保存（复用现有 Note schema，标题=原标题，正文=全文+元数据）
- **资讯 → AI**：调用现有 AI provider 生成摘要
- **资讯 → 日志**：阅读历史自动写入操作日志（module='feed'）
- **资讯 → 标签**：复用笔记标签体系（用户在保存到笔记时打标签）

**验收标准**：
- 可添加 RSS 源并自动抓取
- 三栏布局正确（移动端两栏）
- AI 摘要按钮可触发并显示
- 收藏到笔记可用且回填 note_id
- 玉简卡显示当日 5 条摘要

---

### 5.4 📈 股票查看

**路由**：`/stocks`（列表） + `/stocks/:code`（详情）

**入口**（3 处）：
1. **玉简卡**（📈 行情）
2. **工作台下方快速入口**（"加自选股"按钮 → 弹窗）
3. **单股详情 → 相关资讯**（复用资讯模块）

**玉简卡内容**：
```
┌──────────────────────────┐
│ 📈 行情        查看全部 →│
│ 持仓市值 ¥ 824,500       │
│ 今日 +¥ 1,243 (+0.6%)   │
│ 腾讯 +2.3% · 茅台 -1.1%  │
└──────────────────────────┘
```

**主页布局**（`/stocks`）— 数据大盘
```
┌─────────────────────────────────────┐
│  📈 行情        [刷新] [+ 加自选] │
├─────────────────────────────────────┤
│  ┌────┐ ┌────┐ ┌────┐              │
│  │持仓│ │今日│ │组合│              │
│  │市值│ │盈亏│ │涨跌│              │
│  │82万│ │+432│ │+0.5│             │
│  └────┘ └────┘ └────┘              │
├─────────────────────────────────────┤
│  [自选股组合走势 - 近 30 天]         │
├─────────────────────────────────────┤
│  代码    名称    现价    涨跌        │
│  00700   腾讯    ¥385   +2.3% 🟢   │
│  600519  茅台    ¥1680  -1.1% 🔴   │
│  BABA    中概    ¥92    +0.8% 🟢   │
│  [查看更多 →]                        │
└─────────────────────────────────────┘
```

**单股详情页**（`/stocks/:code`）：
```
┌─────────────────────────────────────┐
│  ← 返回   腾讯控股 00700.HK          │
│  ¥ 385.20  +2.30 (+2.3%) 🟢         │
├─────────────────────────────────────┤
│  [K 线图：1D / 5D / 1M / 3M / 1Y]   │
├─────────────────────────────────────┤
│  持仓：100 股 · 成本 ¥ 350         │
│  盈亏：+¥ 3,520 (+10.1%) 🟢        │
├─────────────────────────────────────┤
│  相关资讯（自动聚合）                │
│  - 腾讯 Q2 财报...                  │
│  - 南向资金加仓腾讯...              │
└─────────────────────────────────────┘
```

**数据模型**：
```sql
-- watchlist：自选股
CREATE TABLE watchlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  code VARCHAR(20) NOT NULL,            -- "00700" / "600519" / "BABA"
  market VARCHAR(10) NOT NULL,         -- sh / sz / hk / us
  name VARCHAR(100) NOT NULL,          -- 显示名（首次添加时填）
  cost_price DECIMAL(12, 4),           -- 持仓成本（可选）
  quantity INTEGER,                    -- 持仓数量（可选）
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  sort_order INTEGER DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id),
  UNIQUE(user_id, code, market)
);

-- stock_quotes：实时报价（缓存用，定期刷新）
CREATE TABLE stock_quotes (
  code VARCHAR(20) PRIMARY KEY,
  market VARCHAR(10) NOT NULL,
  name VARCHAR(100),
  current_price DECIMAL(12, 4),
  change_amount DECIMAL(12, 4),
  change_percent DECIMAL(8, 4),
  open_price DECIMAL(12, 4),
  high_price DECIMAL(12, 4),
  low_price DECIMAL(12, 4),
  volume BIGINT,
  turnover BIGINT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**API 列表**（`/api/stocks/*`）：
| Method | Path | 说明 |
|--------|------|------|
| GET | `/watchlist` | 自选股列表（含实时报价） |
| POST | `/watchlist` | 加自选股（传入 code，自动查询名称） |
| PUT | `/watchlist/{id}` | 修改（成本/数量/排序） |
| DELETE | `/watchlist/{id}` | 删自选股 |
| GET | `/quote/{market}/{code}` | 单股实时报价 |
| GET | `/kline/{market}/{code}?period=1d` | K 线数据 |
| GET | `/summary` | 持仓汇总 |

**关键 UI 组件**：
- `frontend/src/views/StocksView.vue`：行情主页
- `frontend/src/views/StockDetailView.vue`：单股详情
- `frontend/src/components/stocks/WatchlistTable.vue`：自选股表格
- `frontend/src/components/stocks/KlineChart.vue`：K 线图（用 ECharts 或 TradingView Lightweight Charts）
- `frontend/src/components/stocks/PortfolioChart.vue`：组合走势
- `frontend/src/components/stocks/AddStockDialog.vue`：加自选股弹窗

**数据源建议**（首版）：
- **A 股**：调用东方财富 / 新浪财经免费接口（`akshare` 库封装，无需 key）
  - 例：`ak.stock_zh_a_spot_em()` 实时 A 股行情
- **港股 / 美股**：`yfinance` 库（无需 key，但需注意代理）
- **定时刷新**：每 60 秒刷新一次报价（用 `apscheduler` 后台任务）
- **K 线**：调东方财富历史接口，按 period 缓存到 SQLite（避免频繁请求）

**"加自选股"快速入口弹窗**（工作台下方）：
```
┌─────────────────────┐
│  加自选股            │
│  代码：______  🎤   │
│  市场：[A股▼]        │
│  [查询]              │
│  ─────────           │
│  腾讯控股 00700      │
│  [取消] [加入自选]   │
└─────────────────────┘
```

**⚠️ 风险提示**：
- 页面底部固定一行小字："自用工具，数据仅供参考，不构成投资建议"
- 不做任何"买卖建议"、"目标价"、"止损位"等敏感信息

**与现有模块的协同**：
- **股票 → 资讯**：单股详情"相关资讯"复用资讯模块（按股票名称搜索 feed_items）
- **股票 → 笔记**：研报/财报分析一键存笔记

**验收标准**：
- 玉简卡正确显示持仓市值 + 今日盈亏 + 主要持仓涨跌
- 工作台下方"加自选股"可快速加自选
- 主页 KPI、组合走势、自选股表格完整
- 单股详情 K 线 + 持仓 + 相关资讯完整
- 风险提示在底部常驻

---

### 5.5 🛠 证件照工具

**路由**：`/tool/idphoto`

**入口**：
1. **工具库下拉菜单**（顶栏"工具"下）：与视频去水印/PDF/像素压缩并列
2. **工作台常用工具区**：作为常用工具默认项之一
3. **工作台下方快速入口**（可选）：低频但应急，酌情加

**工具页布局**（`/tool/idphoto`）：
```
┌─────────────────────────────────────┐
│  证件照                              │
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐│
│  │   📷 拖拽上传 / 点击选图        ││
│  └─────────────────────────────────┘│
├─────────────────────────────────────┤
│  ┌────┐  ┌────┐                     │
│  │原图│  │预览│  ← 并排对比          │
│  └────┘  └────┘                     │
├─────────────────────────────────────┤
│  尺寸：[一寸 ▼]                       │
│  底色：[白 ▼] [蓝] [红] [自定义]      │
│  □ 美颜（轻量）                       │
├─────────────────────────────────────┤
│  [下载标准照] [下载高清照] [六寸排版照]│
└─────────────────────────────────────┘
```

**参考实现**：[HivisionIDPhotos](https://github.com/Zeyi-Lin/HivisionIDPhotos)（21.5k ⭐，Apache-2.0）

**部署架构**（与现有 parse-service 平行）：
```
yexingchen.cn/api/tool/idphoto  →  FastAPI 转发层
                                  ↓
                              HivisionIDPhotos API（独立 8080 端口）
```

**数据模型**：无需新建表（纯工具，无用户数据持久化）。
**API 列表**（`/api/tool/idphoto`）：
| Method | Path | 说明 |
|--------|------|------|
| POST | `/upload` | 上传原图，返回 session_id |
| POST | `/generate` | 触发生成（参数：尺寸/底色/美颜） |
| GET | `/result/{session_id}` | 拉取结果 |
| GET | `/download/{session_id}` | 下载最终图 |

**关键 UI 组件**：
- `frontend/src/views/IdPhotoToolView.vue`：证件照工具页
- `frontend/src/components/tools/ImageUploader.vue`：上传组件（复用现有）
- `frontend/src/components/tools/IdPhotoPreview.vue`：原图/预览对比

**HivisionIDPhotos 部署**：
- Docker 方式：`docker run -d -p 8080:8080 linzeyi/hivision_idphotos python3 deploy_api.py`
- 模型权重下载：至少一个抠图模型（如 `hivision_modnet`，24.7MB）
- CPU 即可（不需要 GPU），MODNet + mtcnn 推理 ~200ms
- 内存占用 ~410MB

**验收标准**：
- 可上传照片生成标准证件照
- 支持一寸/二寸/护照/自定义尺寸
- 支持白/蓝/红/自定义底色
- 可下载标准照 + 高清照 + 六寸排版照
- 与现有工具库视觉/交互一致

---

## 六、工作台首页改造详细规格

### 玉简轮播改造

**保留**：3 张玉简的样式、动效、玻璃材质（不重做）

**替换内容**：
| 旧（SW v33） | 新（本轮） |
|--------------|-----------|
| 玉简 1/2/3：8 张轮播内容 | 3 张固定：账本 / 资讯 / 股票 |
| 原来分类入口整块 | 移除 |
| 原来的快捷动作区 | 移到下方"快速入口"区 |

**轮播改为非轮播**：3 张直接并排（或保留轮播动画，但只有 3 张可选）。

### 常用工具区（新增模块）

**位置**：工作台首页"玉简"下方、"快速入口"上方。

**布局**：
```
┌────────────────────────────────────────┐
│  🛠 常用工具            [管理 →]       │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐     │
│  │📷│ │📥│ │📄│ │🗜│ │+ │ │...│     │
│  │证│ │去│ │PDF│ │压│ │添│ │  │     │
│  │件│ │水│ │  │ │缩│ │加│ │  │     │
│  │照│ │印│ │  │ │  │ │  │ │  │     │
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘     │
└────────────────────────────────────────┘
```

**每个工具卡片**：图标 + 名称（2 行），点击直达工具页。

**"+"按钮**：打开常用工具选择器（从全量工具库挑）。

**数据存储**：用户常用工具存 `user_favorite_tools` 表：
```sql
CREATE TABLE user_favorite_tools (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  tool_id INTEGER NOT NULL,
  sort_order INTEGER DEFAULT 0,
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (tool_id) REFERENCES tools(id),
  UNIQUE(user_id, tool_id)
);
```

**API**：
| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/user/favorites` | 我的常用工具列表 |
| POST | `/api/user/favorites` | 添加常用 |
| DELETE | `/api/user/favorites/{id}` | 删除 |
| PUT | `/api/user/favorites/sort` | 排序 |

**默认项**：首次进入自动添加 3 个内置工具（视频去水印/PDF/像素压缩）+ 证件照（新增后）。

### 快速入口区（页面下方）

**位置**：工作台首页最下方（网安页脚上方）

**布局**：
```
┌────────────────────────────────────────┐
│  ⚡ 快速入口                            │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │💰   │ │📡   │ │📈   │ │📝   │  │
│  │记一笔│ │今日  │ │加自选│ │快速  │  │
│  │      │ │资讯  │ │股    │ │记录  │  │
│  └──────┘ └──────┘ └──────┘ └──────┘  │
│  ┌──────┐ ┌──────┐                     │
│  │🤖   │ │🏠   │                     │
│  │AI   │ │工作台│                     │
│  │助手  │ │      │                     │
│  └──────┘ └──────┘                     │
└────────────────────────────────────────┘
```

**按钮清单**（6 个）：
| 图标 | 名称 | 行为 |
|------|------|------|
| 💰 | 记一笔 | 打开记账弹窗（语音输入金额） |
| 📡 | 今日资讯 | 跳 `/feeds` |
| 📈 | 加自选股 | 打开加股弹窗 |
| 📝 | 快速记录 | 跳笔记新建 |
| 🤖 | AI 助手 | 打开 AI 对话页 |
| 🏠 | 工作台 | 跳工作台本身（兜底） |

## 七、新增组件清单

### 后端
```
backend/app/routers/
├─ voice_input.py          # 语音输入配置（如需后端处理）
├─ finance.py              # 记账
├─ feeds.py                # 资讯
├─ stocks.py               # 股票
├─ user_favorites.py       # 常用工具
└─ tool/idphoto.py         # 证件照（转发到 Hivision）

backend/app/models/
├─ finance.py              # accounts/categories/transactions/budgets
├─ feeds.py                # sources/items
├─ stocks.py               # watchlist/quotes
└─ user_favorites.py       # user_favorite_tools

backend/app/services/
├─ finance.py              # 业务逻辑
├─ feed_fetcher.py         # RSS 抓取（apscheduler）
├─ stock_fetcher.py        # 股票数据抓取
└─ ai_summarizer.py        # AI 摘要（复用现有 AI provider）

backend/alembic/versions/
└─ xxxx_add_finance_feeds_stocks_favorites.py
```

### 前端
```
frontend/src/views/
├─ FinanceView.vue         # 账本主页
├─ FeedsView.vue           # 资讯主页
├─ StocksView.vue          # 行情主页
├─ StockDetailView.vue     # 单股详情
└─ IdPhotoToolView.vue     # 证件照工具

frontend/src/components/
├─ VoiceInputButton.vue    # 全局语音按钮
├─ finance/
│  ├─ TransactionDialog.vue
│  ├─ KpiCard.vue
│  ├─ CategoryPie.vue
│  ├─ MonthlyBar.vue
│  └─ TransactionList.vue
├─ feeds/
│  ├─ SourceList.vue
│  ├─ ItemList.vue
│  └─ ItemReader.vue
├─ stocks/
│  ├─ WatchlistTable.vue
│  ├─ KlineChart.vue
│  ├─ PortfolioChart.vue
│  └─ AddStockDialog.vue
└─ tools/
   └─ IdPhotoPreview.vue

frontend/src/composables/
└─ useVoiceInput.ts         # Web Speech API 封装
```

### 路由新增
```
frontend/src/router/index.js:
├─ /finance
├─ /feeds
├─ /stocks
├─ /stocks/:code
└─ /tool/idphoto
```

## 八、实施阶段（4 周）

| 周次 | 内容 | 关键交付 |
|------|------|----------|
| **W1** | **语音输入（5）+ 证件照（4）** | 语音按钮全局可用；`/tool/idphoto` 上线 |
| **W2** | **工作台首页改造 + 资讯推送（2）MVP** | 玉简只 3 张、常用工具区、快速入口区；`/feeds` 基础三栏 |
| **W3** | **个人记账（1）MVP** | `/finance` 主页 + 弹窗记账；玉简账本卡 |
| **W4** | **股票查看（3） + 资讯完善** | `/stocks` + `/stocks/:code`；资讯 AI 摘要 + 收藏到笔记 |

**说明**：
- W1 优先做基础设施（语音）+ 独立工具（证件照），风险最低、收益最快
- W2 工作台改造是大动作，配合资讯 MVP 同时上
- W3-W4 三个数据大盘模块按用户优先级：资讯 → 记账 → 股票

## 九、验收清单

每完成一个阶段，按此清单逐项验证：

### W1 验收
- [ ] 所有 `<input>` / `<textarea>` 都有 🎤 按钮
- [ ] 顶栏搜索、笔记、快速记录可用语音输入
- [ ] 浏览器不支持时按钮优雅降级
- [ ] `/tool/idphoto` 完整可用（上传/选项/下载）
- [ ] HivisionIDPhotos 服务稳定运行

### W2 验收
- [ ] 玉简只显示账本/资讯/股票 3 张
- [ ] 工作台首页有常用工具区（4-6 个工具卡）
- [ ] 工作台最下方有快速入口区（6 个按钮）
- [ ] `/feeds` 三栏布局（移动端两栏）
- [ ] 可添加 RSS 源并自动抓取

### W3 验收
- [ ] `/finance` 主页 4 个 KPI 卡 + 2 个图表 + 流水列表
- [ ] "记一笔"弹窗可用，语音输入金额/备注
- [ ] 玉简账本卡显示正确
- [ ] 分类可增删改
- [ ] 预算可设置

### W4 验收
- [ ] `/stocks` 自选股表格 + 持仓汇总
- [ ] 加自选股弹窗可用（支持 A 股 + 港美股）
- [ ] `/stocks/:code` K 线图 + 相关资讯
- [ ] 玉简行情卡显示正确
- [ ] 资讯 AI 摘要可用，收藏到笔记可用
- [ ] 风险提示在页面底部常驻

## 十、风险与注意事项

### 算力风险
- **股票数据抓取**：东方财富 / 新浪接口可能限流，需在抓取层加重试 + 缓存
- **AI 摘要**：复用现有 AI provider，按调用付费的话需要警惕滥用（懒生成策略）
- **RSS 抓取**：源站可能不稳定，需记录 last_status + 重试机制

### 兼容风险
- **Web Speech API**：仅 Chrome/Edge 完整支持，Safari 部分支持，Firefox 需开启 flag
- **东方财富接口**：A 股免费接口随时可能调整，需有备用数据源
- **HivisionIDPhotos**：依赖 Python 3.10，与后端 venv 兼容需测试

### 数据风险
- **自选股数据**：实时数据仅缓存，DB 不持久化历史价格（节省空间）
- **流水数据**：用户隐私敏感，操作日志中不记录流水详情，只记"记账"

### 用户体验风险
- **学习曲线**：5 个新功能不要一次性堆给用户，分阶段上 + 引导提示
- **玉简卡数据源**：必须保证玉简卡数据"准确 + 实时"，否则失去信任

## 十一、相关文档
- 设计规范：`docs/DESIGN_INKWASH.md`
- 当前状态：`docs/ai/CURRENT_STATE.md`
- 工作台历史：`docs/ai/WORKBENCH_*.md`
- 工具库历史：`docs/ai/WORKBENCH_TOOLS_20260904.md`

---

> **执行说明**：本方案交由 MiniMax 实施。每个阶段开始前先读本文件相关章节 + `CURRENT_STATE.md`，按"实施 → 测试 → 浏览器实测取证 → 报告"流程推进。所有用户隐私数据走现有认证 + 操作日志体系。

---

## 十二、v1.1 定稿决策记录（2026-09-06 多轮追问后）

> 本章是**当前唯一有效口径**，如与正文冲突以本章为准。正文为初稿建议，下列为用户拍板的最终形态。

### D1. 范围
- **5 个功能全部一起做**，不打散 4 周分期严格交付，改为持续迭代推进（内部仍按"首页地基 → 模块"顺序）。

### D2. 工作台首页骨架（自上而下，最终形态）
```
┌────────────────────────────────────────────┐
│  玉简轮播（保持现状 = 分类导航，不改动）     │
├────────────────────────────────────────────┤
│  🛠 常用工具区（= 快速入口，工具+动作混排）  │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐          │
│  │证│ │去│ │PDF│ │压│ │AI│ │记│          │
│  │件│ │水│ │  │ │缩│ │对│ │一│          │
│  │照│ │印│ │  │ │  │ │话│ │笔│+更多      │
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘          │
│  （可自定义增删/排序）                      │
├────────────────────────────────────────────┤
│  📈 大数据看板（三块预览卡并排）            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │💰 账本 │ │📡 资讯 │ │📈 行情 │      │
│  │…核心数据│ │…今日摘要│ │…自选盈亏│      │
│  │[查看全部→]│ │[查看全部→]│ │[查看全部→]│ │
│  └─────────┘ └─────────┘ └─────────┘      │
├────────────────────────────────────────────┤
│  📜 网安页脚（保持）                        │
└────────────────────────────────────────────┘
```
- **快速入口寓于常用工具区**，不再单设"快速入口"独立块。
- **玉简轮播内容保持现状**（原分类导航，8 张不重做、不收敛），新模块不占玉简位。
- **大数据看板**三块预览卡并排（账本本月支出、资讯今日摘要、股票自选盈亏），每卡含 2-3 项核心数据 + 「查看全部 →」进对应页。

### D3. 顶栏
- **只加「AI 对话」一个导航项**，放在原顶部「笔记」入口位置，其余保持干净。
- 工作台原顶部「AI 助手」快捷卡由此**收进常用工具区**，不再单独置顶。

### D4. 语音输入
- **技术路线**：浏览器原生 **Web Speech API**（首版即此），不选 faster-whisper / 云 API。
- **铺满范围**：所有 `<input>` / `<textarea>` 全铺 🎤，含顶栏搜索、AI 对话、笔记编辑器、记账金额/备注、去水印/PDF/压缩等内置工具的全部输入位；浏览器不支持时按钮自动隐藏（feature detection）。

### D5. 常用工具区
- **工具与快捷动作混排一块**：工具（证件照/去水印/PDF/压缩）+ 动作（AI 对话/记一笔/今日资讯/加自选股）同排卡片，可自定义增删/排序（复用 `user_favorite_tools` 思想，动作型入口为内置常驻项）。

### D6. 二次追问补丁（2026-09-06 收口前追加，同样为有效口径）
| # | 决策点 | 拍板结论 |
|---|--------|----------|
| 1 | 数据看板空态 | **空态占位常驻**：三卡常显（「还没有流水 / 暂无资讯 / 暂无自选」），点「查看全部 →」进对应施工页；模块上线后自动填实 |
| 2 | 语音输入入口 | **仅每个输入框右侧 🎤 按钮**，不做 Alt+Space 长按全局快捷键（首版） |
| 3 | 常用工具区扩展 | **本轮固定 6 个默认项**（证件照 / 去水印 / PDF / 压缩 / AI 对话 / 记一笔），自定义增删/排序的 `user_favorite_tools` 后端**下轮再做** |
| 4 | 收口顺序 | 首页地基收口 与 记账 / 资讯 / 股票**数据模块并行推进**（非严格串行 4 周分期） |
| 5 | 首页是否展示数据看板 | **是**。首页恒展示大数据看板区（三块预览卡并排），数据未就绪时以空态呈现 |
# 玄黄工作台 · 日常好用好玩功能 Backlog

> 调研时间：2026-09-22 · 来源：GitHub 2025–2026 热门开源项目（open-webui 152k、lobe-chat 82k、dashy 26k、super-productivity 20k、loop-habit 10k、moodist、catime、anytype、joplin、glance 等）
> 选取原则：**与玄黄现有 Vue3 + FastAPI + SQLite 架构契合、复用已有模块（笔记/任务/打卡/天气/资讯/股票）、单人/小团队能 hold、可逐步上线**。

---

## 一、Top Picks（强烈推荐 · 单屏体验型）

| 编号 | 功能 | 参考来源 | 玄黄落地形态 | 为什么值得做 | 难度 | 优先级 |
|---|---|---|---|---|---|---|
| **F01** | **Bento 多视图切换**（工作/生活/写作/财务 4 套布局，按顶栏切换） | Dashy Workspaces + Bento Grid | 工作台新增视图切换器；layouts JSON 存后端 | 现有 Bento S1-S4 信息密度高，但所有信息混在一起；按场景拆分能显著降低认知负担 | 中 | ★★★★★ |
| **F02** | **数字花园 / Contribution 风格年度热力图** | Loop Habit Tracker + commitgrid + GitHub 贡献图 | `views/HeatmapView.vue` + 后端 `/api/workbench/heatmap` 聚合 笔记/打卡/记账/任务/资讯 五源数据 | 一张图覆盖全年"我做了什么"，可视化成瘾，复用现有数据零成本 | 中 | ★★★★★ |
| **F03** | **每日一问 / Surprise Box** | Habitica 每日任务 + Solo Leveling 战利品盒 | 工作台每日首次登录随机抛一个轻量任务（"今天拍张云"、"记录一件好事"、"读 5 分钟书"），完成后奖励 XP/徽章 | 现有习惯打卡是用户驱动，这个是"系统主动制造惊喜"，差异化好玩 | 中 | ★★★★★ |
| **F04** | **白噪音 + 番茄钟 + Todo 三合一 PWA** | Moodist + Catime + Pomotroid | 顶栏新增 🌙 按钮 → 全屏沉浸模式（白噪音播放/番茄钟/今日 Top3 任务联动） | 现有顶栏没有"专注模式"入口；这是专注力刚需，复用现有任务数据 | 中 | ★★★★★ |
| **F05** | **桌面部件 / Widget 引擎**（可拖到桌面的迷你小组件） | Lively Wallpaper + Pinchly + 浏览器桌面小组件 | PWA 内 widget 模块，支持天气/今日一句/热力图/股市卡片拖到副屏（`window.open` + 独立 URL） | 工作台被压在浏览器里；提供"挂件"让关键信息脱屏可见是体验质变 | 高 | ★★★★ |
| **F06** | **心情日记 + 回忆闪回**（AI 周报风格回顾） | Moodiary + Daily You + 现有笔记 | 笔记新增 mood 字段（5 档 emoji），后端每周日生成「这周/上月/去年今日」闪回卡片 | 现有笔记缺情绪维度，闪回是 Obsidian 之外的差异化玩法 | 中 | ★★★★ |
| **F07** | **快查面板**（Cmd+K 全局搜索 + Bang 跳转） | Dashy searchBangs + Raycast | 顶栏 Cmd+K 调出命令面板：`gh` 跳 GitHub、`r/N` 跳 Reddit、`note` 跳笔记搜索、`stock` 跳股票 | 现搜索框只能搜站内；扩展成"系统命令面板"是每天高频用 | 中 | ★★★★ |
| **F08** | **桌面小组件：动态倒计时小组件（带贴图/照片）** | DayKountdown + Moment Keeper | 现有倒计时工具新增"分享小组件"：生成 iframe URL，可嵌入 Notion/博客/桌面 Pin | 倒计时是玄黄强项，扩散到外部场景能反哺引流 | 低 | ★★★★ |
| **F09** | **AI 每日早报**（精简版：每日 9 点生成 1 屏日报） | Open Notebook + Khoj 定时 | 后端 scheduler 每日 09:00 调 AI 生成「昨日回顾 + 今日待办 + 关注股 + 天气 + 一句」，工作台顶部展示 | 已有 AI 能力，可直接落地，不与"AI 简报"重复（已移除）的范围重叠——这次是"早报推送"而不是"随时刷新" | 中 | ★★★★ |
| **F10** | **桌面宠物 / Whael Companion 升级**（互动小游戏） | AIRI + Open-LLM-VTuber + ZcChat | 现有鲸鱼桌宠加一个互动层：扔球/投食/聊天，喂食消耗今日打卡奖励 | 桌宠已有但纯装饰，加互动能让"日常"变得"好玩" | 中 | ★★★ |

---

## 二、AI 嵌入（已经有 AI 能力，补强方向）

| 编号 | 功能 | 参考来源 | 玄黄落地形态 | 难度 |
|---|---|---|---|---|
| **A01** | **本地 LLM 接入**（Ollama / LM Studio 一键切换 provider） | Open WebUI + Cherry Studio | 后端 `ai_providers` 表新增 `type=ollama` 支持，配置 base_url 即可本地推理 | 中 |
| **A02** | **AI 自动打标签 / 笔记分类**（已有 embeddings 服务，复用） | Quivr + Smart Connections | 笔记列表右键"AI 自动打标"，后端调 `/v1/embeddings` → KMeans 归类 → 写入 tags | 低（已有 embeddings 表） |
| **A03** | **AI 解梦 / 心情解读**（基于当日日记） | — | 心情日记新增"AI 解读"按钮，输出 100 字性格/状态分析 | 低 |
| **A04** | **AI 头像生成**（基于自选股 / 打卡数据生成像素徽章） | — | 现有打卡页面新增"生成我的徽章"，Prompt 模板渲染 SVG | 中 |
| **A05** | **AI 播客生成**（笔记/资讯 → 双人对话音频） | Open Notebook 播客功能 | 资讯详情页新增"转播客"，调 TTS 多说话人合成，可下载 | 高 |
| **A06** | **AI 速记扩写**（短语音/文本 → 结构化笔记） | Voice-Pro + faster-whisper | 顶栏麦克风 → 实时转写 → 一键落笔记（已有 OCR / 语音基础） | 中 |

---

## 三、生产力强化

| 编号 | 功能 | 参考来源 | 玄黄落地形态 | 难度 |
|---|---|---|---|---|
| **P01** | **任务番茄联动**（点击任务 → 自动开番茄钟） | Super Productivity + git-tomato | 任务详情页加"开始专注"，自动 25min 计时 + 完成后勾掉 | 低 |
| **P02** | **时间盒 / Timebox 日历**（每日时段提前占位） | Super Productivity | 日历视图新增拖拽占位（30/60/120min），超期高亮 | 中 |
| **P03** | **GTD 周回顾向导**（每周日推送 5 步回顾） | — | 工作台右上角"周回顾"按钮 → 5 步式问卷 → AI 总结 | 中 |
| **P04** | **桌面日历订阅**（输出 .ics 给系统日历） | Vikunja CalDAV | 任务/倒计时/打卡都支持导出 ics URL | 低 |
| **P05** | **桌面通知**：任务/打卡/倒计时 准时推送 | — | PWA 通知 + Service Worker | 低 |
| **P06** | **数据导出 / 备份一键完成**（zip + 加密） | Anytype 导出 | 个人中心新增"导出全部数据"，含 notes/tasks/finance/stocks 全量 | 低 |

---

## 四、好玩 / 视觉向

| 编号 | 功能 | 参考来源 | 玄黄落地形态 | 难度 |
|---|---|---|---|---|
| **V01** | **动态壁纸**（天气联动：下雨天桌面自动飘雨滴） | Lively Wallpaper + 现有天气组件 | 顶栏"主题"新增"动态壁纸"开关，根据 weather 切换视频/GIF | 高 |
| **V02** | **像素徽章系统**（任务/打卡完成解锁像素徽章） | Habitica + git-tomato | 后端新增 `badges` + `user_badges` 表，徽章可在工作台"勋章墙"展示 | 中 |
| **V03** | **收藏夹 / Bento 主题切换**（多套配色） | Bento / Dashboard 主题生态 | 个人中心主题切换（已有 OLED 真黑，再加 Glassmorphism / Pastel / Sunset） | 低 |
| **V04** | **ASCII 头像**（用户自定义） | ASCII Generator | 个人中心头像支持 ASCII / Emoji / 上传 三选一 | 低 |
| **V05** | **桌面日历组件**（顶栏右侧悬浮小组件） | DayKountdown | 顶栏点击日期 → 弹出月历，含打卡/任务/倒计时热点 | 中 |
| **V06** | **打字机彩蛋**（连续敲键盘触发） | — | 全局监听连续输入计数，触发"打字机模式"动效 | 低 |

---

## 五、社区 / 协作（远期）

| 编号 | 功能 | 参考来源 | 玄黄落地形态 | 难度 |
|---|---|---|---|---|
| **C01** | **双人/小队副本**（协作打卡/任务） | Habitica 组队 | 邀请好友共建小队，共享任务/徽章 | 高 |
| **C02** | **公开主页**（玄黄 ID → 公开展示笔记/统计/勋章） | migueravila/Bento + Bento 个人主页 | 用户可设置 `xh.cn/u/<id>` 公开页，可关 | 中 |
| **C03** | **AI 角色市场**（导入/导出角色卡） | SillyTavern 角色卡 | 玄黄 AI 助手支持角色卡 JSON 导入 | 中 |

---

## 六、按"工作量/收益"二维矩阵排序

```
                收益高
                  │
       F01 视图   │  F02 热力图  F03 每日一问  F04 专注模式
       F07 Cmd+K  │  F05 桌面部件 F06 心情闪回  F09 AI 早报
       ──────────┼──────────────
       P01 番茄   │  A02 自动打标 P04 ics V03 主题 V04 ASCII
       V05 月历   │  P05 通知 P06 备份 F08 分享倒计时
                  │
       ──────────┼──────────────
       A01 Ollama │  A05 播客 V01 动态壁纸 F10 桌宠互动
       C02 主页   │  C01 组队
                  │
                收益低
   低 ─────────── 工作量 ───────────→ 高
```

**建议实施节奏**：
1. **第 1 周（立刻）**：F02 热力图 + F07 Cmd+K + F04 专注模式 + P01 番茄联动（全低工作量，收益高）
2. **第 2 周**：F01 多视图 + F03 每日一问 + F06 心情日记 + V05 月历组件
3. **第 3 周起**：F05 桌面部件 / F09 AI 早报 / A01 Ollama / F08 分享小组件

---

## 参考来源（GitHub）

- Dashboard：Dashy 26.5k、Homepage 24k、Glance 37k、Homarr 4.7k、Homer 11.6k
- Bento：migueravila/Bento 2.2k、bentofolio、Hublo
- AI 对话：Open WebUI 152k、Lobe Chat 82k、LibreChat 44k、Cherry Studio 30k、NextChat 86k
- AI 笔记：Khoj 35.9k、Open Notebook 8.8k、Quivr 39.5k、Smart Connections 4.3k
- 习惯/打卡：Loop Habit Tracker 10k、Habitica 13k、Neohabit
- 待办：Super Productivity 20k、Tasks.org 5.3k、Vikunja 3.4k
- 日记心情：Moodiary 1.4k、Daily You、Hey Linda
- 番茄钟：Catime 3k、Pomotroid 1.8k、Moodist
- 桌面美化：Lively Wallpaper 16k、Pinchly
- AI 桌面伴侣：AIRI 5k、Open-LLM-VTuber 4k、ZcChat 1k
- 本地 LLM：Ollama Desktop（2025-07）、Pinokio 5.0、BrowserOS

> 完整 60+ 项目调研明细已包含在对话中（按"个人 Dashboard / Bento / 日常玩具 / CLI / AI 工具箱 / 好玩小品 / 游戏化 / 可视化"分类）。

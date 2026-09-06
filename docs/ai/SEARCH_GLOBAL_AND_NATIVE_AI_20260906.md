# 全站搜索 + 独立原生 AI 助手 · 方案

- 日期：2026-09-06
- 状态：已确认口径，待实施
- 背景：User 4 点诉求 —— ①顶栏搜索提示语改"全站"语义；②去掉搜索下拉的「最近/标签」、腾出空位放其它模块功能；③把 AI 助手做成独立原生对话（不跟笔记捆绑死，能日常问答/总结/按需生成笔记，主要看模型）；④追问后口径收口如下。

## 一、口径决策（来自 3 轮追问）

| 项 | 结论 |
|----|------|
| 顶栏搜索改造 | **真全站搜索 + 模块快捷入口** |
| 搜索命中范围 | **各模块按标题；笔记按标题+正文** |
| 快捷入口（替换"最近/标签"） | **音乐 / 小说 / 视频 / 工具 / AI 助手**（不含日志、不含笔记） |
| 提示语 | 围绕"能搜索全部内容" |
| AI 交付方式 | **流式打字机输出** |
| AI 能力形态 | **自然对话 + 气泡内折叠操作，不强制绑定笔记** |
| AI 对话历史 | **自动保存、可回溯**（沿用 conversations/messages） |

## 二、现状

- 后端存在两套搜索：`routers/search.py` `/api/search`（已搜 Music/Novel/Video/Tool，**缺 Notes**，标题 contains）；顶栏实际调用 `workbenchApi.search`（`/api/workbench/search`，笔记+标签）。两套割裂。
- 后端 AI：`ai_invoke` 强绑定 ability（organize/summarize/suggest_tags/suggest_task）→ 返回结构化 → 前端引导"应用到笔记"。HttpProvider 为 env 级、非流式、JSON schema 强约束。属于"阉割/定制化"。
- 前端 `GlobalTopBar` 下拉固定「笔记/标签」两组 suggest 组。
- 前端 `AssistantView` 走 ability+apply 内联应用流程，发送即被"应用到笔记"引导。

## 三、改造设计

### A. 搜索（前后端）
1. 后端统一 `routers/search.py`：
   - 追加 **notes** 组（owner 限定 = 当前用户，`title or content contains q`），返回 `{id,title,_type:'note',status,snippet}`。
   - 保留 music/novel/video/tool（标题 contains）。工具按 `title` 搜，可顺带 description。
   - 每组各配 `size` 上限，返回 `total`。
2. 前端 `GlobalTopBar`：
   - `placeholder="搜索全站内容"`（语义：能搜全部内容）。
   - 聚焦且非空时，弹层顶部渲染**模块快捷入口**横向 chips（音乐→/music、小说→/novel、视频→/video、工具→/tool、AI 助手→/assistant）。数据源与关键词无关（始终展示）。
   - 其下为搜索建议分组：笔记(标题/正文命中)、音乐、小说、视频、工具，点击直达对应页。**移除「标签」组**。
   - 数据源从 `workbenchApi.search` 切到 `/api/search`（扩展后的全站端）。
   - 前端新增 api 函数 `globalSearch(q, size)`。

### B. 独立原生 AI 助手（前后端）
1. 后端新增**直通对话流式端点** `POST /api/workbench/ai/chat/stream`（`StreamingResponse`，`text/event-stream`）：
   - 入参：`conversation_id`、`content`、可选 `provider_id`。
   - 取用户所选 provider（`_resolve_user_provider`/`_build_http_provider_from_config`，缺省 FakeProvider）。
   - 上下文 = 会话内最近 N 条既有消息 → 追加本次 user 消息 → 用 httpx 以 `stream=True` 调 `/v1/chat/completions`，把 SSE `data:` 中的 `delta.content` 逐段 yield 给前端。
   - 非 OpenAI 兼容兜底：流式失败则退化为一次性返回。
   - 结束后把 user + assistant（完整文本）写入 `AiMessage`（沿用现有表），`conversation.updated_at` 刷新。
   - **不再写 `apply_payload / pending_apply`**（解除笔记绑定）；保留 `sanitize_text` 敏感清洗。
   - 新增 HttpProvider 方法 `chat_stream(messages)`（纯对话，无 ability JSON schema 包裹）。
2. 前端 `AssistantView` 改造为**原生对话形态**：
   - 左侧会话列表、顶部 provider 选择保留；**删除**"能力(ability) + 应用到笔记"内联流程的强制引导。
   - 发送后用 fetch 读 SSE，`response.body` `ReadableStream` 逐块追加到当前 assistant 气泡（打字机）。
   - 每个 assistant 回复下方提供**可折叠操作**：`记入笔记`（把整段回复存为一条新笔记，可在气泡内选目标笔记或新建草稿，作为可选动作，不默认执行），`复制`。满足"能按需生成笔记/总结"且不捆绑。
   - 保持现有对话历史加载/新建/删除。

## 四、验收标准（浏览器取证）
1. 顶栏搜索提示语更新；下拉 = 模块快捷入口 + 全站建议（含笔记正文命中）；无「标签」组。
2. AI 对话以流式打字机输出；任意日常问题可答（主要看模型）；可"记入笔记"；对话历史可回溯；不出现强制"应用到笔记"流程。
3. 登录/其余页面无回归。

## 五、风险
- 流式对 OpenAI 兼容端点依赖 `stream:true` + SSE 格式；个别端点不支持则退化一次性。超时默认 30s。
- 顶部快捷入口与搜索建议同屏高度可控（chips 一行、建议分组 ≤ 若干条）。
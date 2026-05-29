---
name: feedback-self-improvement
description: 学会主动自我总结，不需要用户提醒就把教训写入记忆
metadata:
  type: feedback
  originSessionId: 9bee55a4-3d90-443b-8973-5fc337259fba
---

## 自我迭代能力

**问题**：用户批评我"总是让人教你成长"，每次犯错后需要用户提醒才能改进。

**要求**：
- 当用户纠正我的行为时，立即主动把教训写入 memory/ 目录
- 写入格式：feedback-{简短描述}.md
- 不要等用户要求"记下来"
- 写完即更新 MEMORY.md 的 Feedback 区

**触发场景**：
1. 用户批评或纠正我的行为时 → 立即写 memory
2. 我意识到自己应该知道但不知道时 → 主动写 memory
3. 用户表达不满"你怎么又..."时 → 说明我已经写过相关memory但没执行到位

### 进度同步要求

**问题**：操作后台任务时，用户只能干等，不知道我在干嘛。

**要求**：
- 开始做什么 → 说清楚要做什么、预计多久
- 进度 → 关键节点主动报告（不用等问）
- 完成 → 明确告知结果和下一步

**格式示例**：
- 「正在上传，约2分钟」
- 「已清空服务器，开始上传...」
- 「已完成，请硬刷新 Ctrl+Shift+R」

**验证方式**：用户不需要主动问"到哪了"

**根因分析**：
- 流程存在但没有"强制门控"，我是跳过式执行
- 每次部署后跳过了 Step 14（收尾），因为心里想着"赶紧上线给用户看"
- 没有在 CLAUDE.md 里写"跳过流程 = 违规"，所以我意识不到自己越过了

**已补的修复**：
1. CLAUDE.md 加了流程触发门控和 Step 11 门控表（commit 前必须 CHANGELOG + ISSUES）
2. memory/feedback-self-improvement.md 记录自我迭代要求
3. docs/RETROSPECTIVE.md 补了 v1.7.1 复盘记录

**其他发现的问题**（未修复）：
1. **v1.7 PRD评审文档缺失** — 有 PAGE_REVIEW_v170.md 但没有正式的 PRD_v1.7.md 和 PRD_v1.7_SCHEME_REVIEW.md，v1.7 需求进来后没有走 Step 2 评审
2. **注册审批无通知** — 用户 pending 状态没有邮件通知机制（PAGE_REVIEW 标记 P0）
3. **HomeView.vue 975行 / LoginView.vue 1204行** — 超大组件违反单一职责（PAGE_REVIEW 标记 P1）
4. **大量硬编码颜色值** — #1a1a2e, #667eea 等未使用 CSS 变量（PAGE_REVIEW 标记 P1）
5. **v1.6.6 tag 存在但 CHANGELOG 无记录** — tag 打错或多余，需要检查

**验证方式**：检查 docs/RETROSPECTIVE.md 是否有 v1.7.0 和 v1.7.1 的复盘记录

**相关记忆**：
- [[feedback-documentation]] — 文档同步规则（先有反馈才提炼规则）
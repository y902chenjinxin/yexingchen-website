---
name: feedback-prd-missing
description: PRD文档必须在需求评审阶段生成，不能等用户提醒
metadata:
  type: feedback
  originSessionId: 9bee55a4-3d90-443b-8973-5fc337259fba
---

## 问题

用户批评："每次都要我提醒你，你不记得写PRD嘛"

**根因**：我把"生成PRD"当作可选项，只有用户明确要求时才写。实际上根据 workflow-prd-review.md，Step 2 明确要求：
- "生成 `docs/PRD_vX.Y_SCHEME_REVIEW.md`"
- "PM必须输出PRD文档"

## 触发场景

当任何需求进来并进入评审阶段时，我必须主动生成 PRD_vX.Y_SCHEME_REVIEW.md，不能依赖用户提醒。

## 已发现的历史缺口

| 版本 | 状态 | 说明 |
|------|------|------|
| v1.7.0 | 无正式PRD | 只有PAGE_REVIEW_v170.md，需补充PRD_v1.7_SCHEME_REVIEW.md |
| v1.7.1 | 无PRD | 小版本优化，合并在v1.7.0下可接受 |
| v1.6.6 | CHANGELOG无记录 | 需补充CHANGELOG记录 |

## 如何修复

1. **现在立即补**：v1.7.0 的 PRD_v1.7_SCHEME_REVIEW.md
2. **未来强制门控**：Step 2 出口条件之一是"PRD文档已生成"，未生成不得进入开发

## 相关记忆
- [[workflow-prd-review]] — Step 2 明确要求生成PRD
- [[feedback-self-improvement]] — 自我迭代能力
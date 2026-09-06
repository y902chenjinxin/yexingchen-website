# 玄黄数据模型草案

- 状态：待 PRD 评审
- 日期：2026-08-27

> 这是面向 Coding 模型的逻辑模型，不等于已经批准的数据库迁移脚本。

## 1. Note 笔记

| 字段 | 说明 |
|---|---|
| id | 主键 |
| title | 标题 |
| content | 富文本正文，具体序列化格式待编辑器选型 |
| status | `draft` / `completed` |
| category | 固定内容类型或笔记分类 |
| summary | AI 摘要，可为空 |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| completed_at | 完成时间，可为空 |
| deleted_at | 软删除时间，可为空 |
| user_id | 所属用户 |

## 2. Asset 内容资产

统一承载网页、图片和 PDF。

| 字段 | 说明 |
|---|---|
| id | 主键 |
| type | `link` / `image` / `pdf` |
| title | 标题 |
| description | 描述/备注 |
| url | 网页 URL；文件资产为空 |
| storage_path | 本地文件相对路径；网页为空 |
| original_filename | 原始文件名 |
| mime_type | MIME 类型 |
| file_size | 字节数 |
| status | `active` / `trash` |
| deleted_at | 进入回收站时间 |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| user_id | 所属用户 |

## 3. NoteAsset 笔记与资产关联

- note_id
- asset_id
- sort_order
- created_at

约束：同一关联不能重复；删除笔记或资产时按业务规则处理关联，不直接误删仍被其他内容使用的文件。

## 4. Tag 标签

| 字段 | 说明 |
|---|---|
| id | 主键 |
| name | 标签名，单用户范围内唯一 |
| created_at | 创建时间 |

## 5. NoteTag / AssetTag

采用多对多关联：

- note_id + tag_id
- asset_id + tag_id

任务也可以使用标签，但是否增加 `TaskTag` 视实际搜索需求决定。

## 6. Task 轻量任务

| 字段 | 说明 |
|---|---|
| id | 主键 |
| title | 标题 |
| description | 描述 |
| status | `todo` / `doing` / `done` |
| priority | `low` / `medium` / `high` |
| due_date | 截止日期，可为空 |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| completed_at | 完成时间，可为空 |
| deleted_at | 软删除时间，可为空 |
| user_id | 所属用户 |

## 7. TaskContent 任务与内容关联

- task_id
- note_id，可为空
- asset_id，可为空
- created_at

一条任务至少关联一个内容时，允许关联笔记或资产；手动创建任务可以不关联内容。

## 8. AiConversation / AiMessage

### AiConversation

- id
- title
- created_at
- updated_at
- deleted_at
- user_id

### AiMessage

- id
- conversation_id
- role：`user` / `assistant` / `system`
- content
- input_scope：本次发送的内容范围摘要，可为空
- created_at

AI 调用日志和对话正文应区分；禁止把 API Key 或敏感配置写入消息内容。

## 9. 回收站

MVP 可以用各业务表的 `status` + `deleted_at` 实现，不必立即单独建立 Trash 表。只有当恢复、批量清理和跨类型列表变复杂时，再抽象统一回收站表。

## 10. 搜索

第一版采用数据库字段搜索：

- Note：title、content、summary
- Asset：title、description、url、original_filename
- Task：title、description
- Tag：name

不搜索 PDF 内文、图片文字和网页正文。后续引入全文检索时再评估索引方案。

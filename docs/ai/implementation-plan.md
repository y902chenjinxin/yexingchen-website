# 玄黄 MVP 实施计划

- 状态：待 MiniMax 一次性执行
- 日期：2026-08-28
- 主力执行：MiniMax Coding 模型
- 设计、独立验收：当前助手（Codex）
- 用户：产品确认、敏感操作和生产操作确认

## 协作方式

不再按多个小批次要求用户反复传话。MiniMax 读取总任务单后，内部连续完成全部 MVP；完成后一次性汇报。当前助手随后统一检查代码、测试、安全和范围。

## 总任务

- 任务单：`docs/ai/coding-tasks/MASTER-mvp-implementation.md`
- 仓库目录：`D:\software\codex\codex_work\yexingchen-website`
- 产品资料：`D:\software\codex\codex_work\docs\ai`

## 内部阶段

1. 生产 schema 保护和迁移入口
2. `/workbench` 工作台和 PWA
3. 富文本笔记、自动保存草稿和完成状态
4. 图片、PDF、网页资产和本地存储
5. 分类、标签和搜索
6. 轻量任务
7. AI Provider、AI 整理和对话记录
8. 回收站、清理和操作日志
9. 测试、文档和工程卫生

## 完成后验收

MiniMax 完成后，当前助手一次性检查：

- 改动范围和产品需求符合度
- 数据库迁移和生产 schema 行为
- 笔记、资产、任务和 AI 核心流程
- 权限、文件上传、敏感信息过滤
- 前端构建、后端测试和 PWA
- 回收站、日志和响应式布局
- 测试产物、密钥和 Git 工作区卫生

## 生产操作门槛

生产服务器连接、数据库迁移、域名/证书变更、GitHub 推送、部署、回滚、删除和密钥配置均不包含在本次 Coding 总任务中，需由用户单独确认并执行。

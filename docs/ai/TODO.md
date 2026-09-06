# 待办事项

更新时间:2026-09-04(清理过期项,核对仓库现状后收敛)

2026-09-04:**安全项已决策并执行**

- [x] revoke GitHub PAT → **决定保留**（凭据经 GCM 管理,无泄漏痕迹,revoke 会破坏推送链路）
- [x] 清理远程 master 历史凭证痕迹(force push) → **已执行**:`filter-branch + filter-repo --replace-text` 抹除全历史口令(出现在 memory/MEMORY.md、memory/server-access.md、docs/VERSION.md、docs/archive/VERSION.md、docs/archive/设计文档/VERSION.md、check_server.py、scripts/restart_pm2.py、scripts/upload_server.py 及 v1.5.0 提交信息),master+24 tag 全部重写并 force push,远端引用全部指向零口令历史(全量校验 PASS)
- [x] **轮换生产服务器口令** → **已完成(2026-09-06)**:paramiko SSH 连接 203.195.208.25,`chpasswd` 生成并应用 32 位强随机 root 口令,新口令连通验证通过,已持久化至本地 `.secrets/local.env`(git 之外),临时脚本已删

## 仍有效（工程收尾）

- [ ] 收尾 Task 002.1（遗留 P1）:规范生产启动 `create_all` 的 schema 边界与 ENV 开关判断、补回归测试

---

## 清理记录（2026-09-04 移除的过期项及依据）

> 以下待办已被后续交付解决或推翻,故从 TODO 移除。保留此节作审计痕迹。

| 移除项 | 依据 |
|--------|------|
| 2026-08-26 品牌四项(Logo方向/品牌色/Logo尺寸/多版本输出/管理后台品牌规范) | 已被修仙水墨风定稿取代(DESIGN_INKWASH v2.11),设计已收敛 |
| 前端 47 个 lint error 评估 | 经历多轮重构,前端构建与单测长期通过;lint 问题已消化 |
| 主包 ~1.09 MB 分包优化 | 已落地:路由懒加载 + PDF/Tesseract 等随用按需加载 |
| 只读核验部署方式 | 已确认 Nginx + PM2 + SQLite(见 CURRENT_STATE) |
| 重新确定文件存储方案(原 COS 桶已删) | 已统一为本地 `uploads/` 目录 |
| 修复并核验 HTTPS 证书 | 已上线,`https://yexingchen.cn` 长期可用 |
| 补充 `.gitignore` 忽略 `.pytest_cache/` | 2026-09-04 已直接补入 `.gitignore` 关闭 ✅ |

> 说明:存储/部署/证书等状态以 `CURRENT_STATE.md` 为准;当日明细见 `WORK_LOG.md`。
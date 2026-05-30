---
name: project-lessons
description: 项目遇到的问题和解决记录，下次部署/开发时必读
metadata:
  type: project
---

## 项目经验积累

> 每次遇到问题并解决后，必须更新此文档

---

## 近期问题（2026-05）

| 问题 | 解决方案 | 预防措施 |
|------|----------|----------|
| SFTP路径拼接bug | 使用 `replace("\\", "/")` 统一正斜杠 | SFTP路径必须用正斜杠 |
| 服务器dist目录损坏 | 删除重建dist目录 | 部署后立即验证 |
| Canvas CSS变量不生效 | Canvas无法解析CSS变量字符串，必须用 `getComputedStyle()` | 组件内直接获取计算样式 |
| 登录表单value赋值无效 | 使用 `nativeInputValueSetter` + `dispatchEvent` | Vue表单需触发input事件 |

### 部署验证清单
1. 上传后 `sftp.listdir(remote_dist)` 确认文件数 > 0
2. `curl -I https://yexingchen.cn` 确认 HTTP 200
3. 浏览器自动化验证：`node browser_verify.js --production --all`

---

## 历史问题（已归档）

以下问题已在 v2.x 中修复，详细信息见对应版本的 PRD 和复盘文档：

- v1.6.0 部署问题 → 已在 v1.7+ 修复
- v1.6.1 安全审查 → 已在 v1.7+ 修复
- v1.7.2 部署问题 → 已在 v2.x 修复

**当前版本**: v2.2.0
**文档索引**: `docs/PRD_v2.x_SCHEME_REVIEW.md`, `docs/RETROSPECTIVE.md`

---

## 开发注意事项

### 前端
- **CSS变量**：所有颜色使用 `var(--color-xxx)`，禁止硬编码hex
- **Canvas颜色**：必须用 `getComputedStyle()` 解析CSS变量
- **组件行数**：Vue单文件组件不得超过500行
- **动画seed**：使用 `Math.abs(Math.sin(seed * 12.9898) * 43758.5453)` 计算

### 后端
- **认证**：`get_current_user` 只验身份，`require_super_admin` 验权限
- **数据库**：使用Alembic migration，禁止直接 `create_all`
- **限流**：所有敏感接口必须加限流中间件

### 测试
- **自测**：`python self_test.py` → `browser_verify.js --local --all`
- **部署验证**：`upload_server.py` → `browser_verify.js --production --all`
- **git检测**：`browser_verify.js` 自动根据 `git diff` 检测改动匹配测试
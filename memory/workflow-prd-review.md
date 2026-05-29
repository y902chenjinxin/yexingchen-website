---
name: workflow-prd-review
description: 完整开发流程13步规范，含需求管理、评审、开发、测试、部署、收尾
metadata:
  type: project
---

## 完整开发流程（13步）

**触发条件**：每次提出方案（包括用户主动提出或我方建议）时，自动触发全角色评审

**评审角色清单**：PM/前端/后端/UI/架构师/测试/运维 共7个

---

## Step 1：需求管理
- 统一需求池（GitHub Issues 或 docs/ISSUES.md）
- 需求状态追踪：待处理 → 进行中 → 已完成 → 已验收
- P0/P1/P2 优先级分类

## Step 2：需求评审
1. 搜集历史PRD文档、需求.txt、DESIGN.md
2. 启动7个角色Agent并行评审
3. 生成 `docs/PRD_vX.Y_SCHEME_REVIEW.md`
4. **测试角色必须输出功能验证清单**（格式：[功能点]→[验证操作]→[预期结果]→[优先级]）
5. **后端必须输出API路由设计+数据模型变更**
6. **PM必须输出变更影响分析**（涉及子系统、回归测试模块）
7. **同步更新项目记忆** — 记录需求状态（进行中/已完成）
8. 列出待确认事项给用户

## Step 3：用户确认
- 用户确认评审结论后进入技术方案设计

## Step 4：技术方案设计
- 后端输出：API路由设计 + 数据模型变更 + 时序图
- 前端输出：Design Token变更说明 + 组件接口
- 架构师确认技术风险

## Step 5：开发实施
- 按优先级 P0→P1→P2 实施
- 代码修改
- **使用分支模型**（feature branch），禁止直接push master

## Step 6：Code Review
- 所有变更通过PR合并 ✅ 已建立
- PR必须包含：变更说明、测试结果、影响范围 ✅ PR模板已创建
- 核心模块需2人review同意
- **运行安全扫描**（npm audit）
- **分支模型**：feature/xxx → master ✅ 已建立
- **CI自动化**：GitHub Actions构建+lint验证 ✅ 已建立

## Step 7：自测（自动化）
- 本地构建 `npm run build`
- 单元测试（前端Vitest + 后端pytest）
- E2E测试（test_site.cjs改造为预部署验证脚本）
- 本地启动前后端联调验证 `npm run dev`
- **移动端viewport测试**（375px/768px/1024px）
- **我必须先自测验证**，确认功能正常后才通知用户体验

## Step 8：预部署验证（Staging）
- 部署到staging环境（/var/www/yexingchen/staging/）
- 完整回归测试（对照Step2输出的功能验证清单）
- 数据库migration（如有变更）
- **我必须先自测验证**，确认功能正常后才通知用户体验

## Step 9：用户验收
- 用户在staging环境体验
- OK后进入部署

## Step 10：Git提交+Tag
- **部署前必须先git提交**，不是部署后
- 采用Conventional Commits格式：`feat:`/`fix:`/`docs:`/`refactor:`/`test:`
- 提交信息关联Issue（如有）
- **每次部署打Tag**：与PRD文档版本严格对齐（如`v1.6.0`）
- 提交信息记录本次变更内容

## Step 11：部署生产
- 部署前先备份远程dist：`/var/www/yexingchen/dist.bak.{date}`
- 上传到服务器 `/var/www/yexingchen/dist/`
- nginx重载
- 健康检查验证 `/api/health`
- 验证测试

## Step 12：回滚方案
- 记录回滚命令到 `docs/ROLLBACK.md`
- 回滚后验证

## Step 13：收尾
- 更新项目记忆（需求完成状态）
- 更新CHANGELOG.md（变更内容、时间、负责人）
- 更新PRD文档（补充开发过程中的变更）
- 复盘记录（根因+下次预防措施）写入 `docs/RETROSPECTIVE.md`

---

## 安全红线（任何人不得绕过）

1. **凭证不得硬编码**：密码必须从环境变量或.netrc读取，禁止写入代码 ✅ 已修复
2. **登录限流**：同一IP 5分钟内密码错误5次则封禁 ✅ 已修复（15分钟）
3. **JWT安全**：token使用httpOnly Cookie，敏感操作验证
4. **文件上传**：内容类型检测 + UUID存储 + 路径穿越防护
5. **数据库变更**：必须走migration脚本，禁止直接create_all

---

## 快速部署命令

```bash
# 1. 构建
cd frontend && npm run build

# 2. 上传到服务器
python upload_server.py

# 3. 重启后端
python restart_pm2.py

# 4. 验证测试
node test_site.cjs
```

---

**相关记忆**：
- [[project-v160]] — v1.6.0项目进行中
- [[project-3d-island-pause]] — 3D浮空岛项目暂停记录
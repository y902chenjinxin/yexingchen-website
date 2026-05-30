# 部署前检查清单

> 部署前必须完成所有检查项，未完成不得执行 deploy
> 每次修改代码后重新检查所有项

---

## 一、开发流程（13步）

### Step 2: PRD 文档
- [ ] 需求评审已完成，PRD文档已生成
- [ ] PRD文档路径：`docs/PRD_v{版本号}.md`
- [ ] 用户已确认 PRD

### Step 5: Code Review
- [ ] 核心模块变更已通过 PR 合并
- [ ] 至少 1 人 review 通过（非核心模块可省略）
- [ ] PR 链接已记录

### Step 7: 安全审查
- [ ] SECURITY_CHECKLIST.md 已签字
- [ ] 安全红线检查通过（JWT/限流/凭证/文件上传）

### Step 8: 自测（最关键）
- [ ] `npm run build` 通过，无 error/warning
- [ ] `npm run preview` 已启动，可访问 http://localhost:4173
- [ ] 鼠标轨迹颜色验证：翡翠绿粒子在深墨背景下可见
- [ ] 岛屿hover特效验证：每个岛屿悬停时有专属动效
- [ ] 移动端 375px 验证：布局正常、无横向溢出
- [ ] 移动端 768px 验证：布局正常
- [ ] `node test_site.cjs` E2E 自动化测试通过
- [ ] 登录流程验证：正确账密可登录、错误账密有提示
- [ ] 岛屿导航验证：5个岛屿都能点击跳转

### Step 9: Staging 验证（如有）
- [ ] 已上传到服务器 test 目录（如需要）
- [ ] 在 test 环境验证通过

### Step 10: 用户验收
- [ ] 用户已确认功能可用
- [ ] 用户确认后记录时间

### Step 11: Git 提交
- [ ] `git status` 确认无遗漏
- [ ] CHANGELOG.md 已更新
- [ ] ISSUES.md 已更新
- [ ] `git commit` 已执行
- [ ] `git tag v{x}.x.x` 已打标签
- [ ] `git push origin master` 已推送
- [ ] `git push origin v{x}.x.x` 已推送标签

### Step 12: 部署生产
- [ ] `python upload_server.py` 已执行
- [ ] `python restart_pm2.py` 已执行
- [ ] `curl -s https://yexingchen.cn` 返回有效 HTML
- [ ] `/api/health` 返回 200 或 JSON

### Step 13: 回滚方案
- [ ] 回滚命令已记录到 `docs/ROLLBACK.md`
- [ ] 回滚方案包含具体命令和验证步骤

---

## 二、CSS 变量门控（每次修改样式必查）

- [ ] 无新增 hex 颜色硬编码（`grep -n '#' src/views/*.vue` 无输出）
- [ ] 所有颜色使用 `var(--color-xxx)` 引用
- [ ] 如有新增变量，已写入 `variables.css`

---

## 三、组件门控（每次新增组件必查）

- [ ] 新增 .vue 文件不超过 500 行
- [ ] 样式超过 200 行已提取到独立 CSS 文件
- [ ] 动画使用 seed 模式，不使用 `Math.random()`
- [ ] 动画元素超过 50 个时使用 `will-change` + `transform`

---

## 四、文档同步（每次 commit 前必查）

- [ ] CHANGELOG.md 已记录本次变更
- [ ] ISSUES.md 已更新需求状态
- [ ] 如有新增文档，已更新 MEMORY.md 索引

---

## 五、测试强制要求

- [ ] 涉及 auth/login/JWT → 已运行 E2E + 登录边界测试
- [ ] 涉及岛屿/动画/CSS → 已验证 CSS 变量复用 + 移动端三档
- [ ] 涉及 API 接口 → 已验证 `/api/health` + 关联接口
- [ ] 每次 commit 前运行 `npm run lint`

---

## 检查结果记录

以下由执行者填写（每次部署必须真实填写，不能敷衍）：

**自测描述**（必须具体，不能写"已测"）：
> v2.2 功能集成完成，待用户验收后填写实际效果

**问题记录**：
> v2.2 CSS 变量仍有 79 处硬编码（主要是 AdminView.vue 和 transition 组件），下次迭代继续清理

**deploy 执行者**：Claude Code
**检查时间**：2026-05-30
**deploy 时间**：待用户验收后

---

## 本清单版本

v1.1 - 2026-05-30（v2.2 集成完成，待验收）
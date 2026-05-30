# MEMORY.md

## 项目经验
- [project-lessons](memory/project-lessons.md) — 本次遇到的问题和解决记录，下次部署时必读（包含沟通要求）

## 人设
- [personality-completeness](memory/personality-completeness.md) — 完成度边际成本为零，全部做完做得彻底

## 服务器访问
- [server-access](memory/server-access.md) — 服务器 IP、密码、部署路径

## 设计系统
- [design-xuanmo](docs/DESIGN_XUANMO.md) — 玄墨流金完整规范（色板/阴影/字体/纹理）
- [variables.css](frontend/src/assets/styles/variables.css) — 所有CSS变量，禁止硬编码

## 技能索引

### PM技能库
| 技能名 | 用途 |
|--------|------|
| `prd-development` | PRD文档生成 |
| `positioning-statement` | 定位声明 |
| `press-release` | 发布稿（Working Backwards）|
| `prioritization-advisor` | 优先级排序 |
| `product-strategy-session` | 产品策略会话 |

### 前端技能库
| 技能名 | 用途 |
|--------|------|
| `frontend-design` | 视觉/UI设计评审 |
| `web-design` | 新页面/网站设计 |

### 工程技能
| 技能名 | 用途 |
|--------|------|
| `/improve-codebase-architecture` | 架构决策/重构 |
| `qa-only` | 测试/E2E |

## Feedback
- [feedback-login-expired-error](memory/feedback-login-expired-error.md) — 首次加载时不显示"登录已过期"错误
- [feedback-documentation](memory/feedback-documentation.md) — 每次改动必须同步更新CHANGELOG和ISSUES
- [feedback-self-improvement](memory/feedback-self-improvement.md) — 用户批评"总是让人教你成长"，学会主动自我总结写入记忆
- [feedback-prd-missing](memory/feedback-prd-missing.md) — 用户批评"每次都要我提醒你写PRD"，Step 2 必须生成PRD文档
- [feedback-self-testing-incomplete](memory/feedback-self-testing-incomplete.md) — 自测只做build通过，没实际验证功能和视觉

## 工作流程
- [workflow-prd-review](memory/workflow-prd-review.md) — **完整13步流程**：需求管理→评审→技术方案→开发→CodeReview→自测→Staging验证→用户验收→Git提交+Tag→部署生产→回滚方案→收尾

### 核心要点
1. **更新项目记忆**：需求评审时记录需求状态为"进行中"，完成后更新为"已完成"
2. **自测自动化**：每次代码修改后，我必须先在本地localhost测试验证，OK后再通知用户体验
3. **Git提交时机**：部署前必须先git提交，不是部署后，**每次部署打Tag**
4. **PRD文档**：评审时先生成，后续开发过程中的需求变更在git提交前补充完善
5. **测试环境**：本地localhost预览 + staging环境验证，无需上传到服务器test目录
6. **Code Review**：所有变更通过PR合并，核心模块需2人review
7. **安全红线**：凭证不得硬编码、登录限流、JWT安全、文件上传安全、数据库migration
8. **回滚方案**：每次部署后记录到docs/ROLLBACK.md

## 项目状态
- [project-v200](memory/project-v200.md) — **v2.0-v2.2 当前版本**，包含全部功能
- [project-v2x](memory/project-v2x.md) — v2.x 分阶段规划（v2.1-v2.4）
- [project-3d-island-pause](memory/project-3d-island-pause.md) — 3D浮空岛项目暂停（已归档）
- [project-v170](memory/project-v170.md) — v1.7.0-v1.7.2 玄墨流金（已归档）
- [project-v160](memory/project-v160.md) — v1.6.0（已归档）
- [project-v180](memory/project-v180.md) — v1.8.0（已归档，并入v2.0）

---

## 快速参考

### 部署命令
```bash
# 1. 构建
cd frontend && npm run build

# 2. 自测（本地preview + 自动化浏览器验证）
python self_test.py
python self_test.py record Step 8

# 3. 上传到服务器
python upload_server.py

# 4. 重启后端
python restart_pm2.py

# 5. 验证生产环境
node browser_verify.js --production --all
```

### 服务器 Python 路径
`/var/www/yexingchen/backend/venv/bin/python`

### 数据库
`/var/www/yexingchen/backend/yexingchen.db`
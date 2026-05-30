# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal cloud storage and display platform ("叶兴辰的个人网站") inspired by "神农图" (Shennong Map), featuring a visual design of floating islands above clouds. Domain: yexingchen.cn

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
python run.py
# or with hot reload: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # development
npm run build    # production build
npm run preview  # preview production build
```

## Architecture

### Tech Stack
- **Frontend**: Vue 3 + Vite + Pinia + Vue Router + Element Plus
- **Backend**: Python FastAPI + SQLAlchemy + JWT
- **Database**: SQLite
- **File Storage**: Tencent COS (via cos-python-sdk-v5)
- **Email**: QQ邮箱 SMTP
- **Deployment**: Nginx + Uvicorn

### Directory Structure
```
backend/
├── app/
│   ├── main.py           # FastAPI entry point
│   ├── config.py         # Configuration (COS, email, JWT secret)
│   ├── database.py       # SQLAlchemy connection
│   ├── models/           # ORM models (user, music, novel, video, tool, log, global_setting)
│   ├── schemas/          # Pydantic request/response models
│   ├── routers/          # API routes (auth, admin, music, novel, video, tool, log, search, settings)
│   ├── services/         # Business logic (auth, email, COS, log)
│   └── utils/            # Utilities (security, file_utils)
├── uploads/              # Local file storage (music/, novels/, videos/, covers/, bgm/)
├── requirements.txt
└── run.py                # Startup script

frontend/src/
├── api/                  # Axios API wrappers per module
├── assets/islands/       # SVG island illustrations (music, novel, video, log, tool)
├── assets/styles/        # Global CSS (main.css, variables.css)
├── stores/               # Pinia stores (auth, music, novel, video, tool, settings)
├── views/                # Page components (LoginView, HomeView, MusicIsland, AdminView, etc.)
└── router/index.js       # Vue Router with auth guards

docs/
├── README.md             # Project documentation
├── PRD.md                # Product Requirements Document v1.0
├── PRD_v1.1.md           # Product Requirements Document v1.1 (in progress)
├── TECH_DESIGN_v1.md     # Technical Design Document
└── UI_DESIGN_v1.md       # UI Design Document
```

### Key Design Patterns

**JWT Authentication**: Token stored in localStorage, sent via `Authorization: Bearer` header. Super admin routes protected by `require_super_admin` dependency.

**File Upload Flow**: Files uploaded to local `uploads/` directory, served statically via `/uploads` prefix. Video uploads are also mirrored to Tencent COS.

**Background Music**: Stored in `global_settings` table with key `bg_music`. Default value is `/music/default-bg.mp3`. The script `backend/generate_bg_music.py` generates `garden_music.wav` to `backend/uploads/bgm/`. After generation, update the database setting to `/uploads/bgm/garden_music.wav`.

### Database

SQLite at `backend/app.db`. Tables: users, verification_codes, music, novels, videos, tools, operation_logs, global_settings. Created automatically on first run via SQLAlchemy `Base.metadata.create_all()`.

### 架构决策记录（ADR）

| ID | 日期 | 决策 | 原因 | 影响模块 |
|----|------|------|------|----------|
| ADR-001 | v1.5 | JWT存储于localStorage非Cookie | 简化前端实现，满足同源需求 | auth |
| ADR-002 | v1.5 | 视频文件同时存本地和COS | CDN加速+容灾备份 | video |
| ADR-003 | v1.5 | SQLite用于生产 | 数据量小+运维简单 | database |
| ADR-004 | v1.7 | 3D浮空岛方案暂停，SVG+CSS岛屿+微倾侧动效 | GLB模型缺乏深度感知 | HomeView |
| ADR-005 | v1.7 | 玄墨流金设计系统替代蓝灰调 | 用户反馈视觉不够高级 | 全站 |

**每次架构决策后必须同步更新此表**

### 跨模块依赖矩阵

| 变更影响 | 必须检查的模块 |
|----------|----------------|
| auth模块变更 | router、views/islands、stores |
| bg_music变更 | HomeView.vue、settings store、global_settings表 |
| video上传变更 | COS service、video router、video store |
| 新增岛屿类型 | HomeView.vue、router、stores、DESIGN.md |

**任何跨模块变更必须先输出依赖分析再开发**

## Current Status (v1.5 已完成)

所有 v1.5 需求均已完成并部署：
- 输入框 placeholder 淡蓝灰色 ✓
- 登录错误提示"账密输入错误，请重试" ✓
- 密码显隐图标（默认闭眼）✓
- 登录加载仙气飘飘特效 ✓
- 背景音乐（青花瓷、兰亭序）✓
- 岛屿阵法模式（环形旋转叠加）✓
- 5个岛屿改为数据列表 ✓

## 强制要求

### 流程触发（强制）
- **需求进来 → 必走 [[workflow-prd-review]]，不是可选，是门控**
- 用户说"开始"、"需求在这"、"继续"任意一个 → 先检查当前处于流程哪步
- 跳过流程直接写代码 = 违规，等于没按标准路径做事

### 流程门控（每步必查）
| 步骤 | 门控检查 | 违规说明 |
|------|----------|----------|
| Step 2 需求评审 | 7角色并行评审完成，PRD文档已生成 | 无PRD文档 = 违规 |
| Step 7 安全审查 | SECURITY_CHECKLIST.md 已签字 | 无签字 = 违规 |
| Step 8 自测 | npm run build + **npm run preview本地预览确认** + 移动端验证 | 未预览直接部署 = 严重违规 |
| Step 11 Git提交 | CHANGELOG.md + ISSUES.md 已同步更新，否则不许 commit | 未更新文档 = 违规 |
| Step 14 收尾 | 复盘记录写入 docs/RETROSPECTIVE.md | 未写复盘 = 违规 |

### 7角色技能调用触发

**触发条件 → 调用对应技能 → 产出物**

| 场景 | 触发关键词 | 调用技能 |
|------|-----------|----------|
| 新功能规划/需求分析 | "设计"、"规划"、"策略"、"新品"、"新功能"、"需求" | `prd-development` |
| 产品定位不清晰 | "定位"、"目标用户"、"差异化" | `positioning-statement` |
| 重大发布验证 | "发布"、"发布稿"、"用户会关心吗" | `press-release` |
| 季度战略/长期规划 | "roadmap"、"战略"、"方向" | `product-strategy-session` |
| 问题分析与优先级 | "优先级"、"排序"、"值不值得做" | `prioritization-advisor` |
| 前端UI/动效/视觉 | "界面"、"样式"、"改颜色"、"动画"、"特效" | `frontend-design` |
| 前端新页面/重构 | "做个页面"、"前端重构"、"landing page" | `web-design` |
| 前端CSS变量/设计系统 | "CSS"、"variables.css"、"design token" | 调用frontend-design，引用DESIGN_XUANMO.md |
| 后端API/安全/数据库 | "接口"、"路由"、"安全"、"数据库"、"migration" | backend agent |
| 架构决策/跨模块重构 | "重构"、"架构调整"、"性能优化" | `/improve-codebase-architecture` |
| 安全审查(CORS/JWT/限流) | "安全"、"漏洞"、"权限" | architecture skill |
| E2E测试/自动化验证 | "测试"、"自动化"、"回归" | `qa-only` 或 test_site.cjs |
| 部署/回滚/服务器诊断 | "部署"、"回滚"、"服务器"、"重启" | DevOps agent |
| CI/CD流水线 | "CI"、"GitHub Actions"、"lint"、"audit" | 查看.github/workflows/ci.yml |

**设计系统强制要求**：
- 所有颜色必须使用 `variables.css` 中的 CSS 变量（`var(--color-xxx)`），禁止硬编码 hex
- 禁止蓝色系主色调、纯白文字 `#FFFFFF`、浅蓝背景
- 设计规范：`docs/DESIGN_XUANMO.md`
- CSS变量：`frontend/src/assets/styles/variables.css`

### 测试强制要求
- **Step 8 门控**：`npm run build` + `node test_site.cjs` 必须通过
- E2E 覆盖率清单：登录流程(正确+错密码+空账号)、登出、5岛屿数据加载、管理后台、岛屿动画、音乐播放、/api/health、移动端(375px/768px/1024px)、错误提示、网络异常降级
- 涉及 auth/islands/API 的改动 → 追加专项 E2E 验证
- 移动端测试(375px)必须手动验证

**测试触发规则（强制）**：
- 代码涉及 auth/login/JWT → 必须运行 `node test_site.cjs` + 登录边界测试
- 代码涉及岛屿/动画/CSS → 必须验证 CSS 变量复用 + 移动端三档
- 代码涉及 API 接口 → 必须验证 `/api/health` + 关联接口返回结构
- 代码涉及文件上传 → 必须测试大文件(>10MB)、非法格式、路径穿越
- 每次 commit 前 → 运行 `npm run lint` + `npm run build`
- 部署前 → 必须执行完整 E2E + API 健康检查

### 部署强制门控（必须遵守）

**部署前必须完成 DEPLOY_CHECKLIST.md 中的所有检查项**

| 文件 | 作用 |
|------|------|
| `DEPLOY_CHECKLIST.md` | 部署前检查清单，完成所有 ☐ 变为 [x] 后方可部署 |
| `upload_server.py` | **门控脚本**：检测到未完成的检查项会拒绝执行上传 |
| `self_test.py` | 自测辅助工具：帮助系统性验证所有检查项 |
| `workflow_progress.py` | **工作流门控**：每个 Step 开始前自动检查前置步骤是否完成 |

**门控逻辑**：
1. `python workflow_progress.py Step 2` → 检查是否可以开始 Step 2（需要 Step 1 先完成）
2. `python workflow_progress.py check` → 查看所有步骤完成状态
3. `python self_test.py` → 运行自测检查（可选但推荐）
4. 手动填写 DEPLOY_CHECKLIST.md（填入实际验证结果）
5. `python upload_server.py` → 检测到未完成的项则退出，拒绝部署

**违规后果**：
- upload_server.py 检测到未完成项会直接退出，不执行上传
- workflow_progress.py 检测到前置步骤未完成会阻塞当前步骤
- 每次部署记录会保存在 DEPLOY_CHECKLIST.md 的"检查结果记录"区

### 后端变更检查清单
- [ ] 新接口是否需要认证？若是，加 `Depends(get_current_user)`
- [ ] 管理接口是否需要超级管理员？若是，加 `Depends(require_super_admin)`
- [ ] 涉及密码？必须走 `get_password_hash()`，禁止明文存储
- [ ] 有限流需求？查看 `rate_limit.py` 是否有对应 limiter
- [ ] 错误码是否已存在？若有，复用 `ErrCode.XXX`
- [ ] 数据库模型变更需要 migration 脚本？禁止直接 `create_all` 覆盖
- [ ] migration脚本是否有回滚能力？必须有up/down成对
- [ ] 新依赖是否已加入requirements.txt？禁止pip install后忘记lock
- [ ] 环境变量变更是否已更新.env.example？

### 架构技术债（主动处理）

| ID | 问题 | 优先级 |
|----|------|--------|
| TD-001 | CSS变量重复定义(`--color-primary`两次) | P1 |
| TD-002 | HomeView.vue 975行 / LoginView.vue 1204行，违反单一职责 | P1 |
| TD-003 | 大量硬编码颜色值(#1a1a2e, #667eea等) | P1 |
| TD-004 | 后端无测试文件(backend/tests/目录为空) | P0 |
| TD-005 | v1.7 PRD评审文档缺失 | P0 |
| TD-006 | 注册审批无邮件通知 | P0 |
| TD-007 | test_site.cjs覆盖率不足(缺登出/768px/1024px/错误状态) | P1 |
| TD-008 | CI e2e job无失败截图和日志持久化 | P1 |

### 部署健康检查门控

**部署前门控**：
- [ ] `npm run build` 无error/warning
- [ ] `node test_site.cjs` 全部通过
- [ ] `nginx -t` 配置语法正确
- [ ] PM2 `yexingchen-backend` 状态为online
- [ ] 磁盘空间 >1GB

**部署后门控**：
- [ ] PM2进程仍online（非exited/crashed）
- [ ] `/api/health` HTTP 200
- [ ] `curl -s https://yexingchen.cn` 返回有效HTML
- [ ] 登录流程端到端验证通过

**触发DevOps诊断的症状**：
- PM2进程exited/crashed → 立即执行 `pm2 logs yexingchen-backend --err`
- API 5xx错误 → 检查backend日志+数据库连接
- 前端白屏/静默失败 → 检查nginx error log+静态资源路径

### CSS变量门控检查清单（每次修改样式前必查）
- [ ] 是否有新的hex颜色值被写入？若有，强制改为 `var(--color-xxx)`
- [ ] 是否引用了variables.css中已有的变量？禁止重定义
- [ ] 是否需要新增变量？命名格式 `--color-{用途}`
- [ ] 检查命令：`grep -n '#\|rgb(' frontend/src/views/*.vue frontend/src/components/**/*.vue`
- [ ] 检查命令：`grep -c 'var(--' frontend/src/views/*.vue` 行数/文件数应随新页面增长

### 组件门控规则
- 新增.vue文件最大500行，超出必须先拆分
- 样式超过200行提取到独立CSS文件
- 动画使用seed模式：`const random = (seed) => Math.abs(Math.sin(seed * 12.9898) * 43758.5453) % 1`
- 禁止直接用 `Math.random()`（会导致动画不连贯）
- 动画元素超过50个时必须使用 `will-change` + `transform`

### PM技术债
| ID | 问题 | 优先级 |
|----|------|--------|
| PM-001 | v1.6 PRD评审文档缺失 | P0 |
| PM-002 | 产品决策无记录 | P1 |
| PM-003 | 无产品指标追踪(DAU/留存/转化) | P2 |

### 自我迭代（主动）
- **每次被用户纠正时，立即主动把教训写入 `memory/feedback-*.md`**
- 不要等用户要求"记下来"
- 写完后更新 `memory/MEMORY.md` 的 Feedback 区
- 触发场景：用户批评、纠正、表达不满"你怎么又..."

### 进度同步（强制）
- 操作后台任务时，开始前说明要做什么、预计多久
- 关键节点主动报告进度（不用等用户问）
- 完成后明确告知结果和下一步操作
- 格式：「正在上传，约2分钟」→「已清空服务器，开始上传...」→「已完成，请硬刷新」

### 文档同步
- **每次 commit 前必须检查并更新 `docs/CHANGELOG.md` 和 `docs/ISSUES.md`**
- 不得等用户提醒，代码改动和文档更新必须同步完成
- 验证方式：检查 git log 的提交信息是否与 CHANGELOG.md 记录一致

### Git 规范
- 部署前必须先 commit，不是部署后
- 每次部署必须打 Tag
- 凭证不得硬编码，从环境变量读取

### 部署流程
1. 构建：`cd frontend && npm run build`
2. 上传：`python upload_server.py`
3. 重启：`python restart_pm2.py`
4. 验证：`node test_site.cjs`

---

## Configuration

Backend environment variables (copy from `.env.example` or set directly):
- `SECRET_KEY`: JWT signing key
- `DATABASE_URL`: SQLite path (default: `sqlite:///./app.db`)
- `COS_SECRET_ID`, `COS_SECRET_KEY`: Tencent COS credentials
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: Email configuration

Frontend proxy configured in `vite.config.js` to forward `/api` requests to backend.
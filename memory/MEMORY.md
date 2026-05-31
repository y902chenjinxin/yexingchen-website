# MEMORY.md

## 项目经验
- [project-lessons](memory/project-lessons.md) — 问题记录与解决，下次部署必读

## 服务器访问
- [server-access](memory/server-access.md) — 服务器IP、密码、部署路径

## 设计系统
- [design-inkwash](docs/DESIGN_INKWASH.md) — 水墨国风规范
- [variables.css](frontend/src/assets/styles/variables.css) — CSS变量，禁止硬编码

## 技能索引

### PM技能库
| 技能名 | 用途 |
|--------|------|
| `prd-development` | PRD文档生成 |

### 前端技能库
| 技能名 | 用途 |
|--------|------|
| `frontend-design` | 视觉/UI设计评审 |
| `web-design` | 新页面/网站设计 |

### 工程技能
| 技能名 | 用途 |
|--------|------|
| `/improve-codebase-architecture` | 架构决策/重构 |

## Feedback（经验教训）
- [feedback-prd-missing](memory/feedback-prd-missing.md) — Step 2必须生成PRD文档
- [feedback-self-improvement](memory/feedback-self-improvement.md) — 主动自我总结
- [feedback-self-testing-incomplete](memory/feedback-self-testing-incomplete.md) — 自测必须实际验证功能

## 工作流程
- [workflow-prd-review](memory/workflow-prd-review.md) — 完整13步流程

### 核心要点
1. 部署前必须先git提交+打Tag
2. 自测必须实际浏览器验证，不能只build
3. 每次部署后更新ROLLBACK.md
4. 凭证不得硬编码

---

## 当前版本状态

**v2.12.0** (2026-05-31) - 玉简交互简化
- 移除粒子/光晕/浮动动画，保留玉石纹理
- 修复.carousel-track拦截点击问题

## 历史版本（已归档）
- [project-v200](memory/archive/project-v200.md) — v2.0-v2.10
- [project-v180](memory/archive/project-v180.md) — v1.8.0
- [project-v170](memory/archive/project-v170.md) — v1.7.0-v1.7.2
- [project-v160](memory/archive/project-v160.md) — v1.6.0
- [project-3d-island-pause](memory/archive/project-3d-island-pause.md) — 3D浮空岛暂停

---

## 快速参考

### 部署命令
```bash
# 1. 构建
cd frontend && npm run build

# 2. 自测
python self_test.py

# 3. 上传+重启
export SERVER_PASSWORD='yxCHEN@12345678' && python upload_server.py

# 4. nginx reload（必须）
ssh root@203.195.208.25 "nginx -s reload"

# 5. 验证
node browser_verify.js --production
```

### 服务器信息
- IP: 203.195.208.25
- 前端: /var/www/yexingchen/dist
- 后端: /var/www/yexingchen/backend
- 数据库: /var/www/yexingchen/backend/yexingchen.db
- Python: /var/www/yexingchen/backend/venv/bin/python
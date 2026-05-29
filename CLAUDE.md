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
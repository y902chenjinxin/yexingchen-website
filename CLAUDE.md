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

## Current Status (v1.1 in progress)

- Login page visual redesign complete (purple gradient, white light effects)
- Main page gradient sky background complete
- Five island SVG illustrations complete
- Test data generation script (`generate_test_data.py`) complete
- Background music generation script (`generate_bg_music.py`) complete - 60-second procedural garden-style WAV

Pending: PRD_v1.1 items marked as "待确认" (pending confirmation), particularly island image review.

## Configuration

Backend environment variables (copy from `.env.example` or set directly):
- `SECRET_KEY`: JWT signing key
- `DATABASE_URL`: SQLite path (default: `sqlite:///./app.db`)
- `COS_SECRET_ID`, `COS_SECRET_KEY`: Tencent COS credentials
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: Email configuration

Frontend proxy configured in `vite.config.js` to forward `/api` requests to backend.
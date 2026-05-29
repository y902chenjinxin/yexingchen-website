from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import engine, Base
from app.routers import auth, admin, music, novel, video, tool, log, search, settings as settings_router
from app.config import settings
from app.models.login_attempt import LoginAttempt  # 登录限流模型

# 创建表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="叶兴辰的个人网站 API",
    version="1.0.0",
    description="个人云存储与展示平台后端API",
    docs_url="/docs" if os.environ.get("ENV") != "production" else None,
    redoc_url="/redoc" if os.environ.get("ENV") != "production" else None,
)

# CORS - 严格配置，禁止通配符
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "https://yexingchen.cn").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 静态文件服务（上传的文件）
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# 注册路由
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(music.router)
app.include_router(novel.router)
app.include_router(video.router)
app.include_router(tool.router)
app.include_router(log.router)
app.include_router(search.router)
app.include_router(settings_router.router)


@app.get("/")
async def root():
    return {"msg": "叶兴辰的个人网站 API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
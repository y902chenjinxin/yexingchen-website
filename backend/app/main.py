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

# 注册路由 - API v1版本前缀
API_V1_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(admin.router, prefix=API_V1_PREFIX)
app.include_router(music.router, prefix=API_V1_PREFIX)
app.include_router(novel.router, prefix=API_V1_PREFIX)
app.include_router(video.router, prefix=API_V1_PREFIX)
app.include_router(tool.router, prefix=API_V1_PREFIX)
app.include_router(log.router, prefix=API_V1_PREFIX)
app.include_router(search.router, prefix=API_V1_PREFIX)
app.include_router(settings_router.router, prefix=API_V1_PREFIX)

# 兼容旧路径（未来版本移除）
LEGACY_PREFIX = "/api"
app.include_router(auth.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(admin.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(music.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(novel.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(video.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(tool.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(log.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(search.router, prefix=LEGACY_PREFIX, tags=["legacy"])
app.include_router(settings_router.router, prefix=LEGACY_PREFIX, tags=["legacy"])


@app.get("/")
async def root():
    return {"msg": "叶兴辰的个人网站 API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
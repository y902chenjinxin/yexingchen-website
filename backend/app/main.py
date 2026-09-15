from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import os
import logging

from app.database import engine, Base
from app.routers import (
    admin_menus, admin_roles, admin_users, auth, datahub, finance, log, music, novel, quick, search, settings as settings_router,
    stocks, tool, travels, video, video_parse,
)
from app.routers.workbench import router as workbench_router
from app.routers.feed import router as feed_router
from app.config import settings
from app.models.login_attempt import LoginAttempt  # 登录限流模型
from app.services import schema_guard
from app.services.feed_sync import FEED_SYNC_INTERVAL, FEED_SYNC_WARMUP, sync_all_sources_once
from app.services.stock_analysis import run_daily_scheduler_once
from app.services.logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

# 启动时表初始化与 schema 校验：
# - 生产环境：禁止 Base.metadata.create_all()（避免干扰 Alembic），改为校验 schema 与 head 一致
# - 非生产环境：保留 Base.metadata.create_all()（向后兼容开发与现有测试）
if schema_guard.is_production_env():
    schema_guard.assert_production_schema_ok(engine)
    logger.info("Production schema validated against Alembic head")
else:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="叶兴辰的个人网站 API",
    version="1.0.0",
    description="个人云存储与展示平台后端API",
    docs_url="/docs" if os.environ.get("ENV") != "production" else None,
    redoc_url="/redoc" if os.environ.get("ENV") != "production" else None,
)


# ---------- 资讯后台自动同步（仅生产环境） ----------
# 测试环境不启动后台任务，避免拉取真实 RSS 网络请求与事件循环泄露。
_feed_sync_task: "asyncio.Task | None" = None


async def _feed_sync_loop() -> None:
    """预热后先抓一次，之后按固定间隔循环。"""
    await asyncio.sleep(FEED_SYNC_WARMUP)
    while True:
        try:
            await asyncio.to_thread(sync_all_sources_once)
        except Exception:  # noqa: BLE001
            logger.exception("资讯后台自动同步失败")
        await asyncio.sleep(FEED_SYNC_INTERVAL)


if schema_guard.is_production_env():

    @app.on_event("startup")
    async def _start_feed_auto_sync() -> None:
        global _feed_sync_task
        if _feed_sync_task is None:
            _feed_sync_task = asyncio.create_task(_feed_sync_loop())
            logger.info("资讯后台自动同步已启动（每 %d 秒一次）", FEED_SYNC_INTERVAL)

    @app.on_event("shutdown")
    async def _stop_feed_auto_sync() -> None:
        global _feed_sync_task
        if _feed_sync_task is not None:
            _feed_sync_task.cancel()
            try:
                await _feed_sync_task
            except asyncio.CancelledError:
                pass
            _feed_sync_task = None
            logger.info("资讯后台自动同步已停止")


# ---------- 股票每日研判（AI）后台自动任务（仅生产环境） ----------
_stock_daily_task: "asyncio.Task | None" = None

# 检查间隔（秒）：每 5 分钟看一次是否到收盘窗口；启动预热 2 分钟避免抢在行情稳定前。
STOCK_DAILY_INTERVAL = 5 * 60
STOCK_DAILY_WARMUP = 120


async def _stock_daily_loop() -> None:
    await asyncio.sleep(STOCK_DAILY_WARMUP)
    while True:
        try:
            await asyncio.to_thread(run_daily_scheduler_once)
        except Exception:  # noqa: BLE001
            logger.exception("股票每日研判自动任务失败")
        await asyncio.sleep(STOCK_DAILY_INTERVAL)


if schema_guard.is_production_env():

    @app.on_event("startup")
    async def _start_stock_daily() -> None:
        global _stock_daily_task
        if _stock_daily_task is None:
            _stock_daily_task = asyncio.create_task(_stock_daily_loop())
            logger.info("股票每日研判后台任务已启动（每 %d 秒检查一次）", STOCK_DAILY_INTERVAL)

    @app.on_event("shutdown")
    async def _stop_stock_daily() -> None:
        global _stock_daily_task
        if _stock_daily_task is not None:
            _stock_daily_task.cancel()
            try:
                await _stock_daily_task
            except asyncio.CancelledError:
                pass
            _stock_daily_task = None
            logger.info("股票每日研判后台任务已停止")

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
app.include_router(admin_users.router)
app.include_router(admin_roles.router)
app.include_router(admin_menus.router)
app.include_router(music.router)
app.include_router(novel.router)
app.include_router(video.router)
app.include_router(tool.router)
app.include_router(log.router)
app.include_router(search.router)
app.include_router(settings_router.router)
app.include_router(workbench_router)
app.include_router(video_parse.router)
app.include_router(finance.router)
app.include_router(feed_router)
app.include_router(stocks.router)
app.include_router(travels.router)
app.include_router(datahub.router)
app.include_router(quick.router)


@app.get("/")
async def root():
    return {"msg": "叶兴辰的个人网站 API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """深度健康检查：DB / parse-service / 磁盘。"""
    import shutil
    import time

    from app.database import engine
    from sqlalchemy import text

    checks = {}
    overall_ok = True

    # 1) DB 连通
    db_start = time.monotonic()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["db"] = {"ok": True, "latency_ms": int((time.monotonic() - db_start) * 1000)}
    except Exception as exc:  # noqa: BLE001
        overall_ok = False
        checks["db"] = {"ok": False, "error": str(exc)[:200]}

    # 2) parse-service 可达
    ps_start = time.monotonic()
    try:
        import httpx
        base_url = settings.PARSE_SERVICE_URL.rstrip("/")
        with httpx.Client(timeout=3) as client:
            r = client.get(f"{base_url}/health")
        checks["parse_service"] = {
            "ok": r.status_code in (200, 400, 422),
            "status_code": r.status_code,
            "latency_ms": int((time.monotonic() - ps_start) * 1000),
        }
        if r.status_code >= 500:
            overall_ok = False
    except Exception as exc:  # noqa: BLE001
        overall_ok = False
        checks["parse_service"] = {"ok": False, "error": str(exc)[:200]}

    # 3) 磁盘（uploads / 数据库所在盘）
    try:
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
        total, used, free = shutil.disk_usage(upload_dir)
        free_gb = free / (1024 ** 3)
        checks["disk"] = {
            "ok": free_gb > 0.5,  # 至少 500MB 空闲
            "free_gb": round(free_gb, 2),
            "path": upload_dir,
        }
        if free_gb <= 0.5:
            overall_ok = False
    except Exception as exc:  # noqa: BLE001
        checks["disk"] = {"ok": False, "error": str(exc)[:200]}

    body = {
        "status": "ok" if overall_ok else "degraded",
        "checks": checks,
    }
    return body



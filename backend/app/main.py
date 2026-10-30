from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

from app.database import engine, Base
from app.routers import (
    admin_menus, admin_roles, admin_users, asr, auth, capsule, contacts, cover, countdown, crawler, datahub, finance, fish, idphoto, life, log, lost, music, novel,
    ocr, poem, prefs, quick, search, settings as settings_router, subscriptions,
    day_calendar, game_economy, game_rooms, game_tables, relations, thumb, tool, travels, vault, video, video_parse, voice_clone, wardrobe,
)
from app.routers.workbench import router as workbench_router
from app.config import settings
from app.models.login_attempt import LoginAttempt  # 登录限流模型
from app.services import schema_guard
from app.services.logging_config import configure_logging
from app.services.life_bootstrap import bootstrap_life
from app.database import SessionLocal

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

# v2.15 生活模块引导：保证全局 household + 每用户 member 档案存在
# （Alembic migration 也已做同样的种子，这里是防御性兜底，覆盖 create_all 路径）
bootstrap_life(SessionLocal)

# 生产环境关闭交互式文档。注意 openapi_url 也要一起关：
# FastAPI 只关 docs_url 时，/openapi.json 仍然可访问（会把全部接口结构暴露出去）。
# 判定统一走 schema_guard，避免「只读 os.environ」导致 pm2 重启后判定翻转。
app = FastAPI(
    title="叶兴辰的个人网站 API",
    version="1.0.0",
    description="个人云存储与展示平台后端API",
    **schema_guard.docs_urls(),
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
app.include_router(admin_users.router)
app.include_router(admin_roles.router)
app.include_router(admin_menus.router)
app.include_router(thumb.router)
app.include_router(music.router)
app.include_router(novel.router)
app.include_router(video.router)
app.include_router(tool.router)
app.include_router(crawler.router)
app.include_router(cover.router)
app.include_router(voice_clone.router)
app.include_router(countdown.router)
# v2.46.250 关系维护：与 contacts 同一张表，但按 user_id 隔离（个人私有）
app.include_router(relations.router)
app.include_router(log.router)
app.include_router(search.router)
app.include_router(settings_router.router)
app.include_router(prefs.router)
app.include_router(workbench_router)
app.include_router(video_parse.router)
app.include_router(finance.router)
app.include_router(travels.router)
app.include_router(datahub.router)
app.include_router(quick.router)
app.include_router(contacts.router)
app.include_router(subscriptions.router)
app.include_router(idphoto.router)
# v2.40.14 工具岛：OCR / 语音转文字（本地推理）
app.include_router(ocr.router)
app.include_router(asr.router)
# v2.40.15 工具岛：时间胶囊 / 摸鱼日历 / AI诗签
app.include_router(capsule.router)
app.include_router(fish.router)
app.include_router(poem.router)
from app.routers import rss as rss_router
app.include_router(rss_router.router)
# v2.15 生活模块：家庭共享空间（体重 / 三餐）
app.include_router(life.router)
# v2.40.21 生活模块：遗失物件 / 穿搭推荐 / 密码保险箱（都走 household 共享 + 上传人筛选）
app.include_router(lost.router)
app.include_router(wardrobe.router)
app.include_router(vault.router)
# v2.40.25 棋类游戏：在线双人（房间 + 邀请 + 轮询同步）
app.include_router(game_rooms.router)
# v2.43 棋牌三件套：积分 / 欢乐豆经济系统 + 战绩 + 自定义地图
app.include_router(game_economy.router)
# v2.44 牌类在线对局：掼蛋 / 麻将 / 大富翁 多席服务端权威房间
app.include_router(game_tables.router)
# v2.46.150 暴力摩托在线一起玩：房号 + 轮询（进程内房态）
# v2.40.36 日历数据（农历/节气/节日/法定假期）
app.include_router(day_calendar.router)


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



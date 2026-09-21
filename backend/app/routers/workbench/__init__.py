"""玄黄工作台路由包。

将原 workbench.py 按业务模块拆为多个子模块后，统一在这里聚合。
外部调用方式不变：``from app.routers.workbench import router``，在 main.py 里 ``app.include_router(router)`` 即可。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.routers.workbench.ai import router as ai_router
from app.routers.workbench.ai_advanced import router as ai_advanced_router
from app.routers.workbench.assets import router as assets_router
from app.routers.workbench.brief import router as brief_router
from app.routers.workbench.dashboard import router as dashboard_router
from app.routers.workbench.habits import router as habits_router
from app.routers.workbench.import_export import router as import_export_router
from app.routers.workbench.weather import router as weather_router
from app.routers.workbench.notes import router as notes_router
from app.routers.workbench.providers import router as providers_router
from app.routers.workbench.search import router as search_router
from app.routers.workbench.tasks import router as tasks_router
from app.routers.workbench.trash import router as trash_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(brief_router)
router.include_router(habits_router)
router.include_router(weather_router)
router.include_router(notes_router)
router.include_router(assets_router)
router.include_router(tasks_router)
router.include_router(search_router)
router.include_router(trash_router)
router.include_router(ai_router)
router.include_router(ai_advanced_router)
router.include_router(providers_router)
router.include_router(import_export_router)

__all__ = ["router"]

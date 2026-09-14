"""资讯推送路由包。

按业务拆为 dashboard / feed_sources / feed_articles + 共享的 _common / _fetch。
外部 import 不变：``from app.routers.feed import router``。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.routers.feed.dashboard import router as dashboard_router
from app.routers.feed.feed_sources import router as sources_router
from app.routers.feed.feed_articles import router as articles_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(sources_router)
router.include_router(articles_router)

__all__ = ["router"]

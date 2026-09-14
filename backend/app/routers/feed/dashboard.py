"""feed - 工作台首页数据卡。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feed import FeedArticle, FeedSource
from app.utils.security import get_current_user
from app.routers.feed._common import ok

router = APIRouter(prefix="/api/feeds", tags=["资讯推送-首页"])


@router.get("/dashboard")
def feed_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """工作台首页数据卡：源数量 / 未读数 / 最近文章。"""
    uid = current_user["user_id"]
    today = datetime.now().date()

    source_count = (
        db.query(FeedSource)
        .filter(FeedSource.user_id == uid, FeedSource.deleted_at.is_(None))
        .count()
    )
    unread = (
        db.query(FeedArticle)
        .filter(FeedArticle.user_id == uid, FeedArticle.read == 0)
        .count()
    )
    today_count = (
        db.query(FeedArticle)
        .filter(FeedArticle.user_id == uid, FeedArticle.published_at >= today)
        .count()
    )
    recent = (
        db.query(FeedArticle)
        .filter(FeedArticle.user_id == uid)
        .order_by(FeedArticle.published_at.desc().nullslast(), FeedArticle.id.desc())
        .limit(3)
        .all()
    )
    return ok({
        "source_count": source_count,
        "unread": unread,
        "today_count": today_count,
        "recent": [
            {"id": a.id, "title": a.title, "source_id": a.source_id, "read": a.read}
            for a in recent
        ],
    })

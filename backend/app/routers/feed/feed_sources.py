"""feed - 订阅源 CRUD + 抓取。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feed import FeedSource
from app.utils.security import get_current_user
from app.routers.feed._common import (
    DEFAULT_CATEGORY,
    MAX_FEED_URL_LEN,
    FeedSourceIn,
    _guarded_source,
    _source_to_dict,
    ok,
    raise_http,
)
from app.routers.feed._fetch import _fetch_source_articles, _upsert_articles

router = APIRouter(prefix="/api/feeds", tags=["资讯推送-源"])


@router.get("/sources")
def list_sources(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    rows = (
        db.query(FeedSource)
        .filter(FeedSource.user_id == uid, FeedSource.deleted_at.is_(None))
        .order_by(FeedSource.id.desc())
        .all()
    )
    return ok({"list": [_source_to_dict(s) for s in rows]})


@router.post("/sources")
def create_source(
    payload: FeedSourceIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    url = (payload.feed_url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise_http(400, "订阅地址必须以 http:// 或 https:// 开头")

    source = FeedSource(
        user_id=uid,
        title=(payload.title or "").strip()[:255],
        feed_url=url[:MAX_FEED_URL_LEN],
        category=(payload.category or DEFAULT_CATEGORY).strip()[:32] or DEFAULT_CATEGORY,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # 抓取验证并入库（失败不阻断创建，记录错误状态）
    added = 0
    try:
        articles = _fetch_source_articles(source)
        added = _upsert_articles(db, source, articles)
        source.last_status = 1
        source.last_error = ""
        source.last_check_at = datetime.now()
        db.commit()
        db.refresh(source)
    except Exception as exc:  # noqa: BLE001
        source.last_status = 2
        source.last_error = str(exc)[:255]
        source.last_check_at = datetime.now()
        db.commit()
        db.refresh(source)

    data = _source_to_dict(source)
    data["added"] = added if source.last_status == 1 else 0
    return ok(data)


@router.put("/sources/{source_id}")
def update_source(
    source_id: int,
    payload: FeedSourceIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    source = _guarded_source(db, source_id, current_user["user_id"])
    url = (payload.feed_url or "").strip()
    if payload.feed_url and not url.startswith(("http://", "https://")):
        raise_http(400, "订阅地址必须以 http:// 或 https:// 开头")
    if payload.feed_url:
        source.feed_url = url[:MAX_FEED_URL_LEN]
    if payload.title:
        source.title = payload.title.strip()[:255]
    if payload.category:
        source.category = payload.category.strip()[:32]
    db.commit()
    db.refresh(source)
    return ok(_source_to_dict(source))


@router.post("/sources/{source_id}/fetch")
def fetch_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    source = _guarded_source(db, source_id, current_user["user_id"])
    try:
        articles = _fetch_source_articles(source)
        added = _upsert_articles(db, source, articles)
        source.last_status = 1
        source.last_error = ""
        source.last_check_at = datetime.now()
        db.commit()
        db.refresh(source)
        return ok({"added": added, "source": _source_to_dict(source)})
    except Exception as exc:  # noqa: BLE001
        source.last_status = 2
        source.last_error = str(exc)[:255]
        source.last_check_at = datetime.now()
        db.commit()
        return ok({"added": 0, "source": _source_to_dict(source), "error": source.last_error})


@router.post("/fetch-all")
def fetch_all(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """刷新当前用户所有订阅源。"""
    uid = current_user["user_id"]
    rows = (
        db.query(FeedSource)
        .filter(FeedSource.user_id == uid, FeedSource.deleted_at.is_(None))
        .all()
    )
    results = []
    for s in rows:
        try:
            articles = _fetch_source_articles(s)
            added = _upsert_articles(db, s, articles)
            s.last_status = 1
            s.last_error = ""
            s.last_check_at = datetime.now()
            results.append({"source_id": s.id, "added": added, "ok": True})
        except Exception as exc:  # noqa: BLE001
            s.last_status = 2
            s.last_error = str(exc)[:255]
            s.last_check_at = datetime.now()
            results.append({"source_id": s.id, "added": 0, "ok": False, "error": s.last_error})
    db.commit()
    return ok({"results": results})


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    source = _guarded_source(db, source_id, current_user["user_id"])
    source.deleted_at = datetime.now()
    db.commit()
    return ok({"id": source_id, "deleted": True})

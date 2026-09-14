"""feed 子路由共享工具。"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.feed import FeedArticle, FeedSource

# 默认分类
DEFAULT_CATEGORY = "综合"

# 抓取超时（秒）与正文长度上限
FETCH_TIMEOUT = 15
MAX_TITLE_LEN = 500
MAX_SUMMARY_LEN = 20000
MAX_CONTENT_LEN = 60000
MAX_FEED_URL_LEN = 2048


def ok(data=None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def raise_http(code: int, msg: str, http_status: int = 400) -> None:
    raise HTTPException(
        status_code=http_status,
        detail={"code": code, "msg": msg},
    )


# ---------- 序列化 ----------
def _source_to_dict(s: FeedSource) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "feed_url": s.feed_url,
        "site_url": s.site_url or "",
        "description": s.description or "",
        "category": s.category or DEFAULT_CATEGORY,
        "last_status": s.last_status,
        "last_error": s.last_error or "",
        "last_check_at": str(s.last_check_at) if s.last_check_at else "",
        "article_count": s.article_count,
        "created_at": str(s.created_at),
    }


_IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)


def _first_img_url(content_html: str) -> str:
    m = _IMG_SRC_RE.search(content_html or "")
    if not m:
        return ""
    url = m.group(1).strip()
    if url.startswith("//"):
        url = "https:" + url
    return url[:2048]


def _article_to_dict(a: FeedArticle, *, full: bool = False) -> dict:
    d = {
        "id": a.id,
        "source_id": a.source_id,
        "guid": a.guid,
        "title": a.title,
        "link": a.link or "",
        "author": a.author or "",
        "summary": a.summary or "",
        "image": (a.image or "") or _first_img_url(a.content_html),
        "title_zh": a.title_zh or "",
        "summary_zh": a.summary_zh or "",
        "is_foreign": a.is_foreign or 0,
        "ai_summary": a.ai_summary or "",
        "published_at": str(a.published_at) if a.published_at else "",
        "read": a.read,
        "bookmarked": a.bookmarked,
        "created_at": str(a.created_at),
    }
    if full:
        d["content_html"] = a.content_html or ""
        d["content"] = a.content or ""
        d["content_zh"] = a.content_zh or ""
    return d


# ---------- 守卫 ----------
def _guarded_source(db: Session, source_id: int, uid: int) -> FeedSource:
    s = (
        db.query(FeedSource)
        .filter(
            FeedSource.id == source_id,
            FeedSource.user_id == uid,
            FeedSource.deleted_at.is_(None),
        )
        .first()
    )
    if not s:
        raise_http(404, "订阅源不存在", 404)
    return s


def _guarded_article(db: Session, article_id: int, uid: int) -> FeedArticle:
    a = (
        db.query(FeedArticle)
        .filter(
            FeedArticle.id == article_id,
            FeedArticle.user_id == uid,
        )
        .first()
    )
    if not a:
        raise_http(404, "文章不存在", 404)
    return a


# ---------- 入参 ----------
class FeedSourceIn(BaseModel):
    feed_url: str = Field(..., min_length=1, max_length=2048)
    title: str = ""
    category: str = DEFAULT_CATEGORY

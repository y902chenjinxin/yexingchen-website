"""feed - 文章列表 / 详情 / 翻译 / 摘要 / 收藏 / 笔记化。"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feed import FeedArticle, FeedSource
from app.models.workbench import Note
from app.services.ai_providers import summarize_note
from app.services.translate import translate_summary, translate_text, translate_title
from app.utils.security import get_current_user
from app.routers.feed._common import (
    DEFAULT_CATEGORY,
    MAX_CONTENT_LEN,
    _article_to_dict,
    _guarded_article,
    ok,
    raise_http,
)

router = APIRouter(prefix="/api/feeds", tags=["资讯推送-文章"])


class ToNoteIn(BaseModel):
    with_summary: bool = True


@router.get("/articles")
def list_articles(
    source_id: int = 0,
    category: str = "",
    q: str = "",
    read: int = -1,
    bookmarked: int = -1,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    query = db.query(FeedArticle).filter(FeedArticle.user_id == uid)
    if source_id > 0:
        query = query.filter(FeedArticle.source_id == source_id)
    if category:
        ids = [
            sid for (sid,) in db.query(FeedSource.id).filter(
                FeedSource.user_id == uid,
                FeedSource.deleted_at.is_(None),
                FeedSource.category == category,
            ).all()
        ]
        query = query.filter(FeedArticle.source_id.in_(ids)) if ids else query.filter(False)
    if q:
        kw = f"%{q}%"
        query = query.filter(or_(FeedArticle.title.like(kw), FeedArticle.summary.like(kw)))
    if read == 0:
        query = query.filter(FeedArticle.read == 0)
    elif read == 1:
        query = query.filter(FeedArticle.read == 1)
    if bookmarked == 1:
        query = query.filter(FeedArticle.bookmarked == 1)

    total = query.count()
    rows = (
        query.order_by(FeedArticle.published_at.desc().nullslast(), FeedArticle.id.desc())
        .offset((page - 1) * size).limit(size)
        .all()
    )
    source_map = {
        s.id: s
        for s in db.query(FeedSource).filter(
            FeedSource.user_id == uid, FeedSource.deleted_at.is_(None)
        ).all()
    }
    items = []
    for a in rows:
        d = _article_to_dict(a)
        src = source_map.get(a.source_id)
        d["source_title"] = src.title if src else ""
        d["source_category"] = src.category if src else DEFAULT_CATEGORY
        items.append(d)
    return ok({"list": items, "total": total, "page": page, "size": size})


@router.get("/articles/{article_id}")
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    a = _guarded_article(db, article_id, uid)
    if not a.read:
        a.read = 1
        db.commit()
        db.refresh(a)
    d = _article_to_dict(a, full=True)
    src = (
        db.query(FeedSource).filter(
            FeedSource.id == a.source_id, FeedSource.user_id == uid
        ).first()
    )
    d["source_title"] = src.title if src else ""
    d["source_category"] = src.category if src else DEFAULT_CATEGORY
    return ok(d)


@router.post("/articles/{article_id}/translate")
def translate_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """外文文章按需翻译：标题+摘要+正文一次补齐，结果缓存入库。"""
    a = _guarded_article(db, article_id, current_user["user_id"])
    if a.is_foreign:
        if not (a.title_zh or "").strip():
            a.title_zh = translate_title(a.title or "")[:500]
        if not (a.summary_zh or "").strip():
            a.summary_zh = translate_summary(a.summary or "")[:8000]
        if not (a.content_zh or "").strip():
            content = (a.content or a.summary or "")[:12000]
            a.content_zh = translate_text(content)[:MAX_CONTENT_LEN]
        db.commit()
        db.refresh(a)
    d = _article_to_dict(a, full=True)
    return ok(d)


@router.delete("/articles/{article_id}")
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    a = _guarded_article(db, article_id, current_user["user_id"])
    db.delete(a)
    db.commit()
    return ok({"id": article_id, "deleted": True})


@router.post("/articles/{article_id}/summary")
def generate_summary(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    a = _guarded_article(db, article_id, current_user["user_id"])
    if a.ai_summary:
        return ok({"ai_summary": a.ai_summary, "cached": True})

    content = (a.content_zh or a.content or a.summary or a.title) or ""
    if not content.strip():
        raise_http(400, "文章内容为空，无法生成摘要")
    snippet = content[:6000]
    try:
        resp = summarize_note(snippet)
        summary = (resp.text or "").strip()
        if not summary:
            summary = str((resp.data or {}).get("summary", "")).strip()
        if summary:
            a.ai_summary = summary[:2000]
            db.commit()
            db.refresh(a)
            return ok({"ai_summary": a.ai_summary, "cached": False})
    except Exception:  # noqa: BLE001
        raise_http(502, "AI 摘要生成失败，请稍后重试", 502)
    raise_http(502, "AI 未返回有效摘要", 502)


@router.post("/articles/{article_id}/toggle-bookmark")
def toggle_bookmark(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    a = _guarded_article(db, article_id, current_user["user_id"])
    a.bookmarked = 0 if a.bookmarked else 1
    db.commit()
    db.refresh(a)
    return ok({"bookmarked": a.bookmarked})


@router.post("/articles/{article_id}/to-note")
def article_to_note(
    article_id: int,
    payload: ToNoteIn = Body(default=ToNoteIn()),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """将文章收藏为笔记（生成 AI 摘要并写入独立笔记）。"""
    uid = current_user["user_id"]
    a = _guarded_article(db, article_id, uid)

    ai_summary = a.ai_summary
    if payload.with_summary and not ai_summary:
        content = (a.content_zh or a.content or a.summary or a.title) or ""
        if content.strip():
            try:
                resp = summarize_note(content[:6000])
                ai_summary = (resp.text or "").strip() or str((resp.data or {}).get("summary", ""))
                if ai_summary:
                    a.ai_summary = ai_summary[:2000]
            except Exception:  # noqa: BLE001
                ai_summary = ""

    lines = []
    if ai_summary:
        lines.append(f"【AI 摘要】{a.ai_summary}")
    body_content = (a.content_zh or a.content or a.summary) or ""
    lines.append(body_content)
    body = "\n\n".join(x for x in lines if x).strip()
    if a.link:
        body = body + f"\n\n原文链接：{a.link}"
    if not body:
        body = a.title

    note = Note(
        user_id=uid,
        title=(a.title_zh or a.title)[:255] or "资讯收藏",
        content=body[:60000] or "（内容为空）",
        summary=ai_summary[:2000] or None,
        status="draft",
    )
    db.add(note)
    a.bookmarked = 1
    db.commit()
    db.refresh(note)
    return ok({"note_id": note.id, "title": note.title})

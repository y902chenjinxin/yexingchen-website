"""资讯推送模块。

RSS 订阅源 CRUD + 文章抓取 + 富文本渲染 + 中文翻译 + AI 摘要 + 收藏到笔记，数据按用户隔离。
- 源：增删改查 / 抓取 / 刷新
- 文章：列表 / 详情（自动标记已读）/ 翻译 / AI 摘要 / 收藏开关 / 收藏到笔记
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.security import get_current_user
from app.models.feed import FeedArticle, FeedSource
from app.models.workbench import Note
from app.services.ai_providers import summarize_note
from app.services.translate import is_cjk, translate_summary, translate_text, translate_title

router = APIRouter(prefix="/api/feeds", tags=["资讯推送"])

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
    from fastapi import HTTPException
    raise HTTPException(status_code=http_status, detail={"code": code, "msg": msg})


# ============================================================
# 序列化
# ============================================================
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


def _article_to_dict(a: FeedArticle, *, full: bool = False) -> dict:
    d = {
        "id": a.id,
        "source_id": a.source_id,
        "guid": a.guid,
        "title": a.title,
        "link": a.link or "",
        "author": a.author or "",
        "summary": a.summary or "",
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


# ============================================================
# 抓取工具
# ============================================================
def _clean_html(text: str) -> str:
    """去掉 HTML 标签与多余空白，返回纯文本。"""
    if not text:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;?", "&", text)
    text = re.sub(r"&lt;?", "<", text)
    text = re.sub(r"&gt;?", ">", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------- HTML 白名单清洗（富文本渲染用） ----------
_SAFE_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "dl", "dt", "dd",
    "blockquote", "pre", "code", "table", "thead", "tbody", "tfoot",
    "tr", "th", "td", "figure", "figcaption",
    "strong", "b", "em", "i", "u", "s", "a", "img", "span", "div", "section", "article",
}
_SAFE_ATTRS = {
    "a": ("href", "title", "target", "rel"),
    "img": ("src", "alt", "title", "loading", "width", "height"),
    "td": ("colspan", "rowspan"),
    "th": ("colspan", "rowspan"),
}
_DROP_ELEMS = (
    "script", "style", "iframe", "object", "embed", "form", "input",
    "button", "select", "textarea", "svg", "math", "noscript", "template",
    "video", "audio", "source", "link", "meta", "base", "frame", "frameset",
)
_TAG_RE = re.compile(
    r"<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^\s>]+)*?)\s*(/?)>", re.S
)
_ATTR_RE = re.compile(r'([a-zA-Z0-9:_-]+)(?:\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+))?')
_UNSAFE_PROTO = re.compile(r"^(javascript|vbscript|data):", re.I)


def _sanitize_html(text: str) -> str:
    """白名单清洗 RSS 正文 HTML：去脚本/事件/危险协议，图片加懒加载。"""
    if not text:
        return ""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    for tag in _DROP_ELEMS:
        text = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", " ", text, flags=re.S | re.I)
        text = re.sub(rf"</?{tag}[^>]*>", " ", text, flags=re.I)

    def fix(m: re.Match) -> str:
        closing, name, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3) or "", m.group(4)
        if name not in _SAFE_TAGS:
            return ""  # 非白名单标签：剥掉标签、保留内部文本
        if closing:
            return f"</{name}>"
        allowed = _SAFE_ATTRS.get(name)
        keep: list[str] = []
        for am in _ATTR_RE.finditer(attrs):
            an = am.group(1).lower()
            if allowed is None or an not in allowed or an.startswith("on"):
                continue
            val = (am.group(2) or "").strip().strip('"\'')
            if an in ("href", "src"):
                if _UNSAFE_PROTO.match(val) and not val.lower().startswith("data:image/"):
                    continue
                if an == "src" and val.startswith("//"):
                    val = "https:" + val
            keep.append(f'{an}="{val[:2000]}"')
        if name == "img" and "loading" not in {k.split("=")[0] for k in keep}:
            keep.append('loading="lazy"')
        attrs_str = (" " + " ".join(keep)) if keep else ""
        return f"<{name}{attrs_str}{' /' if selfclose and name in ('br', 'hr', 'img') else ''}>"

    text = _TAG_RE.sub(fix, text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except (ValueError, TypeError):
        try:
            # feedparser 的 struct_time
            from email.utils import mktime_tz, parsedate_tz
            ts = parsedate_tz(str(value))
            if ts:
                return datetime.fromtimestamp(mktime_tz(ts))
        except (ValueError, TypeError, OverflowError):
            pass
        return None


def _fetch_source_articles(source: FeedSource) -> List[dict]:
    """拉取一个源，返回待入库的文章列表（不含已存在 guid）。"""
    import requests

    headers = {"User-Agent": "Mozilla/5.0 (compatible; yexingchen-feed/1.0)"}
    resp = requests.get(source.feed_url, headers=headers, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    body = resp.content

    import feedparser
    parsed = feedparser.parse(body)
    if parsed.bozo and not parsed.entries:
        raise ValueError(parsed.get("bozo_exception") and str(parsed.bozo_exception) or "RSS 解析失败")

    if parsed.feed:
        if parsed.feed.get("title") and not source.title:
            source.title = str(parsed.feed.title)[:255]
        if parsed.feed.get("link") and not source.site_url:
            source.site_url = str(parsed.feed.link)[:2048]
        if not source.description and parsed.feed.get("subtitle"):
            source.description = str(parsed.feed.subtitle)[:500]

    out = []
    for entry in parsed.entries:
        guid = str(entry.get("id") or entry.get("guid") or entry.get("link") or "")[:255]
        if not guid:
            continue
        title = _clean_html(str(entry.get("title") or "无标题"))[:MAX_TITLE_LEN]
        link = str(entry.get("link") or "")[:2048]
        author = _clean_html(str(entry.get("author") or ""))[:128]
        summary_raw = str(entry.get("summary") or entry.get("description") or "")
        summary = _clean_html(summary_raw)[:MAX_SUMMARY_LEN]
        content_raw = ""
        if entry.get("content"):
            content_raw = entry["content"][0].get("value", "") if isinstance(entry["content"], list) else str(entry["content"])
        content = _clean_html(content_raw)[:MAX_CONTENT_LEN]
        if not content:
            content = summary
        published = _parse_dt(entry.get("published") or entry.get("updated") or entry.get("pubDate"))
        is_foreign = 0 if is_cjk(title + " " + summary) else 1
        out.append({
            "guid": guid,
            "title": title,
            "link": link,
            "author": author,
            "summary": summary,
            "content": content,
            "content_html": _sanitize_html(content_raw) or _sanitize_html(summary_raw),
            "is_foreign": is_foreign,
            "title_zh": "",
            "summary_zh": "",
            "published_at": published,
        })
    # 外文文章：并行自动翻译标题与摘要（失败静默保留原文）
    _translate_meta(out)
    return out


def _translate_pair(title: str, summary: str):
    return translate_title(title), translate_summary(summary)


def _translate_meta(articles: List[dict]) -> None:
    """对外文文章的标题/摘要做并行翻译（每篇 ≤10s，失败静默）。"""
    jobs = [(a, a["title"], a["summary"]) for a in articles if a["is_foreign"]]
    if not jobs:
        return
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_translate_pair, t, s): a for a, t, s in jobs}
        for fut in as_completed(futs, timeout=90):
            a = futs[fut]
            try:
                t, s = fut.result()
                if t:
                    a["title_zh"] = t[:500]
                if s:
                    a["summary_zh"] = s[:8000]
            except Exception:  # noqa: BLE001
                continue


def _upsert_articles(db: Session, source: FeedSource, articles: List[dict]) -> int:
    uid = source.user_id
    existing = {
        a.guid for a in db.query(FeedArticle.guid)
        .filter(FeedArticle.user_id == uid, FeedArticle.source_id == source.id)
        .all()
    }
    added = 0
    for art in articles:
        if art["guid"] in existing:
            continue
        db.add(FeedArticle(
            user_id=uid,
            source_id=source.id,
            guid=art["guid"],
            title=art["title"],
            link=art["link"],
            author=art["author"],
            summary=art["summary"],
            content=art["content"],
            content_html=art.get("content_html") or "",
            is_foreign=art.get("is_foreign") or 0,
            title_zh=art.get("title_zh") or "",
            summary_zh=art.get("summary_zh") or "",
            published_at=art["published_at"],
        ))
        existing.add(art["guid"])
        added += 1
    source.article_count = (
        db.query(FeedArticle).filter(
            FeedArticle.user_id == uid, FeedArticle.source_id == source.id
        ).count()
        + added
    )
    db.commit()
    return added


def _guarded_source(db: Session, source_id: int, uid: int) -> FeedSource:
    s = db.query(FeedSource).filter(
        FeedSource.id == source_id,
        FeedSource.user_id == uid,
        FeedSource.deleted_at.is_(None),
    ).first()
    if not s:
        raise_http(404, "订阅源不存在", 404)
    return s


def _guarded_article(db: Session, article_id: int, uid: int) -> FeedArticle:
    a = db.query(FeedArticle).filter(
        FeedArticle.id == article_id,
        FeedArticle.user_id == uid,
    ).first()
    if not a:
        raise_http(404, "文章不存在", 404)
    return a


# ============================================================
# 订阅源 CRUD
# ============================================================
class FeedSourceIn(BaseModel):
    feed_url: str = Field(..., min_length=1, max_length=2048)
    title: str = ""
    category: str = DEFAULT_CATEGORY


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
    data["added"] = added if "added" in locals() and source.last_status == 1 else 0
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


# ============================================================
# 文章列表 / 详情
# ============================================================
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


# ============================================================
# AI 摘要 / 收藏
# ============================================================
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
    # 摘要只看正文前若干字符，降低 token 成本
    snippet = content[:6000]
    try:
        resp = summarize_note(snippet)
        summary = (resp.text or "").strip()
        if not summary:
            # 部分 provider 把结果放 data.summary
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


class ToNoteIn(BaseModel):
    with_summary: bool = True


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
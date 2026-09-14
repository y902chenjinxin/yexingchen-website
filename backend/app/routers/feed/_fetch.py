"""feed 抓取 / 翻译 / upsert 内部工具。"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.feed import FeedArticle, FeedSource
from app.services.translate import is_cjk, translate_summary, translate_title
from app.routers.feed._common import (
    FETCH_TIMEOUT,
    MAX_CONTENT_LEN,
    MAX_SUMMARY_LEN,
    MAX_TITLE_LEN,
    raise_http,
)


# ---------- 文本清洗 ----------
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
_IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)


def _extract_image(entry, summary_raw: str, content_raw: str) -> str:
    """从 RSS entry 中提取首图 URL（media / enclosure / <img> 依次兜底）。"""
    candidate = ""

    def _pick(values) -> str:
        for v in values or []:
            if isinstance(v, dict):
                url = v.get("url") or v.get("href")
                if url:
                    return str(url)
            elif isinstance(v, str):
                return v
        return ""

    candidate = _pick(entry.get("media_content") or entry.get("media_thumbnail") or [])
    if not candidate:
        enc = entry.get("enclosure")
        if isinstance(enc, dict):
            t = str(enc.get("type") or "")
            url = enc.get("url") or enc.get("href")
            if url and ("image" in t or url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))):
                candidate = str(url)
        elif isinstance(enc, list):
            for e in enc:
                if isinstance(e, dict):
                    t = str(e.get("type") or "")
                    url = e.get("url") or e.get("href")
                    if url and ("image" in t or url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))):
                        candidate = str(url)
                        break
    if not candidate:
        img = entry.get("image")
        if isinstance(img, dict) and img.get("href"):
            candidate = str(img["href"])
    if not candidate:
        m = _IMG_SRC_RE.search(content_raw or "") or _IMG_SRC_RE.search(summary_raw or "")
        if m:
            candidate = m.group(1).strip()
    if not candidate:
        return ""
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    if _UNSAFE_PROTO.match(candidate) and not candidate.lower().startswith("data:image/"):
        return ""
    return candidate[:2048]


def _sanitize_html(text: str) -> str:
    """白名单清洗 RSS 正文 HTML：去脚本/事件/危险协议，图片加懒加载。"""
    if not text:
        return ""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    for tag in _DROP_ELEMS:
        text = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", " ", text, flags=re.S | re.I)
        text = re.sub(rf"</?{tag}[^>]*>", " ", text, flags=re.I)

    def fix(m: re.Match) -> str:
        closing, name, attrs, selfclose = (
            m.group(1),
            m.group(2).lower(),
            m.group(3) or "",
            m.group(4),
        )
        if name not in _SAFE_TAGS:
            return ""
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
            from email.utils import mktime_tz, parsedate_tz
            ts = parsedate_tz(str(value))
            if ts:
                return datetime.fromtimestamp(mktime_tz(ts))
        except (ValueError, TypeError, OverflowError):
            pass
        return None


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


def _fetch_source_articles(source: FeedSource) -> List[dict]:
    """拉取一个源，返回待入库的文章列表（不含已存在 guid）。"""
    import requests
    import feedparser

    headers = {"User-Agent": "Mozilla/5.0 (compatible; yexingchen-feed/1.0)"}
    resp = requests.get(source.feed_url, headers=headers, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    body = resp.content

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
            content_raw = (
                entry["content"][0].get("value", "")
                if isinstance(entry["content"], list)
                else str(entry["content"])
            )
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
            "image": _extract_image(entry, summary_raw, content_raw),
            "is_foreign": is_foreign,
            "title_zh": "",
            "summary_zh": "",
            "published_at": published,
        })
    _translate_meta(out)
    return out


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
            image=art.get("image") or "",
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
    return added

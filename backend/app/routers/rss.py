"""RSS 公开订阅源。

F9: 给玄黄个人站提供一份公开的 RSS 2.0 输出。
- 暴露最近 status='completed' 的笔记作为 channel item
- 不需要鉴权（公开内容）
- 末尾带 published/updated 时间、link 回到笔记详情页

注意：Note 模型当前没有 privacy / summary_md 字段；RSS 只暴露已完成笔记的标题与摘要前缀，
避免泄露草稿/隐私内容；如需更细粒度控制，模型加 privacy 字段后再调整过滤条件。
"""
from __future__ import annotations

from datetime import datetime
from email.utils import format_datetime
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workbench import Note

router = APIRouter(prefix="/rss", tags=["rss-公开订阅"])


def _rfc2822(dt: datetime | None) -> str:
    if not dt:
        return ""
    return format_datetime(dt)


@router.get("/notes.xml", response_class=PlainTextResponse, response_description="RSS 2.0 - 最近公开笔记")
def rss_public_notes(db: Session = Depends(get_db)):
    """最近 30 篇笔记（仅已完成，避免草稿外露）。"""
    rows: List[Note] = (
        db.query(Note)
        .filter(Note.deleted_at.is_(None))
        .filter(Note.status == "completed")
        .order_by(Note.updated_at.desc().nullslast(), Note.created_at.desc())
        .limit(30)
        .all()
    )

    last_build = datetime.utcnow()
    items_xml: List[str] = []
    for n in rows:
        link = f"https://yexingchen.cn/notes/{n.id}"
        title = (n.title or "（无标题）").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # 描述用 summary 字段（如果有），否则截取 content 前 600 字符
        desc = (n.summary or n.content or "")[:600]
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        pub = _rfc2822(n.updated_at or n.created_at)
        items_xml.append(
            "<item>"
            f"<title>{title}</title>"
            f"<link>{link}</link>"
            f"<guid isPermaLink=\"true\">{link}</guid>"
            f"<description>{desc}</description>"
            f"<pubDate>{pub}</pubDate>"
            "</item>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '<channel>\n'
        '<title>玄黄 · 叶兴辰的笔记</title>\n'
        '<link>https://yexingchen.cn/notes</link>\n'
        '<description>把零散念头，沉淀为数据。— 已完成笔记的 RSS 订阅源。</description>\n'
        '<language>zh-cn</language>\n'
        f'<lastBuildDate>{_rfc2822(last_build)}</lastBuildDate>\n'
        '<atom:link href="https://yexingchen.cn/rss/notes.xml" rel="self" type="application/rss+xml" />\n'
        + "\n".join(items_xml) +
        '\n</channel>\n</rss>\n'
    )
    return PlainTextResponse(content=xml, media_type="application/rss+xml; charset=utf-8")
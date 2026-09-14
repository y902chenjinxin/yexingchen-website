"""工作台数据导入 / 导出。

- 导出：当前用户的笔记、任务、标签关联；返回 JSON 包（含格式版本号）。
- 导入：接受同样的 JSON 包；merge 模式按 guid 去重，新对象分配新主键。

二进制资产（图片/PDF）不在此导出范围——文件由对象存储接管，
此端点只导出 asset 元数据列表，便于用户在导入时参考哪些资产被引用。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workbench import (
    AiConversation,
    Asset,
    Note,
    NoteTag,
    Tag,
    Task,
    TaskLink,
)
from app.utils.security import get_current_user
from app.routers.workbench._common import ok, raise_http

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-导入导出"])

EXPORT_FORMAT_VERSION = 1


# ---------- 导出 ----------
@router.post("/export")
def export_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导出当前用户的笔记 / 任务 / 标签 / 资产清单。"""
    uid = current_user["user_id"]

    notes = db.query(Note).filter(Note.user_id == uid, Note.deleted_at.is_(None)).all()
    tasks = db.query(Task).filter(Task.user_id == uid, Task.deleted_at.is_(None)).all()
    tags = db.query(Tag).filter(Tag.user_id == uid).all()
    assets = db.query(Asset).filter(Asset.user_id == uid, Asset.deleted_at.is_(None)).all()
    convs = db.query(AiConversation).filter(
        AiConversation.user_id == uid, AiConversation.deleted_at.is_(None)
    ).all()

    payload = {
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "notes": len(notes),
            "tasks": len(tasks),
            "tags": len(tags),
            "assets": len(assets),
            "ai_conversations": len(convs),
        },
        "tags": [{"name": t.name} for t in tags],
        "notes": [
            {
                "client_id": f"n{n.id}",  # 跨环境稳定标识
                "title": n.title,
                "content": n.content,
                "summary": n.summary,
                "status": n.status,
                "created_at": n.created_at.isformat() if n.created_at else None,
                "updated_at": n.updated_at.isformat() if n.updated_at else None,
                "completed_at": n.completed_at.isformat() if n.completed_at else None,
                "tag_names": [t.name for t in n.tags],
            }
            for n in notes
        ],
        "tasks": [
            {
                "client_id": f"t{t.id}",
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isformat() if t.due_date else None,
                "completed_at": t.completed_at.isformat() if t.completed_at else None,
                "created_at": t.created_at.isformat() if t.created_at else None,
                "updated_at": t.updated_at.isformat() if t.updated_at else None,
            }
            for t in tasks
        ],
        "assets": [
            {
                "client_id": f"a{a.id}",
                "type": a.type,
                "title": a.title,
                "description": a.description,
                "url": a.url,
                "original_filename": a.original_filename,
                "mime_type": a.mime_type,
                "file_size": a.file_size or 0,
                "tag_names": [t.name for t in a.tags],
                "created_at": a.created_at.isformat() if a.created_at else None,
            }
            for a in assets
        ],
        "ai_conversations": [
            {
                "client_id": f"c{c.id}",
                "title": c.title,
                "created_at": c.created_at.isformat() if c.created_at else None,
                "updated_at": c.updated_at.isformat() if c.updated_at else None,
            }
            for c in convs
        ],
    }
    return ok(payload)


# ---------- 导入 ----------
class ImportRequest(BaseModel):
    payload: dict = Field(..., description="同导出格式的 JSON 包")
    mode: str = Field("merge", description="merge：新对象新增；overwrite：覆盖标题相同的对象")
    include: Optional[list] = Field(
        None,
        description="None 表示全部；否则按子集：notes / tasks / tags / assets / ai_conversations",
    )


@router.post("/import")
def import_data(
    req: ImportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导入 JSON 包到当前用户。"""
    uid = current_user["user_id"]
    payload = req.payload
    if not isinstance(payload, dict):
        raise_http(400, "payload 必须是对象")

    fmt = payload.get("format_version")
    if fmt != EXPORT_FORMAT_VERSION:
        raise_http(400, f"不支持的 format_version={fmt!r}，当前期望 {EXPORT_FORMAT_VERSION}")

    mode = (req.mode or "merge").lower()
    if mode not in ("merge", "overwrite"):
        raise_http(400, "mode 必须是 merge 或 overwrite")

    inc = set(req.include) if req.include else None
    has = lambda name: inc is None or name in inc

    stats = {
        "tags_created": 0, "tags_skipped": 0,
        "notes_created": 0, "notes_updated": 0, "notes_skipped": 0,
        "tasks_created": 0, "tasks_updated": 0, "tasks_skipped": 0,
        "assets_created": 0, "assets_skipped": 0,
        "ai_conversations_created": 0, "ai_conversations_skipped": 0,
    }

    # ---------- 标签：name 全局唯一（按用户隔离）----------
    tag_map: dict[str, Tag] = {}
    if has("tags"):
        for t in payload.get("tags", []) or []:
            name = (t.get("name") or "").strip()
            if not name:
                stats["tags_skipped"] += 1
                continue
            existing = (
                db.query(Tag).filter(Tag.user_id == uid, Tag.name == name).first()
            )
            if existing:
                tag_map[name] = existing
                stats["tags_skipped"] += 1
                continue
            tag = Tag(name=name[:64], user_id=uid)
            db.add(tag)
            db.flush()
            tag_map[name] = tag
            stats["tags_created"] += 1

    # ---------- 笔记 ----------
    if has("notes"):
        for n in payload.get("notes", []) or []:
            title = (n.get("title") or "").strip()
            if not title:
                stats["notes_skipped"] += 1
                continue

            existing = None
            if mode == "overwrite":
                existing = (
                    db.query(Note)
                    .filter(Note.user_id == uid, Note.title == title, Note.deleted_at.is_(None))
                    .first()
                )

            tag_objs = []
            for tname in n.get("tag_names") or []:
                if tname in tag_map:
                    tag_objs.append(tag_map[tname])

            if existing:
                existing.title = title[:255]
                existing.content = n.get("content") or ""
                existing.summary = n.get("summary")
                if n.get("status") in ("draft", "completed"):
                    existing.status = n["status"]
                # 标签：直接替换关联
                db.query(NoteTag).filter(NoteTag.note_id == existing.id).delete()
                for t in tag_objs:
                    db.add(NoteTag(note_id=existing.id, tag_id=t.id))
                stats["notes_updated"] += 1
            else:
                note = Note(
                    user_id=uid,
                    title=title[:255],
                    content=n.get("content") or "",
                    summary=n.get("summary"),
                    status=n.get("status") if n.get("status") in ("draft", "completed") else "draft",
                )
                db.add(note)
                db.flush()
                for t in tag_objs:
                    db.add(NoteTag(note_id=note.id, tag_id=t.id))
                stats["notes_created"] += 1

    # ---------- 任务 ----------
    if has("tasks"):
        for t in payload.get("tasks", []) or []:
            title = (t.get("title") or "").strip()
            if not title:
                stats["tasks_skipped"] += 1
                continue

            existing = None
            if mode == "overwrite":
                existing = (
                    db.query(Task)
                    .filter(Task.user_id == uid, Task.title == title, Task.deleted_at.is_(None))
                    .first()
                )

            due = None
            if t.get("due_date"):
                try:
                    due = datetime.fromisoformat(t["due_date"])
                except (ValueError, TypeError):
                    due = None

            if existing:
                existing.description = t.get("description") or ""
                if t.get("status") in ("todo", "doing", "done"):
                    existing.status = t["status"]
                if t.get("priority") in ("low", "medium", "high"):
                    existing.priority = t["priority"]
                existing.due_date = due
                stats["tasks_updated"] += 1
            else:
                task = Task(
                    user_id=uid,
                    title=title[:255],
                    description=t.get("description") or "",
                    status=t.get("status") if t.get("status") in ("todo", "doing", "done") else "todo",
                    priority=t.get("priority") if t.get("priority") in ("low", "medium", "high") else "medium",
                    due_date=due,
                )
                db.add(task)
                stats["tasks_created"] += 1

    # ---------- 资产（仅元数据，文件本身不导入）----------
    if has("assets"):
        for a in payload.get("assets", []) or []:
            title = (a.get("title") or "").strip() or a.get("original_filename") or "(untitled)"
            url = (a.get("url") or "").strip()
            # 仅 link 类资产（外部 URL）有意义；file 资产文件未导入，跳过
            if a.get("type") != "link" or not url:
                stats["assets_skipped"] += 1
                continue
            existing = (
                db.query(Asset)
                .filter(Asset.user_id == uid, Asset.type == "link", Asset.url == url, Asset.deleted_at.is_(None))
                .first()
            )
            if existing:
                stats["assets_skipped"] += 1
                continue
            asset = Asset(
                user_id=uid,
                type="link",
                title=title[:255],
                description=(a.get("description") or "")[:2000],
                url=url[:2048],
                file_size=0,
            )
            db.add(asset)
            db.flush()
            for tname in a.get("tag_names") or []:
                if tname in tag_map:
                    asset.tags.append(tag_map[tname])
            stats["assets_created"] += 1

    # ---------- AI 对话（仅标题，不导入消息）----------
    if has("ai_conversations"):
        for c in payload.get("ai_conversations", []) or []:
            title = (c.get("title") or "新对话").strip()
            existing = (
                db.query(AiConversation)
                .filter(AiConversation.user_id == uid, AiConversation.title == title, AiConversation.deleted_at.is_(None))
                .first()
            )
            if existing:
                stats["ai_conversations_skipped"] += 1
                continue
            db.add(AiConversation(user_id=uid, title=title[:255]))
            stats["ai_conversations_created"] += 1

    db.commit()
    logger.info(
        "User %s imported workbench data (mode=%s): %s",
        uid, mode, json.dumps(stats, ensure_ascii=False),
    )
    return ok({"mode": mode, "stats": stats})

"""workbench 子路由共享工具。

- 统一响应包装（ok/fail/raise_http）
- 通用序列化（_to_iso）
- 通用分页（_paginate）
- 通用权限校验（_user_owned、_ensure_user_*）
- ORM → Pydantic 序列化器（_note_to_out、_asset_to_out、_task_to_out）
"""
from __future__ import annotations

from typing import Type

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.workbench import (
    AiConversation,
    Asset,
    Note,
    Task,
)
from app.services.softdelete import active_query
from app.routers.workbench._schemas import (
    AssetOut,
    NoteOut,
    TaskOut,
)


# ---------- 响应包装 ----------
def ok(data=None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data if data is not None else {}}


def fail(code: int, msg: str, http_status: int = 400, data=None) -> dict:
    raise HTTPException(
        status_code=http_status,
        detail={"code": code, "msg": msg, "data": data or {}},
    )


def raise_http(code: int, msg: str, http_status: int = 400) -> None:
    raise HTTPException(
        status_code=http_status,
        detail={"code": code, "msg": msg, "data": {}},
    )


# ---------- 序列化 ----------
def _to_iso(dt):
    return dt.isoformat() if dt else None


def _paginate(page: int, size: int, max_size: int = 100) -> tuple[int, int]:
    """校验并规范化 page/size。"""
    page = max(1, int(page or 1))
    size = max(1, min(int(size or 20), max_size))
    return page, size


# ---------- 权限校验 ----------
def _user_owned(db: Session, model, user_id: int):
    """当前用户的、未删除的资源。"""
    return active_query(db, model).filter(model.user_id == user_id)


def _ensure_user_note(db: Session, note_id: int, user_id: int) -> Note:
    n = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == user_id, Note.deleted_at.is_(None))
        .first()
    )
    if not n:
        raise_http(404, "笔记不存在", 404)
    return n


def _ensure_user_asset(db: Session, asset_id: int, user_id: int) -> Asset:
    a = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.user_id == user_id, Asset.deleted_at.is_(None))
        .first()
    )
    if not a:
        raise_http(404, "资产不存在", 404)
    return a


def _ensure_user_task(db: Session, task_id: int, user_id: int) -> Task:
    t = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None))
        .first()
    )
    if not t:
        raise_http(404, "任务不存在", 404)
    return t


def _ensure_user_conversation(db: Session, conv_id: int, user_id: int) -> AiConversation:
    c = (
        db.query(AiConversation)
        .filter(
            AiConversation.id == conv_id,
            AiConversation.user_id == user_id,
            AiConversation.deleted_at.is_(None),
        )
        .first()
    )
    if not c:
        raise_http(404, "AI 对话不存在", 404)
    return c


# ---------- ORM → Pydantic 序列化器 ----------
def _note_to_out(n: Note, *, db: Session | None = None) -> NoteOut:
    asset_ids = [a.id for a in (n.assets or [])]
    asset_total = sum(
        (a.file_size or 0)
        for a in (n.assets or [])
        if a.deleted_at is None
    )
    return NoteOut(
        id=n.id,
        title=n.title or "",
        content=n.content or "",
        status=n.status or "draft",
        summary=n.summary,
        user_id=n.user_id,
        created_at=_to_iso(n.created_at),
        updated_at=_to_iso(n.updated_at),
        completed_at=_to_iso(n.completed_at),
        deleted_at=_to_iso(n.deleted_at),
        tags=[t.name for t in (n.tags or [])],
        asset_ids=asset_ids,
        asset_total_size=asset_total,
    )


def _asset_to_out(a: Asset) -> AssetOut:
    note_ids = [n.id for n in (a.notes or []) if n.deleted_at is None]
    return AssetOut(
        id=a.id,
        type=a.type,
        title=a.title or "",
        description=a.description,
        url=a.url,
        storage_path=a.storage_path,
        original_filename=a.original_filename,
        mime_type=a.mime_type,
        file_size=a.file_size or 0,
        user_id=a.user_id,
        created_at=_to_iso(a.created_at),
        updated_at=_to_iso(a.updated_at),
        deleted_at=_to_iso(a.deleted_at),
        tags=[t.name for t in (a.tags or [])],
        note_ids=note_ids,
        cleanup_failed=bool(getattr(a, "cleanup_failed_at", None)),
    )


def _task_to_out(t: Task) -> TaskOut:
    note_ids = [l.note_id for l in (t.links or []) if l.note_id]
    asset_ids = [l.asset_id for l in (t.links or []) if l.asset_id]
    return TaskOut(
        id=t.id,
        title=t.title,
        description=t.description,
        status=t.status,
        priority=t.priority,
        due_date=_to_iso(t.due_date),
        completed_at=_to_iso(t.completed_at),
        user_id=t.user_id,
        created_at=_to_iso(t.created_at),
        updated_at=_to_iso(t.updated_at),
        note_ids=note_ids,
        asset_ids=asset_ids,
    )

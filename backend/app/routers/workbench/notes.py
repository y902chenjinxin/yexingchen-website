"""笔记、标签、笔记-资产关联。"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.workbench import (
    Asset,
    Note,
    NoteAsset,
    NoteTag,
    Tag,
)
from app.services.softdelete import (
    log_workbench_action,
    restore,
    soft_delete,
)
from app.utils.security import get_current_user
from app.utils.validation import check_note_attachment_total
from app.routers.workbench._common import (
    _asset_to_out,
    _ensure_user_asset,
    _ensure_user_note,
    _note_to_out,
    _paginate,
    _user_owned,
    ok,
    raise_http,
)
from app.routers.workbench._schemas import NoteIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-笔记"])


# ============================================================
# 笔记 CRUD
# ============================================================
@router.get("/notes")
def list_notes(
    q: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    tag: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    page, size = _paginate(page, size)
    query = _user_owned(db, Note, uid)
    if status_filter:
        query = query.filter(Note.status == status_filter)
    if q:
        query = query.filter(
            or_(Note.title.contains(q), Note.content.contains(q), Note.summary.contains(q))
        )
    if tag:
        query = query.join(Note.tags).filter(Tag.name == tag)
    total = query.count()
    # 预拉关联（避免 _note_to_out 里的 n.assets / n.tags 触发 N+1）
    items = (
        query.options(
            selectinload(Note.assets),
            selectinload(Note.tags),
        )
        .order_by(Note.updated_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ok({
        "list": [_note_to_out(n).model_dump() for n in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.post("/notes", status_code=201)
def create_note(
    payload: NoteIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = Note(
        user_id=current_user["user_id"],
        title=payload.title or "未命名草稿",
        content=payload.content or "",
        status=payload.status if payload.status in ("draft", "completed") else "draft",
        summary=payload.summary,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    log_workbench_action(
        db, user_id=note.user_id, action="create",
        target_type="note", target_id=note.id, detail=f"创建笔记：{note.title}",
    )
    return ok(_note_to_out(note).model_dump())


@router.get("/notes/{note_id}")
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    return ok(_note_to_out(note).model_dump())


@router.get("/notes/{note_id}/assets")
def list_note_assets(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    assets = [a for a in (note.assets or []) if a.deleted_at is None]
    return ok({"list": [_asset_to_out(a).model_dump() for a in assets]})


@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    payload: NoteIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    note.title = payload.title or note.title
    note.content = payload.content if payload.content is not None else note.content
    if payload.status in ("draft", "completed"):
        if payload.status == "completed" and note.status != "completed":
            note.completed_at = note.updated_at
        note.status = payload.status
    if payload.summary is not None:
        note.summary = payload.summary
    db.commit()
    db.refresh(note)
    log_workbench_action(
        db, user_id=note.user_id, action="update",
        target_type="note", target_id=note.id, detail=f"更新笔记：{note.title}",
    )
    return ok(_note_to_out(note).model_dump())


@router.put("/notes/{note_id}/status")
def set_note_status(
    note_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    status = payload.get("status")
    if status not in ("draft", "completed"):
        raise_http(400, "status 必须是 draft 或 completed", 400)
    if status == "completed" and note.status != "completed":
        note.completed_at = note.updated_at
    note.status = status
    db.commit()
    db.refresh(note)
    return ok(_note_to_out(note).model_dump())


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    soft_delete(note, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="delete",
        target_type="note", target_id=note_id, detail=f"删除笔记：{note.title}",
    )
    return ok({"ok": True})


@router.post("/notes/{note_id}/restore")
def restore_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == current_user["user_id"], Note.deleted_at.isnot(None))
        .first()
    )
    if not note:
        raise_http(404, "回收站中无此笔记", 404)
    restore(note, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="restore",
        target_type="note", target_id=note_id, detail=f"恢复笔记：{note.title}",
    )
    return ok(_note_to_out(note).model_dump())


@router.put("/notes/{note_id}/tags")
def set_note_tags(
    note_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    tag_names = payload.get("tags") or []
    if not isinstance(tag_names, list):
        raise_http(400, "tags 必须是数组", 400)
    new_tags = []
    for name in tag_names:
        name = str(name).strip()
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.user_id == current_user["user_id"], Tag.name == name).first()
        if not tag:
            tag = Tag(name=name, user_id=current_user["user_id"])
            db.add(tag)
            db.flush()
        new_tags.append(tag)
    # 删旧关联、写新关联
    db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()
    for t in new_tags:
        db.add(NoteTag(note_id=note_id, tag_id=t.id))
    note.tags = new_tags
    db.commit()
    db.refresh(note)
    return ok(_note_to_out(note).model_dump())


# ============================================================
# 标签
# ============================================================
@router.get("/tags")
def list_tags(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    rows = (
        db.query(Tag)
        .filter(Tag.user_id == uid)
        .order_by(Tag.name.asc())
        .all()
    )
    return ok({"list": [{"id": t.id, "name": t.name} for t in rows]})


# ============================================================
# 笔记-资产关联
# ============================================================
@router.post("/notes/{note_id}/assets/{asset_id}")
def attach_asset_to_note(
    note_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    note = _ensure_user_note(db, note_id, uid)
    asset = _ensure_user_asset(db, asset_id, uid)
    # 总大小校验
    existing = (
        db.query(NoteAsset).filter(NoteAsset.note_id == note_id).all()
    )
    existing_size = 0
    for na in existing:
        if na.asset and na.asset.deleted_at is None:
            existing_size += na.asset.file_size or 0
    try:
        check_note_attachment_total(existing_size, asset.file_size or 0)
    except ValueError as exc:
        raise_http(413, str(exc), 413)
    exists = (
        db.query(NoteAsset)
        .filter(NoteAsset.note_id == note_id, NoteAsset.asset_id == asset_id)
        .first()
    )
    if not exists:
        db.add(NoteAsset(note_id=note_id, asset_id=asset_id))
        db.commit()
    return ok(_note_to_out(note).model_dump())


@router.delete("/notes/{note_id}/assets/{asset_id}")
def detach_asset_from_note(
    note_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """真正从数据库删除 NoteAsset 关联。"""
    uid = current_user["user_id"]
    note = _ensure_user_note(db, note_id, uid)
    asset = _ensure_user_asset(db, asset_id, uid)
    db.query(NoteAsset).filter(
        NoteAsset.note_id == note_id, NoteAsset.asset_id == asset_id
    ).delete()
    db.commit()
    db.refresh(note)
    return ok(_note_to_out(note).model_dump())

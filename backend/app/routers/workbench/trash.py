"""回收站列表与清理（物理文件失败保留记录 + 标记重试）。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workbench import (
    AiConversation,
    Asset,
    Note,
    Task,
)
from app.services.softdelete import (
    TRASH_RETENTION_DAYS,
    trash_query,
)
from app.services.storage_service import get_storage
from app.utils.security import get_current_user
from app.routers.workbench._common import (
    _to_iso,
    ok,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-回收站"])


@router.get("/trash")
def list_trash(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    notes = trash_query(db, Note).filter(Note.user_id == uid).all()
    assets = trash_query(db, Asset).filter(Asset.user_id == uid).all()
    tasks = trash_query(db, Task).filter(Task.user_id == uid).all()
    convs = (
        trash_query(db, AiConversation).filter(AiConversation.user_id == uid).all()
    )
    return ok({
        "notes": [{"id": n.id, "title": n.title, "deleted_at": _to_iso(n.deleted_at)} for n in notes],
        "assets": [{"id": a.id, "title": a.title, "deleted_at": _to_iso(a.deleted_at)} for a in assets],
        "tasks": [{"id": t.id, "title": t.title, "deleted_at": _to_iso(t.deleted_at)} for t in tasks],
        "conversations": [
            {"id": c.id, "title": c.title, "deleted_at": _to_iso(c.deleted_at)}
            for c in convs
        ],
    })


@router.post("/trash/cleanup")
def cleanup_trash(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """立即清理超过 30 天的回收站内容。

    失败策略：
    - Asset 物理文件删除失败 → 保留记录，标记 cleanup_failed_at / cleanup_error，
      下次再试；数据库引用绝不丢失。
    """
    uid = current_user["user_id"]
    threshold = datetime.now() - timedelta(days=TRASH_RETENTION_DAYS)
    storage = get_storage()

    notes = (
        trash_query(db, Note).filter(Note.user_id == uid, Note.deleted_at < threshold).all()
    )
    assets = (
        trash_query(db, Asset).filter(Asset.user_id == uid, Asset.deleted_at < threshold).all()
    )
    tasks = (
        trash_query(db, Task).filter(Task.user_id == uid, Task.deleted_at < threshold).all()
    )
    convs = (
        trash_query(db, AiConversation)
        .filter(AiConversation.user_id == uid, AiConversation.deleted_at < threshold)
        .all()
    )

    counts = {"notes": 0, "assets": 0, "tasks": 0, "conversations": 0}
    failed = []

    # Asset：先尝试删物理文件；失败保留记录
    for a in assets:
        if a.storage_path:
            try:
                storage.delete(user_id=uid, storage_path=a.storage_path)
            except FileNotFoundError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning("cleanup asset file failed: id=%s err=%s", a.id, exc)
                a.cleanup_failed_at = datetime.now()
                a.cleanup_error = str(exc)[:500]
                db.add(a)
                failed.append({"id": a.id, "error": a.cleanup_error})
                continue
        db.delete(a)
        counts["assets"] += 1

    for n in notes:
        db.delete(n)
        counts["notes"] += 1
    for t in tasks:
        db.delete(t)
        counts["tasks"] += 1
    for c in convs:
        db.delete(c)
        counts["conversations"] += 1

    db.commit()

    return ok({
        "cleaned": counts,
        "retention_days": TRASH_RETENTION_DAYS,
        "failed_files": failed,
    })

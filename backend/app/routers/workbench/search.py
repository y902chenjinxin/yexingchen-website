"""全局搜索：跨笔记、资产、任务、标签。"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, text
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.workbench import (
    Asset,
    Note,
    Tag,
    Task,
)
from app.utils.security import get_current_user
from app.routers.workbench._common import (
    _asset_to_out,
    _note_to_out,
    _paginate,
    _task_to_out,
    _user_owned,
    ok,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-搜索"])


@router.get("/search")
def global_search(
    q: str = Query(..., min_length=1),
    type_filter: Optional[str] = Query(None, alias="type"),
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    page, size = _paginate(page, size, max_size=50)
    results = {"notes": [], "assets": [], "tasks": [], "tags": []}

    if not type_filter or type_filter == "note":
        # Note 走 FTS5：先 MATCH 拿候选 id 列表，再按用户隔离 + 软删过滤
        # 测试/未升级环境降级：note_fts 不存在则退回 LIKE
        try:
            fts_rows = db.execute(
                text("SELECT rowid FROM note_fts WHERE note_fts MATCH :q AND user_id = :uid ORDER BY rank LIMIT :lim OFFSET :off"),
                {"q": q, "uid": uid, "lim": size, "off": (page - 1) * size},
            ).fetchall()
            fts_ids = [row[0] for row in fts_rows]
            fts_available = True
        except Exception:  # noqa: BLE001
            fts_ids = None
            fts_available = False
        if not fts_available:
            notes = (
                _user_owned(db, Note, uid)
                .filter(or_(Note.title.contains(q), Note.content.contains(q), Note.summary.contains(q)))
                .options(selectinload(Note.assets), selectinload(Note.tags))
                .order_by(Note.updated_at.desc())
                .offset((page - 1) * size)
                .limit(size)
                .all()
            )
        elif fts_ids:
            notes = (
                db.query(Note)
                .filter(Note.id.in_(fts_ids), Note.user_id == uid, Note.deleted_at.is_(None))
                .options(selectinload(Note.assets), selectinload(Note.tags))
                .order_by(Note.updated_at.desc())
                .all()
            )
        else:
            notes = []
        results["notes"] = [_note_to_out(n).model_dump() for n in notes]

    if not type_filter or type_filter == "asset":
        # Asset 走 FTS5（不存则降级 LIKE）
        try:
            asset_ids = [
                r[0] for r in db.execute(
                    text("SELECT rowid FROM asset_fts WHERE asset_fts MATCH :q AND user_id = :uid ORDER BY rank LIMIT :lim OFFSET :off"),
                    {"q": q, "uid": uid, "lim": size, "off": (page - 1) * size},
                ).fetchall()
            ]
            fts_ok = True
        except Exception:  # noqa: BLE001
            asset_ids = None
            fts_ok = False
        if fts_ok and asset_ids is not None:
            assets = (
                db.query(Asset)
                .filter(Asset.id.in_(asset_ids), Asset.user_id == uid, Asset.deleted_at.is_(None))
                .options(selectinload(Asset.notes), selectinload(Asset.tags))
                .order_by(Asset.updated_at.desc())
                .all()
            )
        else:
            assets = (
                _user_owned(db, Asset, uid)
                .filter(
                    or_(
                        Asset.title.contains(q),
                        Asset.description.contains(q),
                        Asset.url.contains(q),
                        Asset.original_filename.contains(q),
                    )
                )
                .options(selectinload(Asset.notes), selectinload(Asset.tags))
                .order_by(Asset.updated_at.desc())
                .offset((page - 1) * size)
                .limit(size)
                .all()
            )
        results["assets"] = [_asset_to_out(a).model_dump() for a in assets]

    if not type_filter or type_filter == "task":
        # Task 走 FTS5（不存则降级 LIKE）
        try:
            task_ids = [
                r[0] for r in db.execute(
                    text("SELECT rowid FROM task_fts WHERE task_fts MATCH :q AND user_id = :uid ORDER BY rank LIMIT :lim OFFSET :off"),
                    {"q": q, "uid": uid, "lim": size, "off": (page - 1) * size},
                ).fetchall()
            ]
            fts_ok = True
        except Exception:  # noqa: BLE001
            task_ids = None
            fts_ok = False
        if fts_ok and task_ids is not None:
            tasks = (
                db.query(Task)
                .filter(Task.id.in_(task_ids), Task.user_id == uid, Task.deleted_at.is_(None))
                .options(selectinload(Task.links))
                .order_by(Task.created_at.desc())
                .all()
            )
        else:
            tasks = (
                _user_owned(db, Task, uid)
                .filter(or_(Task.title.contains(q), Task.description.contains(q)))
                .options(selectinload(Task.links))
                .order_by(Task.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
                .all()
            )
        results["tasks"] = [_task_to_out(t).model_dump() for t in tasks]

    if not type_filter or type_filter == "tag":
        tags = (
            db.query(Tag)
            .filter(Tag.user_id == uid, Tag.name.contains(q))
            .limit(size)
            .all()
        )
        results["tags"] = [{"id": t.id, "name": t.name} for t in tags]

    return ok({
        "q": q,
        "results": results,
        "page": page,
        "size": size,
    })

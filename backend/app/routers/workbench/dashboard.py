"""工作台首页聚合：今日/逾期任务、最近/草稿笔记。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workbench import Note, Task
from app.utils.security import get_current_user
from app.routers.workbench._common import (
    _note_to_out,
    _paginate,
    _task_to_out,
    _user_owned,
    ok,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-首页"])


@router.get("/summary")
def workbench_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    today_tasks = (
        _user_owned(db, Task, uid)
        .filter(Task.status != "done")
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date <= today_end)
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )
    overdue_tasks = (
        _user_owned(db, Task, uid)
        .filter(Task.status != "done")
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date < today_start)
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )
    recent_notes = (
        _user_owned(db, Note, uid)
        .order_by(Note.updated_at.desc())
        .limit(5)
        .all()
    )
    draft_notes = (
        _user_owned(db, Note, uid)
        .filter(Note.status == "draft")
        .order_by(Note.updated_at.desc())
        .limit(5)
        .all()
    )

    return ok({
        "today_tasks": [_task_to_out(t).model_dump() for t in today_tasks],
        "overdue_tasks": [_task_to_out(t).model_dump() for t in overdue_tasks],
        "recent_notes": [_note_to_out(n).model_dump() for n in recent_notes],
        "draft_notes": [_note_to_out(n).model_dump() for n in draft_notes],
    })

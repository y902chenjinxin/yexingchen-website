"""任务 CRUD、任务-笔记/资产关联。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.workbench import Task, TaskLink
from app.services.softdelete import (
    log_workbench_action,
    restore,
    soft_delete,
)
from app.utils.security import get_current_user
from app.routers.workbench._common import (
    _ensure_user_asset,
    _ensure_user_note,
    _ensure_user_task,
    _paginate,
    _task_to_out,
    _user_owned,
    ok,
    raise_http,
)
from app.routers.workbench._schemas import TaskIn, TaskUpdateIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-任务"])


@router.get("/tasks")
def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    page, size = _paginate(page, size)
    query = _user_owned(db, Task, uid)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if q:
        query = query.filter(or_(Task.title.contains(q), Task.description.contains(q)))
    total = query.count()
    # 预拉关联：避免 _task_to_out 里的 t.links 触发 N+1
    items = (
        query.options(selectinload(Task.links))
        .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ok({
        "list": [_task_to_out(t).model_dump() for t in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.post("/tasks", status_code=201)
def create_task(
    payload: TaskIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    due = None
    if payload.due_date:
        try:
            due = datetime.fromisoformat(payload.due_date)
        except ValueError:
            raise_http(400, "due_date 格式错误（应 ISO）", 400)
    task = Task(
        title=payload.title,
        description=payload.description or "",
        status=payload.status if payload.status in ("todo", "doing", "done") else "todo",
        priority=payload.priority if payload.priority in ("low", "medium", "high") else "medium",
        due_date=due,
        user_id=current_user["user_id"],
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="create",
        target_type="task", target_id=task.id, detail=f"创建任务：{task.title}",
    )
    return ok(_task_to_out(task).model_dump())


@router.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = _ensure_user_task(db, task_id, current_user["user_id"])
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.status is not None:
        if payload.status not in ("todo", "doing", "done"):
            raise_http(400, "status 非法", 400)
        task.status = payload.status
        if payload.status == "done" and not task.completed_at:
            task.completed_at = datetime.now()
    if payload.priority is not None:
        if payload.priority not in ("low", "medium", "high"):
            raise_http(400, "priority 非法", 400)
        task.priority = payload.priority
    if payload.due_date is not None:
        if payload.due_date == "":
            task.due_date = None
        else:
            try:
                task.due_date = datetime.fromisoformat(payload.due_date)
            except ValueError:
                raise_http(400, "due_date 格式错误（应 ISO）", 400)
    db.commit()
    db.refresh(task)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="update",
        target_type="task", target_id=task.id, detail=f"更新任务：{task.title}",
    )
    return ok(_task_to_out(task).model_dump())


@router.post("/tasks/{task_id}/links")
def link_task_to_content(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    task = _ensure_user_task(db, task_id, uid)
    note_id = payload.get("note_id")
    asset_id = payload.get("asset_id")
    if not (note_id or asset_id):
        raise_http(400, "必须提供 note_id 或 asset_id 之一", 400)
    if note_id:
        _ensure_user_note(db, note_id, uid)
    if asset_id:
        _ensure_user_asset(db, asset_id, uid)
    link = TaskLink(task_id=task_id, note_id=note_id, asset_id=asset_id)
    db.add(link)
    db.commit()
    db.refresh(task)
    return ok(_task_to_out(task).model_dump())


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = _ensure_user_task(db, task_id, current_user["user_id"])
    soft_delete(task, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="delete",
        target_type="task", target_id=task_id, detail=f"删除任务：{task.title}",
    )
    return ok({"ok": True})


@router.post("/tasks/{task_id}/restore")
def restore_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user["user_id"], Task.deleted_at.isnot(None))
        .first()
    )
    if not task:
        raise_http(404, "回收站中无此任务", 404)
    restore(task, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="restore",
        target_type="task", target_id=task_id, detail=f"恢复任务：{task.title}",
    )
    return ok(_task_to_out(task).model_dump())

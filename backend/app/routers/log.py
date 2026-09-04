from datetime import datetime

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ResponseBase
from app.utils.security import get_current_user
from app.models.user import OperationLog, User

router = APIRouter(prefix="/api/logs", tags=["日志岛"])


def _parse_dt(value):
    """解析 ISO/表单时间串，失败返回 None（不抛错，便于前端自由传参）。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _apply_scope(query, current_user):
    """非超管只能看/操作自己的日志。"""
    if current_user["role"] != "super_admin":
        query = query.filter(OperationLog.user_id == current_user["user_id"])
    return query


def _user_email_map(db: Session, items):
    user_ids = set(item.user_id for item in items)
    if not user_ids:
        return {}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return {u.id: u.email for u in users}


@router.get("", response_model=ResponseBase)
async def list_logs(
    page: int = 1,
    size: int = 50,
    action: str = None,
    target_type: str = None,
    q: str = None,
    start: str = None,
    end: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """操作日志列表：支持按时间范围(start/end)、动作、目标类型、关键词(q)查询。"""
    query = db.query(OperationLog)
    query = _apply_scope(query, current_user)

    if action:
        query = query.filter(OperationLog.action == action)
    if target_type:
        query = query.filter(OperationLog.target_type == target_type)

    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)
    if start_dt:
        query = query.filter(OperationLog.created_at >= start_dt)
    if end_dt:
        query = query.filter(OperationLog.created_at <= end_dt)

    if q:
        kw = f"%{q}%"
        query = query.filter(
            or_(
                OperationLog.detail.like(kw),
                OperationLog.target_type.like(kw),
                OperationLog.action.like(kw),
            )
        )

    total = query.count()
    items = (
        query.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    email_map = _user_email_map(db, items)

    return ResponseBase(data={
        "list": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "user_email": email_map.get(log.user_id, ""),
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "detail": log.detail,
                "ip_address": log.ip_address,
                "created_at": str(log.created_at),
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "size": size,
    })


@router.delete("", response_model=ResponseBase)
async def delete_logs(
    ids: list[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """批量删除操作日志（非超管仅限自己的日志）。"""
    if not ids:
        return ResponseBase(data={"deleted": 0})

    query = db.query(OperationLog).filter(OperationLog.id.in_(ids))
    query = _apply_scope(query, current_user)
    rows = query.all()
    for row in rows:
        db.delete(row)
    db.commit()
    return ResponseBase(data={"deleted": len(rows)})


@router.delete("/clear", response_model=ResponseBase)
async def clear_logs(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """清空操作日志：可限定时间范围；非超管仅清理自己的日志。"""
    query = db.query(OperationLog)
    query = _apply_scope(query, current_user)

    start_dt = _parse_dt(payload.get("start"))
    end_dt = _parse_dt(payload.get("end"))
    if start_dt:
        query = query.filter(OperationLog.created_at >= start_dt)
    if end_dt:
        query = query.filter(OperationLog.created_at <= end_dt)

    count = query.delete()
    db.commit()
    return ResponseBase(data={"deleted": count})
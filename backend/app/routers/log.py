from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user
from app.models.user import OperationLog, User

router = APIRouter(prefix="/api/logs", tags=["日志岛"])


@router.get("", response_model=ResponseBase)
async def list_logs(
    page: int = 1,
    size: int = 50,
    target_type: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 普通用户只能看自己的日志，管理员可以看所有
    query = db.query(OperationLog)

    if current_user["role"] != "super_admin":
        query = query.filter(OperationLog.user_id == current_user["user_id"])

    if target_type:
        query = query.filter(OperationLog.target_type == target_type)

    total = query.count()
    items = query.order_by(desc(OperationLog.created_at)).offset((page - 1) * size).limit(size).all()

    # 获取用户邮箱映射
    user_ids = set(item.user_id for item in items)
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    email_map = {u.id: u.email for u in users}

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
                "created_at": str(log.created_at)
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "size": size
    })
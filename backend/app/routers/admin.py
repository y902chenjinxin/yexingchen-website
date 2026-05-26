from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user, require_super_admin
from app.models.user import User
from app.services.log_service import log_action

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.get("/users", response_model=ResponseBase)
async def list_users(
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    query = db.query(User)
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return ResponseBase(
        data={
            "list": [
                {
                    "id": u.id,
                    "email": u.email,
                    "nickname": u.nickname,
                    "role": u.role,
                    "status": u.status,
                    "allowed_islands": u.allowed_islands,
                    "last_login_at": str(u.last_login_at) if u.last_login_at else None,
                    "created_at": str(u.created_at)
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "size": size
        }
    )


@router.post("/users/{user_id}/approve", response_model=ResponseBase)
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.status = "approved"
    db.commit()

    log_action(db, current_user["user_id"], "approve", target_type="user", target_id=user_id,
              detail=f"审批通过用户 {user.email}")

    return ResponseBase(msg="审批成功")


@router.post("/users/{user_id}/reject", response_model=ResponseBase)
async def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.status = "rejected"
    db.commit()

    log_action(db, current_user["user_id"], "reject", target_type="user", target_id=user_id,
              detail=f"拒绝用户 {user.email}")

    return ResponseBase(msg="已拒绝该申请")


@router.put("/users/{user_id}", response_model=ResponseBase)
async def update_user(
    user_id: int,
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if req.role is not None:
        if req.role not in ("normal", "super_admin"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的角色")
        user.role = req.role

    if req.status is not None:
        if req.status not in ("pending", "approved", "rejected"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的状态")
        user.status = req.status

    if req.allowed_islands is not None:
        user.allowed_islands = req.allowed_islands

    db.commit()

    log_action(db, current_user["user_id"], "update", target_type="user", target_id=user_id,
              detail=f"更新用户 {user.email} 信息")

    return ResponseBase(msg="更新成功")


@router.delete("/users/{user_id}", response_model=ResponseBase)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    log_action(db, current_user["user_id"], "delete", target_type="user", target_id=user_id,
              detail=f"删除用户 {user.email}")

    db.delete(user)
    db.commit()

    return ResponseBase(msg="删除成功")
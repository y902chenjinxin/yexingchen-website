"""管理员 - 用户管理。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.common import (
    ResponseBase,
    UserCreateRequest,
    UserUpdateRequest,
    validate_email,
    validate_password,
)
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.utils.security import get_password_hash, require_super_admin

router = APIRouter(prefix="/api/admin", tags=["管理员-用户"])


def _check_credentials(email: str, password: Optional[str], strict: bool) -> str:
    """超管建号 / 改密的凭据检查。

    strict=False（默认）：只挡空值，邮箱格式与密码强度一律放行——超管建的是家里人用的账号，
                         不该被「面向公网自主注册」的规则卡住。
    strict=True：套用公开注册同款规则（邮箱格式 + 密码强度），超管需要时按次选用。
    返回 strip 后的账号，供调用方落库（避免「 爸爸 」与「爸爸」被当成两个账号）。
    """
    account = (email or "").strip()
    if not account:
        raise_error(ErrCode.INVALID_PARAM, "账号不能为空")
    if not (password or "").strip():
        raise_error(ErrCode.INVALID_PARAM, "密码不能为空")
    if not strict:
        return account
    try:
        validate_email(account)
    except ValueError:
        raise_error(ErrCode.INVALID_PARAM, "账号格式不正确：启用严格校验时须为邮箱格式")
    try:
        validate_password(password)
    except ValueError as exc:
        raise_error(ErrCode.INVALID_PARAM, str(exc))
    return account


class UserRoleUpdateRequest(BaseModel):
    role: str
    is_super_admin: Optional[int] = None


class UserPasswordResetRequest(BaseModel):
    # 与 UserCreateRequest 同理：校验下移到路由层，由 strict_validation 决定是否启用
    password: str
    strict_validation: bool = False


@router.post("/users", response_model=ResponseBase)
async def create_user(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    account = _check_credentials(req.email, req.password, req.strict_validation)

    existing = db.query(User).filter(User.email == account).first()
    if existing:
        raise_error(ErrCode.REG_EMAIL_EXISTS)

    user = User(
        email=account,
        password_hash=get_password_hash(req.password),
        role=req.role,
        status=req.status,
        allowed_islands=req.allowed_islands,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db, current_user["user_id"], "create",
        target_type="user", target_id=user.id,
        detail=f"新增用户 {user.email}"
        + ("" if req.strict_validation else "（超管建号，已跳过格式/强度校验）"),
    )
    return ResponseBase(msg="用户创建成功")


@router.get("/users", response_model=ResponseBase)
async def list_users(
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    query = db.query(User)
    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
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
                    "created_at": str(u.created_at),
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "size": size,
        }
    )


@router.post("/users/{user_id}/approve", response_model=ResponseBase)
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)
    user.status = "approved"
    db.commit()
    log_action(
        db, current_user["user_id"], "approve",
        target_type="user", target_id=user_id,
        detail=f"审批通过用户 {user.email}",
    )
    return ResponseBase(msg="审批成功")


@router.post("/users/{user_id}/reject", response_model=ResponseBase)
async def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)
    user.status = "rejected"
    db.commit()
    log_action(
        db, current_user["user_id"], "reject",
        target_type="user", target_id=user_id,
        detail=f"拒绝用户 {user.email}",
    )
    return ResponseBase(msg="已拒绝该申请")


@router.put("/users/{user_id}", response_model=ResponseBase)
async def update_user(
    user_id: int,
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)

    if req.role is not None:
        if req.role not in ("normal", "super_admin"):
            raise_error(ErrCode.INVALID_PARAM, "无效的角色")
        user.role = req.role

    if req.status is not None:
        if req.status not in ("pending", "approved", "rejected"):
            raise_error(ErrCode.INVALID_PARAM, "无效的状态")
        user.status = req.status

    if req.allowed_islands is not None:
        user.allowed_islands = req.allowed_islands

    db.commit()
    log_action(
        db, current_user["user_id"], "update",
        target_type="user", target_id=user_id,
        detail=f"更新用户 {user.email} 信息",
    )
    return ResponseBase(msg="更新成功")


@router.put("/users/{user_id}/role", response_model=ResponseBase)
async def update_user_role(
    user_id: int,
    req: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)

    if req.role not in ("user", "admin", "super_admin"):
        raise_error(ErrCode.INVALID_PARAM, "无效的角色")
    if user_id == current_user["user_id"] and req.is_super_admin is not None:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "不能修改自己的超级管理员权限")

    user.role = req.role
    if req.is_super_admin is not None:
        user.is_super_admin = req.is_super_admin

    db.commit()
    log_action(
        db, current_user["user_id"], "update_role",
        target_type="user", target_id=user_id,
        detail=f"更新用户 {user.email} 角色为 {req.role}",
    )
    return ResponseBase(msg="角色更新成功")


@router.post("/users/{user_id}/reset-password", response_model=ResponseBase)
async def reset_user_password(
    user_id: int,
    req: UserPasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)
    # 改密与建号同一套规则：默认只挡空值，strict_validation=True 时套用公开注册的密码强度
    _check_credentials(user.email, req.password, req.strict_validation)
    user.password_hash = get_password_hash(req.password)
    db.commit()
    log_action(
        db, current_user["user_id"], "reset_password",
        target_type="user", target_id=user_id,
        detail=f"重置用户 {user.email} 密码"
        + ("" if req.strict_validation else "（超管操作，已跳过强度校验）"),
    )
    return ResponseBase(msg="密码重置成功")


@router.delete("/users/{user_id}", response_model=ResponseBase)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    if user_id == current_user["user_id"]:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "不能删除自己")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)

    log_action(
        db, current_user["user_id"], "delete",
        target_type="user", target_id=user_id,
        detail=f"删除用户 {user.email}",
    )
    db.delete(user)
    db.commit()
    return ResponseBase(msg="删除成功")

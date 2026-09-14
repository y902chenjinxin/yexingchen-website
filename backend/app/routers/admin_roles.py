"""管理员 - 角色管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import Role
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.utils.security import require_super_admin

router = APIRouter(prefix="/api/admin", tags=["管理员-角色"])


def _role_to_dict(r: Role) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "code": r.code,
        "description": r.description,
        "permissions": r.permissions,
        "sort_order": r.sort_order,
        "is_builtin": r.is_builtin,
        "created_at": str(r.created_at),
    }


class RoleIn(BaseModel):
    name: str = ""
    code: str = ""
    description: str = ""
    permissions: str = "[]"
    sort_order: int = 0


@router.get("/roles", response_model=ResponseBase)
async def list_roles(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    rows = db.query(Role).order_by(Role.sort_order, Role.id).all()
    return ResponseBase(data={"list": [_role_to_dict(r) for r in rows]})


@router.post("/roles", response_model=ResponseBase)
async def create_role(
    req: RoleIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    code = req.code.strip()
    if not code:
        raise_error(ErrCode.INVALID_PARAM, "角色标识不能为空")
    if db.query(Role).filter(Role.code == code).first():
        raise_error(ErrCode.INVALID_PARAM, "角色标识已存在")
    role = Role(
        name=req.name.strip()[:40] or code,
        code=code[:40],
        description=req.description.strip()[:255],
        permissions=req.permissions[:2000] or "[]",
        sort_order=req.sort_order,
        is_builtin=0,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    log_action(
        db, current_user["user_id"], "create",
        target_type="role", target_id=role.id,
        detail=f"新增角色 {role.name}({role.code})",
    )
    return ResponseBase(data=_role_to_dict(role), msg="角色创建成功")


@router.put("/roles/{role_id}", response_model=ResponseBase)
async def update_role(
    role_id: int,
    req: RoleIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise_error(ErrCode.INVALID_PARAM, "角色不存在")
    if req.code.strip() and req.code.strip() != role.code:
        if role.is_builtin:
            raise_error(ErrCode.AUTH_PERMISSION_DENIED, "内置角色不可修改标识")
        if db.query(Role).filter(Role.code == req.code.strip()).first():
            raise_error(ErrCode.INVALID_PARAM, "角色标识已存在")
        role.code = req.code.strip()[:40]
    if req.name:
        role.name = req.name.strip()[:40]
    if req.description is not None:
        role.description = req.description.strip()[:255]
    if req.permissions:
        role.permissions = req.permissions[:2000]
    role.sort_order = req.sort_order
    db.commit()
    log_action(
        db, current_user["user_id"], "update",
        target_type="role", target_id=role.id,
        detail=f"更新角色 {role.name}({role.code})",
    )
    return ResponseBase(data=_role_to_dict(role), msg="更新成功")


@router.delete("/roles/{role_id}", response_model=ResponseBase)
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise_error(ErrCode.INVALID_PARAM, "角色不存在")
    if role.is_builtin:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "内置角色不可删除")
    log_action(
        db, current_user["user_id"], "delete",
        target_type="role", target_id=role_id,
        detail=f"删除角色 {role.name}({role.code})",
    )
    db.delete(role)
    db.commit()
    return ResponseBase(msg="删除成功")

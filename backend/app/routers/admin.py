from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user, require_super_admin
from app.models.user import User
from app.models.admin import Role, Menu
from app.services.log_service import log_action
from app.schemas.common import UserCreateRequest

from app.utils.security import get_password_hash

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.post("/users", response_model=ResponseBase)
async def create_user(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    # 检查邮箱是否已存在
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise_error(ErrCode.REG_EMAIL_EXISTS)

    user = User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        role=req.role,
        status=req.status,
        allowed_islands=req.allowed_islands
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, current_user["user_id"], "create", target_type="user", target_id=user.id,
                detail=f"新增用户 {user.email}")

    return ResponseBase(msg="用户创建成功")


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
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)

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
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)

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

    log_action(db, current_user["user_id"], "update", target_type="user", target_id=user_id,
              detail=f"更新用户 {user.email} 信息")

    return ResponseBase(msg="更新成功")


class UserRoleUpdateRequest(BaseModel):
    role: str
    is_super_admin: Optional[int] = None


@router.put("/users/{user_id}/role", response_model=ResponseBase)
async def update_user_role(
    user_id: int,
    req: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)

    # 验证角色
    if req.role not in ("user", "admin", "super_admin"):
        raise_error(ErrCode.INVALID_PARAM, "无效的角色")

    # 不能修改自己的超级管理员权限
    if user_id == current_user["user_id"] and req.is_super_admin is not None:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "不能修改自己的超级管理员权限")

    user.role = req.role
    if req.is_super_admin is not None:
        user.is_super_admin = req.is_super_admin

    db.commit()

    log_action(db, current_user["user_id"], "update_role", target_type="user", target_id=user_id,
              detail=f"更新用户 {user.email} 角色为 {req.role}")

    return ResponseBase(msg="角色更新成功")


@router.delete("/users/{user_id}", response_model=ResponseBase)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    if user_id == current_user["user_id"]:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "不能删除自己")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)

    log_action(db, current_user["user_id"], "delete", target_type="user", target_id=user_id,
              detail=f"删除用户 {user.email}")

    db.delete(user)
    db.commit()

    return ResponseBase(msg="删除成功")


# ============================================================
# 角色管理
# ============================================================
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
    log_action(db, current_user["user_id"], "create", target_type="role", target_id=role.id,
               detail=f"新增角色 {role.name}({role.code})")
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
    log_action(db, current_user["user_id"], "update", target_type="role", target_id=role.id,
               detail=f"更新角色 {role.name}({role.code})")
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
    log_action(db, current_user["user_id"], "delete", target_type="role", target_id=role_id,
               detail=f"删除角色 {role.name}({role.code})")
    db.delete(role)
    db.commit()
    return ResponseBase(msg="删除成功")


# ============================================================
# 菜单管理
# ============================================================
def _menu_to_dict(m: Menu) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "path": m.path,
        "icon": m.icon,
        "sort_order": m.sort_order,
        "is_enabled": m.is_enabled,
        "is_builtin": m.is_builtin,
        "created_at": str(m.created_at),
    }


class MenuIn(BaseModel):
    title: str = ""
    path: str = ""
    icon: str = ""
    sort_order: int = 0
    is_enabled: int = 1


@router.get("/menus", response_model=ResponseBase)
async def list_menus(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    rows = db.query(Menu).order_by(Menu.sort_order, Menu.id).all()
    return ResponseBase(data={"list": [_menu_to_dict(m) for m in rows]})


@router.get("/menus/public", response_model=ResponseBase)
async def list_public_menus(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """登录用户可见的启用菜单（顶栏导航用，按启用+排序过滤）。"""
    rows = (
        db.query(Menu)
        .filter(Menu.is_enabled == 1)
        .order_by(Menu.sort_order, Menu.id)
        .all()
    )
    return ResponseBase(data={"list": [_menu_to_dict(m) for m in rows]})


@router.post("/menus", response_model=ResponseBase)
async def create_menu(
    req: MenuIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    path = req.path.strip()
    if not path.startswith("/"):
        raise_error(ErrCode.INVALID_PARAM, "路径必须以 / 开头")
    if db.query(Menu).filter(Menu.path == path).first():
        raise_error(ErrCode.INVALID_PARAM, "菜单路径已存在")
    menu = Menu(
        title=req.title.strip()[:60] or path,
        path=path[:255],
        icon=req.icon.strip()[:60],
        sort_order=req.sort_order,
        is_enabled=1 if req.is_enabled else 0,
        is_builtin=0,
    )
    db.add(menu)
    db.commit()
    db.refresh(menu)
    log_action(db, current_user["user_id"], "create", target_type="menu", target_id=menu.id,
               detail=f"新增菜单 {menu.title}({menu.path})")
    return ResponseBase(data=_menu_to_dict(menu), msg="菜单创建成功")


@router.put("/menus/{menu_id}", response_model=ResponseBase)
async def update_menu(
    menu_id: int,
    req: MenuIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    menu = db.query(Menu).filter(Menu.id == menu_id).first()
    if not menu:
        raise_error(ErrCode.INVALID_PARAM, "菜单不存在")
    if req.path.strip() and req.path.strip() != menu.path:
        if menu.is_builtin:
            raise_error(ErrCode.AUTH_PERMISSION_DENIED, "内置菜单不可修改路径")
        if not req.path.strip().startswith("/"):
            raise_error(ErrCode.INVALID_PARAM, "路径必须以 / 开头")
        if db.query(Menu).filter(Menu.path == req.path.strip()).first():
            raise_error(ErrCode.INVALID_PARAM, "菜单路径已存在")
        menu.path = req.path.strip()[:255]
    if req.title:
        menu.title = req.title.strip()[:60]
    if req.icon is not None:
        menu.icon = req.icon.strip()[:60]
    menu.sort_order = req.sort_order
    menu.is_enabled = 1 if req.is_enabled else 0
    db.commit()
    log_action(db, current_user["user_id"], "update", target_type="menu", target_id=menu.id,
               detail=f"更新菜单 {menu.title}({menu.path})")
    return ResponseBase(data=_menu_to_dict(menu), msg="更新成功")


@router.delete("/menus/{menu_id}", response_model=ResponseBase)
async def delete_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    menu = db.query(Menu).filter(Menu.id == menu_id).first()
    if not menu:
        raise_error(ErrCode.INVALID_PARAM, "菜单不存在")
    if menu.is_builtin:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "内置菜单不可删除")
    log_action(db, current_user["user_id"], "delete", target_type="menu", target_id=menu_id,
               detail=f"删除菜单 {menu.title}({menu.path})")
    db.delete(menu)
    db.commit()
    return ResponseBase(msg="删除成功")
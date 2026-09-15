"""管理员 - 菜单管理。"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import Menu, Role
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.utils.security import get_current_user, require_super_admin

router = APIRouter(prefix="/api/admin", tags=["管理员-菜单"])


def _menu_to_dict(m: Menu) -> dict:
    return {
        "id": m.id,
        "parent_id": m.parent_id,
        "title": m.title,
        "path": m.path,
        "icon": m.icon,
        "sort_order": m.sort_order,
        "is_enabled": m.is_enabled,
        "is_builtin": m.is_builtin,
        "created_at": str(m.created_at),
    }


class MenuIn(BaseModel):
    parent_id: int = 0
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
    """登录用户可见的启用菜单（顶栏导航用，按角色 menu_ids 过滤）。

    - super_admin：恒见全部启用菜单
    - 其余角色：若其 role.menu_ids 为空(未配置) → 全部启用菜单；否则仅返回其中 id 命中的菜单
      另：父菜单只是容器，只要任一子项被允许，父菜单一并放行
      （否则会出现「超管明明勾了『账本』，用户却连『数据一览』入口都看不到」）
    """
    rows = (
        db.query(Menu)
        .filter(Menu.is_enabled == 1)
        .order_by(Menu.sort_order, Menu.id)
        .all()
    )
    if current_user.get("is_super_admin") == 1:
        return ResponseBase(data={"list": [_menu_to_dict(m) for m in rows]})
    try:
        menu_ids = _role_allowed_menu_ids(db, current_user.get("role"))
    except Exception:
        menu_ids = None
    if not menu_ids:
        return ResponseBase(data={"list": [_menu_to_dict(m) for m in rows]})

    allowed = {int(x) for x in menu_ids if str(x).strip().lstrip("-").isdigit()}
    allowed |= {m.parent_id for m in rows if m.id in allowed and m.parent_id}
    filtered = [m for m in rows if m.id in allowed]
    return ResponseBase(data={"list": [_menu_to_dict(m) for m in filtered]})


def _role_allowed_menu_ids(db: Session, role_code: Optional[str]) -> list:
    """返回指定角色 code 允许可见的菜单 id 列表；未配置时返回空（表示全部）。"""
    if not role_code:
        return []
    role = db.query(Role).filter(Role.code == role_code).first()
    if not role or not role.menu_ids:
        return []
    try:
        parsed = json.loads(role.menu_ids)
    except Exception:
        return []
    return [int(x) for x in parsed] if isinstance(parsed, list) else []


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
    parent_id = _validate_parent(db, req.parent_id, None)
    menu = Menu(
        parent_id=parent_id,
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
    log_action(
        db, current_user["user_id"], "create",
        target_type="menu", target_id=menu.id,
        detail=f"新增菜单 {menu.title}({menu.path})",
    )
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
    menu.parent_id = _validate_parent(db, req.parent_id, menu_id)
    menu.sort_order = req.sort_order
    menu.is_enabled = 1 if req.is_enabled else 0
    db.commit()
    log_action(
        db, current_user["user_id"], "update",
        target_type="menu", target_id=menu.id,
        detail=f"更新菜单 {menu.title}({menu.path})",
    )
    return ResponseBase(data=_menu_to_dict(menu), msg="更新成功")


def _validate_parent(db: Session, parent_id: int, self_id: Optional[int]) -> int:
    """校验并规范化父菜单：仅支持一级(0) / 二级(parent>0)，父菜单本身必须是一级模块。"""
    parent_id = parent_id or 0
    if parent_id == 0:
        return 0
    if parent_id == self_id:
        raise_error(ErrCode.INVALID_PARAM, "不能选择自身作为上级模块")
    parent = db.query(Menu).filter(Menu.id == parent_id).first()
    if not parent:
        raise_error(ErrCode.INVALID_PARAM, "上级模块不存在")
    if parent.parent_id != 0:
        raise_error(ErrCode.INVALID_PARAM, "仅支持一级/二级模块：上级模块须为一级模块")
    return parent_id


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
    if db.query(Menu).filter(Menu.parent_id == menu_id).first():
        raise_error(ErrCode.INVALID_PARAM, "该模块下存在二级模块，请先删除或转移后再删")
    log_action(
        db, current_user["user_id"], "delete",
        target_type="menu", target_id=menu_id,
        detail=f"删除菜单 {menu.title}({menu.path})",
    )
    db.delete(menu)
    db.commit()
    return ResponseBase(msg="删除成功")

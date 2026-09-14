"""管理员 - 菜单管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import Menu
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.utils.security import get_current_user, require_super_admin

router = APIRouter(prefix="/api/admin", tags=["管理员-菜单"])


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
    menu.sort_order = req.sort_order
    menu.is_enabled = 1 if req.is_enabled else 0
    db.commit()
    log_action(
        db, current_user["user_id"], "update",
        target_type="menu", target_id=menu.id,
        detail=f"更新菜单 {menu.title}({menu.path})",
    )
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
    log_action(
        db, current_user["user_id"], "delete",
        target_type="menu", target_id=menu_id,
        detail=f"删除菜单 {menu.title}({menu.path})",
    )
    db.delete(menu)
    db.commit()
    return ResponseBase(msg="删除成功")

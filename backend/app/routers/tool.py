from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user
from app.models.user import Tool
from app.services.log_service import log_action

router = APIRouter(prefix="/api/tools", tags=["工具岛"])


@router.get("", response_model=ResponseBase)
async def list_tools(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    q: str = Query(None, description="按名称/描述模糊搜索"),
    enabled_only: int = Query(0, description="1=仅上架内置与外部工具；0=全部（含下架，用于管理页）")
):
    query = db.query(Tool)
    if q:
        query = query.filter(or_(Tool.title.contains(q), Tool.description.contains(q)))
    if enabled_only:
        query = query.filter(Tool.is_enabled == 1)
    items = query.order_by(Tool.sort_order.asc(), Tool.id.asc()).all()

    return ResponseBase(data={
        "list": [
            {
                "id": t.id,
                "title": t.title,
                "url": t.url,
                "description": t.description,
                "icon": t.icon,
                "uploader_id": t.uploader_id,
                "kind": t.kind or "external",
                "is_enabled": t.is_enabled,
                "sort_order": t.sort_order,
                "created_at": str(t.created_at)
            }
            for t in items
        ]
    })


@router.post("", response_model=ResponseBase)
async def create_tool(
    req: ToolCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 外部工具默认追加到外部区末尾
    last = db.query(Tool).filter(Tool.kind == "external").order_by(Tool.sort_order.desc()).first()
    tool = Tool(
        title=req.title,
        url=req.url,
        description=req.description or "",
        icon=req.icon or "",
        uploader_id=current_user["user_id"],
        kind="external",
        is_enabled=1,
        sort_order=(last.sort_order + 1 if last else 100000)
    )
    db.add(tool)
    db.commit()

    log_action(db, current_user["user_id"], "upload", "tool", tool.id,
               detail=f"添加工具：{req.title}")

    return ResponseBase(msg="添加成功", data={"id": tool.id})


@router.put("/{tool_id}", response_model=ResponseBase)
async def update_tool(
    tool_id: int,
    req: ToolUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise_error(ErrCode.TOOL_NOT_FOUND)

    if req.title is not None:
        tool.title = req.title
    if req.url is not None:
        tool.url = req.url
    if req.description is not None:
        tool.description = req.description
    if req.icon is not None:
        tool.icon = req.icon
    if req.is_enabled is not None:
        tool.is_enabled = 1 if req.is_enabled else 0
    if req.sort_order is not None:
        tool.sort_order = req.sort_order

    db.commit()

    log_action(db, current_user["user_id"], "update", "tool", tool_id,
               detail=f"更新工具：{tool.title}")

    return ResponseBase(msg="更新成功")


@router.delete("/{tool_id}", response_model=ResponseBase)
async def delete_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise_error(ErrCode.TOOL_NOT_FOUND)

    # 内置工具不允许删除，防止误删核心功能
    if tool.kind == "builtin":
        raise_error(ErrCode.FORBIDDEN, detail="内置工具不可删除，可改为下架")

    log_action(db, current_user["user_id"], "delete", "tool", tool_id,
               detail=f"删除工具：{tool.title}")

    db.delete(tool)
    db.commit()

    return ResponseBase(msg="删除成功")
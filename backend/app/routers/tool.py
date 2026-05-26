from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user
from app.models.user import Tool
from app.services.log_service import log_action

router = APIRouter(prefix="/api/tools", tags=["工具岛"])


@router.get("", response_model=ResponseBase)
async def list_tools(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    items = db.query(Tool).order_by(Tool.created_at.desc()).all()

    return ResponseBase(data={
        "list": [
            {
                "id": t.id,
                "title": t.title,
                "url": t.url,
                "description": t.description,
                "icon": t.icon,
                "uploader_id": t.uploader_id,
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
    tool = Tool(
        title=req.title,
        url=req.url,
        description=req.description or "",
        icon=req.icon or "",
        uploader_id=current_user["user_id"]
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工具不存在")

    if req.title is not None:
        tool.title = req.title
    if req.url is not None:
        tool.url = req.url
    if req.description is not None:
        tool.description = req.description
    if req.icon is not None:
        tool.icon = req.icon

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工具不存在")

    log_action(db, current_user["user_id"], "delete", "tool", tool_id,
               detail=f"删除工具：{tool.title}")

    db.delete(tool)
    db.commit()

    return ResponseBase(msg="删除成功")
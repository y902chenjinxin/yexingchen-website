"""时间胶囊（工具岛）—— 写给未来自己的信，到期才可读。

核心约束：**解锁前的正文绝不离开服务端**。列表接口对未到期条目只回元信息
（title/unlock_at/剩余秒数），正文恒为 null；读取走 /{id}/open，服务端校验时间。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.capsule import TimeCapsule
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/capsules", tags=["工具岛-时间胶囊"])


class CapsuleIn(BaseModel):
    title: str = ""
    content: str = ""
    unlock_at: datetime


def _to_dict(c: TimeCapsule, now: datetime) -> dict:
    unlocked = now >= c.unlock_at
    seconds_left = max(0, int((c.unlock_at - now).total_seconds())) if not unlocked else 0
    return {
        "id": c.id,
        "title": c.title,
        "locked": not unlocked,
        "seconds_left": seconds_left,
        "unlock_at": str(c.unlock_at),
        "opened_at": str(c.opened_at) if c.opened_at else None,
        "created_at": str(c.created_at) if c.created_at else None,
        # 未到期正文绝不返回
        "content": c.content if unlocked else None,
    }


@router.post("")
def create_capsule(
    req: CapsuleIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="信的内容不能为空")
    if req.unlock_at <= datetime.now():
        raise HTTPException(status_code=400, detail="解锁时间必须晚于现在")
    c = TimeCapsule(
        user_id=current_user["user_id"],
        title=req.title.strip()[:80] or "给未来的信",
        content=req.content,
        unlock_at=req.unlock_at,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"code": 0, "msg": "ok", "data": _to_dict(c, datetime.now())}


@router.get("")
def list_capsules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    now = datetime.now()
    rows = (
        db.query(TimeCapsule)
        .filter(TimeCapsule.user_id == current_user["user_id"])
        .order_by(TimeCapsule.unlock_at.desc())
        .all()
    )
    return {"code": 0, "msg": "ok", "data": {"list": [_to_dict(c, now) for c in rows]}}


@router.post("/{capsule_id}/open")
def open_capsule(
    capsule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    now = datetime.now()
    c = (
        db.query(TimeCapsule)
        .filter(TimeCapsule.id == capsule_id, TimeCapsule.user_id == current_user["user_id"])
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="胶囊不存在")
    if now < c.unlock_at:
        raise HTTPException(status_code=403, detail="还没到解锁时间")
    if not c.opened_at:
        c.opened_at = now
        db.commit()
    return {"code": 0, "msg": "ok", "data": _to_dict(c, now)}


@router.delete("/{capsule_id}")
def delete_capsule(
    capsule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = (
        db.query(TimeCapsule)
        .filter(TimeCapsule.id == capsule_id, TimeCapsule.user_id == current_user["user_id"])
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="胶囊不存在")
    if now_check := datetime.now() < c.unlock_at:
        # 未到期的胶囊也允许删（写错了总得能删），但要前端二次确认
        pass
    db.delete(c)
    db.commit()
    return {"code": 0, "msg": "ok"}

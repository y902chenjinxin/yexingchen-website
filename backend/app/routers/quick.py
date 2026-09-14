"""闪念速记：极简随手记 + 每日日记时间线。

数据按用户隔离。时间线按自然日分组，每天一组，倒序排列。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ResponseBase
from app.utils.security import get_current_user
from app.models.quick import QuickNote

router = APIRouter(prefix="/api/quick", tags=["闪念速记"])


def _to_dict(q: QuickNote) -> dict:
    return {
        "id": q.id,
        "content": q.content,
        "created_at": str(q.created_at),
        "day": str(q.created_at.date()),
    }


class QuickIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("", response_model=ResponseBase)
async def create_quick(
    payload: QuickIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = QuickNote(
        user_id=current_user["user_id"],
        content=payload.content.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResponseBase(data=_to_dict(row))


@router.get("", response_model=ResponseBase)
async def list_quick(
    day: str = Query("", description="YYYY-MM-DD，缺省返回近 N 天"),
    days: int = Query(14, ge=1, le=90),
    limit: int = Query(200, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = current_user["user_id"]
    query = db.query(QuickNote).filter(QuickNote.user_id == uid)

    end = datetime.now()
    if day:
        try:
            d = datetime.strptime(day, "%Y-%m-%d")
            s = datetime(d.year, d.month, d.day)
            e = s + timedelta(days=1)
            return ResponseBase(data={
                "timeline": [{
                    "day": s.strftime("%Y-%m-%d"),
                    "date_label": s.strftime("%Y年%m月%d日"),
                    "items": [_to_dict(x) for x in query.filter(QuickNote.created_at >= s, QuickNote.created_at < e).order_by(QuickNote.created_at.asc()).limit(limit).all()],
                }],
                "days": [s.strftime("%Y-%m-%d")],
            })
        except (ValueError, TypeError):
            pass

    start = end - timedelta(days=days - 1)
    rows = (
        query
        .filter(QuickNote.created_at >= datetime(start.year, start.month, start.day))
        .order_by(QuickNote.created_at.desc())
        .limit(limit)
        .all()
    )
    grouped: dict = defaultdict(list)
    for r in rows:
        grouped[str(r.created_at.date())].append(r)
    timeline = []
    for k in sorted(grouped.keys(), reverse=True):
        _d = datetime.strptime(k, "%Y-%m-%d")
        timeline.append({
            "day": k,
            "date_label": _d.strftime("%Y年%m月%d日"),
            "items": [_to_dict(x) for x in sorted(grouped[k], key=lambda x: x.created_at)],
        })
    return ResponseBase(data={
        "timeline": timeline,
        "days": [t["day"] for t in timeline],
    })


@router.delete("/{q_id}", response_model=ResponseBase)
async def delete_quick(
    q_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = db.query(QuickNote).filter(
        QuickNote.id == q_id,
        QuickNote.user_id == current_user["user_id"],
    ).first()
    if not row:
        from app.schemas.errors import raise_error, ErrCode
        raise_error(ErrCode.NOT_FOUND)
    db.delete(row)
    db.commit()
    return ResponseBase(data={"id": q_id, "deleted": True})
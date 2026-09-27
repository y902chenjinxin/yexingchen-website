"""遗失物件 API（生活岛）。

- 家庭共享：`household_id` 过滤（沿用 life.py 的简化设计）
- 按上传人筛选：`uploader_id`
- 纯记录：无「找回」流程；图片可选
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lost import LostItem
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.household import HOUSEHOLD_ID, member_options, name_map
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/lost", tags=["生活岛-遗失物件"])

CATEGORIES = ["证件", "电子", "穿戴", "随身", "其他"]


class LostIn(BaseModel):
    name: str = ""
    category: str = "其他"
    lost_at: Optional[str] = None          # YYYY-MM-DD，空则视为今天
    place: str = ""
    scene: str = ""
    mood: str = ""
    value: Optional[int] = None
    photos: Optional[list[str]] = None
    tags: Optional[list[str]] = None


def _loads(raw: str) -> list:
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _to_out(it: LostItem, names: dict[int, str]) -> dict:
    return {
        "id": it.id,
        "name": it.name,
        "category": it.category or "其他",
        "lost_at": str(it.lost_at) if it.lost_at else "",
        "place": it.place or "",
        "scene": it.scene or "",
        "mood": it.mood or "",
        "value": it.value,
        "photos": _loads(it.photos),
        "tags": _loads(it.tags),
        "uploader_id": it.uploader_id,
        "uploader_name": names.get(it.uploader_id, "家人"),
        "created_at": str(it.created_at) if it.created_at else "",
        "updated_at": str(it.updated_at) if it.updated_at else "",
    }


def _get_or_404(db: Session, item_id: int) -> LostItem:
    it = (
        db.query(LostItem)
        .filter(
            LostItem.id == item_id,
            LostItem.household_id == HOUSEHOLD_ID,
            LostItem.deleted_at.is_(None),
        )
        .first()
    )
    if not it:
        raise_error(ErrCode.NOT_FOUND, "这条记录不存在")
    return it


@router.get("", response_model=ResponseBase)
def list_lost(
    uploader_id: Optional[int] = Query(None),
    category: str = Query(""),
    year: Optional[int] = Query(None),
    q: str = Query(""),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(LostItem).filter(
        LostItem.household_id == HOUSEHOLD_ID, LostItem.deleted_at.is_(None)
    )
    if uploader_id:
        query = query.filter(LostItem.uploader_id == uploader_id)
    if category:
        query = query.filter(LostItem.category == category)
    if year:
        query = query.filter(func.strftime("%Y", LostItem.lost_at) == str(year))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(LostItem.name.like(like), LostItem.place.like(like), LostItem.scene.like(like))
        )
    total = query.count()
    rows = (
        query.order_by(LostItem.lost_at.desc().nullslast(), LostItem.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    names = name_map(db)
    return ResponseBase(data={"list": [_to_out(x, names) for x in rows], "total": total})


@router.get("/stats", response_model=ResponseBase)
def lost_stats(
    uploader_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """顶部一行小统计：记过几件 · 估值合计 · 按年/按分类分布。"""
    base = db.query(LostItem).filter(
        LostItem.household_id == HOUSEHOLD_ID, LostItem.deleted_at.is_(None)
    )
    if uploader_id:
        base = base.filter(LostItem.uploader_id == uploader_id)
    rows = base.all()
    total_value = sum(int(r.value or 0) for r in rows)
    by_year: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for r in rows:
        y = str(r.lost_at)[:4] if r.lost_at else "未填日期"
        by_year[y] = by_year.get(y, 0) + 1
        c = r.category or "其他"
        by_category[c] = by_category.get(c, 0) + 1
    return ResponseBase(data={
        "count": len(rows),
        "total_value": total_value,
        "by_year": [{"year": k, "count": v} for k, v in sorted(by_year.items(), reverse=True)],
        "by_category": [{"category": k, "count": v}
                        for k, v in sorted(by_category.items(), key=lambda x: -x[1])],
        "categories": CATEGORIES,
    })


@router.get("/uploaders", response_model=ResponseBase)
def lost_uploaders(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return ResponseBase(data={"list": member_options(db)})


@router.post("", response_model=ResponseBase)
def create_lost(
    req: LostIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not (req.name or "").strip():
        raise_error(ErrCode.INVALID_PARAM, "至少写个物品名")
    it = LostItem(
        household_id=HOUSEHOLD_ID,
        uploader_id=current_user["user_id"],
        name=req.name.strip()[:120],
        category=(req.category or "其他")[:20],
        lost_at=_parse_date(req.lost_at) or date.today(),
        place=(req.place or "")[:160],
        scene=req.scene or "",
        mood=(req.mood or "")[:60],
        value=req.value,
        photos=json.dumps(req.photos or [], ensure_ascii=False),
        tags=json.dumps(req.tags or [], ensure_ascii=False),
    )
    db.add(it)
    db.commit()
    db.refresh(it)
    return ResponseBase(msg="记下了", data=_to_out(it, name_map(db)))


@router.put("/{item_id}", response_model=ResponseBase)
def update_lost(
    item_id: int,
    req: LostIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    it = _get_or_404(db, item_id)
    if req.name is not None:
        it.name = req.name.strip()[:120]
    if req.category:
        it.category = req.category[:20]
    d = _parse_date(req.lost_at)
    if d:
        it.lost_at = d
    it.place = (req.place or "")[:160]
    it.scene = req.scene or ""
    it.mood = (req.mood or "")[:60]
    it.value = req.value
    if req.photos is not None:
        it.photos = json.dumps(req.photos, ensure_ascii=False)
    if req.tags is not None:
        it.tags = json.dumps(req.tags, ensure_ascii=False)
    db.commit()
    db.refresh(it)
    return ResponseBase(msg="已更新", data=_to_out(it, name_map(db)))


@router.delete("/{item_id}", response_model=ResponseBase)
def delete_lost(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    it = _get_or_404(db, item_id)
    it.deleted_at = datetime.now()   # 软删：回忆类数据，给个后悔的机会
    db.commit()
    return ResponseBase(msg="已删除")

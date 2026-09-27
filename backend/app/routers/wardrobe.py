"""穿搭推荐 API（生活岛）。

三个硬约束（v2.40.21 定稿）：
1. **按人分开**：单品有 `owner_member_id`（归属人），`uploader_id` 只是「谁传的」。
   推荐、搭配、筛选全部以归属人为准，绝不跨人混推。
2. **人 = 家庭成员**：人名单直接来自 `household_member`（`/api/life/members`），
   `wardrobe_person_profiles` 只放穿搭附加信息（全身照 / 尺码备注）。
3. **天气复用**：直接调用工作台的高德代理（同 key、同 10 分钟缓存），无新增依赖。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.life import HouseholdMember
from app.models.wardrobe import WardrobeItem, WardrobeOutfit, WardrobePersonProfile
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.household import HOUSEHOLD_ID, household_members, member_options, name_map
from app.services.member_naming import member_name
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/wardrobe", tags=["生活岛-穿搭推荐"])

CATEGORIES = ["上装", "下装", "外套", "连衣裙", "鞋", "配饰"]
STATUSES = ["在穿", "闲置", "已淘汰"]
STYLE_TAGS = ["通勤", "运动", "居家", "约会", "户外", "正式"]
COLOR_PRESETS = ["黑", "白", "灰", "藏青", "蓝", "卡其", "米白", "棕", "绿", "红", "粉", "黄"]

# 场合 → 目标正式度（1 居家 ~ 5 正式）
OCCASION_FORMALITY = {"居家": 1, "运动": 2, "通勤": 3, "约会": 3, "户外": 2, "正式": 5}


class ItemIn(BaseModel):
    name: str = ""
    owner_member_id: Optional[int] = None
    category: str = "上装"
    color_name: str = ""
    color_hex: str = ""
    seasons: Optional[list[str]] = None
    warmth: int = 3
    formality: int = 3
    style_tags: Optional[list[str]] = None
    photos: Optional[list[str]] = None
    brand: str = ""
    size: str = ""
    price: Optional[int] = None
    buy_date: Optional[str] = None
    status: str = "在穿"
    note: str = ""


class OutfitIn(BaseModel):
    name: str = ""
    owner_member_id: Optional[int] = None
    item_ids: Optional[list[int]] = None
    temp_min: Optional[int] = None
    temp_max: Optional[int] = None
    occasion: str = ""
    tryon_image: str = ""
    is_favorite: int = 0


class PersonProfileIn(BaseModel):
    full_body_photo: Optional[str] = None
    size_note: Optional[str] = None
    style_note: Optional[str] = None


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


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v or lo)))


# ============================== 单品 ==============================

def _item_to_out(it: WardrobeItem, member_names: dict[int, str], uploader_names: dict[int, str]) -> dict:
    return {
        "id": it.id,
        "name": it.name,
        "owner_member_id": it.owner_member_id,
        "owner_name": member_names.get(it.owner_member_id or -1, ""),
        "uploader_id": it.uploader_id,
        "uploader_name": uploader_names.get(it.uploader_id, "家人"),
        "category": it.category or "上装",
        "color_name": it.color_name or "",
        "color_hex": it.color_hex or "",
        "seasons": _loads(it.seasons),
        "warmth": it.warmth or 3,
        "formality": it.formality or 3,
        "style_tags": _loads(it.style_tags),
        "photos": _loads(it.photos),
        "brand": it.brand or "",
        "size": it.size or "",
        "price": it.price,
        "buy_date": str(it.buy_date) if it.buy_date else "",
        "status": it.status or "在穿",
        "wear_count": it.wear_count or 0,
        "last_worn_at": str(it.last_worn_at) if it.last_worn_at else "",
        "note": it.note or "",
        "created_at": str(it.created_at) if it.created_at else "",
    }


def _member_name_map(db: Session) -> dict[int, str]:
    """member.id → 展示名（归属人显示用）"""
    return {m.id: member_name(m) for m in household_members(db)}


def _get_item(db: Session, item_id: int) -> WardrobeItem:
    it = (
        db.query(WardrobeItem)
        .filter(
            WardrobeItem.id == item_id,
            WardrobeItem.household_id == HOUSEHOLD_ID,
            WardrobeItem.deleted_at.is_(None),
        )
        .first()
    )
    if not it:
        raise_error(ErrCode.NOT_FOUND, "这件单品不存在")
    return it


@router.get("/items", response_model=ResponseBase)
def list_items(
    owner_member_id: Optional[int] = Query(None, description="按归属人过滤（推荐/筛选都靠它分开）"),
    category: str = Query(""),
    status: str = Query(""),
    season: str = Query(""),
    tag: str = Query(""),
    stale_days: Optional[int] = Query(None, description="只看 N 天没穿过的"),
    q: str = Query(""),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(WardrobeItem).filter(
        WardrobeItem.household_id == HOUSEHOLD_ID, WardrobeItem.deleted_at.is_(None)
    )
    if owner_member_id:
        query = query.filter(WardrobeItem.owner_member_id == owner_member_id)
    if category:
        query = query.filter(WardrobeItem.category == category)
    if status:
        query = query.filter(WardrobeItem.status == status)
    if tag:
        query = query.filter(WardrobeItem.style_tags.like(f"%{tag}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(WardrobeItem.name.like(like), WardrobeItem.brand.like(like), WardrobeItem.note.like(like))
        )
    rows = query.order_by(WardrobeItem.created_at.desc()).all()
    if season:
        rows = [r for r in rows if season in _loads(r.seasons)]
    if stale_days:
        cutoff = date.today() - timedelta(days=stale_days)
        rows = [r for r in rows if not r.last_worn_at or r.last_worn_at <= cutoff]
    total = len(rows)
    rows = rows[(page - 1) * size: (page - 1) * size + size]
    names, up = _member_name_map(db), name_map(db)
    return ResponseBase(data={
        "list": [_item_to_out(r, names, up) for r in rows],
        "total": total,
        "categories": CATEGORIES,
        "statuses": STATUSES,
        "style_tags": STYLE_TAGS,
        "color_presets": COLOR_PRESETS,
    })


@router.post("/items", response_model=ResponseBase)
def create_item(
    req: ItemIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not (req.name or "").strip():
        raise_error(ErrCode.INVALID_PARAM, "给这件衣服起个名字吧")
    it = WardrobeItem(
        household_id=HOUSEHOLD_ID,
        uploader_id=current_user["user_id"],
        owner_member_id=req.owner_member_id,
        name=req.name.strip()[:120],
        category=(req.category or "上装")[:20],
        color_name=(req.color_name or "")[:30],
        color_hex=(req.color_hex or "")[:9],
        seasons=json.dumps(req.seasons or [], ensure_ascii=False),
        warmth=_clamp(req.warmth, 1, 5),
        formality=_clamp(req.formality, 1, 5),
        style_tags=json.dumps(req.style_tags or [], ensure_ascii=False),
        photos=json.dumps(req.photos or [], ensure_ascii=False),
        brand=(req.brand or "")[:60],
        size=(req.size or "")[:30],
        price=req.price,
        buy_date=_parse_date(req.buy_date),
        status=(req.status or "在穿")[:20],
        note=req.note or "",
    )
    db.add(it)
    db.commit()
    db.refresh(it)
    return ResponseBase(msg="已入库", data=_item_to_out(it, _member_name_map(db), name_map(db)))


@router.put("/items/{item_id}", response_model=ResponseBase)
def update_item(
    item_id: int,
    req: ItemIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    it = _get_item(db, item_id)
    if req.name is not None:
        it.name = req.name.strip()[:120]
    if req.owner_member_id is not None:
        it.owner_member_id = req.owner_member_id or None
    if req.category:
        it.category = req.category[:20]
    it.color_name = (req.color_name or "")[:30]
    it.color_hex = (req.color_hex or "")[:9]
    if req.seasons is not None:
        it.seasons = json.dumps(req.seasons, ensure_ascii=False)
    it.warmth = _clamp(req.warmth, 1, 5)
    it.formality = _clamp(req.formality, 1, 5)
    if req.style_tags is not None:
        it.style_tags = json.dumps(req.style_tags, ensure_ascii=False)
    if req.photos is not None:
        it.photos = json.dumps(req.photos, ensure_ascii=False)
    it.brand = (req.brand or "")[:60]
    it.size = (req.size or "")[:30]
    it.price = req.price
    d = _parse_date(req.buy_date)
    if d:
        it.buy_date = d
    if req.status:
        it.status = req.status[:20]
    it.note = req.note or ""
    db.commit()
    db.refresh(it)
    return ResponseBase(msg="已更新", data=_item_to_out(it, _member_name_map(db), name_map(db)))


@router.post("/items/{item_id}/wear", response_model=ResponseBase)
def wear_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """记录「今天穿了这件」——穿着次数与最近穿着日是「不让衣服被遗忘」的核心数据。"""
    it = _get_item(db, item_id)
    it.wear_count = (it.wear_count or 0) + 1
    it.last_worn_at = date.today()
    db.commit()
    db.refresh(it)
    return ResponseBase(msg="记下了", data=_item_to_out(it, _member_name_map(db), name_map(db)))


@router.delete("/items/{item_id}", response_model=ResponseBase)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    it = _get_item(db, item_id)
    it.deleted_at = datetime.now()
    db.commit()
    return ResponseBase(msg="已移除")


# ============================== 人（家庭成员 + 穿搭附加信息）==============================

def _person_out(m: HouseholdMember, prof: Optional[WardrobePersonProfile], item_count: int) -> dict:
    return {
        "member_id": m.id,
        "user_id": m.user_id,
        "name": member_name(m),
        "avatar": m.avatar or "🌿",
        "is_owner": int(m.is_owner or 0),
        "full_body_photo": (prof.full_body_photo if prof else "") or "",
        "size_note": (prof.size_note if prof else "") or "",
        "style_note": (prof.style_note if prof else "") or "",
        "item_count": item_count,
    }


@router.get("/persons", response_model=ResponseBase)
def list_persons(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    members = household_members(db)
    profs = {
        p.member_id: p
        for p in db.query(WardrobePersonProfile)
        .filter(WardrobePersonProfile.household_id == HOUSEHOLD_ID)
        .all()
    }
    counts: dict[int, int] = {}
    for (mid, cnt) in (
        db.query(WardrobeItem.owner_member_id, func.count(WardrobeItem.id))
        .filter(WardrobeItem.household_id == HOUSEHOLD_ID, WardrobeItem.deleted_at.is_(None))
        .group_by(WardrobeItem.owner_member_id)
        .all()
    ):
        counts[mid or -1] = cnt
    return ResponseBase(data={
        "list": [_person_out(m, profs.get(m.id), counts.get(m.id, 0)) for m in members],
        "uploaders": member_options(db),
    })


@router.put("/persons/{member_id}", response_model=ResponseBase)
def upsert_person_profile(
    member_id: int,
    req: PersonProfileIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    m = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.id == member_id, HouseholdMember.household_id == HOUSEHOLD_ID)
        .first()
    )
    if not m:
        raise_error(ErrCode.NOT_FOUND, "成员不存在")
    prof = (
        db.query(WardrobePersonProfile)
        .filter(WardrobePersonProfile.member_id == member_id)
        .first()
    )
    if not prof:
        prof = WardrobePersonProfile(household_id=HOUSEHOLD_ID, member_id=member_id)
        db.add(prof)
    if req.full_body_photo is not None:
        prof.full_body_photo = req.full_body_photo[:300]
    if req.size_note is not None:
        prof.size_note = req.size_note[:200]
    if req.style_note is not None:
        prof.style_note = req.style_note[:300]
    db.commit()
    db.refresh(prof)
    return ResponseBase(msg="已保存", data=_person_out(m, prof, 0))


# ============================== 搭配 ==============================

def _outfit_to_out(o: WardrobeOutfit, member_names: dict[int, str], items: dict[int, dict]) -> dict:
    ids = [int(i) for i in _loads(o.item_ids) if str(i).isdigit()]
    return {
        "id": o.id,
        "name": o.name or "未命名搭配",
        "owner_member_id": o.owner_member_id,
        "owner_name": member_names.get(o.owner_member_id or -1, ""),
        "item_ids": ids,
        "items": [items[i] for i in ids if i in items],
        "temp_min": o.temp_min,
        "temp_max": o.temp_max,
        "occasion": o.occasion or "",
        "tryon_image": o.tryon_image or "",
        "is_favorite": o.is_favorite or 0,
        "created_at": str(o.created_at) if o.created_at else "",
    }


@router.get("/outfits", response_model=ResponseBase)
def list_outfits(
    owner_member_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    q = db.query(WardrobeOutfit).filter(
        WardrobeOutfit.household_id == HOUSEHOLD_ID, WardrobeOutfit.deleted_at.is_(None)
    )
    if owner_member_id:
        q = q.filter(WardrobeOutfit.owner_member_id == owner_member_id)
    rows = q.order_by(WardrobeOutfit.is_favorite.desc(), WardrobeOutfit.id.desc()).all()
    names, up = _member_name_map(db), name_map(db)
    items = {
        it.id: _item_to_out(it, names, up)
        for it in db.query(WardrobeItem)
        .filter(WardrobeItem.household_id == HOUSEHOLD_ID, WardrobeItem.deleted_at.is_(None))
        .all()
    }
    return ResponseBase(data={"list": [_outfit_to_out(o, names, items) for o in rows]})


@router.post("/outfits", response_model=ResponseBase)
def create_outfit(
    req: OutfitIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ids = req.item_ids or []
    if not ids:
        raise_error(ErrCode.INVALID_PARAM, "先选几件单品再存搭配")
    o = WardrobeOutfit(
        household_id=HOUSEHOLD_ID,
        uploader_id=current_user["user_id"],
        owner_member_id=req.owner_member_id,
        name=(req.name or "")[:80],
        item_ids=json.dumps(ids),
        temp_min=req.temp_min,
        temp_max=req.temp_max,
        occasion=(req.occasion or "")[:20],
        tryon_image=(req.tryon_image or "")[:300],
        is_favorite=int(req.is_favorite or 0),
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    names, up = _member_name_map(db), name_map(db)
    items = {
        it.id: _item_to_out(it, names, up)
        for it in db.query(WardrobeItem)
        .filter(WardrobeItem.id.in_([int(i) for i in ids]), WardrobeItem.deleted_at.is_(None))
        .all()
    }
    return ResponseBase(msg="已存入搭配库", data=_outfit_to_out(o, names, items))


@router.delete("/outfits/{outfit_id}", response_model=ResponseBase)
def delete_outfit(
    outfit_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    o = (
        db.query(WardrobeOutfit)
        .filter(WardrobeOutfit.id == outfit_id, WardrobeOutfit.household_id == HOUSEHOLD_ID)
        .first()
    )
    if not o:
        raise_error(ErrCode.NOT_FOUND, "搭配不存在")
    o.deleted_at = datetime.now()
    db.commit()
    return ResponseBase(msg="已删除")


# ============================== 今日推荐 ==============================

def _season_of(d: date) -> str:
    m = d.month
    if m in (3, 4, 5):
        return "春"
    if m in (6, 7, 8):
        return "夏"
    if m in (9, 10, 11):
        return "秋"
    return "冬"


def _warmth_range(temp: Optional[float]) -> tuple[int, int]:
    if temp is None:
        return 1, 5
    if temp >= 28:
        return 1, 2
    if temp >= 18:
        return 2, 3
    if temp >= 10:
        return 3, 4
    return 4, 5


def _score(it: WardrobeItem, occasion: str, today: date) -> float:
    """打分：场合匹配 0.4 + 标签命中 0.3 + 久未穿着 0.2 + 新买降权 0.1"""
    target = OCCASION_FORMALITY.get(occasion, 3)
    s_formal = 1 - min(1.0, abs((it.formality or 3) - target) / 4)
    tags = _loads(it.style_tags)
    s_tag = 1.0 if (occasion and occasion in tags) else 0.35
    if it.last_worn_at:
        days = max(0, (today - it.last_worn_at).days)
    else:
        days = 120
    s_stale = min(1.0, days / 60)
    s_new = -0.5 if (it.buy_date and (today - it.buy_date).days <= 30) else 0.0
    return s_formal * 0.4 + s_tag * 0.3 + s_stale * 0.2 + s_new * 0.1


@router.get("/suggest", response_model=ResponseBase)
def suggest(
    owner_member_id: int = Query(..., description="给谁搭（必传：绝不跨人混推）"),
    occasion: str = Query(""),
    city: str = Query(""),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """按人 + 当天天气推荐 3 套。天气从工作台高德代理取；取不到就退化为「只按季节/场合」。"""
    today = date.today()
    season = _season_of(today)

    # ---- 天气（复用工作台高德代理；失败不阻断推荐）----
    temp: Optional[float] = None
    weather = ""
    weather_note = ""
    try:
        from app.routers.workbench.weather import _fetch_weather, resolve_adcode  # 复用同一 key 与缓存

        adcode, label = resolve_adcode(city or None, None, None)
        w = _fetch_weather(adcode)
        temp = w["current"].get("temperature")
        weather = w["current"].get("weather") or ""
        weather_note = f"{label} {weather} {temp}℃" if temp is not None else label
    except Exception:  # noqa: BLE001
        weather_note = "天气暂不可用（已按季节推荐）"

    lo, hi = _warmth_range(temp)

    def pool(role: str, allow_offseason: bool = False) -> list[WardrobeItem]:
        rows = (
            db.query(WardrobeItem)
            .filter(
                WardrobeItem.household_id == HOUSEHOLD_ID,
                WardrobeItem.deleted_at.is_(None),
                WardrobeItem.status == "在穿",
                WardrobeItem.owner_member_id == owner_member_id,   # ← 按人隔离
                WardrobeItem.category == role,
            )
            .all()
        )
        # 温度档过滤（连衣裙/配饰不受保暖度约束）
        if role not in ("连衣裙", "配饰"):
            filtered = [r for r in rows if lo <= (r.warmth or 3) <= hi]
            if filtered:
                rows = filtered
        # 季节过滤（允许放行：宁可推错季也别推不出来）
        seasonal = [r for r in rows if season in _loads(r.seasons)]
        if seasonal and not allow_offseason:
            rows = seasonal
        # 最近 3 天穿过的不再出现；若过滤后为空则放行（否则会出现「今天没衣服穿」）
        fresh = [r for r in rows if not r.last_worn_at or (today - r.last_worn_at).days >= 3]
        rows = fresh or rows
        return sorted(rows, key=lambda r: _score(r, occasion, today), reverse=True)

    tops, bottoms, coats, shoes, dresses = (
        pool("上装"), pool("下装"), pool("外套"), pool("鞋"), pool("连衣裙")
    )

    combos = []
    # 优先「连衣裙 + 鞋（+ 外套）」
    for i, d in enumerate(dresses[:2]):
        if not shoes:
            break
        pick = [d, shoes[i % len(shoes)]]
        if coats and (temp is None or temp < 22):
            pick.append(coats[i % len(coats)])
        combos.append(pick)
    # 再排「上装 + 下装（+ 外套）」
    for i in range(3):
        if not (tops and bottoms) or len(combos) >= 3:
            break
        pick = [tops[i % len(tops)], bottoms[i % len(bottoms)]]
        if coats and (temp is None or temp < 22):
            pick.append(coats[i % len(coats)])
        if shoes:
            pick.append(shoes[i % len(shoes)])
        combos.append(pick)
    combos = combos[:3]

    names, up = _member_name_map(db), name_map(db)
    reason = (
        f"今天 {weather_note}，建议保暖度 {lo}~{hi}"
        if temp is not None
        else weather_note
    )
    if occasion:
        reason += f" · 场合「{occasion}」"

    return ResponseBase(data={
        "owner_member_id": owner_member_id,
        "season": season,
        "temp": temp,
        "weather": weather,
        "weather_note": weather_note,
        "reason": reason,
        "options": [
            {"items": [_item_to_out(x, names, up) for x in c], "item_ids": [x.id for x in c]}
            for c in combos
        ],
        "empty_hint": "" if combos else "这位的衣服还没入库 —— 先去「+ 加一件」拍照存起来",
    })


@router.get("/stats", response_model=ResponseBase)
def wardrobe_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rows = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.household_id == HOUSEHOLD_ID, WardrobeItem.deleted_at.is_(None))
        .all()
    )
    cutoff = date.today() - timedelta(days=90)
    by_person: dict[int, int] = {}
    for r in rows:
        by_person[r.owner_member_id or -1] = by_person.get(r.owner_member_id or -1, 0) + 1
    mids = _member_name_map(db)
    return ResponseBase(data={
        "total": len(rows),
        "stale_90": len([r for r in rows if not r.last_worn_at or r.last_worn_at <= cutoff]),
        "never_worn": len([r for r in rows if (r.wear_count or 0) == 0]),
        "by_person": [
            {"member_id": k, "name": mids.get(k, "未指定"), "count": v}
            for k, v in sorted(by_person.items(), key=lambda x: -x[1])
        ],
    })

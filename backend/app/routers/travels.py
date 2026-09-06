"""旅游足迹模块路由。

行程 CRUD + 城市点 + 图片/视频上传 + 统计。展示端公开可读（未登录只能读 is_public=1），
录入/编辑/上传需登录且仅本人可改。
"""
from __future__ import annotations

import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.travels import Travel, TravelCity
from app.models.user import User
from app.utils.security import decode_token, get_current_user
from app.utils.file_utils import save_upload_file

router = APIRouter(prefix="/api/travels", tags=["旅游足迹"])

# 可选鉴权：无/失效 token 也放行（公开读），返回 None
_security_opt = HTTPBearer(auto_error=False)
_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
_VIDEO_EXT = {"mp4", "webm", "mov"}
_IMAGE_MAX = 10 * 1024 * 1024  # 10MB
_VIDEO_MAX = 200 * 1024 * 1024  # 200MB


def ok(data=None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data}


async def optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security_opt),
    db: Session = Depends(get_db),
):
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        uid = payload.get("user_id")
        if uid is None:
            return None
        user = db.query(User).filter(User.id == uid).first()
        if not user or user.status != "approved":
            return None
        return {"user_id": user.id, "role": user.role, "is_super_admin": user.is_super_admin}
    except HTTPException:
        return None


# ---------- Schemas ----------
class CityIn(BaseModel):
    city: str
    province: str = ""
    lon: Optional[float] = None
    lat: Optional[float] = None
    note: str = ""


class TravelBase(BaseModel):
    title: str = Field(..., max_length=120)
    summary: str = ""
    markdown: str = ""
    cover: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    star: int = 0
    tags: List[str] = []
    photos: List[str] = []
    video: str = ""
    cities: List[CityIn] = []
    is_public: int = 1


class TravelUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    markdown: Optional[str] = None
    cover: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    star: Optional[int] = None
    tags: Optional[List[str]] = None
    photos: Optional[List[str]] = None
    video: Optional[str] = None
    cities: Optional[List[CityIn]] = None
    is_public: Optional[int] = None


def _parse_date(s: Optional[str]):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s))
    except ValueError:
        return None


def _city_dict(c: TravelCity) -> dict:
    return {"id": c.id, "city": c.city, "province": c.province,
            "lon": c.lon, "lat": c.lat, "seq": c.seq, "note": c.note}


def _travel_brief(t: Travel, cities: List[TravelCity]) -> dict:
    photos = []
    try:
        photos = json.loads(t.photos or "[]")
    except (ValueError, TypeError):
        photos = []
    tags = [x for x in (t.tags or "").split(",") if x]
    return {
        "id": t.id,
        "title": t.title,
        "summary": t.summary,
        "cover": t.cover,
        "start_date": str(t.start_date) if t.start_date else None,
        "end_date": str(t.end_date) if t.end_date else None,
        "star": t.star,
        "tags": tags,
        "video": t.video,
        "photo_count": len(photos),
        "is_public": t.is_public,
        "cities": [_city_dict(c) for c in cities],
        "created_at": str(t.created_at),
    }


def _list_data(db: Session, user) -> dict:
    q = db.query(Travel)
    if user:
        q = q.filter((Travel.user_id == user["user_id"]) | (Travel.is_public == 1))
    else:
        q = q.filter(Travel.is_public == 1)
    travels = q.order_by(Travel.start_date.desc(), Travel.id.desc()).all()
    crows = {"cities": []}
    if travels:
        ids = [t.id for t in travels]
        cities = db.query(TravelCity).filter(TravelCity.travel_id.in_(ids)).all()
    else:
        cities = []
    by = {}
    for c in cities:
        by.setdefault(c.travel_id, []).append(c)
    items = []
    for t in travels:
        cs = sorted(by.get(t.id, []), key=lambda x: x.seq)
        items.append(_travel_brief(t, cs))
    return {"list": items, "total": len(items)}


@router.get("")
async def list_travels(
    db: Session = Depends(get_db),
    user: dict = Depends(optional_user),
):
    return ok(_list_data(db, user))


@router.get("/stats")
async def travels_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(optional_user),
):
    data = _list_data(db, user)
    prov = set()
    city = set()
    for it in data["list"]:
        for c in it["cities"]:
            if c["province"]:
                prov.add(c["province"])
            if c["city"]:
                city.add(c["city"])
    return ok({"travel_count": data["total"], "province_count": len(prov), "city_count": len(city)})


@router.get("/{travel_id}")
async def get_travel(
    travel_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(optional_user),
):
    t = db.query(Travel).filter(Travel.id == travel_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="行程不存在")
    if t.is_public != 1 and (not user or user["user_id"] != t.user_id):
        raise HTTPException(status_code=404, detail="行程不存在")
    cities = db.query(TravelCity).filter(TravelCity.travel_id == t.id).order_by(TravelCity.seq).all()
    photos = []
    try:
        photos = json.loads(t.photos or "[]")
    except (ValueError, TypeError):
        photos = []
    tags = [x for x in (t.tags or "").split(",") if x]
    return ok(_travel_brief(t, cities) | {
        "markdown": t.markdown,
        "photos": photos,
        "user_id": t.user_id,
    })


@router.post("")
async def create_travel(
    req: TravelBase = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tags = ",".join(req.tags)
    photos = json.dumps(req.photos, ensure_ascii=False)
    t = Travel(
        user_id=current_user["user_id"],
        title=req.title,
        summary=req.summary or "",
        markdown=req.markdown or "",
        cover=req.cover or "",
        start_date=_parse_date(req.start_date),
        end_date=_parse_date(req.end_date),
        star=req.star if 1 <= req.star <= 5 else 0,
        tags=tags[:255],
        photos=photos,
        video=req.video or "",
        is_public=req.is_public,
        sort_order=0,
    )
    db.add(t)
    db.flush()
    _add_cities(db, t.id, req.cities)
    db.commit()
    return ok({"id": t.id}, "已记下这段旅程")


def _add_cities(db: Session, travel_id: int, cities: List[CityIn]) -> None:
    for i, c in enumerate(cities):
        db.add(TravelCity(
            travel_id=travel_id,
            city=c.city or "",
            province=c.province or "",
            lon=c.lon,
            lat=c.lat,
            seq=i,
            note=c.note or "",
        ))


def _owns(t: Travel, user: dict, db: Session) -> bool:
    if user and user["user_id"] == t.user_id:
        return True
    return False


@router.put("/{travel_id}")
async def update_travel(
    travel_id: int,
    req: TravelUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    t = db.query(Travel).filter(Travel.id == travel_id).first()
    if not t or t.user_id != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="行程不存在")
    if req.title is not None:
        t.title = req.title
    if req.summary is not None:
        t.summary = req.summary
    if req.markdown is not None:
        t.markdown = req.markdown
    if req.cover is not None:
        t.cover = req.cover
    if req.start_date is not None:
        t.start_date = _parse_date(req.start_date)
    if req.end_date is not None:
        t.end_date = _parse_date(req.end_date)
    if req.star is not None:
        t.star = req.star if 1 <= req.star <= 5 else 0
    if req.tags is not None:
        t.tags = ",".join(req.tags)[:255]
    if req.photos is not None:
        t.photos = json.dumps(req.photos, ensure_ascii=False)
    if req.video is not None:
        t.video = req.video
    if req.is_public is not None:
        t.is_public = req.is_public
    if req.cities is not None:
        db.query(TravelCity).filter(TravelCity.travel_id == t.id).delete()
        _add_cities(db, t.id, req.cities)
    db.add(t)
    db.commit()
    return ok(None, "已更新")


@router.delete("/{travel_id}")
async def delete_travel(
    travel_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    t = db.query(Travel).filter(Travel.id == travel_id).first()
    if not t or t.user_id != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="行程不存在")
    db.query(TravelCity).filter(TravelCity.travel_id == t.id).delete()
    db.delete(t)
    db.commit()
    return ok(None, "已删除")


@router.post("/upload")
async def upload_media(
    type: str = Query(..., description="image | video"),
    file: UploadFile = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if file is None:
        raise HTTPException(status_code=400, detail="未选择文件")
    try:
        if type == "image":
            relative, size = await save_upload_file(file, "travel", _IMAGE_EXT, _IMAGE_MAX)
        elif type == "video":
            relative, size = await save_upload_file(file, "travel", _VIDEO_EXT, _VIDEO_MAX)
        else:
            raise HTTPException(status_code=400, detail="type 仅支持 image|video")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # save_upload_file 返回 /travel/xxx；静态挂载点在 /uploads，需补前缀以被 <img>/<video> 直接访问
    url = f"/uploads{relative}" if not relative.startswith("/uploads") else relative
    return ok({"url": url}, "上传成功")
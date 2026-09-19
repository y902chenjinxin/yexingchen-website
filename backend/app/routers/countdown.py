"""通用图片上传（jpg/png/webp/gif）+ 倒计时 CRUD。"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.countdown import Countdown
from app.models.user import User
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.utils.file_utils import save_upload_file
from app.utils.security import get_current_user

router = APIRouter(prefix="/api", tags=["工具岛-倒计时"])

# ---- 上传：通用图片（jpg/png/webp/gif）----
# 注意：save_upload_file 的 allowed_file 取的是「不带点」的扩展名（"jpg"），
# 因此这里的集合必须也不带点，否则任何文件都校验失败 → 400「不支持的文件格式」
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/uploads/image", response_model=ResponseBase)
async def upload_image(
    file: UploadFile = File(...),
    sub_dir: str = Form("image"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """通用图片上传。sub_dir 限定字符 [a-z0-9_-]，避免路径逃逸。"""
    safe_sub = "".join(c for c in sub_dir if c.isalnum() or c in "_-")
    if not safe_sub:
        raise_error(ErrCode.INVALID_PARAM, "sub_dir 不合法")
    try:
        rel_path, size = await save_upload_file(file, safe_sub, ALLOWED_IMAGE_EXT, MAX_IMAGE_SIZE)
    except ValueError as e:
        raise_error(ErrCode.INVALID_PARAM, str(e))
    return ResponseBase(data={"url": rel_path, "size": size})


# ---- Pydantic Schemas ----

class CountdownIn(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    target_date: Optional[date] = None  # 农历模式不传，由 lunar_month/day 替代
    is_lunar: bool = False
    lunar_month: Optional[int] = None
    lunar_day: Optional[int] = None
    lunar_leap: bool = False
    direction: str = "count_down"
    repeat_type: str = "none"
    in_home: bool = False
    pinned: bool = False
    sort_order: int = 0
    icon: Optional[str] = None
    color: Optional[str] = None
    bg_image: Optional[str] = None
    memo: Optional[str] = None

    @field_validator("direction")
    @classmethod
    def _v_dir(cls, v: str) -> str:
        if v not in {"count_down", "count_up"}:
            raise ValueError("direction 必须是 count_down 或 count_up")
        return v

    @field_validator("repeat_type")
    @classmethod
    def _v_repeat(cls, v: str) -> str:
        if v not in {"none", "yearly", "monthly", "weekly"}:
            raise ValueError("repeat_type 不合法")
        return v

    @field_validator("color")
    @classmethod
    def _v_color(cls, v: Optional[str]) -> Optional[str]:
        if v and (len(v) > 16 or not v.startswith("#")):
            raise ValueError("color 必须是 hex（如 #8e6a2c）")
        return v

    @field_validator("bg_image")
    @classmethod
    def _v_bg(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 256:
            raise ValueError("bg_image 长度不能超过 256")
        return v

    @field_validator("lunar_month")
    @classmethod
    def _v_lm(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("lunar_month 必须在 1-12")
        return v

    @field_validator("lunar_day")
    @classmethod
    def _v_ld(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 30):
            raise ValueError("lunar_day 必须在 1-30")
        return v


class CountdownUpdate(CountdownIn):
    is_archived: Optional[bool] = None


def _to_dict(c: Countdown) -> dict:
    """把模型序列化成前端友好的 dict（含 computed 字段 days_left / days_text）。"""
    today = date.today()
    # 农历模式：target_date 为 None，此时 days_left 只能按近似公历差计算（或置0）
    if c.target_date is None:
        delta_days = 0
    else:
        delta_days = (c.target_date - today).days
    return {
        "id": c.id,
        "user_id": c.user_id,
        "title": c.title,
        "target_date": c.target_date.isoformat(),
        "is_lunar": bool(c.is_lunar),
        "lunar_month": c.lunar_month,
        "lunar_day": c.lunar_day,
        "lunar_leap": bool(c.lunar_leap),
        "direction": c.direction,
        "repeat_type": c.repeat_type,
        "in_home": bool(c.in_home),
        "pinned": bool(c.pinned),
        "sort_order": c.sort_order,
        "is_archived": bool(c.is_archived),
        "icon": c.icon,
        "color": c.color,
        "bg_image": c.bg_image,
        "memo": c.memo,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        # 计算字段：前端不用重复算
        "days_left": abs(delta_days) if c.direction == "count_up" else delta_days,
        "is_passed": delta_days < 0,
        # 重复事件下次到期的天数（仅 yearly 简化处理：取月日差）
        "next_occurrence": _next_occurrence(c, today) if c.repeat_type != "none" else None,
    }


def _next_occurrence(c: Countdown, today: date) -> Optional[str]:
    """对 yearly/monthly/weekly 重复事件，算下一次发生的日期（仅考虑 target_date 的月日/星期）。"""
    if c.target_date is None:
        return None
    if c.repeat_type == "yearly":
        try:
            this_year = today.replace(year=today.year, month=c.target_date.month, day=c.target_date.day)
        except ValueError:
            return None
        if this_year < today:
            try:
                next_year = today.replace(year=today.year + 1, month=c.target_date.month, day=c.target_date.day)
            except ValueError:
                return None
            return next_year.isoformat()
        return this_year.isoformat()
    if c.repeat_type == "monthly":
        # 下次该日（today 日 <= target_date 日 → 本月该日；否则下月）
        try:
            this_month = today.replace(day=c.target_date.day)
        except ValueError:
            return None
        if this_month < today:
            # 进位到下月
            year, month = today.year, today.month + 1
            if month > 12:
                year += 1
                month = 1
            try:
                return today.replace(year=year, month=month, day=c.target_date.day).isoformat()
            except ValueError:
                return None
        return this_month.isoformat()
    if c.repeat_type == "weekly":
        # 找下一个与 target_date 同星期几的日期
        diff = (c.target_date.weekday() - today.weekday()) % 7
        next_d = today + timedelta(days=diff)
        return next_d.isoformat()
    return None


def _get_or_404(db: Session, uid: int, cid: int) -> Countdown:
    c = db.query(Countdown).filter(Countdown.id == cid).first()
    if not c or c.user_id != uid:
        raise_error(ErrCode.NOT_FOUND, "事件不存在或无权限")
    return c


# ---- 路由 ----

@router.get("/countdowns", response_model=ResponseBase)
def list_countdowns(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """当前用户全部倒计时。默认不含归档。"""
    uid = current_user["user_id"]
    q = db.query(Countdown).filter(Countdown.user_id == uid)
    if not include_archived:
        q = q.filter(Countdown.is_archived == False)  # noqa: E712
    rows = q.order_by(Countdown.pinned.desc(), Countdown.sort_order, Countdown.id).all()
    # 与 axios 拦截器 + 组件风格对齐：data={list: [...]} → response.data.data
    return ResponseBase(data={"list": [_to_dict(c) for c in rows]})


@router.get("/countdowns/home", response_model=ResponseBase)
def list_home_countdowns(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """玉简卡片用的：in_home=true 且未归档，按 pinned desc + sort_order 排序。"""
    uid = current_user["user_id"]
    rows = (
        db.query(Countdown)
        .filter(Countdown.user_id == uid, Countdown.in_home == True, Countdown.is_archived == False)  # noqa: E712
        .order_by(Countdown.pinned.desc(), Countdown.sort_order, Countdown.id)
        .all()
    )
    return ResponseBase(data={"list": [_to_dict(c) for c in rows]})


@router.post("/countdowns", response_model=ResponseBase)
def create_countdown(
    payload: CountdownIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    # 验证用户存在（fastapi get_current_user 已校验 token，但这里再保险）
    if not db.query(User).filter(User.id == uid).first():
        raise_error(ErrCode.NOT_FOUND, "用户不存在")
    c = Countdown(
        user_id=uid,
        title=payload.title.strip(),
        # 农历模式 target_date 为 None，DB 的 date 列非空，用 today 占位（实际日期由 lunar_month/day 驱动）
        target_date=payload.target_date or date.today(),
        is_lunar=payload.is_lunar,
        lunar_month=payload.lunar_month,
        lunar_day=payload.lunar_day,
        lunar_leap=payload.lunar_leap,
        direction=payload.direction,
        repeat_type=payload.repeat_type,
        in_home=payload.in_home,
        pinned=payload.pinned,
        sort_order=payload.sort_order,
        icon=payload.icon,
        color=payload.color,
        bg_image=payload.bg_image,
        memo=payload.memo,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    log_action(db, "countdown", f"create:{c.id}", uid)
    return ResponseBase(msg="创建成功", data=_to_dict(c))


@router.get("/countdowns/{cid}", response_model=ResponseBase)
def get_countdown(
    cid: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = _get_or_404(db, current_user["user_id"], cid)
    return ResponseBase(data=_to_dict(c))


@router.put("/countdowns/{cid}", response_model=ResponseBase)
def update_countdown(
    cid: int,
    payload: CountdownUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = _get_or_404(db, current_user["user_id"], cid)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    log_action(db, "countdown", f"update:{c.id}", current_user["user_id"])
    return ResponseBase(msg="更新成功", data=_to_dict(c))


@router.delete("/countdowns/{cid}", response_model=ResponseBase)
def delete_countdown(
    cid: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = _get_or_404(db, current_user["user_id"], cid)
    if c.bg_image:
        # 顺手清理背景图（失败不阻断删除）
        try:
            full = os.path.join(settings.UPLOAD_DIR, c.bg_image.lstrip("/"))
            if os.path.isfile(full):
                os.remove(full)
        except Exception:
            pass
    db.delete(c)
    db.commit()
    log_action(db, "countdown", f"delete:{cid}", current_user["user_id"])
    return ResponseBase(msg="删除成功")
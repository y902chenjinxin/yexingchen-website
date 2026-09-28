"""日历数据接口（农历 / 节气 / 节日 / 法定假期，v2.40.36）。

给前端日历面板用：一次返回整月逐日信息，切换月份时才请求（前端可缓存）。
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.schemas.common import ResponseBase
from app.services import holidays as hol
from app.services import daycal as cal
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/lunar", tags=["日历"])


@router.get("/month", response_model=ResponseBase)
def month_calendar(
    year: int = Query(..., ge=1900, le=2099),
    month: int = Query(..., ge=1, le=12),
    current_user: dict = Depends(get_current_user),
):
    """某月逐日：农历 / 节气 / 节日 / 是否法定假期或调休补班。"""
    days = cal.month_days(year, month)
    for info in days:
        d = date.fromisoformat(info["date"])
        h = hol.holiday_on(d)
        if h:
            info["holiday"] = h.name
            info["holiday_index"] = h.day_index(d)
            info["holiday_days"] = h.days
        mk = hol.makeup_on(d)
        if mk:
            info["makeup"] = mk[0].name
    first = date(year, month, 1)
    return ResponseBase(data={
        "year": year,
        "month": month,
        "first_weekday": first.weekday(),      # 0=周一，前端排格用
        "days": days,
        "holiday_source": hol.source_of(year),
    })

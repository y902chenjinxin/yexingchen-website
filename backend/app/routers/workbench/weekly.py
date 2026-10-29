"""工作台・每周回顾（v2.46.276）

不挂定时任务的理由：服务器没有 crontab，main.py 里那套 asyncio 后台循环是给资讯抓取用的
（本轮已在删除）。周报的场景是「打开工作台就想看到」，所以改成**懒生成**：
`GET /latest` 时如果上周那条不存在，就当场算一次。打开即得，不需要 cron，也没有空窗。
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.weekly import WeeklyReview
from app.routers.workbench._common import ok
from app.services.weekly_review import generate, last_week, to_dict
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/weekly", tags=["工作台-每周回顾"])


@router.get("/latest")
def weekly_latest(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    uid = int(_user["user_id"])
    key = last_week()[0].isoformat()

    row = db.query(WeeklyReview).filter(
        WeeklyReview.user_id == uid, WeeklyReview.week_start == key
    ).first()

    # 懒生成：上周没算过就算一次。一条数据都没有的周返回 None，前端不渲染。
    if not row:
        row = generate(db, uid)

    # 上周完全没数据时，退回最近一期（让用户至少能看到上一份）
    if not row:
        row = (
            db.query(WeeklyReview)
            .filter(WeeklyReview.user_id == uid)
            .order_by(WeeklyReview.week_start.desc())
            .first()
        )
    return ok(to_dict(row) if row else None)


@router.get("/list")
def weekly_list(
    limit: int = Query(12, ge=1, le=104),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    uid = int(_user["user_id"])
    rows = (
        db.query(WeeklyReview)
        .filter(WeeklyReview.user_id == uid)
        .order_by(WeeklyReview.week_start.desc())
        .limit(limit)
        .all()
    )
    return ok({"items": [to_dict(r) for r in rows], "total": len(rows)})


@router.post("/generate")
def weekly_generate(
    week_start: str = Query("", description="周一日期 YYYY-MM-DD，留空=上一个自然周"),
    force: bool = Query(True),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """手动重算（调试/补算用）。"""
    uid = int(_user["user_id"])
    ws: date | None = None
    if week_start:
        try:
            ws = date.fromisoformat(week_start)
        except ValueError:
            ws = None
    row = generate(db, uid, ws, force=force)
    return ok(to_dict(row) if row else None)

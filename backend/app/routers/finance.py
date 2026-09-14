"""个人记账模块。

流水（账本）CRUD + 汇总统计（KPI / 分类占比 / 收支趋势），数据按用户隔离。
金额在库内以「分」为单位整数存储，入参出参统一用「元」（含两位小数）。
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.schemas.common import ResponseBase
from app.utils.security import get_current_user
from app.models.finance import FinanceTransaction

router = APIRouter(prefix="/api/finance", tags=["个人记账"])

# 收支分类（含 emoji 供前端展示）；未命中归「其他」
EXPENSE_CATEGORIES = [
    {"key": "餐饮", "icon": "🍜"}, {"key": "交通", "icon": "🚇"}, {"key": "购物", "icon": "🛍️"},
    {"key": "居家", "icon": "🏠"}, {"key": "娱乐", "icon": "🎮"}, {"key": "医疗", "icon": "💊"},
    {"key": "教育", "icon": "📚"}, {"key": "人情", "icon": "🎁"}, {"key": "其他", "icon": "🧾"},
]
INCOME_CATEGORIES = [
    {"key": "工资", "icon": "💼"}, {"key": "奖金", "icon": "🏅"}, {"key": "理财", "icon": "📈"},
    {"key": "兼职", "icon": "🧑‍💻"}, {"key": "红包", "icon": "🧧"}, {"key": "其他", "icon": "💰"},
]

CATEGORY_ICONS = {c["key"]: c["icon"] for c in EXPENSE_CATEGORIES + INCOME_CATEGORIES}


class TransactionIn(BaseModel):
    type: str = "expense"
    amount: float = Field(..., gt=0)
    category: str = "其他"
    note: str = ""
    occurred_at: str = ""  # ISO 时间串，缺省用当前时间

    def amount_cents(self) -> int:
        return int(round(self.amount * 100))


def _parse_dt(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _valid_category(ttype: str, category: str) -> str:
    pool = EXPENSE_CATEGORIES if ttype == "expense" else INCOME_CATEGORIES
    keys = [c["key"] for c in pool]
    return category if category in keys else "其他"


def _to_dict(t: FinanceTransaction) -> dict:
    return {
        "id": t.id,
        "type": t.type,
        "amount": round(t.amount_cents / 100, 2),
        "amount_cents": t.amount_cents,
        "category": t.category,
        "category_icon": CATEGORY_ICONS.get(t.category, "🧾"),
        "note": t.note,
        "occurred_at": str(t.occurred_at),
        "created_at": str(t.created_at),
    }


# ---------- 分类元数据 ----------
@router.get("/categories", response_model=ResponseBase)
async def list_categories():
    return ResponseBase(data={
        "expense": EXPENSE_CATEGORIES,
        "income": INCOME_CATEGORIES,
    })


# ---------- 汇总（供首页看板 + 记账页） ----------
@router.get("/summary", response_model=ResponseBase)
async def summary(
    month: str = Query("", description="YYYY-MM，缺省当前月"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    now = datetime.now()

    if month:
        try:
            y, m = (int(x) for x in month.split("-"))
        except (ValueError, TypeError):
            y, m = now.year, now.month
    else:
        y, m = now.year, now.month
    m_start = datetime(y, m, 1)
    m_end = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)

    base = db.query(FinanceTransaction).filter(
        FinanceTransaction.user_id == uid,
        FinanceTransaction.deleted_at.is_(None),
    )

    # 本月流水（用于本月KPI + 分类占比 + 趋势）
    month_rows = [r for r in base.filter(FinanceTransaction.occurred_at >= m_start, FinanceTransaction.occurred_at < m_end).all()]
    month_income = sum(r.amount_cents for r in month_rows if r.type == "income")
    month_expense = sum(r.amount_cents for r in month_rows if r.type == "expense")
    month_count = len(month_rows)

    # 累计结余（全量，含已删除过滤）
    all_rows = base.all()
    total_income = sum(r.amount_cents for r in all_rows if r.type == "income")
    total_expense = sum(r.amount_cents for r in all_rows if r.type == "expense")
    balance = total_income - total_expense

    # 本月支出分类占比
    cat_agg = defaultdict(int)
    for r in month_rows:
        if r.type == "expense":
            cat_agg[r.category] += r.amount_cents
    categories = [
        {"category": k, "amount": round(v / 100, 2), "amount_cents": v, "icon": CATEGORY_ICONS.get(k, "🧾")}
        for k, v in sorted(cat_agg.items(), key=lambda x: -x[1])
    ]

    # 本月每日收支趋势（1..当月天数）
    end_day = (m_end - timedelta(days=1)).day
    day_map = {r.occurred_at.day: r for r in month_rows}
    trends = []
    for d in range(1, end_day + 1):
        rows = [r for r in month_rows if r.occurred_at.day == d]
        trends.append({
            "day": f"{m}-{d:02d}",
            "income": round(sum(r.amount_cents for r in rows if r.type == "income") / 100, 2),
            "expense": round(sum(r.amount_cents for r in rows if r.type == "expense") / 100, 2),
        })

    recent = base.order_by(FinanceTransaction.occurred_at.desc()).limit(10).all()

    return ResponseBase(data={
        "month": f"{y}-{m:02d}",
        "month_income": round(month_income / 100, 2),
        "month_expense": round(month_expense / 100, 2),
        "month_count": month_count,
        "balance": round(balance / 100, 2),
        "total_count": len(all_rows),
        "categories": categories,
        "trends": trends,
        "recent": [_to_dict(r) for r in reversed(recent)],
    })


# ---------- 流水列表 ----------
@router.get("/transactions", response_model=ResponseBase)
async def list_transactions(
    page: int = 1,
    size: int = 20,
    type: str = "",
    category: str = "",
    q: str = "",
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(FinanceTransaction).filter(
        FinanceTransaction.user_id == current_user["user_id"],
        FinanceTransaction.deleted_at.is_(None),
    )
    if type in ("income", "expense"):
        query = query.filter(FinanceTransaction.type == type)
    if category:
        query = query.filter(FinanceTransaction.category == category)
    s_dt, e_dt = _parse_dt(start), _parse_dt(end)
    if s_dt:
        query = query.filter(FinanceTransaction.occurred_at >= s_dt)
    if e_dt:
        query = query.filter(FinanceTransaction.occurred_at <= e_dt)
    if q:
        kw = f"%{q}%"
        query = query.filter(or_(FinanceTransaction.note.like(kw), FinanceTransaction.category.like(kw)))

    total = query.count()
    rows = (
        query.order_by(FinanceTransaction.occurred_at.desc(), FinanceTransaction.id.desc())
        .offset((page - 1) * size).limit(size).all()
    )
    return ResponseBase(data={
        "list": [_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    })


@router.get("/transactions/{t_id}", response_model=ResponseBase)
async def get_transaction(
    t_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = db.query(FinanceTransaction).filter(
        FinanceTransaction.id == t_id,
        FinanceTransaction.user_id == current_user["user_id"],
        FinanceTransaction.deleted_at.is_(None),
    ).first()
    if not row:
        from app.schemas.errors import raise_error, ErrCode
        raise_error(ErrCode.NOT_FOUND)
    return ResponseBase(data=_to_dict(row))


@router.post("/transactions", response_model=ResponseBase)
async def create_transaction(
    payload: TransactionIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ttype = payload.type if payload.type in ("income", "expense") else "expense"
    occurred = _parse_dt(payload.occurred_at) or datetime.now()
    row = FinanceTransaction(
        user_id=current_user["user_id"],
        type=ttype,
        amount_cents=abs(payload.amount_cents()),
        category=_valid_category(ttype, payload.category),
        note=(payload.note or "")[:255],
        occurred_at=occurred,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResponseBase(data=_to_dict(row))


@router.put("/transactions/{t_id}", response_model=ResponseBase)
async def update_transaction(
    t_id: int,
    payload: TransactionIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = db.query(FinanceTransaction).filter(
        FinanceTransaction.id == t_id,
        FinanceTransaction.user_id == current_user["user_id"],
        FinanceTransaction.deleted_at.is_(None),
    ).first()
    if not row:
        from app.schemas.errors import raise_error, ErrCode
        raise_error(ErrCode.NOT_FOUND)
    ttype = payload.type if payload.type in ("income", "expense") else "expense"
    row.type = ttype
    row.amount_cents = abs(payload.amount_cents())
    row.category = _valid_category(ttype, payload.category)
    row.note = (payload.note or "")[:255]
    occurred = _parse_dt(payload.occurred_at) or row.occurred_at
    row.occurred_at = occurred
    db.commit()
    db.refresh(row)
    return ResponseBase(data=_to_dict(row))


@router.delete("/transactions/{t_id}", response_model=ResponseBase)
async def delete_transaction(
    t_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = db.query(FinanceTransaction).filter(
        FinanceTransaction.id == t_id,
        FinanceTransaction.user_id == current_user["user_id"],
        FinanceTransaction.deleted_at.is_(None),
    ).first()
    if not row:
        from app.schemas.errors import raise_error, ErrCode
        raise_error(ErrCode.NOT_FOUND)
    row.deleted_at = datetime.now()
    db.commit()
    return ResponseBase(data={"id": t_id, "deleted": True})


# ---------- CSV 导出（按月或全部） ----------
@router.get("/export")
async def export_csv(
    start: str = Query("", description="起始 YYYY-MM-DD"),
    end: str = Query("", description="截止 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导出流水为 CSV（UTF-8 with BOM，可直接用 Excel 打开）。"""
    query = db.query(FinanceTransaction).filter(
        FinanceTransaction.user_id == current_user["user_id"],
        FinanceTransaction.deleted_at.is_(None),
    )
    s_dt, e_dt = _parse_dt(start), _parse_dt(end)
    if s_dt:
        query = query.filter(FinanceTransaction.occurred_at >= s_dt)
    if e_dt:
        query = query.filter(FinanceTransaction.occurred_at <= e_dt)
    rows = query.order_by(FinanceTransaction.occurred_at.asc(), FinanceTransaction.id.asc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["日期", "类型", "分类", "金额(元)", "备注"])
    for r in rows:
        writer.writerow([
            r.occurred_at.strftime("%Y-%m-%d"),
            "收入" if r.type == "income" else "支出",
            r.category,
            f"{r.amount_cents / 100:.2f}",
            r.note or "",
        ])
    data = "\ufeff" + buf.getvalue()  # BOM → Excel 识别 UTF-8
    filename = f"账本导出_{datetime.now():%Y%m%d}.csv"
    return Response(
        content=data.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class ImportIn(BaseModel):
    csv: str = Field(..., description="CSV 原文")  # noqa: A003


@router.post("/import")
async def import_csv(
    payload: ImportIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """批量导入流水。

    首行为表头（可选，可含 日期/类型/分类/金额(元)/备注 任一本站点导出列）；
    每行字段顺序与表头对应，缺省取本站点导出顺序。金额支持正负号推断收支。
    """
    uid = current_user["user_id"]
    reader = csv.reader(io.StringIO(payload.csv.lstrip("\ufeff")))
    lines = [ln for ln in reader if any(cell.strip() for cell in ln)]
    if not lines:
        return ResponseBase(data={"imported": 0, "skipped": 0, "errors": ["文件为空"]})

    # 识别表头：首行含「日期」「类型」「金额」中任一关键词则视为表头
    header_row, col_map = -1, None
    first = [c.strip() for c in lines[0]]
    if any(("日期" in c or "金额" in c or "类型" in c) for c in first):
        header_row = 0
        col_map = {
            "date": first.index(next((c for c in first if "日期" in c), None)) if any("日期" in c for c in first) else None,
            "type": first.index(next((c for c in first if "类型" in c), None)) if any("类型" in c for c in first) else None,
            "category": first.index(next((c for c in first if "分类" in c), None)) if any("分类" in c for c in first) else None,
            "amount": first.index(next((c for c in first if "金额" in c), None)) if any("金额" in c for c in first) else None,
            "note": first.index(next((c for c in first if "备注" in c), None)) if any("备注" in c for c in first) else None,
        }

    def cell(row, field, fallback):
        idx = col_map[field] if col_map else None
        if idx is None:
            return fallback
        return (row[idx] if idx < len(row) else "").strip()

    imported, skipped, errors = 0, 0, []
    now = datetime.now()
    for i, raw in enumerate(lines):
        if i == header_row:
            continue
        row = [c.strip() for c in raw]
        if not row or all(c == "" for c in row):
            continue
        date_s = cell(row, "date", row[0] if row else "")
        type_s = cell(row, "type", (row[1] if len(row) > 1 else ""))
        amount_s = cell(row, "amount", (row[3] if len(row) > 3 else ""))
        cat_s = cell(row, "category", (row[2] if len(row) > 2 else ""))
        note_s = cell(row, "note", (row[4] if len(row) > 4 else ""))

        try:
            amount = float(amount_s.replace(",", ""))
            if amount == 0:
                skipped += 1
                continue
            ttype = "income" if amount > 0 else "expense"
            if type_s and ("收" in type_s or "income" in type_s.lower()):
                ttype = "income"
            elif type_s and ("支" in type_s or "expense" in type_s.lower()):
                ttype = "expense"
            amount = abs(amount)
            occurred = _parse_dt(date_s) if date_s else now
            if occurred is None:
                # 兼容 YYYY/MM/DD
                try:
                    occurred = datetime.strptime(date_s, "%Y/%m/%d")
                except (ValueError, TypeError):
                    occurred = now
            db.add(FinanceTransaction(
                user_id=uid,
                type=ttype,
                amount_cents=int(round(amount * 100)),
                category=_valid_category(ttype, cat_s or "其他"),
                note=(note_s or "")[:255],
                occurred_at=occurred,
            ))
            imported += 1
        except (ValueError, TypeError):
            skipped += 1
            errors.append(f"第{i + 1}行：金额无效「{amount_s}」")
    db.commit()
    return ResponseBase(data={"imported": imported, "skipped": skipped, "errors": errors[:20]})
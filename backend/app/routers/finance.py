"""个人记账模块。

流水（账本）CRUD + 汇总统计（KPI / 分类占比 / 收支趋势），数据按用户隔离。
金额在库内以「分」为单位整数存储，入参出参统一用「元」（含两位小数）。
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from openpyxl import load_workbook

from app.database import get_db
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user
from app.models.finance import FinanceCategory, FinanceTransaction

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

# 兜底分类名（两个收支方向各有一个「其他」）
FALLBACK_CATEGORY = "其他"
# 自定义分类名长度上限，须 ≤ FinanceTransaction.category(String(32))
MAX_CATEGORY_NAME_LEN = 12
DEFAULT_CUSTOM_ICON = "🏷️"


# ---------- 分类池（内置 + 自定义） ----------
def _builtin_pool(ttype: str) -> list:
    return EXPENSE_CATEGORIES if ttype == "expense" else INCOME_CATEGORIES


def _custom_rows(db: Session, uid: int, ttype: str) -> list:
    """该用户某方向的未删自定义分类，按排序值→id 稳定排列。"""
    return (
        db.query(FinanceCategory)
        .filter(
            FinanceCategory.user_id == uid,
            FinanceCategory.type == ttype,
            FinanceCategory.deleted_at.is_(None),
        )
        .order_by(FinanceCategory.sort_order, FinanceCategory.id)
        .all()
    )


def _category_pool(db: Session, uid: int, ttype: str) -> list:
    """内置 + 自定义合并后的分类列表（内置在前，自定义按用户排序在后）。"""
    pool = [dict(c, is_custom=False) for c in _builtin_pool(ttype)]
    pool += [
        {"key": r.name, "icon": r.icon or DEFAULT_CUSTOM_ICON, "is_custom": True, "id": r.id}
        for r in _custom_rows(db, uid, ttype)
    ]
    return pool


def _category_icon_map(db: Session, uid: int) -> dict:
    """分类名 → 图标。含自定义，供流水序列化与统计复用。

    这里**不过滤软删**：分类被删后，历史流水仍引用那个名字，
    若把图标也一并抹掉，老流水的图标会集体回落成 🧾，看起来像数据坏了。
    """
    icons = dict(CATEGORY_ICONS)
    rows = (
        db.query(FinanceCategory)
        .filter(FinanceCategory.user_id == uid)
        .all()
    )
    for r in rows:
        icons[r.name] = r.icon or DEFAULT_CUSTOM_ICON
    return icons


def _all_categories(db: Session, uid: int) -> dict:
    return {"expense": _category_pool(db, uid, "expense"), "income": _category_pool(db, uid, "income")}


def _allowed_categories(db: Session, uid: int) -> dict:
    """{"expense": {分类名...}, "income": {...}}：内置 + 该用户自定义，供导入校验。"""
    return {
        ttype: {c["key"] for c in _category_pool(db, uid, ttype)}
        for ttype in ("expense", "income")
    }


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
        return datetime.fromisoformat(str(value).replace("Z", "+00:00").replace(tzinfo=None))
    except (ValueError, TypeError):
        return None


def _valid_categories(ttype: str) -> set:
    """内置分类名集合。含自定义的校验请用 _allowed_categories。"""
    return {c["key"] for c in _builtin_pool(ttype)}


def _resolve_category(db: Session, uid: int, ttype: str, category: str) -> str:
    """校验并归一化分类名：命中「内置或该用户自定义」则保留，否则归「其他」。

    自定义分类必须先在此通过，否则前端选了新分类、后端仍会把它写成「其他」。
    """
    name = (category or "").strip()[:MAX_CATEGORY_NAME_LEN]
    if not name:
        return FALLBACK_CATEGORY
    if name in _valid_categories(ttype):
        return name
    hit = (
        db.query(FinanceCategory)
        .filter(
            FinanceCategory.user_id == uid,
            FinanceCategory.type == ttype,
            FinanceCategory.name == name,
            FinanceCategory.deleted_at.is_(None),
        )
        .first()
    )
    return name if hit else FALLBACK_CATEGORY


def _to_dict(t: FinanceTransaction, icons: dict = None) -> dict:
    imap = icons if icons is not None else CATEGORY_ICONS
    return {
        "id": t.id,
        "type": t.type,
        "amount": round(t.amount_cents / 100, 2),
        "amount_cents": t.amount_cents,
        "category": t.category,
        "category_icon": imap.get(t.category, "🧾"),
        "note": t.note,
        "occurred_at": str(t.occurred_at),
        "created_at": str(t.created_at),
    }


# ---------- 分类元数据 ----------
@router.get("/categories", response_model=ResponseBase)
async def list_categories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """内置分类 + 当前用户的自定义分类（is_custom=True 的可改可删）。"""
    return ResponseBase(data=_all_categories(db, current_user["user_id"]))


class CategoryIn(BaseModel):
    type: str = "expense"
    name: str = Field(..., min_length=1, max_length=MAX_CATEGORY_NAME_LEN)
    icon: str = Field(default=DEFAULT_CUSTOM_ICON, max_length=16)


@router.post("/categories", response_model=ResponseBase)
async def create_category(
    payload: CategoryIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """新增自定义分类。同名（或与内置同名）直接拒绝，避免下拉里出现两个「餐饮」。"""
    uid = current_user["user_id"]
    ttype = payload.type if payload.type in ("income", "expense") else "expense"
    name = (payload.name or "").strip()
    if not name:
        raise_error(ErrCode.INVALID_PARAM, "分类名不能为空")
    if name in _valid_categories(ttype):
        raise_error(ErrCode.INVALID_PARAM, f"「{name}」是内置分类，无需重复添加")
    dup = (
        db.query(FinanceCategory)
        .filter(
            FinanceCategory.user_id == uid,
            FinanceCategory.type == ttype,
            FinanceCategory.name == name,
            FinanceCategory.deleted_at.is_(None),
        )
        .first()
    )
    if dup:
        raise_error(ErrCode.INVALID_PARAM, f"已存在同名分类「{name}」")

    max_sort = (
        db.query(func.max(FinanceCategory.sort_order))
        .filter(FinanceCategory.user_id == uid, FinanceCategory.type == ttype)
        .scalar()
    )
    row = FinanceCategory(
        user_id=uid,
        type=ttype,
        name=name,
        icon=(payload.icon or DEFAULT_CUSTOM_ICON).strip() or DEFAULT_CUSTOM_ICON,
        sort_order=(max_sort or 0) + 10,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResponseBase(
        data={"id": row.id, "key": row.name, "icon": row.icon, "is_custom": True},
        msg="分类已添加",
    )


@router.put("/categories/{category_id}", response_model=ResponseBase)
async def update_category(
    category_id: int,
    payload: CategoryIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """改自定义分类的名字/图标。

    改名会**同步更新该用户的存量流水**——否则老流水会指向一个已不存在的分类名，
    在统计里变成孤儿（既不在分类列表里、也不计入任何分类）。
    """
    uid = current_user["user_id"]
    row = (
        db.query(FinanceCategory)
        .filter(
            FinanceCategory.id == category_id,
            FinanceCategory.user_id == uid,
            FinanceCategory.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise_error(ErrCode.NOT_FOUND, "分类不存在")

    new_name = (payload.name or "").strip()
    if not new_name:
        raise_error(ErrCode.INVALID_PARAM, "分类名不能为空")
    if new_name != row.name:
        if new_name in _valid_categories(row.type):
            raise_error(ErrCode.INVALID_PARAM, f"「{new_name}」是内置分类，会混淆统计数据")
        dup = (
            db.query(FinanceCategory)
            .filter(
                FinanceCategory.user_id == uid,
                FinanceCategory.type == row.type,
                FinanceCategory.name == new_name,
                FinanceCategory.deleted_at.is_(None),
                FinanceCategory.id != row.id,
            )
            .first()
        )
        if dup:
            raise_error(ErrCode.INVALID_PARAM, f"已存在同名分类「{new_name}」")
        old_name = row.name
        db.query(FinanceTransaction).filter(
            FinanceTransaction.user_id == uid,
            FinanceTransaction.category == old_name,
        ).update({"category": new_name}, synchronize_session=False)
        row.name = new_name

    if payload.icon:
        row.icon = payload.icon.strip()[:16] or DEFAULT_CUSTOM_ICON
    db.commit()
    db.refresh(row)
    return ResponseBase(
        data={"id": row.id, "key": row.name, "icon": row.icon, "is_custom": True},
        msg="分类已更新",
    )


@router.delete("/categories/{category_id}", response_model=ResponseBase)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """软删自定义分类。存量流水保留原名（不迁移成「其他」），只是下拉里不再出现。"""
    uid = current_user["user_id"]
    row = (
        db.query(FinanceCategory)
        .filter(
            FinanceCategory.id == category_id,
            FinanceCategory.user_id == uid,
            FinanceCategory.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise_error(ErrCode.NOT_FOUND, "分类不存在")
    used = (
        db.query(FinanceTransaction)
        .filter(
            FinanceTransaction.user_id == uid,
            FinanceTransaction.category == row.name,
            FinanceTransaction.deleted_at.is_(None),
        )
        .count()
    )
    row.deleted_at = datetime.now()
    db.commit()
    return ResponseBase(
        data={"used_count": used},
        msg=f"分类已删除（{used} 条历史流水仍保留该分类名）" if used else "分类已删除",
    )



# ---------- 汇总（供首页看板 + 记账页） ----------
@router.get("/summary", response_model=ResponseBase)
async def summary(
    dim: str = Query("month", description="day/month/year，统计维度"),
    month: str = Query("", description="YYYY-MM，dim=month 时生效"),
    day: str = Query("", description="YYYY-MM-DD，dim=day 时生效"),
    year: str = Query("", description="YYYY，dim=year 时生效"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    now = datetime.now()
    dim = dim if dim in ("day", "month", "year") else "month"

    # ---- 解析时间窗与趋势粒度 ----
    if dim == "day":
        d = day or f"{now.year}-{now.month:02d}-{now.day:02d}"
        try:
            sy, sm, sd = (int(x) for x in d.split("-"))
        except (ValueError, TypeError):
            sy, sm, sd = now.year, now.month, now.day
        start = datetime(sy, sm, sd)
        end = start + timedelta(days=1)
        period = f"{sy}-{sm:02d}-{sd:02d}"
        grain = "day"
    elif dim == "year":
        sy = int(year) if year and str(year).isdigit() else now.year
        start = datetime(sy, 1, 1)
        end = datetime(sy + 1, 1, 1)
        period = str(sy)
        grain = "month"
    else:
        if month:
            try:
                sy, sm = (int(x) for x in month.split("-"))
            except (ValueError, TypeError):
                sy, sm = now.year, now.month
        else:
            sy, sm = now.year, now.month
        start = datetime(sy, sm, 1)
        end = datetime(sy + (1 if sm == 12 else 0), 1 if sm == 12 else sm + 1, 1)
        period = f"{sy}-{sm:02d}"
        grain = "day"

    base = db.query(FinanceTransaction).filter(
        FinanceTransaction.user_id == uid,
        FinanceTransaction.deleted_at.is_(None),
    )

    # 所选维度窗口内的流水（KPI + 分类占比 + 趋势）
    rows = base.filter(FinanceTransaction.occurred_at >= start, FinanceTransaction.occurred_at < end).all()
    income = sum(r.amount_cents for r in rows if r.type == "income")
    expense = sum(r.amount_cents for r in rows if r.type == "expense")
    count = len(rows)

    # 累计结余（全量，含已删除过滤）
    all_rows = base.all()
    total_income = sum(r.amount_cents for r in all_rows if r.type == "income")
    total_expense = sum(r.amount_cents for r in all_rows if r.type == "expense")
    balance = total_income - total_expense

    # 最早记账年份（前端用于下拉范围覆盖所有历史数据）
    first = db.query(func.min(FinanceTransaction.occurred_at)).filter(
        FinanceTransaction.user_id == uid,
        FinanceTransaction.deleted_at.is_(None),
    ).scalar()
    min_year = first.year if first else now.year

    # 窗口内支出分类占比（自定义分类的图标由 _category_icon_map 提供）
    icon_map = _category_icon_map(db, uid)
    cat_agg = defaultdict(int)
    for r in rows:
        if r.type == "expense":
            cat_agg[r.category] += r.amount_cents
    categories = [
        {"category": k, "amount": round(v / 100, 2), "amount_cents": v, "icon": icon_map.get(k, "🧾")}
        for k, v in sorted(cat_agg.items(), key=lambda x: -x[1])
    ]

    # 趋势：日为单点｜月按日｜年按月
    trends = []
    if grain == "day":
        trends.append({
            "day": period,
            "income": round(income / 100, 2),
            "expense": round(expense / 100, 2),
        })
    elif grain == "month":
        for d in range(1, (end - timedelta(days=1)).day + 1):
            sub = [r for r in rows if r.occurred_at.day == d]
            trends.append({
                "day": f"{period}-{d:02d}",
                "income": round(sum(r.amount_cents for r in sub if r.type == "income") / 100, 2),
                "expense": round(sum(r.amount_cents for r in sub if r.type == "expense") / 100, 2),
            })
    else:
        for mi in range(1, 13):
            sub = [r for r in rows if r.occurred_at.month == mi]
            trends.append({
                "day": f"{sy}-{mi:02d}",
                "income": round(sum(r.amount_cents for r in sub if r.type == "income") / 100, 2),
                "expense": round(sum(r.amount_cents for r in sub if r.type == "expense") / 100, 2),
            })

    recent = base.order_by(FinanceTransaction.occurred_at.desc()).limit(10).all()

    return ResponseBase(data={
        "period": period,
        "dim": dim,
        "min_year": min_year,
        "income": round(income / 100, 2),
        "expense": round(expense / 100, 2),
        "count": count,
        # 旧字段兼容：工作台/数据看板在默认「本月」视图下消费这些字段
        "month_income": round(income / 100, 2),
        "month_expense": round(expense / 100, 2),
        "month_count": count,
        "balance": round(balance / 100, 2),
        "total_count": len(all_rows),
        "categories": categories,
        "trends": trends,
        "recent": [_to_dict(r, icon_map) for r in reversed(recent)],
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
        "list": [_to_dict(r, _category_icon_map(db, current_user["user_id"])) for r in rows],
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
        raise_error(ErrCode.NOT_FOUND)
    return ResponseBase(data=_to_dict(row, _category_icon_map(db, current_user["user_id"])))


@router.post("/transactions", response_model=ResponseBase)
async def create_transaction(
    payload: TransactionIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ttype = payload.type if payload.type in ("income", "expense") else "expense"
    occurred = _parse_dt(payload.occurred_at) or datetime.now()
    uid = current_user["user_id"]
    row = FinanceTransaction(
        user_id=uid,
        type=ttype,
        amount_cents=abs(payload.amount_cents()),
        category=_resolve_category(db, uid, ttype, payload.category),
        note=(payload.note or "")[:255],
        occurred_at=occurred,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResponseBase(data=_to_dict(row, _category_icon_map(db, uid)))


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
        raise_error(ErrCode.NOT_FOUND)
    ttype = payload.type if payload.type in ("income", "expense") else "expense"
    uid = current_user["user_id"]
    row.type = ttype
    row.amount_cents = abs(payload.amount_cents())
    row.category = _resolve_category(db, uid, ttype, payload.category)
    row.note = (payload.note or "")[:255]
    occurred = _parse_dt(payload.occurred_at) or row.occurred_at
    row.occurred_at = occurred
    db.commit()
    db.refresh(row)
    return ResponseBase(data=_to_dict(row, _category_icon_map(db, uid)))


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


class ImportRowsIn(BaseModel):
    """AI 识别 / 本地解析确认后的结构化流水行。"""
    rows: list[dict] = Field(default_factory=list)


_HEADER_KWS = {
    "date": ["日期", "时间", "交易日", "记账日", "交易创建", "date"],
    "amount": ["金额", "money", "总额", "净额", "occurred"],
    "direction": ["收/支", "收支", "收 支", "借贷", "方向", "收付"],
    "type": ["交易类型", "类型", "流水类型", "商户单号", "类别"],
    "category": ["分类", "类目", "细分", "category"],
    "note": ["备注", "商品", "摘要", "说明", "用途", "项目", "名称"],
    "merchant": ["交易对方", "商户", "对方", "收单", "收款方"],
}


def _locate_header(lines):
    """扫描全表找首个「含日期 + 金额列」的表头行，返回 (行号, 列映射)。

    容忍表头上方存在说明/元信息（如微信/支付宝账单的导出头部），
    并尽量按「列名语义」映射到 date/amount/direction/type/category/note。
    """
    joined_required = ("日期", "时间", "金额", "type", "money")
    for idx, line in enumerate(lines):
        cells = [c.strip() for c in line]
        joined = " ".join(cells)
        if not any(k in joined for k in joined_required):
            continue
        col_map = {}
        for field in ("date", "amount", "direction", "type", "category", "note", "merchant"):
            col_map[field] = None
            for k in _HEADER_KWS[field]:
                if not k or k in ("/", " "):
                    continue
                hit = next((j for j, c in enumerate(cells) if k in c), None)
                if hit is not None:
                    col_map[field] = hit
                    break
        if col_map["date"] is not None and col_map["amount"] is not None:
            return idx, col_map
    return -1, None


def _trim_to_header(text: str) -> str:
    """去掉表头上方的说明/元信息行，返回从表头起的文本，供 AI 读取（减少噪声）。"""
    lines = [ln for ln in csv.reader(io.StringIO(text.lstrip("\ufeff"))) if any(c.strip() for c in ln)]
    hr, _ = _locate_header(lines)
    if hr is None or hr < 0:
        return text
    return "\n".join(",".join(cell for cell in ln) for ln in lines[hr:])


def _ttype_of(direction_s, type_s, amount):
    """由「收/支 方向列」「类型列」与金额符号判定收支，优先级：方向列 > 类型列 > 金额正负。"""
    def p(s):
        return s and ("收" in s or s.lower().startswith("inc") or s.lower().startswith("cr"))
    def e(s):
        return s and ("支" in s or s.lower().startswith("exp") or s.lower().startswith("db"))
    if direction_s:
        if p(direction_s):
            return "income"
        if e(direction_s):
            return "expense"
        if direction_s.strip():
            return "income" if amount > 0 else "expense"
    if type_s:
        if p(type_s):
            return "income"
        if e(type_s):
            return "expense"
    return "income" if amount > 0 else "expense"


# 无 AI 时的自动归类：按 交易对方+商品+类型 里的关键词命中分类池（按优先级）
_CAT_RULES = {
    "医疗": ["医院", "药", "诊所", "口腔", "牙科", "牙", "体检", "门诊", "挂号", "医疗", "太医", "康复"],
    "教育": ["学费", "课程", "培训", "书店", "书籍", "报班", "网课", "教育", "学习", "试卷", "文具"],
    "娱乐": ["电影", "影院", "ktv", "网吧", "网咖", "游戏", "门票", "演出", "摄影", "影像", "旅游", "度假", "景区", "纹绣", "婚纱", "KTV"],
    "交通": ["地铁", "轨道", "公交", "打车", "滴滴", "出租", "网约", "高铁", "火车", "航空", "机票", "加油", "加油站", "石油", "石化", "汽油", "停车", "充电", "单车", "骑行", "高速", "过路", "车辆", "汽车", "汽配", "修车", "车站", "骑车"],
    "人情": ["红包", "发给", "随礼", "份子", "祝福", "人情", "借款", "还", "礼金", "转账给"],
    "居家": ["水电", "燃气", "物业", "房租", "宽带", "话费", "手机充值", "电信", "联通", "移动", "维修", "家居"],
    "购物": ["超市", "便利店", "商场", "百货", "淘宝", "京东", "拼多多", "天猫", "生鲜", "水果", "果园", "零食", "雪糕", "蛋糕", "黄金", "饰品", "服装", "衣库", "衣广汇", "鞋", "箱包", "批发", "零售", "MUJI", "无印良品", "名创", "购物"],
    "餐饮": ["餐", "食", "饭", "吃", "奶茶", "咖啡", "包子", "面馆", "燃面", "馄饨", "米线", "火锅", "烧烤", "小吃", "甜品", "汤", "饺", "堡", "快餐", "餐馆", "饭店", "面包", "华莱士", "麦当劳", "肯德基", "蜜雪", "老乡鸡", "猪脚饭", "盖浇", "炒饭", "盖饭", "黄焖", "鸡公煲", "烧烤", "炸鸡", "龙虾", "螃蟹", "茶", "油炸", "夜宵", "烧腊"],
}

# 收入分类关键词（微信等账单无收入分类列，按金额来源归类）
_CAT_INCOME_RULES = {
    "红包": ["红包", "利是", "压岁"],
    "工资": ["工资", "薪资", "薪", "发薪", "劳务", "薪水"],
    "奖金": ["奖金", "绩效", "奖励"],
    "理财": ["理财", "收益", "利息", "基金", "股票", "分红", "零钱通", "余额宝"],
    "兼职": ["兼职", "佣金", "提成", "跑腿", "稿费", "接单"],
}


def _auto_categorize(ttype: str, text: str) -> str:
    """根据 交易对方+商品+类型 文本自动归类；命中不了归「其他」。"""
    if not text:
        return "其他"
    t = text.lower()
    rules = _CAT_INCOME_RULES if ttype == "income" else _CAT_RULES
    for cat, kws in rules.items():
        for kw in kws:
            if kw.lower() in t:
                return cat
    if ttype == "income" and any(k in t for k in ("退款", "退回", "退还")):
        # 退款尽量按商户名归回原支出分类
        for cat, kws in _CAT_RULES.items():
            for kw in kws:
                if kw.lower() in t:
                    return cat
    return "其他"


def _local_parse_csv(text: str, allowed: dict = None):
    """无 AI 时的本地 CSV 解析兜底，返回 (rows, skipped, errors)。

    rows 为已规整、可直接入库的结构：{occurred, type, category, amount_cents, note}。
    ``allowed`` 形如 {"expense": {分类名...}, "income": {分类名...}}；缺省只用内置分类。
    """
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    lines = [ln for ln in reader if any(cell.strip() for cell in ln)]
    if not lines:
        return [], 0, ["文件为空"]

    header_row, col_map = _locate_header(lines)

    def cell(row, field):
        idx = col_map[field] if col_map else None
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    if col_map is None:
        return [], len(lines), ["未识别到表头（应有含「日期」与「金额」的列名），请先整理为标准流水或交由 AI 识别"]

    rows, skipped, errors = [], 0, []
    now = datetime.now()
    for i, raw in enumerate(lines):
        if i < header_row:
            continue  # 跳过表头上方说明/元信息
        if i == header_row:
            continue  # 表头
        row = [c.strip() for c in raw]
        if not row or all(c == "" for c in row):
            continue
        date_s = cell(row, "date")
        type_s = cell(row, "type")
        direction_s = cell(row, "direction")
        amount_s = cell(row, "amount")
        cat_s = cell(row, "category")
        note_s = cell(row, "note") or cell(row, "type")
        classify_text = " ".join(x for x in (cell(row, "merchant"), note_s, type_s) if x)
        try:
            amount = float(amount_s.replace(",", "").replace("¥", "").strip())
            if amount == 0:
                skipped += 1
                continue
            ttype = _ttype_of(direction_s, type_s, amount)
            occurred = _parse_dt(date_s) if date_s else now
            if occurred is None:
                try:
                    occurred = datetime.strptime(date_s, "%Y/%m/%d")
                except (ValueError, TypeError):
                    occurred = now
            cat = cat_s or "其他"
            known = (allowed or {}).get(ttype) or _valid_categories(ttype)
            # 保持原语义：CSV 里写着「其他」（或不在已知分类里）时，用备注再猜一次
            if cat == "其他" or cat not in known:
                cat = _auto_categorize(ttype, classify_text)
            if cat not in known:
                cat = "其他"
            rows.append({
                "occurred": occurred,
                "type": ttype,
                "category": cat,
                "amount_cents": int(round(abs(amount) * 100)),
                "note": (note_s or "")[:255],
            })
        except (ValueError, TypeError):
            skipped += 1
            errors.append(f"第{header_row + i + 1}行：金额无效「{amount_s}」")
    return rows, skipped, errors


def _normalize_rows(raw: list, allowed: dict = None) -> list[dict]:
    """把字典列表（AI 返回或前端回传）规整为可入库结构，无法识别的整行剔除。

    ``allowed`` 形如 {"expense": {分类名...}, "income": {分类名...}}；
    缺省只用内置分类。传入后可保留用户自定义分类，避免导入时被归成「其他」。
    """
    out = []
    now = datetime.now()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        try:
            amount = float(str(item.get("amount") or item.get("金额") or "0").replace(",", "").replace("¥", "").strip())
            if amount == 0:
                continue
            ts = str(item.get("type") or item.get("类型") or "")
            if "收" in ts or str(item.get("type") or "").strip().lower().startswith("inc"):
                ttype = "income"
            else:
                ttype = "expense"
            date_s = str(item.get("date") or item.get("日期") or "").strip()
            occurred = _parse_dt(date_s) if date_s else now
            if occurred is None:
                # 兼容 YYYY/MM/DD
                try:
                    occurred = datetime.strptime(date_s, "%Y/%m/%d")
                except (ValueError, TypeError):
                    occurred = now
            cat = str(item.get("category") or item.get("分类") or "").strip() or "其他"
            known = (allowed or {}).get(ttype) or _valid_categories(ttype)
            if cat not in known:
                cat = "其他"
            note = str(item.get("note") or item.get("备注") or "").strip()[:255]
            out.append({
                "occurred": occurred,
                "type": ttype,
                "amount_cents": int(round(abs(amount) * 100)),
                "category": cat,
                "note": note,
            })
        except (ValueError, TypeError):
            continue
    return out


def _insert_transactions(db: Session, uid: int, rows: list[dict]):
    imported = 0
    for r in rows:
        db.add(FinanceTransaction(
            user_id=uid,
            type=r["type"],
            amount_cents=r["amount_cents"],
            category=r["category"],
            note=r["note"],
            occurred_at=r["occurred"],
        ))
        imported += 1
    db.commit()
    return imported


FINANCE_AI_INSTRUCT = (
    "下面是个人记账流水（可能来自微信/支付宝/银行/各类 App/Excel 表格导出的原始内容，"
    "表头和列名任意、格式杂乱、夹杂无效行，甚至表头与数据混排）。请只输出符合给定 schema 的一个 JSON 对象，不要输出其它内容。"
    "先判断表头在哪一行、每列含义，把每条有效交易提取为一行 rows；金额无效或缺少日期的行放进 skipped 并简述原因；"
    "日期统一为 YYYY-MM-DD，金额为元（负数或带「支/消费/(-)」语义归支出，否则归收入）。"
    "分类尽量归到给定分类池。\n"
    "分类池：支出=餐饮/交通/购物/居家/娱乐/医疗/教育/人情/其他；收入=工资/奖金/理财/兼职/红包/其他。\n"
)


@router.post("/import/analyze")
async def import_analyze(
    payload: ImportIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """AI 识别 CSV 文本：把杂乱 CSV 归一为结构化流水并返回预览（不落库）。"""
    uid = current_user["user_id"]
    return ResponseBase(data=_analyze_table_text(db, uid, payload.csv.lstrip("\ufeff")))


@router.post("/import/analyze-file")
async def import_analyze_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """AI 识别上传的表格/文本文件（xlsx/xlsm/csv/txt），把任意表头/杂格式归一为结构化流水预览（不落库）。"""
    uid = current_user["user_id"]
    name = file.filename or ""
    ext = name.lower().rsplit(".", 1)[-1]
    if ext == "xls":
        # 旧版 .xls 为二进制 BIFF，openpyxl 不支持；提示另存
        return ResponseBase(data={
            "rows": [], "skipped": 0, "errors": ["暂不支持旧版 .xls，请先在 Excel 中另存为 .xlsx 或 CSV 后重试"],
            "is_fake": True, "provider": "fake", "summary": "",
        })

    binary = await file.read()
    if ext in ("xlsx", "xlsm"):
        text = _xlsx_to_text(binary)
    else:
        for enc in ("utf-8-sig", "gb18030", "utf-8"):
            try:
                text = binary.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = binary.decode("utf-8", errors="replace")
    return ResponseBase(data=_analyze_table_text(db, uid, text.lstrip("\ufeff")))


def _xlsx_to_text(binary: bytes) -> str:
    """把 Excel 首个工作表读为「CSV 风格」文本（表头 + 数据行），供 AI/本地解析重识别。"""
    wb = load_workbook(io.BytesIO(binary), read_only=True, data_only=True)
    try:
        ws = wb.active
        lines = []
        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c).strip() for c in row]
            if not any(cells):
                continue
            out = [('"' + c.replace('"', '""') + '"') if any(ch in c for ch in (",", "\n", '"')) else c for c in cells]
            lines.append(",".join(out))
        return "\n".join(lines)
    finally:
        wb.close()


def _analyze_table_text(db: Session, uid: int, text: str) -> dict:
    """核心：杂表/文本 → 归一化流水 → 预览（不落库）。

    存在用户已配置且启用的 AI Provider 时由 AI 识别（任意表头均可映射到 日期/收支/分类/金额/备注）；
    未配置、或 AI 异常/未吐出有效行时回退本地解析。
    """
    from app.services.ai_providers import AiRequest, FakeProvider
    from app.services.user_ai_provider import build_http_provider_from_config, resolve_user_provider

    cfg = resolve_user_provider(db, uid, None)
    provider, is_fake = (FakeProvider(), True) if not cfg else (build_http_provider_from_config(cfg), False)

    rows, skipped, errors, summary = [], 0, [], ""
    allowed = _allowed_categories(db, uid)
    if not is_fake:
        try:
            ai_text = _trim_to_header(text)  # 去掉表头上方说明/元信息，减少 AI 干扰
            resp = provider.invoke(AiRequest(
                ability="finance_csv_import",
                content=FINANCE_AI_INSTRUCT + f"\n原始数据：\n{ai_text}",
            ))
            data = resp.data or {}
            ai_rows = _normalize_rows(data.get("rows") or [], allowed)
            if ai_rows:
                rows, skipped, summary = ai_rows, len(data.get("skipped") or []), getattr(resp, "text", "")
            else:
                rows, skipped, errors = _local_parse_csv(text, allowed)
        except Exception:  # noqa: BLE001
            rows, skipped, errors = _local_parse_csv(text, allowed)
    else:
        rows, skipped, errors = _local_parse_csv(text, allowed)

    preview = [{
        "date": r["occurred"].strftime("%Y-%m-%d"),
        "type": r["type"],
        "amount": round(r["amount_cents"] / 100, 2),
        "category": r["category"],
        "note": r["note"],
    } for r in rows]
    return {
        "rows": preview,
        "skipped": skipped,
        "errors": errors[:20],
        "is_fake": is_fake,
        "provider": (provider.model if not is_fake else "fake"),
        "summary": summary,
    }


@router.post("/import/confirm")
async def import_confirm(
    payload: ImportRowsIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """确认导入 AI 识别（或本地解析）出的结构化流水，直接落库。"""
    uid = current_user["user_id"]
    rows = _normalize_rows(payload.rows, _allowed_categories(db, uid))
    imported = _insert_transactions(db, uid, rows)
    return ResponseBase(data={
        "imported": imported,
        "skipped": max(0, len(payload.rows or []) - len(rows)),
    })


@router.post("/import")
async def import_csv(
    payload: ImportIn = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """批量导入流水（本地直析，无 AI）。

    首行为表头（可选，可含 日期/类型/分类/金额(元)/备注 任一本站点导出列）；
    每行字段顺序与表头对应，缺省取本站点导出顺序。金额支持正负号推断收支。
    """
    uid = current_user["user_id"]
    rows, skipped, errors = _local_parse_csv(payload.csv, _allowed_categories(db, uid))
    imported = _insert_transactions(db, uid, rows)
    return ResponseBase(data={"imported": imported, "skipped": skipped, "errors": errors[:20]})
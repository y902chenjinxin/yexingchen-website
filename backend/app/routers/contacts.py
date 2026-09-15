"""家人通讯录 API。

生日只存「月-日」，返回时补算 `next_birthday` / `days_to_birthday` / `age`，
前端列表与日历视图都直接用这几个字段，不必各自重算。
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.family import Contact
from app.schemas.errors import ErrCode, raise_error
from app.services.family_reminder import next_birthday
from app.services.log_service import log_action
from app.services.softdelete import restore, soft_delete
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/contacts", tags=["家人通讯录"])

MMDD_RE = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def ok(data=None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data}


class ContactIn(BaseModel):
    name: str
    relation: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""
    birthday: Optional[str] = None       # MM-DD
    birth_year: Optional[int] = None
    birthday_type: Optional[str] = "solar"
    tags: Optional[str] = ""
    notes: Optional[str] = ""
    is_pinned: Optional[int] = 0
    sort_order: Optional[int] = 0

    @field_validator("name")
    @classmethod
    def name_check(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("姓名不能为空")
        if len(v) > 60:
            raise ValueError("姓名过长")
        return v

    @field_validator("birthday")
    @classmethod
    def birthday_check(cls, v):
        return _norm_birthday(v)


class ContactUpdateIn(BaseModel):
    name: Optional[str] = None
    relation: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[str] = None
    birth_year: Optional[int] = None
    birthday_type: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    is_pinned: Optional[int] = None
    sort_order: Optional[int] = None

    @field_validator("birthday")
    @classmethod
    def birthday_check(cls, v):
        return _norm_birthday(v)


def _norm_birthday(v):
    """生日统一收成 MM-DD；允许空串表示「清空」。"""
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return ""
    # 容错：用户可能填成 YYYY-MM-DD，只取月日
    if len(v) == 10 and v[4] == "-":
        v = v[5:]
    if not MMDD_RE.match(v):
        raise ValueError("生日格式应为 MM-DD（如 09-16）")
    return v


def _norm_type(v):
    return v if v in ("solar", "lunar") else "solar"


def _to_out(c: Contact, today: date | None = None) -> dict:
    today = today or date.today()
    nb = next_birthday(c.birthday, today)
    age = nb.year - c.birth_year if (nb and c.birth_year) else None
    return {
        "id": c.id,
        "name": c.name,
        "relation": c.relation or "",
        "phone": c.phone or "",
        "address": c.address or "",
        "birthday": c.birthday,
        "birth_year": c.birth_year,
        "birthday_type": c.birthday_type or "solar",
        "tags": c.tags or "",
        "notes": c.notes or "",
        "is_pinned": c.is_pinned or 0,
        "sort_order": c.sort_order or 0,
        "next_birthday": nb.strftime("%Y-%m-%d") if nb else None,
        "days_to_birthday": (nb - today).days if nb else None,
        "age": age if (age is not None and age > 0) else None,
        "created_at": str(c.created_at),
        "updated_at": str(c.updated_at),
    }


@router.get("")
def list_contacts(
    q: Optional[str] = None,
    relation: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Contact).filter(
        Contact.user_id == current_user["user_id"], Contact.deleted_at.is_(None)
    )
    if q:
        query = query.filter(
            or_(
                Contact.name.contains(q),
                Contact.relation.contains(q),
                Contact.phone.contains(q),
                Contact.address.contains(q),
                Contact.tags.contains(q),
            )
        )
    if relation:
        query = query.filter(Contact.relation == relation)

    # 数据量是「家人级」（几十条），排序在 Python 里算更直观：
    # 置顶优先 → 生日近的靠前 → 无生日 → 手工排序 → 姓名
    today = date.today()
    rows = [_to_out(c, today) for c in query.all()]
    rows.sort(key=lambda r: (
        0 if r["is_pinned"] else 1,
        0 if r["days_to_birthday"] is not None else 1,
        r["days_to_birthday"] if r["days_to_birthday"] is not None else 9999,
        r["sort_order"],
        r["name"],
    ))
    return ok({"list": rows, "total": len(rows)})


@router.get("/upcoming")
def upcoming_birthdays(
    days: int = Query(30, ge=1, le=366),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """未来 N 天内的生日（含今天），供待办/工作台提醒使用。"""
    today = date.today()
    rows = [
        _to_out(c, today)
        for c in db.query(Contact).filter(
            Contact.user_id == current_user["user_id"],
            Contact.deleted_at.is_(None),
            Contact.birthday.isnot(None),
        ).all()
    ]
    hits = [r for r in rows if r["days_to_birthday"] is not None and r["days_to_birthday"] <= days]
    hits.sort(key=lambda r: r["days_to_birthday"])
    return ok({"list": hits, "total": len(hits), "days": days})


@router.get("/{contact_id}")
def get_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = _ensure(db, contact_id, current_user["user_id"])
    return ok(_to_out(c))


@router.post("", status_code=201)
def create_contact(
    payload: ContactIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = Contact(
        user_id=current_user["user_id"],
        name=payload.name,
        relation=payload.relation or "",
        phone=payload.phone or "",
        address=payload.address or "",
        birthday=payload.birthday or None,
        birth_year=payload.birth_year,
        birthday_type=_norm_type(payload.birthday_type),
        tags=payload.tags or "",
        notes=payload.notes or "",
        is_pinned=payload.is_pinned or 0,
        sort_order=payload.sort_order or 0,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    log_action(
        db, current_user["user_id"], "create",
        target_type="contact", target_id=c.id, detail=f"新增联系人 {c.name}",
    )
    return ok(_to_out(c), "已添加")


@router.put("/{contact_id}")
def update_contact(
    contact_id: int,
    payload: ContactUpdateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = _ensure(db, contact_id, current_user["user_id"])
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise_error(ErrCode.INVALID_PARAM, "姓名不能为空")
        c.name = name
    for field in ("relation", "phone", "address", "tags", "notes"):
        v = getattr(payload, field)
        if v is not None:
            setattr(c, field, v)
    if payload.birthday is not None:
        c.birthday = payload.birthday or None
    if payload.birth_year is not None:
        c.birth_year = payload.birth_year or None
    if payload.birthday_type is not None:
        c.birthday_type = _norm_type(payload.birthday_type)
    if payload.is_pinned is not None:
        c.is_pinned = payload.is_pinned
    if payload.sort_order is not None:
        c.sort_order = payload.sort_order
    db.commit()
    db.refresh(c)
    log_action(
        db, current_user["user_id"], "update",
        target_type="contact", target_id=c.id, detail=f"更新联系人 {c.name}",
    )
    return ok(_to_out(c), "已保存")


@router.delete("/{contact_id}")
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = _ensure(db, contact_id, current_user["user_id"])
    soft_delete(c, db)
    log_action(
        db, current_user["user_id"], "delete",
        target_type="contact", target_id=contact_id, detail=f"删除联系人 {c.name}",
    )
    return ok({"ok": True}, "已删除")


@router.post("/{contact_id}/restore")
def restore_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    c = (
        db.query(Contact)
        .filter(
            Contact.id == contact_id,
            Contact.user_id == current_user["user_id"],
            Contact.deleted_at.isnot(None),
        )
        .first()
    )
    if not c:
        raise_error(ErrCode.INVALID_PARAM, "回收站中无此联系人", 404)
    restore(c, db)
    return ok(_to_out(c), "已恢复")


def _ensure(db: Session, contact_id: int, user_id: int) -> Contact:
    c = (
        db.query(Contact)
        .filter(
            Contact.id == contact_id,
            Contact.user_id == user_id,
            Contact.deleted_at.is_(None),
        )
        .first()
    )
    if not c:
        raise_error(ErrCode.INVALID_PARAM, "联系人不存在", 404)
    return c

"""密码保险箱 API（生活岛）。

按 v2.40.21 决策：**不加密**、**家庭共享**、记住 `uploader_id` 支持按人筛选。
接口层面不做「解锁」这套 —— 目标是显眼、好找、别忘；重要密码请用专业工具。
但列表默认由前端打码显示，避免家人旁观时被直接看到。
"""
from __future__ import annotations

import json
import secrets
import string
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vault import VaultEntry
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.household import HOUSEHOLD_ID, member_options, name_map
from app.services.log_service import log_action
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/vault", tags=["生活岛-密码保险箱"])

CATEGORIES = ["网站", "WiFi", "设备", "门禁", "其他"]

CHARSETS = {
    "all": string.ascii_letters + string.digits + "!@#$%^&*()-_=+",
    "safe": string.ascii_letters + string.digits,                 # 去符号：有些老旧系统不吃符号
    "digits": string.digits,
}


class VaultIn(BaseModel):
    title: str = ""
    url: str = ""
    username: str = ""
    password: str = ""
    note: str = ""
    category: str = "网站"
    tags: Optional[list[str]] = None


def _loads(raw: str) -> list:
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _to_out(e: VaultEntry, names: dict[int, str]) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "url": e.url or "",
        "username": e.username or "",
        "password": e.password or "",
        "note": e.note or "",
        "category": e.category or "网站",
        "tags": _loads(e.tags),
        "uploader_id": e.uploader_id,
        "uploader_name": names.get(e.uploader_id, "家人"),
        "created_at": str(e.created_at) if e.created_at else "",
        "updated_at": str(e.updated_at) if e.updated_at else "",
    }


def _get_or_404(db: Session, entry_id: int) -> VaultEntry:
    e = (
        db.query(VaultEntry)
        .filter(
            VaultEntry.id == entry_id,
            VaultEntry.household_id == HOUSEHOLD_ID,
            VaultEntry.deleted_at.is_(None),
        )
        .first()
    )
    if not e:
        raise_error(ErrCode.NOT_FOUND, "这条密码不存在")
    return e


@router.get("", response_model=ResponseBase)
def list_entries(
    uploader_id: Optional[int] = Query(None),
    category: str = Query(""),
    q: str = Query(""),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(VaultEntry).filter(
        VaultEntry.household_id == HOUSEHOLD_ID, VaultEntry.deleted_at.is_(None)
    )
    if uploader_id:
        query = query.filter(VaultEntry.uploader_id == uploader_id)
    if category:
        query = query.filter(VaultEntry.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                VaultEntry.title.like(like),
                VaultEntry.username.like(like),
                VaultEntry.url.like(like),
                VaultEntry.note.like(like),
            )
        )
    total = query.count()
    rows = (
        query.order_by(VaultEntry.updated_at.desc(), VaultEntry.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ResponseBase(data={
        "list": [_to_out(e, name_map(db)) for e in rows],
        "total": total,
        "categories": CATEGORIES,
    })


@router.get("/uploaders", response_model=ResponseBase)
def vault_uploaders(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return ResponseBase(data={"list": member_options(db)})


@router.get("/generate", response_model=ResponseBase)
def generate_password(
    length: int = Query(16, ge=6, le=64),
    charset: str = Query("all"),
    current_user: dict = Depends(get_current_user),
):
    """生成随机密码。与「随机密码」工具同一套字符集口径。"""
    pool = CHARSETS.get(charset) or CHARSETS["all"]
    # 每个字符独立均匀取样；secrets 保证密码学随机
    pwd = "".join(secrets.choice(pool) for _ in range(length))
    return ResponseBase(data={"password": pwd, "length": length, "charset": charset})


@router.post("", response_model=ResponseBase)
def create_entry(
    req: VaultIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not (req.title or "").strip():
        raise_error(ErrCode.INVALID_PARAM, "至少写个名称（比如「公司 WiFi」）")
    e = VaultEntry(
        household_id=HOUSEHOLD_ID,
        uploader_id=current_user["user_id"],
        title=req.title.strip()[:120],
        url=(req.url or "")[:300],
        username=(req.username or "")[:160],
        password=(req.password or "")[:300],
        note=req.note or "",
        category=(req.category or "网站")[:20],
        tags=json.dumps(req.tags or [], ensure_ascii=False),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    log_action(db, current_user["user_id"], "create", "vault", e.id, detail=f"新增密码：{e.title}")
    return ResponseBase(msg="已存进保险箱", data=_to_out(e, name_map(db)))


@router.put("/{entry_id}", response_model=ResponseBase)
def update_entry(
    entry_id: int,
    req: VaultIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    e = _get_or_404(db, entry_id)
    if req.title is not None:
        e.title = req.title.strip()[:120]
    e.url = (req.url or "")[:300]
    e.username = (req.username or "")[:160]
    if req.password is not None:
        e.password = (req.password or "")[:300]
    e.note = req.note or ""
    if req.category:
        e.category = req.category[:20]
    if req.tags is not None:
        e.tags = json.dumps(req.tags, ensure_ascii=False)
    db.commit()
    db.refresh(e)
    return ResponseBase(msg="已更新", data=_to_out(e, name_map(db)))


@router.delete("/{entry_id}", response_model=ResponseBase)
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    e = _get_or_404(db, entry_id)
    e.deleted_at = datetime.now()
    db.commit()
    log_action(db, current_user["user_id"], "delete", "vault", entry_id, detail=f"删除密码：{e.title}")
    return ResponseBase(msg="已删除")

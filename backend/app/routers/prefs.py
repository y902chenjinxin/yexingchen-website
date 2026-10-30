"""用户级偏好读写（v2.46.298）

用途：阅读器的排版设置（字号/行距/边距/字体/主题/自动日夜）跨设备同步。
设计成通用 key-value，后续衣柜、工作台这类「跟着人走」的配置也能直接复用。

- GET  /api/prefs/{key}  → { key, value }（value 是字符串，未设置时为空串）
- PUT  /api/prefs/{key}  → 覆盖保存
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.prefs import UserPref
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/prefs", tags=["用户偏好"])

# 单条偏好上限：阅读设置约 250 字节，留足余量；同时防止被当大文件存储用
MAX_VALUE_LEN = 8000
KEY_RE = re.compile(r"^[a-z0-9_]{1,64}$")


class PrefIn(BaseModel):
    value: str = Field(default="", max_length=MAX_VALUE_LEN)


def _check_key(key: str) -> str:
    if not KEY_RE.match(key):
        raise_error(ErrCode.INVALID_PARAM)
    return key


@router.get("/{key}", response_model=ResponseBase)
async def get_pref(
    key: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    key = _check_key(key)
    row = (
        db.query(UserPref)
        .filter(UserPref.user_id == current_user["user_id"], UserPref.key == key)
        .first()
    )
    return ResponseBase(data={
        "key": key,
        "value": row.value if row else "",
        "updated_at": str(row.updated_at) if row and row.updated_at else "",
    })


@router.put("/{key}", response_model=ResponseBase)
async def put_pref(
    key: str,
    body: PrefIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    key = _check_key(key)
    uid = current_user["user_id"]
    row = db.query(UserPref).filter(UserPref.user_id == uid, UserPref.key == key).first()
    if row:
        row.value = body.value
    else:
        db.add(UserPref(user_id=uid, key=key, value=body.value))
    db.commit()
    return ResponseBase(msg="已保存", data={"key": key})


@router.delete("/{key}", response_model=ResponseBase)
async def delete_pref(
    key: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    key = _check_key(key)
    db.query(UserPref).filter(
        UserPref.user_id == current_user["user_id"], UserPref.key == key
    ).delete()
    db.commit()
    return ResponseBase(msg="已清除")

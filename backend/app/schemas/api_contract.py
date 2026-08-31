"""统一 API 响应包装。

所有 workbench 接口返回 ApiResponse[T] = {code, msg, data}。
前端 axios 拦截器解包到 data 字段。
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = ""
    data: T | None = None


def ok(data: Any = None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def fail(code: int, msg: str, data: Any = None) -> dict:
    return {"code": code, "msg": msg, "data": data}

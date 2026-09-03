from fastapi import APIRouter, Depends
import asyncio
import time
from pydantic import BaseModel

import httpx
from app.schemas.common import *
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user
from app.config import settings

router = APIRouter(prefix="/api", tags=["视频去水印"])

# 串行锁：同一时刻只允许一个解析任务，避免并发冲击目标站点
_lock = asyncio.Lock()

# 按用户的简单限流（秒）——避免滥用
_RATE_SECONDS = 3
_last_by_user: dict = {}


class ParseRequest(BaseModel):
    url: str


@router.post("/video_parse", response_model=ResponseBase)
async def video_parse(
    req: ParseRequest,
    current_user: dict = Depends(get_current_user)
):
    url = (req.url or "").strip()
    if not url:
        raise_error(ErrCode.INVALID_PARAM, "请粘贴视频分享链接")

    uid = current_user["user_id"]
    now = time.monotonic()
    last = _last_by_user.get(uid, 0)
    if now - last < _RATE_SECONDS:
        raise_error(ErrCode.PARSE_RATE_LIMITED)
    _last_by_user[uid] = now

    endpoint = settings.PARSE_SERVICE_URL.rstrip("/") + "/parse"
    try:
        async with _lock:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(endpoint, json={"url": url})
    except Exception:
        raise_error(ErrCode.PARSE_FAILED, "解析服务暂不可用，请稍后重试")

    if resp.status_code != 200:
        raise_error(ErrCode.PARSE_FAILED, "解析失败，可能平台暂不支持或链接已失效")

    try:
        data = resp.json()
    except Exception:
        raise_error(ErrCode.PARSE_FAILED, "解析返回异常")

    return ResponseBase(data=data)
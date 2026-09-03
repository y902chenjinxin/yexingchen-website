"""独立视频解析服务：包装 parse-video-py，提供串行化解析接口。
运行：uvicorn main:app --host 0.0.0.0 --port 8070
全部请求经 asyncio.Lock 串行处理，避免并发冲击解析目标站点。
"""
import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from parse_video_py import parse_video_share_url
    BACKEND_OK = True
except Exception as e:  # pragma: no cover - 依赖缺失时服务仍可启动
    BACKEND_OK = False
    logging.getLogger(__name__).exception("parse_video_py import failed: %s", e)

app = FastAPI(title="Video Parse Service", version="1.0.0")
_lock = asyncio.Lock()


class ParseRequest(BaseModel):
    url: str


def _attr(obj, name):
    return getattr(obj, name, None) if obj is not None else None


def _serialize(info):
    author = _attr(info, "author")
    return {
        "title": _attr(info, "title"),
        "author": {
            "uid": _attr(author, "uid"),
            "name": _attr(author, "name"),
            "avatar": _attr(author, "avatar"),
        } if author else None,
        "video_url": _attr(info, "video_url"),
        "music_url": _attr(info, "music_url"),
        "cover_url": _attr(info, "cover_url"),
        "images": _attr(info, "images") or [],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "backend": BACKEND_OK}


@app.post("/parse")
async def parse(req: ParseRequest):
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url 不能为空")
    if not BACKEND_OK:
        raise HTTPException(status_code=503, detail="解析后端不可用")
    async with _lock:
        try:
            info = await parse_video_share_url(url)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"解析失败: {e}")
    if info is None:
        raise HTTPException(status_code=422, detail="解析结果为空，可能平台不支持或链接失效")
    return _serialize(info)
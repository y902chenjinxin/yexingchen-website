from fastapi import APIRouter, Depends
import asyncio
import time
import os
import shutil
import tempfile
from pydantic import BaseModel

import httpx
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
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


def _rate_check(uid: int):
    now = time.monotonic()
    last = _last_by_user.get(uid, 0)
    if now - last < _RATE_SECONDS:
        raise_error(ErrCode.PARSE_RATE_LIMITED)
    _last_by_user[uid] = now


async def _call_parse(url: str):
    """调用独立解析服务，返回 JSON。失败时抛统一错误。"""
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
    return data


@router.post("/video_parse", response_model=ResponseBase)
async def video_parse(
    req: ParseRequest,
    current_user: dict = Depends(get_current_user)
):
    url = (req.url or "").strip()
    if not url:
        raise_error(ErrCode.INVALID_PARAM, "请粘贴视频分享链接")

    _rate_check(current_user["user_id"])
    data = await _call_parse(url)
    return ResponseBase(data=data)


@router.post("/video_parse/audio")
async def video_parse_audio(
    req: ParseRequest,
    current_user: dict = Depends(get_current_user)
):
    """下载音频。平台提供音频源则原样透传；否则下载无水印视频经 ffmpeg 抽音轨成 mp3。"""
    url = (req.url or "").strip()
    if not url:
        raise_error(ErrCode.INVALID_PARAM, "请粘贴视频分享链接")

    _rate_check(current_user["user_id"])
    data = await _call_parse(url)

    music_url = (data or {}).get("music_url")
    if music_url:
        return ResponseBase(data={"mode": "direct", "url": music_url})

    video_url = (data or {}).get("video_url")
    if not video_url:
        raise_error(ErrCode.PARSE_FAILED, "该源没有可提取音频的视频")

    return await _extract_audio(video_url)


async def _extract_audio(video_url: str):
    if not shutil.which("ffmpeg"):
        raise_error(ErrCode.PARSE_FAILED, "服务端未安装 ffmpeg，暂无法抽取音频")

    tmpdir = tempfile.mkdtemp(prefix="prs_audio_")
    video_path = os.path.join(tmpdir, "src")
    out_mp3 = os.path.join(tmpdir, "audio.mp3")

    async def _cleanup():
        shutil.rmtree(tmpdir, ignore_errors=True)

    try:
        # 下载无水印视频（支持流式）
        async with _lock:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("GET", video_url) as r:
                    if r.status_code != 200:
                        raise_error(ErrCode.PARSE_FAILED, "视频下载失败，可能已失效或需重试")
                    with open(video_path, "wb") as f:
                        async for chunk in r.aiter_bytes(262144):
                            f.write(chunk)

            if os.path.getsize(video_path) == 0:
                raise_error(ErrCode.PARSE_FAILED, "下载的视频为空，请重试")

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", video_path,
                "-vn", "-acodec", "libmp3lame", "-b:a", "128k",
                out_mp3,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, err = await proc.communicate()
    except Exception as ex:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ex

    if proc.returncode != 0 or not os.path.exists(out_mp3):
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise_error(ErrCode.PARSE_FAILED, "音频抽取失败，该源可能无音轨")

    return FileResponse(
        out_mp3,
        media_type="audio/mpeg",
        filename="audio.mp3",
        background=BackgroundTask(_cleanup),
    )
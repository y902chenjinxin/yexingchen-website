from fastapi import APIRouter, Depends
import asyncio
import re
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


# 分享链接外可能还带着标题/口令等文案（抖音「7.35 复制打开抖音…」，B 站「【标题】 https://b23.tv/xxx」），
# 抠出其中第一条 http(s) 链接再交解析服务；纯 BV 号则补成完整链接（v2.46.136 起支持 B 站）
_URL_RE = re.compile(r"https?://[^\s\u4e00-\u9fff，。、；]+", re.I)
_BV_RE = re.compile(r"BV[0-9A-Za-z]{10}")
_URL_TAIL = "，,。.、；;：:）)]}\"'"


def _normalize(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    m = _URL_RE.search(text)
    if m:
        return m.group(0).rstrip(_URL_TAIL)
    bv = _BV_RE.search(text)
    if bv:
        return f"https://www.bilibili.com/video/{bv.group(0)}"
    return text


# B 站 CDN 校验 UA：无 UA（httpx 默认）会直接 403，抽音频前必须先带上浏览器 UA
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
)


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
    url = _normalize(req.url)
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
    url = _normalize(req.url)
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
        # 下载无水印视频（支持流式）。必须带浏览器 UA：B 站 CDN 对无 UA 请求直接 403
        async with _lock:
            async with httpx.AsyncClient(timeout=120, headers={"User-Agent": _BROWSER_UA}) as client:
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
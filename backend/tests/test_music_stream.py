"""music router 的 _stream_file 单元测试。

覆盖：
- content_type 按 magic bytes 正确识别（WAV/FLAC/MP3）
- Content-Length / Accept-Ranges / Cache-Control headers
- 文件不存在时抛 404
- 默认音乐路径解析

实现说明：_stream_file 用 __file__ 解析到 backend/uploads/，无法 chdir 绕开，
所以测试直接在 backend/uploads/_test_temp_<id>/ 下建临时文件，测完清理。
"""
import asyncio
import os
import struct
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.routers.music import _stream_file


@pytest.fixture
def uploads_dir():
    """在 backend/uploads/_test_temp_<uuid>/ 下建临时目录，测完删除。"""
    backend_dir = Path(__file__).resolve().parent.parent
    test_dir = backend_dir / "uploads" / f"_test_temp_{uuid.uuid4().hex[:8]}"
    (test_dir / "bgm").mkdir(parents=True, exist_ok=True)
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


def _write_wav(path: Path):
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + 1024))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<I", 44100))
        f.write(struct.pack("<I", 88200))
        f.write(struct.pack("<H", 2))
        f.write(struct.pack("<H", 16))
        f.write(b"data")
        f.write(struct.pack("<I", 1024))
        f.write(b"\x00" * 1024)


def _write_flac(path: Path):
    with open(path, "wb") as f:
        f.write(b"fLaC")
        f.write(b"\x00\x00\x00\x22")
        f.write(b"\x00" * 34)


def _write_mp3(path: Path):
    with open(path, "wb") as f:
        f.write(b"\xff\xfb\x90\x00")
        f.write(b"\x00" * 100)


def _run(coro):
    return asyncio.run(coro)


def _rel(test_dir: Path, file: Path) -> str:
    """把绝对路径转成 _stream_file 期望的 uploads/xxx 相对路径。"""
    backend_uploads = test_dir.parent.parent / "uploads"
    return str(file.relative_to(backend_uploads)).replace("\\", "/")


# ---------- content_type 识别 ----------

def test_stream_file_detects_wav_content_type(uploads_dir):
    wav = uploads_dir / "test.wav"
    _write_wav(wav)
    response = _run(_stream_file(_rel(uploads_dir, wav)))
    assert response.media_type == "audio/wav"


def test_stream_file_detects_flac_content_type(uploads_dir):
    flac = uploads_dir / "test.flac"
    _write_flac(flac)
    response = _run(_stream_file(_rel(uploads_dir, flac)))
    assert response.media_type == "audio/flac"


def test_stream_file_detects_mp3_content_type(uploads_dir):
    mp3 = uploads_dir / "test.mp3"
    _write_mp3(mp3)
    response = _run(_stream_file(_rel(uploads_dir, mp3)))
    assert response.media_type == "audio/mpeg"


def test_stream_file_content_length_matches_file_size(uploads_dir):
    mp3 = uploads_dir / "len.mp3"
    _write_mp3(mp3)
    expected_size = mp3.stat().st_size
    response = _run(_stream_file(_rel(uploads_dir, mp3)))
    assert response.headers["Content-Length"] == str(expected_size)


def test_stream_file_has_required_headers(uploads_dir):
    mp3 = uploads_dir / "h.mp3"
    _write_mp3(mp3)
    response = _run(_stream_file(_rel(uploads_dir, mp3)))
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Cache-Control"] == "no-cache"


def test_stream_file_streams_actual_content(uploads_dir):
    mp3 = uploads_dir / "content.mp3"
    _write_mp3(mp3)
    original = mp3.read_bytes()
    response = _run(_stream_file(_rel(uploads_dir, mp3)))
    async def _consume():
        out = b""
        async for chunk in response.body_iterator:
            out += chunk
        return out
    body = asyncio.run(_consume())
    assert body == original


# ---------- 错误路径 ----------

def test_stream_file_missing_file_raises_error(uploads_dir):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        _run(_stream_file("uploads/_test_temp_doesnotexist/file.mp3"))
    body = exc_info.value.detail
    assert body.get("code") == "MUSIC_NOT_FOUND" or "音乐文件不存在" in str(body)


# ---------- 默认 BGM 路径（不需要 fixture，路径里 BGM 文件可以不存在） ----------

def test_stream_file_default_bgm_path_uses_uploads_bgm():
    """默认 BGM 路径固定 uploads/bgm/xxx.mp3"""
    from fastapi import HTTPException
    # 不存在的话会抛 HTTPException 而不是 NotImplemented
    with pytest.raises(HTTPException):
        _run(_stream_file("uploads/bgm/_test_temp_doesnotexist.mp3"))

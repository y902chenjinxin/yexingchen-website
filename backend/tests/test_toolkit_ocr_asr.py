"""工具岛 OCR / ASR 路由测试（v2.40.14）。

路由本身不落库（鉴权用注入的 user dict），故无需内存库建表；
本机/CI 不装推理依赖，因此只测「校验与降级」路径 + 纯函数，真实推理留生产取证。
"""
import asyncio
import io
import struct
import wave

import pytest
from fastapi import HTTPException

from app.routers import asr as asr_mod
from app.routers import ocr as ocr_mod


def _wav_bytes(seconds=1.0, sr=16000, freq=440.0):
    """生成合法的 16k 单声道 WAV 字节（正弦波）。"""
    n = int(seconds * sr)
    frames = b"".join(
        struct.pack("<h", int(0.3 * 32767 * __import__("math").sin(2 * 3.14159 * freq * i / sr)))
        for i in range(n)
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(frames)
    return buf.getvalue()


class _FakeUpload:
    def __init__(self, data: bytes):
        self.file = io.BytesIO(data)


def _user():
    return {"user_id": 1, "email": "a@b.c", "role": "user"}


# ---------------- OCR ----------------

def test_ocr_rejects_empty():
    with pytest.raises(HTTPException) as ei:
        asyncio.run(ocr_mod.recognize(file=_FakeUpload(b""), current_user=_user()))
    assert ei.value.status_code in (400, 503)   # 空文件 / 引擎未装（本地 CI 无 rapidocr）


def test_ocr_rejects_oversize():
    with pytest.raises(HTTPException) as ei:
        asyncio.run(ocr_mod.recognize(file=_FakeUpload(b"x" * (13 * 1024 * 1024)), current_user=_user()))
    # 引擎未装时先撞 503；已装则应撞 400 超限
    assert ei.value.status_code in (400, 503)


def test_ocr_rejects_bad_image():
    with pytest.raises(HTTPException) as ei:
        asyncio.run(ocr_mod.recognize(file=_FakeUpload(b"not-an-image" * 10), current_user=_user()))
    assert ei.value.status_code in (400, 503)


# ---------------- ASR ----------------

def test_asr_status_shape():
    body = asr_mod.status(current_user=_user())   # 同步路由，直接调用
    assert body["code"] == 0
    assert set(body["data"].keys()) == {"ready", "engine", "model"}


def test_asr_rejects_bad_wav():
    with pytest.raises(HTTPException) as ei:
        asyncio.run(asr_mod.transcribe(file=_FakeUpload(b"not-a-wav"), current_user=_user()))
    # 纯函数 _read_wav_bytes 在引擎检查之前/之后均可能先触发，两种错误都可接受
    assert ei.value.status_code in (400, 503)


def test_asr_wav_reader_and_resampler():
    """纯函数直测：合法 WAV 解析 + 任意采样率重采样到 16k。"""
    raw = _wav_bytes(seconds=0.5, sr=44100)
    samples, sr = asr_mod._read_wav_bytes(raw)
    assert sr == 44100
    assert str(samples.dtype) == "float32"
    rs = asr_mod._resample(samples, sr)
    assert len(rs) == int(0.5 * 16000)

    raw16 = _wav_bytes(seconds=0.3, sr=16000)
    s2, sr2 = asr_mod._read_wav_bytes(raw16)
    assert sr2 == 16000
    assert asr_mod._resample(s2, sr2) is s2  # 同采样率不重采样


def test_asr_tag_regex_strips_sensevoice_markers():
    # SenseVoice 真实输出形如「今天天气<|en|><|zh|><|NEUTRAL|>不错」
    text = asr_mod._TAG_RE.sub("", "今天天气<|en|><|zh|><|NEUTRAL|>不错").strip()
    assert text == "今天天气不错"

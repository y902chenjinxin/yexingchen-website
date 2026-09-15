"""MiniMax 音色克隆 + 语音合成（T2A）客户端。

接口事实（2026-09 核对自 platform.minimaxi.com 官方文档）：

1. 上传复刻音频  POST {base}/v1/files/upload   multipart: purpose=voice_clone + file
   - mp3/m4a/wav；时长 10s–5min；≤20MB → 返回 file.file_id
2. 快速复刻      POST {base}/v1/voice_clone    json: file_id + voice_id(+text/model 试听)
   - voice_id 自定义：字母开头，[8,256]，字母/数字/-/_
   - 复刻本身不收费；**首次用该音色合成时**才收克隆费
   - 临时音色：168h 内无任何 T2A 调用即被删除
3. 语音合成      POST {base}/v1/t2a_v2         json: model + text + voice_setting
   - 返回 data.audio 为 **hex 编码的 mp3 字节**（不是 base64，也不是 URL）

域名差异：国内站 api.minimaxi.com（双 i），国际站 api.minimax.io。
共享 Provider 的 base_url 两者都可能，按传入 cfg 判定，不写死。
"""
from __future__ import annotations

import binascii
import re
import secrets
import time

import httpx

import logging

logger = logging.getLogger(__name__)

TTS_MODEL = "speech-02-hd"  # 稳定版；2.8/2.6 系列为 newer 选项，这里取文档长期列出的稳定型号

ALLOWED_AUDIO_EXT = (".mp3", ".m4a", ".wav")
MAX_AUDIO_BYTES = 20 * 1024 * 1024

_VOICE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{7,255}$")


class MiniMaxVoiceError(RuntimeError):
    """MiniMax 语音接口错误（带人类可读 msg，路由层直接透给前端）。"""


def is_minimax_base(base_url: str | None) -> bool:
    """判定 Provider 配置是否指向 MiniMax（音色克隆仅对 MiniMax 开放）。"""
    return bool(base_url) and "minimax" in (base_url or "").lower()


def gen_voice_id() -> str:
    """生成合规 voice_id：字母开头 + 16 位随机 hex（8 字符下限留足余量）。"""
    return "yh" + secrets.token_hex(9)  # 2 + 18 = 20 字符


def _api_base(cfg) -> str:
    base = (cfg.base_url or "").rstrip("/")
    # Provider 的 base_url 是 OpenAI 风格（.../v1）；MiniMax 端点也挂在 /v1 下，同源复用
    if base.endswith("/v1"):
        return base
    if base:
        return base + "/v1"
    raise MiniMaxVoiceError("该 Provider 未配置 base_url，无法调用 MiniMax 语音接口")


def _check_base_resp(payload: dict, action: str) -> dict:
    base_resp = payload.get("base_resp") or {}
    code = base_resp.get("status_code", 0)
    if code != 0:
        msg = base_resp.get("status_msg") or f"MiniMax {action} 失败（{code}）"
        # 常见错误翻译成用户能懂的话
        hints = {
            1004: "API Key 无效或权限不足",
            1043: "样本音频与校验文本相似度过低",
            2038: "音色已过期（临时音色 7 天未使用会被删除）",
            2039: "音色不存在",
        }
        hint = hints.get(code)
        if hint:
            msg = f"{msg}：{hint}"
        raise MiniMaxVoiceError(msg)
    return payload


def upload_clone_audio(cfg, data: bytes, filename: str, purpose: str = "voice_clone") -> int:
    """上传复刻样本 → file_id。"""
    import os

    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXT:
        raise MiniMaxVoiceError("仅支持 mp3 / m4a / wav 格式的样本音频")
    if len(data) == 0:
        raise MiniMaxVoiceError("样本音频为空")
    if len(data) > MAX_AUDIO_BYTES:
        raise MiniMaxVoiceError("样本音频超过 20MB 上限")

    url = _api_base(cfg) + "/files/upload"
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {cfg.api_key}"},
        data={"purpose": purpose},
        files={"file": (filename or f"clone{ext}", data)},
        timeout=120,
    )
    if r.status_code != 200:
        raise MiniMaxVoiceError(f"上传失败（HTTP {r.status_code}）：{r.text[:200]}")
    payload = _check_base_resp(r.json(), "上传音频")
    file_id = (payload.get("file") or {}).get("file_id")
    if not file_id:
        raise MiniMaxVoiceError("上传响应中缺少 file_id")
    return int(file_id)


def clone_voice(cfg, file_id: int, voice_id: str, preview_text: str = "") -> dict:
    """快速复刻。preview_text 非空时返回 demo_audio 试听链接。"""
    if not _VOICE_ID_RE.match(voice_id):
        raise MiniMaxVoiceError("voice_id 不合规：字母开头，8 位以上，仅字母/数字/-/_")

    body: dict = {"file_id": file_id, "voice_id": voice_id}
    if preview_text:
        body["text"] = preview_text[:1000]
        body["model"] = TTS_MODEL

    r = httpx.post(
        _api_base(cfg) + "/voice_clone",
        headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=180,
    )
    if r.status_code != 200:
        raise MiniMaxVoiceError(f"复刻失败（HTTP {r.status_code}）：{r.text[:200]}")
    payload = _check_base_resp(r.json(), "音色复刻")
    return {
        "voice_id": voice_id,
        "demo_audio": payload.get("demo_audio") or "",
    }


def tts(cfg, text: str, voice_id: str, *, speed: float = 1.0) -> bytes:
    """T2A 同步合成。返回 mp3 字节（hex 字段解码）。"""
    text = (text or "").strip()
    if not text:
        raise MiniMaxVoiceError("合成文本不能为空")
    if len(text) > 2000:
        raise MiniMaxVoiceError("单次合成最长 2000 字，请分段")

    r = httpx.post(
        _api_base(cfg) + "/t2a_v2",
        headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
        json={
            "model": TTS_MODEL,
            "text": text,
            "stream": False,
            "voice_setting": {"voice_id": voice_id, "speed": speed, "vol": 1.0, "pitch": 0},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3"},
        },
        timeout=180,
    )
    if r.status_code != 200:
        raise MiniMaxVoiceError(f"合成失败（HTTP {r.status_code}）：{r.text[:200]}")
    payload = _check_base_resp(r.json(), "语音合成")
    audio_hex = (payload.get("data") or {}).get("audio") or ""
    if not audio_hex:
        raise MiniMaxVoiceError("合成响应中缺少音频数据")
    try:
        return binascii.unhexlify(audio_hex)
    except (binascii.Error, ValueError):
        # 兜底：部分版本/代理可能直接给 URL
        if audio_hex.startswith("http"):
            dl = httpx.get(audio_hex, timeout=120)
            if dl.status_code == 200:
                return dl.content
        raise MiniMaxVoiceError("音频数据解码失败")

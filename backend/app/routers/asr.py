"""语音转文字（工具岛）—— sherpa-onnx + SenseVoice 本地推理，纯 CPU，无外部 API。

选型：funasr+torch 运行时要 1.5GB+ 内存；sherpa-onnx 走 onnxruntime，wheel 仅几十 MB，
SenseVoiceSmall int8 模型约 230MB，CPU 上 17x 实时（FunASR 官方基准中文 CER 4.2%，
显著优于 Whisper 的 9.8%）。

约定：前端把任意音频（录音 webm / mp3 / m4a …）用 AudioContext 解码后重采样为
16k 单声道 WAV 再上传（浏览器 decodeAudioData 原生支持这些容器），服务端因此
不需要 ffmpeg。若上传的不是 16k，服务端用 numpy 线性重采样兜底。

POST /api/asr          multipart: file=<wav>    -> {"text": "...", "seconds": 3.2}
GET  /api/asr/status                            -> {"ready": bool, "model": str|null}

模型目录（按序探测）：
  backend/models/sherpa-onnx-sense-voice/          （model.int8.onnx + tokens.txt）
也可用环境变量 ASR_MODEL_DIR 指向含这两文件的目录。
模型缺失时接口返回 503 与明确提示，服务其余功能不受影响。
"""
from __future__ import annotations

import io
import os
import re
import struct
import threading
import wave

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.utils.security import get_current_user

router = APIRouter(prefix="/api/asr", tags=["工具岛-语音转文字"])

_MAX_BYTES = 25 * 1024 * 1024          # 16k 单声道 16bit ≈ 13 分钟音频
_TARGET_SR = 16000

_ASR_READY = False
try:
    import numpy as np  # noqa: F401  — onnxruntime 系硬依赖，独立于 sherpa
except Exception:  # pragma: no cover
    np = None

try:
    import sherpa_onnx  # noqa: F401
    _ASR_READY = np is not None
except Exception:  # pragma: no cover
    sherpa_onnx = None
    _ASR_READY = False

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))

_MODEL_DIRS = [
    os.environ.get("ASR_MODEL_DIR", ""),
    os.path.join(_BACKEND_DIR, "models", "sherpa-onnx-sense-voice"),
    "/var/www/yexingchen/backend/models/sherpa-onnx-sense-voice",
]

_recognizer = None
_recognizer_lock = threading.Lock()
_model_name = None

_TAG_RE = re.compile(r"<\|[^|]*\|>")   # SenseVoice 输出里的 <|zh|>|<|NEUTRAL|> 等标记


def _resolve_model_dir() -> str:
    for d in _MODEL_DIRS:
        if not d:
            continue
        if os.path.isfile(os.path.join(d, "model.int8.onnx")) and os.path.isfile(os.path.join(d, "tokens.txt")):
            return d
    return ""


def _get_recognizer():
    """懒加载单例；模型缺失抛 503（前端据此提示「服务端未启用」）。"""
    global _recognizer, _model_name
    if _recognizer is None:
        with _recognizer_lock:
            if _recognizer is None:
                model_dir = _resolve_model_dir()
                if not model_dir:
                    raise HTTPException(
                        status_code=503,
                        detail="服务端未启用语音识别：模型未部署（缺少 model.int8.onnx / tokens.txt）",
                    )
                try:
                    _recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                        model=os.path.join(model_dir, "model.int8.onnx"),
                        tokens=os.path.join(model_dir, "tokens.txt"),
                        num_threads=2,
                        use_itn=True,
                    )
                    _model_name = os.path.basename(model_dir)
                except Exception as exc:  # noqa: BLE001
                    _recognizer = None
                    raise HTTPException(status_code=500, detail=f"ASR 引擎初始化失败：{str(exc)[:160]}")
    return _recognizer


def _read_wav_bytes(raw: bytes):
    """读 WAV -> (float32 samples, sample_rate)。"""
    try:
        with wave.open(io.BytesIO(raw), "rb") as wf:
            sr = wf.getframerate()
            nch = wf.getnchannels()
            width = wf.getsampwidth()
            n_frames = wf.getnframes()
            pcm = wf.readframes(n_frames)
    except Exception:
        raise HTTPException(status_code=400, detail="不是有效的 WAV 文件（前端会自动转 16k 单声道 WAV）")

    if width == 2:
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 4:
        samples = np.frombuffer(pcm, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif width == 1:
        samples = (np.frombuffer(pcm, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise HTTPException(status_code=400, detail=f"不支持的位宽 {width * 8}bit")
    if nch > 1:
        samples = samples.reshape(-1, nch).mean(axis=1)
    return samples, sr


def _resample(samples, sr: int):
    if sr == _TARGET_SR or len(samples) == 0:
        return samples
    duration = len(samples) / sr
    n_out = max(1, int(duration * _TARGET_SR))
    x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    return np.interp(x_new, x_old, samples).astype(np.float32)


@router.get("/status")
def status(current_user: dict = Depends(get_current_user)):
    model_dir = _resolve_model_dir()
    return {
        "code": 0, "msg": "ok",
        "data": {
            "ready": bool(_ASR_READY and model_dir),
            "engine": "sherpa-onnx-sense-voice" if _ASR_READY else None,
            "model": os.path.basename(model_dir) if model_dir else None,
        },
    }


@router.post("")
async def transcribe(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not _ASR_READY:
        raise HTTPException(status_code=503, detail="服务端未启用语音识别（缺 sherpa-onnx）")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="音频超过 25MB（约 13 分钟），请分段")

    samples, sr = _read_wav_bytes(raw)
    samples = _resample(samples, sr)
    seconds = round(len(samples) / _TARGET_SR, 2)
    if seconds < 0.2:
        raise HTTPException(status_code=400, detail="音频太短")

    recognizer = _get_recognizer()
    try:
        stream = recognizer.create_stream()
        stream.accept_waveform(_TARGET_SR, samples)
        recognizer.decode_stream(stream)
        text = _TAG_RE.sub("", stream.result.text or "").strip()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"识别失败：{str(exc)[:160]}")

    return {"code": 0, "msg": "ok", "data": {"text": text, "seconds": seconds}}

"""OCR 文字识别（工具岛）—— RapidOCR 本地推理，无需任何外部 API key。

选型说明：workbench/ai_advanced.py 里已有 /ai/ocr，但它依赖高德 key 或多模态
Provider，未配置即不可用；工具岛需要开箱即用的本地引擎，故用 RapidOCR
（PaddleOCR 的 onnxruntime 移植，模型随 wheel 自带，纯 CPU，中文强）。

POST /api/ocr          multipart: file=<图片>   -> {"text": "...", "lines": n, "engine": "rapidocr"}
限制：单图 ≤ 12MB。
"""
from __future__ import annotations

import io
import threading

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.utils.security import get_current_user

router = APIRouter(prefix="/api/ocr", tags=["工具岛-OCR"])

_MAX_BYTES = 12 * 1024 * 1024

_OCR_READY = False
try:
    from rapidocr_onnxruntime import RapidOCR  # noqa: F401
    _OCR_READY = True
except Exception:  # pragma: no cover - 依赖未装时路由降级
    RapidOCR = None

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    """懒加载单例：首次调用才初始化模型（约 1s），避免拖慢启动。"""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = RapidOCR()
    return _engine


@router.post("")
async def recognize(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not _OCR_READY:
        raise HTTPException(status_code=503, detail="服务端未启用 OCR 引擎（缺 rapidocr_onnxruntime）")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="图片超过 12MB，请压缩后再试")

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析的图片文件")

    try:
        # RapidOCR 接受 numpy/路径/字节；直接喂原始字节最省事
        result, _elapsed = _get_engine()(raw)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"OCR 推理失败：{str(exc)[:160]}")

    lines = []
    if result:
        for _box, text, score in result:
            lines.append({"text": str(text), "score": round(float(score), 4)})
    text = "\n".join(item["text"] for item in lines)

    return {"code": 0, "msg": "ok", "data": {"text": text, "lines": len(lines), "engine": "rapidocr"}}

"""证件照 AI 人像分割（服务端 MODNet ONNX CPU 推理）
浏览器端 onnxruntime-web 的 WASM 后端对动态 INT8 量化算子输出全零，
故把模型推理迁到服务端（CPU 已验证：同一量化模型在 CPU 上产出正确人像 mask），
客户端传图 -> 收全分辨率 matte，再复用前端 applyMatte 落 alpha。
返回体：{"code":0,"msg":"ok","data":{"w":<源宽>,"h":<源高>,"b64":<全分辨率灰度 matte PNG base64>}}
"""
from __future__ import annotations

import io
import os
import threading

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from PIL import Image

from app.utils.security import get_current_user

router = APIRouter(prefix="/api/idphoto", tags=["工具岛-证件照"])

ONNX_READY = False
try:
    import numpy as np
    import onnxruntime as ort
    ONNX_READY = True
except Exception:  # pragma: no cover
    np = None
    ort = None

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))          # <repo>/backend/app/routers
_BACKEND_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))        # <repo>/backend

MODEL_CANDIDATES = [
    # 线上后端部署目录（部署时把 model-q 上传为 backend/models/modnet.onnx）
    os.path.join(_BACKEND_DIR, "models", "modnet.onnx"),
    "/var/www/yexingchen/backend/models/modnet.onnx",
    # 仓库内自托管模型（本地开发）
    os.path.join(_BACKEND_DIR, "models", "modnet", "model-q.onnx"),
]

_session = None
_session_lock = threading.Lock()
_model_path = None


def _resolve_model() -> str:
    for p in MODEL_CANDIDATES:
        if p and os.path.exists(p):
            return p
    # 兜底：后端目录 models/modnet.onnx
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(base, exist_ok=True)
    p = os.path.join(base, "modnet.onnx")
    return p if os.path.exists(p) else ""


def _get_session():
    global _session, _model_path
    if _session is not None:
        return _session
    with _session_lock:
        if _session is not None:
            return _session
        if not ONNX_READY:
            raise RuntimeError("onnxruntime 未安装")
        p = _resolve_model()
        if not p:
            raise RuntimeError("未找到 MODNet 模型文件")
        _model_path = p
        _session = ort.InferenceSession(
            p,
            providers=["CPUExecutionProvider"],
            sess_options=ort.SessionOptions(),
        )
        return _session


def _preprocess(img: Image.Image) -> tuple:
    W = H = 512
    sw, sh = img.size
    ratio = min(W / sw, H / sh)
    nw = max(1, round(sw * ratio))
    nh = max(1, round(sh * ratio))
    ox = (W - nw) // 2
    oy = (H - nh) // 2
    small = img.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(small, (ox, oy))
    arr = np.asarray(canvas, dtype=np.float32) / 127.5 - 1.0
    x = arr.transpose(2, 0, 1)[None]
    return x, (ox, oy, nw, nh)


@router.post("/matte")
async def idphoto_matte(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    if not ONNX_READY or ort is None:
        raise HTTPException(status_code=500, detail="服务端未安装 onnxruntime")
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片超过 20MB")
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析图片")
    w, h = img.size
    try:
        x, _box = _preprocess(img)
        sess = _get_session()
        out = sess.run(["output"], {"input": x})[0][0, 0]  # 512x512 float32
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"推理失败: {exc}")

    # 上采样到原图尺寸，编码灰度 PNG
    matte_img = Image.fromarray(
        (np.clip(out, 0.0, 1.0) * 255).astype("uint8")
    ).resize((w, h), Image.BILINEAR)
    buf = io.BytesIO()
    matte_img.save(buf, format="PNG")
    import base64
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"code": 0, "msg": "ok", "data": {"w": w, "h": h, "b64": b64}}
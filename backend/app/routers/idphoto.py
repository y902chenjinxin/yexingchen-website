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


# ---------------------------------------------------------------- matte 后处理
# v2.46.239：MODNet 在 512×512 上推理，直接双线性放大到 4000px 边长后过渡带
# 也被放大 8 倍 —— 人像边缘会出现「一圈半透明的雾」（夜星：「边缘还是不行」）。
# 另外原实现把**含黑边的 512 方图**整体 resize 回原图，非 1:1 照片的 mask
# 会被压缩偏移。两处一起修：① 按 letterbox 的 box 裁回再放大；
# ② 用原图亮度做引导滤波，把过渡带贴到真实轮廓上。

def _box(a, r):
    """均值滤波（积分图实现，O(N)，不依赖 scipy）。边缘按窗口内实际像素数归一。"""
    h, w = a.shape
    I = np.zeros((h + 1, w + 1), dtype=np.float32)
    np.cumsum(np.cumsum(a.astype(np.float32), axis=0), axis=1, out=I[1:, 1:])
    ys = np.arange(h)
    xs = np.arange(w)
    y0 = np.clip(ys - r, 0, h)
    y1 = np.clip(ys + r + 1, 0, h)
    x0 = np.clip(xs - r, 0, w)
    x1 = np.clip(xs + r + 1, 0, w)
    S = (I[np.ix_(y1, x1)] - I[np.ix_(y0, x1)]
         - I[np.ix_(y1, x0)] + I[np.ix_(y0, x0)])
    cnt = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float32)
    return S / cnt


def _guided(guide, src, r=8, eps=1e-4):
    """引导滤波（He et al.）：用原图亮度当引导，把 alpha 的过渡带吸附到真实边缘。"""
    I = guide.astype(np.float32)
    p = src.astype(np.float32)
    mI = _box(I, r)
    mp = _box(p, r)
    cov = _box(I * p, r) - mI * mp
    var = _box(I * I, r) - mI * mI
    a = cov / (var + eps)
    b = mp - a * mI
    return _box(a, r) * I + _box(b, r)


# 后处理面积上限：原图可能有 1200 万像素，全量做 10 次均值滤波要 ~500MB 峰值，
# 小 CVM 扛不住。超过就降采样做细化再放回去（无损于观感，因为要细化的就是过渡带）。
_MAX_REFINE_PX = 6_000_000


def _refine_alpha(matte_img, rgb_img, lo=0.10, hi=0.86, radius=8, feather=1):
    """matte → 干净 alpha：软阈值去雾 + 引导滤波贴边 + 1px 羽化去锯齿。"""
    w, h = rgb_img.size
    scale = 1.0
    area = w * h
    if area > _MAX_REFINE_PX:
        scale = (_MAX_REFINE_PX / area) ** 0.5
    rw = max(1, int(round(w * scale)))
    rh = max(1, int(round(h * scale)))
    a_img = matte_img if (rw, rh) == (w, h) else matte_img.resize((rw, rh), Image.BILINEAR)
    g_img = rgb_img if (rw, rh) == (w, h) else rgb_img.resize((rw, rh), Image.BILINEAR)

    a = np.asarray(a_img, dtype=np.float32) / 255.0
    # ① 软阈值：<lo 的雾状残影压成 0、>hi 的压成 1，中间线性 —— 保留真实半透明（发丝）
    a = np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    # ② 引导滤波：过渡带贴到原图真实轮廓上（这一步是「边缘锐利」的关键）
    gray = np.asarray(g_img.convert("L"), dtype=np.float32) / 255.0
    a = np.clip(_guided(gray, a, r=radius, eps=1e-4), 0.0, 1.0)
    # ③ 1px 羽化：去掉阈值带来的硬锯齿
    if feather > 0:
        a = np.clip(_box(a, feather), 0.0, 1.0)

    out = Image.fromarray((a * 255.0 + 0.5).astype("uint8"), mode="L")
    if (rw, rh) != (w, h):
        out = out.resize((w, h), Image.BICUBIC)
    return out


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
        x, _box_info = _preprocess(img)
        sess = _get_session()
        out = sess.run(["output"], {"input": x})[0][0, 0]  # 512x512 float32
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"推理失败: {exc}")

    # ① 先把 512 方图里**真正的图像区域**裁出来（去掉 letterbox 黑边），再放大到原图尺寸。
    #    旧实现直接把含黑边的整张 512 方图 resize 回原图 —— 非 1:1 的照片
    #    mask 会整体被压缩并偏移，表现为「抠出来的边缘和人像对不上」。
    ox, oy, nw, nh = _box_info
    raw = Image.fromarray((np.clip(out, 0.0, 1.0) * 255).astype("uint8"), mode="L")
    raw = raw.crop((ox, oy, ox + nw, oy + nh)).resize((w, h), Image.BILINEAR)
    # ② 细化：软阈值去雾 + 引导滤波贴边 + 羽化
    matte_img = _refine_alpha(raw, img)
    buf = io.BytesIO()
    matte_img.save(buf, format="PNG")
    import base64
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"code": 0, "msg": "ok", "data": {"w": w, "h": h, "b64": b64}}
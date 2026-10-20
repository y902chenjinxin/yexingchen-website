"""按需缩略图（v2.46.145）。

为什么要有它：
  `/uploads/` 已经由 nginx 直出并带 30 天缓存，**慢的不是缓存，是原图本身**。
  实测生产 42 张图平均 1.1MB，最狠的是一张 10.6MB 的通讯录头像、9.7MB 的倒计时背景。
  列表/头像/卡片这些位置只需要 160~480px 的图，却一直在下原图。

设计要点：
  · **按需生成 + 落盘缓存**：第一次请求才处理，之后直接命中磁盘（`uploads/_thumbs/<w>/<hash>.webp`），
    所以历史图片不用回填脚本，也不用改已有数据。
  · **尺寸白名单**：只允许 160/240/320/480/768/960，避免被刷出无数尺寸把磁盘写满。
  · **防目录穿越**：resolve 后必须仍在 uploads 根目录内。
  · **失败即降级**：Pillow 打不开（如 HEIC）就 302 回原图，不让页面挂图。
  · 输出统一 WebP（质量 82），实测比同尺寸 JPEG 再小 25~40%。
"""
from __future__ import annotations

import hashlib
import os

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, RedirectResponse
from PIL import Image, ImageOps

router = APIRouter(prefix="/api/uploads", tags=["上传-缩略图"])

# backend/uploads —— 本文件在 backend/app/routers/，所以要往上两级才是 backend
# （踩过：写 `..` 会指到 backend/app/uploads，导致每次都 302 回原图、缩略图形同虚设）
UPLOAD_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
THUMB_ROOT = os.path.join(UPLOAD_ROOT, "_thumbs")

# 白名单：只处理这些宽度（列表 160/240、卡片 320/480、详情 768/960）
SIZES = (160, 240, 320, 480, 768, 960)
DEFAULT_W = 480
# 只处理常规位图；HEIC/TIFF 之类交给降级分支
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

CACHE_HEADER = {"Cache-Control": "public, max-age=31536000, immutable"}


def _resolve_src(rel: str) -> str | None:
    """把相对路径解析成 uploads 下的绝对路径；越界返回 None。"""
    rel = (rel or "").lstrip("/")
    if not rel:
        return None
    path = os.path.realpath(os.path.join(UPLOAD_ROOT, rel))
    if not (path == UPLOAD_ROOT or path.startswith(UPLOAD_ROOT + os.sep)):
        return None
    return path


def _thumb_path(src: str, width: int) -> str:
    """缩略图落盘路径：用「源路径 + 宽度 + 源 mtime」做 key，源图换了自动失效。"""
    try:
        mtime = int(os.path.getmtime(src))
    except OSError:
        mtime = 0
    key = hashlib.md5(f"{os.path.relpath(src, UPLOAD_ROOT)}|{width}|{mtime}".encode()).hexdigest()[:16]
    return os.path.join(THUMB_ROOT, str(width), f"{key}.webp")


@router.get("/thumb")
def thumb(
    p: str = Query(..., description="uploads 下的相对路径，如 contacts/xxx.jpg"),
    w: int = Query(DEFAULT_W, description="目标宽度（白名单内的会被吸附到最近档）"),
):
    src = _resolve_src(p)
    if not src or not os.path.isfile(src):
        return RedirectResponse("/uploads/" + p.lstrip("/"), status_code=302)

    ext = os.path.splitext(src)[1].lower()
    # 非位图（HEIC 等）或已经是小图：直接回原图
    if ext not in ALLOWED_EXT:
        return RedirectResponse("/uploads/" + p.lstrip("/"), status_code=302)

    width = min(SIZES, key=lambda s: abs(s - int(w or DEFAULT_W)))
    out = _thumb_path(src, width)

    if not os.path.exists(out):
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)  # 手机照片的旋转要按 EXIF 摆正
                # 已经比目标还小就别放大（放大只会更糊更占空间）
                if im.width > width:
                    im.thumbnail((width, width * 4), Image.LANCZOS)
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
                # 写临时文件再改名：并发请求不会读到半个文件
                tmp = f"{out}.{os.getpid()}.tmp"
                im.save(tmp, "WEBP", quality=82, method=5)
                os.replace(tmp, out)
        except Exception:  # noqa: BLE001 —— 任何解码失败都降级回原图
            return RedirectResponse("/uploads/" + p.lstrip("/"), status_code=302)

    return FileResponse(out, media_type="image/webp", headers=CACHE_HEADER)

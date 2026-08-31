"""URL / 文件 / 内容校验工具。"""
from __future__ import annotations

import io
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

# 允许的 scheme（避免 file://, javascript:, data: 等）
ALLOWED_URL_SCHEMES = ("http", "https")
# 单条 URL 最大长度（含 scheme）
MAX_URL_LENGTH = 2048


class UrlValidationError(ValueError):
    """URL 校验失败。"""


def validate_http_url(url: str, *, max_length: int = MAX_URL_LENGTH) -> str:
    """校验 URL：
    - 必须为字符串；
    - 长度 <= max_length；
    - 仅允许 http / https；
    - 必须包含 host；
    - 拒绝含 userinfo（防止 http://user:pass@host 注入）；
    - 拒绝空 host 或仅端口；
    - 拒绝控制字符。

    返回规范化后的 URL。
    """
    if not isinstance(url, str):
        raise UrlValidationError("URL 必须是字符串")
    if not url:
        raise UrlValidationError("URL 不能为空")
    if len(url) > max_length:
        raise UrlValidationError(f"URL 长度超过 {max_length}")

    # 控制字符 / 空白
    if any(ord(c) < 0x20 or ord(c) == 0x7f for c in url):
        raise UrlValidationError("URL 包含非法控制字符")
    if any(c in url for c in (" ", "\t", "\n", "\r")):
        raise UrlValidationError("URL 不能包含空白字符")

    try:
        parsed = urlparse(url)
    except Exception as exc:  # noqa: BLE001
        raise UrlValidationError(f"URL 解析失败: {exc}") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        raise UrlValidationError(f"URL scheme 必须是 http 或 https，得到 {scheme!r}")

    if parsed.username or parsed.password:
        raise UrlValidationError("URL 不能包含用户名密码")

    host = parsed.hostname
    if not host:
        raise UrlValidationError("URL 缺少 host")

    # 拒绝明显的本地 / 回环地址
    if _is_local_host(host):
        raise UrlValidationError(f"不允许本地地址 {host}")

    return url


def _is_local_host(host: str) -> bool:
    """判断 host 是否为本地 / 回环 / IPv6 本地。

    包括：localhost, 0.0.0.0, ::1, 127.0.0.0/8, ::/128（IPv6 回环前缀）。
    """
    h = (host or "").lower().strip("[]")
    if h in ("localhost", "0.0.0.0", "::1", "::"):
        return True
    # IPv4 回环：127.0.0.0/8
    if h.startswith("127."):
        return True
    # IPv6 回环：::1、::ffff:127.0.0.1
    if h.startswith("::ffff:127."):
        return True
    return False


# ============================================================
# 文件扩展名 / MIME / 内容校验
# ============================================================
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_PDF_EXT = {".pdf"}

ALLOWED_IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/bmp",
}
ALLOWED_PDF_MIMES = {"application/pdf"}

# 图片 magic number 头部
_IMAGE_MAGIC = (
    b"\x89PNG",         # PNG
    b"GIF8",           # GIF87a / GIF89a
    b"\xff\xd8\xff",   # JPEG
    b"RIFF",           # WEBP (后续 4 字节含 WEBP)
    b"BM",             # BMP
)


def _split_ext(filename: str) -> str:
    """从文件名取扩展名（小写，含 .）。"""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def classify_upload(filename: str, content_type: str) -> str:
    """根据扩展名判定文件类型，返回 'image' / 'pdf' / 抛 ValueError。"""
    ext = _split_ext(filename)
    ctype = (content_type or "").lower().strip()
    if ext in _IMAGE_EXT:
        return "image"
    if ext in _PDF_EXT:
        return "pdf"
    raise ValueError(f"不支持的文件类型：ext={ext!r} content_type={ctype!r}")


def verify_image_content(data: bytes) -> None:
    """用 Pillow 校验图片真实内容；失败抛 ValueError。

    要求 Pillow 已安装（在 requirements.txt 中）。
    """
    if not data:
        raise ValueError("图片数据为空")
    # 快速 magic 检查
    if not any(data.startswith(s) for s in _IMAGE_MAGIC):
        raise ValueError("图片 magic 校验失败")
    try:
        from PIL import Image  # 延迟导入

        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"图片内容校验失败: {exc}") from exc


def verify_pdf_content(data: bytes) -> None:
    if not data:
        raise ValueError("PDF 数据为空")
    if not data.startswith(b"%PDF-"):
        raise ValueError("PDF 头部校验失败")


def verify_upload(
    *,
    filename: str,
    content_type: str,
    data: bytes,
    max_size: int,
    expected_kind: str,  # 'image' or 'pdf'
) -> None:
    """统一校验：扩展名 + content_type + 大小 + 内容。

    expected_kind 必须与 classify_upload 的结果一致。
    """
    kind = classify_upload(filename, content_type)
    if kind != expected_kind:
        raise ValueError(f"文件类型与预期不符：kind={kind} expected={expected_kind}")

    ctype = (content_type or "").lower().strip()
    if expected_kind == "image" and ctype not in ALLOWED_IMAGE_MIMES:
        raise ValueError(f"图片 content_type 非法：{content_type!r}")
    if expected_kind == "pdf" and ctype not in ALLOWED_PDF_MIMES:
        raise ValueError(f"PDF content_type 非法：{content_type!r}")

    if len(data) > max_size:
        raise ValueError(f"文件超过大小限制 {max_size} bytes")

    if expected_kind == "image":
        verify_image_content(data)
    else:
        verify_pdf_content(data)


# ============================================================
# 分块读取（避免无上限全量读入内存）
# ============================================================
async def read_upload_chunks(
    file,  # starlette.datastructures.UploadFile
    *,
    chunk_size: int = 64 * 1024,
    max_bytes: int,
) -> bytes:
    """从 UploadFile 读取字节，限制最大字节数。

    超过 max_bytes 抛 ValueError。
    """
    buf = bytearray()
    remaining = max_bytes + 1  # 容忍多读 1 字节以判断超限
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise ValueError(f"文件超过大小限制 {max_bytes} bytes")
    return bytes(buf)


# ============================================================
# 笔记附件大小校验
# ============================================================
MAX_NOTE_ATTACHMENT_TOTAL = 200 * 1024 * 1024  # 200 MB


def check_note_attachment_total(existing_total: int, new_size: int) -> None:
    """单条笔记附件总量上限 200 MB。"""
    if existing_total + new_size > MAX_NOTE_ATTACHMENT_TOTAL:
        raise ValueError(
            f"单条笔记附件总量将超过 {MAX_NOTE_ATTACHMENT_TOTAL // (1024 * 1024)} MB 上限"
        )


# ============================================================
def _guess_mime(ext: str) -> str:
    """根据扩展名猜测 MIME。"""
    e = (ext or "").lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".pdf": "application/pdf",
    }
    return mapping.get(e, "application/octet-stream")


# ============================================================
# 笔记/资产详情辅助
# ============================================================
def safe_filename(name: str) -> str:
    """从原始文件名生成安全的展示文件名（防路径穿越）。"""
    if not name:
        return ""
    name = name.replace("\\", "/").split("/")[-1]
    # 去掉 ASCII 控制字符
    name = re.sub(r"[\x00-\x1f]", "", name)
    return name[:255]


def file_size_human(n: int) -> str:
    """把字节数格式化为人类可读字符串。"""
    if n is None:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    size = float(n)
    for u in units:
        if size < 1024:
            return f"{size:.1f} {u}"
        size /= 1024
    return f"{size:.1f} TB"

import os
import uuid
import time
from werkzeug.utils import secure_filename
from fastapi import UploadFile
from app.config import settings


ALLOWED_MUSIC_EXTENSIONS = {"mp3", "flac", "wav"}
ALLOWED_NOVEL_EXTENSIONS = {"epub", "pdf", "txt"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm"}
ALLOWED_COVER_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def generate_filename(original_filename: str) -> str:
    ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""
    timestamp = int(time.time())
    unique = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique}.{ext}"


def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


async def save_upload_file(file: UploadFile, sub_dir: str, allowed_extensions: set, max_size: int) -> tuple[str, int]:
    if not file.filename:
        raise ValueError("文件名不能为空")

    if not allowed_file(file.filename, allowed_extensions):
        raise ValueError(f"不支持的文件格式，仅支持: {', '.join(allowed_extensions)}")

    # 读取文件内容检查大小
    content = await file.read()
    file_size = len(content)

    if file_size > max_size:
        raise ValueError(f"文件大小超出限制，最大 {max_size // (1024*1024)}MB")

    # 生成安全文件名
    filename = generate_filename(file.filename)
    upload_dir = os.path.join(settings.UPLOAD_DIR, sub_dir)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)

    # 写回磁盘
    with open(file_path, "wb") as f:
        f.write(content)

    relative_path = f"/{sub_dir}/{filename}"
    return relative_path, file_size


def delete_file(file_path: str):
    """删除文件，file_path 为相对路径如 /music/xxx.mp3"""
    if not file_path:
        return
    full_path = os.path.join(settings.UPLOAD_DIR, file_path.lstrip("/"))
    if os.path.exists(full_path):
        os.remove(full_path)
"""本地文件存储服务（StorageService 接口 + LocalStorageProvider）。

- save: 写入并返回 metadata；
- open_stream: 返回文件字节流 + size，调用方按需消费；
- delete_file: 删除物理文件；
- safe_resolve: 校验路径不越权。
"""
from __future__ import annotations

import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

from werkzeug.utils import secure_filename


class StorageService(ABC):
    @abstractmethod
    def save(
        self,
        *,
        user_id: int,
        file_type: str,
        original_filename: str,
        data: bytes,
    ) -> dict: ...

    @abstractmethod
    def open_path(self, *, user_id: int, storage_path: str) -> Path: ...

    @abstractmethod
    def delete(self, *, user_id: int, storage_path: str) -> None: ...

    @abstractmethod
    def exists(self, *, storage_path: str) -> bool: ...


class LocalStorageProvider(StorageService):
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 路径校验 ----------
    def _resolve(self, storage_path: str) -> Path:
        if not storage_path or ".." in storage_path:
            raise PermissionError(f"非法路径: {storage_path}")
        target = (self.root_dir / storage_path).resolve()
        if not str(target).startswith(str(self.root_dir)):
            raise PermissionError(f"非法路径: {storage_path}")
        return target

    def _check_user_dir(self, user_id: int, target: Path) -> None:
        parts = target.relative_to(self.root_dir).parts
        if len(parts) < 2 or parts[0] != "users" or parts[1] != str(int(user_id)):
            raise PermissionError(f"路径不属于当前用户: {target}")

    # ---------- 接口实现 ----------
    def save(
        self,
        *,
        user_id: int,
        file_type: str,
        original_filename: str,
        data: bytes,
    ) -> dict:
        raw_ext = Path(original_filename or "").suffix.lower()
        ext = "." + secure_filename(raw_ext.lstrip(".")) if raw_ext else ""
        ext = "".join(c for c in ext if c.isalnum() or c == ".")[:16]
        safe_name = f"{uuid.uuid4().hex}{ext}"
        rel_dir = Path("users") / str(int(user_id)) / file_type
        abs_dir = self.root_dir / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        abs_path = abs_dir / safe_name
        with open(abs_path, "wb") as f:
            f.write(data)
        storage_path = str(rel_dir / safe_name).replace("\\", "/")
        # 由调用方根据上下文决定 mime_type
        from app.utils.validation import _guess_mime

        mime = _guess_mime(ext)
        return {
            "storage_path": storage_path,
            "file_size": len(data),
            "mime_type": mime,
            "original_filename": original_filename or "",
        }

    def open_path(self, *, user_id: int, storage_path: str) -> Path:
        target = self._resolve(storage_path)
        self._check_user_dir(user_id, target)
        if not target.exists():
            raise FileNotFoundError(storage_path)
        return target

    def stat(self, *, storage_path: str) -> dict:
        """返回文件大小、修改时间等元数据。"""
        target = self._resolve(storage_path)
        st = target.stat()
        return {"size": st.st_size, "mtime": st.st_mtime, "path": target}

    def delete(self, *, user_id: int, storage_path: str) -> None:
        target = self._resolve(storage_path)
        self._check_user_dir(user_id, target)
        if target.exists() and target.is_file():
            target.unlink()

    def exists(self, *, storage_path: str) -> bool:
        try:
            target = self._resolve(storage_path)
            return target.exists()
        except PermissionError:
            return False


# 单例
_storage: Optional[StorageService] = None


def get_storage() -> StorageService:
    global _storage
    if _storage is None:
        upload_dir = os.environ.get("UPLOAD_DIR") or "./uploads"
        _storage = LocalStorageProvider(upload_dir)
    return _storage


def reset_storage_for_tests(provider: Optional[StorageService]) -> None:
    global _storage
    _storage = provider

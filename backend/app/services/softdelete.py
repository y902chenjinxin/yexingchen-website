"""软删除与回收站通用工具。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterable, Type

from sqlalchemy.orm import Session

from app.models.workbench import Asset, WorkbenchLog

logger = logging.getLogger(__name__)

TRASH_RETENTION_DAYS = 30


def soft_delete(obj, db: Session) -> None:
    if obj is None:
        return
    if getattr(obj, "deleted_at", None) is None:
        obj.deleted_at = datetime.now()
    db.add(obj)
    db.commit()


def restore(obj, db: Session) -> None:
    if obj is None:
        return
    obj.deleted_at = None
    db.add(obj)
    db.commit()


def active_query(db: Session, model: Type):
    return db.query(model).filter(model.deleted_at.is_(None))


def trash_query(db: Session, model: Type):
    return db.query(model).filter(model.deleted_at.isnot(None))


def log_workbench_action(
    db: Session,
    *,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int | None,
    detail: str = "",
) -> None:
    db.add(
        WorkbenchLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail or "",
        )
    )
    db.commit()


def cleanup_expired_trash(
    db: Session,
    models: Iterable[Type],
    *,
    days: int = TRASH_RETENTION_DAYS,
) -> int:
    """物理删除超过 days 天的回收站记录。

    - 对 Asset 类型，先尝试删除物理文件：
      - 文件删除成功 → 删除 Asset 记录；
      - 文件删除失败 → 保留 Asset 记录，标记 cleanup_failed_at / cleanup_error，
        等待下一次清理重试，绝不丢失数据库引用。
    """
    from app.services.storage_service import get_storage

    threshold = datetime.now() - timedelta(days=days)
    cleaned = 0
    for model in models:
        rows = (
            db.query(model)
            .filter(model.deleted_at.isnot(None))
            .filter(model.deleted_at < threshold)
            .all()
        )
        for r in rows:
            if isinstance(r, Asset):
                # 跳过曾清理失败的；只有再过一天再试
                if getattr(r, "cleanup_failed_at", None) and (
                    datetime.now() - r.cleanup_failed_at
                ) < timedelta(days=1):
                    logger.info(
                        "skip recently failed cleanup asset_id=%s", r.id
                    )
                    continue
                storage_path = getattr(r, "storage_path", None)
                user_id = getattr(r, "user_id", None)
                if storage_path and user_id:
                    try:
                        get_storage().delete(
                            user_id=user_id, storage_path=storage_path
                        )
                        # 文件已删 → 清除失败标记（重试成功）
                        r.cleanup_failed_at = None
                        r.cleanup_error = None
                    except FileNotFoundError:
                        # 文件已不存在，按清理成功处理
                        r.cleanup_failed_at = None
                        r.cleanup_error = None
                    except Exception as exc:  # noqa: BLE001
                        # 删除失败：标记并跳过数据库删除
                        logger.warning(
                            "cleanup asset file failed: asset_id=%s err=%s",
                            r.id,
                            exc,
                        )
                        r.cleanup_failed_at = datetime.now()
                        r.cleanup_error = str(exc)[:500]
                        db.add(r)
                        continue
            db.delete(r)
            cleaned += 1
    db.commit()
    return cleaned

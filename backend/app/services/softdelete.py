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

    - 对 Asset 类型，先尝试删除物理文件（委托给 AssetTrashCleaner）：
      - 文件删除成功 → 删除 Asset 记录；
      - 文件不存在 / 没有文件 → 视为成功，删除 Asset 记录；
      - 失败冷却期内 → 跳过；
      - 删除失败 → 保留 Asset 记录并标记 cleanup_failed_at / cleanup_error，
        等待下一次清理重试，绝不丢失数据库引用。
    - 其他模型直接 db.delete。
    """
    from app.services.asset_trash import AssetTrashCleaner

    threshold = datetime.now() - timedelta(days=days)
    cleaner = AssetTrashCleaner()
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
                if cleaner.should_skip_recently_failed(r):
                    continue
                status, _err = cleaner.try_cleanup(r)
                if status == AssetTrashCleaner.FAILED:
                    db.add(r)
                    continue
                # CLEANED（含无文件情况）：继续 db.delete
            db.delete(r)
            cleaned += 1
    db.commit()
    return cleaned

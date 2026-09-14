"""Asset 回收站清理：物理文件删除 + 失败重试。

把 Asset 特有的"删除文件 → 标记重试"逻辑从 softdelete.cleanup_expired_trash 抽出，
主流程保持原接口，AssetTrashCleaner 内部处理"快失败冷却 + 文件删除 + 错误标记"。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.models.workbench import Asset
from app.services.storage_service import get_storage

logger = logging.getLogger(__name__)

# 失败重试冷却：上次失败后多久才能再尝试
RETRY_COOLDOWN = timedelta(days=1)

# 单次错误信息最大长度（DB 列约束）
MAX_ERROR_LEN = 500


class AssetTrashCleaner:
    """Asset 物理文件清理策略。

    try_cleanup 返回三种状态：
    - (CLEANED, None)         文件已删（成功），调用方可以 db.delete(asset)
    - (SKIP, None)            处于失败冷却中，调用方什么都不做
    - (FAILED, error)         删除失败，调用方记录错误并跳过
    """

    CLEANED = "cleaned"
    SKIP = "skip"
    FAILED = "failed"

    @staticmethod
    def should_skip_recently_failed(asset: Asset) -> bool:
        """失败冷却期内跳过（避免每次都重试同一个失败）。"""
        last = getattr(asset, "cleanup_failed_at", None)
        if last and (datetime.now() - last) < RETRY_COOLDOWN:
            logger.info("skip recently failed cleanup asset_id=%s", asset.id)
            return True
        return False

    @staticmethod
    def try_cleanup(asset: Asset) -> Tuple[str, Optional[str]]:
        """尝试删除物理文件；返回 (status, error_message)。"""
        storage_path = getattr(asset, "storage_path", None)
        user_id = getattr(asset, "user_id", None)
        if not storage_path or not user_id:
            # 没有物理文件（link 类资产），视为已清理
            return AssetTrashCleaner.CLEANED, None

        try:
            get_storage().delete(user_id=user_id, storage_path=storage_path)
            # 文件已删 → 清除失败标记
            asset.cleanup_failed_at = None
            asset.cleanup_error = None
            return AssetTrashCleaner.CLEANED, None
        except FileNotFoundError:
            # 文件已不存在，按清理成功处理
            asset.cleanup_failed_at = None
            asset.cleanup_error = None
            return AssetTrashCleaner.CLEANED, None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "cleanup asset file failed: asset_id=%s err=%s", asset.id, exc,
            )
            asset.cleanup_failed_at = datetime.now()
            asset.cleanup_error = str(exc)[:MAX_ERROR_LEN]
            return AssetTrashCleaner.FAILED, str(exc)[:MAX_ERROR_LEN]

"""资讯订阅源后台自动同步，供生产环境定时抓取所有源并入库。"""
from __future__ import annotations

import logging
from datetime import datetime

from app.database import SessionLocal
from app.models.feed import FeedSource
from app.routers.feed._fetch import _fetch_source_articles, _upsert_articles

logger = logging.getLogger(__name__)

# 自动同步间隔（秒）：每 60 分钟一次
FEED_SYNC_INTERVAL = 3600
# 启动预热后首次抓取的等待时间（秒）
FEED_SYNC_WARMUP = 30


def sync_all_sources_once() -> dict:
    """抓取全部未删除订阅源并入库，返回统计（幂等，按 guid 去重）。"""
    added = 0
    total = 0
    failed = 0
    with SessionLocal() as db:
        rows = (
            db.query(FeedSource)
            .filter(FeedSource.deleted_at.is_(None))
            .all()
        )
        total = len(rows)
        for s in rows:
            try:
                articles = _fetch_source_articles(s)
                added += _upsert_articles(db, s, articles)
                s.last_status = 1
                s.last_error = ""
                s.last_check_at = datetime.now()
            except Exception as exc:  # noqa: BLE001
                failed += 1
                s.last_status = 2
                s.last_error = str(exc)[:255]
                s.last_check_at = datetime.now()
        db.commit()
    if total:
        logger.info(
            "资讯自动同步完成：%d 个源，新增 %d 篇，失败 %d 个",
            total,
            added,
            failed,
        )
    return {"total": total, "added": added, "failed": failed}
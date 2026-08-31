"""生产环境 schema 保护。

在 ENV=production 时，强制要求：
1. 数据库已执行 alembic upgrade head；
2. alembic_version 唯一对应 head；
3. alembic_version 不允许出现多个 head（迁移树必须线性）；
4. 空库、未迁移、落后版本均 fail-fast。
5. 非生产环境直接返回。
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class ProductionSchemaError(RuntimeError):
    """生产环境 schema 校验失败时的可读异常。"""


HEAD_REVISION = "b2c3d4e5f6a7"


def is_production_env() -> bool:
    return os.environ.get("ENV", "").strip().lower() == "production"


def _count_heads(engine: Engine) -> int:
    """检查 alembic_version 表是否唯一对应 head revision。

    返回行数（应为 1）。多行意味着迁移树出现多个 head。
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            return len(rows)
    except SQLAlchemyError as exc:
        logger.debug("alembic_version not queryable: %s", exc)
        return 0


def get_alembic_version(engine: Engine) -> Optional[str]:
    """从 alembic_version 表读取当前 revision；表不存在返回 None。"""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).first()
            return row[0] if row else None
    except SQLAlchemyError as exc:
        logger.debug("alembic_version not queryable: %s", exc)
        return None


def assert_production_schema_ok(engine: Engine) -> None:
    """生产环境 fail-fast 校验。"""
    if not is_production_env():
        return

    cnt = _count_heads(engine)
    if cnt == 0:
        raise ProductionSchemaError(
            "Production database has not been migrated. "
            "请在启动应用前执行: alembic upgrade head"
        )

    if cnt > 1:
        raise ProductionSchemaError(
            f"Production alembic_version 表存在 {cnt} 行，说明迁移树存在多个 head。"
            "请用 alembic heads 检查并合并后重新升级。"
        )

    version = get_alembic_version(engine)
    if version is None:
        raise ProductionSchemaError("alembic_version 表为空，无法确认当前版本")

    if version != HEAD_REVISION:
        raise ProductionSchemaError(
            f"Production alembic version mismatch: db={version!r} != head={HEAD_REVISION!r}. "
            "请执行: alembic upgrade head"
        )

    logger.info("Production schema OK: alembic head=%s", HEAD_REVISION)


def check_schema_for_env(engine: Engine, *, env: Optional[str] = None) -> None:
    """显式入口，便于测试传 env。"""
    saved = os.environ.get("ENV")
    try:
        if env is not None:
            os.environ["ENV"] = env
        if is_production_env():
            assert_production_schema_ok(engine)
    finally:
        if env is not None:
            if saved is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = saved

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
from pathlib import Path
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class ProductionSchemaError(RuntimeError):
    """生产环境 schema 校验失败时的可读异常。"""


def _alembic_versions_dir() -> Path:
    """定位 alembic/versions 目录。"""
    # schema_guard.py 位于 backend/app/services/schema_guard.py
    # alembic/versions 在 backend/alembic/versions
    return Path(__file__).resolve().parent.parent.parent / "alembic" / "versions"


def _discover_heads(versions_dir: Path) -> List[str]:
    """扫描 alembic/versions 下的所有迁移文件，找出真正的 head revisions。

    head = 没有任何其他迁移的 ``down_revision`` 指向它。
    改用扫描而不是 ``alembic heads`` 子进程，避免生产启动时多一次进程开销。
    """
    if not versions_dir.is_dir():
        return []

    revisions: dict[str, Optional[str]] = {}
    for py in versions_dir.glob("*.py"):
        if py.name.startswith("_"):
            continue
        text = py.read_text(encoding="utf-8")
        rev = _down_rev = None
        for line in text.splitlines():
            line = line.strip()
            if (line.startswith("revision ") or line.startswith("revision:")) and "=" in line:
                # revision = "xxxxx"  或  revision = ('a', 'b')
                rev = _parse_value(line.split("=", 1)[1])
            elif (line.startswith("down_revision ") or line.startswith("down_revision:")) and "=" in line:
                _down_rev = _parse_value(line.split("=", 1)[1])
        if rev:
            revisions[rev] = _down_rev

    # 所有被任何迁移 down_revision 引用的 revision 不是
    # head = 至少有一个 revision 没有被引用
    referenced = {v for v in revisions.values() if v}
    # 元组形式（branch_labels）需要平展
    flat_referenced = set()
    for r in referenced:
        flat_referenced.add(r)
    heads = [r for r in revisions if r not in flat_referenced]
    return sorted(heads)


def _parse_value(raw: str) -> Optional[str]:
    """解析 alembic 的 revision / down_revision 赋值右侧，返回第一个 revision id（如果是元组取第一个）。"""
    raw = raw.strip().rstrip(",").strip()
    if not raw or raw == "None":
        return None
    # 元组形式 ('a', 'b') → 取第一个
    if raw.startswith("(") and raw.endswith(")"):
        inner = raw[1:-1].strip()
        if not inner:
            return None
        first = inner.split(",", 1)[0].strip().strip("'\"")
        return first or None
    return raw.strip("'\"")


def resolved_env() -> str:
    """当前运行环境标识。

    优先取真实环境变量（生产 pm2 / CI 会显式传入），其次回落到 ``.env`` 里的 ``ENV``。
    前者兼容既有部署方式，后者避免「同一份配置，pm2 重启一次就变回非生产」——
    这个差异会让 `/docs` 悄悄对外可用（见 ISSUES ENV-008）。
    """
    value = os.environ.get("ENV") or ""
    if not value:
        try:
            from app.config import settings  # 延迟导入，避免与 config 形成导入环

            value = getattr(settings, "ENV", "") or ""
        except Exception:  # noqa: BLE001 — 配置不可用时按非生产处理，不影响主流程
            value = ""
    return value.strip().lower()


def is_production_env() -> bool:
    return resolved_env() == "production"


def docs_urls() -> dict:
    """FastAPI 的文档路由配置。

    生产环境必须**三处一起关**：只关 `docs_url` 时 `/openapi.json` 仍可访问，
    等于把全部接口结构公开（本次实测：三者在生产都是 200）。
    抽成函数是为了让「生产关文档」这件事可被单测直接覆盖，而不必去 import app.main。
    """
    if is_production_env():
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


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


def _expected_heads() -> List[str]:
    """返回当前迁移树期望的 head revisions（自动从文件扫描，禁止手写）。"""
    return _discover_heads(_alembic_versions_dir())


def assert_production_schema_ok(engine: Engine) -> None:
    """生产环境 fail-fast 校验。"""
    if not is_production_env():
        return

    expected_heads = _expected_heads()
    if not expected_heads:
        raise ProductionSchemaError(
            "无法从 alembic/versions 发现任何 head revision，请检查迁移文件。"
        )

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

    if version not in expected_heads:
        raise ProductionSchemaError(
            f"Production alembic version {version!r} 不在已知 head 列表 {expected_heads} 中。"
            "请执行: alembic upgrade head"
        )

    logger.info(
        "Production schema OK: alembic head=%s (auto-discovered)",
        version,
    )


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

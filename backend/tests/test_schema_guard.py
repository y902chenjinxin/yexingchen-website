"""生产环境 schema 保护测试。

覆盖：
- 空数据库（含 alembic_version 不存在）→ 启动失败
- 未迁移数据库（alembic_version 存在但无 row）→ 启动失败
- 版本落后（alembic_version 指向旧 revision）→ 启动失败
- 版本与 head 一致 → 通过
- 非生产环境 → 不校验
- HEAD_REVISION 常量保持与迁移 head 一致
"""
import importlib
import os
import subprocess
import sys
import sqlite3
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
HEAD_REVISION = "b2c3d4e5f6a7"


def _make_db(tmp_path: Path) -> Path:
    return tmp_path / "schema_guard.db"


def _write_alembic_version(db_path: Path, value: str | None) -> None:
    """手工往 sqlite 文件写入 alembic_version 表，便于模拟生产场景。"""
    c = sqlite3.connect(str(db_path))
    c.execute(
        "CREATE TABLE IF NOT EXISTS alembic_version "
        "(version_num VARCHAR(32) NOT NULL)"
    )
    c.execute("DELETE FROM alembic_version")
    if value is not None:
        c.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (value,))
    c.commit()
    c.close()


def _import_schema_guard():
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from app.services import schema_guard  # noqa: E402

    return importlib.reload(schema_guard)


def test_empty_db_fails_in_production(tmp_path):
    db = _make_db(tmp_path)
    # 不创建 alembic_version 表，模拟空库
    guard = _import_schema_guard()
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{db}")
    with pytest.raises(guard.ProductionSchemaError):
        guard.check_schema_for_env(engine, env="production")
    engine.dispose()


def test_versionless_alembic_version_fails_in_production(tmp_path):
    db = _make_db(tmp_path)
    _write_alembic_version(db, None)
    guard = _import_schema_guard()
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{db}")
    with pytest.raises(guard.ProductionSchemaError):
        guard.check_schema_for_env(engine, env="production")
    engine.dispose()


def test_version_mismatch_fails_in_production(tmp_path):
    db = _make_db(tmp_path)
    _write_alembic_version(db, "old_rev")
    guard = _import_schema_guard()
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{db}")
    with pytest.raises(guard.ProductionSchemaError):
        guard.check_schema_for_env(engine, env="production")
    engine.dispose()


def test_matching_head_passes_in_production(tmp_path):
    db = _make_db(tmp_path)
    _write_alembic_version(db, HEAD_REVISION)
    guard = _import_schema_guard()
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{db}")
    # 不应抛
    guard.check_schema_for_env(engine, env="production")
    engine.dispose()


def test_non_production_skips_check(tmp_path):
    db = _make_db(tmp_path)
    # 即便 alembic_version 不存在，development 也不应抛
    guard = _import_schema_guard()
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{db}")
    for env in ("development", "staging", "test", "", "PROD"):
        # 仅 production 触发
        guard.check_schema_for_env(engine, env=env)


def test_head_revision_constant_matches_alembic_head():
    """HEAD_REVISION 必须与 alembic/versions 下实际 head 一致。"""
    versions_dir = BACKEND_DIR / "alembic" / "versions"
    rev_files = list(versions_dir.glob("*.py"))
    assert rev_files, "no alembic migration file found"
    heads = set()
    for f in rev_files:
        text = f.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("revision:"):
                # 形如: revision: str = 'abc123'
                after = line.split(":", 1)[1]
                # 取第一个引号包裹的字符串
                import re
                m = re.search(r"""['"]([0-9a-fA-F]+)['"]""", after)
                if m:
                    heads.add(m.group(1))
    assert heads, "no revision id parsed"
    from app.services import schema_guard

    assert schema_guard.HEAD_REVISION in heads, (
        f"schema_guard.HEAD_REVISION={schema_guard.HEAD_REVISION!r} not in {heads}"
    )


def test_production_env_case_insensitive(monkeypatch):
    guard = _import_schema_guard()
    monkeypatch.setenv("ENV", "production")
    assert guard.is_production_env() is True
    monkeypatch.setenv("ENV", "PRODUCTION")
    assert guard.is_production_env() is True
    monkeypatch.setenv("ENV", "Production")
    assert guard.is_production_env() is True
    monkeypatch.setenv("ENV", "dev")
    assert guard.is_production_env() is False
    monkeypatch.delenv("ENV", raising=False)
    assert guard.is_production_env() is False

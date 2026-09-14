"""生产环境 schema 保护测试。

覆盖：
- 空数据库（含 alembic_version 不存在）→ 启动失败
- 未迁移数据库（alembic_version 存在但无 row）→ 启动失败
- 版本落后（alembic_version 指向旧 revision）→ 启动失败
- 版本与 head 一致 → 通过
- 非生产环境 → 不校验
- HEAD 自动扫描：从 alembic/versions 文件中识别 head revision
"""
import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
from app.services import schema_guard as _schema_guard  # noqa: E402


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
    return importlib.reload(_schema_guard)


def _current_head() -> str:
    """从 alembic/versions 动态识别第一个 head（用于测试断言）。"""
    return _schema_guard._expected_heads()[0]


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
    _write_alembic_version(db, "old_rev_definitely_not_existing")
    guard = _import_schema_guard()
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{db}")
    with pytest.raises(guard.ProductionSchemaError):
        guard.check_schema_for_env(engine, env="production")
    engine.dispose()


def test_matching_head_passes_in_production(tmp_path):
    db = _make_db(tmp_path)
    _write_alembic_version(db, _current_head())
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


def test_discover_heads_finds_alembic_heads():
    """_discover_heads 必须能从 alembic/versions 下识别真正的 head revision。"""
    versions_dir = BACKEND_DIR / "alembic" / "versions"
    rev_files = list(versions_dir.glob("*.py"))
    assert rev_files, "no alembic migration file found"

    # 直接解析每个文件的 revision + down_revision
    revs: dict[str, str | None] = {}
    for f in rev_files:
        text = f.read_text(encoding="utf-8")
        rev = down = None
        for line in text.splitlines():
            line = line.strip()
            if (line.startswith("revision ") or line.startswith("revision:")) and "=" in line:
                rev = _schema_guard._parse_value(line.split("=", 1)[1])
            elif (line.startswith("down_revision ") or line.startswith("down_revision:")) and "=" in line:
                down = _schema_guard._parse_value(line.split("=", 1)[1])
        if rev:
            revs[rev] = down
    referenced = {v for v in revs.values() if v}
    expected_heads = sorted(r for r in revs if r not in referenced)

    discovered = _schema_guard._discover_heads(versions_dir)
    assert discovered == expected_heads
    assert discovered, "no head discovered"


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

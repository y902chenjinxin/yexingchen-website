"""数据库迁移测试

覆盖：
1. 全新数据库：alembic upgrade head 后存在全部 9 张业务表 + alembic_version。
2. 幂等性：再次 upgrade head 不会破坏已有数据。
3. 老环境接管：先用 Base.metadata.create_all 创建表，再 alembic stamp head
   不会丢失已存在的表。

测试使用临时 SQLite 文件；不依赖外部数据库。

注意：app.database.engine 是在 app.database 模块加载时基于环境变量
绑定的，而 conftest.py 已经把 SECRET_KEY / DATABASE_URL 指向 ./test.db。
为避免不同测试间互相干扰，本测试使用独立的临时引擎连接到临时数据库。
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _run_alembic(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )


EXPECTED_TABLES = {
    "alembic_version",
    "global_settings",
    "login_attempts",
    "music",
    "novels",
    "operation_logs",
    "tools",
    "users",
    "verification_codes",
    "videos",
    "xuanhuang_ai_conversations",
    "xuanhuang_ai_messages",
    "xuanhuang_asset_tags",
    "xuanhuang_assets",
    "xuanhuang_logs",
    "xuanhuang_note_assets",
    "xuanhuang_note_tags",
    "xuanhuang_notes",
    "xuanhuang_tags",
    "xuanhuang_task_links",
    "xuanhuang_tasks",
    "xuanhuang_ai_conversation_links",
}


@pytest.fixture
def temp_db_env(tmp_path):
    """返回临时数据库路径与运行 alembic 子进程所需的 env。"""
    db_path = tmp_path / "migration_test.db"
    env = os.environ.copy()
    env["SECRET_KEY"] = "test-secret-for-migrations"
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    return db_path, env


def _list_tables(db_path: Path) -> set:
    c = sqlite3.connect(str(db_path))
    rows = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    c.close()
    return {r[0] for r in rows}


def _ensure_backend_path():
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))


def _make_fresh_engine(db_path: Path):
    """创建一个独立的 SQLAlchemy engine，绑定到临时数据库。

    这样不依赖 app.database 已加载的 engine，避免与 conftest.py 中
    的 test.db 互相干扰。
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    ), sessionmaker(bind=None)


def test_alembic_upgrade_creates_all_tables(temp_db_env):
    db_path, env = temp_db_env
    r = _run_alembic(env, "upgrade", "head")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _list_tables(db_path) == EXPECTED_TABLES


def test_alembic_upgrade_is_idempotent(temp_db_env):
    """重复执行 upgrade head 不应破坏现有数据。"""
    db_path, env = temp_db_env
    r = _run_alembic(env, "upgrade", "head")
    assert r.returncode == 0, r.stdout + r.stderr

    # 通过独立引擎插入数据，避免污染 conftest 中的 test.db
    engine, Session = _make_fresh_engine(db_path)
    _ensure_backend_path()
    # pylint: disable=import-outside-toplevel
    from app.models.user import User

    session = Session(bind=engine)
    session.add(
        User(
            email="idem@test.local",
            password_hash="x",
            role="user",
            status="approved",
        )
    )
    session.commit()
    session.close()

    # 再执行一次 upgrade head，幂等
    r = _run_alembic(env, "upgrade", "head")
    assert r.returncode == 0, r.stdout + r.stderr

    c = sqlite3.connect(str(db_path))
    count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    c.close()
    assert count == 1
    engine.dispose()


def test_legacy_database_can_be_stamped(temp_db_env):
    """模拟老环境：先用 Base.metadata.create_all 建表，再 alembic stamp head 接管。"""
    db_path, env = temp_db_env

    engine, _ = _make_fresh_engine(db_path)
    _ensure_backend_path()
    # pylint: disable=import-outside-toplevel
    from app.database import Base
    from app.models.login_attempt import LoginAttempt  # noqa: F401
    from app.models.user import (  # noqa: F401
        GlobalSetting,
        Music,
        Novel,
        OperationLog,
        Tool,
        User,
        VerificationCode,
        Video,
    )

    Base.metadata.create_all(engine)

    legacy_tables = _list_tables(db_path)
    assert "alembic_version" not in legacy_tables

    # 执行 stamp head：标记为已应用 baseline，但不动现有表
    r = _run_alembic(env, "stamp", "head")
    assert r.returncode == 0, r.stdout + r.stderr

    tables_after_stamp = _list_tables(db_path)
    # 原有 9 张业务表必须保留
    assert legacy_tables <= tables_after_stamp
    # alembic_version 表被加上
    assert "alembic_version" in tables_after_stamp

    # stamp 后再执行 upgrade head 也应该是 no-op
    r = _run_alembic(env, "upgrade", "head")
    assert r.returncode == 0, r.stdout + r.stderr
    engine.dispose()

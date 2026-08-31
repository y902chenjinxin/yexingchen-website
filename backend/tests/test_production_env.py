"""生产环境 schema 边界测试。

验证：
1. ENV=production 时，导入 app.main 不会触发 Base.metadata.create_all()。
2. 非生产环境（development / 未设置 / 其他值）导入 app.main 时，
   仍然会调用 Base.metadata.create_all()，保持向后兼容。

测试通过 subprocess 启动独立 Python 进程，并 monkey-patch
Base.metadata.create_all 来记录调用次数，避免污染当前测试进程的数据库。
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent


SCRIPT_TEMPLATE = textwrap.dedent(
    """
    import os
    import sys
    import tempfile

    sys.path.insert(0, {backend_dir!r})

    # 用临时 sqlite 文件作为目标库
    tmpdir = tempfile.mkdtemp(prefix='prod_env_')
    db_path = os.path.join(tmpdir, 'empty.db')
    open(db_path, 'wb').close()
    os.environ['SECRET_KEY'] = 'test-secret'
    os.environ['DATABASE_URL'] = 'sqlite:///' + db_path

    # 旁路 schema_guard（测试目标是 create_all 是否被调用，不是 guard 行为）
    import app.services.schema_guard as sg
    sg.assert_production_schema_ok = lambda engine: None

    from app.database import Base

    # 记录 create_all 是否被调用
    called = {{'count': 0}}

    real_create_all = Base.metadata.create_all

    def patched_create_all(*args, **kwargs):
        called['count'] += 1
        return None

    Base.metadata.create_all = patched_create_all

    try:
        import app.main  # noqa: F401
    finally:
        Base.metadata.create_all = real_create_all

    print('CREATE_ALL_CALLED=' + str(called['count']))
    """
)


def _run_in_child(env_value):
    """在独立 Python 进程中以指定 ENV 导入 app.main，记录 create_all 调用次数。

    旁路 schema_guard，仅验证 create_all 调用次数（schema_guard 行为由
    test_schema_guard.py 单独覆盖）。
    """
    env = os.environ.copy()
    env["SECRET_KEY"] = "test-secret"
    env.pop("DATABASE_URL", None)
    if env_value is None:
        env.pop("ENV", None)
    else:
        env["ENV"] = env_value

    script = SCRIPT_TEMPLATE.format(backend_dir=str(BACKEND_DIR))
    r = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, (
        f"child process failed (ENV={env_value!r})\n"
        f"stdout={r.stdout}\nstderr={r.stderr}"
    )
    last_line = r.stdout.strip().splitlines()[-1]
    assert last_line.startswith("CREATE_ALL_CALLED="), last_line
    return int(last_line.split("=", 1)[1])


@pytest.mark.parametrize("env_value", ["production", "PRODUCTION", "Production"])
def test_production_env_skips_create_all(env_value):
    """ENV=production（任意大小写）必须跳过 Base.metadata.create_all()。"""
    count = _run_in_child(env_value)
    assert count == 0, f"ENV={env_value!r} 不应调用 create_all，实际调用 {count} 次"


@pytest.mark.parametrize("env_value", ["development", "staging", "test", ""])
def test_non_production_env_still_calls_create_all(env_value):
    """非生产环境必须保留 create_all，向后兼容历史部署与现有 test_api.py。"""
    count = _run_in_child(env_value)
    assert count == 1, f"ENV={env_value!r} 应调用 create_all 1 次，实际 {count} 次"


def test_env_unset_still_calls_create_all():
    """未设置 ENV 时按非生产处理。"""
    count = _run_in_child(None)
    assert count == 1, f"未设置 ENV 应调用 create_all 1 次，实际 {count} 次"

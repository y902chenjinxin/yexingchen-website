"""生产环境判定与文档路由暴露的回归测试。

背景（2026-09-16 生产实测发现）：`is_production_env()` 原来只读 `os.environ["ENV"]`，
而 `ENV=production` 只写在 `backend/.env` 里（pydantic-settings 只把它读进 Settings，
不写回 os.environ）。结果 pm2 用别的方式重启一次，判定就翻成「非生产」，
于是 `/docs`、`/redoc`、`/openapi.json` **在生产上变成公开可访问**（实测三者均 200）。

本测试锁住两件事：
1. 判定要同时认「真实环境变量」和「.env 里的 ENV」，且环境变量优先
2. 生产环境下三个文档路由必须一起关（只关 docs_url 不够）
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest

from app.services import schema_guard


@pytest.fixture(autouse=True)
def _restore_env():
    """本文件会改动 ENV，逐例还原，避免污染其他测试。"""
    saved = os.environ.get("ENV")
    yield
    if saved is None:
        os.environ.pop("ENV", None)
    else:
        os.environ["ENV"] = saved


class TestResolvedEnv:
    def test_reads_real_env_var(self):
        os.environ["ENV"] = "production"
        assert schema_guard.resolved_env() == "production"
        assert schema_guard.is_production_env() is True

    def test_falls_back_to_settings_when_env_var_absent(self, monkeypatch):
        """回归重点：pm2 重启丢掉环境变量时，必须还能从 .env 读到 production。"""
        os.environ.pop("ENV", None)
        from app.config import settings

        monkeypatch.setattr(settings, "ENV", "production", raising=False)
        assert schema_guard.resolved_env() == "production"
        assert schema_guard.is_production_env() is True

    def test_real_env_var_wins_over_settings(self, monkeypatch):
        from app.config import settings

        os.environ["ENV"] = "development"
        monkeypatch.setattr(settings, "ENV", "production", raising=False)
        assert schema_guard.is_production_env() is False

    def test_settings_fallback_is_case_insensitive(self, monkeypatch):
        os.environ.pop("ENV", None)
        from app.config import settings

        monkeypatch.setattr(settings, "ENV", "  Production  ", raising=False)
        assert schema_guard.is_production_env() is True

    @pytest.mark.parametrize("value", ["development", "test", "", "staging"])
    def test_non_production_values(self, value, monkeypatch):
        from app.config import settings

        os.environ["ENV"] = value
        monkeypatch.setattr(settings, "ENV", value, raising=False)
        assert schema_guard.is_production_env() is False


class TestDocsUrls:
    def test_production_disables_all_three(self):
        os.environ["ENV"] = "production"
        urls = schema_guard.docs_urls()
        assert urls == {"docs_url": None, "redoc_url": None, "openapi_url": None}

    def test_non_production_keeps_docs(self):
        os.environ["ENV"] = "development"
        urls = schema_guard.docs_urls()
        assert urls["docs_url"] == "/docs"
        assert urls["redoc_url"] == "/redoc"
        # openapi_url 必须一起暴露，否则 /docs 页面拿不到 schema 会白屏
        assert urls["openapi_url"] == "/openapi.json"

    def test_openapi_disabled_whenever_docs_disabled(self):
        """防回归：任何情况下都不允许出现「docs 关了但 openapi.json 还开着」。"""
        for value in ("production", "Production", "development", "test"):
            os.environ["ENV"] = value
            urls = schema_guard.docs_urls()
            assert (urls["docs_url"] is None) == (urls["openapi_url"] is None)


class TestSettingsDeclaresEnv:
    def test_env_is_a_declared_field(self):
        """必须显式声明：靠 extra='allow' 兜着的值不会写回 os.environ。"""
        from app.config import Settings

        assert "ENV" in Settings.model_fields

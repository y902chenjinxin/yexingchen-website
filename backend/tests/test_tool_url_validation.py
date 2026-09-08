"""# 工具 URL 校验测试
"""
import os
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SMTP_USER", "test@x.com")

import pytest
from pydantic import ValidationError

from app.schemas.common import ToolCreate, ToolUpdate


class TestToolCreateURL:
    """ToolCreate.url 校验。"""

    def test_https_url_passes(self):
        t = ToolCreate(title="Figma", url="https://www.figma.com", description="", icon="")
        assert str(t.url).startswith("https://")

    def test_http_url_passes(self):
        t = ToolCreate(title="X", url="http://example.com", description="", icon="")
        assert str(t.url).startswith("http://")

    def test_relative_path_builtin_tool_passes(self):
        """内置工具使用相对路径（如 /tool/watermark），应允许。"""
        t = ToolCreate(title="watermark", url="/tool/watermark", description="", icon="")
        assert t.url == "/tool/watermark"

    def test_javascript_scheme_rejected(self):
        """javascript: 等危险 scheme 必须拒绝。"""
        with pytest.raises(ValidationError) as exc:
            ToolCreate(title="X", url="javascript:alert(1)", description="", icon="")
        assert "URL" in str(exc.value) or "http" in str(exc.value).lower()

    def test_file_scheme_rejected(self):
        """file:// 也必须拒绝。"""
        with pytest.raises(ValidationError):
            ToolCreate(title="X", url="file:///etc/passwd", description="", icon="")

    def test_garbage_string_rejected(self):
        """纯字符串拒绝。"""
        with pytest.raises(ValidationError):
            ToolCreate(title="X", url="not a url", description="", icon="")

    def test_empty_string_rejected(self):
        """空字符串拒绝。"""
        with pytest.raises(ValidationError):
            ToolCreate(title="X", url="", description="", icon="")

    def test_relative_path_with_double_slash_rejected(self):
        """/a//b 形式拒绝（防止 // 注入）。"""
        with pytest.raises(ValidationError):
            ToolCreate(title="X", url="/tool//watermark", description="", icon="")


class TestToolUpdateURL:
    """ToolUpdate.url 校验（仅在提供 url 时）。"""

    def test_none_url_passes(self):
        t = ToolUpdate()
        assert t.url is None

    def test_https_url_passes(self):
        t = ToolUpdate(url="https://example.com")
        assert str(t.url).startswith("https://")

    def test_relative_path_passes(self):
        t = ToolUpdate(url="/tool/watermark")
        assert t.url == "/tool/watermark"

    def test_javascript_scheme_rejected(self):
        with pytest.raises(ValidationError):
            ToolUpdate(url="javascript:alert(1)")

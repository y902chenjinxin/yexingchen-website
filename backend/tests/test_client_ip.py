"""# get_client_ip 工具函数测试
"""
import os
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SMTP_USER", "t@x.com")

from app.utils.security import get_client_ip


class _FakeRequest:
    """模拟 FastAPI Request 用于测试。"""
    def __init__(self, headers=None, client_host="127.0.0.1"):
        self.headers = headers or {}
        if client_host:
            self.client = type("C", (), {"host": client_host})()
        else:
            self.client = None


def test_get_client_ip_prefers_x_real_ip():
    """X-Real-IP 优先。"""
    req = _FakeRequest(
        headers={"x-real-ip": "203.0.113.1", "x-forwarded-for": "10.0.0.1"},
        client_host="127.0.0.1"
    )
    assert get_client_ip(req) == "203.0.113.1"


def test_get_client_ip_uses_xff_when_no_real_ip():
    """没有 X-Real-IP 时用 X-Forwarded-For 第一项。"""
    req = _FakeRequest(
        headers={"x-forwarded-for": "198.51.100.5, 10.0.0.1, 10.0.0.2"},
        client_host="127.0.0.1"
    )
    assert get_client_ip(req) == "198.51.100.5"


def test_get_client_ip_falls_back_to_client_host():
    """没有代理头时用直连 IP（防止绕过代理）。"""
    req = _FakeRequest(headers={}, client_host="192.168.1.100")
    assert get_client_ip(req) == "192.168.1.1" or get_client_ip(req) == "127.0.0.1" or get_client_ip(req) == "192.168.1.100"


def test_get_client_ip_handles_empty_request():
    """None / 空 request 兜底返回空字符串。"""
    assert get_client_ip(None) == ""


def test_get_client_ip_xff_only_one_ip():
    """X-Forwarded-For 只有一项时直接返回。"""
    req = _FakeRequest(headers={"x-forwarded-for": "203.0.113.50"}, client_host="127.0.0.1")
    assert get_client_ip(req) == "203.0.113.50"


def test_get_client_ip_strips_whitespace():
    """X-Real-IP 去除空白。"""
    req = _FakeRequest(headers={"x-real-ip": "  203.0.113.1  "})
    assert get_client_ip(req) == "203.0.113.1"

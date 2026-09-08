"""# 密码强度校验测试
"""
import os
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from pydantic import ValidationError

from app.schemas.common import VerifyRequest, UserCreateRequest


class TestVerifyRequestPassword:
    """VerifyRequest 密码强度校验。"""

    def test_strong_password_passes(self):
        r = VerifyRequest(email="u@x.com", code="AB12", password="Strong1Pass")
        assert r.password == "Strong1Pass"

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError) as exc:
            VerifyRequest(email="u@x.com", code="AB12", password="Ab1")
        assert "8" in str(exc.value) or "密码" in str(exc.value)

    def test_no_uppercase_rejected(self):
        with pytest.raises(ValidationError) as exc:
            VerifyRequest(email="u@x.com", code="AB12", password="weak1pass")
        assert "大写" in str(exc.value) or "upper" in str(exc.value).lower()

    def test_no_lowercase_rejected(self):
        with pytest.raises(ValidationError) as exc:
            VerifyRequest(email="u@x.com", code="AB12", password="WEAK1PASS")
        assert "小写" in str(exc.value) or "lower" in str(exc.value).lower()

    def test_no_digit_rejected(self):
        with pytest.raises(ValidationError) as exc:
            VerifyRequest(email="u@x.com", code="AB12", password="OnlyLetters")
        assert "数字" in str(exc.value) or "digit" in str(exc.value).lower()


class TestUserCreateRequestPassword:
    """UserCreateRequest 密码强度校验。"""

    def test_strong_password_passes(self):
        r = UserCreateRequest(email="admin@x.com", password="Admin1Pass")
        assert r.password == "Admin1Pass"

    def test_weak_password_rejected(self):
        with pytest.raises(ValidationError):
            UserCreateRequest(email="admin@x.com", password="123")

    def test_password_without_uppercase_rejected(self):
        with pytest.raises(ValidationError):
            UserCreateRequest(email="admin@x.com", password="weak1password")

    def test_password_without_digit_rejected(self):
        with pytest.raises(ValidationError):
            UserCreateRequest(email="admin@x.com", password="OnlyLetters")


def test_existing_strong_password_works():
    """现有用户密码（Chen@12345678）应仍能通过 validator（如有改动密码流程）。"""
    r = UserCreateRequest(email="admin@yexingchen.cn", password="Chen@12345678")
    assert r.password == "Chen@12345678"

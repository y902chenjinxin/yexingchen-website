"""# 密码强度校验测试

⚠️ 2026-09-16 语义变更（v2.19.0）
------------------------------------------------
原先 `UserCreateRequest` 在 pydantic 层强制「邮箱格式 + 密码强度」，导致超管给家里人
开号时被面向公网的自主注册规则拦住（如账号「爸爸」、密码「123456」）。

现策略：
- **超管建号（`POST /api/admin/users`）默认不校验**格式与强度，只挡空值；
  请求体置 `strict_validation=True` 可按次启用公开注册同款规则。
- 校验逻辑从 pydantic 下移到 `app.routers.admin_users._check_credentials`。
- **公开注册口保持不变**（`RegisterRequest` 强制邮箱、`VerifyRequest` 强制密码强度）——
  这正是 `TestVerifyRequestPassword` 仍然断言「必须拒绝弱密码」的原因。
- **登录口 `LoginRequest` 不再校验邮箱格式**，否则超管创建的非邮箱账号建了也登不进去。
"""
import os
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers.admin_users import _check_credentials
from app.schemas.common import LoginRequest, UserCreateRequest, VerifyRequest


class TestVerifyRequestPassword:
    """公开注册（VerifyRequest）密码强度校验 —— 面向公网，规则不变。"""

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


class TestUserCreateRequestAdminBypass:
    """超管建号请求体：pydantic 层不再拦，校验交由路由层按开关决定。"""

    def test_weak_password_accepted_by_schema(self):
        assert UserCreateRequest(email="admin@x.com", password="123").password == "123"

    def test_non_email_account_accepted_by_schema(self):
        assert UserCreateRequest(email="爸爸", password="123456").email == "爸爸"

    def test_phone_account_accepted_by_schema(self):
        assert UserCreateRequest(email="13800138000", password="1").email == "13800138000"

    def test_strict_validation_defaults_off(self):
        req = UserCreateRequest(email="a@b.cn", password="Abcd1234")
        assert req.strict_validation is False


class TestAdminCredentialCheck:
    """路由层 _check_credentials：默认只挡空值，strict=True 时套用公开注册规则。"""

    def test_default_skips_format_and_strength(self):
        assert _check_credentials("爸爸", "123456", False) == "爸爸"

    def test_default_skips_strength_even_for_email(self):
        assert _check_credentials("kid@x.com", "1", False) == "kid@x.com"

    def test_account_is_stripped(self):
        assert _check_credentials("  爸爸  ", "123456", False) == "爸爸"

    @pytest.mark.parametrize(
        "email,password",
        [("", "123456"), ("   ", "123456"), ("爸爸", ""), ("爸爸", "   ")],
    )
    def test_empty_credentials_rejected(self, email, password):
        with pytest.raises(HTTPException) as exc:
            _check_credentials(email, password, False)
        assert exc.value.status_code == 400

    def test_strict_rejects_non_email(self):
        with pytest.raises(HTTPException) as exc:
            _check_credentials("爸爸", "123456", True)
        assert "邮箱格式" in exc.value.detail["msg"]

    def test_strict_rejects_weak_password(self):
        with pytest.raises(HTTPException) as exc:
            _check_credentials("kid@x.com", "123456", True)
        assert exc.value.status_code == 400

    def test_strict_accepts_valid_email_and_password(self):
        assert _check_credentials("kid@x.com", "Kid2024pass", True) == "kid@x.com"


class TestLoginRequestAcceptsNonEmail:
    """登录口必须接受非邮箱账号，否则超管建的账号无法登录。"""

    def test_non_email_login_passes(self):
        assert LoginRequest(email="爸爸", password="123456").email == "爸爸"

    def test_phone_login_passes(self):
        assert LoginRequest(email="13800138000", password="x").email == "13800138000"

    def test_login_account_is_stripped(self):
        assert LoginRequest(email="  爸爸  ", password="x").email == "爸爸"

    def test_empty_login_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="", password="x")

    def test_overlong_login_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="a" * 300, password="x")


def test_existing_strong_password_works():
    """现有用户密码（Chen@12345678）应仍能通过 validator（如有改动密码流程）。"""
    r = UserCreateRequest(email="admin@yexingchen.cn", password="Chen@12345678")
    assert r.password == "Chen@12345678"

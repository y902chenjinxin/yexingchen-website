"""security.py 单元测试 - 不依赖 DB。

覆盖：
- 密码哈希/验证（pbkdf2 现行格式 + sha256 旧格式回退）
- JWT Token 创建/解码/失败
- require_super_admin 逻辑（admin/super_admin/普通 user）
"""
import os

# 测试前设置必需的环境变量（必须在 import app 之前）
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-security-tests")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_DAYS", "7")

import hashlib
import pytest
from fastapi import HTTPException

from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    require_super_admin,
)


# ---------- 密码哈希 ----------

def test_password_hash_uses_pbkdf2_format():
    """新生成的哈希必须是 pbkdf2-sha256 格式"""
    h = get_password_hash("MySecretPassword123")
    assert h.startswith("$pbkdf2-sha256$")
    # pbkdf2-sha256$<rounds>$<salt>$<hash>，按 $ 切分至少 5 段
    assert len(h.split("$")) >= 5


def test_password_hash_verifies_correct_plaintext():
    """正确明文验证通过"""
    plain = "MySecretPassword123"
    h = get_password_hash(plain)
    assert verify_password(plain, h) is True


def test_password_hash_rejects_wrong_plaintext():
    """错误明文验证失败"""
    h = get_password_hash("MySecretPassword123")
    assert verify_password("wrong-password", h) is False
    assert verify_password("", h) is False
    assert verify_password("MySecretPassword124", h) is False


def test_password_verify_old_sha256_hex_format_still_works():
    """旧版 sha256 hex 哈希仍可验证（向后兼容）"""
    plain = "legacy-pass"
    old_hash = hashlib.sha256(plain.encode()).hexdigest()
    # 不以 $pbkdf2-sha256$ 开头，走 sha256 fallback 分支
    assert not old_hash.startswith("$")
    assert verify_password(plain, old_hash) is True


def test_password_verify_old_sha256_rejects_wrong_plaintext():
    """旧版 sha256 哈希对错误明文返回 False"""
    old_hash = hashlib.sha256(b"legacy-pass").hexdigest()
    assert verify_password("wrong", old_hash) is False


def test_password_hash_is_salted_and_unique():
    """两次哈希同一明文得到不同结果（salt 唯一）"""
    h1 = get_password_hash("same-password")
    h2 = get_password_hash("same-password")
    assert h1 != h2
    # 两个都能验证通过
    assert verify_password("same-password", h1)
    assert verify_password("same-password", h2)


# ---------- JWT Token ----------

def test_create_access_token_returns_string():
    """create_access_token 返回字符串"""
    token = create_access_token({"user_id": 1, "role": "user"})
    assert isinstance(token, str)
    assert len(token) > 20  # JWT 至少几十字符


def test_decode_token_returns_payload():
    """decode_token 能正确解码刚创建的 token"""
    token = create_access_token({"user_id": 42, "role": "admin"})
    payload = decode_token(token)
    assert payload["user_id"] == 42
    assert payload["role"] == "admin"
    assert "exp" in payload  # 必须有过期时间


def test_decode_token_rejects_garbage_string():
    """decode_token 对非法字符串抛 401"""
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-valid-jwt-at-all")
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_tampered_signature():
    """decode_token 对被篡改签名的 token 抛 401"""
    valid = create_access_token({"user_id": 1})
    # 把签名段最后两位改了
    head, payload, sig = valid.split(".")
    tampered = f"{head}.{payload}.{sig[:-2]}AA"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_empty_string():
    """空字符串 token 抛 401"""
    with pytest.raises(HTTPException) as exc_info:
        decode_token("")
    assert exc_info.value.status_code == 401


def test_token_payload_preserves_extra_claims():
    """extra claims 应该保留在 payload 里"""
    token = create_access_token({"user_id": 7, "role": "user", "is_super_admin": 1})
    payload = decode_token(token)
    assert payload["user_id"] == 7
    assert payload["is_super_admin"] == 1


# ---------- require_super_admin ----------

def test_require_super_admin_accepts_is_super_admin_flag():
    """is_super_admin=1 的用户通过"""
    user = {"user_id": 1, "role": "user", "is_super_admin": 1}
    result = require_super_admin(current_user=user)
    assert result["user_id"] == 1


def test_require_super_admin_accepts_admin_role():
    """role=admin 通过"""
    user = {"user_id": 2, "role": "admin", "is_super_admin": 0}
    result = require_super_admin(current_user=user)
    assert result["user_id"] == 2


def test_require_super_admin_accepts_super_admin_role():
    """role=super_admin 通过"""
    user = {"user_id": 3, "role": "super_admin", "is_super_admin": 0}
    result = require_super_admin(current_user=user)
    assert result["user_id"] == 3


def test_require_super_admin_rejects_normal_user():
    """普通 user 被拒"""
    user = {"user_id": 4, "role": "user", "is_super_admin": 0}
    with pytest.raises(HTTPException) as exc_info:
        require_super_admin(current_user=user)
    assert exc_info.value.status_code == 403


def test_require_super_admin_rejects_empty_user():
    """空用户信息被拒"""
    with pytest.raises(HTTPException) as exc_info:
        require_super_admin(current_user={})
    assert exc_info.value.status_code == 403

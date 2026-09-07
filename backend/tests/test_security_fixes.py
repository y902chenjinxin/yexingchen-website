"""# Audit 修复测试 (2026-09-07)。

覆盖三类严重漏洞的修复：
1. novel/video/music 路由 IDOR 防护（uploader 检查）
2. tool 路由仅超管可操作
3. settings.bg_music/stream 路径穿越防护
"""
import inspect
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("UPLOAD_DIR", "./uploads")
os.environ.setdefault("ENV", "development")

import pytest
from fastapi import HTTPException

# 旁路 schema_guard
import app.services.schema_guard as sg
sg.assert_production_schema_ok = lambda engine: None

from app.utils.security import (
    get_password_hash,
    create_access_token,
    check_owner_or_admin,
    require_super_admin,
)


# ============================================================
# 单元测试：check_owner_or_admin
# ============================================================

def test_check_owner_allows_owner():
    """资源所有者可操作自己的资源。"""
    u = {"user_id": 1, "role": "user", "is_super_admin": 0}
    check_owner_or_admin(u, owner_id=1)


def test_check_owner_allows_super_admin():
    """超管可操作任何人的资源。"""
    u = {"user_id": 1, "role": "user", "is_super_admin": 1}
    check_owner_or_admin(u, owner_id=999)


def test_check_owner_rejects_other_user():
    """普通用户操作别人的资源抛 403。"""
    u = {"user_id": 1, "role": "user", "is_super_admin": 0}
    with pytest.raises(HTTPException) as exc:
        check_owner_or_admin(u, owner_id=999)
    assert exc.value.status_code == 403


def test_check_owner_admin_role_passes():
    """role=admin 的非超管用户也被允许（与超管等价）。"""
    u = {"user_id": 1, "role": "admin", "is_super_admin": 0}
    check_owner_or_admin(u, owner_id=999)


# ============================================================
# 单元测试：require_super_admin 直接调用
# ============================================================

def test_require_super_admin_rejects_normal_user():
    """普通用户被 require_super_admin 拒绝。"""
    u = {"user_id": 1, "role": "user", "is_super_admin": 0}
    with pytest.raises(HTTPException) as exc:
        require_super_admin(current_user=u)
    assert exc.value.status_code == 403


def test_require_super_admin_allows_super_admin():
    """超管被允许。"""
    u = {"user_id": 1, "role": "user", "is_super_admin": 1}
    assert require_super_admin(current_user=u) == u


def test_require_super_admin_allows_admin_role():
    """role=admin 被允许（即使 is_super_admin=0）。"""
    u = {"user_id": 1, "role": "admin", "is_super_admin": 0}
    assert require_super_admin(current_user=u) == u


# ============================================================
# 静态检查：tool 路由的写接口必须用 require_super_admin
# ============================================================

def test_tool_routes_use_require_super_admin():
    """tool.py 的 create/update/delete 必须用 require_super_admin（防止 IDOR）。"""
    from app.routers import tool as tool_module
    funcs = ["create_tool", "update_tool", "delete_tool"]
    for fname in funcs:
        f = getattr(tool_module, fname)
        src = inspect.getsource(f)
        assert "require_super_admin" in src, (
            f"tool.{fname} 未使用 require_super_admin，"
            f"会导致任何登录用户都能管理工具（安全漏洞）"
        )
        assert "get_current_user" not in src, (
            f"tool.{fname} 仍使用 get_current_user，"
            f"应改为 require_super_admin"
        )


# ============================================================
# 静态检查：novel/video/music 路由的 update/delete 必须有 owner check
# ============================================================

def test_novel_routes_have_owner_check():
    """novel.py 的 update/delete 必须调用 check_owner_or_admin。"""
    from app.routers import novel as novel_module
    for fname in ["update_novel", "delete_novel"]:
        f = getattr(novel_module, fname)
        src = inspect.getsource(f)
        assert "check_owner_or_admin" in src, (
            f"novel.{fname} 未调用 check_owner_or_admin，"
            f"会导致 A 用户修改/删除 B 的小说（IDOR）"
        )


def test_video_routes_have_owner_check():
    """video.py 的 update/delete 必须调用 check_owner_or_admin。"""
    from app.routers import video as video_module
    for fname in ["update_video", "delete_video"]:
        f = getattr(video_module, fname)
        src = inspect.getsource(f)
        assert "check_owner_or_admin" in src, (
            f"video.{fname} 未调用 check_owner_or_admin（IDOR）"
        )


def test_music_routes_have_owner_check():
    """music.py 的 update/delete 必须调用 check_owner_or_admin。"""
    from app.routers import music as music_module
    for fname in ["update_music", "delete_music"]:
        f = getattr(music_module, fname)
        src = inspect.getsource(f)
        assert "check_owner_or_admin" in src, (
            f"music.{fname} 未调用 check_owner_or_admin（IDOR）"
        )


# ============================================================
# 静态检查：settings.py 的 bg_music/stream 必须有路径校验
# ============================================================

def test_settings_bgm_stream_has_path_traversal_check():
    """settings.py 的 stream_bgm 必须有路径穿越防护。"""
    from app.routers import settings as settings_module
    src = inspect.getsource(settings_module.stream_bgm)
    # 必须包含路径穿越检查关键词
    assert "Path Traversal" in src or "路径穿越" in src, (
        "stream_bgm 缺少路径穿越防护注释/检查"
    )
    assert '".." in bgm_id' in src or "realpath" in src, (
        "stream_bgm 缺少路径校验代码"
    )

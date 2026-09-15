"""AI 封面生成：参数校验 + 渲染产出 + 预设枚举。

直调 async 路由（不走 TestClient）；渲染不依赖 db。
"""
import asyncio
import base64
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi import HTTPException

from app.routers.cover import CoverIn, presets, render_cover
from app.services.cover_render import SIZES, _resolve_font_file

USER = {"user_id": 1}


def call(coro):
    try:
        return 200, asyncio.run(coro)
    except HTTPException as e:
        return e.status_code, e.detail


def test_title_required_and_clamped():
    with pytest.raises(HTTPException):
        CoverIn(title="   ")
    assert CoverIn(title="a" * 100).title == "a" * 40  # 截断到 40 字
    assert CoverIn(title="标题", subtitle="x" * 100).subtitle == "x" * 60


def test_render_all_sizes_and_themes():
    for size in SIZES:
        status, res = call(render_cover(
            CoverIn(title="测试标题", subtitle="副标", size=size), USER))
        assert status == 200, res
        assert res.data["image"].startswith("data:image/png;base64,")
        # 解码后是真实 PNG（magic bytes）
        raw = base64.b64decode(res.data["image"].split(",", 1)[1])
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(raw) > 10_000  # 不可能是空白小图


def test_render_invalid_params_rejected():
    for bad in ("size", "layout", "theme"):
        kw = {"title": "t", bad: "no_such_key"}
        status, detail = call(render_cover(CoverIn(**kw), USER))
        assert status == 422 or status == 400, (bad, status, detail)


def test_render_matches_requested_aspect():
    status, res = call(render_cover(CoverIn(title="比例", size="wechat"), USER))
    import io
    from PIL import Image
    raw = base64.b64decode(res.data["image"].split(",", 1)[1])
    w, h = Image.open(io.BytesIO(raw)).size
    ew, eh = SIZES["wechat"]
    assert (w, h) == (ew, eh)


def test_presets_shape():
    status, res = call(presets(USER))
    assert status == 200
    d = res.data
    assert {s["key"] for s in d["sizes"]} == set(SIZES)
    assert {l["key"] for l in d["layouts"]} == {"center", "leftband", "seal"}
    assert {t["key"] for t in d["themes"]} == {"ink", "rain", "paper"}


def test_font_available():
    """渲染依赖自带中文字体；字体文件丢失时这里直接暴露，而不是等到线上出豆腐块。"""
    assert _resolve_font_file(), "assets/fonts/SmileySans-Oblique.ttf 缺失"

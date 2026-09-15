"""AI 封面生成：纯服务端 Pillow 模板渲染（不依赖任何外部 AI 接口）。

为什么不用文生图：封面 90% 的需求是「固定版式 + 自己的标题文案 + 统一视觉规范」，
文生图不可控（字号/措辞/比例都会漂），模板渲染反而一次到位、零成本、秒出图。

设计要点：
- 主题沿用站点「玄墨流金 / 雨青 / 宣纸」三套 token 配色，与全站视觉一致
- 中文字体自带（SmileySans 得意黑，OFL-1.1 可再分发）——生产服务器只有 dejavu，
  不带字体中文全是豆腐块；Windows/本地开发则优先探测系统字体做备选
- 标题超宽自动降字号，降到下限后逐字换行（中文没有空格，不能按词断）
- 装饰元素：内缩细线框 + 角部短线 + 胶片噪点 + 渐晕，全部用 PIL 原生实现
"""
from __future__ import annotations

import base64
import io
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- 尺寸 / 主题 / 版式

SIZES = {
    "wechat": (900, 383),     # 公众号首图 2.35:1
    "xhs": (1080, 1440),      # 小红书 3:4
    "video": (1280, 720),     # 视频封面 16:9
    "square": (1080, 1080),   # 方形 1:1
}

THEMES = {
    # bg 上/下渐变, 主字, 辅字, 点缀(朱砂/雨青), 线框
    "ink":   {"bg1": (18, 25, 34),    "bg2": (30, 40, 52),    "main": (216, 181, 115), "sub": (154, 168, 181), "accent": (217, 138, 118), "line": (216, 181, 115)},
    "rain":  {"bg1": (40, 62, 66),    "bg2": (58, 86, 90),    "main": (242, 237, 227), "sub": (198, 210, 208), "accent": (127, 168, 163), "line": (242, 237, 227)},
    "paper": {"bg1": (240, 233, 220), "bg2": (228, 218, 200), "main": (42, 47, 56),    "sub": (107, 114, 128), "accent": (194, 84, 80),   "line": (42, 47, 56)},
}

LAYOUTS = ("center", "leftband", "seal")

# 标题字号基准（按画布短边比例缩放），下限保证可读
_TITLE_RATIO = 0.115
_TITLE_MIN = 28
_TITLE_MAX = 96


# ---------------------------------------------------------------- 字体

_FONT_CANDIDATES = (
    # 自带字体（生产服务器唯一可靠来源）
    "fonts/SmileySans-Oblique.ttf",
    # 本地开发备选：Windows / 常见 Linux
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)

_font_file_cache: str | None = None


def _resolve_font_file() -> str | None:
    global _font_file_cache
    if _font_file_cache is not None:
        return _font_file_cache or None
    import os

    hit = None
    for p in _FONT_CANDIDATES:
        # 自带字体相对 backend/app/assets/ 解析
        if not os.path.isabs(p):
            here = os.path.dirname(os.path.abspath(__file__))
            p = os.path.normpath(os.path.join(here, "..", "assets", p))
        if os.path.exists(p):
            hit = p
            break
    _font_file_cache = hit or ""
    return hit


@lru_cache(maxsize=16)
def _font(size: int) -> ImageFont.FreeTypeFont | None:
    path = _resolve_font_file()
    if not path:
        return None
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return None


# ---------------------------------------------------------------- 基础绘制件


def _linear_bg(w: int, h: int, c1: tuple, c2: tuple) -> Image.Image:
    """垂直线性渐变底。"""
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        base.putpixel((0, y), tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return base.resize((w, h))


def _grain(img: Image.Image, amount: float = 14.0, alpha: int = 18) -> None:
    """胶片颗粒：PIL 原生 effect_noise（灰度），转低透明度叠加层，无 numpy 依赖。"""
    noise = Image.effect_noise(img.size, amount)  # L 模式
    # 噪声亮度直方整体拉到中灰附近 → 用作 alpha，亮处叠灰、暗处透底
    alpha_mask = noise.point(lambda v: int(abs(v - 128) * (alpha / 128.0)))
    overlay = Image.new("RGB", img.size, (110, 110, 110))
    img.paste(overlay, (0, 0), alpha_mask)


def _vignette(img: Image.Image, strength: float = 0.35) -> None:
    """四角渐晕：径向 mask + 叠暗。"""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-w * 0.25, -h * 0.25, w * 1.25, h * 1.25), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(min(w, h) // 6))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    img.paste(dark, (0, 0), mask.point(lambda v: int((255 - v) * strength)))


def _frame(d: ImageDraw.ImageDraw, w: int, h: int, color: tuple, inset: int = 26, width: int = 2) -> None:
    """内缩细线框 + 四角加粗短线（中式装裱意象）。"""
    d.rectangle([inset, inset, w - inset, h - inset], outline=color + (110,), width=width)
    L = 26
    for (x, y, dx, dy) in (
        (inset, inset, 1, 1), (w - inset, inset, -1, 1),
        (inset, h - inset, 1, -1), (w - inset, h - inset, -1, -1),
    ):
        d.line([(x, y), (x + dx * L, y)], fill=color + (200,), width=max(3, width + 1))
        d.line([(x, y), (x, y + dy * L)], fill=color + (200,), width=max(3, width + 1))


def _fit_font(text: str, max_w: int, base: int, max_lines: int = 3):
    """以「换行后不超过 max_lines 行」为目标选字号：从基准字号往下试。

    不能只看单行放不放得下——30 字的标题缩到下限也能塞成一行，
    但字号会小到没法看；正确策略是先换行，行数超限才降字号。
    """
    tmp = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    size = base
    f = _font(size)
    if f is None:
        raise RuntimeError("未找到可用中文字体（assets/fonts/SmileySans-Oblique.ttf 缺失？）")
    best = (f, _wrap_by_width(text, f, max_w))
    while size > _TITLE_MIN and len(best[1]) > max_lines:
        size = max(_TITLE_MIN, int(size * 0.88))
        f = _font(size)
        best = (f, _wrap_by_width(text, f, max_w))
    return best


def _wrap_by_width(text: str, font, max_w: int) -> list[str]:
    """中文逐字换行（没有空格，不能按词断）。"""
    tmp = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines, cur = [], ""
    for ch in text:
        if tmp.textlength(cur + ch, font=font) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def _draw_center_block(img: Image.Image, title: str, subtitle: str, pal: dict) -> None:
    """版式 center：标题居中（超宽自动换行），上下装饰线，副标题下方。"""
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    base = int(min(w, h) * _TITLE_RATIO)
    base = min(max(base, _TITLE_MIN), _TITLE_MAX)
    font_t, lines = _fit_font(title, w - 120, base)
    lines = lines[:3]  # 最多 3 行
    line_h = int(font_t.size * 1.28)
    total_h = len(lines) * line_h + (44 if subtitle else 0)
    y = (h - total_h) // 2
    for ln in lines:
        tw = d.textlength(ln, font=font_t)
        d.text(((w - tw) / 2, y), ln, font=font_t, fill=pal["main"])
        y += line_h
    if subtitle:
        font_s = _font(max(16, base // 3))
        if font_s:
            tw = d.textlength(subtitle, font=font_s)
            # 标题与副标题之间的短分隔线
            d.line([(w / 2 - 40, y + 6), (w / 2 + 40, y + 6)], fill=pal["accent"] + (200,), width=2)
            d.text(((w - tw) / 2, y + 22), subtitle, font=font_s, fill=pal["sub"])
    # 顶部小点（克制）
    r = 4
    d.ellipse([w / 2 - r, h * 0.12 - r, w / 2 + r, h * 0.12 + r], fill=pal["accent"] + (220,))


def _draw_leftband(img: Image.Image, title: str, subtitle: str, pal: dict) -> None:
    """版式 leftband：左侧粗色带 + 左对齐标题块。"""
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    band_w = max(10, int(min(w, h) * 0.02))
    inset = int(min(w, h) * 0.12)
    # 左侧主色带 + 右侧细线（双线更有装裱感）
    d.rectangle([inset, inset, inset + band_w, h - inset], fill=pal["line"] + (210,))
    d.rectangle([inset + band_w + 10, inset, inset + band_w + 12, h - inset], fill=pal["line"] + (90,))

    text_left = inset + band_w + 44
    max_w = w - text_left - inset
    base = int(min(w, h) * _TITLE_RATIO)
    base = min(max(base, _TITLE_MIN), _TITLE_MAX)
    font_t, lines = _fit_font(title, max_w, base)
    lines = lines[:3]
    line_h = int(font_t.size * 1.3)
    total_h = len(lines) * line_h + (40 if subtitle else 0)
    y = (h - total_h) // 2
    for ln in lines:
        d.text((text_left, y), ln, font=font_t, fill=pal["main"])
        y += line_h
    if subtitle:
        font_s = _font(max(16, base // 3))
        if font_s:
            d.line([(text_left, y + 2), (text_left + 56, y + 2)], fill=pal["accent"] + (220,), width=2)
            d.text((text_left, y + 16), subtitle, font=font_s, fill=pal["sub"])


def _draw_seal(img: Image.Image, title: str, subtitle: str, pal: dict) -> None:
    """版式 seal：标题块偏左上 + 右下朱砂方印（取标题首二字）。"""
    _draw_leftband(img, title, subtitle, pal)
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    inset = int(min(w, h) * 0.12)
    side = int(min(w, h) * 0.14)
    x1, y1 = w - inset - side, h - inset - side
    # 印章：朱砂底 + 内白框 + 两字竖排
    d.rounded_rectangle([x1, y1, x1 + side, y1 + side], radius=6, fill=pal["accent"] + (235,))
    m = side // 8
    d.rectangle([x1 + m, y1 + m, x1 + side - m, y1 + side - m], outline=(255, 255, 255, 190), width=2)
    chars = (title or "玄黄").replace(" ", "")[:2] or "玄黄"
    font_c = _font(int(side * 0.34))
    if font_c:
        for i, ch in enumerate(chars):
            cw = d.textlength(ch, font=font_c)
            d.text((x1 + (side - cw) / 2, y1 + m + 10 + i * int(side * 0.36)), ch,
                   font=font_c, fill=(255, 252, 246, 245))


# ---------------------------------------------------------------- 入口


def render_cover(title: str, subtitle: str = "", size: str = "wechat",
                 layout: str = "center", theme: str = "ink") -> bytes:
    """渲染封面，返回 PNG 字节。参数由路由层校验。"""
    w, h = SIZES[size]
    pal = THEMES[theme]
    img = _linear_bg(w, h, pal["bg1"], pal["bg2"]).convert("RGBA")

    # 背景大字水印（同主题超淡，丰富层次）
    if _font(int(min(w, h) * 0.5)):
        wm = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        wd = ImageDraw.Draw(wm)
        f = _font(int(min(w, h) * 0.5))
        wd.text((w * 0.62, h * 0.30), (title or "玄黄")[:1], font=f, fill=pal["main"] + (16,))
        wm = wm.filter(ImageFilter.GaussianBlur(2))
        img = Image.alpha_composite(img, wm)

    draw = ImageDraw.Draw(img, "RGBA")
    _frame(draw, w, h, pal["line"])
    {"center": _draw_center_block, "leftband": _draw_leftband, "seal": _draw_seal}[layout](img, title, subtitle, pal)

    img = img.convert("RGB")
    random.seed(len(title) * 131 + h)  # 同参数渲染结果稳定
    _grain(img)
    _vignette(img, 0.30 if theme != "paper" else 0.12)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_cover_b64(**kw) -> str:
    return "data:image/png;base64," + base64.b64encode(render_cover(**kw)).decode()

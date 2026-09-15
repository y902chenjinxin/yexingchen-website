"""工具岛 - AI 封面生成（服务端 Pillow 模板渲染）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.cover_render import LAYOUTS, SIZES, THEMES, render_cover_b64
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/tools/cover", tags=["工具岛-封面"])


class CoverIn(BaseModel):
    title: str = ""
    subtitle: str = ""
    size: str = "wechat"
    layout: str = "center"
    theme: str = "ink"

    @field_validator("title")
    @classmethod
    def _title_required(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise_error(ErrCode.INVALID_PARAM, "标题不能为空")
        return v[:40]

    @field_validator("subtitle")
    @classmethod
    def _subtitle_len(cls, v: str) -> str:
        return (v or "").strip()[:60]


@router.post("/render", response_model=ResponseBase)
async def render_cover(req: CoverIn, current_user: dict = Depends(get_current_user)):
    """渲染封面图，返回 data:image/png;base64（前端直接 <img> 预览 / 转 blob 下载）。"""
    if req.size not in SIZES:
        raise_error(ErrCode.INVALID_PARAM, f"不支持的尺寸：{req.size}")
    if req.layout not in LAYOUTS:
        raise_error(ErrCode.INVALID_PARAM, f"不支持的版式：{req.layout}")
    if req.theme not in THEMES:
        raise_error(ErrCode.INVALID_PARAM, f"不支持的主题：{req.theme}")
    try:
        image = render_cover_b64(
            title=req.title, subtitle=req.subtitle,
            size=req.size, layout=req.layout, theme=req.theme,
        )
    except RuntimeError as e:
        raise_error(ErrCode.INVALID_PARAM, str(e))
    return ResponseBase(data={"image": image, "size": req.size, "layout": req.layout, "theme": req.theme})


@router.get("/presets", response_model=ResponseBase)
async def presets(current_user: dict = Depends(get_current_user)):
    """可选参数枚举（前端构建选择器，避免硬编码两份）。"""
    return ResponseBase(data={
        "sizes": [
            {"key": k, "label": v[0], "w": v[1], "h": v[2]}
            for k, v in (
                ("wechat", ("公众号首图", *SIZES["wechat"])),
                ("xhs", ("小红书 3:4", *SIZES["xhs"])),
                ("video", ("视频封面 16:9", *SIZES["video"])),
                ("square", ("方形 1:1", *SIZES["square"])),
            )
        ],
        "layouts": [
            {"key": "center", "label": "居中标题"},
            {"key": "leftband", "label": "左带装裱"},
            {"key": "seal", "label": "朱砂钤印"},
        ],
        "themes": [
            {"key": "ink", "label": "玄墨流金"},
            {"key": "rain", "label": "雨青"},
            {"key": "paper", "label": "宣纸"},
        ],
    })

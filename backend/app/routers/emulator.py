"""模拟器 ROM 库（v2.46.192）

## 这个模块做什么 / 不做什么

做：管理「服务器上可玩的 ROM 文件列表」，并允许账号本人**上传自己的 ROM 文件**。
不做：不提供、不下载、不预置任何商业游戏 ROM。

## 目录约定（nginx 已配 `location /roms/` 指向 ROM_ROOT）

    /var/www/yexingchen/roms/          内置（随代码发布，只读）
    /var/www/yexingchen/roms/user/     账号上传（可增删）

前端下拉读 `GET /api/emulator/roms`，返回两组：builtin / uploaded。
"""
from __future__ import annotations

import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import *
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/emulator", tags=["模拟器"])

ROM_ROOT = os.environ.get("ROM_ROOT", "/var/www/yexingchen/roms")
USER_ROOT = os.path.join(ROM_ROOT, "user")

# 与前端 CORES 对应：扩展名 → EmulatorJS core
EXT_CORE = {
    ".nes": "nes",
    ".sfc": "snes", ".smc": "snes",
    ".gba": "gba",
    ".gb": "gb", ".gbc": "gb",
    ".n64": "n64", ".z64": "n64",
    ".md": "segaMD", ".gen": "segaMD", ".bin": "segaMD",
    ".iso": "psx",
}
MAX_BYTES = 64 * 1024 * 1024
SAFE_NAME = re.compile(r"^[A-Za-z0-9 _\-.\u4e00-\u9fa5]{1,120}$")

# 内置游戏的中文标签（文件放在 ROM_ROOT 根目录）
BUILTIN_META = {
    "nova.nes": {"label": "Nova the Squirrel", "tag": "平台动作",
                 "credit": "GPL-3.0 / CC BY-NC-SA 4.0 · NovaSquirrel"},
    "thwaite.nes": {"label": "Thwaite", "tag": "射击",
                    "credit": "开源 · pinobatch"},
}


def _scan(dir_path: str, builtin: bool) -> list[dict]:
    out: list[dict] = []
    if not os.path.isdir(dir_path):
        return out
    for name in sorted(os.listdir(dir_path)):
        full = os.path.join(dir_path, name)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in EXT_CORE:
            continue
        meta = BUILTIN_META.get(name, {}) if builtin else {}
        out.append({
            "file": name,
            "label": meta.get("label") or os.path.splitext(name)[0],
            "tag": meta.get("tag") or "",
            "credit": meta.get("credit") or "",
            "core": EXT_CORE[ext],
            "size": os.path.getsize(full),
            "builtin": builtin,
            "url": f"/roms/{name}" if builtin else f"/roms/user/{name}",
        })
    return out


@router.get("/roms", response_model=ResponseBase)
async def list_roms(current_user: dict = Depends(get_current_user)):
    """服务器上可玩的 ROM 列表（内置 + 本账号上传的）"""
    builtin = _scan(ROM_ROOT, True)
    uploaded = _scan(USER_ROOT, False)
    return ResponseBase(data={"builtin": builtin, "uploaded": uploaded})


@router.post("/roms", response_model=ResponseBase)
async def upload_rom(
    file: UploadFile = File(...),
    label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """上传自己的 ROM 文件到本账号的库里。

    说明：服务器不提供任何商业游戏 ROM，这里只是把**你自己**的文件放进你自己的目录，
    便于下次直接在下拉里选。文件大小上限 64MB。
    """
    name = os.path.basename(file.filename or "")
    if not name or not SAFE_NAME.match(name):
        raise_error(ErrCode.INVALID_PARAM, "文件名不合法")
    ext = os.path.splitext(name)[1].lower()
    if ext not in EXT_CORE:
        raise_error(ErrCode.INVALID_PARAM, f"不支持的格式 {ext or '(无扩展名)'}")

    data = await file.read()
    if not data:
        raise_error(ErrCode.INVALID_PARAM, "文件为空")
    if len(data) > MAX_BYTES:
        raise_error(ErrCode.INVALID_PARAM, "文件超过 64MB")

    os.makedirs(USER_ROOT, exist_ok=True)
    # 同名覆盖（用户可能重新上传同一份）
    target = os.path.join(USER_ROOT, name)
    with open(target, "wb") as f:
        f.write(data)

    # 可选：给个友好名字
    if label:
        clean = re.sub(r"[^\w\u4e00-\u9fa5 \-.]", "", label)[:60].strip()
        if clean:
            BUILTIN_META[name] = {"label": clean, "tag": "已上传", "credit": ""}

    return ResponseBase(msg="已保存", data={
        "file": name, "size": len(data), "core": EXT_CORE[ext],
        "url": f"/roms/user/{name}",
    })


@router.delete("/roms/{filename}", response_model=ResponseBase)
async def delete_rom(filename: str, current_user: dict = Depends(get_current_user)):
    """删除本账号上传的 ROM（内置的不能删）"""
    if not SAFE_NAME.match(filename):
        raise_error(ErrCode.INVALID_PARAM, "文件名不合法")
    target = os.path.join(USER_ROOT, filename)
    if not os.path.isfile(target):
        raise_error(ErrCode.NOT_FOUND, "文件不存在")
    os.remove(target)
    return ResponseBase(msg="已删除")

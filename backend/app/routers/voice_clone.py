"""工具岛 - 音色克隆与语音合成（复用 MiniMax 共享 Provider）。

仅对 base_url 指向 MiniMax 的 Provider 开放：其它（OpenAI 等）没有克隆能力，
前端据 /status 决定显示「去配置 MiniMax」还是工具本体。
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.voice_clone import VoiceClone
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services import minimax_voice
from app.services.log_service import log_action
from app.services.user_ai_provider import resolve_user_provider
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/tools/voice", tags=["工具岛-音色克隆"])


def _cfg_for(db: Session, user_id: int, provider_id=None):
    cfg = resolve_user_provider(db, user_id, provider_id)
    if cfg is None:
        raise_error(ErrCode.INVALID_PARAM, "尚未配置任何 AI Provider，请先在 AI 助手中配置")
    if not minimax_voice.is_minimax_base(cfg.base_url):
        raise_error(ErrCode.INVALID_PARAM, "音色克隆仅支持 MiniMax Provider，请切换或配置 MiniMax")
    return cfg


@router.get("/status", response_model=ResponseBase)
async def status(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """前端探测：是否具备克隆条件 + 音色保留期倒计时。"""
    uid = current_user["user_id"]
    cfg = resolve_user_provider(db, uid, None)
    ready = bool(cfg) and minimax_voice.is_minimax_base(cfg.base_url)
    rows = (
        db.query(VoiceClone)
        .filter(VoiceClone.user_id == uid, VoiceClone.deleted_at.is_(None))
        .order_by(VoiceClone.id.desc())
        .all()
    )
    now = datetime.now()
    voices = [{
        "id": v.id,
        "voice_id": v.voice_id,
        "name": v.name,
        "created_at": str(v.created_at),
        "last_used_at": str(v.last_used_at),
        # 临时音色 168h 保留期：距删除的小时数（用过一次 TTS 即刷新）
        "hours_left": max(0, 168 - int((now - v.last_used_at).total_seconds() // 3600)),
    } for v in rows]
    return ResponseBase(data={"ready": ready, "voices": voices})


@router.get("/voices", response_model=ResponseBase)
async def list_voices(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    rows = (
        db.query(VoiceClone)
        .filter(VoiceClone.user_id == current_user["user_id"], VoiceClone.deleted_at.is_(None))
        .order_by(VoiceClone.id.desc())
        .all()
    )
    return ResponseBase(data={"list": [{
        "id": v.id, "voice_id": v.voice_id, "name": v.name,
        "created_at": str(v.created_at), "last_used_at": str(v.last_used_at),
    } for v in rows]})


class CloneOut(BaseModel):
    name: str = "我的音色"
    preview_text: str = "你好，这是我复刻的声音，很高兴认识你。"
    provider_id: int | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = (v or "").strip() or "我的音色"
        return v[:64]


@router.post("/clone", response_model=ResponseBase)
async def clone(
    file: UploadFile = File(...),
    name: str = Form("我的音色"),
    preview_text: str = Form("你好，这是我复刻的声音，很高兴认识你。"),
    provider_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """上传样本（10s–5min，mp3/m4a/wav）→ 复刻 → 返回试听链接。"""
    uid = current_user["user_id"]
    cfg = _cfg_for(db, uid, provider_id)
    data = await file.read()

    try:
        file_id = await asyncio.to_thread(
            minimax_voice.upload_clone_audio, cfg, data, file.filename or ""
        )
        voice_id = minimax_voice.gen_voice_id()
        result = await asyncio.to_thread(
            minimax_voice.clone_voice, cfg, file_id, voice_id, preview_text
        )
    except minimax_voice.MiniMaxVoiceError as e:
        raise_error(ErrCode.INVALID_PARAM, str(e))

    rec = VoiceClone(user_id=uid, voice_id=voice_id, name=name.strip()[:64] or "我的音色",
                     provider_id=cfg.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    log_action(db, uid, "create", "voice_clone", rec.id, detail=f"复刻音色「{rec.name}」({voice_id})")

    return ResponseBase(data={
        "id": rec.id, "voice_id": voice_id, "name": rec.name,
        "demo_audio": result["demo_audio"],
        "notice": "试听不收费；7 天内用「合成」一次即可永久保留该音色",
    })


class SpeakIn(BaseModel):
    voice_record_id: int
    text: str
    speed: float = 1.0

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        if not (v or "").strip():
            raise_error(ErrCode.INVALID_PARAM, "合成文本不能为空")
        return v.strip()[:2000]


@router.post("/speak")
async def speak(
    req: SpeakIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """用克隆音色合成语音，返回 audio/mpeg 字节流。同时刷新 168h 保留期。"""
    uid = current_user["user_id"]
    rec = (
        db.query(VoiceClone)
        .filter(VoiceClone.id == req.voice_record_id,
                VoiceClone.user_id == uid, VoiceClone.deleted_at.is_(None))
        .first()
    )
    if not rec:
        raise_error(ErrCode.NOT_FOUND)
    cfg = _cfg_for(db, uid, rec.provider_id)

    try:
        audio = await asyncio.to_thread(
            minimax_voice.tts, cfg, req.text, rec.voice_id,
            speed=min(max(req.speed, 0.5), 2.0),
        )
    except minimax_voice.MiniMaxVoiceError as e:
        raise_error(ErrCode.INVALID_PARAM, str(e))

    rec.last_used_at = datetime.now()
    db.commit()
    return Response(content=audio, media_type="audio/mpeg")


@router.delete("/voices/{record_id}", response_model=ResponseBase)
async def remove_voice(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rec = (
        db.query(VoiceClone)
        .filter(VoiceClone.id == record_id,
                VoiceClone.user_id == current_user["user_id"], VoiceClone.deleted_at.is_(None))
        .first()
    )
    if not rec:
        raise_error(ErrCode.NOT_FOUND)
    rec.deleted_at = datetime.now()
    db.commit()
    log_action(db, current_user["user_id"], "delete", "voice_clone", record_id,
               detail=f"删除音色「{rec.name}」")
    return ResponseBase(msg="已删除")

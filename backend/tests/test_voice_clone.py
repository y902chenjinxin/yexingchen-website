"""音色克隆：MiniMax 客户端契约 + 路由落库 + 保留期语义。

httpx 全程 monkeypatch，不触真实 API、不花额度。
"""
import asyncio
import binascii
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.ai_provider import UserAiProvider
from app.models.user import User
from app.models.voice_clone import VoiceClone
from app.routers.voice_clone import SpeakIn, clone, remove_voice, speak, status
from app.services.minimax_voice import (
    MiniMaxVoiceError, gen_voice_id, is_minimax_base, tts, upload_clone_audio,
)

UID = 1


class _Cfg:
    """最小 Provider 配置桩（duck-typing UserAiProvider）。"""
    id = 7
    api_key = "test-key"
    base_url = "https://api.minimaxi.com/v1"


def _resp(code=0, payload=None, status_code=200, text=""):
    class R:
        def __init__(self):
            self.status_code = status_code
            self.text = text
        def json(self):
            return payload if payload is not None else {"base_resp": {"status_code": code, "status_msg": "err"}}

    return R()


def _db():
    from app.models.log import OperationLog
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[
        User.__table__, UserAiProvider.__table__, VoiceClone.__table__, OperationLog.__table__,
    ])
    s = sessionmaker(bind=engine)()
    s.add(User(id=UID, email="a@test.local", password_hash="x", role="user", is_super_admin=0, status="approved"))
    # 一条可用的 MiniMax 共享配置（owner 超管 999）
    s.add(User(id=999, email="boss@test.local", password_hash="x", role="super_admin",
               is_super_admin=1, status="approved"))
    s.add(UserAiProvider(id=7, user_id=999, provider_key="openai", display_name="共享MiniMax",
                         api_key="test-key", base_url="https://api.minimaxi.com/v1",
                         model_name="gpt-4o-mini", enabled=True, is_default=True))
    s.commit()
    return s


USER = {"user_id": UID}


def test_minimax_base_detection():
    assert is_minimax_base("https://api.minimaxi.com/v1")
    assert is_minimax_base("https://api.minimax.io/v1")
    assert not is_minimax_base("https://api.openai.com/v1")
    assert not is_minimax_base(None)


def test_gen_voice_id_compliant():
    import re
    for _ in range(20):
        assert re.match(r"^[A-Za-z][A-Za-z0-9_-]{7,255}$", gen_voice_id())


def test_upload_rejects_bad_ext_and_empty():
    with pytest.raises(MiniMaxVoiceError, match="mp3"):
        upload_clone_audio(_Cfg(), b"x", "sample.txt")
    with pytest.raises(MiniMaxVoiceError, match="为空"):
        upload_clone_audio(_Cfg(), b"", "a.mp3")


def test_upload_ok(monkeypatch):
    def fake_post(url, **kw):
        assert url.endswith("/v1/files/upload")
        assert kw["data"]["purpose"] == "voice_clone"
        return _resp(payload={"file": {"file_id": 42}, "base_resp": {"status_code": 0}})
    monkeypatch.setattr(httpx, "post", fake_post)
    assert upload_clone_audio(_Cfg(), b"audio-bytes", "sample.mp3") == 42


def test_minimax_error_translated(monkeypatch):
    def fake_post(url, **kw):
        return _resp(payload={"base_resp": {"status_code": 2038, "status_msg": "voice expired"}})
    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(MiniMaxVoiceError, match="7 天"):
        tts(_Cfg(), "你好", "yhabcdef12")


def test_tts_decodes_hex(monkeypatch):
    raw = b"ID3fake-mp3-bytes"
    def fake_post(url, **kw):
        assert kw["json"]["voice_setting"]["voice_id"] == "yhabcdef12"
        return _resp(payload={"data": {"audio": binascii.hexlify(raw).decode()},
                              "base_resp": {"status_code": 0}})
    monkeypatch.setattr(httpx, "post", fake_post)
    assert tts(_Cfg(), "你好", "yhabcdef12") == raw


def test_speak_touches_last_used(monkeypatch):
    db = _db()
    rec = VoiceClone(user_id=UID, voice_id="yhabcdef12", name="测试", provider_id=7)
    db.add(rec); db.commit(); db.refresh(rec)
    old = rec.last_used_at

    raw = b"mp3-data"
    def fake_post(url, **kw):
        return _resp(payload={"data": {"audio": binascii.hexlify(raw).decode()},
                              "base_resp": {"status_code": 0}})
    monkeypatch.setattr(httpx, "post", fake_post)

    resp = asyncio.run(speak(SpeakIn(voice_record_id=rec.id, text="在吗"), db=db, current_user=USER))
    assert resp.body == raw
    assert resp.media_type == "audio/mpeg"
    assert rec.last_used_at > old  # 合成即续命（168h 保留期刷新）


def test_status_reports_ready_for_shared_minimax():
    """自己没配 Provider 时回落超管共享 MiniMax → ready=True。"""
    db = _db()
    res = asyncio.run(status(db=db, current_user=USER))
    assert res.data["ready"] is True
    assert res.data["voices"] == []


def test_clone_full_flow_persists_record(monkeypatch):
    """上传 → 复刻 → 落库，全链 mock（绝不触真实 API）。"""
    db = _db()
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        if url.endswith("/files/upload"):
            assert kw["files"]["file"][0] == "sample.mp3"
            return _resp(payload={"file": {"file_id": 42}, "base_resp": {"status_code": 0}})
        if url.endswith("/voice_clone"):
            assert kw["json"]["file_id"] == 42
            assert kw["json"]["voice_id"].startswith("yh")
            return _resp(payload={"demo_audio": "https://cdn.example.com/demo.mp3",
                                  "base_resp": {"status_code": 0}})
        raise AssertionError(f"意外请求 {url}")

    monkeypatch.setattr(httpx, "post", fake_post)
    res = asyncio.run(clone(
        file=_FakeUpload("sample.mp3", b"x" * 100), name="我的分身",
        preview_text="你好", provider_id=None, db=db, current_user=USER))

    d = res.data
    assert d["voice_id"].startswith("yh") and d["demo_audio"].endswith(".mp3")
    rec = db.query(VoiceClone).filter(VoiceClone.id == d["id"]).first()
    assert rec is not None and rec.user_id == UID and rec.provider_id == 7
    assert len(calls) == 2  # 恰好两次外部调用：上传 + 复刻


class _FakeUpload:
    def __init__(self, filename, data):
        self.filename = filename
        self._data = data
    async def read(self):
        return self._data


def test_remove_voice_soft_delete():
    db = _db()
    rec = VoiceClone(user_id=UID, voice_id="yhffffaa11", name="删我", provider_id=7)
    db.add(rec); db.commit(); db.refresh(rec)
    asyncio.run(remove_voice(rec.id, db=db, current_user=USER))
    assert rec.deleted_at is not None
    # 二次删除报 404（列表里已看不到）
    with pytest.raises(HTTPException):
        asyncio.run(remove_voice(rec.id, db=db, current_user=USER))

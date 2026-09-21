"""Embedding 服务（v2.39 RAG 基础）。

OpenAI 兼容 /v1/embeddings 接口，支持 bge-m3 / text-embedding-3-small 等。
向量以 numpy float32 BLOB 存到 xuanhuang_note_embeddings，按 note_id + model 幂等。

设计要点：
- 模型默认跟随用户当前 AI Provider 的 base_url + api_key（共享配置）。
  没有 provider 时退化为 hash 占位向量（None），搜索功能仍可跑但语义召回退化为空。
- content_hash 避免文本未变时重复请求 Provider，节省配额。
- 向量维度按 Provider 返回值自适应（首次写入保存 dim）。
"""
from __future__ import annotations

import hashlib
import json
import logging
import struct
from datetime import datetime
from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models.ai_advanced import NoteEmbedding
from app.models.workbench import Note
from app.services.user_ai_provider import (
    build_http_provider_from_config,
    resolve_user_provider,
)

logger = logging.getLogger(__name__)


# ---------- 文本归一化 ----------
def _hash_content(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _normalize_for_embedding(text: str, max_chars: int = 4000) -> str:
    """截断 + 去多余空白，避免超出 embedding 模型 token 上限。"""
    t = (text or "").strip()
    if len(t) > max_chars:
        t = t[:max_chars]
    return t


# ---------- Provider 调嵌入 ----------
def _call_embed(base_url: str, api_key: str, model: str, inputs: List[str], timeout: int = 60):
    """调 /v1/embeddings；失败抛 RuntimeError。返回 List[List[float]]。"""
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 httpx，无法调用 embeddings") from exc
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "input": inputs}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload, headers=headers)
    if r.status_code >= 400:
        raise RuntimeError(f"embeddings HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    items = data.get("data") or []
    out = []
    for it in items:
        emb = it.get("embedding")
        if isinstance(emb, list):
            out.append(emb)
    return out


# ---------- 公共入口 ----------
def get_or_create_note_embedding(
    db: Session,
    user_id: int,
    note: Note,
    *,
    force: bool = False,
) -> Optional[NoteEmbedding]:
    """拿一条笔记的 embedding（按 (note_id, model) 幂等），文本变更才重算。

    返回 None 表示当前用户未配置 Provider 或嵌入失败（不阻塞主路径）。
    """
    cfg = resolve_user_provider(db, user_id, None)
    if not cfg:
        return None
    model = cfg.model_name or "text-embedding-3-small"
    text = _normalize_for_embedding(
        f"{note.title or ''}\n\n{note.content or ''}".strip()
    )
    h = _hash_content(text)

    row = (
        db.query(NoteEmbedding)
        .filter(NoteEmbedding.note_id == note.id, NoteEmbedding.model == model)
        .first()
    )
    if row and not force and row.content_hash == h:
        return row

    # 调 provider
    base_url = cfg.base_url or "https://api.openai.com/v1"
    try:
        vecs = _call_embed(base_url, cfg.api_key, model, [text])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[embedding] %s/%s failed: %s", model, note.id, exc)
        return row  # 返回旧 row（即便过期），避免阻塞调用方
    if not vecs:
        return row
    vec = np.asarray(vecs[0], dtype=np.float32)
    blob = vec.tobytes()
    if row:
        row.vector = blob
        row.dim = int(vec.shape[0])
        row.content_hash = h
        row.updated_at = datetime.now()
    else:
        row = NoteEmbedding(
            note_id=note.id,
            user_id=user_id,
            model=model,
            dim=int(vec.shape[0]),
            vector=blob,
            content_hash=h,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def embed_query(
    db: Session, user_id: int, query: str
) -> Optional[np.ndarray]:
    """把搜索 query 也嵌入为同一维度的向量。"""
    cfg = resolve_user_provider(db, user_id, None)
    if not cfg:
        return None
    model = cfg.model_name or "text-embedding-3-small"
    q = _normalize_for_embedding(query)
    try:
        vecs = _call_embed(cfg.base_url or "https://api.openai.com/v1", cfg.api_key, model, [q])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[embedding] query failed: %s", exc)
        return None
    if not vecs:
        return None
    return np.asarray(vecs[0], dtype=np.float32)


def vector_blob_to_array(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """余弦相似度；维度不一致时安全返回 0。"""
    if a.shape != b.shape or a.size == 0:
        return 0.0
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def search_semantic(
    db: Session,
    user_id: int,
    query: str,
    *,
    top_k: int = 8,
    only_active: bool = True,
) -> List[dict]:
    """语义召回：返回 [{"id","title","snippet","score"}]。"""
    q_vec = embed_query(db, user_id, query)
    if q_vec is None:
        return []
    rows = (
        db.query(NoteEmbedding, Note)
        .join(Note, Note.id == NoteEmbedding.note_id)
        .filter(NoteEmbedding.user_id == user_id)
        .all()
    )
    if not rows:
        return []
    scored: list = []
    for ne, note in rows:
        if only_active and note.deleted_at is not None:
            continue
        if ne.dim != q_vec.shape[0]:
            continue  # 跨维度无法比较
        a = vector_blob_to_array(ne.vector)
        s = cosine_sim(q_vec, a)
        scored.append((s, note))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for s, note in scored[:top_k]:
        snippet = (note.content or "").strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        out.append({
            "id": note.id,
            "title": note.title or "（无标题）",
            "snippet": snippet,
            "score": round(s, 4),
        })
    return out

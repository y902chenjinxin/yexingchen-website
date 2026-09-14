"""AI 对话与能力调用：preview / invoke / chat_stream / apply、对话管理、对话-内容关联。"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workbench import (
    AiConversation,
    AiConversationLink,
    AiMessage,
    Tag,
    Task,
)
from app.services.ai_providers import (
    AiRequest,
    FakeProvider,
    organize_note,
    preview_input_scope,
    sanitize_text,
    suggest_tags as ai_suggest_tags,
    suggest_task as ai_suggest_task,
    summarize_note,
)
from app.services.softdelete import (
    active_query,
    log_workbench_action,
    soft_delete,
)
from app.utils.security import get_current_user
from app.routers.workbench._common import (
    _ensure_user_asset,
    _ensure_user_conversation,
    _ensure_user_note,
    _ensure_user_task,
    _note_to_out,
    _task_to_out,
    _to_iso,
    ok,
    raise_http,
)
from app.routers.workbench._kb import build_knowledge_context
from app.routers.workbench._schemas import (
    AiApplyIn,
    AiChatStreamIn,
    AiConversationIn,
    AiInvokeIn,
    AiLinkIn,
    AiMessageIn,
)
from app.services.user_ai_provider import (
    build_http_provider_from_config,
    resolve_user_provider,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-AI"])


# 独立原生 AI 助手：system 提示与携带的历史轮数上限
AI_CHAT_SYSTEM_PROMPT = (
    "你是一个独立、通用的人工智能助手，并不隶属于任何笔记或工作台系统。"
    "你可以回答日常问题、解释概念、分析和总结用户提供的内容、根据需求撰写文本、"
    "生成笔记草稿、提供建议或进行创作。用自然、温暖、口语化的中文回答，条理清晰，"
    "不刻意引用\u2018笔记\u2019等系统概念。"
)
AI_CHAT_CONTEXT = 20


# ============================================================
# AI 能力分发
# ============================================================
def _ability_dispatch(ability: str, content: str):
    if ability == "organize":
        return organize_note(content)
    if ability == "summarize":
        return summarize_note(content)
    if ability == "suggest_tags":
        return ai_suggest_tags(content)
    if ability == "suggest_task":
        return ai_suggest_task(content)
    raise_http(400, f"未知 ability：{ability}", 400)


# ============================================================
# AI 调用：preview / invoke / chat_stream / apply
# ============================================================
@router.post("/ai/preview")
def ai_preview(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """生成 AI 调用前的发送范围预览，不真正调用。"""
    ability = payload.get("ability")
    note_id = payload.get("note_id")
    content = payload.get("content")
    if not ability:
        raise_http(400, "ability 必填", 400)
    if note_id:
        note = _ensure_user_note(db, note_id, current_user["user_id"])
        content = content if content is not None else (note.content or "")
    if not content:
        raise_http(400, "内容为空", 400)
    return ok(preview_input_scope(content, ability))


@router.post("/ai/invoke")
def ai_invoke(
    payload: AiInvokeIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """执行 AI 调用。强制要求 conversation_id，并校验会话归属与未删除。

    行为：
    - 用户取消时不调用本端点；
    - 调用成功后，把 user/assistant 两条消息写入指定 conversation；
    - assistant 消息携带 pending_apply=True 与 apply_payload（AI 返回结构化结果），
      供后续 /ai/apply 端点消费。
    """
    uid = current_user["user_id"]
    conv = _ensure_user_conversation(db, payload.conversation_id, uid)

    content = payload.content
    if payload.note_id:
        note = _ensure_user_note(db, payload.note_id, uid)
        content = content if content is not None else (note.content or "")
    if not content:
        raise_http(400, "内容为空", 400)

    preview = preview_input_scope(content, payload.ability)
    cleaned_content = sanitize_text(content)

    # 选 provider：payload.provider_id → 默认 → 都没有则 FakeProvider
    user_cfg = resolve_user_provider(db, uid, payload.provider_id)
    if user_cfg:
        active_provider = build_http_provider_from_config(user_cfg)
        provider_name = f"{user_cfg.provider_key}:{user_cfg.display_name}"
        model_name = user_cfg.model_name
    else:
        active_provider = FakeProvider()
        provider_name = "fake"
        model_name = "fake-1"

    req = AiRequest(
        ability=payload.ability,
        content=cleaned_content,
    )
    resp = active_provider.invoke(req)

    # AiResponse 兼容
    class _Resp:
        def __init__(self, ability, text, data, provider, model, raw):
            self.ability, self.text, self.data = ability, text, data
            self.provider, self.model = provider, model
            self._raw_provider = raw

    resp = _Resp(payload.ability, resp.text, resp.data, provider_name, model_name, active_provider)

    # 入库
    scope_text = json.dumps(preview, ensure_ascii=False)
    apply_payload_json = json.dumps(resp.data or {}, ensure_ascii=False)

    user_msg = AiMessage(
        conversation_id=conv.id,
        role="user",
        content=scope_text,
        input_scope=scope_text,
    )
    assistant_msg = AiMessage(
        conversation_id=conv.id,
        role="assistant",
        content=resp.text,
        input_scope=scope_text,
        pending_apply=True,
        apply_payload=apply_payload_json,
    )
    db.add_all([user_msg, assistant_msg])
    conv.updated_at = datetime.now()
    db.commit()
    db.refresh(assistant_msg)

    provider = provider_name
    is_fake = isinstance(getattr(resp, "_raw_provider", None), FakeProvider) or provider == "fake"

    return ok({
        "ability": resp.ability,
        "text": resp.text,
        "data": resp.data,
        "provider": provider,
        "model": model_name,
        "is_fake": is_fake,
        "conversation_id": conv.id,
        "assistant_message_id": assistant_msg.id,
        "scope_preview": preview,
    })


@router.post("/ai/chat/stream")
def ai_chat_stream(
    payload: AiChatStreamIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """独立原生 AI 对话（流式直通，不与笔记/能力绑定）。

    - 读取会话历史 → 拼 system + 最近若干轮 → 追加本次用户消息；
    - 用户消息立即入库；助手回复以 SSE 逐段下发，流式完成后落库成 assistant 消息；
    - 前端通过 fetch + ReadableStream 解析，实现打字机输出。
    """
    uid = current_user["user_id"]
    conv = _ensure_user_conversation(db, payload.conversation_id, uid)

    content = sanitize_text(payload.content or "")
    if not content:
        raise_http(400, "内容为空", 400)

    # 选 provider：payload.provider_id → 默认 → 都没有则 FakeProvider
    user_cfg = resolve_user_provider(db, uid, payload.provider_id)
    if user_cfg:
        active_provider = build_http_provider_from_config(user_cfg)
        provider_name = f"{user_cfg.provider_key}:{user_cfg.display_name}"
        model_name = user_cfg.model_name
    else:
        active_provider = FakeProvider()
        provider_name = "fake"
        model_name = "fake-1"

    history = [{"role": m.role, "content": m.content} for m in conv.messages if m.content]
    history = history[-(AI_CHAT_CONTEXT - 1):]  # 预留一条给本次 user 消息
    messages = [
        {"role": "system", "content": AI_CHAT_SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": content},
    ]

    # 知识库检索注入：可选（前端开关控制），命中则追加一条 system 上下文
    knowledge_ctx = ""
    if payload.use_knowledge:
        try:
            knowledge_ctx = build_knowledge_context(db, uid, content) or ""
        except Exception:  # noqa: BLE001
            logger.debug("knowledge injection failed, fallback to plain chat", exc_info=True)
            knowledge_ctx = ""
    if knowledge_ctx:
        messages.insert(1, {"role": "system", "content": knowledge_ctx})

    # 用户消息立即入库（input_scope 记录知识库注入情况，便于排障/取证）
    user_msg = AiMessage(conversation_id=conv.id, role="user", content=content)
    if knowledge_ctx:
        try:
            user_msg.input_scope = json.dumps(
                {"knowledge": True, "chars": len(knowledge_ctx)}, ensure_ascii=False
            )
        except Exception:  # noqa: BLE001
            pass
    db.add(user_msg)
    conv.updated_at = datetime.now()
    db.commit()
    db.refresh(user_msg)

    conv_id = conv.id
    # 流式生成器在请求主 handler 返回后才执行；用与本次请求同源的 bind 建独立 session，
    # 避免与 dependency get_db 的生命周期耦合，也便于测试 override 生效。
    from sqlalchemy.orm import sessionmaker as _make_session
    _SaveSession = _make_session(bind=db.get_bind(), autoflush=False)

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    async def event_stream():
        total: list = []
        try:
            async for delta in active_provider.stream_chat(messages):
                total.append(delta)
                yield sse({"type": "token", "delta": delta})
            text = "".join(total).strip()
            if not text:
                text = "（AI 未返回有效内容，请检查 Provider 配置或网络。）"
            assistant_id = None
            s = _SaveSession()
            try:
                am = AiMessage(
                    conversation_id=conv_id,
                    role="assistant",
                    content=text,
                    input_scope=None,
                    pending_apply=False,
                )
                s.add(am)
                s.query(AiConversation).filter(AiConversation.id == conv_id).update(
                    {"updated_at": datetime.now()}
                )
                s.commit()
                s.refresh(am)
                assistant_id = am.id
            finally:
                s.close()
            yield sse({
                "type": "done",
                "conversation_id": conv_id,
                "message_id": assistant_id,
                "text": text,
                "provider": provider_name,
                "model": model_name,
            })
        except Exception as exc:  # noqa: BLE001
            logger.exception("AI chat stream failed")
            yield sse({"type": "error", "msg": str(exc)[:300]})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/ai/apply")
def ai_apply(
    payload: AiApplyIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """AI 结果应用（用户确认后由本端点写入）。

    - 重新校验 user/conversation 归属；
    - 重新校验 target（note / task）归属；
    - 对 suggest_task 允许 target_type=task 而 target_id 为 None（创建任务）。
    """
    uid = current_user["user_id"]
    _ensure_user_conversation(db, payload.conversation_id, uid)

    ability = payload.ability
    target_type = payload.target_type
    target_id = payload.target_id
    pdata = payload.payload or {}

    if ability not in ("organize", "summarize", "suggest_tags", "suggest_task"):
        raise_http(400, "未知 ability", 400)

    if target_type == "note":
        if not target_id:
            raise_http(400, "target_id 必填", 400)
        note = _ensure_user_note(db, target_id, uid)
        if ability == "summarize":
            summary = pdata.get("summary") or pdata.get("data", {}).get("summary")
            if not summary:
                raise_http(400, "payload 缺少 summary", 400)
            note.summary = str(summary)[:5000]
        elif ability == "organize":
            title = pdata.get("title") or pdata.get("data", {}).get("title")
            content = pdata.get("content") or pdata.get("data", {}).get("content")
            if title is not None:
                note.title = str(title)[:255]
            if content is not None:
                note.content = str(content)
            summary = pdata.get("summary") or pdata.get("data", {}).get("summary")
            if summary is not None:
                note.summary = str(summary)[:5000]
        elif ability == "suggest_tags":
            tag_names = pdata.get("tags") or pdata.get("data", {}).get("tags") or []
            if not isinstance(tag_names, list):
                raise_http(400, "tags 必须是数组", 400)
            names = [str(x).strip() for x in tag_names if str(x).strip()]
            new_tags = []
            for name in names:
                tag = db.query(Tag).filter(Tag.user_id == uid, Tag.name == name).first()
                if not tag:
                    tag = Tag(name=name, user_id=uid)
                    db.add(tag)
                    db.flush()
                new_tags.append(tag)
            note.tags = new_tags
        else:
            raise_http(400, f"ability {ability} 不能用于 note", 400)
        db.commit()
        db.refresh(note)
        log_workbench_action(
            db, user_id=uid, action="ai_apply",
            target_type="note", target_id=note.id,
            detail=f"AI 应用 {ability}：{note.title}",
        )
        return ok({"applied": "note", "note": _note_to_out(note).model_dump()})

    if target_type == "task":
        if ability != "suggest_task":
            raise_http(400, f"ability {ability} 不能用于 task", 400)
        title = pdata.get("title") or pdata.get("data", {}).get("title")
        description = pdata.get("description") or pdata.get("data", {}).get("description") or ""
        if not title:
            raise_http(400, "payload 缺少 title", 400)
        task = Task(
            title=str(title)[:255],
            description=str(description)[:5000],
            status="todo",
            priority="medium",
            user_id=uid,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        log_workbench_action(
            db, user_id=uid, action="ai_apply",
            target_type="task", target_id=task.id,
            detail=f"AI 生成任务：{task.title}",
        )
        return ok({"applied": "task", "task": _task_to_out(task).model_dump()})

    raise_http(400, f"未知 target_type: {target_type}", 400)


# ============================================================
# AI 对话管理
# ============================================================
@router.get("/ai/conversations")
def list_ai_conversations(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    query = active_query(db, AiConversation).filter(AiConversation.user_id == uid)
    if q:
        query = query.filter(AiConversation.title.contains(q))
    rows = query.order_by(AiConversation.updated_at.desc()).all()
    return ok({
        "list": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": _to_iso(c.created_at),
                "updated_at": _to_iso(c.updated_at),
            }
            for c in rows
        ]
    })


@router.post("/ai/conversations", status_code=201)
def create_ai_conversation(
    payload: AiConversationIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = AiConversation(
        title=(payload.title or "新对话")[:255],
        user_id=current_user["user_id"],
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ok({"id": conv.id, "title": conv.title})


@router.put("/ai/conversations/{conv_id}")
def rename_ai_conversation(
    conv_id: int,
    payload: AiConversationIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    conv.title = (payload.title or conv.title)[:255]
    db.commit()
    return ok({"id": conv.id, "title": conv.title})


@router.get("/ai/conversations/{conv_id}/messages")
def list_ai_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    return ok({
        "list": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "input_scope": m.input_scope,
                "pending_apply": bool(m.pending_apply),
                "created_at": _to_iso(m.created_at),
            }
            for m in conv.messages
        ]
    })


@router.post("/ai/conversations/{conv_id}/messages")
def append_ai_message(
    conv_id: int,
    payload: AiMessageIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    if payload.role not in ("user", "assistant", "system"):
        raise_http(400, "role 非法", 400)
    msg = AiMessage(
        conversation_id=conv.id,
        role=payload.role,
        content=sanitize_text(payload.content),
        input_scope=payload.input_scope,
    )
    db.add(msg)
    conv.updated_at = datetime.now()
    db.commit()
    db.refresh(msg)
    return ok({"id": msg.id, "role": msg.role, "content": msg.content})


@router.delete("/ai/conversations/{conv_id}")
def delete_ai_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    soft_delete(conv, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="delete",
        target_type="ai_conversation", target_id=conv_id, detail=f"删除AI对话：{conv.title}",
    )
    return ok({"ok": True})


# ============================================================
# AI 对话 与 笔记/资产/任务 关联
# ============================================================
def _resolve_link_target(db: Session, conv_id: int, payload: AiLinkIn, user_id: int):
    """校验链接目标属于当前用户；返回对应外键列和 id。"""
    if payload.target_type == "note":
        _ensure_user_note(db, payload.target_id, user_id)
        return payload.target_id, None, None
    if payload.target_type == "asset":
        _ensure_user_asset(db, payload.target_id, user_id)
        return None, payload.target_id, None
    if payload.target_type == "task":
        _ensure_user_task(db, payload.target_id, user_id)
        return None, None, payload.target_id
    raise_http(400, f"未知 target_type: {payload.target_type}", 400)


@router.post("/ai/conversations/{conv_id}/links")
def ai_link(
    conv_id: int,
    payload: AiLinkIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    _ensure_user_conversation(db, conv_id, uid)
    note_id, asset_id, task_id = _resolve_link_target(db, conv_id, payload, uid)
    link = AiConversationLink(
        conversation_id=conv_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        note_id=note_id,
        asset_id=asset_id,
        task_id=task_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return ok({
        "id": link.id,
        "conversation_id": conv_id,
        "target_type": link.target_type,
        "target_id": link.target_id,
    })


@router.get("/ai/conversations/{conv_id}/links")
def ai_list_links(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _ensure_user_conversation(db, conv_id, current_user["user_id"])
    rows = (
        db.query(AiConversationLink)
        .filter(AiConversationLink.conversation_id == conv_id)
        .order_by(AiConversationLink.created_at.desc())
        .all()
    )
    return ok({
        "list": [
            {
                "id": r.id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "note_id": r.note_id,
                "asset_id": r.asset_id,
                "task_id": r.task_id,
                "created_at": _to_iso(r.created_at),
            }
            for r in rows
        ]
    })


@router.delete("/ai/conversations/{conv_id}/links/{link_id}")
def ai_unlink(
    conv_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _ensure_user_conversation(db, conv_id, current_user["user_id"])
    link = (
        db.query(AiConversationLink)
        .filter(AiConversationLink.id == link_id, AiConversationLink.conversation_id == conv_id)
        .first()
    )
    if not link:
        raise_http(404, "关联不存在", 404)
    db.delete(link)
    db.commit()
    return ok({"ok": True})

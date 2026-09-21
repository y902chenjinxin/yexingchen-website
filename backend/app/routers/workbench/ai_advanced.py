"""工作台 AI 高级玩法（v2.39）：

- POST /ai/advanced        通用入口（rewrite/explain/extract_entities/memory_distill/agent_plan）
- POST /ai/semantic_search 语义召回（基于嵌入）
- POST /ai/index           重建/建立某条笔记的嵌入
- POST /ai/agent/start     启动自动任务
- POST /ai/agent/run       同步执行一步 / 或完整跑完（max_steps）
- GET  /ai/agent/{id}      查看 job
- GET  /ai/memory          列出长期记忆
- POST /ai/memory/forget   忘记一条
- GET  /ai/usage           当月用量
- POST /ai/ocr             OCR（图片→文字，复用高德 OCR / 站内已有）

设计原则：
- 全部复用 resolve_user_provider + build_http_provider_from_config；
- 每次调用累计 token 到 xuanhuang_ai_usage，超额抛 429；
- Agent 默认 8 步上限、可中断；tool 注册由本文件集中维护；
- 所有异常按 ok/fail 包装返回，避免 v2.38.x 拦截器误弹吐司。
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_advanced import AgentJob, NoteEmbedding, UserFact
from app.models.workbench import Note, Tag, Task
from app.services.ai_providers import (
    AiRequest,
    FakeProvider,
    sanitize_text,
    set_tool_executor,
)
from app.services.ai_usage import check_quota, current_month_usage, record_usage
from app.services.embedding import (
    get_or_create_note_embedding,
    search_semantic,
)
from app.services.user_ai_provider import (
    build_http_provider_from_config,
    resolve_user_provider,
)
from app.utils.security import get_current_user
from app.routers.workbench._common import ok, raise_http
from app.routers.workbench._schemas import (
    AiAdvancedIn,
    AiAgentRunIn,
    AiAgentStartIn,
    AiForgetIn,
    AiOcrIn,
    AiSemanticIndexIn,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-AI高级"])

# ============ Tool 注册表（Agent 可调用） ============
# 每个 executor 签名：(args: dict, *, db: Session, user_id: int) -> dict

def _tool_create_note(args: dict, *, db: Session, user_id: int) -> dict:
    title = (args.get("title") or "").strip()[:255] or "AI 自动创建"
    content = (args.get("content") or "").strip()
    if not content:
        return {"ok": False, "error": "content 不能为空"}
    n = Note(user_id=user_id, title=title, content=content, status="draft")
    db.add(n); db.commit(); db.refresh(n)
    return {"ok": True, "note_id": n.id, "title": n.title}


def _tool_create_task(args: dict, *, db: Session, user_id: int) -> dict:
    title = (args.get("title") or "").strip()[:255]
    if not title:
        return {"ok": False, "error": "title 不能为空"}
    t = Task(
        user_id=user_id,
        title=title,
        description=(args.get("description") or "").strip()[:5000],
        status="todo",
        priority=args.get("priority") or "medium",
        source_type="ai_agent",
    )
    db.add(t); db.commit(); db.refresh(t)
    return {"ok": True, "task_id": t.id, "title": t.title}


def _tool_search_notes(args: dict, *, db: Session, user_id: int) -> dict:
    q = (args.get("query") or "").strip()
    if not q:
        return {"ok": False, "error": "query 不能为空"}
    rows = (
        db.query(Note)
        .filter(Note.user_id == user_id, Note.deleted_at.is_(None))
        .filter(Note.title.contains(q))
        .order_by(Note.updated_at.desc().nullslast())
        .limit(10)
        .all()
    )
    return {
        "ok": True,
        "results": [
            {"id": n.id, "title": n.title or "（无标题）"}
            for n in rows
        ],
    }


def _tool_log_finance(args: dict, *, db: Session, user_id: int) -> dict:
    """记账工具（占位，实际字段以 finance 表为准；此版本落库尽量兼容）。"""
    from app.models.finance import FinanceTransaction

    try:
        amount = float(args.get("amount") or 0)
    except Exception:
        amount = 0
    t_type = (args.get("type") or "expense").strip()
    category = (args.get("category") or "其他").strip()[:32]
    note = (args.get("note") or "").strip()[:500]
    if amount <= 0:
        return {"ok": False, "error": "amount 必须 > 0"}
    tx = FinanceTransaction(
        user_id=user_id,
        amount_cents=int(amount * 100),
        type=t_type,
        category=category,
        note=note,
        occurred_at=datetime.now(),
    )
    db.add(tx); db.commit(); db.refresh(tx)
    return {"ok": True, "tx_id": tx.id, "amount": amount}


# 把工具注入到 ai_providers 的执行器
def _bind_default_tools():
    set_tool_executor("create_note", _tool_create_note)
    set_tool_executor("create_task", _tool_create_task)
    set_tool_executor("search_notes", _tool_search_notes)
    set_tool_executor("log_finance", _tool_log_finance)


_bind_default_tools()

# Agent 暴露给模型的 tool schema（OpenAI function calling 格式）
AGENT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "创建一条新笔记（标题+正文），用于沉淀 AI 提炼的内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "笔记标题（<=255 字符）"},
                    "content": {"type": "string", "description": "笔记正文"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "创建一条新任务（标题+描述+可选优先级）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "按关键词模糊搜索用户的笔记标题。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_finance",
            "description": "记一笔账（收入/支出）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "double", "description": "金额（元）"},
                    "type": {"type": "string", "enum": ["income", "expense"]},
                    "category": {"type": "string", "description": "分类名"},
                    "note": {"type": "string", "description": "备注"},
                },
                "required": ["amount", "type"],
            },
        },
    },
]


def _provider_or_fake(db: Session, user_id: int, provider_id: Optional[int]):
    """统一取 provider；带 fake 兜底。"""
    cfg = resolve_user_provider(db, user_id, provider_id)
    if cfg:
        return build_http_provider_from_config(cfg), cfg
    return FakeProvider(), None


def _resolve_content(payload: AiAdvancedIn, db: Session, user_id: int) -> str:
    if payload.content:
        return sanitize_text(payload.content)
    if payload.note_id:
        note = db.query(Note).filter(
            Note.id == payload.note_id, Note.user_id == user_id, Note.deleted_at.is_(None)
        ).first()
        if not note:
            raise_http(404, "笔记不存在", 404)
        return sanitize_text(f"{(note.title or '').strip()}\n\n{(note.content or '').strip()}".strip())
    raise_http(400, "content 与 note_id 至少填一个", 400)


def _resolve_style_system(ability: str, style: Optional[str]) -> Optional[str]:
    """rewrite/explain 等会按 ability + style 注入特定系统提示。"""
    if ability == "rewrite":
        m = {
            "casual": "更口语化、像朋友聊天；",
            "formal": "更书面、正式、严谨；",
            "concise": "更短、更紧凑、删冗余；",
            "emoji": "保持原意、加适度 emoji 增加生动感；",
            "polish": "润色文字流畅度，但不改变核心意思；",
            "critical": "批判审视、指出问题与改进方向。",
        }
        instr = m.get((style or "polish").lower(), m["polish"])
        return f"你是中文写作助手，{instr}不要复述原文，只输出改写后的全文。"
    if ability == "explain":
        return ("你是中文概念解释者，用通俗易懂的方式回答，"
                "避免学术腔。给出定义、例子、相关概念三个维度。")
    if ability == "extract_entities":
        return ("你从用户文本里抽取实体（人/地点/日期/承诺/待办），"
                "中文输出，不要遗漏显式提到的实体。")
    if ability == "memory_distill":
        return ("你从用户近期文本中蒸馏「稳定事实」：身份/习惯/偏好/人际关系/项目/其它。"
                "只输出确定且长期适用的事实，不要写临时想法。")
    if ability == "agent_plan":
        return ("你把用户的目标拆解为 2~6 步，每步指明意图、可调用的工具及参数。"
                "不要捏造不存在的工具，只能用 create_note / create_task / search_notes / log_finance / none。")
    if ability == "agent_step":
        return ("你执行 Agent 的下一步：先内部思考（thought），"
                "再决定一个 action（工具名 + 入参）。若目标已完成则 action=finish、done=true。"
                "只能使用 create_note / create_task / search_notes / log_finance / finish。")
    return None


# ============ 通用入口 ============
@router.post("/ai/advanced")
def ai_advanced(
    payload: AiAdvancedIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """rewrite / explain / extract_entities / memory_distill / agent_plan 的统一入口。"""
    uid = current_user["user_id"]
    try:
        check_quota(db, uid)
    except RuntimeError as e:
        raise_http(429, str(e), 429)

    ability = payload.ability.strip().lower()
    if ability not in {"rewrite", "explain", "extract_entities", "memory_distill", "agent_plan"}:
        raise_http(400, f"ability 不支持：{ability}", 400)

    content = _resolve_content(payload, db, uid)

    # 多模态：传 image_url 时把图塞进 content_parts
    content_parts = None
    if payload.image_url and ability in {"explain", "rewrite"}:
        content_parts = [
            {"type": "text", "text": (payload.style and ability == "rewrite")
             and f"按「{payload.style}」风格改写以下图片中的文字。" or "请解读以下图片并执行相应能力。"},
            {"type": "image_url", "image_url": {"url": payload.image_url}},
        ]

    system = _resolve_style_system(ability, payload.style)

    provider, cfg = _provider_or_fake(db, uid, payload.provider_id)
    req = AiRequest(
        ability=ability,
        content=content,
        system=system,
        content_parts=content_parts,
        temperature=0.4 if ability in {"extract_entities", "memory_distill"} else 0.7,
    )
    resp = provider.invoke(req)
    record_usage(db, uid, ability, resp.usage)

    # memory_distill 落库
    saved_facts = []
    if ability == "memory_distill" and isinstance(resp.data, dict):
        for f in (resp.data.get("facts") or []):
            fact_text = (f.get("fact") or "").strip()
            if not fact_text:
                continue
            cat = (f.get("category") or "other").strip()[:32]
            conf = int(f.get("confidence") or 80)
            row = UserFact(user_id=uid, category=cat, fact=fact_text[:2000],
                           source="ai_distill", confidence=conf)
            db.add(row)
            saved_facts.append({"category": cat, "fact": fact_text, "confidence": conf})
        if saved_facts:
            db.commit()

    provider_name = f"{cfg.provider_key}:{cfg.display_name}" if cfg else "fake"
    return ok({
        "ability": ability,
        "text": resp.text,
        "data": resp.data,
        "usage": resp.usage,
        "provider": provider_name,
        "model": (cfg.model_name if cfg else "fake-1"),
        "saved_facts": saved_facts,
    })


# ============ 语义搜索（RAG 入口） ============
@router.get("/ai/semantic_search")
def ai_semantic_search(
    q: str = Query(..., min_length=1, description="自然语言查询"),
    top_k: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    results = search_semantic(db, uid, q.strip(), top_k=top_k)
    return ok({"query": q, "results": results, "top_k": top_k})


@router.post("/ai/index")
def ai_index_note(
    payload: AiSemanticIndexIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """建立/重建某条笔记的嵌入（幂等）。"""
    uid = current_user["user_id"]
    note = db.query(Note).filter(
        Note.id == payload.note_id, Note.user_id == uid, Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise_http(404, "笔记不存在", 404)
    row = get_or_create_note_embedding(db, uid, note, force=payload.force)
    if not row:
        raise_http(503, "未配置 AI Provider，无法生成嵌入", 503)
    return ok({"note_id": note.id, "model": row.model, "dim": row.dim, "updated_at": row.updated_at.isoformat() if row.updated_at else None})


# ============ 长期记忆 ============
@router.get("/ai/memory")
def ai_memory_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    rows = (
        db.query(UserFact)
        .filter(UserFact.user_id == uid, UserFact.active == True)  # noqa: E712
        .order_by(desc(UserFact.confidence), desc(UserFact.updated_at))
        .all()
    )
    return ok({"list": [
        {
            "id": r.id,
            "category": r.category,
            "fact": r.fact,
            "confidence": r.confidence,
            "source": r.source,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]})


@router.post("/ai/memory/forget")
def ai_memory_forget(
    payload: AiForgetIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    row = db.query(UserFact).filter(
        UserFact.id == payload.fact_id, UserFact.user_id == uid
    ).first()
    if not row:
        raise_http(404, "记忆不存在", 404)
    row.active = False
    db.commit()
    return ok({"ok": True, "id": row.id})


# ============ 用量 ============
@router.get("/ai/usage")
def ai_usage(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return ok(current_month_usage(db, current_user["user_id"]))


# ============ Agent 自动任务 ============
def _save_job_steps(job: AgentJob):
    try:
        job.steps_json = json.dumps(job.steps_json if isinstance(job.steps_json, list) else [],
                                    ensure_ascii=False)
    except Exception:
        pass


@router.post("/ai/agent/start")
def ai_agent_start(
    payload: AiAgentStartIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """启动一个 Agent 任务（pending）。"""
    uid = current_user["user_id"]
    job = AgentJob(
        user_id=uid,
        title=(payload.title or payload.goal[:80])[:255],
        goal=sanitize_text(payload.goal),
        max_steps=max(1, min(payload.max_steps or 8, 20)),
        steps_json="[]",
        status="pending",
    )
    db.add(job); db.commit(); db.refresh(job)
    return ok({"job_id": job.id, "status": job.status, "max_steps": job.max_steps})


@router.get("/ai/agent/{job_id}")
def ai_agent_get(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    job = db.query(AgentJob).filter(AgentJob.id == job_id, AgentJob.user_id == uid).first()
    if not job:
        raise_http(404, "任务不存在", 404)
    try:
        steps = json.loads(job.steps_json or "[]")
    except Exception:
        steps = []
    return ok({
        "id": job.id,
        "title": job.title,
        "goal": job.goal,
        "status": job.status,
        "max_steps": job.max_steps,
        "used_tokens": job.used_tokens,
        "steps": steps,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    })


@router.post("/ai/agent/run")
def ai_agent_run(
    payload: AiAgentRunIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """同步执行一个 Agent 任务（最多 max_steps 步）。阻塞调用 5-30s。"""
    from app.services.ai_providers import _default_tool_executor  # noqa: F401

    uid = current_user["user_id"]
    job = db.query(AgentJob).filter(
        AgentJob.id == payload.job_id, AgentJob.user_id == uid
    ).first()
    if not job:
        raise_http(404, "任务不存在", 404)
    if job.status == "done":
        return ok({"job_id": job.id, "status": "done", "result": job.result})
    if job.status == "failed":
        return ok({"job_id": job.id, "status": "failed", "error": job.error})

    try:
        check_quota(db, uid)
    except RuntimeError as e:
        raise_http(429, str(e), 429)

    try:
        steps = json.loads(job.steps_json or "[]")
    except Exception:
        steps = []
    job.status = "running"
    job.started_at = job.started_at or datetime.now()
    db.commit()

    provider, cfg = _provider_or_fake(db, uid, payload.provider_id)
    is_fake = isinstance(provider, FakeProvider)

    messages = [
        {"role": "system", "content": (
            "你是用户的智能助理，能调用工具替用户操作笔记/任务/搜索/记账。"
            "每步先思考（thought），再决定一个 action。"
            "当目标完成时设 action=finish、done=true；否则继续选下一个 action。"
        )},
        {"role": "user", "content": f"目标：{job.goal}"},
    ]

    finished = False
    last_observation = ""
    final_text = ""
    error = None
    for step_idx in range(1, job.max_steps + 1):
        req = AiRequest(
            ability="agent_step",
            content=f"第 {step_idx} 步。目标：{job.goal}。上一次观察：{last_observation or '（无）'}",
            system=messages[0]["content"],
            tools=AGENT_TOOLS_SCHEMA,
            temperature=0.2,
        )
        try:
            resp = provider.invoke(req)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)[:300]
            break
        record_usage(db, uid, "agent_step", resp.usage)
        # 累计 token
        try:
            job.used_tokens += int(resp.usage.get("total_tokens", 0) or 0) if resp.usage else 0
        except Exception:
            pass

        data = resp.data or {}
        action = (data.get("action") or "").strip()
        is_done = str(data.get("done") or "").lower() == "true"
        thought = (data.get("thought") or "").strip()
        params = data.get("input") or {}

        step_record = {
            "step": step_idx,
            "thought": thought,
            "action": action,
            "input": params,
            "observation": None,
            "text": resp.text,
        }

        if action in ("finish", "", "none") or is_done or is_fake and action == "finish":
            final_text = resp.text or "(完成)"
            step_record["observation"] = "done"
            finished = True
            steps.append(step_record)
            break

        # 真正执行工具
        obs = _default_tool_executor(action, params)
        # 但 default_tool_executor 期望 dict 而非 kwargs，需要把 db/user_id 注入
        if isinstance(obs, dict) and obs.get("ok") is False and obs.get("error", "").startswith("未知工具"):
            obs = {"ok": False, "error": f"工具未实现：{action}"}
        else:
            # 我们需要 db/user_id；重写一遍手工调用
            try:
                fn = globals().get(f"_tool_{action}")
                if fn is None:
                    obs = {"ok": False, "error": f"工具未注册：{action}"}
                else:
                    obs = fn(params, db=db, user_id=uid)
            except Exception as exc:  # noqa: BLE001
                obs = {"ok": False, "error": str(exc)[:300]}

        last_observation = json.dumps(obs, ensure_ascii=False)
        step_record["observation"] = obs
        steps.append(step_record)

    job.steps_json = json.dumps(steps, ensure_ascii=False)
    job.finished_at = datetime.now()
    if error:
        job.status = "failed"
        job.error = error
    elif finished:
        job.status = "done"
        job.result = final_text
    else:
        job.status = "failed"
        job.error = "达 max_steps 上限未完成"
    db.commit()
    return ok({
        "job_id": job.id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "used_tokens": job.used_tokens,
        "step_count": len(steps),
    })


# ============ OCR ============
@router.post("/ai/ocr")
def ai_ocr(
    payload: AiOcrIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """OCR：优先复用高德 OCR（若 key 已配置），否则调多模态 vision 模型（需 provider 支持）。"""
    uid = current_user["user_id"]
    if not payload.image_url:
        raise_http(400, "image_url 必填", 400)

    # 优先：高德 OCR（已在 weather.py 复用 key）
    from app.config import settings
    text = ""
    if settings.AMAP_WEATHER_KEY:
        # 高德官方「图片文字识别」接口（与天气 key 同属一个开发者套餐，多数账号通用）
        try:
            with httpx.Client(timeout=20) as cli:
                r = cli.post(
                    "https://restapi.amap.com/v3/ai/ocr/image",
                    params={"key": settings.AMAP_WEATHER_KEY},
                    json={"url": payload.image_url},
                )
            if r.status_code < 400:
                j = r.json()
                # 高德 OCR 返回 {"words":[{"word":"..."}]} 或 {"result":"..."}
                if "result" in j and isinstance(j["result"], str):
                    text = j["result"]
                elif "words" in j and isinstance(j["words"], list):
                    text = "\n".join([w.get("word", "") for w in j["words"]])
        except Exception as exc:  # noqa: BLE001
            logger.debug("[ocr] amap failed: %s", exc)

    # 兜底：多模态 vision（provider 支持时）
    if not text:
        provider, cfg = _provider_or_fake(db, uid, None)
        if isinstance(provider, FakeProvider):
            return ok({"text": "", "engine": "none", "note": "未配置 OCR/多模态 Provider"})
        req = AiRequest(
            ability="explain",
            content=payload.prompt or "请逐字提取图片中的文字，按原顺序输出，不要解释。",
            content_parts=[
                {"type": "text", "text": payload.prompt or "请逐字提取图片中的文字。"},
                {"type": "image_url", "image_url": {"url": payload.image_url}},
            ],
            temperature=0.0,
        )
        try:
            resp = provider.invoke(req)
            text = (resp.data.get("text") if isinstance(resp.data, dict) else None) or resp.text
        except Exception as exc:  # noqa: BLE001
            raise_http(502, f"OCR 失败：{str(exc)[:200]}", 502)

    return ok({"text": text, "engine": "amap" if settings.AMAP_WEATHER_KEY and text else "vision"})

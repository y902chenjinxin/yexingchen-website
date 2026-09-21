"""AI Provider 抽象层 + FakeProvider + 通用 HTTP Provider。

业务代码只依赖 AiProvider 接口；具体供应商由环境变量切换。
不允许把真实 API Key 写进代码 / 测试 / 前端 / Git。
"""
from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============ 敏感信息过滤 ============
SENSITIVE_PATTERNS = [
    # 常见密码、Token、私钥配置行
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|private[_-]?key)\s*[:=]\s*\S+"),
    # 看起来像 JWT / Bearer Token 的连续字符
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    # 长 hex 串（≥40 字符连续）作为可疑私钥 / token
    re.compile(r"\b[0-9a-fA-F]{40,}\b"),
]


def sanitize_text(text: str) -> str:
    """返回过滤后的文本；命中敏感模式的部分用 [REDACTED] 替换。

    用于：
    - AI 入参清洗；
    - 写入 AiMessage 的 input_scope 摘要；
    - 不在 AiMessage.content 中记录原始 API Key。
    """
    if not text:
        return text
    out = text
    for pat in SENSITIVE_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def sanitize_payload(payload: Any) -> Any:
    """递归清洗 dict / list / str。"""
    if isinstance(payload, str):
        return sanitize_text(payload)
    if isinstance(payload, dict):
        return {k: sanitize_payload(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [sanitize_payload(v) for v in payload]
    return payload


# ============ 数据结构 ============
@dataclass
class AiRequest:
    """单次 AI 调用的入参。"""

    ability: str  # organize / summarize / suggest_tags / suggest_task / stock_analysis / rewrite / explain / extract_entities / memory_distill / agent_plan / agent_step
    content: str
    options: Optional[Dict[str, Any]] = None
    # 可选：覆盖默认"笔记助手"系统提示，用于非笔记场景（如股票研判）
    system: Optional[str] = None
    # 可选：OpenAI 兼容的 tools 列表（function calling schema）；后端会执行工具并二轮调用
    tools: Optional[List[Dict[str, Any]]] = None
    # 可选：内容是多模态 parts 列表（[{"type":"text","text":...},{"type":"image_url",...}]）
    # 若提供此字段则忽略 content
    content_parts: Optional[List[Dict[str, Any]]] = None
    # 可选：覆盖模型默认温度
    temperature: Optional[float] = None


@dataclass
class AiResponse:
    """AI 返回的统一结构。"""

    ability: str
    text: str
    data: Dict[str, Any]
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None  # {"prompt_tokens":..,"completion_tokens":..,"total_tokens":..}
    tool_calls: Optional[List[Dict[str, Any]]] = None  # 模型返回的工具调用（已在本轮被本地执行并回喂）


class AiProvider(ABC):
    """AI 供应商抽象接口。"""

    name: str = "base"

    @abstractmethod
    def invoke(self, req: AiRequest) -> AiResponse: ...


# ============ Fake Provider ============
class FakeProvider(AiProvider):
    """离线 / 测试用假 provider。

    不连接任何外部服务；返回可预测的结果，便于业务层测试与本地开发。
    """

    name = "fake"

    def invoke(self, req: AiRequest) -> AiResponse:
        snippet = (req.content or "").strip()
        title_match = re.search(r"^#\s+(.+)$", snippet, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else (snippet[:20] or "笔记")

        if req.ability == "organize":
            text = f"[fake] 已整理：{title}"
            data = {
                "title": title,
                "summary": f"摘要（fake）：{title}",
                "tags": [title[:4] or "未命名", "工作台"],
            }
        elif req.ability == "summarize":
            text = f"[fake] 摘要：{title}"
            data = {"summary": f"摘要（fake）：{title}"}
        elif req.ability == "suggest_tags":
            text = "[fake] 标签建议"
            data = {"tags": [title[:4] or "未命名", "工作台"]}
        elif req.ability == "suggest_task":
            text = "[fake] 任务建议"
            data = {
                "title": f"跟进：{title}",
                "description": f"来自笔记「{title}」的待办建议（fake）",
            }
        elif req.ability == "finance_csv_import":
            text = "[fake] 已离线解析流水（未连接 AI Provider）"
            data = {"rows": [], "skipped": []}
        elif req.ability == "rewrite":
            text = "[fake] 已改写（未连接 AI Provider）"
            data = {"text": snippet, "diff_ratio": 1.0}
        elif req.ability == "explain":
            text = "[fake] 这是占位解释（未连接 AI Provider）"
            data = {"definition": title, "example": "略", "related": []}
        elif req.ability == "extract_entities":
            text = "[fake] 实体抽取占位（未连接 AI Provider）"
            data = {"people": [], "places": [], "dates": [], "commitments": [], "todos": []}
        elif req.ability == "memory_distill":
            text = "[fake] 记忆蒸馏占位（未连接 AI Provider）"
            data = {"facts": []}
        elif req.ability == "agent_plan":
            text = "[fake] 计划占位（未连接 AI Provider）"
            data = {"steps": [{"id": 1, "intent": "无 AI", "tool": "none", "input": None}]}
        elif req.ability == "agent_step":
            text = "[fake] 一步占位（未连接 AI Provider）"
            data = {"thought": "无", "action": "finish", "input": {}, "done": "true"}
        else:
            text = f"[fake] 未知能力 {req.ability}"
            data = {}

        return AiResponse(
            ability=req.ability,
            text=text,
            data=data,
            provider=self.name,
            model="fake-1",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            tool_calls=[],
        )

    async def stream_chat(self, messages: list, extra=None):
        """原生对话流式输出（异步生成器，逐段产出文本增量）。

        messages: [{"role": "user/assistant/system", "content": "..."}, ...]
        """
        import asyncio

        snippet = (messages[-1].get("content") or "").strip()
        title = snippet[:20] or "对话"
        fake_text = (
            f"（离线演示）我是你的独立 AI 助手。你问：{title}。"
            "配置真实 AI Provider 后可获得真实流式答复。"
        )
        for i in range(0, len(fake_text), 4):
            yield fake_text[i : i + 4]
            await asyncio.sleep(0.02)


# ============ Generic HTTP Provider ============
# 各能力要求模型输出的 JSON schema。reply 字段用于面向用户展示。
_ABILITY_SCHEMAS = {
    "organize": {
        "reply": "整理后的要点中文文本（面向用户，直接可用）",
        "title": "整理后的标题（可为 null）",
        "content": "整理后的正文全文（可为 null）",
        "summary": "一句话摘要（可为 null）",
    },
    "summarize": {
        "reply": "面向用户的摘要中文文本（直接可用，不要 JSON）",
        "summary": "摘要正文",
        "keywords": ["关键词数组，3-6 个"],
    },
    "suggest_tags": {
        "reply": "面向用户的标签建议中文说明",
        "tags": ["推荐标签数组，3-6 个"],
    },
    "suggest_task": {
        "reply": "面向用户的任务建议中文说明",
        "title": "任务标题",
        "description": "任务描述",
    },
    "finance_csv_import": {
        "reply": "给用户的识别结果中文说明（简洁，2~3句）",
        "rows": [
            {"date": "YYYY-MM-DD", "type": "income 或 expense", "category": "分类名", "amount": 12.34, "note": "备注"}
        ],
        "skipped": ["无法识别或无效的一行的简短说明"],
    },
    "stock_analysis": {
        "reply": "面向用户的每日研判中文说明（1~3句，直接可用）",
        "level": "只填一个档位：up(强/偏多)/hold(持/中性偏多)/watch(观/中性)/down(减/偏空)/danger(避/空头)",
        "summary": "该股当日技术形态总结（中文，1~2句）",
        "suggestion": "具体可操作建议（中文，1~2句）",
    },
    # ====== v2.39 新增能力 ======
    "rewrite": {
        # style: casual / formal / concise / emoji / polish / critical
        "reply": "改写后给用户的简短说明（一句话，说清改了什么风格）",
        "text": "改写后的正文（保留原意，仅改变语气/长度/视角）",
        "diff_ratio": "与原文长度的比值，保留 2 位小数（如 0.85）",
    },
    "explain": {
        "reply": "面向用户的解释（自然、口语，3~6 句）",
        "definition": "一句话精确定义（中文）",
        "example": "一个通俗例子（中文，1~2 句）",
        "related": ["相关概念数组，2~5 个"],
    },
    "extract_entities": {
        "reply": "抽取结果简要说明（1~2句）",
        "people": [{"name": "人名", "role": "与用户的关系/角色"}],
        "places": [{"name": "地点"}],
        "dates": [{"value": "YYYY-MM-DD 或自然语言", "context": "上下文"}],
        "commitments": ["承诺/约定列表，2~6 条"],
        "todos": ["待办列表，2~6 条"],
    },
    "memory_distill": {
        # 从最近笔记/对话蒸馏稳定事实
        "reply": "蒸馏简要说明（1~2句）",
        "facts": [
            {"category": "identity|habit|preference|relationship|project|other", "fact": "事实描述", "confidence": 80}
        ],
    },
    "agent_plan": {
        # Agent 第一步：把目标拆成步骤
        "reply": "计划说明（1~2 句）",
        "steps": [
            {"id": 1, "intent": "这一步要做什么", "tool": "create_note|create_task|search_notes|log_finance|none", "input": "调用参数（可为 null）"}
        ],
    },
    "agent_step": {
        # Agent 单步：决定下一步行动
        "reply": "这一步的思考说明",
        "thought": "这一步的内部思考（中文）",
        "action": "create_note|create_task|search_notes|log_finance|finish",
        "input": {"key": "value"},
        "done": "true/false（本步是否完成目标）",
    },
}

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
# 常见思考包裹标记：有些模型即使被要求只输出 JSON，仍会内联思考过程，一律剥除
_REASONING_MARKERS = [
    re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<thought>.*?</thought>", re.DOTALL | re.IGNORECASE),
    re.compile(r"```(?:think|reasoning|分析|思考).*?```", re.DOTALL | re.IGNORECASE),
]


def _strip_reasoning(text: str) -> str:
    out = text or ""
    for pat in _REASONING_MARKERS:
        out = pat.sub("", out)
    return out.strip()


def _extract_json_object(text: str):
    """从模型输出中尽力提取一个 JSON 对象（dict），失败返回 None。"""
    if not text:
        return None
    cleaned = _strip_reasoning(text)
    if not cleaned:
        return None
    m = _JSON_FENCE_RE.search(cleaned)
    candidate = m.group(1).strip() if m else cleaned
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end <= start:
        return None
    candidate = candidate[start : end + 1]
    try:
        obj = json.loads(candidate)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return _try_balanced_json(candidate)


def _try_balanced_json(text: str):
    """朴素的花括号配对解析，容忍模型输出夹杂噪声后仍能捞出第一个完整 JSON 对象。"""
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    obj = json.loads(text[start : i + 1])
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    pass
    return None


class HttpProvider(AiProvider):
    """通用 OpenAI 兼容 HTTP Provider。

    通过环境变量配置：
    - AI_PROVIDER=http
    - AI_BASE_URL=https://api.example.com
    - AI_MODEL=gpt-x
    - AI_API_KEY=***
    - AI_TIMEOUT=30
    """

    name = "http"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        timeout: int = 30,
    ):
        if not base_url or not model or not api_key:
            raise ValueError("HttpProvider requires base_url, model, api_key")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def _build_prompt(self, req: AiRequest) -> str:
        ability = req.ability
        content = sanitize_text(req.content or "")
        schema = json.dumps(
            _ABILITY_SCHEMAS.get(ability, {}), ensure_ascii=False, indent=2
        )
        if req.system:
            # 非笔记场景（如股票研判）使用调用方给定角色/原则
            intro = req.system
        else:
            intro = "你是用户的贴心笔记助手，陪他整理生活和工作。"
        return (
            f"{intro}请只输出一个有效的 JSON 对象，"
            "不要输出任何其它内容。\n"
            "输出 JSON 的绝对原则：\n"
            "1. 只输出 JSON 本身，前面不要任何解释、思考过程、逐字推断；"
            "不要包裹 markdown 代码块（不要用 ```）；不要用 <thinking> 等任何标记。\n"
            "2. reply 字段是直接展示给用户看的中文本体：语气要自然、温暖、口语化，"
            "像好朋友在说话，不说官腔、不用生硬书面语。\n"
            "3. reply 必须紧扣输入内容，简洁地说清结果（一般 2~4 句），"
            "不要复述或大段引用原文，不要堆砌空话，能一句话讲清就不要三句。\n"
            "4. 其它字段严格按给定 schema 填充，缺失用 null 或空数组，不要乱加字段。\n"
            f"能力：{ability}\n"
            f"schema：\n{schema}\n"
            f"待研判内容：\n{content}\n"
        )

    def _build_messages(self, req: AiRequest, prompt: str):
        """构造 OpenAI 兼容的 messages。支持 content_parts（多模态）。"""
        if req.content_parts:
            return [{"role": "user", "content": req.content_parts}]
        return [{"role": "user", "content": prompt}]

    def _post_chat(self, messages, *, tools=None, temperature=None):
        """调一次 /v1/chat/completions，返回 (data_dict, last_err_str)。"""
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("缺少 httpx，无法使用 HttpProvider") from exc
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        url = f"{base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload_base = {"model": self.model, "messages": messages}
        if temperature is not None:
            payload_base["temperature"] = temperature
        if tools:
            payload_base["tools"] = tools
            payload_base["tool_choice"] = "auto"

        attempts = [
            # 优先 JSON 模式
            {**payload_base, "response_format": {"type": "json_object"}},
            payload_base,
        ]
        data = None
        last_err = None
        for payload in attempts:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    r = client.post(url, json=payload, headers=headers)
                if r.status_code < 400:
                    return r.json(), None
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
        return None, last_err or "AI provider 调用失败"

    def _extract_usage(self, data):
        u = (data or {}).get("usage") or {}
        try:
            return {
                "prompt_tokens": int(u.get("prompt_tokens", 0) or 0),
                "completion_tokens": int(u.get("completion_tokens", 0) or 0),
                "total_tokens": int(u.get("total_tokens", 0) or 0),
            }
        except Exception:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _postprocess(self, content: str, ability: str):
        """从模型输出里提 JSON 与最终给用户的文本。"""
        obj = _extract_json_object(content)
        scrubbed = _strip_reasoning(content)
        if isinstance(obj, dict):
            reply = obj.get("reply")
            if reply in (None, "") and obj:
                reply = next(
                    (
                        str(v).strip()
                        for v in obj.values()
                        if isinstance(v, str)
                        and v.strip()
                        and v.strip().lower() != "null"
                        and not v.strip().startswith(("面向用户", "整理后的"))
                    ),
                    "",
                )
            structured = {k: v for k, v in obj.items() if k != "reply"}
            text = str(reply).strip() if reply not in (None, "") else scrubbed
            text = text or "（AI 未返回可展示的文本）"
        else:
            text = scrubbed or "（AI 未返回有效结果）"
            structured = {}
        text = _remove_embedded_json(text)
        text = _polish_readable(text, scrubbed or content)
        return text, structured

    def invoke(self, req: AiRequest) -> AiResponse:
        prompt = self._build_prompt(req)
        messages = self._build_messages(req, prompt)
        data, err = self._post_chat(messages, tools=req.tools, temperature=req.temperature)
        if data is None:
            raise RuntimeError(err or "AI provider 调用失败")
        usage_total = dict(self._extract_usage(data))
        tool_calls_done: list = []

        # ---- 工具调用循环：模型若返回 tool_calls，本地执行后回喂 messages 再调一次 ----
        # 最多 3 轮，防止无限循环。
        for _ in range(3):
            message = (data.get("choices", [{}])[0].get("message", {}) or {})
            tcalls = message.get("tool_calls")
            if not tcalls:
                break
            tool_msgs = []
            for tc in tcalls:
                fn = (tc.get("function") or {})
                name = fn.get("name") or ""
                args_raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                except Exception:
                    args = {}
                tool_calls_done.append({"name": name, "arguments": args})
                # 真实执行委托给 _ToolExecutor；缺则返回友好提示
                obs = _default_tool_executor(name, args)
                tool_msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or "",
                    "content": json.dumps(obs, ensure_ascii=False),
                })
            # 把 assistant 决策 + tool 结果回喂
            followup = list(messages) + [message] + tool_msgs
            data, err = self._post_chat(followup, tools=req.tools, temperature=req.temperature)
            if data is None:
                raise RuntimeError(err or "AI provider 调用失败（tool followup）")
            u = self._extract_usage(data)
            for k in usage_total:
                usage_total[k] += u.get(k, 0)

        # ---- 后处理（取最终给用户的文本与结构化字段）----
        message = (data.get("choices", [{}])[0].get("message", {}) or {})
        content = (message.get("content") or "").strip()
        text, structured = self._postprocess(content, req.ability)
        return AiResponse(
            ability=req.ability,
            text=text,
            data=structured,
            provider=self.name,
            model=self.model,
            usage=usage_total,
            tool_calls=tool_calls_done,
        )

    async def stream_chat(self, messages: list, extra=None):
        """原生多轮对话流式输出（异步生成器）。

        messages: [{"role": "user/assistant/system", "content": "..."}, ...]
        采用 SSE 逐段读取 delta.content 并产出文本增量。
        """
        try:
            import httpx  # 延迟导入
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("缺少 httpx，无法使用 HttpProvider") from exc

        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        url = f"{base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "messages": messages, "stream": True}
        if extra:
            payload.update(extra)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as r:
                if r.status_code >= 400:
                    body = (await r.aread()).decode(errors="ignore")
                    raise RuntimeError(f"AI provider HTTP {r.status_code}: {body[:300]}")
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        obj = json.loads(data)
                    except Exception:
                        continue
                    delta = (obj.get("choices") or [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield delta


def _remove_embedded_json(text: str) -> str:
    """若文本里混了一段 {...} JSON（模型有时把 JSON 塞进 reply 字段），剥掉 JSON，只留前面的自然句。"""
    c = (text or "").strip()
    i = c.find("{")
    if i == -1:
        return c
    j = c.rfind("}")
    if j <= i:
        return c
    pre = c[:i].rstrip("，。；、\n\t ")
    return pre or ""


def _polish_readable(candidate: str, fallback: str) -> str:
    """若候选文本仍是被剥壳的 JSON，则从中拼出可读的纯文本；否则原样返回。"""
    c = (candidate or "").strip()
    if not c or not (c.startswith("{") and "}" in c):
        return c
    obj = _extract_json_object(c)
    if not isinstance(obj, dict):
        return fallback or ""
    pieces = []
    for k, v in obj.items():
        if isinstance(v, str) and v.strip() and v.strip().lower() != "null":
            pieces.append(str(v).strip())
        elif isinstance(v, list):
            texts = [str(x) for x in v if isinstance(x, str) and x.strip()]
            if texts:
                pieces.append("、".join(texts[:6]))
    return "；".join(pieces)[:800] or (fallback or "")


# ============ 工具执行注册表 ============
# 默认实现：注册一些开箱即用工具，路由层可覆写。
# 入参：tool_name (str) + args (dict)；返回 dict（被 JSON 序列化进 messages.tool role）
_TOOL_EXECUTORS: Dict[str, Any] = {}


def register_tool_executor(name: str):
    """装饰器：注册工具名 → 可调用对象 (args: dict) -> dict。"""

    def deco(fn):
        _TOOL_EXECUTORS[name] = fn
        return fn

    return deco


def set_tool_executor(name: str, fn):
    """运行时注入工具实现（路由层用）。"""
    _TOOL_EXECUTORS[name] = fn


def _default_tool_executor(name: str, args: dict) -> dict:
    fn = _TOOL_EXECUTORS.get(name)
    if fn is None:
        return {"ok": False, "error": f"未知工具：{name}"}
    try:
        return fn(args or {})
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}


# ============ Provider 工厂 ============
def get_provider() -> AiProvider:
    """根据环境变量选择 provider。

    - AI_PROVIDER=fake 或未设置 → FakeProvider（默认安全）
    - AI_PROVIDER=http 且配置完整 → HttpProvider
    """
    provider = os.environ.get("AI_PROVIDER", "fake").strip().lower()
    if provider == "http":
        base = os.environ.get("AI_BASE_URL", "").strip()
        model = os.environ.get("AI_MODEL", "").strip()
        key = os.environ.get("AI_API_KEY", "").strip()
        timeout = int(os.environ.get("AI_TIMEOUT", "30") or 30)
        if not (base and model and key):
            logger.warning("AI_PROVIDER=http 但配置不完整，回退到 FakeProvider")
            return FakeProvider()
        return HttpProvider(base_url=base, model=model, api_key=key, timeout=timeout)
    return FakeProvider()


# ============ 业务能力封装 ============
def organize_note(content: str) -> AiResponse:
    return get_provider().invoke(AiRequest(ability="organize", content=content))


def summarize_note(content: str) -> AiResponse:
    return get_provider().invoke(AiRequest(ability="summarize", content=content))


def suggest_tags(content: str) -> AiResponse:
    return get_provider().invoke(AiRequest(ability="suggest_tags", content=content))


def suggest_task(content: str) -> AiResponse:
    return get_provider().invoke(AiRequest(ability="suggest_task", content=content))


def preview_input_scope(content: str, ability: str) -> Dict[str, Any]:
    """生成发送给 AI 的内容预览摘要。"""
    cleaned = sanitize_text(content or "")
    return {
        "ability": ability,
        "char_count": len(cleaned),
        "preview": cleaned[:200],
        "has_more": len(cleaned) > 200,
        "sensitive_redacted": cleaned != (content or ""),
    }

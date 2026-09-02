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

    ability: str  # organize / summarize / suggest_tags / suggest_task
    content: str
    options: Optional[Dict[str, Any]] = None


@dataclass
class AiResponse:
    """AI 返回的统一结构。"""

    ability: str
    text: str
    data: Dict[str, Any]
    provider: str
    model: str


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
        else:
            text = f"[fake] 未知能力 {req.ability}"
            data = {}

        return AiResponse(
            ability=req.ability,
            text=text,
            data=data,
            provider=self.name,
            model="fake-1",
        )


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
        return (
            "你是用户的贴心笔记助手，陪他整理生活和工作。请只输出一个有效的 JSON 对象，"
            "不要输出任何其它内容。\n"
            "输出 JSON 的绝对原则：\n"
            "1. 只输出 JSON 本身，前面不要任何解释、思考过程、逐字推断；"
            "不要包裹 markdown 代码块（不要用 ```）；不要用 <thinking> 等任何标记。\n"
            "2. reply 字段是直接展示给用户看的中文本体：语气要自然、温暖、口语化，"
            "像好朋友在说话，不说官腔、不用生硬书面语。\n"
            "3. reply 必须紧扣笔记本身，简洁地说清结果（一般 2~4 句），"
            "不要复述或大段引用笔记原文，不要堆砌空话，能一句话讲清就不要三句。\n"
            "4. 其它字段严格按给定 schema 填充，缺失用 null 或空数组，不要乱加字段。\n"
            f"能力：{ability}\n"
            f"schema：\n{schema}\n"
            f"笔记内容：\n{content}\n"
        )

    def invoke(self, req: AiRequest) -> AiResponse:
        try:
            import httpx  # 延迟导入
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("缺少 httpx，无法使用 HttpProvider") from exc

        prompt = self._build_prompt(req)
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        url = f"{base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = [{"role": "user", "content": prompt}]

        # 优先请求仅 JSON 输出；部分 OpenAI 兼容端点不支持 response_format，则回退普通请求
        attempts = [
            {
                "model": self.model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            {"model": self.model, "messages": messages},
        ]
        data = None
        last_err = None
        for payload in attempts:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    r = client.post(url, json=payload, headers=headers)
                if r.status_code < 400:
                    data = r.json()
                    break
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
        if data is None:
            raise RuntimeError(last_err or "AI provider 调用失败")

        message = (data.get("choices", [{}])[0].get("message", {}) or {})
        content = (message.get("content") or "").strip()
        # 推理模型可能把过程放在 reason_content / 或内联进 content，这里统一剥除，只留最终答案
        obj = _extract_json_object(content)
        scrubbed = _strip_reasoning(content)
        if isinstance(obj, dict):
            reply = obj.get("reply")
            if reply in (None, "") and obj:
                # reply 缺失时，抓取任一可读字符串字段当作给用户的文本，避免把整个 JSON 结构漏给界面
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
        # 兜底：剥掉可能内嵌在 reply 里的 JSON 块；若文本里仍残留 JSON 结构痕迹，转为可读摘要
        text = _remove_embedded_json(text)
        text = _polish_readable(text, scrubbed or content)
        # 结构化结果解析失败时宁可为空（apply 会明确报缺字段），也不把原始文本回传污染界面
        return AiResponse(
            ability=req.ability,
            text=text,
            data=structured,
            provider=self.name,
            model=self.model,
        )


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

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
        return (
            f"请按能力 {ability} 处理以下内容（仅返回 JSON，键名固定）：\n"
            f"{content}"
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
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"AI provider HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                or ""
            )
            return AiResponse(
                ability=req.ability,
                text=text,
                data={"raw": text},
                provider=self.name,
                model=self.model,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("HttpProvider invoke failed: %s", exc)
            raise


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

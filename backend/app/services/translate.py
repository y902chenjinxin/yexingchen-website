"""免费翻译端点模块（中文资讯展示用）。

策略（机房实测连通性排序）：
1. MyMemory（api.mymemory.translated.net，本机可达，免费 ~5 万字符/天/IP，无需 key）
2. Google gtx（translate.googleapis.com，本机被墙，保留作后备）
失败则返回原文（不抛错，保证抓取/阅读流程不中断）。

调用方约束：
- 标题/摘要自动翻译：抓取时对 is_foreign 文章翻译标题与摘要（≤1200 字摘要）
- 正文按需翻译：阅读器点「翻译全文」→ POST /api/feeds/articles/{id}/translate 缓存入库
- 内存 TTL 缓存降低重复调用；线程锁避免并发重复请求。
"""
from __future__ import annotations

import re
import threading
import time
import urllib.parse
import urllib.request

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# 内存缓存 {文本哈希: (译文, 过期时间戳)}
_MEMO: dict[str, tuple[str, float]] = {}
_MEMO_TTL = 12 * 3600  # 12 小时
_MEMO_MAX = 3000
_LOCK = threading.Lock()

# 单次请求最大字符（MyMemory 免费接口限制 ~500 字符/请求）
_CHUNK = 450
_MAX_INPUT = 12000  # 正文翻译输入上限（超出截断）


def is_cjk(text: str, ratio: float = 0.15) -> bool:
    """判断文本是否以中文为主（CJK 字符占比 >= ratio）。"""
    if not text:
        return False
    total = 0
    cjk = 0
    for ch in text:
        if ch.isalnum():
            total += 1
            if CJK_RE.match(ch):
                cjk += 1
    if total == 0:
        return False
    return (cjk / total) >= ratio


def _memo_get(key: str) -> str | None:
    now = time.time()
    with _LOCK:
        hit = _MEMO.get(key)
        if hit and hit[1] > now:
            return hit[0]
        if hit:
            _MEMO.pop(key, None)
    return None


def _memo_set(key: str, value: str) -> None:
    with _LOCK:
        if len(_MEMO) >= _MEMO_MAX:
            # 简单淘汰：清掉最旧一半
            items = sorted(_MEMO.items(), key=lambda kv: kv[1][1])
            for k, _ in items[: _MEMO_MAX // 2]:
                _MEMO.pop(k, None)
        _MEMO[key] = (value, time.time() + _MEMO_TTL)


def _call_endpoint(url: str, timeout: float = 10.0) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; yexingchen-translate/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _translate_mymemory(text: str) -> str | None:
    q = urllib.parse.quote(text)
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en%7Czh-CN"
    raw = _call_endpoint(url)
    import json

    data = json.loads(raw)
    out = ((data.get("responseData") or {}).get("translatedText") or "").strip()
    return out or None


def _translate_google(text: str) -> str | None:
    q = urllib.parse.quote(text)
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
    )
    raw = _call_endpoint(url, timeout=5)
    import json

    parts = json.loads(raw)[0]
    return "".join(p[0] for p in parts if p and p[0]) or None


def translate_text(text: str) -> str:
    """把一段外文翻译为中文；失败返回原文。"""
    text = (text or "").strip()
    if not text or is_cjk(text):
        return text
    text = text[:_MAX_INPUT]
    key = f"t:{text}"
    cached = _memo_get(key)
    if cached is not None:
        return cached

    chunks = [text[i : i + _CHUNK] for i in range(0, len(text), _CHUNK)]
    translated: list[str] = []
    ok = False
    for chunk in chunks:
        out = None
        for fn in (_translate_mymemory, _translate_google):
            try:
                out = fn(chunk)
                if out:
                    ok = True
                    break
            except Exception:  # noqa: BLE001
                continue
        translated.append(out if out else chunk)

    result = "".join(translated)
    if ok:
        _memo_set(key, result)
        return result
    return text


def translate_title(title: str) -> str:
    """标题翻译（单次，最多 500 字符）。"""
    t = (title or "").strip()
    if not t or is_cjk(t):
        return t
    return translate_text(t[:500])


def translate_summary(summary: str) -> str:
    """摘要翻译（截断 1200 字）。"""
    t = (summary or "").strip()
    if not t or is_cjk(t):
        return t
    return translate_text(t[:1200])


def translate_content(content: str) -> str:
    """正文翻译（截断 12000 字符，返回译文或原文）。"""
    t = (content or "").strip()
    if not t or is_cjk(t):
        return t
    return translate_text(t)

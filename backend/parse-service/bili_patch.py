"""B 站解析补丁（v2.46.169）

问题：B 站对 api.bilibili.com 的风控要求请求携带 buvid3 Cookie。
     只带 User-Agent + Referer 会直接返回 **HTTP 412**，
     而 parse-video-py 0.0.3 的 BiliBili.get_default_headers() 恰好没带 Cookie
     （源码里那行 Cookie 是注释掉的），导致 B 站链接 100% 解析失败。

实测（服务器上 curl）：
    仅 UA + Referer            → 412
    再加 Cookie: buvid3=...    → 200 + 正常 JSON

做法：给 BiliBili.get_default_headers 打补丁，注入 buvid3。
      buvid3 从官方 https://api.bilibili.com/x/frontend/finger/spi 取（b_3 字段），
      6 小时刷新一次；取不到时用格式合法的固定值兜底（B 站只校验存在与格式）。
"""
import logging
import time

import httpx
from parse_video_py.parser.bilibili import BiliBili

log = logging.getLogger(__name__)

_UA = BiliBili.USER_AGENT
_buvid3 = ""
_refreshed_at = 0.0
_TTL = 6 * 3600
# 兜底值：格式合法即可通过 B 站的存在性校验
_FALLBACK = "8F1A2B3C-1234-4A5B-9C8D-1234567890ABinfoc"


async def refresh_buvid3(force: bool = False) -> str:
    """取（或复用）buvid3，失败时回落固定值，保证请求始终带 Cookie。"""
    global _buvid3, _refreshed_at
    if not force and _buvid3 and time.time() - _refreshed_at < _TTL:
        return _buvid3
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            resp = await cli.get(
                "https://api.bilibili.com/x/frontend/finger/spi",
                headers={"User-Agent": _UA},
            )
            data = (resp.json() or {}).get("data") or {}
            b3 = data.get("b_3") or ""
        if b3:
            _buvid3 = b3
            _refreshed_at = time.time()
            log.info("buvid3 refreshed: %s...", b3[:8])
    except Exception as exc:  # 网络异常不应阻断解析
        log.warning("refresh buvid3 failed: %s", exc)
    if not _buvid3:
        _buvid3 = _FALLBACK
    return _buvid3


def install() -> None:
    """替换 get_default_headers，使其带上 buvid3 Cookie。"""
    original = BiliBili.get_default_headers

    def patched(self):
        headers = original(self)
        if _buvid3:
            headers["Cookie"] = f"buvid3={_buvid3}"
        return headers

    BiliBili.get_default_headers = patched
    log.info("BiliBili cookie patch installed")

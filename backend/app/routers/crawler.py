"""爬虫工具（v2.46.120）：通用网页抓取 + 小说下载（番茄/起点）+ 精校导出。

合规边界（写进前端提示与这里）：
- 仅抓取**公开可访问**的内容；付费/登录/加密章节一律标注 paywalled 跳过，不做任何绕过；
- 服务端限制：仅 http/https、禁内网地址（SSRF）、单页 ≤3MB、超时 15s、章节间限速；
- 提示用户遵守目标站 robots.txt 与版权，抓取数据仅限个人使用。

通用抓取模式：text（正文纯文本）/ links / images / tables / html。
小说适配器：fanqie（番茄 fanqienovel.com，SSR JSON 友好）、qidian（起点，
免费章节 DOM 提取，VIP/混淆章节如实标注失败）。auto 按 host 识别。
精校（polish）：去广告噪声行 / NFKC 规范化 / 段落规整，纯规则无外部服务。
"""
import ipaddress
import json
import re
import socket
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.schemas.common import ResponseBase
from app.utils.security import get_current_user
from app.services.log_service import log_action

router = APIRouter(prefix="/api/crawler", tags=["爬虫工具"])

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MAX_BYTES = 3 * 1024 * 1024
TIMEOUT = 15.0
CHAPTER_GAP = 0.35  # 章节间限速秒

_NOISE_PATTERNS = [
    r"请记住本书首发域名[^\s]*", r"最新章节[！!。]?", r"^\s*[（(]?章节未?完[，,]?点击下一页[）)]?\s*$",
    r"[一-龥]{0,6}小说网?[^\s]{0,20}欢迎您", r"w{3}\.[\w.-]+", r"^[（(]?记住本站地址[）)]?",
    r"^本章完$", r"^\(本章完\)$", r"天才一秒记住[^\s]*", r"拉到书页底部[^\s]*",
    r"^求收藏[，,]求推荐票[！!。]?\s*$", r"^求月票[，,]求订阅[！!。]?\s*$",
    r"[（(]?未完待续[）)]?\s*$", r"笔趣阁[^\s]{0,10}", r"^手机用户请浏览阅读[^\s]*",
]
_NOISE_RE = [re.compile(p) for p in _NOISE_PATTERNS]


# ---------------------------------------------------------------- SSRF 防护
def _assert_public_host(url: str) -> None:
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        raise ValueError("仅支持 http/https")
    host = u.hostname or ""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as e:
        raise ValueError(f"域名解析失败：{host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise ValueError(f"目标解析到内网/保留地址（{ip}），已拦截")


def _fetch(url: str) -> str:
    _assert_public_host(url)
    got = 0
    chunks = []
    with httpx.Client(headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
                      timeout=TIMEOUT, follow_redirects=True) as cli:
        with cli.stream("GET", url) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype and "json" not in ctype and "text" not in ctype:
                raise ValueError(f"不支持的内容类型：{ctype.split(';')[0]}")
            for chunk in resp.iter_bytes(65536):
                got += len(chunk)
                if got > MAX_BYTES:
                    raise ValueError("页面超过 3MB 上限，已截断")
                chunks.append(chunk)
    for enc in ("utf-8", "gb18030"):
        try:
            return b"".join(chunks).decode(enc)
        except UnicodeDecodeError:
            continue
    return b"".join(chunks).decode("utf-8", "ignore")


# ---------------------------------------------------------------- 通用提取
def _extract(html: str, mode: str, base: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    if mode == "html":
        return {"html": str(soup)[:MAX_BYTES]}
    if mode == "links":
        seen, out = set(), []
        for a in soup.find_all("a", href=True):
            href, txt = a["href"], a.get_text(" ", strip=True)[:120]
            if href.startswith("//"):
                href = "https:" + href
            if href.startswith("#") or href in seen:
                continue
            seen.add(href)
            out.append({"href": href, "text": txt})
        return {"links": out[:2000], "total": len(out)}
    if mode == "images":
        out = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src.startswith("//"):
                src = "https:" + src
            if src.startswith("data:"):
                continue
            out.append({"src": src, "alt": (img.get("alt") or "")[:100]})
        return {"images": out[:1000], "total": len(out)}
    if mode == "tables":
        tables = []
        for tb in soup.find_all("table"):
            rows = []
            for tr in tb.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows[:500])
        return {"tables": tables[:20]}
    # text：优先语义正文，兜底全文本
    art = (soup.find("article") or soup.find("main")
           or soup.find(id="content") or soup.find(class_=re.compile("content|article|read", re.I)))
    text = (art or soup).get_text("\n", strip=True)
    return {"text": text[:200_000], "title": (soup.title.get_text(strip=True) if soup.title else "")}


class FetchIn(BaseModel):
    url: str
    mode: str = "text"  # text|links|images|tables|html


@router.post("/fetch", response_model=ResponseBase)
async def crawler_fetch(body: FetchIn, current_user: dict = Depends(get_current_user)):
    try:
        html = _fetch(body.url)
    except ValueError as e:
        return ResponseBase(code=1, msg=str(e))
    except httpx.HTTPStatusError as e:
        return ResponseBase(code=1, msg=f"目标返回 {e.response.status_code}")
    except Exception as e:  # noqa: BLE001
        return ResponseBase(code=1, msg=f"抓取失败：{e}")
    mode = body.mode if body.mode in ("text", "links", "images", "tables", "html") else "text"
    await log_action(current_user.get("id"), "crawler.fetch", body.url)
    return ResponseBase(data=_extract(html, mode, body.url))


# ---------------------------------------------------------------- 小说适配器
def _detect_source(url: str) -> str:
    if "fanqienovel" in url:
        return "fanqie"
    if "qidian" in url:
        return "qidian"
    return "unknown"


def _book_id(url: str) -> str:
    m = (re.search(r"/page/(\d+)", url) if "fanqie" in url else re.search(r"/book/(\d+)", url))
    return m.group(1) if m else ""


def _fanqie_outline(url: str) -> dict:
    bid = _book_id(url)
    if not bid:
        raise ValueError("番茄目录页地址形如 https://fanqienovel.com/page/<书籍ID>")
    detail = _fetch(f"https://fanqienovel.com/page/{bid}")
    soup = BeautifulSoup(detail, "html.parser")
    title = (soup.find("h1") or soup.find("div", class_=re.compile("title"))).get_text(strip=True) if soup.find("h1") else ""
    meta = soup.get_text(" ", strip=True)[:400]
    author = ""
    m = re.search(r"作者[：:]\s*([^\s]{1,30})", meta)
    if m:
        author = m.group(1)
    api = _fetch(f"https://fanqienovel.com/api/reader/directory/detail?bookId={bid}")
    data = json.loads(api).get("data", {})
    chapters = []
    for vol in data.get("chapterListWithVolume", []) or []:
        for it in vol.get("chapterList", []) or []:
            chapters.append({"title": it.get("title", ""), "url": f"https://fanqienovel.com/reader/{it.get('item_id', it.get('chapterId', ''))}",
                             "paywalled": bool(it.get("need_pay") or it.get("is_paid"))})
    if not chapters:
        for it in data.get("chapterList", []) or []:
            chapters.append({"title": it.get("title", ""), "url": f"https://fanqienovel.com/reader/{it.get('item_id', '')}",
                             "paywalled": bool(it.get("need_pay"))})
    return {"source": "fanqie", "book_id": bid, "title": title or "番茄小说", "author": author, "chapters": chapters}


def _qidian_outline(url: str) -> dict:
    bid = _book_id(url)
    if not bid:
        raise ValueError("起点目录页地址形如 https://www.qidian.com/book/<书籍ID>/")
    html = _fetch(f"https://www.qidian.com/book/{bid}/")
    soup = BeautifulSoup(html, "html.parser")
    title = soup.h1.get_text(strip=True) if soup.h1 else ""
    info = soup.get_text(" ", strip=True)[:600]
    author = ""
    m = re.search(r"作者[：:]\s*([^\s·]{1,30})", info)
    if m:
        author = m.group(1)
    chapters = []
    catalog = soup.find(id="catalog") or soup.find(class_=re.compile("catalog"))
    if catalog:
        for a in catalog.find_all("a", href=True):
            href = a["href"]
            if href.startswith("//"):
                href = "https:" + href
            if "/chapter/" not in href and "book/" not in href:
                continue
            chapters.append({"title": a.get_text(strip=True)[:80], "url": href, "paywalled": "vip" in href})
    return {"source": "qidian", "book_id": bid, "title": title or "起点小说", "author": author, "chapters": chapters}


class OutlineIn(BaseModel):
    url: str


@router.post("/novel/outline", response_model=ResponseBase)
async def novel_outline(body: OutlineIn, current_user: dict = Depends(get_current_user)):
    src = _detect_source(body.url)
    try:
        if src == "fanqie":
            data = _fanqie_outline(body.url)
        elif src == "qidian":
            data = _qidian_outline(body.url)
        else:
            return ResponseBase(code=1, msg="暂只识别番茄（fanqienovel.com）与起点（qidian.com）目录页")
    except ValueError as e:
        return ResponseBase(code=1, msg=str(e))
    except Exception as e:  # noqa: BLE001
        return ResponseBase(code=1, msg=f"目录解析失败：{e}")
    return ResponseBase(data=data)


def _fanqie_chapter(url: str) -> dict:
    html = _fetch(url)
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    content, title = "", ""
    if m:
        try:
            data = json.loads(m.group(1))
            ch = (data.get("reader", {}) or {}).get("chapterData", {}) or {}
            content = ch.get("content") or ""
            title = ch.get("title") or ""
        except Exception:  # noqa: BLE001
            pass
    if not content:
        soup = BeautifulSoup(html, "html.parser")
        art = soup.find(class_=re.compile("muye-reader-content|chapter-content|reader-content"))
        if art:
            content = art.decode_contents()
            t = soup.find("h1")
            title = t.get_text(strip=True) if t else title
    if not content:
        return {"title": title, "content": "", "paywalled": True, "note": "未取到正文（可能为付费/受限章节）"}
    return {"title": title, "content": content, "paywalled": False}


def _qidian_chapter(url: str) -> dict:
    html = _fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.find("h1") or soup.find("h3"))
    title = title.get_text(strip=True) if title else ""
    art = soup.find(class_=re.compile("read-content|j_readContent|main-text-wrap"))
    if art and len(art.get_text(strip=True)) > 60:
        return {"title": title, "content": art.decode_contents(), "paywalled": False}
    text = soup.get_text(" ", strip=True)
    if re.search(r"起点中文网欢迎您|登录|立即订阅|本章未解锁|订阅本章", text) and not art:
        return {"title": title, "content": "", "paywalled": True, "note": "付费/需登录章节，按合规跳过"}
    return {"title": title, "content": "", "paywalled": True, "note": "正文被反爬保护或结构变化，未取到"}


class ChaptersIn(BaseModel):
    source: str                 # fanqie | qidian
    items: list[dict]           # [{title, url, paywalled}]
    polish: bool = True


def polish_text(raw: str) -> str:
    """精校：去广告噪声 / NFKC / 段落规整。输入可为 HTML 片段。"""
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    text = re.sub(r"</p>\s*<p[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    import html as _h
    text = _h.unescape(text)
    import unicodedata
    text = unicodedata.normalize("NFKC", text)
    lines = []
    for ln in text.splitlines():
        ln = ln.replace("\u3000", " ").strip()
        if not ln:
            lines.append("")
            continue
        if any(p.search(ln) for p in _NOISE_RE):
            continue
        lines.append(ln)
    # 压缩 3+ 连续空行 → 1 空行；去首尾空行
    out, blank = [], 0
    for ln in lines:
        blank = blank + 1 if not ln else 0
        if blank <= 1:
            out.append(ln)
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


@router.post("/novel/chapters", response_model=ResponseBase)
async def novel_chapters(body: ChaptersIn, current_user: dict = Depends(get_current_user)):
    if len(body.items) > 60:
        return ResponseBase(code=1, msg="单批最多 60 章（避免请求轰炸目标站），可分批抓取")
    fn = _fanqie_chapter if body.source == "fanqie" else _qidian_chapter
    out, ok = [], 0
    for it in body.items:
        if it.get("paywalled"):
            out.append({"title": it.get("title", ""), "content": "", "paywalled": True, "note": "付费章节，跳过"})
            continue
        try:
            ch = fn(it["url"])
            content = polish_text(ch.get("content") or "") if (body.polish and ch.get("content")) else ch.get("content") or ""
            out.append({"title": ch.get("title") or it.get("title", ""), "content": content,
                        "paywalled": ch.get("paywalled", False), "note": ch.get("note", "")})
            if content:
                ok += 1
        except Exception as e:  # noqa: BLE001
            out.append({"title": it.get("title", ""), "content": "", "paywalled": False, "note": f"抓取失败：{e}"})
        time.sleep(CHAPTER_GAP)
    await log_action(current_user.get("id"), "crawler.novel.chapters", f"{body.source} ok={ok}/{len(out)}")
    return ResponseBase(data={"list": out, "ok": ok, "total": len(out)})


class ExportIn(BaseModel):
    title: str = "未命名小说"
    author: str = ""
    chapters: list[dict]        # [{title, content}]
    fmt: str = "txt"            # txt | md


@router.post("/novel/export")
async def novel_export(body: ExportIn, current_user: dict = Depends(get_current_user)):
    safe = re.sub(r"[\\/:*?\"<>|]", "_", body.title)[:60]
    if body.fmt == "md":
        parts = [f"# {body.title}", f"> 作者：{body.author or '未知'}", ""]
        for i, ch in enumerate(body.chapters, 1):
            parts.append(f"## 第{i}章 {ch.get('title', '')}")
            parts.append(ch.get("content") or "（付费章节，未收录）")
            parts.append("")
        fname, mime, payload = f"{safe}.md", "text/markdown; charset=utf-8", "\n".join(parts)
    else:
        parts = [f"书名：{body.title}", f"作者：{body.author or '未知'}", "=" * 30, ""]
        for i, ch in enumerate(body.chapters, 1):
            parts.append(f"第{i}章 {ch.get('title', '')}")
            parts.append(ch.get("content") or "（付费章节，未收录）")
            parts.append("")
        fname, mime, payload = f"{safe}.txt", "text/plain; charset=utf-8", "\n".join(parts)
    await log_action(current_user.get("id"), "crawler.novel.export", f"{body.title} {len(body.chapters)}章")
    from urllib.parse import quote
    return StreamingResponse(
        iter([payload.encode("utf-8")]), media_type=mime,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"},
    )

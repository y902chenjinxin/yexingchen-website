"""歌词抓取 / 解析 / 匹配（v2.46.327）。

夜星：「音乐播放时没有歌词，你去完善下，通过语音识别或者网上找对应的资源都行，
我需要完整的内容」「后续要同时支持上传歌词并能关联到对应歌曲」「同名即可关联」。

三条实用主义决定：

1. **不做语音识别**。本地曲库 250+ 首、单曲 3~5 分钟，ASR 要么上云（按分钟计费、
   还要传整首歌），要么本地跑 whisper（CVM 是 CPU，一首歌几分钟，不现实）。
   而中文歌的歌词在网易云/酷狗上基本都有带时间轴的 LRC，命中率高一个数量级。
2. **主源网易云，酷狗兜底**。网易云接口返回干净 JSON；酷狗要两步（search→download，base64），
   但中文老歌/网络歌曲覆盖更全。
3. **只认「带时间轴」的结果**。抓回来是纯文本也不能用 —— 播放器要靠 [mm:ss.xx] 定位高亮，
   没时间轴的歌词只能当静态文本，反而制造「歌词不动」的疑惑。所以有纯文本时返回空，让用户手填。

文件名匹配（批量上传歌词）也在这里：`match_title()` 负责把
「晴天 - 周杰伦.lrc」「01 晴天.lrc」「晴天(live).lrc」都归一到「晴天」。
"""
from __future__ import annotations

import base64
import difflib
import json
import re
from typing import Optional

import httpx

# LRC 时间轴：[mm:ss] / [mm:ss.xx] / [mm:ss.xxx]
TIME_RE = re.compile(r"\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\]")
# 文件名的噪音：序号、括号备注、破折号后缀、扩展名
_NOISE_RE = re.compile(
    r"^\s*\d{1,3}[\s._\-、]+"          # 01 晴天 / 01.晴天
    r"|[（(\[【].*?[)）\]】]"           # (Live) 【伴奏】
    r"|\s*[-—_]\s*[^-—_]*$"            # 晴天 - 周杰伦
    r"|\.(lrc|txt|krc|srt)$"
)
# 元信息行：只有这些的行不算歌词。网易云对没版权的纯音乐会给一条
# 「[00:00.00] 作曲 : xxx / [00:05.00]纯音乐，请欣赏」—— 有时间轴，但是垃圾。
_META_LINE = re.compile(
    r"^(作词|作曲|编曲|混音|母带|制作人|监制|出品|录音|和声|吉他|贝斯|鼓|键盘|弦乐|"
    r"OP|SP|发行|统筹|策划|纯音乐|此歌曲|这首歌|请欣赏|未经许可)"
    , re.I
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)
_TIMEOUT = 8.0


# ---------------- 文本处理 ----------------

def normalize_lrc(text: str) -> str:
    """统一换行、去 BOM、去首尾空白。不校验时间轴（调用方自己判）。"""
    if not text:
        return ""
    t = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()


def has_timeline(text: str) -> bool:
    return bool(text) and bool(TIME_RE.search(text))


def effective_lines(text: str) -> int:
    """去掉元信息行后的真实歌词行数（判断这份歌词是不是"纯音乐，请欣赏"）。"""
    n = 0
    for raw in (text or "").split("\n"):
        line = TIME_RE.sub("", raw).strip()
        if not line or _META_LINE.match(line):
            continue
        n += 1
    return n


def is_usable(text: str, min_lines: int = 3) -> bool:
    """能用的歌词 = 有时间轴 + 至少有 min_lines 行真歌词。

    为什么必须挡：网易云对无版权纯音乐返回的正是带时间轴的
    「作曲/编曲/纯音乐，请欣赏」，不挡就会铺满整个歌词区（夜星反馈「爱河dj」）。
    """
    return has_timeline(text) and effective_lines(text) >= min_lines


def clean_name(name: str) -> str:
    """把歌名/文件名归一成可比对的形式：去序号、括号备注、破折号后缀、扩展名。"""
    s = (name or "").strip()
    s = _NOISE_RE.sub("", s)
    s = re.sub(r"\s+", "", s)
    return s.lower()


def match_title(filename: str, title: str, artist: str = "") -> bool:
    """批量上传时判「这个歌词文件是不是这首歌的」。

    口径（宁可漏配也不要乱配 —— 配错了比没有更糟）：
      归一后完全相等 → 命中；
      文件名以歌名开头（后面跟的是歌手/备注）→ 命中；
      互相包含且长度差 ≤ 2 → 命中（「晴天」vs「晴天(live)」已经被 clean 掉）。
    """
    a = clean_name(filename)
    b = clean_name(title)
    if not a or not b:
        return False
    if a == b:
        return True
    if a.startswith(b) and len(a) - len(b) <= 6:
        return True
    if b.startswith(a) and len(b) - len(a) <= 6:
        return True
    art = clean_name(artist)
    if art and f"{b}{art}" in a:
        return True
    return False


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, clean_name(a), clean_name(b)).ratio()


# ---------------- 网易云 ----------------

def _netease_best(title: str, artist: str, duration: int) -> Optional[dict]:
    headers = {"User-Agent": _UA, "Referer": "https://music.163.com"}
    keyword = f"{title} {artist}".strip()
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=headers, follow_redirects=True) as c:
            r = c.get(
                "https://music.163.com/api/search/get/web",
                params={"csrf_token": "", "s": keyword, "type": 1, "offset": 0, "limit": 10},
            )
            songs = ((r.json() or {}).get("result") or {}).get("songs") or []
            if not songs:
                # 带歌手搜不到就去掉歌手再搜一次（很多曲库里的歌名不带演唱者）
                r = c.get(
                    "https://music.163.com/api/search/get/web",
                    params={"csrf_token": "", "s": title, "type": 1, "offset": 0, "limit": 10},
                )
                songs = ((r.json() or {}).get("result") or {}).get("songs") or []
            if not songs:
                return None

            best, best_score = None, 0.0
            for s in songs:
                name = s.get("name") or ""
                artists = " ".join((a.get("name") or "") for a in (s.get("artists") or []))
                score = _sim(name, title) * 2
                if artist:
                    score += _sim(artists, artist) * 1.2
                dur = int(s.get("duration") or 0) // 1000
                if duration and dur and abs(dur - duration) <= 5:
                    score += 0.8
                if score > best_score:
                    best, best_score = s, score
            if not best or best_score < 1.2:      # 标题对不上就别硬配
                return None

            r2 = c.get(
                "https://music.163.com/api/song/lyric",
                params={"os": "pc", "id": best.get("id"), "lv": -1, "kv": -1, "tv": -1},
            )
            data = r2.json() or {}
            lrc = normalize_lrc((data.get("lrc") or {}).get("lyric") or "")
            if not has_timeline(lrc):
                return None
            return {
                "lyric": lrc,
                "source": "netease",
                "title": best.get("name") or "",
                "artist": " ".join((a.get("name") or "") for a in (best.get("artists") or [])),
            }
    except Exception:  # noqa: BLE001 —— 抓歌词失败不能影响主流程
        return None


# ---------------- 酷狗（兜底） ----------------

def _kugou(title: str, artist: str) -> Optional[dict]:
    headers = {"User-Agent": _UA}
    keyword = f"{title} {artist}".strip()
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=headers, follow_redirects=True) as c:
            r = c.get(
                "http://mobilecdn.kugou.com/api/v3/search/song",
                params={"format": "json", "keyword": keyword, "page": 1, "pagesize": 5},
            )
            info = ((r.json() or {}).get("data") or {}).get("info") or []
            if not info:
                return None
            # 取最像的一首
            pick = max(
                info,
                key=lambda x: _sim((x.get("songname") or "").split(" - ")[0], title),
            )
            hash_ = pick.get("hash")
            if not hash_:
                return None

            r2 = c.get(
                "http://krcs.kugou.com/search",
                params={"ver": 1, "man": "yes", "client": "mobi", "keyword": "", "hash": hash_},
            )
            cands = (r2.json() or {}).get("candidates") or []
            if not cands:
                return None
            cand = cands[0]
            r3 = c.get(
                "http://lyrics.kugou.com/download",
                params={
                    "ver": 1,
                    "client": "pc",
                    "id": cand.get("id"),
                    "accesskey": cand.get("accesskey"),
                    "fmt": "lrc",
                    "charset": "utf8",
                },
            )
            content = (r3.json() or {}).get("content") or ""
            if not content:
                return None
            lrc = normalize_lrc(base64.b64decode(content).decode("utf-8", "ignore"))
            if not has_timeline(lrc):
                return None
            return {
                "lyric": lrc,
                "source": "kugou",
                "title": pick.get("songname") or "",
                "artist": (pick.get("singername") or ""),
            }
    except Exception:  # noqa: BLE001
        return None


def fetch_online(title: str, artist: str = "", duration: int = 0) -> Optional[dict]:
    """在线抓歌词：网易云 → 酷狗。

    ⚠️ 不能写 `a or b`：网易云经常返回「纯音乐，请欣赏」这种**有时间轴但没内容**的结果，
    直接 or 就吃掉兜底机会。这里逐个校验，不合格的继续找下一个源。
    """
    if not (title or "").strip():
        return None
    for fn in (_netease_best, _kugou):
        cand = fn(title, artist, duration) if fn is _netease_best else fn(title, artist)
        if cand and is_usable(cand.get("lyric") or ""):
            return cand
    return None


def parse_lrc_lines(text: str) -> list:
    """把 LRC 拆成 [{t, text}]，供前端/工具校验预览（前端有自己的解析，这里只用于回显）。"""
    out = []
    for raw in normalize_lrc(text).split("\n"):
        m = TIME_RE.match(raw)
        if not m:
            continue
        tag = m.group(0)[1:-1]
        mm, _, ss = tag.partition(":")
        try:
            t = int(mm) * 60 + float(ss.replace(":", "."))
        except ValueError:
            continue
        line = raw[m.end():].strip()
        if line:
            out.append({"t": round(t, 2), "text": line})
    return out


def dumps(obj) -> str:  # 小工具：调试用
    return json.dumps(obj, ensure_ascii=False)

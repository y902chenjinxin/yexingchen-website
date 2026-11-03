"""歌词对齐引擎（v2.46.343）—— 用音频本身定时间轴

## 为什么需要这个

夜星：「不要偷懒找现成的，有些是对不上的，有些资源是我在网上找的，不是原版」
「现在歌词老是慢了一拍」。

网上抓的 LRC 是**官方版的时间轴**，但他的音频是 DJ 版 / 翻唱版 / 钢琴版。
实测兰亭序：官方 LRC 每一行都比人声晚 0.2~0.4 秒，而播放器还额外加了 120ms 滞后
→ 两处叠加，用户看到的就是「慢了一拍」。不同歌的偏差方向还不一样
（逍遥仙 -1.6s、虫儿飞 -0.5s），所以**没有一个全局常数能救**。

## 做法

1. ffmpeg 抽 16k 单声道 PCM（带通 120~6000Hz，压掉鼓和镲片）
2. 能量 VAD 切成人声段；超长段（>13s）按能量谷递归二分
   （不切的话 150 秒会被当成一段，一口气识别出十几句，后面全废）
3. 每段跑 SenseVoice 识别 —— 段的时间就是这段人声的时间，这是唯一的真值来源
4. 歌词行 ↔ 识别段对齐：
   - **有时间先验**（已有 LRC）：在 ±4s 窗口内找配对，取**最早**的合格段
     （一行常被唱成两段，后半段文本更长、分数更高，但歌词行时间是句首）
   - **没有先验**（新上传音频）：整段做序列 DP 对齐
5. 一段对应多行 → 段内按字数比例分配

## 性能

SenseVoice int8 在 4 核 Xeon 上实测 **19x 实时**：4 分钟歌约 18 秒。
内存峰值约 600MB（模型 230MB + PCM 与中间数组），3GB 机器上必须串行跑。
"""
from __future__ import annotations

import os
import re
import subprocess
import threading

import numpy as np

SR = 16000
_MODEL_DIRS = [
    os.environ.get("ASR_MODEL_DIR", ""),
    "/var/www/yexingchen/backend/models/sherpa-onnx-sense-voice",
]

TAG_RE = re.compile(r"<\|[^|]*\|>")
PUNCT_RE = re.compile(r"[\s，。！？、；：""''（）()【】《》,.!?~—－-]+")
TIME_RE = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")
META_RE = re.compile(
    r"^(作词|作曲|编曲|混音|母带|制作人|监制|出品|录音|和声|吉他|贝斯|鼓|键盘|弦乐|"
    r"OP|SP|发行|统筹|策划|纯音乐|此歌曲|这首歌|请欣赏|未经许可)\s*[:：]"
)

# 平台水印行（v2.46.354）。Kugou 的自动生成歌词会插一句
# 「由酷狗凌音引擎提供声学技术服务」，没有冒号，旧 META_RE 漏了它 ——
# 结果它一直挂在播放页的高亮位上。
WATERMARK_RE = re.compile(
    r"(由.{0,14}(提供|技术支持|制作)|酷狗|凌音引擎|网易云|QQ音乐|酷我|虾米|百度音乐|"
    r"搜狗音乐|未经授权|翻唱自|原唱[:：])"
)

_recognizer = None
_lock = threading.Lock()


def _resolve_model_dir() -> str:
    for d in _MODEL_DIRS:
        if not d:
            continue
        if os.path.isfile(os.path.join(d, "model.int8.onnx")) and os.path.isfile(os.path.join(d, "tokens.txt")):
            return d
    return ""


def available() -> bool:
    return bool(_resolve_model_dir())


def _get_recognizer():
    global _recognizer
    if _recognizer is None:
        with _lock:
            if _recognizer is None:
                import sherpa_onnx
                d = _resolve_model_dir()
                if not d:
                    raise RuntimeError("ASR 模型未部署")
                _recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                    model=os.path.join(d, "model.int8.onnx"),
                    tokens=os.path.join(d, "tokens.txt"),
                    num_threads=2,      # 4 核里留 2 核给 web 服务，别把站点拖死
                    use_itn=True,
                )
    return _recognizer


# ============================ 基础工具 ============================

def norm(s: str) -> str:
    """去掉标点与空白，只留实字（识别的标点和歌词的标点永远不一致）"""
    return PUNCT_RE.sub("", s or "")


def parse_lrc(text: str, title: str = "", artist: str = "") -> list[tuple[float, str]]:
    """LRC → [(秒, 文本)]，滤掉制作信息 / 平台水印 / 「歌名 - 歌手」标题行。

    v2.46.354 加了两类过滤，都是童话镇（id 176）暴露出来的：
      · `由酷狗凌音引擎提供声学技术服务` —— 平台水印，正则里没有冒号，旧 META_RE 漏了它；
      · `童话镇 - 小野来了` —— 首行的「歌名 - 歌手」，同样没有冒号，
        结果播放页第一句永远显示歌名。
    title/artist 从库里带进来，只用来判断「这行是不是标题」，
    不参与任何时间计算。
    """
    out = []
    nt = norm(title)
    na = norm(artist)
    for line in (text or "").split("\n"):
        if not TIME_RE.search(line):
            continue
        content = TIME_RE.sub("", line).strip()
        if not content or META_RE.match(content) or WATERMARK_RE.search(content):
            continue
        nc = norm(content)
        # 「歌名」「歌名 - 歌手」「歌手 - 歌名」：长度必须接近歌名+歌手，
        # 否则会误杀真歌词（"总有一条蜿蜒在童话镇里七彩的河" 也含歌名）
        if nt and nt in nc and len(nc) <= len(nt) + len(na) + 6:
            continue
        for m, s, f in TIME_RE.findall(line):
            sec = int(m) * 60 + int(s) + (int(f.ljust(3, "0")) / 1000 if f else 0)
            out.append((sec, content))
    out.sort(key=lambda x: x[0])
    return out


def build_lrc(pairs: list[tuple[float, str]]) -> str:
    lines = []
    for t, text in pairs:
        t = max(0.0, float(t))
        m = int(t // 60)
        s = t - m * 60
        lines.append(f"[{m:02d}:{s:05.2f}]{text}")
    return "\n".join(lines)


# ============================ 音频 → 人声段 ============================

def pcm_from_file(path: str) -> np.ndarray:
    p = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR),
         "-af", "highpass=f=120,lowpass=f=6000", "-f", "f32le", "-"],
        capture_output=True, timeout=600,
    )
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError("音频解码失败（ffmpeg 读不出这个文件）")
    return np.frombuffer(p.stdout, dtype=np.float32)


def pcm_from_bytes(raw: bytes, suffix: str = ".mp3") -> np.ndarray:
    """从上传的字节直接解码（不落盘也能跑，但落盘更稳，见路由层）"""
    p = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", "pipe:0", "-ac", "1", "-ar", str(SR),
         "-af", "highpass=f=120,lowpass=f=6000", "-f", "f32le", "-"],
        input=raw, capture_output=True, timeout=600,
    )
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(f"音频解码失败（{suffix} 格式 ffmpeg 读不出）")
    return np.frombuffer(p.stdout, dtype=np.float32)


def _frame_rms(x: np.ndarray, hop: float = 0.02, win: float = 0.04) -> np.ndarray:
    n, w = int(SR * hop), int(SR * win)
    x2 = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    frames = max(0, (len(x) - w) // n)
    if frames <= 0:
        return np.zeros(1)
    idx = np.arange(frames) * n
    return np.sqrt((x2[idx + w] - x2[idx]) / w + 1e-12)


def vad_segments(x: np.ndarray, hop: float = 0.02, min_speech: float = 0.55,
                 min_sil: float = 0.22, rel: float = 0.12) -> list[tuple[float, float]]:
    """能量 VAD：阈值取 dB 动态范围的下 12%，静音超过 220ms 断句。

    参数都是实测调的：min_sil 太大（0.32）会让连续演唱粘成一段，
    整段识别成十几句连着的一大串，后面全没法逐句定位。
    """
    rms = _frame_rms(x, hop)
    db = 20 * np.log10(rms + 1e-9)
    hi, lo = np.percentile(db, 92), np.percentile(db, 12)
    thr = lo + (hi - lo) * rel
    voiced = db > thr

    segs, start, sil = [], None, 0
    for i, v in enumerate(voiced):
        if v:
            if start is None:
                start = i
            sil = 0
        elif start is not None:
            sil += 1
            if sil * hop >= min_sil:
                end = i - sil + 1
                if (end - start) * hop >= min_speech:
                    segs.append((start * hop, end * hop))
                start, sil = None, 0
    if start is not None and (len(voiced) - start) * hop >= min_speech:
        segs.append((start * hop, len(voiced) * hop))
    return segs


def split_long(x: np.ndarray, segs, hop: float = 0.02, limit: float = 13.0):
    """超长段按能量谷递归二分 —— 人换气的地方能量最低。"""
    rms = _frame_rms(x, hop)
    out, stack = [], list(segs)
    while stack:
        a, b = stack.pop()
        if b - a <= limit:
            out.append((a, b))
            continue
        lo, hi = int(a / hop) + 5, int(b / hop) - 5
        if hi - lo < 10:
            out.append((a, b))
            continue
        q1, q3 = lo + (hi - lo) // 4, hi - (hi - lo) // 4   # 避开两端，别一切就切碎
        k = int(np.argmin(rms[q1:q3])) + q1
        cut = k * hop
        stack.append((a, cut))
        stack.append((cut, b))
    return sorted(out)


def transcribe_segments(x: np.ndarray, segs) -> list[tuple[float, float, str]]:
    """逐段识别 → [(start, end, text)]"""
    rec = _get_recognizer()
    out = []
    for a, b in segs:
        chunk = x[int(a * SR):int(b * SR)]
        if len(chunk) < int(0.2 * SR):
            continue
        s = rec.create_stream()
        s.accept_waveform(SR, chunk)
        rec.decode_stream(s)
        out.append((a, b, norm(TAG_RE.sub("", s.result.text))))
    return out


# ============================ 对齐 ============================
#
# ## v2.46.354 为什么推翻重写
#
# 原来按「原 LRC 时间 ±4s 窗口内找识别段」配对。夜星：「童话镇的歌曲比歌词快两句」。
# 实测（id 176）：55 行只配上 12 行，其余 43 行**原样保留了源 LRC 的时间**，
# 而源 LRC 是酷狗自动生成的（首行水印「凌音引擎」，时间轴一路排到 12:51，
# 音频只有 4:16），于是：
#   00:23.75 听说白雪公主在逃跑  ← 真人声从 00:17.72 就开唱了
#   00:45.34~00:47.67 四句挤在 2.3 秒里（自动生成的时间轴根本没对齐）
# 表现出来就是「歌词比歌慢，慢两句左右」。
#
# 根因不是窗口宽度，是**把源时间当成了坐标系**。翻唱/DJ 版和原版的时间轴
# 没有任何稳定关系（实测三首偏差 +0.56 / -1.61 / -0.48 秒，方向都不一样），
# 一旦某行配不上就退回源时间 = 把一个错误的时间留在原地。
#
# 所以改成**只用识别结果排序，完全不看源时间**：歌词行和识别段都是有序的，
# 这就是一个单调序列对齐问题，DP 解（55×37 的格子，毫秒级）。
# 源时间只在两处还用得上：① 判断前导行该不该保留 ② 全对不上时的兜底。

_MIN_SIM = 0.30      # 低于这个相似度不考虑配对
_SKIP_LINE = 0.60    # 这行没被唱 / 识别漏了 → 丢弃的代价
_SKIP_SEG = 0.012    # 跳过一个识别段（伴奏、气口）几乎免费
_MULTI_PEN = 0.10    # 一段里塞第二行以后的额外代价（一口气唱 2~3 行很常见）


def _distribute(rows: list[dict], segs_index: dict) -> None:
    """多行落在同一段 → 段内按字数比例分配时间。

    否则「忙不迭 千年碑易拓」和「却难拓你的美」会挤在同一秒亮起来。
    """
    # 只在「已配上的行」序列里找连续段。中间夹一条没配上的行（seg=None）不能把
    # 一段切断 —— 否则 [seg36, None, seg36] 会被当成两个单行，谁都分不到时间，
    # 最后一起被单调兜底压成 +0.05 的连珠炮（首版童话镇尾段就是这个毛病）。
    idx = [k for k, r in enumerate(rows) if r["seg"] is not None]
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and rows[idx[j + 1]]["seg"] == rows[idx[i]]["seg"]:
            j += 1
        if j > i:
            rows_ = [rows[idx[x]] for x in range(i, j + 1)]
            a, b = segs_index[rows_[0]["seg"]]
            total = sum(len(norm(r["text"])) or 1 for r in rows_) or 1
            acc = a
            for r in rows_:
                share = (b - a) * (len(norm(r["text"])) or 1) / total
                r["t"] = round(acc, 2)
                acc += share
        i = j + 1


def _sim(lyric: str, heard: str) -> float:
    """行 ↔ 识别段的相似度：LCS 的双向覆盖 F1。

    旧的 `_lcs_cover` 只算「识别文本有多少落在歌词里」（分母是识别长度）。
    一段识别常含两三句，分母被拉大 —— 完全命中的行也只有 0.4 分，
    和“沾个边”的行（0.3 分）几乎分不开，窗口里随便抓一段就配上了。
    改成双向：P = 覆盖了多少这行，R = 这段里有多少是这行，取 F1。
    """
    if not lyric or not heard:
        return 0.0
    la, lb = len(lyric), len(heard)
    prev = [0] * (la + 1)
    for i in range(1, lb + 1):
        cur = [0] * (la + 1)
        ch = heard[i - 1]
        for j in range(1, la + 1):
            cur[j] = prev[j - 1] + 1 if ch == lyric[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    lcs = prev[la]
    if not lcs:
        return 0.0
    p, r = lcs / la, lcs / lb
    return 2 * p * r / (p + r)


def align(lines: list[tuple[float, str]], heard: list[tuple[float, float, str]],
          dur: float = 0.0) -> list[dict]:
    """歌词行 ↔ 识别段 单调对齐（不看源时间）。

    转移只有四种：
      丢掉这一行       +0.60
      跳过一段识别     +0.012   （伴奏/气口，随便跳）
      行配段（都前进）+1-sim
      行配段（段不动） +1-sim+0.10   ← 一段唱好几行
    """
    n, m = len(lines), len(heard)
    if not n:
        return []
    if not m:
        return [{"t": t, "text": c, "ok": False, "score": 0.0, "heard": "", "seg": None}
                for t, c in lines]

    nl = [norm(c) for _t, c in lines]
    sims = [[_sim(nl[i], heard[j][2]) for j in range(m)] for i in range(n)]

    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    back: list[list] = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        row, brow = dp[i], back[i]
        for j in range(m + 1):
            cur = row[j]
            if cur == INF:
                continue
            if j < m and cur + _SKIP_SEG < row[j + 1]:
                row[j + 1] = cur + _SKIP_SEG
                brow[j + 1] = ("seg", i, j)
            if i == n:
                continue
            if cur + _SKIP_LINE < dp[i + 1][j]:
                dp[i + 1][j] = cur + _SKIP_LINE
                back[i + 1][j] = ("drop", i, j)
            if j < m and sims[i][j] >= _MIN_SIM:
                c = cur + 1.0 - sims[i][j]
                if c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = c
                    back[i + 1][j + 1] = ("match", i, j)
                if c + _MULTI_PEN < dp[i + 1][j]:
                    dp[i + 1][j] = c + _MULTI_PEN
                    back[i + 1][j] = ("multi", i, j)

    assign: list = [None] * n
    i, j = n, m
    while i > 0 or j > 0:
        act, pi, pj = back[i][j]
        if act in ("match", "multi"):
            assign[pi] = pj
        i, j = pi, pj

    rows = []
    for k, (t, content) in enumerate(lines):
        s = assign[k]
        if s is None:
            rows.append({"t": t, "text": content, "ok": False, "score": 0.0, "heard": "", "seg": None})
        else:
            rows.append({"t": heard[s][0], "text": content, "ok": True,
                         "score": round(sims[k][s], 3), "heard": heard[s][2], "seg": s})
    if not any(r["ok"] for r in rows):
        return rows

    segs_index = {k: (a, b) for k, (a, b, _) in enumerate(heard)}
    _distribute(rows, segs_index)

    first = next(k for k, r in enumerate(rows) if r["ok"])
    last = max(k for k, r in enumerate(rows) if r["ok"])

    # 中间的空缺：夹在两行已对齐的中间 → 按行数插值（比留源时间准得多）
    k0 = first
    while k0 <= last:
        if rows[k0]["ok"]:
            k0 += 1
            continue
        k1 = k0
        while k1 <= last and not rows[k1]["ok"]:
            k1 += 1
        prev, nxt = rows[k0 - 1], (rows[k1] if k1 <= last else None)
        if nxt is not None and nxt["t"] > prev["t"]:
            cnt = k1 - k0
            for q in range(cnt):
                rows[k0 + q]["t"] = round(prev["t"] + (nxt["t"] - prev["t"]) * (q + 1) / (cnt + 1), 2)
                rows[k0 + q]["interp"] = True
        k0 = k1

    # 收尾：前导行只在「源时间还落在第一句之前」时保留（宣传语/纯人声前奏），
    # 尾巴上没配上的行一律丢 —— 源 LRC 经常比音频长（id 176 排到 12:51）
    out = []
    for k, r in enumerate(rows):
        if r["ok"] or r.get("interp"):
            out.append(r)
        elif k < first and rows[first]["t"] >= r["t"] >= 0:
            out.append(r)
        else:
            r["dropped"] = True
            out.append(None)
    out = [r for r in out if r]
    rows = out

    # 单调性兜底（插值/分配偶尔会产生倒序），顺便把超出音频长度的尾巴砍掉
    limit = (dur + 1.5) if dur > 0 else None
    if limit:
        rows = [r for r in rows if r["t"] <= limit]
    for k in range(1, len(rows)):
        if rows[k]["t"] <= rows[k - 1]["t"]:
            rows[k]["t"] = round(rows[k - 1]["t"] + 0.05, 2)
    return rows


# ============================ 对外入口 ============================

_CACHE_DIR = os.environ.get("LYRIC_ASR_CACHE_DIR", "") or "/var/www/yexingchen/backend/.cache/lyric_asr"


def _segments_for(audio_path: str):
    """音频 → (heard, 时长)。带磁盘缓存。

    识别是重活（19x 实时，一首 4 分钟歌 13 秒）。调对齐算法时不该把
    ASR 重跑一遍 —— 280 首就是 70 分钟白烧。缓存键 = 文件名+大小+修改时间，
    音频被替换了自然失效。
    """
    import hashlib
    import json
    st = os.stat(audio_path)
    key = hashlib.md5(
        f"{os.path.basename(audio_path)}|{st.st_size}|{int(st.st_mtime)}".encode()
    ).hexdigest()
    cf = os.path.join(_CACHE_DIR, key + ".json")
    if os.path.isfile(cf):
        try:
            with open(cf, encoding="utf-8") as f:
                d = json.load(f)
            return [tuple(x) for x in d["heard"]], float(d["dur"])
        except Exception:
            pass

    x = pcm_from_file(audio_path)
    dur = len(x) / SR
    segs = split_long(x, vad_segments(x))
    heard = transcribe_segments(x, segs)
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        tmp = cf + f".{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"dur": dur, "heard": [list(h) for h in heard]}, f, ensure_ascii=False)
        os.replace(tmp, cf)
    except OSError:
        pass
    return heard, dur


def align_audio(audio_path: str, lyric_text: str, title: str = "", artist: str = "") -> dict:
    """主入口：音频 + 已有 LRC → 对齐后的 LRC 与统计。"""
    lines = parse_lrc(lyric_text, title, artist)
    if not lines:
        raise RuntimeError("这份歌词没有时间轴，先用「识别」生成再对齐")

    heard, dur = _segments_for(audio_path)
    rows = align(lines, heard, dur)

    ok = sum(1 for r in rows if r["ok"])
    n = len(lines)
    ratio = ok / n if n else 0.0

    # 兜底：几乎一行都配不上（ASR 全废 / 纯音乐没人声 / 歌词不是这首歌），
    # 就别动原文 —— 留着一个"能读但慢半拍"的版本，好过换个完全不认识的。
    # need 按行数缩放：库里有一堆只有一个标题行的纯音乐条目，
    # 用固定的 "至少 3 行" 会把它们全判成降级。
    need = min(3, n)
    if ok < need or ratio < 0.18:
        return {
            "lyric": lyric_text,
            "rows": rows,
            "stats": {"lines": n, "segments": len(heard), "aligned": ok, "ratio": round(ratio, 2),
                      "kept": n, "dropped": 0, "duration": round(dur, 1), "degraded": True},
        }

    return {
        "lyric": build_lrc([(r["t"], r["text"]) for r in rows]),
        "rows": rows,
        "stats": {
            "lines": n,
            "segments": len(heard),
            "aligned": ok,
            "ratio": round(ratio, 2),
            "kept": len(rows),
            "dropped": n - len(rows),
            "duration": round(dur, 1),
            "degraded": False,
        },
    }


def transcribe_to_lrc(audio_path: str, hint_text: str = "", title: str = "") -> dict:
    """新音频 → LRC。有歌词文本就按文本对齐，没有就直接用识别结果。

    识别的文本会有错别字（"悬笔一绝"→"旋笔一卷"），所以**只要用户给了歌词文本，
    就以用户的文本为准**，识别结果只用来定时间。
    """
    heard, dur = _segments_for(audio_path)
    with_time = parse_lrc(hint_text, title)

    if with_time:
        rows = align(with_time, heard, dur)
        pairs = [(r["t"], r["text"]) for r in rows]
        aligned = sum(1 for r in rows if r["ok"])
    elif (hint_text or "").strip():
        # 纯文本歌词：没有源时间可用，只能靠单调对齐，配不上的行直接丢
        plain = [(0.0, ln.strip()) for ln in hint_text.split("\n") if ln.strip()]
        rows = align(plain, heard, dur)
        pairs = [(r["t"], r["text"]) for r in rows if r["ok"] or r.get("interp")]
        aligned = sum(1 for r in rows if r["ok"])
    else:
        pairs = [(a, txt) for a, _b, txt in heard if txt]
        aligned = len(pairs)

    return {
        "lyric": build_lrc(pairs),
        "stats": {
            "segments": len(heard),
            "lines": len(pairs),
            "aligned": aligned,
            "duration": round(dur, 1),
            "mode": "with-hint" if hint_text.strip() else "asr-only",
        },
    }

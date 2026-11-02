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


def parse_lrc(text: str) -> list[tuple[float, str]]:
    """LRC → [(秒, 文本)]，过滤制作信息行"""
    out = []
    for line in (text or "").split("\n"):
        if not TIME_RE.search(line):
            continue
        content = TIME_RE.sub("", line).strip()
        if not content or META_RE.match(content):
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


def _lcs_cover(lyric: str, heard: str) -> float:
    """识别文本有多少内容落在歌词行里。

    为什么不用 Jaccard：识别常常只吐出半句（"旋笔一卷" vs "悬笔一绝 那岸边浪千叠"），
    Jaccard 被行长度拖死。看"识别出的部分对了多少"更有判别力。
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
    return prev[la] / lb


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

def _distribute(rows: list[dict], segs_index: dict) -> None:
    """多行落在同一段 → 段内按字数比例分配时间。

    否则「忙不迭 千年碑易拓」和「却难拓你的美」会挤在同一秒亮起来。
    """
    i = 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1]["ok"] and rows[j + 1]["seg"] is not None \
                and rows[j]["seg"] is not None and rows[j + 1]["seg"] == rows[j]["seg"]:
            j += 1
        if j > i:
            a, b = segs_index[rows[i]["seg"]]
            total = sum(len(norm(rows[k]["text"])) or 1 for k in range(i, j + 1)) or 1
            acc = a
            for k in range(i, j + 1):
                share = (b - a) * (len(norm(rows[k]["text"])) or 1) / total
                rows[k]["t"] = round(acc, 2)
                acc += share
        i = j + 1


def align(lines: list[tuple[float, str]], heard: list[tuple[float, float, str]],
          window: float = 4.0, cover: float = 0.45, max_shift: float = 3.5) -> list[dict]:
    """歌词行 ↔ 识别段 对齐。

    lines 带原时间（先验）；heard 是 [(start, end, text)]。
    返回每行 {t, text, ok, score, heard}。
    """
    segs_index = {i: (a, b) for i, (a, b, _) in enumerate(heard)}
    rows = []
    for t, content in lines:
        nc = norm(content)
        hits = []
        for i, (a, b, txt) in enumerate(heard):
            if b < t - window or a > t + window or len(txt) < 2:
                continue
            sc = _lcs_cover(nc, txt)
            if sc >= cover:
                hits.append((i, a, sc, txt))
        if not hits:
            rows.append({"t": t, "text": content, "ok": False, "score": 0.0, "heard": "", "seg": None})
            continue
        # 取最早：一行常被唱成两段（换气），后半段文本更长、分数更高，
        # 但歌词行的时间是**句首**，取最高分会整句晚 2~3 秒。
        hits.sort(key=lambda h: h[1])
        i, a, sc, txt = hits[0]
        if abs(a - t) > max_shift and sc < 0.75:
            # 偏太多又没有强证据 → 很可能匹配到隔壁句，保留原值更安全
            rows.append({"t": t, "text": content, "ok": False, "score": sc, "heard": txt, "seg": i})
        else:
            rows.append({"t": a, "text": content, "ok": True, "score": sc, "heard": txt, "seg": i})

    _distribute(rows, segs_index)

    # 没对齐上的行：如果夹在两行已对齐的中间，按比例插值（比留着原值准）
    for k, r in enumerate(rows):
        if r["ok"]:
            continue
        prev = next((rows[x] for x in range(k - 1, -1, -1) if rows[x]["ok"]), None)
        nxt = next((rows[x] for x in range(k + 1, len(rows)) if rows[x]["ok"]), None)
        if prev and nxt and nxt["t"] > prev["t"]:
            span = sum(1 for x in range(k, len(rows)) if not rows[x]["ok"] and (nxt is None or rows[x] is not nxt))
            step = (nxt["t"] - prev["t"]) / max(1, span + 1)
            r["t"] = round(prev["t"] + step * (sum(1 for x in range(k, -1, -1) if not rows[x]["ok"])), 2)
            r["interp"] = True

    # 单调性兜底：时间必须递增，插值/分配偶尔会产生倒序
    for k in range(1, len(rows)):
        if rows[k]["t"] <= rows[k - 1]["t"]:
            rows[k]["t"] = round(rows[k - 1]["t"] + 0.05, 2)
    return rows


# ============================ 对外入口 ============================

def align_audio(audio_path: str, lyric_text: str) -> dict:
    """主入口：音频 + 已有 LRC → 对齐后的 LRC 与统计。"""
    lines = parse_lrc(lyric_text)
    if not lines:
        raise RuntimeError("这份歌词没有时间轴，先用「识别」生成再对齐")

    x = pcm_from_file(audio_path)
    dur = len(x) / SR
    segs = split_long(x, vad_segments(x))
    heard = transcribe_segments(x, segs)
    rows = align(lines, heard)

    ok = sum(1 for r in rows if r["ok"])
    return {
        "lyric": build_lrc([(r["t"], r["text"]) for r in rows]),
        "rows": rows,
        "stats": {
            "lines": len(lines),
            "segments": len(segs),
            "aligned": ok,
            "kept": len(rows) - ok,
            "duration": round(dur, 1),
        },
    }


def transcribe_to_lrc(audio_path: str, hint_text: str = "") -> dict:
    """新音频 → LRC。有歌词文本就按文本对齐，没有就直接用识别结果。

    识别的文本会有错别字（"悬笔一绝"→"旋笔一卷"），所以**只要用户给了歌词文本，
    就以用户的文本为准**，识别结果只用来定时间。
    """
    x = pcm_from_file(audio_path)
    dur = len(x) / SR
    segs = split_long(x, vad_segments(x))
    heard = transcribe_segments(x, segs)

    hint_lines = [(0.0, ln.strip()) for ln in (hint_text or "").split("\n") if ln.strip()]
    # 用户给的文本可能带 LRC 时间（那就当先验用）
    with_time = parse_lrc(hint_text)
    if with_time:
        hint_lines = with_time

    if hint_lines:
        if with_time:
            rows = align(hint_lines, heard)
            pairs = [(r["t"], r["text"]) for r in rows]
            aligned = sum(1 for r in rows if r["ok"])
        else:
            pairs, aligned = _align_without_hint(hint_lines, heard)
    else:
        pairs = [(a, txt) for a, _b, txt in heard if txt]
        aligned = len(pairs)

    return {
        "lyric": build_lrc(pairs),
        "stats": {
            "segments": len(segs),
            "lines": len(pairs),
            "aligned": aligned,
            "duration": round(dur, 1),
            "mode": "with-hint" if hint_lines else "asr-only",
        },
    }


def _align_without_hint(hint_lines, heard):
    """没有时间先验时的序列对齐（贪心单调 + 断点回退）。

    不用 DP：歌词行数（几十）和段数（几十）都不大，但 DP 的路径在
    "一段含多行"时会给出反直觉的分配；贪心加单调约束更可控也更好调。
    """
    rows, cursor = [], 0
    for _t, content in hint_lines:
        nc = norm(content)
        best, best_sc = None, 0.0
        for i in range(cursor, min(cursor + 6, len(heard))):      # 只往前看 6 段
            a, b, txt = heard[i]
            if len(txt) < 2:
                continue
            sc = _lcs_cover(nc, txt)
            if sc > best_sc:
                best, best_sc = i, sc
        if best is not None and best_sc >= 0.4:
            rows.append({"t": heard[best][0], "text": content, "ok": True, "seg": best})
            cursor = best
        else:
            # 匹配不上就沿用上一行时间 + 段均摊，保证单调且不飞出去
            base = rows[-1]["t"] + 2.5 if rows else (heard[0][0] if heard else 0.0)
            rows.append({"t": round(base, 2), "text": content, "ok": False, "seg": None})

    segs_index = {i: (a, b) for i, (a, b, _) in enumerate(heard)}
    _distribute(rows, segs_index)
    return [(r["t"], r["text"]) for r in rows], sum(1 for r in rows if r["ok"])

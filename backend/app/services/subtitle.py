"""视频自动字幕（v2.46.236）—— ffmpeg 抽音轨 + faster-whisper 本地推理，纯 CPU。

## 为什么用 whisper 而不是已有的 SenseVoice

项目里 `routers/asr.py` 已经有 sherpa-onnx + SenseVoice（中文 CER 4.2%，比 whisper 好），
但它**只输出整段文本、没有时间戳**。做 SRT 需要每句的起止时间。

试过两条路（2026-10-26 实测，素材是一段 90 秒带 BGM 的音频）：
1. **ffmpeg silencedetect 切句 + SenseVoice 逐段识别** → 只切出 **1 段**
   （BGM 一直在响，静音检测找不到切点），时间戳完全不可用。
2. **faster-whisper base** → **15 段**，每段 3-6 秒，边界合理，**5.9x 实时**。

→ 视频字幕用 whisper；纯讲话音频场景若只要文字，仍可走 `/api/asr`（更快更准）。

## 依赖与模型

- `faster-whisper`（CTranslate2 引擎）+ `ffmpeg`（服务器已装 7.0.2）
- 模型：**base int8，142MB**，从 ModelScope 下载（HuggingFace 与 hf-mirror 在本机全部超时）：
  ```bash
  pip install faster-whisper modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
  HF 不通时用：python -c "from modelscope import snapshot_download; \
      snapshot_download('pengzhendong/faster-whisper-base', cache_dir='backend/models/ms')"
  ```
- 模型目录按序探测：环境变量 `SUBTITLE_MODEL_DIR` → `backend/models/whisper` →
  `backend/models/ms/models/*/snapshots/master`。都找不到时接口返回 503，其余功能不受影响。

## 并发策略

CPU 只有 2-4 核，边说边转会把整站拖慢 → **全局单任务队列**（同时只跑一个字幕任务），
其余排队。任务状态放在进程内 dict，结果落盘 `uploads/subtitles/{video_id}.srt`，
前端按 video_id 取固定 URL，**不需要动数据库**。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from typing import Callable, Optional

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- 模型探测

def _candidate_model_dirs() -> list[str]:
    env = os.environ.get("SUBTITLE_MODEL_DIR", "").strip()
    out: list[str] = []
    if env:
        out.append(env)
    out.append(os.path.join(_BACKEND_DIR, "models", "whisper"))
    out.append("/var/www/yexingchen/backend/models/whisper")
    # ModelScope 缓存目录：models/ms/models/<owner>--<name>/snapshots/master
    ms_root = os.path.join(_BACKEND_DIR, "models", "ms", "models")
    if os.path.isdir(ms_root):
        for owner in os.listdir(ms_root):
            snap = os.path.join(ms_root, owner, "snapshots", "master")
            if os.path.isdir(snap):
                out.append(snap)
    return out


def resolve_model_dir() -> str:
    """返回可用的 CTranslate2 模型目录；找不到返回空串。"""
    for d in _candidate_model_dirs():
        if not d or not os.path.isdir(d):
            continue
        # faster-whisper 需要 model.bin + config.json（tokenizer 视版本而定）
        if os.path.isfile(os.path.join(d, "model.bin")) and \
           os.path.isfile(os.path.join(d, "config.json")):
            return d
    return ""


def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg"))


# ---------------------------------------------------------------- 引擎（懒加载 + 单例）

_model = None
_model_dir = ""
_model_lock = threading.Lock()


class SubtitleUnavailable(RuntimeError):
    """依赖或模型缺失，接口应返回 503 并带上这句提示。"""


def get_model():
    global _model, _model_dir
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        if not ffmpeg_available():
            raise SubtitleUnavailable("服务器未安装 ffmpeg，无法从视频抽取音轨")
        d = resolve_model_dir()
        if not d:
            raise SubtitleUnavailable(
                "未找到 whisper 模型（需含 model.bin / config.json）。"
                "见 services/subtitle.py 文件头的下载说明"
            )
        try:
            from faster_whisper import WhisperModel  # 延迟导入：缺包时只影响本功能
        except Exception as exc:  # noqa: BLE001
            raise SubtitleUnavailable(f"未安装 faster-whisper：{str(exc)[:120]}") from exc
        try:
            # int8 量化：CPU 上速度约 6x 实时，内存明显低于 float32
            _model = WhisperModel(d, device="cpu", compute_type="int8", cpu_threads=2)
        except Exception as exc:  # noqa: BLE001
            raise SubtitleUnavailable(f"whisper 模型加载失败：{str(exc)[:160]}") from exc
        _model_dir = d
        return _model


def engine_status() -> dict:
    d = resolve_model_dir()
    return {
        "ready": bool(d) and ffmpeg_available(),
        "model": os.path.basename(d) or None,
        "model_dir": d or None,
        "ffmpeg": ffmpeg_available(),
    }


# ---------------------------------------------------------------- 音频处理

_SR = 16000


def extract_audio(video_path: str, out_wav: str) -> float:
    """抽成 16k 单声道 wav，返回时长（秒）。失败抛 RuntimeError。"""
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", video_path,
        "-vn", "-ac", "1", "-ar", str(_SR),
        "-f", "wav", out_wav,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out_wav):
        raise RuntimeError(f"抽取音轨失败：{(proc.stderr or '')[:200]}")
    import wave
    with wave.open(out_wav) as f:
        frames, rate = f.getnframes(), f.getframerate()
    return frames / float(rate or _SR)


# ---------------------------------------------------------------- SRT 生成

def _fmt_ts(sec: float) -> str:
    """秒 → SRT 时间码 00:01:23,456（注意是逗号，不是点）"""
    if sec < 0:
        sec = 0.0
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(segments: list[dict]) -> str:
    """segments: [{'start': float, 'end': float, 'text': str}, ...]"""
    lines: list[str] = []
    idx = 0
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        idx += 1
        lines.append(str(idx))
        lines.append(f"{_fmt_ts(seg['start'])} --> {_fmt_ts(seg['end'])}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- 转写

def transcribe(
    wav_path: str,
    on_progress: Optional[Callable[[float, str], None]] = None,
    duration: float = 0.0,
) -> list[dict]:
    """转写 wav，返回带时间戳的段列表。on_progress(0-1, 状态文案)。"""
    model = get_model()
    seg_iter, info = model.transcribe(
        wav_path,
        language="zh",                 # 站内视频以中文为主；要自动检测可改 None
        beam_size=5,
        vad_filter=False,              # silero VAD 需额外模型，且对 BGM 视频会误切
        condition_on_previous_text=False,  # 长视频防复读幻觉
    )
    total = duration or float(getattr(info, "duration", 0) or 0)
    out: list[dict] = []
    for seg in seg_iter:
        text = (seg.text or "").strip()
        if text:
            out.append({"start": float(seg.start), "end": float(seg.end), "text": text})
        if on_progress and total > 0:
            on_progress(min(0.99, float(seg.end) / total), f"已识别 {len(out)} 句")
    if on_progress:
        on_progress(1.0, f"识别完成，共 {len(out)} 句")
    return out


# ---------------------------------------------------------------- 任务管理（全局单并发）

_LOCK = threading.Lock()
_TASKS: dict[str, dict] = {}
_QUEUE_LOCK = threading.Lock()
_running = False


def _task_dir() -> str:
    d = os.path.join(_BACKEND_DIR, "uploads", "subtitles")
    os.makedirs(d, exist_ok=True)
    return d


def subtitle_path(video_id: int | str) -> str:
    """固定路径：uploads/subtitles/{video_id}.srt（前端 URL 不依赖任务 id）"""
    return os.path.join(_task_dir(), f"{video_id}.srt")


def get_task(task_id: str) -> Optional[dict]:
    with _LOCK:
        t = _TASKS.get(task_id)
        return dict(t) if t else None


def _update(task_id: str, **kw):
    with _LOCK:
        if task_id in _TASKS:
            _TASKS[task_id].update(kw)
            _TASKS[task_id]["updated_at"] = time.time()


def _prune():
    """清掉超过 2 小时的旧任务，避免内存缓慢增长。"""
    now = time.time()
    with _LOCK:
        for k in [k for k, v in _TASKS.items() if now - v.get("updated_at", now) > 7200]:
            _TASKS.pop(k, None)


def _worker(task_id: str, video_id: int, src_path: str):
    global _running
    tmp_wav = os.path.join(_task_dir(), f".{video_id}.{task_id}.wav")
    try:
        _update(task_id, status="extracting", progress=0.02, message="正在抽取音轨…")
        duration = extract_audio(src_path, tmp_wav)
        _update(task_id, status="transcribing", progress=0.05,
                message=f"音轨 {duration:.0f} 秒，开始识别…")

        def cb(p: float, msg: str):
            # 音轨已抽完，把 5%-99% 映射给识别阶段
            _update(task_id, progress=0.05 + p * 0.94, message=msg)

        segs = transcribe(tmp_wav, on_progress=cb, duration=duration)
        if not segs:
            raise RuntimeError("没有识别到语音内容（可能是纯音乐或静音）")

        out = subtitle_path(video_id)
        with open(out, "w", encoding="utf-8") as f:
            f.write(build_srt(segs))
        _update(task_id, status="done", progress=1.0,
                message=f"完成，共 {len(segs)} 句",
                sentences=len(segs), duration=round(duration, 1),
                srt=f"/api/videos/{video_id}/subtitle.srt")
    except Exception as exc:  # noqa: BLE001
        _update(task_id, status="failed", progress=1.0,
                message=str(exc)[:300] or "识别失败")
    finally:
        try:
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)
        except OSError:
            pass
        with _QUEUE_LOCK:
            _running = False


def start_task(video_id: int, src_path: str) -> dict:
    """创建并排队一个字幕任务。返回 {task_id, queued}。

    引擎缺失时**先抛** SubtitleUnavailable，让接口立刻 503，而不是建一个必败的任务。
    """
    get_model()  # 触发可用性检查（模型/ffmpeg/依赖）
    _prune()
    task_id = uuid.uuid4().hex[:12]
    running = False
    with _QUEUE_LOCK:
        running = _running
        if not running:
            _running = True
    with _LOCK:
        _TASKS[task_id] = {
            "task_id": task_id,
            "video_id": video_id,
            "status": "queued" if running else "starting",
            "progress": 0.0,
            "message": "已排队，等待前面的任务完成…" if running else "准备中…",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    if running:
        return {"task_id": task_id, "queued": True}

    t = threading.Thread(target=_worker, args=(task_id, video_id, src_path), daemon=True)
    t.start()
    return {"task_id": task_id, "queued": False}


def has_subtitle(video_id: int | str) -> bool:
    p = subtitle_path(video_id)
    return os.path.isfile(p) and os.path.getsize(p) > 0

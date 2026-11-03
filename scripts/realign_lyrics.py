"""全库重跑歌词对齐（v2.46.354）。

## 为什么要有这个脚本，而不是再用 /api/music/lyric/align-all

批量接口跑在 PM2 的 daemon 线程里，后端一重启（部署=重启）就断，
而且日志只在内存和 /tmp 里。这个脚本挂在服务器上后台跑，逐首落库、逐行打日志，
断了能续（已对齐的歌重跑成本 ≈ 0，因为识别结果有磁盘缓存）。

## 用法（在服务器 /var/www/yexingchen/backend 下）

    ./venv/bin/python realign_lyrics.py                # 全库
    ./venv/bin/python realign_lyrics.py --only 176,257 # 只跑某几首
    ./venv/bin/python realign_lyrics.py --limit 10     # 先跑 10 首看看
    ./venv/bin/python realign_lyrics.py --dry          # 只报告不写库
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal            # noqa: E402
from app.models.music import Music                # noqa: E402

# 🔴 模型之间有大量 relationship 按类名解析。只 import Music 会在 mapper
# 初始化时炸 `expression 'User' failed to locate a name`，只补 User 又会炸
# `'Novel'`…… 干脆把 app/models 下的模块全 import 一遍（等价于 main.py 的加载效果）。
import importlib                                  # noqa: E402
import pkgutil                                    # noqa: E402

import app.models as _models_pkg                  # noqa: E402

for _info in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_info.name}")
from app.services import lyric_align, lyrics as lyric_svc   # noqa: E402


def audio_abs(m) -> str:
    rel = (m.file_path or "").lstrip("/")
    for base in ("/var/www/yexingchen/backend/uploads", os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")):
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            return p
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔的音乐 id")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--report", default="/tmp/realign_report.json")
    args = ap.parse_args()

    db = SessionLocal()
    q = db.query(Music)
    if args.only:
        ids = [int(x) for x in args.only.split(",") if x.strip()]
        q = q.filter(Music.id.in_(ids))
    rows = q.order_by(Music.sort_order.asc(), Music.id.asc()).all()
    if args.limit:
        rows = rows[: args.limit]

    total = len(rows)
    print(f"共 {total} 首待处理，ASR 缓存目录 {lyric_align._CACHE_DIR}", flush=True)

    report = []
    ok_c = deg_c = err_c = skip_c = 0
    t_all = time.time()
    for k, m in enumerate(rows, 1):
        tag = f"[{k}/{total}] {m.id} {m.title}"
        if not lyric_svc.has_timeline(m.lyric or ""):
            skip_c += 1
            print(f"{tag} 跳过（没有带时间轴的歌词）", flush=True)
            continue
        path = audio_abs(m)
        if not path:
            err_c += 1
            print(f"{tag} 音频文件缺失", flush=True)
            continue
        t0 = time.time()
        try:
            res = lyric_align.align_audio(path, m.lyric, m.title or "", m.artist or "")
        except Exception as exc:                     # noqa: BLE001
            err_c += 1
            print(f"{tag} 失败: {str(exc)[:120]}", flush=True)
            report.append({"id": m.id, "title": m.title, "error": str(exc)[:200]})
            continue
        st = res["stats"]
        cost = time.time() - t0
        rec = {"id": m.id, "title": m.title, **st, "cost": round(cost, 1)}
        report.append(rec)
        if st.get("degraded"):
            deg_c += 1
            print(f"{tag} 降级保留原文（{st['aligned']}/{st['lines']}）{cost:.0f}s", flush=True)
            continue
        if not args.dry:
            m.lyric = res["lyric"]
            m.lyric_source = "aligned"
            db.commit()
        ok_c += 1
        print(f"{tag} ok {st['aligned']}/{st['lines']} 丢{st['dropped']} 段{st['segments']} "
              f"{st['duration']:.0f}s 用时{cost:.0f}s", flush=True)

    print(f"\n完成：成功 {ok_c}，降级 {deg_c}，跳过 {skip_c}，失败 {err_c}，"
          f"总耗时 {(time.time() - t_all) / 60:.1f} 分钟", flush=True)
    try:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print("报告：", args.report, flush=True)
    except OSError:
        pass
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

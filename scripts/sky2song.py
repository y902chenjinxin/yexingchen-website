"""把「光遇」15 键乐谱转成本站曲谱 JSON（v2.46.335，本地工具）

为什么走光遇谱：midishow 等站点了 Cloudflare（curl 403），能拿到的完整
中文流行曲谱大多是光遇/SkyStudio 的转录稿。它们的音高模型是确定的：

    15 键 = 该调的**大调音阶**铺满两个八度 + 高八度根音
    offset = [0,2,4,5,7,9,11] ×2 再补一个 24

这是从 SkyMusicPlay / sky15keys 的实现里核对过的（sky15/layout.py），
不是猜的。所以 `n 号键 → MIDI = 根音 + OFFSET[n]`，没有歧义。

⚠️ 光遇谱只有调内音（没有升降号），所以转出来是「主旋律 + 该调音阶」的简化版：
   旋律轮廓、节奏、句法是原曲的，但和声色彩会淡一些。要原调的完整版得拿真 MIDI。

用法：
    python scripts/sky2song.py <输入文件...> --out "C:/Users/xxx/Desktop/songs"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# 大调音阶（半音）→ 15 键偏移
SEMIS = [0, 2, 4, 5, 7, 9, 11]
OFFSETS = [SEMIS[i] if i < 7 else (12 + SEMIS[i - 7] if i < 14 else 24) for i in range(15)]

# 本站键盘音域（utils/pianoKeys.js：C3=48 ~ F5=77）
RANGE = (48, 77)


def decode(raw: bytes) -> str:
    for enc in ("utf-16", "utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", "ignore")


def parse_key(k: str) -> tuple[int, int] | None:
    """'1Key4' → (1, 4)；'2Key11' → (2, 11)。

    前导数字是**页/八度**（1 起），后面是 15 键的音级序号 0..14。
    ⚠️ 一开始按「3 行 × 5 列」解析（列只能是 0..4），结果 `1Key11` 这类
    全部被当成非法丢掉 —— 兰亭序 1108 个音只解析出 300 多个，
    表现是「整首歌只有 5 个不同音高」，很容易误判成谱子太简单。
    """
    m = re.match(r"^(\d)Key(\d{1,2})$", (k or "").strip())
    if not m:
        return None
    page, idx = int(m.group(1)), int(m.group(2))
    if not (0 <= idx <= 14):
        return None
    return page, idx


def fit_octave(midis: list[int]) -> int:
    """选一个整八度平移量，让尽可能多的音落进本站音域。

    只平移整八度：调性不变（八度不是调），听感只是整体高低。
    比逐个音折叠好得多 —— 逐个折叠会把高音折到低音区，旋律突然掉八度。
    """
    best, best_ok = 0, -1
    for shift in (0, -12, -24, 12):
        ok = sum(1 for m in midis if RANGE[0] <= m + shift <= RANGE[1])
        if ok > best_ok:
            best, best_ok = shift, ok
    return best


def convert(path: str, title: str | None = None) -> dict:
    raw = open(path, "rb").read()
    data = json.loads(decode(raw))
    sheet = data[0] if isinstance(data, list) else data

    root = 60 + int(sheet.get("pitchLevel") or 0)
    notes_raw = sheet.get("songNotes") or []

    tmp = []
    for n in notes_raw:
        hit = parse_key(n.get("key", ""))
        if hit is None:
            continue
        page, idx = hit
        t = float(n.get("time") or 0) / 1000.0
        # 页 = 八度：page 2 比 page 1 高一个八度
        tmp.append((t, root + (page - 1) * 12 + OFFSETS[idx]))
    if not tmp:
        raise SystemExit(f"{os.path.basename(path)}：没有解析出音符")

    shift = fit_octave([m for _, m in tmp])
    tmp.sort(key=lambda x: x[0])

    # 同一时刻（30ms 内）的音合成和弦；时值取到下一个音的间隔，封顶 0.6s
    out = []
    i = 0
    while i < len(tmp):
        t = tmp[i][0]
        group = []
        while i < len(tmp) and tmp[i][0] - t <= 0.03:
            midi = tmp[i][1] + shift
            if midi not in group:
                group.append(midi)
            i += 1
        nxt = tmp[i][0] if i < len(tmp) else t + 0.6
        dur = max(0.12, min(0.6, nxt - t))
        for midi in sorted(group):
            out.append({"t": round(t, 3), "midi": midi, "dur": round(dur, 3)})

    # MIDI → 本站键位（白键 18 + 黑键 10，见 utils/pianoKeys.js）
    keymap = {}
    for k, m in [("A", 48), ("S", 50), ("D", 52), ("F", 53), ("G", 55), ("H", 57), ("J", 59),
                 ("K", 60), ("L", 62), ("Q", 64), ("W", 65), ("E", 67), ("R", 69), ("T", 71),
                 ("Y", 72), ("U", 74), ("I", 76), ("O", 77),
                 ("1", 49), ("2", 51), ("3", 54), ("4", 56), ("5", 58),
                 ("6", 61), ("7", 63), ("8", 66), ("9", 68), ("0", 70)]:
        keymap[m] = k

    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    notes = []
    for n in out:
        m = n["midi"]
        if m not in keymap:          # 理论上不会剩下，留个兜底
            continue
        notes.append({
            "time": n["t"],
            "key": keymap[m],
            "pitch": names[m % 12] + str(m // 12 - 1),
            "dur": n["dur"],
        })

    dur = max((x["time"] + x["dur"]) for x in notes) if notes else 0
    song = {
        "songName": title or sheet.get("name") or os.path.splitext(os.path.basename(path))[0],
        "artist": sheet.get("author") or "周杰伦",
        "bpm": 0,
        "notes": notes,
        "meta": {
            "source": "sky-sheet",
            "transcribedBy": sheet.get("transcribedBy") or "",
            "octaveShift": shift,
            "duration": round(dur, 1),
        },
    }
    return song


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=os.path.join(os.path.expanduser("~"), "Desktop", "songs"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    for f in args.files:
        try:
            song = convert(f)
        except SystemExit as e:
            print("✗", e)
            continue
        name = song["songName"].strip().replace("/", "_")
        p = os.path.join(args.out, name + ".json")
        with open(p, "w", encoding="utf-8") as fp:
            json.dump(song, fp, ensure_ascii=False, indent=1)
        ns = song["notes"]
        span = max(x["time"] for x in ns)
        keys = sorted({x["key"] for x in ns})
        print(f"✓ {name}: {len(ns)} 音，{span:.0f}s，{len(keys)} 个不同键，"
              f"八度平移 {song['meta']['octaveShift']:+d} → {p}")


if __name__ == "__main__":
    sys.exit(main())

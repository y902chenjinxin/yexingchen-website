"""临时排查②：真人 apply 路径随机动作压力测试（seat 0 = 真人，其余 AI）。"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, r"D:\software\codex\codex_work\yexingchen-website\backend")

from app.games.base import TableError
from app.games.mahjong import MahjongEngine


def total_of(st, s):
    hand = len(st["hands"][s])
    m3 = sum(1 for m in st["melds"][s] if m["type"] in ("pong", "chi"))
    m4 = sum(1 for m in st["melds"][s] if m["type"] in ("kong", "ankong", "bugang"))
    return hand + 3 * m3 + 4 * m4, m4


def check(st, tag):
    for s in range(4):
        if s in st["hu"]:
            continue
        total, m4 = total_of(st, s)
        if st.get("turn") == s:
            ok = total in (13 + m4, 14 + m4)
        else:
            ok = total == 13 + m4
        if not ok:
            print(f"[{tag}] seat {s} total={total} m4={m4} turn={st.get('turn')} "
                  f"melds={[m['type'] for m in st['melds'][s]]} hand={st['hands'][s]}")
            return False
    return True


def human_step(eng, st, rnd):
    """seat 0 随机做一个合法动作（有响应优先响应）。"""
    try:
        cl = st.get("claim")
        if cl is not None and cl.get("seat") == 0:
            opts = cl.get("options") or []
            act = rnd.choice(opts + ["pass"])
            return eng.apply(st, 0, {"type": act})
        if st.get("turn") == 0 and st.get("phase") == "playing":
            hand = st["hands"][0]
            opts = ["discard"]
            if hand:
                # 摸到了能胡就一定试一下胡（也随机放弃胡以覆盖 pass 路径）
                from app.games.mahjong import can_hu, find_ankongs, find_bugangs
                if can_hu(hand, len(st["melds"][0])) and rnd.random() < 0.9:
                    return eng.apply(st, 0, {"type": "hu"})
                ak = find_ankongs(hand)
                if ak and rnd.random() < 0.8:
                    return eng.apply(st, 0, {"type": "ankong", "tile": ak[0]})
                bg = find_bugangs(hand, st["melds"][0])
                if bg and rnd.random() < 0.8:
                    return eng.apply(st, 0, {"type": "bugang", "tile": bg[0]})
                t = rnd.choice(hand)
                return eng.apply(st, 0, {"type": "discard", "tile_id": t["id"]})
        return None
    except TableError:
        # 非法动作（响应窗口已变等）→ 过
        try:
            if st.get("claim") and st["claim"].get("seat") == 0:
                return eng.apply(st, 0, {"type": "pass"})
        except TableError:
            return None
        return None


def run_seed(seed: int):
    rnd = random.Random(seed * 7919 + 13)
    eng = MahjongEngine()
    seats = [{"seat": 0, "user_id": 1, "is_ai": False, "name": "我"}] + [
        {"seat": i, "user_id": 0, "is_ai": True, "name": f"AI{i}"} for i in range(1, 4)]
    st = eng.new_game(seats, {}, seed)
    st["_ai_wait_until"] = 0
    n = 0
    while st["phase"] == "playing" and n < 1200:
        out = human_step(eng, st, rnd)
        if out is None:
            out = eng.step_ai(st, seats)
        if out is None:
            break
        st, _ = out
        st["_ai_wait_until"] = 0
        n += 1
        if not check(st, f"hseed{seed}#step{n}"):
            return False
    return True


def main():
    bad = 0
    for seed in range(200):
        if not run_seed(seed):
            bad += 1
            if bad >= 3:
                break
    print("done, bad =", bad)


if __name__ == "__main__":
    main()

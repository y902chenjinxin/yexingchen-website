"""临时排查：手牌数不变量压力测试（复现 v2.46.44「你手牌 0」）。

不变量：任一未胡座位  hand_len + 3*pong/chi + 4*kong/ankong/bugang == 13 + kong数
（轮到出牌/刚摸时可为 14 + kong数）。
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"D:\software\codex\codex_work\yexingchen-website\backend")

from app.games.base import get_engine
from app.games.mahjong import MahjongEngine


def totals(st):
    out = []
    for s in range(4):
        hand = len(st["hands"][s])
        m3 = sum(1 for m in st["melds"][s] if m["type"] in ("pong", "chi"))
        m4 = sum(1 for m in st["melds"][s] if m["type"] in ("kong", "ankong", "bugang"))
        out.append((hand, m3, m4))
    return out


def check(st, tag):
    for s in range(4):
        if s in st["hu"]:
            continue
        hand, m3, m4 = totals(st)[s]
        total = hand + 3 * m3 + 4 * m4
        # 轮到该座位（刚摸/刚吃碰杠）→ 手里多一张待打：13+m4 ~ 14+m4
        # 其余座位必须恒等于 13+m4
        if st.get("turn") == s:
            ok = total in (13 + m4, 14 + m4)
        else:
            ok = total == 13 + m4
        if not ok:
            print(f"[{tag}] seat {s} hand={hand} m3={m3} m4={m4} total={total} "
                  f"expect={13 + m4}{'/' + str(14 + m4) if st.get('turn') == s else ''} "
                  f"turn={st.get('turn')} claim={bool(st.get('claim'))} melds={[m['type'] for m in st['melds'][s]]}")
            return False
    return True


def run_seed(seed: int):
    eng = MahjongEngine()
    seats = [{"seat": i, "user_id": 0, "is_ai": True, "name": f"AI{i}"} for i in range(4)]
    st = eng.new_game(seats, {}, seed)
    st["_ai_wait_until"] = 0
    n = 0
    while st["phase"] == "playing" and n < 800:
        out = eng.step_ai(st, seats)
        if out is None:
            break
        st, _ = out
        st["_ai_wait_until"] = 0
        n += 1
        if not check(st, f"seed{seed}#step{n}"):
            return False
    return True


def main():
    bad = 0
    for seed in range(300):
        if not run_seed(seed):
            bad += 1
            if bad >= 5:
                break
    print("done, bad =", bad)


if __name__ == "__main__":
    main()

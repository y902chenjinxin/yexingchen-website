# -*- coding: utf-8 -*-
"""v2.46.43 麻将牌张守恒压力测试。

背景：v2.46.42 开牌仪式把庄家第 14 张（跳牌）只存 last_draw 引用、没进 hands，
这张牌整局凭空消失（庄家 13 打 12，AI 不可见、不能胡）。夜星在线对局截图实锤：
3 组副露手牌只剩 3 张（应为 4）。

守恒式（任何时刻）：
    全桌 Σ(len(hand) + 副露持有 + len(弃牌)) + 墙 == 120
    庄家起手 14 张；任何时刻 hand + 副露从手里拿走张数 ≤ 14（刚摸/刚吃碰未打为上界）

两组副露张数语义不同：
- hold（持有，如今归属本家的牌）：吃/碰 3、点杠/补杠/暗杠 4 —— 用于全局守恒；
- take（从手里拿走）：吃/碰 2、点杠 3、暗杠 4、补杠 1 —— 用于 hand 上限。
"""
from app.games import get_engine

MELD_TAKE = {"pong": 2, "chi": 2, "kong": 3, "ankong": 4, "bugang": 3}
MELD_HOLD = {"pong": 3, "chi": 3, "kong": 4, "ankong": 4, "bugang": 4}


def _seats(n=4):
    return [{"seat": i, "user_id": 0, "is_ai": True, "name": f"AI{i}", "joined": True}
            for i in range(n)]


def _check(st, tag, expect=120):
    total_all = 0
    for s in range(4):
        hand = len(st["hands"][s])
        take = sum(MELD_TAKE.get(m["type"], 2) for m in st["melds"][s])
        hold = sum(MELD_HOLD.get(m["type"], 3) for m in st["melds"][s])
        assert hand + take <= 14, (
            f"{tag}: seat{s} hand={hand} + take={take} > 14 "
            f"(melds={[m['type'] for m in st['melds'][s]]})")
        total_all += hand + hold + len(st["discards"][s])
    assert total_all + len(st["wall"]) == expect, (
        f"{tag}: 全桌守恒破坏 sum={total_all} wall={len(st['wall'])} expect={expect}")


def test_mahjong_tile_conservation():
    eng = get_engine("mahjong")
    claim_events = 0
    for seed in range(6100, 6112):
        st = eng.new_game(_seats(), {"base_stake": 100, "seat_count": 4, "round_no": 1}, seed)
        assert len(st["hands"][st["dealer"]]) == 14   # 庄家起手 14 张（v2.46.43 修复点）
        # 点炮胡：胡的那张从放炮者弃牌堆移入 hu_info.hand（只作结算展示，不进
        # hands/melds）→ 账面每发生一次 -1，属设计使然；自摸胡的牌本就在手里。
        hu_pao = 0
        for step in range(20000):
            if st["phase"] != "playing":
                break
            out = eng.step_ai(st, _seats())
            if out is None:
                break
            st, evs = out
            claim_events += sum(1 for e in evs if e.get("kind") in ("chi", "pong", "kong"))
            hu_pao += sum(1 for e in evs if e.get("kind") == "hu" and not e.get("zimo"))
            _check(st, f"seed{seed} step{step}", expect=120 - hu_pao)
    assert claim_events > 0, "随机对局里没出现吃/碰/杠，测试没覆盖到目标路径"

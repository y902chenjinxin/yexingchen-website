"""v2.44 牌类在线对局 · 规则引擎单测。

覆盖：三引擎注册 / 全 AI 整局收敛 / 结算零和 / 掼蛋进贡·还贡·抗贡 /
麻将定缺与刮风下雨 / 牌型识别与比大小。
"""
import json

from app.games import engine_keys, get_engine
from app.games.base import TableError
from app.games.guandan import (
    can_beat,
    detect_pattern,
    level_text,
    _return_ok,
    _tribute_plan,
)
from app.games.mahjong import (
    can_hu,
    has_missing,
    score_hu,
    _counts,
    _gang_pay,
)


def _seats(n=4):
    return [{"seat": i, "user_id": 0, "is_ai": True, "name": f"AI{i}", "joined": True}
            for i in range(n)]


def _play_out(game, seed, prev=None, n=4, limit=20000):
    eng = get_engine(game)
    cfg = {"base_stake": 100, "seat_count": n, "round_no": 1}
    if prev:
        cfg["prev"] = prev
    st = eng.new_game(_seats(n), cfg, seed)
    events = []
    for _ in range(limit):
        out = eng.step_ai(st, _seats(n))
        if out is None:
            break
        st, evs = out
        events.extend(evs)
        json.dumps(st, ensure_ascii=False)   # state 必须始终可序列化
    return st, events


def test_engines_registered():
    assert set(engine_keys()) == {"guandan", "mahjong", "monopoly"}


def test_guandan_full_games_are_zero_sum():
    eng = get_engine("guandan")
    for seed in range(8):
        st, _ = _play_out("guandan", 1000 + seed * 7)
        assert st["phase"] == "finished"
        res = eng.result(st)
        deltas = [int(res["deltas"][str(i)]) for i in range(4)]
        assert sum(deltas) == 0
        assert sorted(res["ranking"]) == [0, 1, 2, 3]


def test_mahjong_full_games_are_zero_sum():
    eng = get_engine("mahjong")
    for seed in range(8):
        st, _ = _play_out("mahjong", 2000 + seed * 11)
        assert st["phase"] == "finished"
        res = eng.result(st)
        deltas = [int(res["deltas"][str(i)]) for i in range(4)]
        # 刮风下雨已即时结算并从 deltas 剔除，胡牌部分仍是零和
        assert sum(deltas) == 0
        total = [int(res["score"][str(i)]) for i in range(4)]
        assert sum(total) == 0


def test_guandan_tribute_flow():
    """连打多局应触发进贡 / 还贡，且每次进贡都有对应还贡。"""
    eng = get_engine("guandan")
    tribute = ret = 0
    for base in range(4):
        st = eng.new_game(_seats(), {"base_stake": 100, "seat_count": 4, "round_no": 1},
                          500 + base)
        for rnd in range(5):
            events = []
            for _ in range(8000):
                out = eng.step_ai(st, _seats())
                if out is None:
                    break
                st, evs = out
                events.extend(evs)
            assert st["phase"] == "finished"
            tribute += sum(1 for e in events if e.get("kind") == "tribute")
            ret += sum(1 for e in events if e.get("kind") == "return")
            res = eng.result(st)
            if res.get("match_over"):
                break
            st = eng.new_game(_seats(), {"base_stake": 100, "seat_count": 4,
                                         "round_no": rnd + 2,
                                         "prev": {"ranking": st["ranking"],
                                                  "team_levels": st["team_levels"]}},
                              9000 + base * 10 + rnd)
    assert tribute > 0
    assert tribute == ret   # 一张贡一张还


def test_guandan_tribute_plan_double_loss():
    """双下：胜方（0/2 同队）拿 1、2 名 → 对方两人都进贡，大的给头游、小的给二游，贡牌大者先出。"""
    st = {
        "level": 2,
        "hands": [
            [{"id": 1, "suit": "♠", "rank": 14, "joker": None}],   # seat0 头游（队 0）
            [{"id": 2, "suit": "♠", "rank": 13, "joker": None}],   # seat1 三游（队 1，进贡）
            [{"id": 3, "suit": "♠", "rank": 3, "joker": None}],    # seat2 二游（队 0）
            [{"id": 4, "suit": "♠", "rank": 5, "joker": None}],    # seat3 末游（队 1，进贡）
        ],
    }
    plan = _tribute_plan(st, [0, 2, 1, 3])
    assert plan["resisted"] is False
    assert len(plan["pairs"]) == 2
    # seat1 的 K 比 seat3 的 5 大 → 给头游 seat0
    big = next(p for p in plan["pairs"] if p["card"]["rank"] == 13)
    assert big["to"] == 0
    assert plan["leader"] == 1


def test_guandan_tribute_plan_single_loss():
    """单下：胜方拿 1、3 名 → 只有末游进贡。"""
    st = {
        "level": 2,
        "hands": [
            [{"id": 1, "suit": "♠", "rank": 14, "joker": None}],   # seat0 头游（队 0）
            [{"id": 2, "suit": "♠", "rank": 13, "joker": None}],   # seat1 二游（队 1）
            [{"id": 3, "suit": "♠", "rank": 3, "joker": None}],    # seat2 三游（队 0）
            [{"id": 4, "suit": "♠", "rank": 5, "joker": None}],    # seat3 末游（队 1，进贡）
        ],
    }
    plan = _tribute_plan(st, [0, 1, 2, 3])
    assert plan["resisted"] is False
    assert len(plan["pairs"]) == 1
    assert plan["pairs"][0]["from"] == 3
    assert plan["pairs"][0]["to"] == 0


def test_guandan_resist_tribute():
    """进贡方合计持有两张大王 → 抗贡，由头游先出。"""
    st = {
        "level": 2,
        "hands": [
            [{"id": 1, "suit": "♠", "rank": 14, "joker": None}],
            [{"id": 2, "suit": "♠", "rank": 3, "joker": None}],
            [{"id": 3, "suit": "♠", "rank": 13, "joker": None}],
            [{"id": 4, "suit": "", "rank": 0, "joker": "big"},
             {"id": 5, "suit": "", "rank": 0, "joker": "big"}],
        ],
    }
    plan = _tribute_plan(st, [0, 1, 2, 3])
    assert plan["resisted"] is True
    assert plan["pairs"] == []
    assert plan["leader"] == 0


def test_guandan_return_must_be_ten_or_less():
    assert _return_ok({"suit": "♠", "rank": 10, "joker": None}, 2)
    assert not _return_ok({"suit": "♠", "rank": 11, "joker": None}, 2)
    assert not _return_ok({"suit": "♠", "rank": 2, "joker": None}, 2)      # 级牌
    assert not _return_ok({"suit": "♥", "rank": 2, "joker": None}, 2)      # 逢人配
    assert not _return_ok({"suit": "", "rank": 0, "joker": "big"}, 2)      # 王


def test_guandan_patterns():
    lv = 2
    def C(suit, rank, cid):
        return {"id": cid, "suit": suit, "rank": rank, "joker": None}

    pair = detect_pattern([C("♠", 5, 1), C("♥", 5, 2)], lv)
    assert pair["type"] == "pair"
    straight = detect_pattern([C("♠", 3, 3), C("♥", 4, 4), C("♣", 5, 5),
                               C("♦", 6, 6), C("♠", 7, 7)], lv)
    assert straight["type"] == "straight"
    bomb = detect_pattern([C("♠", 9, 7), C("♥", 9, 8), C("♣", 9, 9), C("♦", 9, 10)], lv)
    assert bomb["type"] == "bomb"
    assert can_beat(bomb, straight)
    assert not can_beat(straight, bomb)


def test_guandan_wild_card_makes_bomb():
    """红桃级牌（逢人配）可补齐炸弹。"""
    lv = 7
    cards = [
        {"id": 1, "suit": "♠", "rank": 9, "joker": None},
        {"id": 2, "suit": "♣", "rank": 9, "joker": None},
        {"id": 3, "suit": "♦", "rank": 9, "joker": None},
        {"id": 4, "suit": "♥", "rank": 7, "joker": None},   # 逢人配
    ]
    pat = detect_pattern(cards, lv)
    assert pat["type"] == "bomb"


def test_mahjong_missing_blocks_hu():
    missing = "m"
    hand = [{"id": i, "suit": "s", "rank": 1} for i in range(13)] + \
           [{"id": 99, "suit": "m", "rank": 5}]
    assert has_missing(_counts(hand), missing) is True
    assert can_hu(hand, 0, missing) is False
    assert can_hu(hand, 0, None) is True or can_hu(hand, 0, None) is False  # 不抛异常


def test_mahjong_gang_payment_is_zero_sum():
    st = {"score": [0, 0, 0, 0], "gang_total": [0, 0, 0, 0]}
    events = []
    _gang_pay(st, 1, [0, 2, 3], 2, "an", events)
    assert st["score"] == [-2, 6, -2, -2]
    assert sum(st["score"]) == 0
    assert st["gang_total"] == st["score"]
    assert len(events) == 3 and all(e["kind"] == "gang_pay" for e in events)


def test_mahjong_score_seven_pairs():
    hand = []
    cid = 0
    for rank in (1, 2, 3, 4, 5, 6, 7):
        for _ in range(2):
            hand.append({"id": cid, "suit": "s", "rank": rank})
            cid += 1
    res = score_hu(hand, [])
    assert res["names"][0] == "七对"
    assert res["fan"] >= 4


def test_mahjong_discard_out_of_turn_rejected():
    eng = get_engine("mahjong")
    st = eng.new_game(_seats(), {"base_stake": 100, "seat_count": 4, "round_no": 1}, 42)
    # 定缺阶段：非当前席位应被拒
    turn = st["turn"]
    other = next(s for s in range(4) if s != turn)
    try:
        eng.apply(st, other, {"type": "missing", "suit": "m"})
        raise AssertionError("应当拒绝非当前席位的定缺")
    except TableError:
        pass


def test_guandan_level_text():
    assert level_text(2) == "2"
    assert level_text(14) == "A"
    assert level_text(15) == "A+"

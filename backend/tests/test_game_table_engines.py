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
    _advance_turn,
    _return_ok,
    _tribute_plan,
)
from app.games.mahjong import (
    can_hu,
    score_hu,
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
            # v2.46.23 进贡在 new_game 里自动完成，不再走 step_ai 事件流 → 从 history 统计
            # v2.46.70 改用结构化状态统计：_history 有 120 条裁剪上限，长局会把起局的
            # tribute/return 事件从头部裁掉（DanKS 接入后对局变长首次踩中），事后数
            # history 不再可靠；tribute.pairs / returns.done 是权威状态。
            tr = st.get("tribute") or {}
            tribute += len(tr.get("pairs") or [])
            ret += sum(1 for r in tr.get("returns") or [] if r.get("done"))
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
    """双下：胜方（0/2 同队）拿 1、2 名 → 对方两人都进贡（不区分三游/末游），
    贡牌由玩家手动选，故 plan 只给出「谁贡给谁」，先由三游选牌。"""
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
    assert plan["pairs"] == []                      # 贡牌手动选，此处不预置
    assert len(plan["givers"]) == 2
    assert {(g["from"], g["to"]) for g in plan["givers"]} == {(1, 0), (3, 2)}
    assert plan["turn"] == 1                        # 先由三游（seat1）选贡牌
    assert plan["leader"] is None


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
    assert len(plan["givers"]) == 1
    assert plan["givers"][0]["from"] == 3
    assert plan["givers"][0]["to"] == 0
    assert plan["turn"] == 3


def test_guandan_double_loss_ends_round_immediately():
    """双下（头游、二游同队）→ 本局立即结束，不再让其余两家争三游/末游。"""
    st = {
        "phase": "playing",
        "level": 2,
        "team_levels": [2, 2],
        "hands": [[], [], [], []],
        "finished": [0, 2],          # 0/2 同队（TEAM_OF: 0→队0, 2→队0）
        "turn": 1,
        "target": None,
        "last_play": None,
        "pass_count": 0,
        "history": [],
        "logs": [],
        "ranking": [],
        "result": None,
        "round_no": 1,
    }
    events = []
    _advance_turn(st, events)
    assert st["phase"] == "finished"
    assert st["ranking"][:2] == [0, 2]
    assert st["result"]["up"] == 3           # 双下 +3 级
    assert st["result"]["win_team"] == 0
    assert any(e.get("kind") == "finish" for e in events)


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


def test_mahjong_can_hu_basic():
    """v2.46.24 起无缺门概念（can_hu 的 missing 参数仅为兼容旧签名，恒忽略）。"""
    hand = []
    cid = 0
    for _ in range(4):                       # 345 三色齐刻 + 55 将 → 平胡
        for rank in (3, 4, 5):
            hand.append({"id": cid, "suit": "s", "rank": rank})
            cid += 1
    hand.append({"id": cid, "suit": "s", "rank": 9})
    cid += 1
    hand.append({"id": cid, "suit": "s", "rank": 9})
    assert can_hu(hand, 0) is True
    bad = [{"id": 100 + i, "suit": "s", "rank": r}
           for i, r in enumerate((1, 1, 2, 4, 6, 8, 9))]     # 杂乱不成型
    assert can_hu(bad, 0) is False


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
    # 出牌阶段：非当前席位打牌应被拒
    turn = st["turn"]
    other = next(s for s in range(4) if s != turn)
    tile = st["hands"][other][0]
    try:
        eng.apply(st, other, {"type": "discard", "tile_id": tile["id"]})
        raise AssertionError("应当拒绝非当前席位的出牌")
    except TableError:
        pass


def test_monopoly_last_three_settle_and_round_cap():
    """v2.46.25 终局口径：4 人局破产到只剩 3 人即按资产排名结算；2 人局 200 轮封顶。"""
    eng = get_engine("monopoly")
    st = eng.new_game(_seats(4), {"base_stake": 100, "seat_count": 4, "round_no": 1}, 7)
    st["alive"] = [True, False, True, True]
    events = []
    eng._check_end(st, events)
    assert st["phase"] == "finished"
    res = eng.result(st)
    assert res["winner"] in (0, 2, 3) and sorted(res["ranking"]) == [0, 1, 2, 3]

    duo = eng.new_game(_seats(2), {"base_stake": 100, "seat_count": 2, "round_no": 1}, 9)
    assert duo["turn_limit"] == 400            # 200 轮 × 2 人
    quart = eng.new_game(_seats(4), {"base_stake": 100, "seat_count": 4, "round_no": 1}, 9)
    assert quart["turn_limit"] == 800


def test_guandan_level_text():
    assert level_text(2) == "2"
    assert level_text(14) == "A"
    assert level_text(15) == "A+"

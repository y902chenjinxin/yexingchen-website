"""掼蛋服务端引擎（v2.44）。

两副牌 108 张，4 人各 27 张，座位 0/2 一队、1/3 一队。规则与前端 `utils/games/guandan.js`
保持一致（同屏练习用 JS，在线用本文件），差异仅在本文件补齐 PRD §6.1 的**进贡 / 还贡 / 抗贡**。

阶段机：
``tribute``（进贡，系统自动挑牌）→ ``return``（还贡，手动选 ≤10，30s 倒计时）
→ ``playing``（正常出牌）→ ``finished``（结算，含 ``deltas`` 底注倍数）。

牌值：大王 17 > 小王 16 > 级牌 15 > 其余 2..14。逢人配 = 红桃级牌，可当除王外任意牌。
"""
from __future__ import annotations

from app.games.base import TableEngine, TableError, copy_state, register, rng

SUITS = ["♠", "♥", "♣", "♦"]
RANK_TEXT = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
             10: "10", 11: "J", 12: "Q", 13: "K", 14: "A"}
JOKER_SMALL = 16
JOKER_BIG = 17
TEAM_OF = {0: 0, 1: 1, 2: 0, 3: 1}
MAX_LEVEL = 14
MIN_LEVEL = 2

PATTERN_NAME = {
    "single": "单张", "pair": "对子", "triple": "三张", "triple2": "三带二",
    "straight": "顺子", "tube": "三连对", "plate": "钢板",
    "bomb": "炸弹", "flushbomb": "同花顺", "rocket": "四大天王",
}


def level_text(lv: int) -> str:
    if lv > MAX_LEVEL:
        return "A+"
    return RANK_TEXT.get(lv, str(lv))


# ---------------- 牌工具 ----------------

def _is_wild(card: dict, level: int) -> bool:
    return (not card.get("joker")) and card.get("suit") == "♥" and card.get("rank") == level


def _card_value(card: dict, level: int) -> int:
    if card.get("joker"):
        return JOKER_BIG if card["joker"] == "big" else JOKER_SMALL
    return 15 if card.get("rank") == level else int(card["rank"])


def _rank_key(card: dict) -> int:
    if card.get("joker"):
        return JOKER_BIG if card["joker"] == "big" else JOKER_SMALL
    return int(card["rank"])


def _key_of_rank(rk: int, level: int) -> int:
    if rk >= 16:
        return rk
    return 15 if rk == level else rk


def _card_text(card: dict) -> str:
    if card.get("joker"):
        return "大王" if card["joker"] == "big" else "小王"
    return f"{card.get('suit', '')}{RANK_TEXT.get(int(card['rank']), card['rank'])}"


def _build_deck() -> list[dict]:
    cards: list[dict] = []
    i = 0
    for _ in range(2):
        for s in SUITS:
            for r in range(2, 15):
                cards.append({"id": i, "suit": s, "rank": r, "joker": None})
                i += 1
        cards.append({"id": i, "suit": "", "rank": 0, "joker": "small"})
        i += 1
        cards.append({"id": i, "suit": "", "rank": 0, "joker": "big"})
        i += 1
    return cards


def _sort_hand(hand: list[dict], level: int) -> list[dict]:
    return sorted(
        hand,
        key=lambda c: (-_card_value(c, level),
                       SUITS.index(c["suit"]) if c.get("suit") in SUITS else 9),
    )


def _deal(level: int, r) -> list[list[dict]]:
    deck = _build_deck()
    r.shuffle(deck)
    return [_sort_hand(deck[i * 27:(i + 1) * 27], level) for i in range(4)]


def _move_card(src: list[dict], dst: list[dict], card_id: int) -> dict | None:
    for idx, c in enumerate(src):
        if c["id"] == card_id:
            dst.append(src.pop(idx))
            return c
    return None


def _mk(kind: str, ln: int, key: int, bomb_level: float, cards: list[dict]) -> dict:
    return {"type": kind, "len": ln, "key": key, "bomb_level": bomb_level, "cards": cards}


# ---------------- 牌型识别（移植自 guandan.js） ----------------

def _seq_ranks(a: int, ln: int) -> list[int]:
    return [14 if (a + i) == 1 else (a + i) for i in range(ln)]


def _try_straight(rest: list[dict], w: int, same_suit: bool):
    if not rest:
        return None
    if any(c.get("joker") for c in rest):
        return None
    ranks = [int(c["rank"]) for c in rest]
    if len(set(ranks)) != len(ranks):
        return None
    if same_suit and len({c.get("suit") for c in rest}) > 1:
        return None
    for a in range(1, 11):
        seq = _seq_ranks(a, 5)
        if all(r in seq for r in ranks) and 5 - len(rest) == w:
            return {"top": seq[4]}
    return None


def _try_triple2(rest: list[dict], w: int, level: int):
    if any(c.get("joker") for c in rest):
        jokers = [c for c in rest if c.get("joker")]
        others = [c for c in rest if not c.get("joker")]
        if len(jokers) == 2 and jokers[0]["joker"] == jokers[1]["joker"]:
            if len(others) + w == 3 and (not others or len({int(c["rank"]) for c in others}) == 1):
                rk = int(others[0]["rank"]) if others else level
                return {"key": _key_of_rank(rk, level)}
        return None
    cnt: dict[int, int] = {}
    for c in rest:
        cnt[int(c["rank"])] = cnt.get(int(c["rank"]), 0) + 1
    for tr in list(cnt.keys()):
        for pr in list(cnt.keys()):
            if tr == pr:
                continue
            ct, cp = cnt[tr], cnt[pr]
            if ct > 3 or cp > 2 or ct + cp != len(rest):
                continue
            if max(0, 3 - ct) + max(0, 2 - cp) != w:
                continue
            return {"key": _key_of_rank(tr, level)}
    return None


def _try_tube(rest: list[dict], w: int):
    if not rest or any(c.get("joker") for c in rest):
        return None
    cnt: dict[int, int] = {}
    for c in rest:
        cnt[int(c["rank"])] = cnt.get(int(c["rank"]), 0) + 1
    for a in range(1, 13):
        seq = _seq_ranks(a, 3)
        need = used = 0
        ok = True
        for r in seq:
            c = cnt.get(r, 0)
            if c > 2:
                ok = False
                break
            need += max(0, 2 - c)
            used += min(2, c)
        if ok and used == len(rest) and need == w:
            return {"key": seq[2]}
    return None


def _try_plate(rest: list[dict], w: int):
    if not rest or any(c.get("joker") for c in rest):
        return None
    cnt: dict[int, int] = {}
    for c in rest:
        cnt[int(c["rank"])] = cnt.get(int(c["rank"]), 0) + 1
    for a in range(1, 14):
        seq = _seq_ranks(a, 2)
        need = used = 0
        ok = True
        for r in seq:
            c = cnt.get(r, 0)
            if c > 3:
                ok = False
                break
            need += max(0, 3 - c)
            used += min(3, c)
        if ok and used == len(rest) and need == w:
            return {"key": seq[1]}
    return None


def detect_pattern(cards: list[dict], level: int) -> dict | None:
    n = len(cards)
    if not n:
        return None
    wilds = [c for c in cards if _is_wild(c, level)]
    rest = [c for c in cards if not _is_wild(c, level)]
    w = len(wilds)

    if n == 1:
        return _mk("single", 1, _card_value(cards[0], level), 0, cards)
    if n == 4 and w == 0 and all(c.get("joker") for c in rest):
        return _mk("rocket", 4, 0, 99, cards)

    rks = [_rank_key(c) for c in rest]
    if not rest or len(set(rks)) == 1:
        if rest and rest[0].get("joker"):
            if n == 2 and len(rest) == 2 and rest[0]["joker"] == rest[1]["joker"]:
                return _mk("pair", 2, _key_of_rank(rks[0], level), 0, cards)
            return None
        rk = rks[0] if rest else level
        key = _key_of_rank(rk, level)
        if n == 2:
            return _mk("pair", 2, key, 0, cards)
        if n == 3:
            return _mk("triple", 3, key, 0, cards)
        if 4 <= n <= 8:
            return _mk("bomb", n, key, n, cards)
        return None

    if n == 5:
        fl = _try_straight(rest, w, True)
        if fl:
            return _mk("flushbomb", 5, fl["top"], 5.5, cards)
        st = _try_straight(rest, w, False)
        if st:
            return _mk("straight", 5, st["top"], 0, cards)
        t2 = _try_triple2(rest, w, level)
        if t2:
            return _mk("triple2", 5, t2["key"], 0, cards)
        return None

    if n == 6:
        tb = _try_tube(rest, w)
        if tb:
            return _mk("tube", 6, tb["key"], 0, cards)
        pl = _try_plate(rest, w)
        if pl:
            return _mk("plate", 6, pl["key"], 0, cards)
        return None
    return None


def can_beat(cand: dict | None, target: dict | None) -> bool:
    if not cand:
        return False
    if not target:
        return True
    if cand["type"] == "rocket":
        return True
    if target["type"] == "rocket":
        return False
    cb = cand.get("bomb_level") or 0
    tb = target.get("bomb_level") or 0
    if cb and tb:
        return cb > tb if cb != tb else cand["key"] > target["key"]
    if cb:
        return True
    if tb:
        return False
    if cand["type"] != target["type"] or cand["len"] != target["len"]:
        return False
    return cand["key"] > target["key"]


# ---------------- AI 候选生成（移植自 guandan.js） ----------------

def _build_seq(hand: list[dict], level: int, ranks: list[int], per_rank: int):
    used: set[int] = set()
    out: list[dict] = []
    need_wilds = 0
    for r in ranks:
        pool = [c for c in hand if c["id"] not in used and not _is_wild(c, level)
                and not c.get("joker") and int(c["rank"]) == r]
        take = min(per_rank, len(pool))
        for i in range(take):
            used.add(pool[i]["id"])
            out.append(pool[i])
        need_wilds += per_rank - take
    if need_wilds > 0:
        w = [c for c in hand if _is_wild(c, level) and c["id"] not in used][:need_wilds]
        if len(w) < need_wilds:
            return None
        for c in w:
            used.add(c["id"])
            out.append(c)
    return out


def _build_flush(hand: list[dict], level: int, suit: str, ranks: list[int]):
    used: set[int] = set()
    out: list[dict] = []
    need_wilds = 0
    for r in ranks:
        c = next((x for x in hand if x["id"] not in used and not _is_wild(x, level)
                  and x.get("suit") == suit and not x.get("joker") and int(x["rank"]) == r), None)
        if c:
            used.add(c["id"])
            out.append(c)
        else:
            need_wilds += 1
    if need_wilds > 0:
        w = [x for x in hand if _is_wild(x, level) and x["id"] not in used][:need_wilds]
        if len(w) < need_wilds:
            return None
        for c in w:
            used.add(c["id"])
            out.append(c)
    return out


def gen_candidates(hand: list[dict], level: int) -> list[list[dict]]:
    out: list[list[dict]] = []
    wilds = [c for c in hand if _is_wild(c, level)]
    non_wild = [c for c in hand if not _is_wild(c, level)]
    w = len(wilds)

    for c in hand:
        out.append([c])

    by_rank: dict[int, list[dict]] = {}
    for c in non_wild:
        by_rank.setdefault(_rank_key(c), []).append(c)

    for rk, arr in by_rank.items():
        can_wild = w if rk < 16 else 0
        mx = len(arr) + can_wild
        for size in (2, 3):
            if mx < size:
                continue
            take = min(len(arr), size)
            out.append(arr[:take] + wilds[:size - take])
        for size in range(4, mx + 1):
            take = min(len(arr), size)
            out.append(arr[:take] + wilds[:size - take])

    bigs = [c for c in non_wild if c.get("joker") == "big"]
    smalls = [c for c in non_wild if c.get("joker") == "small"]
    if len(bigs) >= 2 and len(smalls) >= 2:
        out.append(bigs[:2] + smalls[:2])

    for a in range(1, 11):
        seq = _seq_ranks(a, 5)
        st = _build_seq(hand, level, seq, 1)
        if st and len(st) == 5:
            out.append(st)
        for s in SUITS:
            fl = _build_flush(hand, level, s, seq)
            if fl and len(fl) == 5:
                out.append(fl)
    for a in range(1, 13):
        t = _build_seq(hand, level, _seq_ranks(a, 3), 2)
        if t and len(t) == 6:
            out.append(t)
    for a in range(1, 14):
        p = _build_seq(hand, level, _seq_ranks(a, 2), 3)
        if p and len(p) == 6:
            out.append(p)
    return out


def ai_choose(hand: list[dict], target: dict | None, level: int,
              last_is_teammate: bool = False) -> list[dict]:
    """AI 出牌：返回要出的牌，``[]`` 表示不要。target 为牌型 dict（None=起牌）。"""
    seen: set[str] = set()
    plays: list[tuple[list[dict], dict]] = []
    for cs in gen_candidates(hand, level):
        key = ",".join(str(c["id"]) for c in sorted(cs, key=lambda c: c["id"]))
        if key in seen:
            continue
        seen.add(key)
        p = detect_pattern(cs, level)
        if p:
            plays.append((cs, p))
    if not plays:
        return []

    fin = next((x for x in plays if len(x[0]) == len(hand)), None)
    if fin and (not target or can_beat(fin[1], target)):
        return fin[0]

    if not target:
        non_bomb = [x for x in plays if not x[1]["bomb_level"]]
        pool = non_bomb or plays
        pool.sort(key=lambda x: (-len(x[0]), x[1]["key"]))
        return pool[0][0]

    beats = [x for x in plays if can_beat(x[1], target)]
    if not beats:
        return []
    if last_is_teammate:
        return []
    beats.sort(key=lambda x: (x[1]["bomb_level"] or 0, x[1]["key"], len(x[0])))
    return beats[0][0]


# ---------------- 升级 ----------------

def _upgrade_for(order: list[int]) -> int:
    first = order[0]
    partner = (first + 2) % 4
    pos = order.index(partner)
    if pos == 1:
        return 3
    if pos == 2:
        return 2
    return 1


# ---------------- 进贡 / 还贡 ----------------

def _pick_tribute(hand: list[dict], level: int) -> dict:
    """贡牌：手上最大的一张，红桃级牌（逢人配）不用于进贡。"""
    pool = [c for c in hand if not _is_wild(c, level)]
    if not pool:
        pool = list(hand)
    return max(pool, key=lambda c: _card_value(c, level))


def _return_ok(card: dict, level: int) -> bool:
    """还贡：≤10，不能还王、不能还级牌（含逢人配）。"""
    if card.get("joker"):
        return False
    return int(card["rank"]) <= 10 and int(card["rank"]) != level


def _pick_return(hand: list[dict], level: int) -> dict:
    pool = [c for c in hand if _return_ok(c, level)]
    if not pool:
        pool = [c for c in hand if not c.get("joker") and not _is_wild(c, level)]
    if not pool:
        pool = list(hand)
    return min(pool, key=lambda c: _card_value(c, level))


def _tribute_plan(st: dict, ranking: list[int]) -> dict:
    """按 PRD §6.1 生成进贡方案：双下两人都进贡，单下末游进贡。"""
    first = int(ranking[0])
    partner = (first + 2) % 4
    pos = ranking.index(partner)
    losers = [int(ranking[2]), int(ranking[3])] if pos == 1 else [int(ranking[3])]

    big_count = sum(1 for s in losers for c in st["hands"][s] if c.get("joker") == "big")
    if big_count >= 2:
        # 抗贡：进贡方合计持有两张大王 → 不进贡，由上一局头游先出牌
        return {"pairs": [], "resisted": True, "leader": first, "returns": []}

    picks = [(s, _pick_tribute(st["hands"][s], st["level"])) for s in losers]
    pairs: list[dict] = []
    if pos == 1:
        picks.sort(key=lambda x: _card_value(x[1], st["level"]), reverse=True)
        for (s, card), to in zip(picks, [first, partner]):
            pairs.append({"from": s, "to": to, "card": card})
    else:
        pairs.append({"from": losers[0], "to": first, "card": picks[0][1]})

    leader = max(pairs, key=lambda p: _card_value(p["card"], st["level"]))["from"]
    return {"pairs": pairs, "resisted": False, "leader": leader, "returns": []}


def _run_tribute(st: dict, events: list[dict]) -> None:
    tr = st["tribute"]
    for p in tr["pairs"]:
        _move_card(st["hands"][p["from"]], st["hands"][p["to"]], p["card"]["id"])
        events.append({"kind": "tribute", "seat": p["from"], "to": p["to"], "card": p["card"]})
        _log(st, f"{p['from']} 号位向 {p['to']} 号位进贡 {_card_text(p['card'])}")
    if tr["pairs"]:
        tr["returns"] = [{"from": p["to"], "to": p["from"]} for p in tr["pairs"]]
        st["phase"] = "return"
        st["turn"] = tr["returns"][0]["from"]
    else:
        st["phase"] = "playing"
        st["turn"] = tr["leader"]
        st["target"] = None
        st["last_play"] = None
        st["pass_count"] = 0


def _do_return(st: dict, seat: int, card: dict, events: list[dict]) -> None:
    tr = st["tribute"]
    item = next((r for r in tr["returns"] if r["from"] == seat), None)
    if item is None:
        raise TableError("你不需要还贡")
    _move_card(st["hands"][seat], st["hands"][item["to"]], card["id"])
    events.append({"kind": "return", "seat": seat, "to": item["to"], "card": card})
    _log(st, f"{seat} 号位还贡 {_card_text(card)} 给 {item['to']} 号位")
    tr["returns"].remove(item)
    if tr["returns"]:
        st["turn"] = tr["returns"][0]["from"]
    else:
        st["phase"] = "playing"
        st["turn"] = tr["leader"]
        st["target"] = None
        st["last_play"] = None
        st["pass_count"] = 0


# ---------------- 出牌 ----------------

def _log(st: dict, text: str) -> None:
    logs = st.setdefault("logs", [])
    logs.insert(0, text)
    del logs[20:]


def _history(st: dict, item: dict) -> None:
    hist = st.setdefault("history", [])
    hist.append(item)
    if len(hist) > 120:
        del hist[:len(hist) - 120]


def _next_active(st: dict, frm: int) -> int:
    for i in range(1, 5):
        s = (frm + i) % 4
        if s not in st["finished"]:
            return s
    return frm


def _end_round(st: dict, events: list[dict]) -> None:
    for s in range(4):
        if s not in st["finished"]:
            st["finished"].append(s)
    ranking = st["finished"][:4]
    up = _upgrade_for(ranking)
    win_team = TEAM_OF[ranking[0]]
    st["team_levels"][win_team] = min(MAX_LEVEL + 1, int(st["team_levels"][win_team]) + up)
    match_over = int(st["team_levels"][win_team]) > MAX_LEVEL
    deltas = {str(s): (up if TEAM_OF[s] == win_team else -up) for s in range(4)}
    st["ranking"] = ranking
    st["result"] = {
        "finished": True, "ranking": ranking, "up": up, "win_team": win_team,
        "match_over": match_over, "deltas": deltas,
    }
    st["phase"] = "finished"
    st["turn"] = None
    st["target"] = None
    st["last_play"] = None
    events.append({"kind": "finish", "ranking": ranking, "up": up, "win_team": win_team})
    _log(st, f"本局结束，{win_team} 队升 {up} 级")
    _history(st, {"kind": "finish", "ranking": ranking, "up": up, "win_team": win_team})


def _advance_turn(st: dict, events: list[dict]) -> None:
    if st["phase"] != "playing":
        return
    if len(st["finished"]) >= 3:
        _end_round(st, events)
        return
    actives = [s for s in range(4) if s not in st["finished"]]
    if len(actives) <= 1:
        _end_round(st, events)
        return
    tgt = st.get("target")
    if tgt:
        need = len([s for s in actives if s != tgt["seat"]])
        if st.get("pass_count", 0) >= need:
            lead = tgt["seat"]
            if lead not in st["finished"]:
                st["turn"] = lead
            else:
                partner = (lead + 2) % 4
                st["turn"] = partner if partner not in st["finished"] else _next_active(st, lead)
            st["target"] = None
            st["pass_count"] = 0
            st["last_play"] = None
            _log(st, "本轮结束，重新起牌")
            return
    st["turn"] = _next_active(st, st["turn"])


def _do_play(st: dict, seat: int, cards: list[dict], events: list[dict]) -> None:
    pat = detect_pattern(cards, st["level"])
    if not pat:
        raise TableError("这不是合法牌型")
    tgt = st.get("target")
    if not can_beat(pat, tgt["pattern"] if tgt else None):
        raise TableError("压不过上一手")
    ids = {c["id"] for c in cards}
    st["hands"][seat] = [c for c in st["hands"][seat] if c["id"] not in ids]
    st["target"] = {"seat": seat, "cards": cards, "pattern": pat}
    st["last_play"] = {"seat": seat, "cards": cards, "pattern": pat}
    st["pass_count"] = 0
    events.append({"kind": "play", "seat": seat, "cards": cards, "pattern": pat})
    _history(st, {"kind": "play", "seat": seat, "cards": cards,
                  "pattern": {k: pat[k] for k in ("type", "len", "key", "bomb_level")}})
    _log(st, f"{seat} 号位出「{PATTERN_NAME.get(pat['type'], pat['type'])}」")
    if not st["hands"][seat] and seat not in st["finished"]:
        st["finished"].append(seat)
        _log(st, f"{seat} 号位出完，第 {len(st['finished'])} 名")
    _advance_turn(st, events)


def _do_pass(st: dict, seat: int, events: list[dict]) -> None:
    if not st.get("target"):
        raise TableError("本轮由你先出，必须出牌")
    st["pass_count"] = int(st.get("pass_count", 0)) + 1
    events.append({"kind": "pass", "seat": seat})
    _history(st, {"kind": "pass", "seat": seat})
    _log(st, f"{seat} 号位不要")
    _advance_turn(st, events)


# ---------------- 投影 ----------------

def _pub_pattern(pat: dict | None) -> dict | None:
    if not pat:
        return None
    return {"type": pat["type"], "len": pat["len"], "key": pat["key"],
            "bomb_level": pat.get("bomb_level") or 0,
            "name": PATTERN_NAME.get(pat["type"], pat["type"])}


def _pub_play(p: dict | None) -> dict | None:
    if not p:
        return None
    return {"seat": p["seat"], "cards": p["cards"], "pattern": _pub_pattern(p["pattern"])}


@register
class GuandanEngine(TableEngine):
    key = "guandan"
    seat_count = 4
    min_humans = 2

    # ---------- 生命周期 ----------

    def new_game(self, seats: list[dict], config: dict, seed: int) -> dict:
        r = rng(seed)
        prev = config.get("prev") or {}
        tl = prev.get("team_levels") or [MIN_LEVEL, MIN_LEVEL]
        team_levels = [int(tl[0]), int(tl[1])] if len(tl) >= 2 else [MIN_LEVEL, MIN_LEVEL]
        ranking_prev = [int(x) for x in (prev.get("ranking") or [])]

        level = MIN_LEVEL
        if len(ranking_prev) == 4:
            wt = TEAM_OF.get(ranking_prev[0], 0)
            level = min(MAX_LEVEL, team_levels[wt])

        st = {
            "phase": "playing",
            "level": level,
            "team_levels": team_levels,
            "hands": _deal(level, r),
            "turn": int(ranking_prev[0]) if len(ranking_prev) == 4 else r.randrange(4),
            "target": None,
            "last_play": None,
            "pass_count": 0,
            "finished": [],
            "history": [],
            "logs": [],
            "tribute": None,
            "ranking": [],
            "result": None,
            "round_no": int(config.get("round_no") or 1),
        }
        if len(ranking_prev) == 4:
            plan = _tribute_plan(st, ranking_prev)
            if plan["pairs"] or plan["resisted"]:
                st["tribute"] = plan
                st["phase"] = "tribute"
                st["turn"] = None
                _log(st, "抗贡成功，不进贡" if plan["resisted"] else "进贡阶段")
        return st

    def view(self, state: dict, seat: int) -> dict:
        st = state
        players = [
            {
                "seat": s,
                "hand_count": len(st["hands"][s]),
                "finished": s in st["finished"],
                "rank": (st["finished"].index(s) + 1) if s in st["finished"] else 0,
                "is_turn": st.get("turn") == s,
                "team": TEAM_OF.get(s, 0),
            }
            for s in range(4)
        ]
        me = {"seat": seat, "hand": st["hands"][seat] if 0 <= seat < 4 else []}
        if st["phase"] == "return" and st.get("turn") == seat:
            me["return_pending"] = True
            me["return_options"] = [c for c in st["hands"][seat] if _return_ok(c, st["level"])]
        else:
            me["return_pending"] = False
        return {
            "phase": st["phase"],
            "turn": st.get("turn"),
            "level": st["level"],
            "level_text": level_text(st["level"]),
            "team_levels": st["team_levels"],
            "team_levels_text": [level_text(st["team_levels"][0]), level_text(st["team_levels"][1])],
            "round_no": st.get("round_no", 1),
            "players": players,
            "me": me,
            "target": _pub_play(st.get("target")),
            "last_play": _pub_play(st.get("last_play")),
            "pass_count": st.get("pass_count", 0),
            "history": st.get("history", [])[-60:],
            "logs": st.get("logs", [])[:10],
            "tribute": st.get("tribute"),
            "result": st.get("result"),
        }

    def apply(self, state: dict, seat: int, action: dict) -> tuple[dict, list[dict]]:
        st = copy_state(state)
        events: list[dict] = []
        act = str(action.get("type") or "")

        if st["phase"] == "return":
            if seat != st.get("turn"):
                raise TableError("还没轮到你")
            cid = action.get("card_id")
            if cid is None:
                raise TableError("请选择要还的牌")
            card = next((c for c in st["hands"][seat] if c["id"] == int(cid)), None)
            if card is None:
                raise TableError("这张牌不在你手里")
            if not _return_ok(card, st["level"]):
                raise TableError("还贡必须是 10 及以下的非王、非级牌")
            _do_return(st, seat, card, events)
            return st, events

        if st["phase"] != "playing":
            raise TableError("当前不能出牌")
        if seat != st.get("turn"):
            raise TableError("还没轮到你")

        if act == "pass":
            _do_pass(st, seat, events)
        elif act == "play":
            ids = action.get("card_ids") or action.get("cards") or []
            by_id = {c["id"]: c for c in st["hands"][seat]}
            cards = []
            for cid in ids:
                c = by_id.get(int(cid))
                if c is None:
                    raise TableError("出的牌不在你手里")
                cards.append(c)
            if not cards:
                raise TableError("至少选一张牌")
            _do_play(st, seat, cards, events)
        else:
            raise TableError("未知动作")
        return st, events

    def step_ai(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        from app.games.base import ai_seats

        st = copy_state(state)
        ai = ai_seats(seats)
        events: list[dict] = []

        if st["phase"] == "tribute":
            _run_tribute(st, events)
            return st, events
        if st["phase"] == "return":
            if st.get("turn") in ai:
                seat = st["turn"]
                card = _pick_return(st["hands"][seat], st["level"])
                _do_return(st, seat, card, events)
                return st, events
            return None
        if st["phase"] != "playing":
            return None
        cur = st.get("turn")
        if cur is None or cur not in ai:
            return None

        tgt = st.get("target")
        last_is_teammate = bool(tgt) and TEAM_OF.get(tgt["seat"]) == TEAM_OF.get(cur)
        pick = ai_choose(st["hands"][cur], tgt["pattern"] if tgt else None,
                         st["level"], last_is_teammate)
        if pick:
            _do_play(st, cur, pick, events)
        else:
            _do_pass(st, cur, events)
        return st, events

    def on_timeout(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        from app.games.base import ai_seats

        st = copy_state(state)
        if st["phase"] != "return":
            return None
        seat = st.get("turn")
        if seat is None or seat in ai_seats(seats):
            return None
        events: list[dict] = []
        card = _pick_return(st["hands"][seat], st["level"])
        _do_return(st, seat, card, events)
        _log(st, f"{seat} 号位还贡超时，自动代还")
        return st, events

    def result(self, state: dict) -> dict | None:
        return state.get("result")

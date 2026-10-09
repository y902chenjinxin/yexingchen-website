"""四川麻将 · 胡牌即结束 服务端引擎（v2.46.17）。

万(m)/条(s)/筒(p) 各 1–9 共 108 张，**另加字牌：箭牌（中/發/白）+ 风牌（东南西北）
各 4 张（v2.46.15 起加箭牌、v2.46.17 起加风牌，共 136 张）**。字牌只能刻/对、不成顺子。
规则与前端 `utils/games/mahjong.js` 一致，本文件补齐 PRD §6.2 的**刮风下雨**
（明杠即时收 1 倍底注 / 暗杠即时收 2 倍底注）。

阶段机：``playing``（摸打 / 碰杠胡）→ ``finished``。
**v2.46.17 起取消定缺**（夜星要求「单纯的胡牌规则」）：开局庄家直接起手摸牌，
手上不再有缺门限制，碰/杠/胡只看牌型。``missing`` 字段保留为全 None 以兼容旧房态。
**胡牌即结束**（v2.46.10 起，不再是血战到底）：任意一家胡牌（自摸或点炮）本局立即收摊，
其余人不补摸补打；一炮只取**一家**胡（放炮者下家起逆时针就近优先），不存在一炮多响。
牌墙摸完仍无人胡 = 流局。
**庄家轮换（v2.46.17）**：下一局由本局胡牌者坐庄先出牌（流局则庄家下移一位）。

``state["score"]`` 以**底注倍数**为单位累计（含刮风下雨的即时收豆），
路由层据此换算成豆子结算；刮风下雨另外落 ``gang_pay`` 事件供即时提示。
"""
from __future__ import annotations

from app.games.base import TableEngine, TableError, copy_state, register, rng

SUITS = ["m", "s", "p", "z"]
SUIT_NAME = {"m": "万", "s": "条", "p": "筒", "z": "字"}
HONOR_NAME = {1: "红中", 2: "发财", 3: "白板", 4: "东风", 5: "南风", 6: "西风", 7: "北风"}
RANKS = {"m": 9, "s": 9, "p": 9, "z": 7}
RANK_TEXT = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}

# 刮风下雨：明杠（直杠）放杠者付 1 倍底注；暗杠每家付 2 倍；补杠每家付 1 倍
GANG_MING = 1
GANG_AN = 2
GANG_BU = 1


def idx_of(suit: str, rank: int) -> int:
    return SUITS.index(suit) * 9 + (rank - 1)


def tile_of(i: int) -> dict:
    return {"suit": SUITS[i // 9], "rank": (i % 9) + 1}


def tile_text(t: dict) -> str:
    if t["suit"] == "z":
        return HONOR_NAME.get(t["rank"], str(t["rank"]))
    return f"{RANK_TEXT.get(t['rank'], t['rank'])}{SUIT_NAME.get(t['suit'], t['suit'])}"


def _build_deck() -> list[dict]:
    tiles: list[dict] = []
    i = 0
    for suit in SUITS:
        for rank in range(1, RANKS[suit] + 1):
            for _ in range(4):
                tiles.append({"id": i, "suit": suit, "rank": rank})
                i += 1
    return tiles


def _sort_hand(hand: list[dict]) -> list[dict]:
    return sorted(hand, key=lambda t: idx_of(t["suit"], t["rank"]))


def _counts(tiles: list[dict]) -> list[int]:
    c = [0] * 36
    for t in tiles:
        c[idx_of(t["suit"], t["rank"])] += 1
    return c


# ---------------- 和牌判定 ----------------

def _try_sets(c: list[int], need: int) -> bool:
    if need == 0:
        return all(x == 0 for x in c)
    i = 0
    while i < 36 and c[i] == 0:
        i += 1
    if i == 36:
        return False
    if c[i] >= 3:
        c[i] -= 3
        ok = _try_sets(c, need - 1)
        c[i] += 3
        if ok:
            return True
    rank = i % 9
    if i < 27 and rank <= 6 and c[i + 1] > 0 and c[i + 2] > 0:
        c[i] -= 1
        c[i + 1] -= 1
        c[i + 2] -= 1
        ok = _try_sets(c, need - 1)
        c[i] += 1
        c[i + 1] += 1
        c[i + 2] += 1
        if ok:
            return True
    return False


def is_standard_hu(c: list[int], meld_count: int) -> bool:
    need = 4 - meld_count
    for i in range(36):
        if c[i] >= 2:
            c[i] -= 2
            ok = _try_sets(c, need)
            c[i] += 2
            if ok:
                return True
    return False


def is_seven_pairs(c: list[int]) -> dict:
    pairs = quads = 0
    for i in range(36):
        n = c[i]
        if n == 0:
            continue
        if n % 2 != 0:
            return {"ok": False, "quads": 0}
        pairs += n // 2
        if n == 4:
            quads += 1
    return {"ok": pairs == 7, "quads": quads}


def is_flush(c: list[int]) -> bool:
    used = {i // 9 for i in range(36) if c[i] > 0}
    return len(used) == 1


def is_all_eyes(c: list[int]) -> bool:
    for i in range(36):
        if c[i] == 0:
            continue
        if i >= 27:
            return False   # 字牌不算将将胡的 2/5/8
        if ((i % 9) + 1) not in (2, 5, 8):
            return False
    return True


def _is_all_triplets_hand(ch: list[int], meld_count: int) -> bool:
    for i in range(36):
        if ch[i] >= 2:
            copy = ch[:]
            copy[i] -= 2
            if all(copy[j] % 3 == 0 for j in range(36)):
                return True
    return False


def can_hu(hand: list[dict], meld_count: int, missing: str | None = None, seven_ok: bool = True) -> bool:
    """和牌判定。``missing`` 参数保留仅为兼容旧调用点（v2.46.17 起无缺门概念，恒忽略）。"""
    c = _counts(hand)
    if is_standard_hu(c, meld_count):
        return True
    if seven_ok and meld_count == 0 and len(hand) == 14 and is_seven_pairs(c)["ok"]:
        return True
    return False


def score_hu(hand: list[dict], melds: list[dict], flags: dict | None = None) -> dict:
    flags = flags or {}
    names = ["平胡"]
    fan = 1
    all_tiles = list(hand)
    for m in melds:
        all_tiles.extend([m["tile"]] * (4 if m["type"] in ("kong", "ankong", "bugang") else 3))
    c = _counts(all_tiles)
    ch = _counts(hand)
    meld_count = len(melds)

    seven = is_seven_pairs(ch) if (meld_count == 0 and len(hand) == 14) else {"ok": False, "quads": 0}
    if seven["ok"]:
        fan = 8 if seven["quads"] > 0 else 4
        names = ["龙七对" if seven["quads"] > 0 else "七对"]
    elif _is_all_triplets_hand(ch, meld_count) and all(
            m["type"] in ("pong", "kong", "ankong", "bugang") for m in melds):
        fan = 2
        names = ["对对胡"]

    if is_all_eyes(c):
        fan = max(fan, 4)
        names.append("将将胡")
    if is_flush(c):
        fan = max(fan, 4)
        names.append("清一色")
    if meld_count == 4 and len(hand) == 2:
        fan = max(fan, 4)
        names.append("金钩钓")

    gen = sum(1 for i in range(36) if c[i] == 4)
    if gen:
        fan += gen
        names.append(f"根×{gen}")

    if flags.get("gang_flower"):
        fan += 1
        names.append("杠上花")
    if flags.get("gang_pao"):
        fan += 1
        names.append("杠上炮")
    if flags.get("qiang_gang"):
        fan += 1
        names.append("抢杠胡")
    if flags.get("haidi"):
        fan += 1
        names.append("海底捞月")
    return {"fan": fan, "names": names}


def ting_tiles(hand: list[dict], meld_count: int, missing: str | None = None) -> list[dict]:
    out: list[dict] = []
    if len(hand) % 3 != 1:
        return out
    for suit in SUITS:
        for rank in range(1, RANKS[suit] + 1):
            probe = {"id": -1, "suit": suit, "rank": rank}
            if can_hu(hand + [probe], meld_count):
                out.append({"suit": suit, "rank": rank})
    return out


def shanten(hand: list[dict], meld_count: int = 0) -> int:
    c = _counts(hand)
    need = 4 - meld_count
    best = 8
    eyes = [-1] + [i for i in range(36) if c[i] >= 2]
    for e in eyes:
        copy = c[:]
        if e >= 0:
            copy[e] -= 2
        sets = 0
        for i in range(36):
            while copy[i] >= 3:
                copy[i] -= 3
                sets += 1
        # 顺子只在数字牌（i<27）里成立；字牌没有任何顺子搭法
        for i in range(27):
            rank = i % 9
            while rank <= 6 and copy[i] > 0 and copy[i + 1] > 0 and copy[i + 2] > 0:
                copy[i] -= 1
                copy[i + 1] -= 1
                copy[i + 2] -= 1
                sets += 1
        partials = 0
        rest = copy[:]
        for i in range(36):
            while rest[i] >= 2 and sets + partials < need:
                rest[i] -= 2
                partials += 1
        for i in range(27):
            rank = i % 9
            while rank <= 7 and rest[i] > 0 and rest[i + 1] > 0 and sets + partials < need:
                rest[i] -= 1
                rest[i + 1] -= 1
                partials += 1
        for i in range(27):
            rank = i % 9
            while rank <= 6 and rest[i] > 0 and rest[i + 2] > 0 and sets + partials < need:
                rest[i] -= 1
                rest[i + 2] -= 1
                partials += 1
        m = min(sets, need)
        p = min(partials, need - m)
        s = (need - m) * 2 - p - (1 if e >= 0 else 0)
        if s < best:
            best = s

    if meld_count == 0:
        pairs = kinds = 0
        for i in range(36):
            if c[i] > 0:
                kinds += 1
            pairs += c[i] // 2
        sp = 6 - pairs + max(0, 7 - kinds)
        if sp < best:
            best = sp
    return best


# ---------------- AI ----------------

def _tile_score(c: list[int], i: int) -> int:
    rank = (i % 9) + 1
    s = 0
    if c[i] >= 3:
        s += 6
    elif c[i] == 2:
        s += 4
    if i >= 27:
        if c[i] == 1:
            s -= 1   # 孤张字牌没有顺子搭法，价值最低
        return s
    if 3 <= rank <= 7:
        s += 2
    if (i + 1 < 27 and c[i + 1] > 0) or (i - 1 >= 0 and c[i - 1] > 0):
        s += 1
    if i % 9 <= 7 and c[i + 1] > 0:
        s += 1
    if i % 9 >= 1 and c[i - 1] > 0:
        s += 1
    return s


def ai_discard(hand: list[dict], meld_count: int, missing: str | None = None) -> dict:
    """AI 选打。``missing`` 仅为兼容旧签名（v2.46.17 起无缺门）。"""
    c = _counts(hand)
    best_tile = hand[0]
    best_key = -10 ** 9
    seen: set[str] = set()
    for t in hand:
        k = f"{t['suit']}{t['rank']}"
        if k in seen:
            continue
        seen.add(k)
        rest = [x for x in hand if x["id"] != t["id"]]
        sh = shanten(rest, meld_count)
        u = len(ting_tiles(rest, meld_count))
        s = _tile_score(c, idx_of(t["suit"], t["rank"]))
        key = -sh * 100 + u * 3 + s
        if key > best_key:
            best_key = key
            best_tile = t
    return best_tile


def ai_want_pong(hand: list[dict], tile: dict, meld_count: int, missing: str | None = None) -> bool:
    c = _counts(hand)
    same = c[idx_of(tile["suit"], tile["rank"])]
    if same < 2:
        return False
    before = shanten(hand, meld_count)
    after = shanten([t for t in hand if not (t["suit"] == tile["suit"] and t["rank"] == tile["rank"])][2:],
                    meld_count + 1)
    return after < before or same >= 3


def ai_want_kong(hand: list[dict], tile: dict, missing: str | None = None) -> bool:
    return _counts(hand)[idx_of(tile["suit"], tile["rank"])] >= 3


def find_ankongs(hand: list[dict]) -> list[dict]:
    c = _counts(hand)
    return [tile_of(i) for i in range(36) if c[i] == 4]


def find_bugangs(hand: list[dict], melds: list[dict]) -> list[dict]:
    c = _counts(hand)
    out = []
    for m in melds:
        if m["type"] != "pong":
            continue
        if c[idx_of(m["tile"]["suit"], m["tile"]["rank"])] >= 1:
            out.append(m["tile"])
    return out


# ---------------- 牌堆工具 ----------------

def _take_n(hand: list[dict], tile: dict, n: int) -> None:
    left = n
    for idx in range(len(hand) - 1, -1, -1):
        if left <= 0:
            break
        t = hand[idx]
        if t["suit"] == tile["suit"] and t["rank"] == tile["rank"]:
            hand.pop(idx)
            left -= 1


def _remove_discard(discards: list[dict], tile: dict) -> None:
    for idx in range(len(discards) - 1, -1, -1):
        d = discards[idx]
        if d["suit"] == tile["suit"] and d["rank"] == tile["rank"]:
            discards.pop(idx)
            return


def _gang_pay(st: dict, winner: int, payers: list[int], amount: int,
              sub: str, events: list[dict]) -> None:
    """刮风下雨即时结算：把 amount 分从每个 payer 划到 winner（已胡的不再付）。"""
    for p in payers:
        if p == winner:
            continue
        st["score"][p] -= amount
        st["score"][winner] += amount
        st["gang_total"][p] -= amount
        st["gang_total"][winner] += amount
        events.append({"kind": "gang_pay", "seat": winner, "from": p,
                       "amount": amount, "sub": sub})


def _log(st: dict, text: str) -> None:
    logs = st.setdefault("logs", [])
    logs.insert(0, text)
    del logs[20:]


def _history(st: dict, item: dict) -> None:
    hist = st.setdefault("history", [])
    hist.append(item)
    if len(hist) > 160:
        del hist[:len(hist) - 160]


@register
class MahjongEngine(TableEngine):
    key = "mahjong"
    seat_count = 4
    min_humans = 2

    # ---------- 生命周期 ----------

    def new_game(self, seats: list[dict], config: dict, seed: int) -> dict:
        r = rng(seed)
        prev = config.get("prev") or {}
        # 庄家轮换（v2.46.17）：由上一局胡牌者坐庄；流局则庄家下移一位（旧字段兜底）
        dealer = int((prev.get("result") or {}).get("dealer_next")
                     or prev.get("dealer_next") or 0) % 4
        deck = _build_deck()
        r.shuffle(deck)
        hands = [_sort_hand(deck[i * 13:(i + 1) * 13]) for i in range(4)]
        wall = deck[52:]
        st = {
            "phase": "playing",           # v2.46.17 起无定缺阶段，庄家直接起手
            "dealer": dealer,
            "wall": wall,
            "hands": hands,
            "melds": [[], [], [], []],
            "discards": [[], [], [], []],
            "missing": [None, None, None, None],   # 保留字段（恒 None），旧房态兼容
            "turn": dealer,
            "last_draw": None,
            "last_discard": None,
            "claim": None,
            "after_kong": False,
            "hu": [],
            "hu_info": {},
            "score": [0, 0, 0, 0],        # 总账（含刮风下雨），仅用于展示
            "gang_total": [0, 0, 0, 0],   # 刮风下雨已即时结算的部分（结算时从 deltas 里剔除）
            "history": [],
            "logs": [],
            "result": None,
            "round_no": int(config.get("round_no") or 1),
        }
        _log(st, f"对局开始，{dealer} 号位坐庄（上一局胡牌者先出）")
        self._draw(st, dealer, [])   # 庄家起手第一摸（new_game 无事件通道，直接丢弃）
        return st

    # ---------- 投影 ----------

    def view(self, state: dict, seat: int) -> dict:
        st = state
        players = []
        for s in range(4):
            players.append({
                "seat": s,
                "hand_count": len(st["hands"][s]),
                "melds": st["melds"][s],
                "discards": st["discards"][s],
                "is_turn": st.get("turn") == s,
                "hu": s in st["hu"],
                "hu_info": st["hu_info"].get(str(s)),
                "score": st["score"][s],
            })
        me = {
            "seat": seat,
            "hand": st["hands"][seat] if 0 <= seat < 4 else [],
            "melds": st["melds"][seat] if 0 <= seat < 4 else [],
            "last_draw": st.get("last_draw") if st.get("turn") == seat else None,
        }
        cl = st.get("claim")
        if cl and cl.get("seat") == seat:
            me["options"] = list(cl.get("options") or []) + ["pass"]
        elif st["phase"] == "playing" and st.get("turn") == seat and not cl:
            opts = ["discard"]
            if can_hu(st["hands"][seat], len(st["melds"][seat])):
                opts.append("hu")
            me["ankongs"] = find_ankongs(st["hands"][seat])
            me["bugangs"] = find_bugangs(st["hands"][seat], st["melds"][seat])
            if me["ankongs"]:
                opts.append("ankong")
            if me["bugangs"]:
                opts.append("bugang")
            me["options"] = opts
        else:
            me["options"] = []
        return {
            "phase": st["phase"],
            "turn": st.get("turn"),
            "dealer": st.get("dealer", 0),
            "round_no": st.get("round_no", 1),
            "wall_left": len(st["wall"]),
            "players": players,
            "me": me,
            "claim": ({"seat": cl["seat"], "tile": cl["tile"], "from": cl["from"],
                       "options": cl.get("options")} if cl else None),
            "last_discard": st.get("last_discard"),
            "history": st.get("history", [])[-80:],
            "logs": st.get("logs", [])[:10],
            "result": st.get("result"),
        }

    # ---------- 动作 ----------

    def apply(self, state: dict, seat: int, action: dict) -> tuple[dict, list[dict]]:
        st = copy_state(state)
        events: list[dict] = []
        act = str(action.get("type") or "")

        if st["phase"] != "playing":
            raise TableError("牌局已结束")

        cl = st.get("claim")
        if cl is not None:
            if seat != cl.get("seat"):
                raise TableError("现在不是你的响应")
            if act == "pass":
                cl["passed"] = list(cl.get("passed") or []) + [seat]
                _history(st, {"kind": "claim_pass", "seat": seat})
                cand = self._find_claim(st, cl["tile"], cl["from"], cl["passed"])
                if cand:
                    cl["seat"], cl["options"] = cand
                    st["turn"] = cand[0]
                else:
                    st["claim"] = None
                    _log(st, f"{cl['tile'] and tile_text(cl['tile'])} 无人要")
                    self._advance_draw_from(st, cl["from"], events)
            elif act in ("pong", "kong", "hu"):
                self._resolve_claim(st, seat, act, events)
            else:
                raise TableError("未知的响应")
            return st, events

        if seat != st.get("turn"):
            raise TableError("还没轮到你")

        if act == "discard":
            self._do_discard(st, seat, action, events)
        elif act == "hu":
            if not can_hu(st["hands"][seat], len(st["melds"][seat])):
                raise TableError("现在不能和牌")
            self._do_hu(st, seat, st["hands"][seat], None, True, events)
            self._advance_draw_from(st, seat, events)
        elif act == "ankong":
            tile = action.get("tile") or {}
            cands = find_ankongs(st["hands"][seat])
            hit = next((t for t in cands if t["suit"] == tile.get("suit") and t["rank"] == tile.get("rank")), None)
            if hit is None:
                raise TableError("没有这张牌的暗杠")
            _take_n(st["hands"][seat], hit, 4)
            st["melds"][seat].append({"type": "ankong", "tile": hit, "from": seat})
            _gang_pay(st, seat, [s for s in range(4) if s != seat and s not in st["hu"]],
                           GANG_AN, "ankong", events)
            self._draw(st, seat, events, after_kong=True)
        elif act == "bugang":
            tile = action.get("tile") or {}
            cands = find_bugangs(st["hands"][seat], st["melds"][seat])
            hit = next((t for t in cands if t["suit"] == tile.get("suit") and t["rank"] == tile.get("rank")), None)
            if hit is None:
                raise TableError("没有这张牌的补杠")
            _take_n(st["hands"][seat], hit, 1)
            for m in st["melds"][seat]:
                if m["type"] == "pong" and m["tile"]["suit"] == hit["suit"] and m["tile"]["rank"] == hit["rank"]:
                    m["type"] = "bugang"
                    break
            _gang_pay(st, seat, [s for s in range(4) if s != seat and s not in st["hu"]],
                           GANG_BU, "bugang", events)
            self._draw(st, seat, events, after_kong=True)
        else:
            raise TableError("未知动作")
        return st, events

    # ---------- 内部推进 ----------

    def _draw(self, st: dict, seat: int, events: list[dict], after_kong: bool = False) -> None:
        if not st["wall"]:
            self._end_game(st, events)
            return
        t = st["wall"].pop()
        st["hands"][seat].append(t)
        st["hands"][seat] = _sort_hand(st["hands"][seat])
        st["last_draw"] = t
        st["turn"] = seat
        st["after_kong"] = bool(after_kong)
        events.append({"kind": "draw", "seat": seat})

    def _advance_draw_from(self, st: dict, frm: int, events: list[dict]) -> None:
        # 胡牌即结束：只要有一家胡了（st["hu"] 非空），本局立刻收摊，不再补摸补打。
        if st["hu"] or not st["wall"]:
            self._end_game(st, events)
            return
        nxt = self._next_alive(st, frm)
        if nxt is None:
            self._end_game(st, events)
            return
        self._draw(st, nxt, events)

    def _next_alive(self, st: dict, frm: int) -> int | None:
        """胡牌即结束后本方法只在无人胡时用到（理论上恒有解）；保留给防御性调用。"""
        for i in range(1, 5):
            s = (frm + i) % 4
            if s not in st["hu"]:
                return s
        return None

    def _do_discard(self, st: dict, seat: int, action: dict, events: list[dict]) -> None:
        tid = action.get("tile_id")
        tile = next((t for t in st["hands"][seat] if t["id"] == int(tid)), None) if tid is not None else None
        if tile is None:
            raise TableError("这张牌不在你手里")
        st["hands"][seat] = [t for t in st["hands"][seat] if t["id"] != tile["id"]]
        st["discards"][seat].append(tile)
        st["last_discard"] = {"seat": seat, "tile": tile}
        st["last_draw"] = None
        was_after_kong = bool(st.get("after_kong"))
        st["after_kong"] = False
        events.append({"kind": "discard", "seat": seat, "tile": tile})
        _history(st, {"kind": "discard", "seat": seat, "tile": tile})
        _log(st, f"{seat} 号位打 {tile_text(tile)}")

        cand = self._find_claim(st, tile, seat, [])
        if cand:
            st["claim"] = {"tile": tile, "from": seat, "seat": cand[0],
                           "options": cand[1], "passed": [], "after_kong": was_after_kong}
            st["turn"] = cand[0]
        else:
            self._advance_draw_from(st, seat, events)

    def _find_claim(self, st: dict, tile: dict, from_seat: int, passed: list[int]):
        """找这张弃牌的响应者：从放炮者**下家起逆时针**扫，胡 > 杠 > 碰。

        胡牌即结束 → 点炮只取**一家**，所以扫到第一个能胡的座位就定下来（就近优先，
        不存在一炮多响）；没人能胡时再按同样顺序找杠 / 碰。
        """
        best = None
        for off in range(1, 4):
            s = (from_seat + off) % 4
            if s in st["hu"] or s in passed:
                continue
            hand = st["hands"][s]
            opts: list[str] = []
            if can_hu(hand + [tile], len(st["melds"][s])):
                opts.append("hu")
            cnt = _counts(hand)[idx_of(tile["suit"], tile["rank"])]
            if cnt >= 3:
                opts.append("kong")
            if cnt >= 2:
                opts.append("pong")
            if not opts:
                continue
            pr = 3 if "hu" in opts else (2 if "kong" in opts else 1)
            if best is None or pr > best[0]:
                best = (pr, s, opts)
                if pr == 3:
                    break      # 最近的能胡者即本局赢家，后面不必再看
        return (best[1], best[2]) if best else None

    def _resolve_claim(self, st: dict, seat: int, act: str, events: list[dict]) -> None:
        cl = st["claim"]
        tile = cl["tile"]
        frm = cl["from"]
        if act == "hu":
            self._do_hu(st, seat, st["hands"][seat] + [tile], frm, False, events)
            _remove_discard(st["discards"][frm], tile)
            st["claim"] = None
            self._advance_draw_from(st, frm, events)
        elif act == "pong":
            _take_n(st["hands"][seat], tile, 2)
            st["melds"][seat].append({"type": "pong", "tile": tile, "from": frm})
            _remove_discard(st["discards"][frm], tile)
            st["claim"] = None
            st["turn"] = seat
            st["last_draw"] = None
            events.append({"kind": "pong", "seat": seat, "tile": tile, "from": frm})
            _history(st, {"kind": "pong", "seat": seat, "tile": tile})
            _log(st, f"{seat} 号位碰 {tile_text(tile)}")
        elif act == "kong":
            _take_n(st["hands"][seat], tile, 3)
            st["melds"][seat].append({"type": "kong", "tile": tile, "from": frm})
            _remove_discard(st["discards"][frm], tile)
            st["claim"] = None
            events.append({"kind": "kong", "seat": seat, "tile": tile, "from": frm, "sub": "ming"})
            _history(st, {"kind": "kong", "seat": seat, "tile": tile, "sub": "ming"})
            _log(st, f"{seat} 号位明杠 {tile_text(tile)}（刮风）")
            _gang_pay(st, seat, [frm], GANG_MING, "ming", events)
            self._draw(st, seat, events, after_kong=True)

    def _do_hu(self, st: dict, seat: int, hand_all: list[dict], fan_seat: int | None,
               zimo: bool, events: list[dict]) -> None:
        flags = {
            "gang_flower": zimo and bool(st.get("after_kong")),
            "gang_pao": (not zimo) and bool((st.get("claim") or {}).get("after_kong")),
            "haidi": not st["wall"],
        }
        res = score_hu(hand_all, st["melds"][seat], flags)
        fan = int(res["fan"])
        if zimo:
            payers = [s for s in range(4) if s != seat and s not in st["hu"]]
            for p in payers:
                st["score"][p] -= fan
                st["score"][seat] += fan
        else:
            st["score"][fan_seat] -= fan
            st["score"][seat] += fan
        st["hu"].append(seat)
        st["hu_info"][str(seat)] = {
            "fan": fan, "names": res["names"], "zimo": zimo,
            "from": fan_seat, "hand": hand_all,
        }
        events.append({"kind": "hu", "seat": seat, "fan": fan, "names": res["names"],
                       "zimo": zimo, "from": fan_seat})
        _history(st, {"kind": "hu", "seat": seat, "fan": fan, "names": res["names"], "zimo": zimo})
        _log(st, f"{seat} 号位{'自摸' if zimo else '和牌'}（{'/'.join(res['names'])} {fan} 番）")

    def _end_game(self, st: dict, events: list[dict]) -> None:
        if st["phase"] == "finished":
            return
        st["phase"] = "finished"
        st["turn"] = None
        st["claim"] = None
        st["result"] = {
            "finished": True,
            # 刮风下雨已即时收豆，最终结算只补「胡牌番数」部分，避免重复结算
            "deltas": {str(s): int(st["score"][s]) - int(st["gang_total"][s]) for s in range(4)},
            "score": {str(s): int(st["score"][s]) for s in range(4)},
            "hu": list(st["hu"]),
            "hu_info": st["hu_info"],
            # 庄家轮换（v2.46.17）：下一局由本局胡牌者坐庄；流局则庄家下移一位
            "dealer_next": (int(st["hu"][0]) if st["hu"] else (int(st.get("dealer", 0)) + 1) % 4),
            "match_over": False,
        }
        events.append({"kind": "finish", "hu": list(st["hu"])})
        _log(st, "本局结束")
        _history(st, {"kind": "finish", "hu": list(st["hu"])})

    # ---------- AI 驱动 ----------

    def step_ai(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        from app.games.base import ai_seats

        st = copy_state(state)
        ai = ai_seats(seats)
        events: list[dict] = []

        if st["phase"] != "playing":
            return None

        cl = st.get("claim")
        if cl is not None:
            if cl.get("seat") not in ai:
                return None
            seat = cl["seat"]
            opts = cl.get("options") or []
            tile = cl["tile"]
            melds = len(st["melds"][seat])
            if "hu" in opts:
                self._resolve_claim(st, seat, "hu", events)
            elif "kong" in opts and ai_want_kong(st["hands"][seat], tile):
                self._resolve_claim(st, seat, "kong", events)
            elif "pong" in opts and ai_want_pong(st["hands"][seat], tile, melds):
                self._resolve_claim(st, seat, "pong", events)
            else:
                cl["passed"] = list(cl.get("passed") or []) + [seat]
                cand = self._find_claim(st, tile, cl["from"], cl["passed"])
                if cand:
                    cl["seat"], cl["options"] = cand
                    st["turn"] = cand[0]
                else:
                    st["claim"] = None
                    self._advance_draw_from(st, cl["from"], events)
            return st, events

        cur = st.get("turn")
        if cur is None or cur not in ai:
            return None
        hand = st["hands"][cur]
        melds = st["melds"][cur]
        if can_hu(hand, len(melds)):
            self._do_hu(st, cur, hand, None, True, events)
            self._advance_draw_from(st, cur, events)
            return st, events
        ank = find_ankongs(hand)
        if ank:
            hit = ank[0]
            _take_n(hand, hit, 4)
            melds.append({"type": "ankong", "tile": hit, "from": cur})
            _log(st, f"{cur} 号位暗杠 {tile_text(hit)}（下雨）")
            _history(st, {"kind": "kong", "seat": cur, "tile": hit, "sub": "an"})
            _gang_pay(st, cur, [s for s in range(4) if s != cur and s not in st["hu"]],
                           GANG_AN, "an", events)
            self._draw(st, cur, events, after_kong=True)
            return st, events
        bug = find_bugangs(hand, melds)
        if bug:
            hit = bug[0]
            _take_n(hand, hit, 1)
            for m in melds:
                if m["type"] == "pong" and m["tile"]["suit"] == hit["suit"] and m["tile"]["rank"] == hit["rank"]:
                    m["type"] = "bugang"
                    break
            _log(st, f"{cur} 号位补杠 {tile_text(hit)}")
            _history(st, {"kind": "kong", "seat": cur, "tile": hit, "sub": "bu"})
            _gang_pay(st, cur, [s for s in range(4) if s != cur and s not in st["hu"]],
                           GANG_BU, "bu", events)
            self._draw(st, cur, events, after_kong=True)
            return st, events

        tile = ai_discard(hand, len(melds))
        st["hands"][cur] = [t for t in hand if t["id"] != tile["id"]]
        st["discards"][cur].append(tile)
        st["last_discard"] = {"seat": cur, "tile": tile}
        st["last_draw"] = None
        was_after_kong = bool(st.get("after_kong"))
        st["after_kong"] = False
        events.append({"kind": "discard", "seat": cur, "tile": tile})
        _history(st, {"kind": "discard", "seat": cur, "tile": tile})
        _log(st, f"{cur} 号位打 {tile_text(tile)}")
        cand = self._find_claim(st, tile, cur, [])
        if cand:
            st["claim"] = {"tile": tile, "from": cur, "seat": cand[0],
                           "options": cand[1], "passed": [], "after_kong": was_after_kong}
            st["turn"] = cand[0]
        else:
            self._advance_draw_from(st, cur, events)
        return st, events

    def on_timeout(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        return None

    def result(self, state: dict) -> dict | None:
        return state.get("result")

    def abort(self, state: dict, seats: list[dict],
              quit_seat: int | None = None) -> tuple[dict, list[dict]] | None:
        """有人中途退出：本局立即收摊，按当前分数结算（本局未胡完的部分不再补）。"""
        if state.get("phase") == "finished":
            return None
        st = copy_state(state)
        events: list[dict] = []
        self._end_game(st, events)
        return st, events

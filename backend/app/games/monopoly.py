"""大富翁（Monopoly）服务端权威引擎。

规则要点（家庭休闲简化版）：
- 52 格环形棋盘：起点 / 地产 / 命运 / 道具格 / 税务 / 监狱 / 免费停车。
- 2~8 人，掷两骰顺时针前进；双数可再掷一次（连续三次双数进监狱）。
- 地产可买、可盖楼（0→4 级）、可抵押 / 赎回；集齐同色组基础租金翻倍。
- 跳过后立即公开拍卖；破产者资产归债权人（银行则回到拍卖行）。
- 玩家间可随时发起交易；8 位角色各有技能，8 种道具卡在道具格抽取。

状态即 JSON：全部数组按「座位」下标存放（list，不用 dict[int] / tuple / set），
所有对外动作都走 `apply` / `step_ai`，内部先 `copy_state` 再改，绝不污染入参。
"""
from __future__ import annotations

from app.games.base import (
    TableEngine,
    TableError,
    ai_seats,
    copy_state,
    register,
    rng,
)

# ---------------- 静态棋盘 ----------------

# 8 个颜色组，每组 3 座城市（共 24 块地产）
GROUP_CITIES = [
    ["北京", "上海", "广州"],
    ["深圳", "杭州", "苏州"],
    ["成都", "重庆", "武汉"],
    ["西安", "南京", "天津"],
    ["长沙", "青岛", "厦门"],
    ["郑州", "济南", "沈阳"],
    ["昆明", "贵阳", "南宁"],
    ["哈尔滨", "大连", "兰州"],
]

# 52 格布局：kind + 附加参数（property 为 (组号, 组内序号)）
_LAYOUT = [
    ("start", None),          # 0  起点
    ("property", (0, 0)),     # 1  北京
    ("property", (0, 1)),     # 2  上海
    ("chance", None),         # 3  命运
    ("property", (0, 2)),     # 4  广州
    ("tax", None),            # 5  税务
    ("item", None),           # 6  道具格
    ("property", (1, 0)),     # 7  深圳
    ("property", (1, 1)),     # 8  杭州
    ("chance", None),         # 9  命运
    ("property", (1, 2)),     # 10 苏州
    ("jail", None),           # 11 监狱
    ("item", None),           # 12 道具格
    ("property", (2, 0)),     # 13 成都
    ("property", (2, 1)),     # 14 重庆
    ("chance", None),         # 15 命运
    ("property", (2, 2)),     # 16 武汉
    ("tax", None),            # 17 税务
    ("item", None),           # 18 道具格
    ("property", (3, 0)),     # 19 西安
    ("property", (3, 1)),     # 20 南京
    ("chance", None),         # 21 命运
    ("property", (3, 2)),     # 22 天津
    ("parking", None),        # 23 免费停车
    ("item", None),           # 24 道具格
    ("property", (4, 0)),     # 25 长沙
    ("property", (4, 1)),     # 26 青岛
    ("chance", None),         # 27 命运
    ("property", (4, 2)),     # 28 厦门
    ("tax", None),            # 29 税务
    ("item", None),           # 30 道具格
    ("property", (5, 0)),     # 31 郑州
    ("property", (5, 1)),     # 32 济南
    ("chance", None),         # 33 命运
    ("property", (5, 2)),     # 34 沈阳
    ("goto_jail", None),      # 35 进监狱
    ("item", None),           # 36 道具格
    ("property", (6, 0)),     # 37 昆明
    ("property", (6, 1)),     # 38 贵阳
    ("chance", None),         # 39 命运
    ("property", (6, 2)),     # 40 南宁
    ("tax", None),            # 41 税务
    ("item", None),           # 42 道具格
    ("property", (7, 0)),     # 43 哈尔滨
    ("property", (7, 1)),     # 44 大连
    ("chance", None),         # 45 命运
    ("property", (7, 2)),     # 46 兰州
    ("item", None),           # 47 道具格
    ("chance", None),         # 48 命运
    ("tax", None),            # 49 税务
    ("item", None),           # 50 道具格
    ("goto_jail", None),      # 51 进监狱
]

BOARD_LEN = 52
JAIL_POS = 11


def _build_board() -> list[dict]:
    """确定性构建 52 格棋盘。"""
    board: list[dict] = []
    for idx, (kind, arg) in enumerate(_LAYOUT):
        if kind == "property":
            g, k = arg
            price = 2000 + g * 2000 + k * 600
            r0 = price // 10
            board.append({
                "idx": idx,
                "kind": "property",
                "name": GROUP_CITIES[g][k],
                "price": price,
                "build": price // 2,
                "group": g,
                "rents": [r0, r0 * 3, r0 * 6, r0 * 10, r0 * 16],
            })
        elif kind == "start":
            board.append({"idx": idx, "kind": "start", "name": "起点"})
        elif kind == "chance":
            board.append({"idx": idx, "kind": "chance", "name": "命运"})
        elif kind == "item":
            board.append({"idx": idx, "kind": "item", "name": "道具格"})
        elif kind == "tax":
            board.append({"idx": idx, "kind": "tax", "name": "税务", "amount": 2500 + (idx % 3) * 1000})
        elif kind == "jail":
            board.append({"idx": idx, "kind": "jail", "name": "监狱"})
        elif kind == "goto_jail":
            board.append({"idx": idx, "kind": "goto_jail", "name": "进监狱"})
        else:  # parking
            board.append({"idx": idx, "kind": "parking", "name": "免费停车"})
    return board


BOARD = _build_board()

# 组号 -> 该组全部地块下标（升级 / 双倍租金判定用）
GROUP_TILES: list[list[int]] = [[] for _ in range(8)]
for _t in BOARD:
    if _t["kind"] == "property":
        GROUP_TILES[_t["group"]].append(_t["idx"])

# 8 位角色及其技能（每人 3 次）：
#   0 骰王：掷骰加成（可重掷一次，取更优结果）
#   1 房东：免租一次（下一次应付租金豁免）
#   2 强拆：强买邻地（1.2 倍价买下相邻对手地块）
#   3 拆迁：拆迁令（对手地块降 1 级）
#   4 财神：双倍收租（下一次收租翻倍）
#   5 忍者：闪现（瞬移到任意格并结算）
#   6 均富：均富（存活者现金取平均）
#   7 抄底：抄底（7 折买下对手地块）
CHARACTERS = ["骰王", "房东", "强拆", "拆迁", "财神", "忍者", "均富", "抄底"]

# 8 种道具卡（道具格抽取）：
#   0 路障：指定对手跳过下一回合
#   1 传送：自己瞬移到任意格并结算
#   2 免费卡：下一次应付租金豁免
#   3 均富卡：存活者现金取平均
#   4 购地卡：以原价买下脚下无主地块
#   5 转向卡：全场行进方向反转
#   6 怪兽卡：拆掉对手地块全部等级
#   7 天使卡：免灾（免租并出狱）
ITEMS = ["路障", "传送", "免费卡", "均富卡", "购地卡", "转向卡", "怪兽卡", "天使卡"]

CHAR_USES = 3
ITEM_VALUE = 1500  # AI 估值：一张道具卡


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise TableError(msg)


def _as_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@register
class MonopolyEngine(TableEngine):
    key = "monopoly"
    seat_count = 8      # 引擎支持 2..8 席，默认上限 8
    min_humans = 2

    # ---------------- 开局 ----------------

    def new_game(self, seats: list[dict], config: dict, seed: int) -> dict:
        n = len(seats)
        _need(2 <= n <= 8, "大富翁需要 2~8 位玩家")
        config = config or {}
        start_cash = _as_int(config.get("start_cash", 50000), 50000)

        characters = self._assign_characters(config, n)
        # v2.46.25 终局口径（夜星）：2 人局最长 200 轮封顶按资产排名；4 人及以上局
        # 破产淘汰到只剩 3 人时即结算排名（不再硬耗到最后一人生）。轮数按「整圈」算：
        # turn_limit 以单人行动次数计 = 轮数 × 人数。
        turn_limit = _as_int(config.get("turn_limit"), 0) or (200 * n)
        state = {
            "phase": "action",
            "turn": 0,
            "n": n,
            "seed": int(seed) & 0xFFFFFFFF,
            "rng_count": 0,
            "turn_limit": turn_limit,
            "turns": 0,
            "base_stake": _as_int(config.get("base_stake", 100), 100),
            "start_cash": start_cash,
            "salary": _as_int(config.get("salary", 5000), 5000),
            "jail_fine": _as_int(config.get("jail_fine", 3000), 3000),
            "bid_step": max(1, _as_int(config.get("bid_step", 500), 500)),
            "ai_buffer": _as_int(config.get("ai_buffer", 5000), 5000),
            # 按座位存放的公开状态
            "pos": [0] * n,
            "cash": [start_cash] * n,
            "alive": [True] * n,
            "items": [[] for _ in range(n)],
            "characters": characters,
            "char_uses": [CHAR_USES] * n,
            "in_jail": [0] * n,
            "is_ai": [bool(s.get("is_ai")) for s in seats],
            "names": [str(s.get("name") or "玩家") for s in seats],
            # 按地块下标存放
            "owner": [-1] * BOARD_LEN,
            "level": [0] * BOARD_LEN,
            "mortgaged": [False] * BOARD_LEN,
            # 回合内临时态
            "direction": 1,
            "rolled": False,
            "doubles": 0,
            "extra_roll": False,
            "pending": None,
            "last_dice": None,
            "pot": 0,
            "skip": [False] * n,
            "free_rent": [False] * n,
            "double_rent": [False] * n,
            "angel": [False] * n,
            "lucky_reroll": False,
            # 拍卖 / 交易
            "auction": None,
            "trades": [],
            "trade_seq": 0,
            # 终局
            "winner": None,
            "ranking": [],
        }
        return state

    @staticmethod
    def _assign_characters(config: dict, n: int) -> list[int]:
        """读取 config["characters"]（dict 座位→角色 / list），否则按下标自动分配。"""
        chars = [-1] * n
        raw = (config or {}).get("characters")
        if isinstance(raw, dict):
            for k, v in raw.items():
                seat = _as_int(k, -1)
                if 0 <= seat < n:
                    chars[seat] = _as_int(v, 0) % 8
        elif isinstance(raw, list):
            for i, v in enumerate(raw[:n]):
                chars[i] = _as_int(v, i) % 8
        for i in range(n):
            if chars[i] < 0:
                chars[i] = i % 8
        return chars

    # ---------------- 投影 ----------------

    def view(self, state: dict, seat: int) -> dict:
        st = state
        n = st["n"]
        seat = _as_int(seat, -1)
        players = []
        for i in range(n):
            players.append({
                "seat": i,
                "pos": st["pos"][i],
                "cash": st["cash"][i],
                "alive": st["alive"][i],
                "items": list(st["items"][i]),
                "character": st["characters"][i],
                "in_jail": st["in_jail"][i],
                "net_worth": self._net_worth(st, i),
            })
        me = {
            "seat": seat,
            "cash": st["cash"][seat] if 0 <= seat < n else 0,
            "items": list(st["items"][seat]) if 0 <= seat < n else [],
            "character": st["characters"][seat] if 0 <= seat < n else -1,
            "skill_left": st["char_uses"][seat] if 0 <= seat < n else 0,
            "jail_left": st["in_jail"][seat] if 0 <= seat < n else 0,
            "options": self._options(st, seat),
        }
        return {
            "phase": st["phase"],
            "turn": st["turn"],
            "finished": st["phase"] == "finished",
            "result": self.result(st),
            "players": players,
            "me": me,
            "table": {
                "board": BOARD,
                "owner": st["owner"],
                "level": st["level"],
                "mortgaged": st["mortgaged"],
                "auction": st.get("auction"),
                "trades": st.get("trades", []),
                "last_dice": st.get("last_dice"),
                # v2.46.25：真实轮数（整圈）+ 上限，前端「第 X 轮」不再恒显示 1
                "rounds": st["turns"] // max(1, st["n"]) + 1,
                "round_limit": st["turn_limit"] // max(1, st["n"]),
            },
        }

    def _options(self, st: dict, seat: int) -> dict:
        n = st["n"]
        if not (0 <= seat < n) or not st["alive"][seat]:
            return {"roll": False, "buy": False, "end_turn": False,
                    "upgrade": [], "mortgage": [], "redeem": [],
                    "pay_jail": False, "roll_jail": False}
        pending = st["pending"]
        my_turn = st["phase"] == "action" and st["turn"] == seat
        in_jail = st["in_jail"][seat] > 0
        upgrade, mortgage, redeem = [], [], []
        for i in range(BOARD_LEN):
            if st["owner"][i] != seat:
                continue
            if st["mortgaged"][i]:
                redeem.append(i)
            else:
                mortgage.append(i)
                t = BOARD[i]
                if t["kind"] == "property" and st["level"][i] < 4 \
                        and self._group_complete(st, seat, t["group"]):
                    upgrade.append(i)
        return {
            "roll": bool(my_turn and st["alive"][seat] and not st["rolled"]
                         and pending is None and not in_jail),
            "buy": bool(pending is not None and pending.get("seat") == seat),
            "end_turn": bool(my_turn and st["rolled"] and pending is None
                             and not in_jail),
            "upgrade": upgrade,
            "mortgage": mortgage,
            "redeem": redeem,
            "pay_jail": bool(my_turn and in_jail and st["cash"][seat] >= st["jail_fine"]),
            "roll_jail": bool(my_turn and in_jail),
        }

    def result(self, state: dict) -> dict | None:
        if state.get("phase") != "finished":
            return None
        n = state["n"]
        winner = state.get("winner")
        ranking = list(state.get("ranking") or [])
        deltas = {}
        for i in range(n):
            deltas[i] = -1 if i != winner else (n - 1)
        return {
            "finished": True,
            "winner": winner,
            "ranking": ranking,
            "deltas": deltas,
        }

    def abort(self, state: dict, seats: list[dict],
              quit_seat: int | None = None) -> tuple[dict, list[dict]] | None:
        """有人中途退出：本局立即收摊，按当前净资产排名结算。"""
        if state.get("phase") == "finished":
            return None
        st = copy_state(state)
        events: list[dict] = []
        self._finish(st, events)
        return st, events

    # ---------------- 动作入口 ----------------

    def apply(self, state: dict, seat: int, action: dict) -> tuple[dict, list[dict]]:
        st = copy_state(state)
        seat = _as_int(seat, -1)
        n = st["n"]
        _need(0 <= seat < n, "座位不存在")
        act = (action or {}).get("type")
        _need(st["phase"] != "finished", "对局已结束")
        events: list[dict] = []

        if act == "roll":
            self._req_turn(st, seat)
            _need(st["alive"][seat], "你已出局")
            _need(st["pending"] is None, "请先处理购地")
            _need(st["in_jail"][seat] == 0, "在监狱中，请先支付罚金或掷骰出狱")
            _need(not st["rolled"], "本回合已经掷过骰子")
            self._do_roll(st, seat, events)
        elif act == "buy":
            p = st["pending"]
            _need(p is not None and p.get("seat") == seat and p.get("kind") == "buy", "当前没有待购地块")
            self._buy(st, seat, p["tile"], events)
        elif act == "skip_buy":
            p = st["pending"]
            _need(p is not None and p.get("seat") == seat, "当前没有待购地块")
            tile = p["tile"]
            st["pending"] = None
            self._start_auction(st, tile, events)
        elif act == "upgrade":
            self._req_turn(st, seat)
            self._upgrade(st, seat, _as_int((action or {}).get("tile"), -1), events)
        elif act == "mortgage":
            self._req_turn(st, seat)
            self._mortgage(st, seat, _as_int((action or {}).get("tile"), -1), events)
        elif act == "redeem":
            self._req_turn(st, seat)
            self._redeem(st, seat, _as_int((action or {}).get("tile"), -1), events)
        elif act == "end_turn":
            self._req_turn(st, seat)
            _need(st["pending"] is None, "请先处理购地")
            _need(st["in_jail"][seat] == 0, "请先处理监狱")
            _need(st["rolled"], "还没掷骰子")
            self._end_turn(st, events)
        elif act == "pay_jail":
            self._req_turn(st, seat)
            self._pay_jail(st, seat, events)
        elif act == "roll_jail":
            self._req_turn(st, seat)
            self._roll_jail(st, seat, events)
        elif act == "bid":
            self._auction_bid(st, seat, _as_int((action or {}).get("amount"), 0), events)
        elif act == "pass_bid":
            _need(st["phase"] == "auction", "当前没有拍卖")
            _need(st["auction"]["turn"] == seat, "还没轮到你出价")
            _need(st["alive"][seat], "你已出局")
            self._auction_pass(st, seat, events)
        elif act == "trade_offer":
            self._trade_offer(st, seat, action or {}, events)
        elif act == "trade_accept":
            self._trade_respond(st, seat, _as_int((action or {}).get("id"), -1), True, events)
        elif act == "trade_reject":
            self._trade_respond(st, seat, _as_int((action or {}).get("id"), -1), False, events)
        elif act == "skill":
            self._use_skill(st, seat, action or {}, events)
        elif act == "use_item":
            self._use_item(st, seat, action or {}, events)
        else:
            raise TableError("未知动作")

        self._check_end(st, events)
        return st, events

    def _req_turn(self, st: dict, seat: int) -> None:
        _need(st["phase"] == "action", "当前不是行动阶段")
        _need(st["alive"][seat], "你已出局")
        _need(st["turn"] == seat, "还没轮到你")

    # ---------------- 掷骰 / 移动 ----------------

    def _rng(self, st: dict):
        st["rng_count"] = st.get("rng_count", 0) + 1
        return rng(st["seed"] * 1000003 + st["rng_count"])

    def _dice(self, st: dict, seat: int) -> tuple[int, int]:
        r = self._rng(st)
        a, b = r.randint(1, 6), r.randint(1, 6)
        if st.get("lucky_reroll"):
            st["lucky_reroll"] = False
            c, d = r.randint(1, 6), r.randint(1, 6)
            if c + d > a + b:
                return c, d
        return a, b

    def _dest(self, st: dict, seat: int, steps: int) -> int:
        return (st["pos"][seat] + st["direction"] * steps) % BOARD_LEN

    def _do_roll(self, st: dict, seat: int, events: list[dict]) -> None:
        d1, d2 = self._dice(st, seat)
        st["last_dice"] = [d1, d2]
        st["rolled"] = True
        is_double = d1 == d2
        dest = self._dest(st, seat, d1 + d2)
        events.append({"act": "roll", "seat": seat, "dice": [d1, d2], "to": dest})
        if is_double:
            st["doubles"] += 1
            if st["doubles"] >= 3:          # 三连双 → 直接进监狱
                self._send_to_jail(st, seat, events)
                self._end_turn(st, events)
                return
        self._move(st, seat, d1 + d2, events, 2)
        if not st["alive"][seat]:
            self._end_turn(st, events)
            return
        if st["phase"] == "auction":
            return
        if is_double and st["in_jail"][seat] == 0:
            if st["pending"] is None:
                st["rolled"] = False        # 双数 → 再掷一次
            else:
                st["extra_roll"] = True     # 处理完购地后再掷
        elif is_double:
            st["extra_roll"] = True

    def _move(self, st: dict, seat: int, steps: int, events: list[dict], depth: int) -> None:
        old = st["pos"][seat]
        raw = old + st["direction"] * steps
        new = raw % BOARD_LEN
        if steps > 0 and (raw < 0 or raw >= BOARD_LEN):
            st["cash"][seat] += st["salary"]   # 经过起点发工资
            events.append({"act": "rent", "from": -1, "to": seat, "amount": st["salary"]})
        st["pos"][seat] = new
        events.append({"act": "move", "seat": seat, "pos": new})
        if depth > 0:
            self._resolve_tile(st, seat, events, depth)

    def _teleport(self, st: dict, seat: int, pos: int, events: list[dict], depth: int) -> None:
        st["pos"][seat] = pos % BOARD_LEN
        events.append({"act": "move", "seat": seat, "pos": st["pos"][seat]})
        if depth > 0:
            self._resolve_tile(st, seat, events, depth)

    def _send_to_jail(self, st: dict, seat: int, events: list[dict]) -> None:
        st["pos"][seat] = JAIL_POS
        st["in_jail"][seat] = 2
        st["doubles"] = 0
        st["extra_roll"] = False
        st["pending"] = None
        st["rolled"] = True
        events.append({"act": "move", "seat": seat, "pos": JAIL_POS})

    # ---------------- 落地结算 ----------------

    def _resolve_tile(self, st: dict, seat: int, events: list[dict], depth: int) -> None:
        if not st["alive"][seat]:
            return
        tile = BOARD[st["pos"][seat]]
        kind = tile["kind"]
        if kind == "property":
            self._resolve_property(st, seat, tile, events)
        elif kind == "chance":
            self._chance(st, seat, events, depth)
        elif kind == "item":
            self._draw_item(st, seat, events)
        elif kind == "tax":
            events.append({"act": "rent", "from": seat, "to": -1, "amount": tile["amount"]})
            self._pay(st, seat, tile["amount"], -1, events)
            if st["alive"][seat]:
                st["pot"] += tile["amount"]
        elif kind in ("jail", "goto_jail"):
            self._send_to_jail(st, seat, events)
        elif kind == "parking":
            if st["pot"] > 0:
                amount = st["pot"]
                st["cash"][seat] += amount
                st["pot"] = 0
                events.append({"act": "rent", "from": -1, "to": seat, "amount": amount})
        # start 已在经过时发过工资

    def _resolve_property(self, st: dict, seat: int, tile: dict, events: list[dict]) -> None:
        idx = tile["idx"]
        owner = st["owner"][idx]
        if owner == -1:
            if st["cash"][seat] >= tile["price"]:
                st["pending"] = {"kind": "buy", "tile": idx, "seat": seat}
            else:
                self._start_auction(st, idx, events)   # 买不起 → 直接拍卖
        elif owner != seat and st["alive"][owner] and not st["mortgaged"][idx]:
            rent = self._rent_of(st, idx)
            if rent > 0:
                self._pay_rent(st, seat, owner, rent, events)

    def _rent_of(self, st: dict, idx: int) -> int:
        owner = st["owner"][idx]
        if owner < 0 or st["mortgaged"][idx]:
            return 0
        tile = BOARD[idx]
        base = tile["rents"][st["level"][idx]]
        if self._group_complete(st, owner, tile["group"]):
            base *= 2                               # 集齐同色组，租金翻倍
        return int(base)

    def _group_complete(self, st: dict, seat: int, group: int) -> bool:
        return all(st["owner"][t] == seat for t in GROUP_TILES[group])

    def _pay_rent(self, st: dict, payer: int, owner: int, amount: int, events: list[dict]) -> None:
        if st["free_rent"][payer] or st["angel"][payer]:
            st["free_rent"][payer] = False
            st["angel"][payer] = False
            events.append({"act": "rent", "from": payer, "to": owner, "amount": 0})
            return
        if st["double_rent"][owner]:
            st["double_rent"][owner] = False
            amount *= 2
        events.append({"act": "rent", "from": payer, "to": owner, "amount": amount})
        self._pay(st, payer, amount, owner, events)

    def _pay(self, st: dict, seat: int, amount: int, creditor: int, events: list[dict]) -> bool:
        """付款；付不出则先抵押变卖，仍不足 → 破产。返回是否付清。"""
        if amount <= 0:
            return True
        self._liquidate(st, seat, amount)
        if st["cash"][seat] >= amount:
            st["cash"][seat] -= amount
            if creditor >= 0 and st["alive"][creditor]:
                st["cash"][creditor] += amount
            return True
        self._bankrupt(st, seat, creditor, events)
        return False

    def _liquidate(self, st: dict, seat: int, need: int) -> None:
        """现金不足时按地块下标顺序自动抵押（简单实现）。"""
        for i in range(BOARD_LEN):
            if st["cash"][seat] >= need:
                break
            if st["owner"][i] == seat and not st["mortgaged"][i]:
                st["mortgaged"][i] = True
                st["cash"][seat] += BOARD[i]["price"] // 2

    def _bankrupt(self, st: dict, seat: int, creditor: int, events: list[dict]) -> None:
        st["alive"][seat] = False
        to_player = creditor >= 0 and st["alive"][creditor]
        if to_player:
            st["cash"][creditor] += st["cash"][seat]
        st["cash"][seat] = 0
        for i in range(BOARD_LEN):
            if st["owner"][i] != seat:
                continue
            if to_player:                            # 资产归债权人
                st["owner"][i] = creditor
            else:                                    # 无债权人 → 回到拍卖行
                st["owner"][i] = -1
                st["level"][i] = 0
                st["mortgaged"][i] = False
        st["items"][seat] = []
        st["in_jail"][seat] = 0
        events.append({"act": "bankrupt", "seat": seat,
                       "to": creditor if to_player else None})

    # ---------------- 购地 / 升级 / 抵押 ----------------

    def _buy(self, st: dict, seat: int, idx: int, events: list[dict]) -> None:
        _need(0 <= idx < BOARD_LEN and BOARD[idx]["kind"] == "property", "该地块不可购买")
        _need(st["owner"][idx] == -1, "该地块已有主人")
        price = BOARD[idx]["price"]
        _need(st["cash"][seat] >= price, "现金不足")
        st["cash"][seat] -= price
        st["owner"][idx] = seat
        st["level"][idx] = 0
        st["mortgaged"][idx] = False
        st["pending"] = None
        events.append({"act": "buy", "seat": seat, "tile": idx, "price": price})
        if st["extra_roll"] and st["phase"] == "action" and st["in_jail"][seat] == 0:
            st["extra_roll"] = False
            st["rolled"] = False

    def _upgrade(self, st: dict, seat: int, idx: int, events: list[dict]) -> None:
        _need(0 <= idx < BOARD_LEN and BOARD[idx]["kind"] == "property", "该地块不可建造")
        _need(st["owner"][idx] == seat, "这不是你的地块")
        _need(not st["mortgaged"][idx], "抵押中的地块不能建造")
        _need(st["level"][idx] < 4, "已建到最高等级")
        tile = BOARD[idx]
        _need(self._group_complete(st, seat, tile["group"]), "需集齐同色组才能建造")
        cost = tile["build"]
        _need(st["cash"][seat] >= cost, "现金不足")
        st["cash"][seat] -= cost
        st["level"][idx] += 1
        events.append({"act": "upgrade", "seat": seat, "tile": idx, "level": st["level"][idx]})

    def _mortgage(self, st: dict, seat: int, idx: int, events: list[dict]) -> None:
        _need(0 <= idx < BOARD_LEN, "地块不存在")
        _need(st["owner"][idx] == seat, "这不是你的地块")
        _need(not st["mortgaged"][idx], "该地块已抵押")
        _need(st["level"][idx] == 0, "请先拆完建筑再抵押")
        st["mortgaged"][idx] = True
        gain = BOARD[idx]["price"] // 2
        st["cash"][seat] += gain
        events.append({"act": "mortgage", "seat": seat, "tile": idx})

    def _redeem(self, st: dict, seat: int, idx: int, events: list[dict]) -> None:
        _need(0 <= idx < BOARD_LEN, "地块不存在")
        _need(st["owner"][idx] == seat, "这不是你的地块")
        _need(st["mortgaged"][idx], "该地块未抵押")
        cost = int(BOARD[idx]["price"] // 2 * 1.1)
        _need(st["cash"][seat] >= cost, "现金不足")
        st["cash"][seat] -= cost
        st["mortgaged"][idx] = False
        events.append({"act": "redeem", "seat": seat, "tile": idx})

    # ---------------- 监狱 ----------------

    def _pay_jail(self, st: dict, seat: int, events: list[dict]) -> None:
        _need(st["in_jail"][seat] > 0, "你不在监狱")
        _need(st["cash"][seat] >= st["jail_fine"], "现金不足")
        st["cash"][seat] -= st["jail_fine"]
        st["pot"] += st["jail_fine"]
        st["in_jail"][seat] = 0
        events.append({"act": "pay_jail", "seat": seat, "amount": st["jail_fine"]})

    def _roll_jail(self, st: dict, seat: int, events: list[dict]) -> None:
        _need(st["in_jail"][seat] > 0, "你不在监狱")
        d1, d2 = self._dice(st, seat)
        st["last_dice"] = [d1, d2]
        st["rolled"] = True
        dest = self._dest(st, seat, d1 + d2)
        events.append({"act": "roll", "seat": seat, "dice": [d1, d2], "to": dest})
        if d1 == d2:
            st["in_jail"][seat] = 0
            self._move(st, seat, d1 + d2, events, 2)
            if not st["alive"][seat]:
                self._end_turn(st, events)
            return
        st["in_jail"][seat] -= 1
        if st["in_jail"][seat] <= 0:
            st["in_jail"][seat] = 0
        self._end_turn(st, events)

    # ---------------- 命运 / 道具 ----------------

    def _chance(self, st: dict, seat: int, events: list[dict], depth: int) -> None:
        card = self._rng(st).randint(0, 7)
        if card == 0:                                   # 领取分红
            st["cash"][seat] += 5000
            events.append({"act": "rent", "from": -1, "to": seat, "amount": 5000})
        elif card == 1:                                 # 缴纳罚款
            events.append({"act": "rent", "from": seat, "to": -1, "amount": 3000})
            self._pay(st, seat, 3000, -1, events)
        elif card == 2:                                 # 前进 3 格
            if depth > 0:
                self._move(st, seat, 3, events, depth - 1)
        elif card == 3:                                 # 后退 2 格
            if depth > 0:
                self._move(st, seat, -2, events, depth - 1)
        elif card == 4:                                 # 直接进监狱
            self._send_to_jail(st, seat, events)
        elif card == 5:                                 # 获得随机道具卡
            self._draw_item(st, seat, events)
        elif card == 6:                                 # 直达起点并领工资
            st["pos"][seat] = 0
            st["cash"][seat] += st["salary"]
            events.append({"act": "move", "seat": seat, "pos": 0})
            events.append({"act": "rent", "from": -1, "to": seat, "amount": st["salary"]})
        else:                                           # 其他玩家各付你 1000
            for other in range(st["n"]):
                if other != seat and st["alive"][other]:
                    events.append({"act": "rent", "from": other, "to": seat, "amount": 1000})
                    self._pay(st, other, 1000, seat, events)

    def _draw_item(self, st: dict, seat: int, events: list[dict]) -> None:
        item = self._rng(st).randint(0, 7)
        st["items"][seat].append(item)
        events.append({"act": "item", "seat": seat, "item": item})

    # ---------------- 拍卖 ----------------

    def _start_auction(self, st: dict, tile: int, events: list[dict]) -> None:
        st["auction"] = {
            "tile": tile,
            "high": 0,
            "high_seat": -1,
            "passed": [],
            "turn": self._next_alive(st, st["turn"]),
        }
        st["phase"] = "auction"
        events.append({"act": "auction_start", "tile": tile})

    def _auction_bid(self, st: dict, seat: int, amount: int, events: list[dict]) -> None:
        _need(st["phase"] == "auction" and st["auction"], "当前没有拍卖")
        a = st["auction"]
        _need(a["turn"] == seat, "还没轮到你出价")
        _need(st["alive"][seat], "你已出局")
        step = st["bid_step"]
        floor = a["high"] + step if a["high_seat"] >= 0 else step
        _need(amount >= floor, f"出价至少 {floor}")
        _need(amount % step == 0, f"出价必须是 {step} 的整数倍")
        _need(amount <= st["cash"][seat], "现金不足")
        a["high"] = amount
        a["high_seat"] = seat
        a["passed"] = []
        events.append({"act": "bid", "seat": seat, "amount": amount})
        self._auction_advance(st, seat, events)

    def _auction_pass(self, st: dict, seat: int, events: list[dict]) -> None:
        a = st["auction"]
        if seat not in a["passed"]:
            a["passed"].append(seat)
        self._auction_advance(st, seat, events)

    def _auction_advance(self, st: dict, last: int, events: list[dict]) -> None:
        a = st["auction"]
        alive = [i for i in range(st["n"]) if st["alive"][i]]
        hs = a["high_seat"]
        if hs >= 0:
            remaining = [i for i in alive if i == hs or i not in a["passed"]]
        else:
            remaining = [i for i in alive if i not in a["passed"]]
        if len(remaining) <= 1 and (hs >= 0 or not remaining):
            self._auction_close(st, events)
            return
        if not remaining:
            self._auction_close(st, events)
            return
        nxt = self._next_alive_excluding(st, last, a["passed"])
        if nxt is None:
            self._auction_close(st, events)
            return
        a["turn"] = nxt

    def _auction_close(self, st: dict, events: list[dict]) -> None:
        a = st["auction"]
        tile, hs, amt = a["tile"], a["high_seat"], a["high"]
        if hs >= 0 and st["alive"][hs] and st["cash"][hs] >= amt:
            st["cash"][hs] -= amt
            st["owner"][tile] = hs
            st["level"][tile] = 0
            st["mortgaged"][tile] = False
            events.append({"act": "auction_done", "tile": tile, "seat": hs, "amount": amt})
        else:
            events.append({"act": "auction_done", "tile": tile, "seat": -1, "amount": 0})
        st["auction"] = None
        st["phase"] = "action"
        if not st["alive"][st["turn"]]:
            self._end_turn(st, events)

    # ---------------- 交易 ----------------

    def _bundle(self, st: dict, owner: int, raw: dict) -> dict:
        raw = raw or {}
        cash = _as_int(raw.get("cash"), 0)
        tiles = [_as_int(t, -1) for t in (raw.get("tiles") or [])]
        items = [_as_int(x, -1) for x in (raw.get("items") or [])]
        _need(cash >= 0, "金额不能为负")
        _need(cash <= st["cash"][owner], "对方现金不足")
        for t in tiles:
            _need(0 <= t < BOARD_LEN and st["owner"][t] == owner, "包含不属于对方的地块")
        for it in items:
            _need(it in st["items"][owner], "包含对方没有的道具")
        return {"cash": cash, "tiles": tiles, "items": items}

    def _trade_offer(self, st: dict, seat: int, action: dict, events: list[dict]) -> None:
        _need(st["alive"][seat], "你已出局")
        to = _as_int(action.get("to"), -1)
        _need(0 <= to < st["n"] and to != seat, "交易对象不合法")
        _need(st["alive"][to], "对方已出局")
        give = self._bundle(st, seat, action.get("give") or {})
        want = self._bundle(st, to, action.get("want") or {})
        _need(give["cash"] or give["tiles"] or give["items"] or
              want["cash"] or want["tiles"] or want["items"], "交易内容不能为空")
        st["trade_seq"] += 1
        tid = st["trade_seq"]
        st["trades"].append({
            "id": tid, "from": seat, "to": to,
            "give": give, "want": want, "status": "pending",
        })
        events.append({"act": "trade_offer", "from": seat, "to": to, "id": tid})

    def _trade_respond(self, st: dict, seat: int, tid: int, accept: bool, events: list[dict]) -> None:
        trade = None
        for t in st["trades"]:
            if t["id"] == tid:
                trade = t
                break
        _need(trade is not None, "交易不存在")
        _need(trade["status"] == "pending", "交易已处理")
        _need(trade["to"] == seat, "这不是发给你的交易")
        if not accept:
            trade["status"] = "rejected"
            events.append({"act": "trade_reject", "id": tid})
            return
        # 重新校验双方资产仍然满足
        self._bundle(st, trade["from"], trade["give"])
        self._bundle(st, trade["to"], trade["want"])
        self._transfer(st, trade["from"], trade["to"], trade["give"])
        self._transfer(st, trade["to"], trade["from"], trade["want"])
        trade["status"] = "accepted"
        events.append({"act": "trade_accept", "id": tid})

    @staticmethod
    def _transfer(st: dict, frm: int, to: int, bundle: dict) -> None:
        st["cash"][frm] -= bundle["cash"]
        st["cash"][to] += bundle["cash"]
        for t in bundle["tiles"]:
            st["owner"][t] = to
        for it in bundle["items"]:
            if it in st["items"][frm]:
                st["items"][frm].remove(it)
                st["items"][to].append(it)

    # ---------------- 角色技能 ----------------

    def _use_skill(self, st: dict, seat: int, action: dict, events: list[dict]) -> None:
        _need(st["alive"][seat], "你已出局")
        _need(st["phase"] == "action", "当前不能使用技能")
        _need(st["char_uses"][seat] > 0, "技能次数已用完")
        ch = st["characters"][seat]
        if ch == 0:                                     # 骰王：下次掷骰重掷取优
            _need(not st["rolled"], "本回合已掷骰，无法加成")
            st["lucky_reroll"] = True
        elif ch == 1:                                   # 房东：免租一次
            st["free_rent"][seat] = True
        elif ch == 2:                                   # 强拆：1.2 倍价强买邻地
            idx = _as_int(action.get("tile"), -1)
            self._require_adjacent(st, seat, idx)
            owner = st["owner"][idx]
            _need(owner >= 0 and owner != seat, "该地块不是对手的")
            cost = int(BOARD[idx]["price"] * 1.2)
            _need(st["cash"][seat] >= cost, "现金不足")
            st["cash"][seat] -= cost
            st["cash"][owner] += cost
            st["owner"][idx] = seat
        elif ch == 3:                                   # 拆迁令：对手地块降 1 级
            idx = _as_int(action.get("tile"), -1)
            _need(0 <= idx < BOARD_LEN and BOARD[idx]["kind"] == "property", "目标必须是地产")
            owner = st["owner"][idx]
            _need(owner >= 0 and owner != seat, "该地块不是对手的")
            _need(st["level"][idx] > 0, "该地块没有建筑")
            st["level"][idx] -= 1
        elif ch == 4:                                   # 财神：下次收租翻倍
            st["double_rent"][seat] = True
        elif ch == 5:                                   # 忍者：瞬移任意格并结算
            pos = _as_int(action.get("pos"), -1)
            _need(0 <= pos < BOARD_LEN, "目标格不合法")
            self._teleport(st, seat, pos, events, 2)
        elif ch == 6:                                   # 均富：存活者现金取平均
            self._equalize(st, events)
        else:                                           # 抄底：7 折买对手地块
            idx = _as_int(action.get("tile"), -1)
            _need(0 <= idx < BOARD_LEN and BOARD[idx]["kind"] == "property", "目标必须是地产")
            owner = st["owner"][idx]
            _need(owner >= 0 and owner != seat, "该地块不是对手的")
            cost = int(BOARD[idx]["price"] * 0.7)
            _need(st["cash"][seat] >= cost, "现金不足")
            st["cash"][seat] -= cost
            st["cash"][owner] += cost
            st["owner"][idx] = seat
        st["char_uses"][seat] -= 1
        events.append({"act": "skill", "seat": seat, "character": ch})

    def _require_adjacent(self, st: dict, seat: int, idx: int) -> None:
        _need(0 <= idx < BOARD_LEN and BOARD[idx]["kind"] == "property", "目标必须是地产")
        pos = st["pos"][seat]
        _need(idx == (pos + 1) % BOARD_LEN or idx == (pos - 1) % BOARD_LEN, "只能强买相邻地块")

    @staticmethod
    def _equalize(st: dict, events: list[dict]) -> None:
        alive = [i for i in range(st["n"]) if st["alive"][i]]
        total = sum(st["cash"][i] for i in alive)
        avg = total // len(alive)
        for i in alive:
            st["cash"][i] = avg
        events.append({"act": "equalize", "seats": alive, "amount": avg})

    # ---------------- 道具卡 ----------------

    def _use_item(self, st: dict, seat: int, action: dict, events: list[dict]) -> None:
        _need(st["alive"][seat], "你已出局")
        _need(st["phase"] == "action", "当前不能使用道具")
        item = _as_int(action.get("item"), -1)
        _need(item in st["items"][seat], "你没有这张道具卡")
        if item == 0:                                   # 路障：对手跳过下一回合
            target = _as_int(action.get("target_seat"), -1)
            _need(0 <= target < st["n"] and target != seat and st["alive"][target], "目标不合法")
            st["skip"][target] = True
        elif item == 1:                                 # 传送：瞬移任意格并结算
            pos = _as_int(action.get("pos"), -1)
            _need(0 <= pos < BOARD_LEN, "目标格不合法")
            self._teleport(st, seat, pos, events, 2)
        elif item == 2:                                 # 免费卡：下次免租
            st["free_rent"][seat] = True
        elif item == 3:                                 # 均富卡
            self._equalize(st, events)
        elif item == 4:                                 # 购地卡：原价买下脚下无主地块
            idx = st["pos"][seat]
            _need(BOARD[idx]["kind"] == "property" and st["owner"][idx] == -1, "脚下不是无主地产")
            price = BOARD[idx]["price"]
            _need(st["cash"][seat] >= price, "现金不足")
            st["cash"][seat] -= price
            st["owner"][idx] = seat
            st["level"][idx] = 0
            st["mortgaged"][idx] = False
        elif item == 5:                                 # 转向卡：方向反转
            st["direction"] = -st["direction"]
        elif item == 6:                                 # 怪兽卡：拆光对手地块建筑
            idx = _as_int(action.get("tile"), -1)
            _need(0 <= idx < BOARD_LEN, "地块不存在")
            owner = st["owner"][idx]
            _need(owner >= 0 and owner != seat, "该地块不是对手的")
            st["level"][idx] = 0
        else:                                           # 天使卡：免灾（免租 + 出狱）
            st["angel"][seat] = True
            st["free_rent"][seat] = True
            st["in_jail"][seat] = 0
        st["items"][seat].remove(item)
        events.append({"act": "item_used", "seat": seat, "item": item})

    # ---------------- 回合推进 / 终局 ----------------

    def _end_turn(self, st: dict, events: list[dict]) -> None:
        if st["phase"] == "finished":
            return
        cur = st["turn"]
        st["rolled"] = False
        st["doubles"] = 0
        st["extra_roll"] = False
        st["pending"] = None
        st["turns"] += 1
        if st["turns"] >= st["turn_limit"]:
            self._finish(st, events)
            return
        nxt = self._next_alive(st, cur)
        guard = 0
        while st["skip"][nxt] and guard < st["n"]:      # 路障：跳过被点名的玩家
            st["skip"][nxt] = False
            nxt = self._next_alive(st, nxt)
            guard += 1
        st["turn"] = nxt

    def _next_alive(self, st: dict, seat: int) -> int:
        n = st["n"]
        for k in range(1, n + 1):
            j = (seat + k) % n
            if st["alive"][j]:
                return j
        return seat

    def _next_alive_excluding(self, st: dict, seat: int, excluded: list) -> int | None:
        n = st["n"]
        for k in range(1, n + 1):
            j = (seat + k) % n
            if st["alive"][j] and j not in excluded:
                return j
        return None

    def _net_worth(self, st: dict, seat: int) -> int:
        worth = st["cash"][seat]
        for i in range(BOARD_LEN):
            if st["owner"][i] != seat:
                continue
            price = BOARD[i]["price"]
            worth += price if not st["mortgaged"][i] else price // 2
            worth += st["level"][i] * BOARD[i].get("build", 0)
        return worth

    def _check_end(self, st: dict, events: list[dict]) -> None:
        if st["phase"] == "finished":
            return
        alive = [i for i in range(st["n"]) if st["alive"][i]]
        if len(alive) <= 1:
            self._finish(st, events)
            return
        # v2.46.25：4 人及以上局，只剩最后 3 人时按资产排名结算（夜星定的口径）
        if st["n"] >= 4 and len(alive) <= 3:
            self._finish(st, events)
            return
        if st["turns"] >= st["turn_limit"]:
            self._finish(st, events)

    def _finish(self, st: dict, events: list[dict]) -> None:
        if st["phase"] == "finished":
            return
        n = st["n"]
        alive = [i for i in range(n) if st["alive"][i]]
        dead = [i for i in range(n) if not st["alive"][i]]
        alive.sort(key=lambda i: (-self._net_worth(st, i), i))
        dead.sort(key=lambda i: (-self._net_worth(st, i), i))
        ranking = alive + dead
        st["ranking"] = ranking
        st["winner"] = ranking[0] if ranking else -1
        st["phase"] = "finished"
        st["pending"] = None
        st["auction"] = None
        events.append({"act": "finish", "seat": st["winner"]})

    # ---------------- AI ----------------

    def step_ai(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        if state.get("phase") == "finished":
            return None
        ai = set(ai_seats(seats)) if seats else set()
        ai |= {i for i in range(state["n"]) if state["is_ai"][i]}
        if not ai:
            return None
        st = copy_state(state)
        events: list[dict] = []

        # 1) 有待处理的交易且受让方是 AI → 立刻表态
        for t in st["trades"]:
            if t["status"] == "pending" and t["to"] in ai:
                self._ai_trade(st, t, events)
                return st, events
        # 2) 拍卖中且轮到 AI 出价
        if st["phase"] == "auction":
            a = st["auction"]
            if a and a["turn"] in ai:
                self._ai_bid(st, events)
                return st, events
            return None
        # 3) 待购地属于 AI
        if st["pending"] is not None:
            if st["pending"]["seat"] in ai:
                self._ai_buy(st, events)
                return st, events
            return None
        # 4) 轮到 AI 行动
        seat = st["turn"]
        if seat in ai and st["alive"][seat]:
            self._ai_turn(st, events)
            return st, events
        return None

    def _ai_turn(self, st: dict, events: list[dict]) -> None:
        seat = st["turn"]
        if st["in_jail"][seat] > 0:
            if st["cash"][seat] >= st["jail_fine"] + st["ai_buffer"]:
                self._pay_jail(st, seat, events)
            else:
                self._roll_jail(st, seat, events)
            return
        if not st["rolled"]:
            self._do_roll(st, seat, events)
            return
        if st["pending"] is not None:
            return
        # 现金宽裕时升级最便宜的、已集齐组的地块
        if st["cash"][seat] > st["ai_buffer"] * 3:
            best = -1
            for i in range(BOARD_LEN):
                if st["owner"][i] != seat or st["mortgaged"][i]:
                    continue
                tile = BOARD[i]
                if tile["kind"] != "property" or st["level"][i] >= 4:
                    continue
                if not self._group_complete(st, seat, tile["group"]):
                    continue
                if st["cash"][seat] - tile["build"] < st["ai_buffer"]:
                    continue
                if best < 0 or tile["build"] < BOARD[best]["build"]:
                    best = i
            if best >= 0:
                self._upgrade(st, seat, best, events)
                return
        self._end_turn(st, events)

    def _ai_buy(self, st: dict, events: list[dict]) -> None:
        p = st["pending"]
        seat = p["seat"]
        tile = BOARD[p["tile"]]
        if st["cash"][seat] - tile["price"] >= st["ai_buffer"]:
            self._buy(st, seat, p["tile"], events)
        else:
            tile_idx = p["tile"]
            st["pending"] = None
            self._start_auction(st, tile_idx, events)

    def _ai_bid(self, st: dict, events: list[dict]) -> None:
        a = st["auction"]
        seat = a["turn"]
        if a["high_seat"] == seat:                      # 自己就是最高价 → 不再抬价
            self._auction_pass(st, seat, events)
            return
        price = BOARD[a["tile"]]["price"]
        step = st["bid_step"]
        floor = a["high"] + step if a["high_seat"] >= 0 else step
        cap = min(price, st["cash"][seat] - st["ai_buffer"])
        if floor <= cap:
            self._auction_bid(st, seat, floor, events)
        else:
            self._auction_pass(st, seat, events)

    def _ai_trade(self, st: dict, trade: dict, events: list[dict]) -> None:
        received = self._value(st, trade["give"])
        given = self._value(st, trade["want"])
        self._trade_respond(st, trade["to"], trade["id"], received >= given, events)

    @staticmethod
    def _value(st: dict, bundle: dict) -> int:
        v = bundle["cash"]
        for t in bundle["tiles"]:
            price = BOARD[t]["price"]
            v += price if not st["mortgaged"][t] else price // 2
            v += st["level"][t] * BOARD[t].get("build", 0)
        v += len(bundle["items"]) * ITEM_VALUE
        return v

    # ---------------- 超时兜底 ----------------

    def on_timeout(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        if state.get("phase") == "finished":
            return None
        st = copy_state(state)
        events: list[dict] = []
        if st["phase"] == "auction" and st["auction"]:
            self._auction_pass(st, st["auction"]["turn"], events)
            return st, events
        if st["pending"] is not None:
            seat = st["pending"]["seat"]
            tile = st["pending"]["tile"]
            st["pending"] = None
            self._start_auction(st, tile, events)
            return st, events
        seat = st["turn"]
        if not st["alive"][seat]:
            self._end_turn(st, events)
            return st, events
        if st["in_jail"][seat] > 0:
            if st["cash"][seat] >= st["jail_fine"]:
                self._pay_jail(st, seat, events)
            else:
                self._roll_jail(st, seat, events)
        elif not st["rolled"]:
            self._do_roll(st, seat, events)
        else:
            self._end_turn(st, events)
        self._check_end(st, events)
        return st, events

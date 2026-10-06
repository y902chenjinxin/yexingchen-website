"""多席牌桌引擎框架（v2.44）。

三款牌类（掼蛋 / 麻将 / 大富翁）共用同一套「服务端权威」骨架：

- **状态即 JSON**：引擎的全部私有状态存在 `game_rooms.game_state`（JSON 列），
  含各家手牌 / 牌墙 / 阶段。**绝不下发**；对外只走 `view(state, seat)` 投影。
- **纯函数式推进**：`apply()` / `step_ai()` / `on_timeout()` 都接收 state、返回新 state
  （内部用 `copy_state` 深拷贝，避免污染调用方），事件流另行返回，由路由落成 `game_moves`。
- **AI 与真人同权**：AI 只基于「公开信息 + 自己手牌」决策，`step_ai()` 的决策入口与
  `apply()` 完全一致，天然不作弊。

引擎需要实现的接口见 `TableEngine`。注册走 `@register`，路由用 `get_engine(key)` 取。
"""
from __future__ import annotations

import json
import random

# 底注档位（豆），与 game_rooms.STAKES 保持一致
STAKES = (100, 500, 2000)


class TableError(Exception):
    """非法动作 / 状态异常。路由层会转成 400 INVALID_PARAM。"""


class TableEngine:
    key: str = ""
    seat_count: int = 4          # 默认席位数（掼蛋 / 麻将 = 4）
    min_humans: int = 2          # 开局所需最少真人数

    # ---------- 生命周期 ----------

    def new_game(self, seats: list[dict], config: dict, seed: int) -> dict:
        """开新局，返回初始 state（JSON 可序列化）。

        seats 为房间席位表：``[{seat, user_id, is_ai, name, ...}]``，长度 = 实际席位数。
        """
        raise NotImplementedError

    def view(self, state: dict, seat: int) -> dict:
        """投影：返回 seat 这一席**可见**的信息（含自己的手牌 / 私有选项）。

        约定返回结构至少包含：
        ``{"phase", "turn", "finished", "result", "players": [...], "me": {...}}``
        其中 players 只含公开信息（名字、张数、牌河、已出等），me 为该席位私有信息。
        """
        raise NotImplementedError

    def apply(self, state: dict, seat: int, action: dict) -> tuple[dict, list[dict]]:
        """校验并应用 seat 的动作，返回 ``(new_state, events)``；非法时 raise TableError。"""
        raise NotImplementedError

    def step_ai(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        """推进一手。当前行动席位是 AI，或存在可自动推进的步骤（发牌 / 进贡 / 结算）时，
        执行一步并返回 ``(new_state, events)``；轮到真人且无需自动推进时返回 None。"""
        return None

    def on_timeout(self, state: dict, seats: list[dict]) -> tuple[dict, list[dict]] | None:
        """真人操作超时（如还贡 30s）兜底：自动代打一手；无超时逻辑返回 None。"""
        return None

    def result(self, state: dict) -> dict | None:
        """已结束时返回 ``{"finished": True, "ranking": [seat...], "deltas": {seat: mult}}``，
        其中 deltas 是**底注倍数**（正=赢，负=输）；未结束返回 None。"""
        return None

    def abort(self, state: dict, seats: list[dict],
              quit_seat: int | None = None) -> tuple[dict, list[dict]] | None:
        """中途终止：有人退出时按**当前局势**补出终局（名次 / 结算），返回 ``(state, events)``。

        与 `on_timeout` 不同，这里不是「代打一手」而是「就地收摊」——让已进行到一半的牌局
        也能产出合法的 `result()`，避免「人走了、桌子还挂着、又打不完」。
        ``quit_seat`` 是主动退出者（退出＝认输，名次应排最后）。引擎不支持则返回 None。
        """
        return None


# ---------- 工具 ----------

def rng(seed: int) -> random.Random:
    return random.Random(int(seed) & 0xFFFFFFFF)


def copy_state(state: dict) -> dict:
    """深拷贝 state。走 JSON 往返，顺带保证结果一定可序列化。"""
    return json.loads(json.dumps(state, ensure_ascii=False))


def seat_index(seats: list[dict], user_id: int) -> int | None:
    for s in seats:
        if s.get("user_id") == user_id and not s.get("is_ai"):
            return int(s["seat"])
    return None


def ai_seats(seats: list[dict]) -> set[int]:
    return {int(s["seat"]) for s in seats if s.get("is_ai")}


def normalize_seats(raw) -> list[dict]:
    """把房间 seats 字段规整成 ``[{seat,user_id,is_ai,name,joined}]``（按 seat 升序）。"""
    out: list[dict] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        try:
            seat = int(item.get("seat"))
        except (TypeError, ValueError):
            continue
        out.append({
            "seat": seat,
            "user_id": int(item.get("user_id") or 0),
            "is_ai": bool(item.get("is_ai")),
            "name": str(item.get("name") or ("机器人" if item.get("is_ai") else "家人")),
            "joined": bool(item.get("joined")),
            "online_at": item.get("online_at"),
            "autopilot": bool(item.get("autopilot")),
        })
    out.sort(key=lambda s: s["seat"])
    return out


_ENGINES: dict[str, TableEngine] = {}


def register(cls):
    """引擎类装饰器：实例化并登记到注册表。"""
    inst = cls()
    if not inst.key:
        raise ValueError("引擎必须声明 key")
    _ENGINES[inst.key] = inst
    return cls


def get_engine(key: str) -> TableEngine:
    eng = _ENGINES.get(key)
    if eng is None:
        raise TableError(f"未知的牌桌类型：{key}")
    return eng


def engine_keys() -> list[str]:
    return sorted(_ENGINES.keys())

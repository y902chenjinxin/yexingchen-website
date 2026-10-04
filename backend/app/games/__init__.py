"""牌桌引擎包：导入即完成三款引擎的注册。"""
from app.games.base import (  # noqa: F401
    STAKES,
    TableEngine,
    TableError,
    ai_seats,
    copy_state,
    engine_keys,
    get_engine,
    normalize_seats,
    register,
    rng,
    seat_index,
)
from app.games import guandan as _guandan  # noqa: F401,E402
from app.games import mahjong as _mahjong  # noqa: F401,E402
from app.games import monopoly as _monopoly  # noqa: F401,E402

__all__ = [
    "STAKES",
    "TableEngine",
    "TableError",
    "ai_seats",
    "copy_state",
    "engine_keys",
    "get_engine",
    "normalize_seats",
    "register",
    "rng",
    "seat_index",
]

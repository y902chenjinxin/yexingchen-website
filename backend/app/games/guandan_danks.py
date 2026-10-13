"""DanKS V1 接入层（v2.46.70，夜星：「出牌策略有点定死」）。

移植自金山 AI 产品中心开源的 DanKS V1（Apache-2.0）：
https://github.com/Calix-L/DanKS —— 源码随包附于 ``app/games/danks_v1/``
（含 LICENSE/NOTICE）。V1 = 结构化候选检索 + 启发式评分引擎（纯 NumPy，
无训练权重依赖，CPU 单步毫秒级）。

适配器职责：把玄黄掼蛋引擎的手牌/牌型/历史翻译成 DanKS 的
RetrievalContext + 合法动作列表，用其评分挑最优动作；异常时返回 None
由调用方回退到旧启发式。夜星的三条出炸规则保留在 ai_choose 里作为
「DanKS 选择过牌时」的保底覆盖层。
"""

from __future__ import annotations

import logging

from .danks_v1.retrieval import StructuralCandidateRanker, build_context

logger = logging.getLogger(__name__)

# ---------------- 牌表示转换 ----------------

_RANK_TEXT = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
              10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}
_SUIT_TEXT = {"♠": "S", "♥": "H", "♣": "C", "♦": "D"}
# 我方 pattern type → DanKS kind
_KIND = {"single": "Single", "pair": "Pair", "triple": "Triple",
         "triple2": "TriplePlus", "straight": "Straight", "tube": "StraightPair",
         "plate": "StraightTriple", "bomb": "Bomb", "flushbomb": "StraightFlush",
         "rocket": "FourKings"}


def _label(card: dict) -> str:
    """我方牌 dict → DanKS 牌标签（如 ``S3``/``HT``/``BJ``/``RJ``）。

    红桃级牌（逢人配）自然映射为 ``H{level}``，DanKS 通过 curRank 识别其野牌身份。
    """
    if card.get("joker") == "big":
        return "RJ"
    if card.get("joker") == "small":
        return "BJ"
    return _SUIT_TEXT[card["suit"]] + _RANK_TEXT[int(card["rank"])]


def _key_text(key: int, level: int) -> str | None:
    """我方 pattern key（_key_of_rank 产物）→ DanKS rank 文本。"""
    if key >= 17:
        return "RJ"
    if key >= 16:
        return "BJ"
    if key == 15:  # 级牌
        return _RANK_TEXT.get(level)
    return _RANK_TEXT.get(key)


# ---------------- 上下文与动作翻译 ----------------

def _played_labels(st: dict) -> list[str]:
    out: list[str] = []
    for ev in st.get("history") or []:
        if isinstance(ev, dict) and ev.get("kind") == "play":
            out.extend(_label(c) for c in ev.get("cards") or [])
    return out


def _build_state(st: dict, seat: int, hand: list[dict],
                 target: dict | None, level: int) -> dict:
    """target = ai_choose 收到的牌型 pattern dict（非完整 target）；上家从 st 取。"""
    tgt_pat = target
    st_target = st.get("target") or {}
    return {
        "my_seat": seat,
        "curRank": _RANK_TEXT[level],
        "public_counts": [len(st["hands"][s]) for s in range(4)],
        "current_kind": _KIND.get(tgt_pat["type"], "Single") if tgt_pat else "Lead",
        "current_rank": _key_text(tgt_pat["key"], level) if tgt_pat else None,
        "current_size": len(st_target.get("cards") or ()) if tgt_pat else 0,
        "last_player": st_target.get("seat") if tgt_pat else None,
        "played_cards": _played_labels(st),
        "known_hand_cards": {str(seat): [_label(c) for c in hand]},
    }


def _actions_of(plays: list[tuple[list[dict], dict]], level: int,
                has_target: bool) -> tuple[list[dict], dict[str, list[dict]]]:
    """我方候选 → DanKS 动作列表；返回 (actions, label→原牌 的反查表)。"""
    actions: list[dict] = []
    label2card: dict[str, list[dict]] = {}
    for i, (cs, pat) in enumerate(plays):
        labels = [_label(c) for c in cs]
        for lb, c in zip(labels, cs):
            label2card.setdefault(lb, []).append(c)
        actions.append({
            "index": i,
            "kind": _KIND.get(pat["type"], "Single"),
            "cards": labels,
            "rank": _key_text(pat["key"], level),
        })
    if has_target:
        actions.append({"index": len(actions), "kind": "PASS", "cards": [], "rank": None})
    return actions, label2card


_RANKER = None


def _get_ranker():
    global _RANKER
    if _RANKER is None:
        _RANKER = StructuralCandidateRanker(max_partitions=8)
    return _RANKER


def danks_pick(st: dict, seat: int, hand: list[dict], target: dict | None,
               level: int, plays: list[tuple[list[dict], dict]]) -> list[dict] | None:
    """DanKS V1 选牌。返回要出的牌；``[]`` = 主动过牌；``None`` = 失败回退。

    注意：DanKS 平台约定 ``legal_actions`` 只含**当前合法动作**（跟牌时必须
    能压过 target + PASS），合法性由平台负责——传压不过的候选它会误当成
    可出（V24670-001 教训）。
    """
    try:
        if target is not None:
            from .guandan import can_beat  # 延迟导入避免环
            plays = [(cs, pat) for cs, pat in plays if can_beat(pat, target)]
        state = _build_state(st, seat, hand, target, level)
        actions, label2card = _actions_of(plays, level, target is not None)
        if not actions:
            return [] if target else None
        ctx = build_context(state)
        ranked = _get_ranker().rank([_label(c) for c in hand], actions, ctx)
        if not ranked:
            return None
        top = ranked[0].action
        if top.kind == "PASS":
            return []
        picked: list[dict] = []
        for lb in top.cards:
            pool = label2card.get(lb)
            if not pool:
                return None
            picked.append(pool.pop(0))
        if len(picked) != len(top.cards):
            return None
        return picked
    except Exception:  # noqa: BLE001 —— 第三方引擎任何异常都不许炸对局
        logger.exception("danks_pick failed, fallback to legacy heuristic")
        return None

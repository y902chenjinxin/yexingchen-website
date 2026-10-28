"""工作台・思维逻辑卡（v2.46.269）

夜星：
> 长脑子最快的就是学习思维逻辑，将 github 上所有关于思维逻辑的内容都以卡片的形式每天提供。

所以这张卡不是「再攒一堆定律」，而是**专门练逻辑**：怎么看出一个论证是空的、
怎么判断相关不是因果、怎么用演绎/归纳/溯因、别人在用哪一招糊弄你。

数据 `logic_data.json` 由 GitHub 上的公开清单交叉整理（logic / mind-models /
cognitive-bias 三类仓库），按四个类别轮转交错排列：
  谬误  43  形式与非形式谬误（打不赢就换招的那些）
  偏差  43  认知偏差（自己脑子里先歪掉的部分）
  模型  23  思维模型（换个角度看系统）
  方法  18  推理与检验方法（怎么把话说实）

交错是为了**每天不重样**：连续两天都是「谬误」很容易看腻。

字段：
  cat      类别（谬误 / 偏差 / 模型 / 方法）
  name     名称
  name_en  英文名
  one_line 一句话说透
  shape    它怎么运作（为什么会这样，机制在哪）
  example  一句具体例子（最好能对上自己的生活）
  howto    拆法：一句可以背下来、当场能用的反问
  caveat   什么时候这招本身会过头
"""
from __future__ import annotations

import json
import pathlib

from datetime import date as _date_cls

from fastapi import APIRouter, Depends, Query

from app.routers.workbench._common import ok
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/logic", tags=["工作台-思维逻辑"])

_EPOCH = _date_cls(2026, 1, 1)

_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        try:
            p = pathlib.Path(__file__).with_name("logic_data.json")
            data = json.loads(p.read_text(encoding="utf-8"))
            _cache = data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001
            _cache = []
    return _cache


def _entry_at(offset: int = 0) -> dict | None:
    items = _load()
    total = len(items)
    if not total:
        return None
    today = _date_cls.today()
    days = (today - _EPOCH).days + offset
    idx = days % total
    item = dict(items[idx])
    item["index"] = idx
    item["position"] = idx + 1
    item["total"] = total
    # 同类内的序号：谬误一共 43 条，这是第几条 —— 让人知道自己走了多远
    same = [x for x in items if x.get("cat") == item.get("cat")]
    item["cat_position"] = next(
        (i + 1 for i, x in enumerate(same) if x.get("id") == item.get("id")), 0
    )
    item["cat_total"] = len(same)
    item["day_no"] = days + 1
    item["round"] = days // total + 1
    item["remaining"] = total - (idx + 1)
    item["date"] = _date_cls.fromordinal(today.toordinal() + offset).isoformat()
    return item


@router.get("/today")
def logic_today(
    offset: int = Query(0, ge=-365, le=365, description="0=今天，-1=昨天，可翻到任意一天"),
    _user: dict = Depends(get_current_user),
):
    """今天的思维逻辑卡。数据缺失时返回 null，前端不渲染。"""
    return ok(_entry_at(offset))


@router.get("/list")
def logic_list(
    limit: int = Query(30, ge=1, le=120),
    cat: str = Query("", description="按类别过滤：谬误 / 偏差 / 模型 / 方法"),
    _user: dict = Depends(get_current_user),
):
    """最近若干天的卡片；传 cat 则只在该类别里轮转（回看用）。"""
    if cat:
        pool = [x for x in _load() if x.get("cat") == cat]
        items = []
        for i in range(min(limit, len(pool))):
            it = dict(pool[i])
            it["position"] = i + 1
            it["total"] = len(pool)
            items.append(it)
        return ok({"items": items, "total": len(pool), "cat": cat})

    items = [e for e in (_entry_at(i) for i in range(limit)) if e]
    return ok({"items": items, "total": len(_load())})


@router.get("/stats")
def logic_stats(_user: dict = Depends(get_current_user)):
    """分类统计，给卡片顶部的筛选用。"""
    items = _load()
    counts: dict[str, int] = {}
    for x in items:
        c = x.get("cat") or "其它"
        counts[c] = counts.get(c, 0) + 1
    return ok({
        "total": len(items),
        "cats": [{"cat": k, "count": v} for k, v in counts.items()],
    })

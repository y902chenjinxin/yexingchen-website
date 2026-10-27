"""工作台・定律卡（v2.46.255）

夜星：
> 去网上找下类似瞎猫理论、好运设计这列的理论，放在新的卡片里，我觉得我挺喜欢看这些东西的。

两个样本定性了这批内容是什么：
- **瞎猫理论**（纳瓦尔《纳瓦尔宝典》）：运气分四层 —— 瞎猫碰上死耗子、瞎折腾撞大运、
  有准备的头脑、吸引而来的运气。绝大多数人卡在第二层，以为自己努力，其实在乱撞。
- **好运设计**（史铁生）：设想一个完美来世，最后发现把挫折全删掉，成功时的喜悦也没了。

所以这不是教科书条目，是**「一句话把某件事说透」的镜片**：读完会点头，能拿去解释自己的生活。

和已有三张卡的分工：

| 卡片 | 收什么 |
|---|---|
| 每日英语 | 一个词 + 记忆法 |
| 每日知识 | 学科原理 + 寓言（**为什么会这样**） |
| 每日场景 | 人情世故怎么应对（**该怎么做**） |
| **定律卡** | 有名有姓的定律 / 效应 / 悖论（**原来世界是这样运转的**） |

字段：
  domain    领域（心理与自我 / 人际与社会 / 商业与组织 / 概率与运气 /
            时间与效率 / 系统与复杂 / 语言与思维 / 人生与哲学）
  name      名称（中文）
  name_en   英文名
  who       谁提的 / 出自哪（可为空）
  one_line  一句话说透它
  explain   来历与逻辑（这套说法到底在解释什么）
  reality   它在生活里的样子
  use       怎么拿它做判断
  caveat    什么时候它不成立、被谁滥用 —— 每条都写，不粉饰
"""
from __future__ import annotations

import json
import pathlib

from datetime import date as _date_cls

from fastapi import APIRouter, Depends, Query

from app.routers.workbench._common import ok
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/laws", tags=["工作台-定律"])

_EPOCH = _date_cls(2026, 1, 1)

_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        try:
            p = pathlib.Path(__file__).with_name("laws_data.json")
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
    item["day_no"] = days + 1
    item["round"] = days // total + 1
    item["remaining"] = total - (idx + 1)
    item["date"] = _date_cls.fromordinal(today.toordinal() + offset).isoformat()
    return item


@router.get("/today")
def law_today(
    offset: int = Query(0, ge=-30, le=30, description="0=今天，-1=昨天"),
    _user: dict = Depends(get_current_user),
):
    """今天的定律卡。数据缺失时返回 null，前端不渲染。"""
    return ok(_entry_at(offset))


@router.get("/list")
def law_list(
    limit: int = Query(30, ge=1, le=60),
    _user: dict = Depends(get_current_user),
):
    items = [e for e in (_entry_at(i) for i in range(limit)) if e]
    return ok({"items": items, "total": len(_load())})

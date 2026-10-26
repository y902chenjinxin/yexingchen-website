"""工作台・每日知识（v2.46.248）

夜星的诉求原话：
> 找下所有值得我学习的知识点，比如经济学，比如生物学，比如各种其他的可以扩张我知识面的学科，
> 每天在里面找一个知识点，用通俗易懂的话编一个寓言故事，能让我快速理解的……
> 主要就是想形成被动学习的效果。

设计取舍：
- **寓言故事是主体**，不是「名词解释 + 例子」。人记住的是人和场景，不是术语，
  所以每条都有一个具体的、有名字有动作的小故事，术语只在「所以呢」里点一次。
- **每天一条，按学科轮转**，全部走完再回头（与每日英语同一套心智，同一套取模逻辑）。
- 内容固化在 `knowledge_data.json`（11 学科 × 20 条 = 220 条，约 7 个月一轮），
  运行时零外部调用 —— 每天都要出现的东西，稳定 > 新鲜；断网、欠费都照样能看。
- 数据结构里有 `apply`（怎么用在自己身上）和 `question`（一句自省提问），
  这两栏是「看完就忘」和「真的改了行为」之间的差别。

字段：
  field / concept / concept_en   学科 / 知识点 / 英文名
  one_line                       一句话说穿
  fable                          180~260 字原创寓言
  insight                        故事 ↔ 原理的对位
  apply                          能立刻用在自己身上的做法
  question                       一句自省提问
"""
from __future__ import annotations

import json
import pathlib

from datetime import date as _date_cls

from fastapi import APIRouter, Depends, Query

from app.routers.workbench._common import ok
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/knowledge", tags=["工作台-每日知识"])

# 取词基准日：与每日英语一致，避免负数取模的边界情况
_EPOCH = _date_cls(2026, 1, 1)

_cache: list[dict] | None = None


def _load() -> list[dict]:
    """读知识库 JSON。缺失 / 损坏时返回空表 —— 卡片不显示，但不影响工作台其它模块。"""
    global _cache
    if _cache is None:
        try:
            p = pathlib.Path(__file__).with_name("knowledge_data.json")
            data = json.loads(p.read_text(encoding="utf-8"))
            _cache = data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001
            _cache = []
    return _cache


def _entry_at(offset: int = 0) -> dict | None:
    """offset=0 是今天，-1 是昨天，+1 是明天。"""
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
def knowledge_today(
    offset: int = Query(0, ge=-30, le=30, description="0=今天，-1=昨天"),
    _user: dict = Depends(get_current_user),
):
    """今天的知识卡。词库读不到时返回 data=null，前端不渲染这张卡。"""
    return ok(_entry_at(offset))


@router.get("/list")
def knowledge_list(
    limit: int = Query(30, ge=1, le=60),
    _user: dict = Depends(get_current_user),
):
    """往后翻的知识卡（前端做「翻一翻」用）。"""
    items = [e for e in (_entry_at(i) for i in range(limit)) if e]
    return ok({"items": items, "total": len(_load())})

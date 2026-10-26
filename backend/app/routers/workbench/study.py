"""工作台・每日英语（v2.46.245）

夜星要的「被动学习」：每天一个单词 + 时态变化 + 组词 + 一个超过 50 词的长句（带中文）。
不用费神，打开工作台就看一眼。

设计：
- **内置词库**（`_study_data.py`，30 条 = 一个自然月循环），不调外部模型：
  每天都要出现的东西，稳定比「新」重要；断网/欠费也照样能用。
- 按**本地日期**取词：`days_since_epoch % len(ALL)`，同一天永远同一词（
  刷新不会换掉，跟「每日一言」同样的心智）。
- 可选 `?offset=N` 往前/往后看几天，方便「昨天那个词想看回来」。
"""
from __future__ import annotations

from datetime import date as _date_cls

from fastapi import APIRouter, Depends, Query

from app.routers.workbench._common import ok
from app.utils.security import get_current_user
from app.routers.workbench._study_data import ALL

router = APIRouter(prefix="/api/study", tags=["工作台-每日英语"])

# 取词基准日：用固定日期而不是 1970，避免负数取模的边界情况
_EPOCH = _date_cls(2026, 1, 1)


def _entry_at(offset: int = 0) -> dict:
    """offset=0 是今天，-1 是昨天，+1 是明天。"""
    today = _date_cls.today()
    idx = ((today - _EPOCH).days + offset) % len(ALL)
    item = dict(ALL[idx])
    item["index"] = idx
    item["day_no"] = ((today - _EPOCH).days + offset) + 1     # 从 1 开始，给前端显示「第 N 天」
    item["cycle_len"] = len(ALL)
    item["date"] = _date_cls.fromordinal(today.toordinal() + offset).isoformat()
    item["word_count"] = len(item["sentence"].split())
    return item


@router.get("/today")
def study_today(
    offset: int = Query(0, ge=-30, le=30, description="0=今天，-1=昨天"),
    _user: dict = Depends(get_current_user),
):
    """今天的单词卡。"""
    return ok(_entry_at(offset))


@router.get("/list")
def study_list(
    limit: int = Query(30, ge=1, le=60),
    _user: dict = Depends(get_current_user),
):
    """词库预览（按日期顺序，从今天往后排），前端做「翻一翻」用。"""
    return ok({"items": [_entry_at(i) for i in range(limit)], "cycle_len": len(ALL)})

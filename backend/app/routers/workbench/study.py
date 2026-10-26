"""工作台・每日英语（v2.46.245 / 词库 v2.46.247）

夜星要的「被动学习」：每天一个单词 + 时态变化 + 组词 + 一个超过 50 词的长句（带中文）。
不用费神，打开工作台就看一眼。

设计（v2.46.247 起是「长期任务」口径）：
- **内置词典**（`study_words.json`，500 词，CET6/考研/雅思区间），不调外部模型：
  每天都要出现的东西，稳定比「新」重要；断网、欠费也照样能用。
- 按**本地日期**顺序取词：`(today - EPOCH).days % len(ALL)`。
  所以每天都是**没看过的新词**，整本走完（约 500 天）才回到第一个，进入第二轮。
  同一天永远同一词（刷新不换），跟「每日一言」同样的心智。
- 可选 `?offset=N` 往前/往后看几天，方便「昨天那个词想看回来」。

词条来源：ECDICT（skywind3000，MIT）提供词的音标/释义/变形骨架，
搭配与 55~70 词长句由一次性脚本生成后固化进 JSON —— 运行时零依赖。
"""
from __future__ import annotations

from datetime import date as _date_cls

from fastapi import APIRouter, Depends, Query

from app.routers.workbench._common import ok
from app.utils.security import get_current_user
from app.routers.workbench._study_data import ALL as CURATED
from app.routers.workbench._study_dict import merge as _merge

# 精选 30 条在前 + study_words.json 的词典级词库在后（约 950 词，按词频排序）
ALL = _merge(CURATED)

router = APIRouter(prefix="/api/study", tags=["工作台-每日英语"])

# 取词基准日：用固定日期而不是 1970，避免负数取模的边界情况
_EPOCH = _date_cls(2026, 1, 1)


def _entry_at(offset: int = 0) -> dict:
    """offset=0 是今天，-1 是昨天，+1 是明天。"""
    today = _date_cls.today()
    total = len(ALL)
    days = (today - _EPOCH).days + offset
    idx = days % total
    item = dict(ALL[idx])
    item["index"] = idx
    item["day_no"] = days + 1                                # 从 1 开始，给前端显示「第 N 天」
    item["total"] = total
    item["position"] = idx + 1                               # 这是词库里的第几个词
    item["round"] = days // total + 1                        # 第几轮（词库走完一次 +1）
    item["remaining"] = total - (idx + 1)                    # 这一轮还剩几词
    item["cycle_len"] = total                                # 兼容旧前端字段
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

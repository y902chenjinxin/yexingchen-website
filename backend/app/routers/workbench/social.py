"""工作台・人情世故（v2.46.249）

夜星：
> 现在 github 上有个人情世故指南，你集成下，然后在工作台做个模块，每日展示一个场景，
> 点击卡片展开查看这个场景，当小故事看的。

**关于来源（重要）**：GitHub 上最有名的是 `kkk-bot/HowToGetAlong`《人情世故指南》（10 章 77 条），
但它的 LICENSE 是**自定义「个人非商业学习使用许可」**，明确写了：除个人使用与链接分享外，
公开转载、收录、改编、二创发布都必须先取得作者书面同意（基础授权 59.9 元）。
所以这里**没有收录它的正文**，而是自写了一套同结构的内容：

- 主题是公共社交常识（拒绝、谈钱、饭局、亲戚……），表达全部原创；
- 卡片底部外链回原项目（链接分享是该许可明确允许的）；
- 如果以后想要原文，需要去 Issues 找作者要授权。

同结构参考了三个项目（都是我在调研时看的，没抄正文）：
  kkk-bot/HowToGetAlong   「判断关键 / 怎么做 / 怎么说 / 代价 / 例外」这一套拆法
  endual/Tianji（Apache-2.0）  七大领域的分类思路（敬酒 / 请客 / 送礼 / 祝福 / 说话 / 尴尬 / 冲突）
  GeminiLight/SocialCoach（Apache-2.0）  「先预演再上场」的产品形态

字段：
  domain   领域（职场分寸 / 求人办事 / 得体拒绝 / 谈钱 / 饭局与酒 / 送礼与回礼 / 亲戚与家庭 / 冲突与尴尬）
  scene    具体场景（卡片标题）
  name     故事主角名（每条不同，避免所有故事都叫「老周」）
  hook     难在哪（收起时唯一可见的一句）
  story    80~130 字小故事
  judge    判断关键
  do       怎么做（2~3 步，分号分隔）
  say      可以怎么说（可直接复制的台词）
  cost     代价
  trap     常见错误 / 例外
"""
from __future__ import annotations

import json
import pathlib

from datetime import date as _date_cls

from fastapi import APIRouter, Depends, Query

from app.routers.workbench._common import ok
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/social", tags=["工作台-人情世故"])

_EPOCH = _date_cls(2026, 1, 1)

_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        try:
            p = pathlib.Path(__file__).with_name("social_data.json")
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
def social_today(
    offset: int = Query(0, ge=-30, le=30, description="0=今天，-1=昨天"),
    _user: dict = Depends(get_current_user),
):
    """今天的场景卡。数据缺失时返回 null，前端不渲染。"""
    return ok(_entry_at(offset))


@router.get("/list")
def social_list(
    limit: int = Query(30, ge=1, le=60),
    _user: dict = Depends(get_current_user),
):
    items = [e for e in (_entry_at(i) for i in range(limit)) if e]
    return ok({"items": items, "total": len(_load())})

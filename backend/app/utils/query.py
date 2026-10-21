"""查询条件收口（v2.46.169）

## 为什么要有它

全库此前有 **130 处** `X.household_id == HOUSEHOLD_ID` 和 **104 处** `X.deleted_at.is_(None)`，
每个查询各写一遍。问题有两个：

1. **漏写就是事故**：漏家庭过滤 = 串户（看到别人家的钱）；
   漏软删过滤 = 把已删数据当有效数据查出来。
2. **常量有 9 个来源**：8 个 router 各自 `HOUSEHOLD_ID = 1`，另有 6 个从
   `services.household` import。将来若支持多家庭，改一处必漏八处。
   （这一项已在 v2.46.169 统一到 `services.household`，勿再本地定义。）

## 用法

```python
from app.utils.query import scoped, in_house, alive

# 最常见：家庭隔离 + 软删过滤，一次到位
db.query(Contact).filter(scoped(Contact)).all()

# 只需要家庭隔离（表没有 deleted_at，或确实要包含已删数据）
db.query(SomeModel).filter(in_house(SomeModel)).all()

# 只要软删过滤（如按 user_id 归属、不涉及家庭的表）
db.query(Note).filter(Note.user_id == uid, alive(Note)).all()
```

`scoped()` 会自动判断模型有没有 `deleted_at` 列 —— 没有就只做家庭隔离，不会报错。

## 边界

- 这个模块**不改变**任何现有查询行为，只是把重复条件抽成单点。
- 多家庭支持时，只需把 `HOUSEHOLD_ID` 换成从请求上下文取，全部 `scoped()` 调用自动生效。
"""
from __future__ import annotations

from sqlalchemy import and_

from app.services.household import HOUSEHOLD_ID


def in_house(model, household_id: int | None = None):
    """家庭隔离条件。默认取全局 HOUSEHOLD_ID。"""
    return model.household_id == (HOUSEHOLD_ID if household_id is None else household_id)


def alive(model):
    """软删过滤条件；模型没有 deleted_at 列时返回 None。"""
    col = getattr(model, "deleted_at", None)
    return None if col is None else col.is_(None)


def scoped(model, household_id: int | None = None):
    """家庭隔离 + 软删过滤的组合条件，可直接丢给 .filter()。

    模型无 deleted_at 时只返回家庭隔离条件，不会因为缺列而报错。
    """
    conds = [in_house(model, household_id)]
    soft = alive(model)
    if soft is not None:
        conds.append(soft)
    return and_(*conds)

"""工作台・每日一题（v2.46.270）

夜星：
> 给我找一些脑筋急转弯的题目，考公的题目等等，就是那种绕来绕去的，
> 但是能扩张思维边界的，然后每天以卡片形式出一题，要有选项和最终答案的。

所以这不是「每日一句」，是**每天一道带选项的题**：先做，再看答案和解析。

数据 `quiz_data.json`，77 题七类，按类别轮转交错（每天换一种脑子）：
  逻辑判断 12   真假话、必要条件、排列对应、抽屉原理
  数量关系 12   工程、行程、浓度、日期、排列组合、钟表
  概率直觉 10   三门问题、假阳性、生日悖论、辛普森悖论、信封悖论
  思维陷阱  8   幸存者偏差、沉没成本、相关非因果、确认偏误
  脑筋急转弯 15 字面拆解、条件陷阱、视角偷换
  定义判断 10   沉没成本/机会成本/道德风险/逆向选择/帕累托改进…
  类比推理 10   工具、种属、组成、因果、功能、顺承

字段：
  cat      类别
  level    1 简单 / 2 中等 / 3 烧脑
  q        题干
  options  四个选项（顺序在落库时已确定性打乱，避免答案总在 A）
  answer   正确选项下标（0-3）
  why      解析：为什么是这个，以及为什么会选错
  trick    绕点：这题练的是哪种思维，一句话可以带走

⚠️ 落库时用固定 seed 打乱过选项，答案分布 A/B/C/D 约 23/19/15/20。
   以后加题也要打乱，否则「总选 B」就能蒙对。
"""
from __future__ import annotations

import json
import pathlib
import re

from datetime import date as _date_cls, timedelta as _timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import QuizAnswer
from app.routers.workbench._common import ok
from app.routers.workbench.logic import _load as _load_logic
from app.utils.security import get_current_user

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

router = APIRouter(prefix="/api/quiz", tags=["工作台-每日一题"])

_EPOCH = _date_cls(2026, 1, 1)

_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        try:
            p = pathlib.Path(__file__).with_name("quiz_data.json")
            data = json.loads(p.read_text(encoding="utf-8"))
            _cache = data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001
            _cache = []
    return _cache


def _related(topic: str) -> dict | None:
    """题目挂到的概念，从思维逻辑库（127 条）里取完整解释（v2.46.273）。

    设计取舍：**不给所有题都硬挂一个概念**。175 题里只有 19 题真的在考某个可命名的
    心理效应（沉没成本 / 确认偏误 / 框架效应…），其余是纯计算、字面拆解、语法辨析，
    本来就没有「延伸阅读」这回事。覆盖率 11% 是真实的，不是为了凑数去硬配。
    """
    if not topic:
        return None
    for x in _load_logic():
        if x.get("name") == topic:
            return {
                "name": x.get("name", ""),
                "name_en": x.get("name_en", ""),
                "cat": x.get("cat", ""),
                "one_line": x.get("one_line", ""),
                "shape": x.get("shape", ""),
                "example": x.get("example", ""),
                "howto": x.get("howto", ""),
                "caveat": x.get("caveat", ""),
            }
    return None


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
    item["related"] = _related(item.get("topic", ""))
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
def quiz_today(
    offset: int = Query(0, ge=-365, le=365, description="0=今天，-1=昨天，可翻到任意一天"),
    _user: dict = Depends(get_current_user),
):
    """今天的题目（含答案与解析，前端在用户作答后才展开）。数据缺失返回 null。"""
    return ok(_entry_at(offset))


@router.get("/list")
def quiz_list(
    # v2.46.271：题库扩到 155 条，limit 上限跟着提到 300（原来 120 取不全，验证时踩到 422）
    limit: int = Query(10, ge=1, le=300),
    cat: str = Query("", description="按类别过滤：逻辑判断 / 数量关系 / 概率直觉 / 思维陷阱 / 脑筋急转弯 / 定义判断 / 类比推理"),
    _user: dict = Depends(get_current_user),
):
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
def quiz_stats(_user: dict = Depends(get_current_user)):
    items = _load()
    counts: dict[str, int] = {}
    for x in items:
        c = x.get("cat") or "其它"
        counts[c] = counts.get(c, 0) + 1
    return ok({
        "total": len(items),
        "cats": [{"cat": k, "count": v} for k, v in counts.items()],
        "levels": {
            str(lv): sum(1 for x in items if x.get("level") == lv)
            for lv in (1, 2, 3)
        },
    })


# ======================= 答题记录（v2.46.274 跨设备） =======================
# 夜星：「要支持跨设备，优化下。」——之前错题本和七天格都在 localStorage，
# 换设备/清缓存就没了。现在按账号落库，本地那份只作接口失败时的兜底。

def _my_stats(db: Session, uid: int, days: int = 7) -> dict:
    """我的答题统计：累计 + 最近 N 天（每天有错=bad，全对=ok，没答=none）。"""
    rows = db.query(QuizAnswer).filter(QuizAnswer.user_id == uid).all()
    total = len(rows)
    right = sum(1 for r in rows if r.correct)

    by_date: dict[str, list[bool]] = {}
    for r in rows:
        by_date.setdefault(r.quiz_date or "", []).append(bool(r.correct))

    today = _date_cls.today()
    out = []
    for k in range(days - 1, -1, -1):
        d = today - _timedelta(days=k)
        key = d.isoformat()
        arr = by_date.get(key)
        state = "none" if not arr else ("bad" if any(not c for c in arr) else "ok")
        out.append({"date": key, "state": state})

    return {
        "total": total,
        "correct": right,
        "rate": round(right / total * 100) if total else 0,
        "wrong": total - right,
        "days": out,
    }


@router.get("/mine")
def quiz_mine(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """我的答题统计（跨设备）：累计正确率 + 最近 7 天。"""
    return ok(_my_stats(db, int(_user["user_id"])))


@router.post("/answer")
def quiz_answer(
    payload: dict,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """提交一次作答。upsert：同一题再答是更新，答对之后自动离开错题本。"""
    uid = int(_user["user_id"])
    try:
        quiz_id = int(payload.get("quiz_id") or 0)
        picked = int(payload.get("picked"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="参数不合法")

    item = next((x for x in _load() if x.get("id") == quiz_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="题目不存在")
    if not 0 <= picked <= 3:
        raise HTTPException(status_code=400, detail="选项越界")

    raw_date = str(payload.get("date") or "")
    quiz_date = raw_date if _DATE_RE.match(raw_date) else _date_cls.today().isoformat()
    correct = picked == int(item.get("answer", -1))

    row = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.user_id == uid, QuizAnswer.quiz_id == quiz_id)
        .first()
    )
    if row:
        row.picked = picked
        row.correct = correct
        row.quiz_date = quiz_date
    else:
        db.add(QuizAnswer(
            user_id=uid, quiz_id=quiz_id, quiz_date=quiz_date,
            picked=picked, correct=correct,
        ))
    db.commit()

    return ok({"correct": correct, "stats": _my_stats(db, uid)})


@router.get("/mistakes")
def quiz_mistakes(
    limit: int = Query(80, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """错题本（跨设备）：答错且**还没答对**的题，带完整题面与解析。"""
    uid = int(_user["user_id"])
    rows = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.user_id == uid, QuizAnswer.correct.is_(False))
        .order_by(QuizAnswer.updated_at.desc(), QuizAnswer.id.desc())
        .limit(limit)
        .all()
    )
    idx = {int(x.get("id", 0)): x for x in _load()}
    items = []
    for r in rows:
        q = idx.get(int(r.quiz_id))
        if not q:
            continue   # 题库里已无此题（下架/改号）：跳过，不留空壳
        items.append({
            "id": q.get("id"),
            "cat": q.get("cat", ""),
            "level": q.get("level", 2),
            "q": q.get("q", ""),
            "table": q.get("table"),
            "options": q.get("options", []),
            "answer": q.get("answer", 0),
            "why": q.get("why", ""),
            "trick": q.get("trick", ""),
            "topic": q.get("topic", ""),
            "picked": int(r.picked),
            "date": r.quiz_date or "",
        })
    return ok({"items": items, "total": len(items)})


@router.delete("/mistakes/{quiz_id}")
def quiz_mistake_drop(
    quiz_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """从错题本移除一道（连记录一起删，统计也跟着少一条）。"""
    uid = int(_user["user_id"])
    n = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.user_id == uid, QuizAnswer.quiz_id == quiz_id)
        .delete()
    )
    db.commit()
    return ok({"removed": int(n)})


@router.delete("/mistakes")
def quiz_mistake_clear(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """清空错题本。"""
    uid = int(_user["user_id"])
    n = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.user_id == uid, QuizAnswer.correct.is_(False))
        .delete()
    )
    db.commit()
    return ok({"removed": int(n)})


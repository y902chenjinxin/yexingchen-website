"""词典级词库加载器（v2.46.247）

夜星：单词要「按照英文词典来，每天都是新的，全部完成了再循环着来，作为长期的任务」。
原来 `_study_data.py` 里 30 条手写词一个月就循环完了，不够长期。

现在拆成两部分：

- `_study_data.py` 的 30 条 = 手工写定的精选词，排在词库最前面（质量最高，已上线验证过）
- `study_words.json` = 词典级词库，约 950 个 CET6 / 考研 / 雅思区间的进阶词

JSON 里每条字段与手工词完全一致：
  w / ipa / pos / zh / forms_label / forms / collocations / sentence / sentence_zh

数据来自 ECDICT（skywind3000，MIT 许可）的词表与释义骨架，
搭配和 55~70 词长句由一次性生成脚本产出后固化 —— 运行时零外部依赖、零费用，
断网或模型欠费都照样能看。要扩词直接往 JSON 里追加，或者替换整份文件。

为什么不放 DB：这张卡是「每天都一样」的只读内容，进库只会多一次查询和一套迁移，
放文件更简单、更快、也更好备份和 diff。
"""
from __future__ import annotations

import json
import pathlib
from typing import Iterable

_HERE = pathlib.Path(__file__).parent
_JSON_PATH = _HERE / "study_words.json"

_cache: list[dict] | None = None


def load_generated() -> list[dict]:
    """读词典 JSON。文件缺失 / 损坏时返回空表 —— 卡片退化成只有精选词，不报错。"""
    global _cache
    if _cache is None:
        try:
            data = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
            _cache = data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001 —— 词库坏了不该拖垮工作台
            _cache = []
    return _cache


def merge(curated: Iterable[dict]) -> list[dict]:
    """精选词在前 + 词典词在后，按 `w` 去重（精选优先）。"""
    merged: list[dict] = []
    seen: set[str] = set()
    for entry in curated:
        w = entry.get("w")
        if not w or w in seen:
            continue
        seen.add(w)
        merged.append(entry)
    for entry in load_generated():
        w = entry.get("w")
        if not w or w in seen:
            continue
        seen.add(w)
        merged.append(entry)
    return merged

"""TXT 小说解析服务（v2.46.283）

背景：此前 TXT 每次打开都由**前端**全量 fetch + 前端切章，13MB 的 txt（约 650 万字）
在手机上要 split 几十万行、全部段落驻内存，实测卡死/解析不完。改成后端一次解析、
前端按章取。

产物（列在 uploads/novels/.cache/ 下）：
- `{id}.txt`   归一化后的 UTF-8 正文（一次转码，之后按字节偏移 seek 读）
- `{id}.json`  {encoding, chars, chapters:[{t, s, e}]}，s/e 是上面 .txt 的**字节**偏移

这样单章读取是 seek + read，复杂度只跟章大小相关（几十 KB，毫秒级）。
解析本身是一次 decode + 一次 split('\n') + 逐行正则，13MB 实测 1~2 秒（服务器 CPU）。
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

# 章节标题：整行匹配、长度 ≤ 42（与前端旧逻辑保持一致，避免同一本书两边切分不同）
CHAPTER_RE = re.compile(
    r'^[\s\u3000]*(第\s*[0-9零一二三四五六七八九十百千万两]+\s*[章回节卷篇]'
    r'|卷\s*[0-9零一二三四五六七八九十百千万两]+'
    r'|序章|楔子|引子|尾声|后记|番外)[^\n]{0,40}$'
)

CACHE_DIRNAME = '.cache'


def _decode(raw: bytes) -> tuple[str, str]:
    """BOM → 严格 UTF-8 → GBK → UTF-16 → UTF-8 容错。返回 (文本, 编码名)。"""
    if raw[:3] == b'\xef\xbb\xbf':
        return raw[3:].decode('utf-8', 'replace'), 'utf-8-sig'
    if raw[:2] == b'\xff\xfe':
        return raw[2:].decode('utf-16-le', 'replace'), 'utf-16-le'
    if raw[:2] == b'\xfe\xff':
        return raw[2:].decode('utf-16-be', 'replace'), 'utf-16-be'
    try:
        return raw.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        pass
    for enc in ('gbk', 'gb18030', 'big5'):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', 'replace'), 'utf-8(含替换字符)'


def split_chapters(text: str) -> list[dict]:
    """单次扫描切章。返回 [{t: 标题, s: 字符起点, e: 字符终点}]。

    🔴 必须过滤「目录页」（v2.46.283 实测）：很多 TXT 开头有整页目录，
    「第001章 xxx」一行接一行 —— 直接按行切会把目录每一行都当成一章，
    结果是 2479 个章节里一半只有标题没有正文，翻页体验灾难。
    判据：与下一个候选标题的间距 < 80 字符 → 视为目录项丢弃。
    """
    # 1) 扫候选标题位置
    cands: list[tuple[str, int]] = []
    offset = 0
    for line in text.split('\n'):
        probe = line.strip()
        if probe and len(probe) <= 42 and CHAPTER_RE.match(probe):
            cands.append((probe, offset))
        offset += len(line) + 1

    if not cands:
        return [{'t': '正文', 's': 0, 'e': len(text)}]

    # 2) 目录项过滤：紧跟下一个标题（间距过小）= 目录行，不是真章节
    kept: list[tuple[str, int]] = []
    for i, (title, start) in enumerate(cands):
        nxt = cands[i + 1][1] if i + 1 < len(cands) else len(text)
        if nxt - start < 80:
            continue
        kept.append((title, start))
    if not kept:            # 全书都是短章（极端情况）：回退不过滤
        kept = cands

    # 3) 组装区间：第一个真标题之前的内容算「开始」
    chapters: list[dict] = []
    if kept[0][1] > 0:
        chapters.append({'t': '开始', 's': 0, 'e': kept[0][1]})
    for i, (title, start) in enumerate(kept):
        end = kept[i + 1][1] if i + 1 < len(kept) else len(text)
        chapters.append({'t': title, 's': start, 'e': end})
    return chapters


def _paras(seg: str) -> list[str]:
    """章节正文切段：逐行拼接，空行分段（与前端旧口径一致）。"""
    out: list[str] = []
    buf: list[str] = []
    for line in seg.split('\n'):
        line = line.replace('\u00a0', ' ').strip()
        if not line:
            if buf:
                out.append(''.join(buf))
                buf = []
        else:
            buf.append(line)
    if buf:
        out.append(''.join(buf))
    return out


def cache_dir_for(file_path: str) -> str:
    """缓存目录：与上传文件同级的 .cache/（uploads/novels/.cache）。"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel = file_path.lstrip('/').replace('\\', '/')
    if not rel.startswith('uploads/'):
        rel = 'uploads/' + rel
    full = os.path.normpath(os.path.join(backend_dir, rel))
    return os.path.join(os.path.dirname(full), CACHE_DIRNAME)


def resolve_upload_path(file_path: str) -> Optional[str]:
    """把 Novel.file_path 解析成磁盘绝对路径（老数据 /uploads/xxx，新数据 /xxx）。"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel = (file_path or '').lstrip('/').replace('\\', '/')
    if not rel.startswith('uploads/'):
        rel = 'uploads/' + rel
    full = os.path.normpath(os.path.join(backend_dir, rel))
    return full if os.path.isfile(full) else None


def parse_novel_txt(novel_id: int, file_path: str) -> dict:
    """解析一本 TXT 并写缓存。返回 {encoding, chars, chapters}。抛异常由调用方记 failed。"""
    full = resolve_upload_path(file_path)
    if not full:
        raise FileNotFoundError('小说文件不存在')

    t0 = time.time()
    with open(full, 'rb') as f:
        raw = f.read()
    text, enc = _decode(raw)
    del raw
    if '\r' in text:
        text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.lstrip('\ufeff')

    ch_chars = split_chapters(text)

    # 逐章 encode 累加字节偏移，顺手拼出归一化全文（总字节量 = 一次全文 encode）
    buf = bytearray()
    chapters: list[dict] = []
    for ch in ch_chars:
        seg = text[ch['s']:ch['e']]
        b = seg.encode('utf-8')
        chapters.append({'t': ch['t'], 's': len(buf), 'e': len(buf) + len(b)})
        buf += b
    del text

    cdir = cache_dir_for(file_path)
    os.makedirs(cdir, exist_ok=True)
    txt_path = os.path.join(cdir, f'{novel_id}.txt')
    json_path = os.path.join(cdir, f'{novel_id}.json')
    with open(txt_path, 'wb') as f:
        f.write(bytes(buf))

    meta = {
        'encoding': enc,
        'chars': len(buf),
        'chapters': chapters,
        'parsed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'cost_ms': int((time.time() - t0) * 1000),
    }
    tmp = json_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False)
    os.replace(tmp, json_path)   # 原子替换，读侧不会看到半截文件
    return meta


def load_index(novel_id: int, file_path: str) -> Optional[dict]:
    """读缓存索引；没有返回 None。"""
    json_path = os.path.join(cache_dir_for(file_path), f'{novel_id}.json')
    if not os.path.isfile(json_path):
        return None
    try:
        with open(json_path, encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def read_chapter(novel_id: int, file_path: str, idx: int) -> Optional[dict]:
    """按章读正文。返回 {i, title, paras, total} 或 None。"""
    meta = load_index(novel_id, file_path)
    if not meta:
        return None
    chapters = meta.get('chapters') or []
    if idx < 0 or idx >= len(chapters):
        return None
    ch = chapters[idx]
    txt_path = os.path.join(cache_dir_for(file_path), f'{novel_id}.txt')
    with open(txt_path, 'rb') as f:
        f.seek(ch['s'])
        seg = f.read(ch['e'] - ch['s']).decode('utf-8', 'replace')
    paras = _paras(seg)
    # 章节正文首段往往就是标题本身（标题与正文之间没空行）→ 去掉，模板已单独渲染标题
    if paras and paras[0].strip() == ch['t'].strip():
        paras = paras[1:]
    return {
        'i': idx,
        'title': ch['t'],
        'paras': paras,
        'total': len(chapters),
    }


def search(novel_id: int, file_path: str, q: str, limit: int = 300) -> list[dict]:
    """全文搜索（在后端的归一化缓存上跑，13MB 几百 MB 也只几十毫秒）。"""
    meta = load_index(novel_id, file_path)
    if not meta or not q:
        return []
    txt_path = os.path.join(cache_dir_for(file_path), f'{novel_id}.txt')
    chapters = meta.get('chapters') or []
    out: list[dict] = []
    with open(txt_path, 'rb') as f:
        for i, ch in enumerate(chapters):
            f.seek(ch['s'])
            seg = f.read(ch['e'] - ch['s']).decode('utf-8', 'replace')
            pos = seg.find(q)
            while pos >= 0 and len(out) < limit:
                out.append({
                    'i': i,
                    'title': ch['t'],
                    'snippet': seg[max(0, pos - 24): pos + len(q) + 34].replace('\n', ' '),
                })
                pos = seg.find(q, pos + len(q))
            if len(out) >= limit:
                break
    return out


def drop_cache(novel_id: int, file_path: str) -> None:
    """删书时清缓存。"""
    cdir = cache_dir_for(file_path)
    for name in (f'{novel_id}.txt', f'{novel_id}.json'):
        p = os.path.join(cdir, name)
        if os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass

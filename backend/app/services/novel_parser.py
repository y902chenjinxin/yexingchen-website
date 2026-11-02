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

# =====================================================================
# 章节标题识别（v2.46.321 全面重写）
# ---------------------------------------------------------------------
# 判据从强到弱，任何单一判据都不足以定性，靠打分综合：
#   ① 缩进   —— 正文带缩进（4 半角空格 / 2 全角空格），标题顶格。**最可靠**
#   ② 空行   —— 标题通常独占一段，前后有空行
#   ③ 句末标点 —— 标题极少以 。！？ 结尾（"第一回合的KO！"靠这条排除）
#   ④ 格式   —— 覆盖常见写法，不止「第X章」
#
# 历史教训：
#   - v2.46.283 只看格式，把正文里的「第一章咖喱酱被鬼拉下水啦！」当标题
#   - v2.46.320 加缩进但太粗（strict/loose 二分），带缩进的真标题被整批丢掉
#   - v2.46.321 改成打分：缩进只是扣分项，配合句末标点区分「带缩进的真标题」与
#     「正文里的伪标题」。目标是宁可多几个短章，绝不丢正文。
# =====================================================================

TITLE_MAX_LEN = 42

# 中/全角数字与中文数字
_CN_NUM = '0-9０-９零〇一二三四五六七八九十百千万两壹贰叁肆伍陆柒捌玖拾佰仟'

# 强格式：命中即有资格成为标题（仍要过打分）
_STRONG_RES = [
    # 第X章/回/节/卷/篇/集/部/话/幕（含全角数字、中文数字）
    re.compile(rf'^第\s*[{_CN_NUM}]+\s*[章回節节卷篇集部话話幕]'),
    # 卷X / 卷之X
    re.compile(rf'^卷\s*之?\s*[{_CN_NUM}]+'),
    # Chapter N
    re.compile(r'^第?\s*chapter\s*[0-9]+', re.I),
    # 无编号篇名
    re.compile(
        r'^(?:序章|序言|序|楔子|引子|前言|尾声|尾聲|后记|後記|番外|终章|終章|大结局|结局|結局'
        r'|完本感言|写在前面|写在后面|作者的话|正文完|全书完|完本)'
    ),
    # 阿拉伯序号 + 分隔符：0001、 / 1. / 12，
    re.compile(r'^\d{1,5}\s*[、.．,，:：)）]'),
    # 中文序号 + 顿号：一、 / 十二、
    re.compile(r'^[一二三四五六七八九十百千]{1,4}\s*[、.．]'),
]

# 弱格式：必须靠上下文补分才成立（数字+空格，至少三位，减少误判）
_WEAK_RES = [
    re.compile(r'^\d{3,5}\s+\S'),
]

# 包裹符号：`【第一章】开端` / `（第2章）测试` —— 替换成空格而不是删掉，
# 这样「第X章」仍在行首可被匹配；用于显示时一律保留原文。
_BRACKETS_RE = re.compile(r'[【】（）()《》「」〔〕\[\]<>]')
# 噪音前缀：`正文 第四百四十四章 xxx` 这种带前缀的标题
_NOISE_PREFIX_RE = re.compile(
    r'^(?:正文|更新|公告|通知|求票|求收藏|求月票|求推荐|ps|PS|P\.S\.)(?=[\s:：、.\-])[\s:：、.\-]*'
)

CACHE_DIRNAME = '.cache'


def _indent_width(line: str) -> int:
    """行首缩进宽度（半角空格 1、全角空格 2、制表符 4）。

    区分「章标题」与「正文」最可靠的判据：中文 TXT 正文几乎都带缩进，标题通常顶格。
    """
    w = 0
    for ch in line:
        if ch == ' ':
            w += 1
        elif ch == '\t':
            w += 4
        elif ch == '\u3000':
            w += 2
        else:
            break
    return w


def _normalize_title(probe: str) -> str:
    """只用于「格式匹配」，不用于显示。"""
    s = _BRACKETS_RE.sub(' ', probe)
    s = re.sub(r'\s+', ' ', s).strip()
    s = _NOISE_PREFIX_RE.sub('', s)
    return s.strip()


def _score_title(line: str, prev_blank: bool) -> tuple[bool, int]:
    """给一行打分，判断它是不是章标题。返回 (是否标题, 分数)。

    6 分 = 标准格式 + 顶格 + 前有空行
    3 分 = 及格线（带缩进的真标题也能过）
    0 分 = 正文
    """
    probe = line.strip()
    if not probe or len(probe) > TITLE_MAX_LEN:
        return False, 0
    norm = _normalize_title(probe)
    if not norm:
        return False, 0

    strong = any(rx.match(norm) for rx in _STRONG_RES)
    weak = any(rx.match(norm) for rx in _WEAK_RES)
    if not (strong or weak):
        return False, 0

    s = 3 if strong else 1
    ind = _indent_width(line)
    if ind <= 2:
        s += 2          # 顶格
    else:
        s -= 1          # 带缩进 → 可能是正文，但不直接判死
                        # （圣王有一批真标题带 4 空格缩进，判死会丢整章）
    if prev_blank:
        s += 1          # 标题前通常空一行
    if probe[-1] in '。！？…!?」』”"）)':
        s -= 2          # 句末标点收尾 → 更像正文（"第一回合的KO！"靠这条排除）

    # 弱格式必须靠上下文补足
    if weak and not strong and s < 4:
        return False, s
    return s >= 3, s


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


def split_chapters(text: str, min_gap: int = 80) -> list[dict]:
    """单次扫描切章。返回 [{t: 标题, s: 字符起点, e: 字符终点}]。

    v2.46.321 改动（对比 v2.46.320）：
    1. 格式覆盖扩到 章/回/节/卷/篇/集/部/话/幕 + Chapter N + 【】（）包裹 + 「正文」前缀
    2. 缩进从「一票否决」改成「扣 1 分」，配合句末标点区分真标题与正文里的伪标题
    3. **不做序号递进过滤** —— 试过并有实测证据：对 1600 章的长篇，卷内重排/跳号很常见，
       按邻域剔除会误杀真章节（圣王丢 10 个 3500 字的真章、极品家丁丢 3 个 4000~7000 字的）。
       缩进 + 句末标点已经够用，宁可多几个短章，不能少一章正文。

    目录页过滤仍保留：很多 TXT 开头有整页目录，「第001章 xxx」一行接一行，
    直接按行切会切出一半只有标题没有正文的空章。判据是「与下一个标题间距过小」。
    """
    lines = text.split('\n')
    strict: list[tuple[str, int]] = []   # 顶格候选
    loose: list[tuple[str, int]] = []    # 全部候选（含带缩进的）
    offset = 0
    prev_blank = True
    for line in lines:
        ok, _score = _score_title(line, prev_blank)
        if ok:
            probe = line.strip()          # 🔴 存原文：显示时不能丢括号/前缀
            loose.append((probe, offset))
            if _indent_width(line) <= 2:
                strict.append((probe, offset))
        prev_blank = not line.strip()
        offset += len(line) + 1

    # 顶格候选够多说明这本书「正文带缩进、标题顶格」，用 strict 滤掉带缩进的伪标题；
    # 否则说明标题本身也带缩进，只能全用 loose。
    cands = strict if len(strict) >= 3 else loose

    if not cands:
        return [{'t': '正文', 's': 0, 'e': len(text)}]

    # 目录项过滤：紧跟下一个标题（间距过小）= 目录行，不是真章节
    kept: list[tuple[str, int]] = []
    for i, (title, start) in enumerate(cands):
        nxt = cands[i + 1][1] if i + 1 < len(cands) else len(text)
        if nxt - start < min_gap:
            continue
        kept.append((title, start))
    if not kept:            # 全书都是短章（极端情况）：回退不过滤
        kept = cands

    # 组装区间：第一个真标题之前的内容算「开始」
    chapters: list[dict] = []
    if kept[0][1] > 0:
        chapters.append({'t': '开始', 's': 0, 'e': kept[0][1]})
    for i, (title, start) in enumerate(kept):
        end = kept[i + 1][1] if i + 1 < len(kept) else len(text)
        chapters.append({'t': title, 's': start, 'e': end})
    return chapters


"""段落结尾判定用的标点（句末 + 右引号/右括号）。
   行尾是这些字符 → 认为这句/这段写完了；否则是硬换行，要和下一行合并。"""
_SENT_END = '。！？…!?．.』」”"）)～~'


def _paras(seg: str) -> list[str]:
    """章节正文切段（Kindle/Calibre 口径，v2.46.285）。

    TXT 小说的换行有两种常见格式：
    ① 段与段之间有空行；② 每行后面都跟一个空行，但句子在 40 字处被**硬换行**
       截断（万妖之祖就是这种：「…王级高手不如狗！恍若两」/「世啊…」）。
    只按空行切 → 每个半句都成一段，读起来满屏碎片（夜星反馈的「格式问题」）。

    正确做法：按行累积，**行尾是句末标点才收段**，否则继续拼下一行；
    空行也收段（兼容 ① 格式）。这样硬换行的半句会自动接回去。
    """
    out: list[str] = []
    buf: list[str] = []
    for line in seg.split('\n'):
        line = line.replace('\u00a0', ' ').strip()
        if not line:
            if buf:
                out.append(''.join(buf))
                buf = []
            continue
        buf.append(line)
        if line[-1] in _SENT_END:
            out.append(''.join(buf))
            buf = []
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

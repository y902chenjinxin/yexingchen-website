/**
 * LRC 歌词解析（v2.46.327）
 *
 * 只做两件事，因为只有这两件是播放器真正需要的：
 *   parseLrc(text) → [{ t: 秒, text }]  按时间升序
 *   findLine(lines, sec) → 当前行索引（-1 = 还没到第一句）
 *
 * 为什么不用现成库：LRC 的方言就那几种（[00:12.34] / [00:12.340] / 一行多个时间标签 /
 * [ti:] [ar:] 元信息），一个 40 行的正则比引一个包更可控 —— 挂了也好改。
 */

const TAG_RE = /\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]/g

export function hasTimeline(text) {
  if (!text) return false
  return new RegExp(TAG_RE.source).test(text)
}

/**
 * @param {string} text LRC 原文（也可以是纯文本 —— 那样会返回空数组，播放器按「无时间轴」处理）
 * @returns {{t:number, text:string}[]}
 */
export function parseLrc(text) {
  if (!text) return []
  const out = []
  for (const raw of String(text).split('\n')) {
    TAG_RE.lastIndex = 0
    const tags = [...raw.matchAll(TAG_RE)]
    if (!tags.length) continue
    const line = raw.replace(new RegExp(TAG_RE.source, 'g'), '').trim()
    if (!line) continue
    for (const m of tags) {
      const min = Number(m[1]) || 0
      const sec = Number(m[2]) || 0
      // [00:12.3] = 300ms；[00:12.34] = 340ms；[00:12.345] = 345ms
      const frac = m[3] ? Number(`0.${m[3].padEnd(3, '0')}`) : 0
      out.push({ t: min * 60 + sec + frac, text: line })
    }
  }
  out.sort((a, b) => a.t - b.t)
  return out
}

/**
 * 当前该高亮哪一行 —— 二分找「最后一个 t <= sec」。
 * 歌词动辄上百行、每帧都调，线性扫在低端机上会掉帧。
 *
 * ⚠️ 偏移方向（v2.46.328）：**必须略滞后，不能提前**。
 * 之前写了 `sec + 0.15`（提前 150ms），夜星反馈「刚唱到这，就跑下一句了」——
 * 提前量会让人在上一句还唱完时就滑到下一句，比"慢半拍"难受得多。
 * 现在改成 `sec - 0.12`：等这一句真的唱出来再切。LRC 行时间本身是句首，
 * 留 120ms 让字先出声、再位移，观感最稳。
 */
const LINE_LAG = 0.12

export function findLine(lines, sec) {
  if (!lines || !lines.length) return -1
  let lo = 0
  let hi = lines.length - 1
  let ans = -1
  const at = sec - LINE_LAG
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (lines[mid].t <= at) {
      ans = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return ans
}

/** 没有时间轴的纯文本歌词：按行拆开，供播放页静态展示。 */
export function plainLines(text) {
  if (!text) return []
  return String(text)
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => ({ t: 0, text: s }))
}

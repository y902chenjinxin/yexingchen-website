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
 * 当前该高亮哪一行 —— 二分找「最后一个 t <= sec + LINE_AHEAD」。
 * 歌词动辄上百行、每帧都调，线性扫在低端机上会掉帧。
 *
 * ## 偏移方向改过两次，这里是最终结论（v2.46.343）
 *
 * v2.46.328：写成 `sec - 0.12`（滞后 120ms），当时判断"提前切行会抢拍"。
 * 但那是在**时间轴本身不准**的前提下调的 —— 网上抓的 LRC 比人声晚 0.2~0.4 秒，
 * 再加 120ms 滞后，就变成夜星说的「老慢了一拍」。
 *
 * v2.46.343：歌词改成**按音频重新对齐**（后端 services/lyric_align.py，
 * 时间戳 = 人声真正开始的时刻），前置误差没了。此时应当**略微提前**：
 * `<audio>` 从 currentTime 到扬声器出声有 20~60ms 缓冲，
 * 人眼也要一点时间才能读到字 —— 提前 60ms 让"字先亮、声再出"，观感最贴。
 *
 * 所以常量是**正数=提前**。改这里前先确认歌词时间轴是不是对齐过的
 * （music.lyric_source === 'aligned' / 'asr'）。
 */
const LINE_AHEAD = 0.06

export function findLine(lines, sec) {
  if (!lines || !lines.length) return -1
  let lo = 0
  let hi = lines.length - 1
  let ans = -1
  const at = sec + LINE_AHEAD
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

/**
 * 这行是「制作信息」还是真歌词（v2.46.329）。
 *
 * 从网易云/酷狗抓来的 LRC 里，前几行常常是
 *   [00:00.22]凤凰传奇 - 最炫民族风
 *   [00:07.79]作词：张超
 *   [00:08.35]作曲：张超
 * 这些跟着时间轴一起滚，会让"正在唱"的那一行变成「作曲：张超」——很怪。
 * 播放页只展示真歌词，制作信息直接丢掉。
 */
const META_RE = /^(作词|作曲|编曲|混音|母带|制作人|监制|出品|录音|和声|吉他|贝斯|鼓|键盘|弦乐|OP|SP|发行|统筹|策划|纯音乐|此歌曲|这首歌|请欣赏|未经许可)\s*[:：]/i
export function isMetaLine(text) {
  const t = String(text || '').trim()
  if (!t) return true
  return META_RE.test(t)
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

/**
 * 全站格式化工具（v2.46.157）
 *
 * 为什么要有它：扫下来 `toFixed` 87 处、`slice(0,10)` / `replace('T',' ')` 17 处、
 * 各页面自定义的 `function fmtXxx()` 37 个 —— 同一件事有十几种写法，
 * 改一次（比如日期要不要带秒、金额要不要分组）要翻十几个文件。
 *
 * 约定（与本项目既有口径一致）：
 *   · **日期一律按本地日历日处理**，不要用 toISOString().slice(0,10)（东八区会退一天）。
 *   · 金额入参统一是**分**（后端 amount_cents），输出带 ¥ 与两位小数。
 *   · 空值统一返回 ''，不要返回 'Invalid Date' / 'NaN' / '¥NaN'。
 */

const pad = (n) => String(n).padStart(2, '0')

/** 任意值 → Date；失败返回 null */
export function toDate(v) {
  if (!v && v !== 0) return null
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : v
  if (typeof v === 'number') {
    // 秒级时间戳自动补成毫秒（后端偶尔给 10 位）
    const d = new Date(v < 1e12 ? v * 1000 : v)
    return Number.isNaN(d.getTime()) ? null : d
  }
  const s = String(v).trim()
  if (!s) return null
  // 'YYYY-MM-DD HH:mm:ss' 在 Safari 里不被 Date 解析，统一换成 T
  const d = new Date(s.includes('T') ? s : s.replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

/** 2026-10-20 */
export function fmtDate(v, fallback = '') {
  const d = toDate(v)
  if (!d) return fallback
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 2026-10-20 21:30 */
export function fmtDateTime(v, fallback = '') {
  const d = toDate(v)
  if (!d) return fallback
  return `${fmtDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 21:30:05 */
export function fmtTime(v, fallback = '') {
  const d = toDate(v)
  if (!d) return fallback
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 10-20（列表里省年份用） */
export function fmtMd(v, fallback = '') {
  const d = toDate(v)
  if (!d) return fallback
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/**
 * 金额：入参是**分**。
 *   fmtMoney(123456)        → '¥1,234.56'
 *   fmtMoney(123456, {sign:false}) → '1,234.56'
 *   fmtMoney(0)             → '¥0.00'
 */
export function fmtMoney(cents, { sign = true, decimals = 2 } = {}) {
  // 注意：金额的 null 有意按 0 处理（列表里不显示空，显示 ¥0.00）
  const n = Number(cents)
  if (!Number.isFinite(n)) return sign ? '¥0.00' : '0.00'
  const yuan = n / 100
  const body = Math.abs(yuan).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
  return `${sign ? (yuan < 0 ? '-¥' : '¥') : (yuan < 0 ? '-' : '')}${body}`
}

/** 元（不是分）：金额已经是元时用这个 */
export function fmtYuan(yuan, { sign = true, decimals = 2 } = {}) {
  const n = Number(yuan)
  if (!Number.isFinite(n)) return sign ? '¥0.00' : '0.00'
  return fmtMoney(n * 100, { sign, decimals })
}

/** 文件体积：1536 → '1.5 KB' */
export function fmtSize(bytes) {
  // 🔴 Number(null) === 0、Number('') === 0，必须先判空，否则空值会显示成 '0 B'
  if (bytes == null || bytes === '') return ''
  const n = Number(bytes)
  if (!Number.isFinite(n) || n < 0) return ''
  if (n < 1024) return `${Math.round(n)} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let v = n / 1024
  let i = 0
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v >= 10 ? Math.round(v) : v.toFixed(1)} ${units[i]}`
}

/** 相对时间：刚刚 / 5 分钟前 / 3 小时前 / 昨天 / 2026-10-20 */
export function fmtRelative(v, fallback = '') {
  const d = toDate(v)
  if (!d) return fallback
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)} 小时前`
  if (diff < 172800_000) return '昨天'
  return fmtDate(d)
}


/** 2026-10-20 21:30:05（日志类需要到秒） */
export function fmtDateTimeSec(v, fallback = '') {
  const d = toDate(v)
  if (!d) return fallback
  return `${fmtDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 21:30（只要时分，如资讯/快速浏览） */
export function fmtHm(v, fallback = '') {
  const d = toDate(v)
  if (!d) return fallback
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * 时长：秒 → '1:05'（分钟不补零，音乐列表用）
 * 非法/空返回 fallback。
 */
export function fmtDuration(sec, fallback = '-') {
  // 🔴 同上：空值必须先判，否则显示 '0:00'
  if (sec == null || sec === '') return fallback
  const n = Number(sec)
  if (!Number.isFinite(n) || n < 0) return fallback
  const m = Math.floor(n / 60)
  return `${m}:${pad(Math.floor(n % 60))}`
}

/**
 * 时钟：秒 → '01:05'（分钟补零，播放器进度 / 游戏计时用）
 * 非法或 ≤0 返回 '00:00'。
 */
export function fmtClock(sec) {
  const n = Number(sec)
  if (!Number.isFinite(n) || n <= 0) return '00:00'
  return `${pad(Math.floor(n / 60))}:${pad(Math.floor(n % 60))}`
}

/** 纯数字百分比：0.2567 → '26%'（入参若已是 0-100 的整数，直接返回） */
export function fmtPercent(v, decimals = 0) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '0%'
  const p = Math.abs(n) <= 1 ? n * 100 : n
  return `${p.toFixed(decimals)}%`
}

/**
 * 从音乐文件名解析「歌名-作者」（v2.46.234）
 *
 * 需求：上传 `晴天-周杰伦.mp3` 时自动拆成 标题=晴天、作者=周杰伦，
 * 用户不用在两个输入框里各打一次。
 *
 * 规则（按夜星口径，**前面是歌名、后面是作者**）：
 * - `晴天-周杰伦.mp3`   → { title: '晴天', artist: '周杰伦' }
 * - `晴天 - 周杰伦.mp3` → 同上（容忍分隔符两侧空格）
 * - `晴天－周杰伦.mp3`  → 同上（全角破折号 / em dash / en dash 都认）
 * - `晴天.mp3`          → { title: '晴天', artist: '' }
 * - `Live-版-周杰伦.mp3` → { title: 'Live', artist: '版-周杰伦' }（取**第一个**分隔符）
 *
 * 不拆的情况：分隔符在首尾（`-晴天` / `晴天-`），拆出来会有空串。
 *
 * 注意：如果文件名是「作者-歌名」的写法，会拆反 —— 这是按产品口径定的，
 * 不做智能猜测（猜错了更难解释）。用户改了哪个框下次就不再自动覆盖。
 */
export function parseMusicFilename(filename) {
  const raw = String(filename || '')
  // 去掉目录前缀（有些浏览器的 file.name 带路径）与扩展名
  const base = raw.split(/[/\\]/).pop().replace(/\.[^.]+$/, '').trim()
  if (!base) return { title: '', artist: '' }

  const m = base.match(/^(.+?)\s*[-－—–]\s*(.+)$/)
  if (!m) return { title: base, artist: '' }

  const title = m[1].trim()
  const artist = m[2].trim()
  // 任一侧为空就当作没有分隔符（`-晴天` / `晴天-` 这种）
  if (!title || !artist) return { title: base, artist: '' }
  return { title, artist }
}

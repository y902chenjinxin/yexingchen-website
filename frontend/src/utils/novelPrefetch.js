/**
 * 阅读器预取（v2.46.294）
 *
 * 原来打开一本书是串行四次往返：
 *   详情 → 挂载 Reader → 章节目录 → 当前章正文
 * 目录接口（1000+ 章约 30KB gzip）和详情没有任何依赖关系，可以和详情同时发。
 * 这里把目录请求提前到进入路由那一刻，Reader 挂载时直接取结果，省掉一整次串行等待。
 */

const tocCache = new Map()   // novelId -> Promise<data|null>
const TTL = 5 * 60 * 1000

function authHeaders() {
  const tk = localStorage.getItem('token') || ''
  return tk ? { Authorization: `Bearer ${tk}` } : {}
}

/** 提前发起目录请求（幂等，重复调用复用同一个 Promise） */
export function prefetchToc(novelId) {
  const id = Number(novelId)
  if (!id) return null
  if (tocCache.has(id)) return tocCache.get(id)
  const p = fetch(`/api/novels/${id}/chapters`, { headers: authHeaders() })
    .then((r) => (r.ok ? r.json() : null))
    .then((j) => (j && j.code === 0 ? j.data : null))
    .catch(() => null)
  tocCache.set(id, p)
  setTimeout(() => tocCache.delete(id), TTL)
  return p
}

/* ---------------- 首章正文预取 ----------------
   目录没回来之前不知道「当前章是第几章」吗？其实知道 —— 本地进度里就存着章节下标。
   所以进页面就可以把目录、详情、首章三件事一起发，打开时间从「串行 3 段」压成「1 段」。 */

const chapterCache = new Map()   // `${novelId}:${idx}` -> Promise<data|null>

/** 猜当前该读第几章：本地进度下标 > 0，没读过就是第 0 章 */
export function guessChapterIndex(novelId) {
  try {
    const raw = localStorage.getItem(`xuanhuang:reader:prog:${novelId}`)
    const s = raw ? JSON.parse(raw) : null
    const n = s && Number.isInteger(s.chapter) ? s.chapter : 0
    return n >= 0 ? n : 0
  } catch {
    return 0
  }
}

export function prefetchChapter(novelId, idx) {
  const id = Number(novelId)
  if (!id || idx == null || idx < 0) return null
  const key = `${id}:${idx}`
  if (chapterCache.has(key)) return chapterCache.get(key)
  const p = fetch(`/api/novels/${id}/chapters/${idx}`, { headers: authHeaders() })
    .then((r) => (r.ok ? r.json() : null))
    .then((j) => (j && j.code === 0 ? j.data : null))
    .catch(() => null)
  chapterCache.set(key, p)
  setTimeout(() => chapterCache.delete(key), 60000)
  return p
}

export function takeChapter(novelId, idx) {
  const key = `${Number(novelId)}:${idx}`
  const p = chapterCache.get(key)
  if (!p) return null
  chapterCache.delete(key)
  return p
}

/** 取走预取结果（取走后不再复用，避免目录重解析后拿到旧数据） */
export function takeToc(novelId) {
  const id = Number(novelId)
  const p = tocCache.get(id)
  if (!p) return null
  tocCache.delete(id)
  return p
}

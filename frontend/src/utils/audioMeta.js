/**
 * 音频元信息（时长）读取 —— v2.46.231
 *
 * 背景：音乐列表的「时长」列一直是 0:00，因为上传接口从来没写入过 duration
 * （后端模型有这个字段，但前端没解析、后端没接收）。
 *
 * 两个入口：
 * - `readAudioDuration(file)`：上传前读**本地 File 对象**的时长，零网络。
 *   原理：`URL.createObjectURL` + `<audio preload="metadata">`，
 *   浏览器只解析文件头，不会真的下载/解码整个音频。
 * - `readRemoteDuration(url)`：给**历史数据**补全用。对已上传的音频发一次
 *   metadata 请求（nginx 支持 Range，只取文件头），读到时长后回写数据库，
 *   之后列表直接显示，不用再读。
 *
 * 为什么不用后端解析（mutagen）：生产环境不用装新依赖，且浏览器读本地文件
 * 比上传后再解析更快、更省（上传前就知道，随表单一起提交）。
 *
 * 两者都**永不 reject**：读不到就返回 0，调用方按「未知」处理。
 */

/** 兜底超时：某些损坏文件或不支持格式的元数据事件永远不触发 */
const TIMEOUT_MS = 8000

function probe(src, cleanup) {
  return new Promise((resolve) => {
    let settled = false
    const done = (v) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      try { cleanup() } catch { /* 忽略 */ }
      // 直播流 / 损坏文件可能返回 Infinity 或 NaN
      const sec = Number(v)
      resolve(Number.isFinite(sec) && sec > 0 ? Math.round(sec) : 0)
    }
    const timer = setTimeout(() => done(0), TIMEOUT_MS)

    const audio = document.createElement('audio')
    audio.preload = 'metadata'
    audio.muted = true
    audio.addEventListener('loadedmetadata', () => done(audio.duration), { once: true })
    // 有些浏览器元数据非法时只触发 durationchange
    audio.addEventListener('durationchange', () => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) done(audio.duration)
    })
    audio.addEventListener('error', () => done(0), { once: true })
    audio.src = src
  })
}

/**
 * 读本地音频文件时长（秒）。返回 0 表示读不到（格式不支持 / 文件损坏）。
 * @param {File} file
 * @returns {Promise<number>}
 */
export function readAudioDuration(file) {
  if (!file || typeof URL === 'undefined' || !URL.createObjectURL) return Promise.resolve(0)
  let url = ''
  try {
    url = URL.createObjectURL(file)
  } catch {
    return Promise.resolve(0)
  }
  return probe(url, () => URL.revokeObjectURL(url))
}

/**
 * 读远程音频 URL 的时长（秒）。用于历史数据补全。
 * 注意：会给服务器发一次 metadata 请求（通常只有几 KB 的头），别在长列表里
 * 无节制并发 —— 调用方应串行或小并发。
 * @param {string} url
 * @returns {Promise<number>}
 */
export function readRemoteDuration(url) {
  if (!url) return Promise.resolve(0)
  return probe(url, () => { /* 远程 URL 无需释放 */ })
}

/**
 * 小并发地跑一批任务，避免同时开几十个 audio 探针把连接池占满。
 * @param {Array} list
 * @param {(item) => Promise<any>} fn
 * @param {number} concurrency
 */
export async function runWithConcurrency(list, fn, concurrency = 3) {
  const results = []
  let cursor = 0
  const workers = Array.from({ length: Math.min(concurrency, list.length) }, async () => {
    while (cursor < list.length) {
      const idx = cursor++
      results[idx] = await fn(list[idx], idx)
    }
  })
  await Promise.all(workers)
  return results
}

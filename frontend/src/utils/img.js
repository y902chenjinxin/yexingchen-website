/**
 * 图片 URL 工具（v2.46.145）
 *
 * 背景：`/uploads/` 由 nginx 直出、带 30 天缓存，**慢的不是缓存而是原图**——
 * 生产 42 张图平均 1.1MB，最狠的通讯录头像 10.6MB、倒计时背景 9.7MB。
 * 列表/头像只要 160~480px，却一直在下原图。
 *
 * 用法：`<img :src="thumb(url, 160)" loading="lazy" decoding="async">`
 * 详情/原图预览仍然用原 URL（不要 thumb），否则放大就糊了。
 *
 * 转不了的（外链、data:、blob:、已经是缩略图）原样返回，调用方不用判断。
 */
const SIZES = [160, 240, 320, 480, 768, 960]

function nearest(w) {
  const n = Number(w) || 480
  return SIZES.reduce((a, b) => (Math.abs(b - n) < Math.abs(a - n) ? b : a), SIZES[0])
}

/** 从任意 URL 里取出 uploads 下的相对路径；不是 uploads 的返回空串 */
export function uploadsPath(url) {
  if (!url || typeof url !== 'string') return ''
  let u = url.trim()
  if (!u || u.startsWith('data:') || u.startsWith('blob:')) return ''
  // 同源绝对地址 → 只留 path
  try {
    if (/^https?:\/\//i.test(u)) {
      const parsed = new URL(u)
      if (parsed.host !== window.location.host) return ''
      u = parsed.pathname + parsed.search
    }
  } catch {
    return ''
  }
  const m = u.match(/^\/?uploads\/(.+)$/)
  if (!m) return ''
  return m[1].replace(/^\/+/, '').split('?')[0]
}

/**
 * 缩略图地址。
 * @param {string} url  原图地址（/uploads/... 或同源绝对地址）
 * @param {number} w    期望宽度，会吸附到 [160,240,320,480,768,960]
 * @returns {string}    可用的图片地址（不可缩略时原样返回）
 */
export function thumb(url, w = 480) {
  const rel = uploadsPath(url)
  if (!rel) return url || ''
  // 缩略图目录本身不要再套一层
  if (rel.startsWith('_thumbs/')) return url
  return `/api/uploads/thumb?p=${encodeURIComponent(rel)}&w=${nearest(w)}`
}

/**
 * 生成 srcset（同一张图的多档），配合 sizes 让浏览器自己挑。
 * @example <img :src="thumb(u, 480)" :srcset="thumbSrcset(u, [320,480,768])" sizes="(max-width: 430px) 45vw, 220px">
 */
export function thumbSrcset(url, widths = [320, 480, 768]) {
  const rel = uploadsPath(url)
  if (!rel) return ''
  return widths
    .map((w) => {
      const s = nearest(w)
      return `/api/uploads/thumb?p=${encodeURIComponent(rel)}&w=${s} ${s}w`
    })
    .join(', ')
}

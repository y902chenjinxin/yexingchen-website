/* 玄黄 Service Worker
 *
 * 仅缓存静态壳与稳定资源：
 *   - /index.html
 *   - /assets/**
 *   - /icons/**
 *   - /manifest.webmanifest
 *
 * 不缓存：API 请求、/api/**、Authorization 头请求、AI 响应、登录页 POST。
 * 不缓存：跨源资源（CDN/字体/统计）。
 * 注册失败不应阻塞应用启动（main.js 中已 try/catch）。
 */
const VERSION = 'xuanhuang-v593'
const STATIC_CACHE = `${VERSION}-static`

self.addEventListener('install', (event) => {
  // 立即激活，无需等待
  self.skipWaiting()
})

self.addEventListener('message', (event) => {
  if (event?.data?.type === 'SKIP_WAITING') {
    try { self.skipWaiting() } catch {}
  }
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  // 非 GET（POST/PUT/DELETE 等）一律放行：避免污染缓存 + 业务幂等性
  if (req.method !== 'GET') return
  let url
  try {
    url = new URL(req.url)
  } catch {
    return
  }

  // 不同源：放行（不缓存 CDN/字体/统计）
  if (url.origin !== self.location.origin) return

  // API 请求：不缓存
  if (url.pathname.startsWith('/api/')) return

  // 带 Authorization 头的请求：不缓存
  if (req.headers.get('authorization')) return

  // 仅缓存静态资源（vite 构建产物 + 桌宠视频）
  const isStaticAsset =
    url.pathname.startsWith('/assets/') ||
    url.pathname === '/' ||
    url.pathname === '/index.html' ||
    url.pathname === '/manifest.webmanifest' ||
    url.pathname.startsWith('/icons/') ||
    url.pathname.startsWith('/sounds/') ||
    url.pathname.startsWith('/whale-pet/') ||
    url.pathname.startsWith('/geo/') ||
    url.pathname.startsWith('/preview/')

  if (!isStaticAsset) return

  // 首帧壳（/ 与 index.html）网络优先：每次导航都必须拿到最新入口，避免旧壳残影
  const isShell = url.pathname === '/' || url.pathname === '/index.html'

  /* 「HTML 冒充资源」防御（v2.45.1）
   *
   * 部署会整体替换 dist/，老壳引用的旧 chunk 随即从磁盘消失。若此时服务器把
   * 缺失的 chunk 顶成 SPA fallback（HTTP 200 + text/html），浏览器会把这段 HTML
   * 当 JS / CSS 用 —— 症状是「样式全丢、图标巨大」，而且一旦被本 SW 缓存就
   * **刷新也不会好**。服务器侧已改成缺文件回 404（见 nginx/yexingchen.cn.conf），
   * 这里再兜一层：识别到 text/html 就不缓存，并清掉已经中毒的旧条目让其自愈。 */
  const wantsAsset = url.pathname.startsWith('/assets/')
  const isHtmlPoison = (res) => {
    if (!res || !wantsAsset) return false
    const ct = (res.headers.get('content-type') || '').toLowerCase()
    return ct.includes('text/html')
  }

  event.respondWith(
    caches.open(STATIC_CACHE).then((cache) => {
      const networkFirst = () =>
        fetch(req)
          .then((response) => {
            if (isHtmlPoison(response)) {
              cache.delete(req).catch(() => {})
              return new Response('', { status: 404, statusText: 'asset-missing' })
            }
            if (response && response.status === 200 && response.type === 'basic') {
              cache.put(req, response.clone()).catch(() => {})
            }
            return response
          })
          .catch(() => cache.match(req))
      if (isShell) {
        return networkFirst()
      }
      return cache.match(req).then((cached) => {
        if (cached && !isHtmlPoison(cached)) return cached
        // 中毒条目：删掉再回源，别让「HTML 当 CSS」一直粘着
        if (cached) cache.delete(req).catch(() => {})
        return networkFirst()
      })
    })
  )
})


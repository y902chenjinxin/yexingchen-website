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
const VERSION = 'xuanhuang-v32'
const STATIC_CACHE = `${VERSION}-static`

self.addEventListener('install', (event) => {
  // 立即激活，无需等待
  self.skipWaiting()
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
    url.pathname.startsWith('/whale-pet/')

  if (!isStaticAsset) return

  event.respondWith(
    caches.open(STATIC_CACHE).then((cache) =>
      cache.match(req).then((cached) => {
        const fetchPromise = fetch(req)
          .then((response) => {
            // 仅缓存同源 200 basic 响应，避免 opaque/重定向污染
            if (response && response.status === 200 && response.type === 'basic') {
              cache.put(req, response.clone()).catch(() => {})
            }
            return response
          })
          .catch(() => cached)
        return cached || fetchPromise
      })
    )
  )
})

/**
 * 注册 Service Worker（失败不阻塞）。
 * 仅在生产构建 + 支持 navigator.serviceWorker 时启用。
 */
export function registerServiceWorker() {
  if (typeof window === 'undefined') return
  if (!('serviceWorker' in navigator)) return
  if (!import.meta.env || import.meta.env.PROD !== true) return

  try {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          // 注册成功不做任何事
        })
        .catch(() => {
          // 静默失败
        })
    })
  } catch {
    // 静默失败
  }
}

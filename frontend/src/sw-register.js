/**
 * 注册 Service Worker（失败不阻塞）。
 * 仅在生产构建 + 支持 navigator.serviceWorker 时启用。
 *
 * 关键策略（v2.39.2+）：新 SW 一进入 waiting 状态立刻 skipWaiting + claim，
 * 让旧页面也立刻用上新资源；如发现 controller 已变化（说明是激活后的 SW），
 * 主动 location.reload() 一次，避免「改了资源但页面仍在旧 SW 控制下」的诡异现象。
 */
export function registerServiceWorker() {
  if (typeof window === 'undefined') return
  if (!('serviceWorker' in navigator)) return
  if (!import.meta.env || import.meta.env.PROD !== true) return

  // 防止 controller 已变化（首次 install + claim 后）时旧页面继续显示旧资源
  let refreshing = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (refreshing) return
    refreshing = true
    // 页面已在新 SW 控制下，硬刷一次取最新静态资源
    try { window.location.reload() } catch {}
  })

  try {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          // 若已有 waiting 状态的 SW，立刻激活它
          if (reg.waiting) {
            try { reg.waiting.postMessage({ type: 'SKIP_WAITING' }) } catch {}
          }
          // 监听后续更新：新 SW 进入 waiting 时立刻激活
          reg.addEventListener('updatefound', () => {
            const sw = reg.installing
            if (!sw) return
            sw.addEventListener('statechange', () => {
              if (sw.state === 'installed' && navigator.serviceWorker.controller) {
                // 新 SW 已 installed，控制权仍在旧 SW——让它立刻接管
                try { sw.postMessage({ type: 'SKIP_WAITING' }) } catch {}
              }
            })
          })
        })
        .catch(() => {
          // 静默失败
        })

      // 接收 SKIP_WAITING 指令后激活
      navigator.serviceWorker.addEventListener('message', (e) => {
        if (e?.data?.type === 'SKIP_WAITING' && e.source && e.source.state === 'installed') {
          try { e.source.postMessage({ type: 'SKIP_WAITING' }) } catch {}
        }
      })
    })
  } catch {
    // 静默失败
  }
}

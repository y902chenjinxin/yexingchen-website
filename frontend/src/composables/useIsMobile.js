import { ref, onMounted, onBeforeUnmount, computed } from 'vue'

// 与桌面端共享单一代码库：手机上渲染独立沉浸式外壳（底部两 Tab），桌面保持现状。
// 断点沿用全站 767px，与桌面 768+ 不冲突。
const MQ = '(max-width: 767px)'

/**
 * 是否走**移动端外壳**。
 *
 * v2.40.30 政策调整（夜星拍板）：
 *   **只有玄黄自己的 APK（WebView 注入 UA `XuanHuangApp/x.y.z`）才用移动端样式**；
 *   手机浏览器（含鸿蒙自带浏览器、微信等）一律走**桌面版**布局 ——
 *   配合入口处的 viewport 覆写（宽 1280），手机上看到的是可缩放的完整桌面站。
 *
 * 判断依据只认 APK 标识，不再看「窄屏 + 移动 UA」：
 *  - 之前的双条件把所有手机浏览器都判成移动端，夜星要的是浏览器里看网页版；
 *  - APK 的 UA 由 MainActivity 注入（见 /opt/android-build/webview/yexingchen）。
 *
 * 逃生口：URL 带 `?m=1` 可强制移动端（写入 localStorage，`?m=0` 清除），
 * 万一装了旧版不带标记的 APK 也能手动切回来。
 */
const APK_UA = /XuanHuangApp/i
const FORCE_KEY = 'xuanhuang_force_mobile'

function readForce() {
  try {
    const q = new URLSearchParams(window.location.search)
    if (q.get('m') === '1') localStorage.setItem(FORCE_KEY, '1')
    else if (q.get('m') === '0') localStorage.removeItem(FORCE_KEY)
    return localStorage.getItem(FORCE_KEY) === '1'
  } catch { return false }
}

function isApkWebView() {
  if (typeof navigator === 'undefined') return false
  return APK_UA.test(navigator.userAgent || '')
}

function compute() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  if (readForce()) return true
  return isApkWebView()
}

/** #app 的移动端类名也按同一口径走（桌面浏览器窗口压窄不再切移动端） */
export function shouldUseMobileShell() {
  return compute()
}

export function useIsMobile() {
  const isMobile = ref(compute())
  let mq = null

  const sync = () => { isMobile.value = compute() }

  onMounted(() => {
    mq = window.matchMedia ? window.matchMedia(MQ) : null
    sync()
    if (mq && mq.addEventListener) mq.addEventListener('change', sync)
    window.addEventListener('resize', sync, { passive: true })
  })

  onBeforeUnmount(() => {
    if (mq && mq.removeEventListener) mq.removeEventListener('change', sync)
    window.removeEventListener('resize', sync)
  })

  return { isMobile: computed(() => isMobile.value) }
}

/** 供非组件场景（如路由守卫）直接取一次判定结果 */
export function detectIsMobile() {
  return compute()
}

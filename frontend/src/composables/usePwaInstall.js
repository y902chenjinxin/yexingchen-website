import { ref, computed } from 'vue'

/**
 * PWA 安装引导。
 *
 * - Chromium（Android/桌面）：监听 beforeinstallprompt，把原生安装事件存起来，
 *   用户点「安装 App」时再触发（浏览器规定 prompt() 必须在用户手势里调用）
 * - iOS Safari：不派发该事件，只能引导用户「分享 → 添加到主屏幕」；
 *   通过 isIos() + 是否已处于 standalone 判断要不要显示手动引导
 * - 已安装（display-mode: standalone）时所有引导都不显示
 *
 * Web Push 预留：订阅推送需要在 SW 就绪后调用
 *   registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })
 *   服务端暂未部署 VAPID 公钥，接入时新增 /api/push/* 路由即可，前端只需在此文件补订阅逻辑。
 */

const deferredPrompt = ref(null)
const installed = ref(false)
const inited = ref(false)
const iosLike = ref(false)

function isStandalone() {
  return window.matchMedia?.('(display-mode: standalone)').matches
    || window.navigator.standalone === true
}

function isIos() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent)
    // iPadOS 13+ 桌面 UA，用平台手势特征兜底
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

export function usePwaInstall() {
  if (!inited.value) {
    inited.value = true
    installed.value = isStandalone()
    iosLike.value = isIos()
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault()  // 阻止浏览器自己的迷你横幅，改由站内入口触发
      deferredPrompt.value = e
    })
    window.addEventListener('appinstalled', () => {
      installed.value = true
      deferredPrompt.value = null
    })
  }

  // 响应式：beforeinstallprompt 到达 / 安装完成都会自动刷新 UI
  const canInstall = computed(() => !!deferredPrompt.value && !installed.value)
  const showIosGuide = computed(() => iosLike.value && !installed.value)

  /** 触发原生安装弹窗；返回 'accepted' | 'dismissed' | 'unavailable' */
  async function promptInstall() {
    if (!deferredPrompt.value) return 'unavailable'
    deferredPrompt.value.prompt()
    const { outcome } = await deferredPrompt.value.userChoice
    deferredPrompt.value = null
    return outcome
  }

  return { canInstall, showIosGuide, promptInstall, isIos, installed }
}

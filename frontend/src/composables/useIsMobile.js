import { ref, onMounted, onBeforeUnmount, computed } from 'vue'

// 与桌面端共享单一代码库：手机上渲染独立沉浸式外壳（底部两 Tab），桌面保持现状。
// 断点沿用全站 767px，与桌面 768+ 不冲突。
const MQ = '(max-width: 767px)'

/**
 * 是否「真正的移动设备」。
 *
 * ⚠️ 不能只看宽度：桌面浏览器把窗口压窄（典型场景是**打开 DevTools 停靠**）时
 * 宽度会掉到 767px 以下，若只看宽度会误判成手机端、整站切成移动布局。
 * 因此叠加设备信号（移动 UA 或 多点触控）双条件判定。
 * DevTools 的设备模拟会同时命中 UA + maxTouchPoints，模拟依旧可用。
 */
function isTouchOrMobileUA() {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent || ''
  const mobileUA = /Android|iPhone|iPad|iPod|Windows Phone|HarmonyOS|Mobile|MicroMessenger/i.test(ua)
  const multiTouch = (navigator.maxTouchPoints || 0) > 1
  return mobileUA || multiTouch
}

function compute() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia(MQ).matches && isTouchOrMobileUA()
}

export function useIsMobile() {
  const isMobile = ref(false)
  let mq = null

  const sync = () => { isMobile.value = compute() }

  onMounted(() => {
    mq = window.matchMedia ? window.matchMedia(MQ) : null
    sync()
    if (mq && mq.addEventListener) mq.addEventListener('change', sync)
    // 窗口尺寸变化（含 DevTools 停靠）也重新判定
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

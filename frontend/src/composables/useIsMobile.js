import { ref, onMounted, onBeforeUnmount, computed } from 'vue'

// 与桌面端共享单一代码库：手机上渲染独立沉浸式外壳（底部三 Tab），桌面保持现状。
// 断点沿用全站 767px，与桌面 768+ 不冲突。
const MQ = '(max-width: 767px)'

function createMatcher() {
  if (typeof window === 'undefined' || !window.matchMedia) return null
  return window.matchMedia(MQ)
}

export function useIsMobile() {
  const isMobile = ref(false)
  let mq = null

  const onChange = (e) => { isMobile.value = e.matches }

  onMounted(() => {
    mq = createMatcher()
    if (mq) {
      isMobile.value = mq.matches
      mq.addEventListener('change', onChange)
    }
  })

  onBeforeUnmount(() => {
    if (mq && mq.removeEventListener) mq.removeEventListener('change', onChange)
  })

  return { isMobile: computed(() => isMobile.value) }
}
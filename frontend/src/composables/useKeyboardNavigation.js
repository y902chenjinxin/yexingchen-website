/**
 * useKeyboardNavigation.js
 * 键盘导航 - Tab遍历岛屿，方向键移动，?显示帮助
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useKeyboardNavigation() {
  const router = useRouter()
  const islands = ref([])
  const currentIndex = ref(-1)
  const isHelpVisible = ref(false)

  // 玉简路由映射
  const routes = {
    music: '/island/music',
    novel: '/island/novel',
    video: '/island/video',
    log: '/island/log',
    tool: '/island/tool'
  }

  // 获取所有玉简元素
  function getIslandElements() {
    return document.querySelectorAll('.jade-card')
  }

  // 设置玉简聚焦状态
  function setIslandFocus(index) {
    // 移除之前的聚焦
    islands.value.forEach((el, i) => {
      if (el) el.classList.remove('jade-focused')
    })

    // 添加新的聚焦
    if (index >= 0 && index < islands.value.length) {
      currentIndex.value = index
      const el = islands.value[index]
      if (el) {
        el.classList.add('jade-focused')
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    } else {
      currentIndex.value = -1
    }
  }

  // 获取当前聚焦的玉简类型
  function getCurrentIslandType() {
    if (currentIndex.value >= 0 && currentIndex.value < islands.value.length) {
      const el = islands.value[currentIndex.value]
      return el?.dataset.type || null
    }
    return null
  }

  // 数字快捷键
  const numberKeys = ['1', '2', '3', '4', '5']

  // 键盘事件处理
  function handleKeydown(e) {
    // 如果没有首页元素，忽略
    const homePage = document.querySelector('.home-page')
    if (!homePage) return

    switch (e.key) {
      case 'Tab':
        e.preventDefault()
        if (e.shiftKey) {
          // Shift+Tab 向后遍历
          if (currentIndex.value <= 0) {
            currentIndex.value = islands.value.length - 1
          } else {
            currentIndex.value--
          }
        } else {
          // Tab 向前遍历
          if (currentIndex.value < 0 || currentIndex.value >= islands.value.length - 1) {
            currentIndex.value = 0
          } else {
            currentIndex.value++
          }
        }
        setIslandFocus(currentIndex.value)
        break

      case 'Enter':
        if (currentIndex.value >= 0) {
          const type = getCurrentIslandType()
          if (type && routes[type]) {
            router.push(routes[type])
          }
        }
        break

      case 'Escape':
        if (isHelpVisible.value) {
          isHelpVisible.value = false
        } else if (currentIndex.value >= 0) {
          currentIndex.value = -1
          islands.value.forEach(el => el?.classList.remove('jade-focused'))
        }
        break

      case '?':
        isHelpVisible.value = !isHelpVisible.value
        break

      default:
        // 数字快捷键 1-5
        if (numberKeys.includes(e.key)) {
          const num = parseInt(e.key) - 1
          setIslandFocus(num)
        }
    }
  }

  // 初始化
  function setup() {
    // 获取岛屿元素
    islands.value = Array.from(getIslandElements())

    // 监听键盘事件
    document.addEventListener('keydown', handleKeydown)
  }

  // 清理
  function cleanup() {
    document.removeEventListener('keydown', handleKeydown)
    isHelpVisible.value = false
    currentIndex.value = -1
  }

  onMounted(() => {
    setup()
  })

  onUnmounted(() => {
    cleanup()
  })

  return {
    islands,
    currentIndex,
    isHelpVisible,
    setup,
    cleanup
  }
}